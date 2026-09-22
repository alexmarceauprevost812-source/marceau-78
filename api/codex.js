// Le Codex quand la personne n'a pas sa propre clé : c'est le serveur du site
// qui paie, donc c'est lui qui écrit les consignes et qui décide du modèle.
//
// Les outils ne s'exécutent PAS ici. Le navigateur les exécute contre GitHub
// avec le token de la personne. Ici on ne fait que passer la question à Claude
// et renvoyer ce qu'il répond — y compris ses demandes d'outils.
import Anthropic from "@anthropic-ai/sdk";
import { timingSafeEqual } from "node:crypto";

export const config = { maxDuration: 60 };

const MODELES = new Set([
  "claude-opus-5",
  "claude-sonnet-5",
  "claude-haiku-4-5",
  "claude-fable-5-1",
]);
const MODELE_DEFAUT = "claude-sonnet-5";
const MAX_TOKENS = 8000;
const MESSAGES_MAX = 60;
const CARACTERES_MAX = 60000;

// Les seuls outils qu'on accepte de décrire à Claude. Le client envoie leur
// schéma, mais un nom inconnu est jeté : la clé du site ne sert pas à inventer
// des capacités qu'on n'a pas écrites nous autres mêmes.
const OUTILS_CONNUS = new Set([
  "lister_fichiers", "lire_fichier", "chercher", "ecrire_fichier", "remplacer_dans_fichier",
  "pousser_sur_github",
]);

const QUEBECOIS =
  "Tu parles pis tu écris en français québécois familier : tu tutoies, tu utilises " +
  "les tournures orales (y'a, j'suis, t'sais, faque, pis, ben, là) quand ça sonne " +
  "naturel. Pas de caricature. Les termes techniques, les commandes et le code " +
  "restent exacts et bien écrits. ";

function instructionsSysteme() {
  return (
    "Tu es l'assistant Codex : tu travailles dans un vrai projet GitHub. " + QUEBECOIS +
    "Tu as des outils pour lister les fichiers, en lire, chercher du texte partout, " +
    "écrire un fichier au complet et corriger un bout précis. Sers-t'en au lieu de " +
    "deviner : avant de changer quoi que ce soit, lis le fichier. " +
    "Pour une petite correction, prends remplacer_dans_fichier plutôt que de " +
    "réécrire tout le fichier. " +
    "Tes changements vont dans des onglets. Si l'outil pousser_sur_github t'est offert, " +
    "la personne t'a donné le droit d'envoyer : appelle-le UNE SEULE FOIS à la fin, avec un " +
    "message de commit court. S'il ne t'est pas offert, dis à la personne de cliquer " +
    "Enregistrer quand t'as fini. " +
    "Écris en texte brut, sans Markdown, sauf les blocs de code en ```."
  );
}

/** Garde seulement ce qui est valide. Les blocs d'outils passent tels quels. */
function nettoyerMessages(brut) {
  if (!Array.isArray(brut)) return [];
  const messages = [];
  for (const m of brut.slice(-MESSAGES_MAX)) {
    if (!m || (m.role !== "user" && m.role !== "assistant")) continue;
    if (typeof m.content === "string") {
      const texte = m.content.trim();
      if (texte) messages.push({ role: m.role, content: texte.slice(0, CARACTERES_MAX) });
    } else if (Array.isArray(m.content) && m.content.length) {
      messages.push({ role: m.role, content: m.content });
    }
  }
  while (messages.length && messages[0].role !== "user") messages.shift();
  return messages;
}

function nettoyerOutils(brut) {
  if (!Array.isArray(brut)) return [];
  return brut
    .filter((o) => o && OUTILS_CONNUS.has(o.name) && o.input_schema)
    .slice(0, OUTILS_CONNUS.size)
    .map((o) => ({
      name: o.name,
      description: String(o.description || "").slice(0, 2000),
      input_schema: o.input_schema,
    }));
}

function memeCode(recu, attendu) {
  const a = Buffer.from(String(recu ?? ""), "utf8");
  const b = Buffer.from(String(attendu), "utf8");
  return a.length === b.length && timingSafeEqual(a, b);
}

function messageErreur(err) {
  const code = err?.status ?? err?.statusCode;
  if (code === 401) return "La clé API du serveur est refusée. Le propriétaire du site doit la vérifier.";
  if (code === 429) return "Trop de demandes d'un coup. Attends quelques secondes.";
  if (code === 400) return "Demande refusée : " + (err?.message || "requête invalide") + ".";
  if (code >= 500) return "Le service est surchargé. Réessaie dans un instant.";
  return "Erreur : " + (err?.message || err);
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ erreur: "Utilise POST." });
    return;
  }
  if (!process.env.ANTHROPIC_API_KEY) {
    res.status(500).json({
      erreur: "Le serveur n'a pas de clé API. Mets la tienne dans Paramètres, " +
              "ou le propriétaire du site doit ajouter ANTHROPIC_API_KEY sur Vercel.",
    });
    return;
  }
  const attendu = process.env.CODE_ACCES;
  if (attendu && !memeCode(req.headers["x-code-acces"], attendu)) {
    res.status(401).json({ erreur: "Code d'accès manquant ou invalide.", besoinCode: true });
    return;
  }

  const demande = String(req.body?.modele || "");
  const modele = MODELES.has(demande) ? demande : MODELE_DEFAUT;
  const messages = nettoyerMessages(req.body?.messages);
  const tools = nettoyerOutils(req.body?.outils);
  if (!messages.length) {
    res.status(400).json({ erreur: "Aucune demande à envoyer." });
    return;
  }

  try {
    const client = new Anthropic();
    const reponse = await client.messages.create({
      model: modele,
      max_tokens: MAX_TOKENS,
      system: instructionsSysteme(),
      messages,
      ...(tools.length ? { tools } : {}),
    });
    res.status(200).json(reponse);
  } catch (err) {
    console.error("codex:", err);
    res.status(err?.status >= 400 && err?.status < 600 ? err.status : 500)
       .json({ erreur: messageErreur(err) });
  }
}
