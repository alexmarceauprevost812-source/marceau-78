// Fonction serverless : c'est elle qui parle à Claude.
// La clé API reste ici, côté serveur — elle ne part jamais dans le navigateur.
import Anthropic from "@anthropic-ai/sdk";
import { timingSafeEqual } from "node:crypto";

export const config = { maxDuration: 60 };

// Les modèles qu'on accepte. Le client choisit dans cette liste, jamais ailleurs :
// sans ça, n'importe qui pourrait faire payer au site un modèle bien plus cher.
const MODELES = new Set([
  "claude-opus-5",
  "claude-sonnet-5",
  "claude-haiku-4-5",
  "claude-fable-5-1",
]);
const MODELE_DEFAUT = "claude-sonnet-5";
const MAX_TOKENS = 8000;
const RECHERCHES_MAX = 4;      // recherches web par question
const TOURS_MAX = 5;           // relances quand l'API met la réponse sur pause
const MESSAGES_MAX = 40;       // on ne renvoie pas une conversation sans fin
const CARACTERES_MAX = 60000;  // ni un pavé

const QUEBECOIS =
  "Tu es un vrai Québécois. Tu parles pis tu écris en français québécois familier, " +
  "comme quelqu'un d'ici qui jase avec un chum : tu tutoies, tu utilises les tournures " +
  "orales (y'a, j'suis, t'sais, c'est-tu, faque, pis, ben, là, pantoute, tantôt, astheure) " +
  "et les expressions d'ici quand ça sonne naturel (c'est l'fun, ça a pas d'allure, " +
  "lâche pas, c'est correct, mets-en). Garde ça clair et facile à lire, sans en beurrer " +
  "trop épais : pas de caricature, pas de sacres à moins que la personne en utilise. " +
  "Les termes techniques, les commandes et le code restent exacts et bien écrits. ";

function instructionsSysteme() {
  const aujourdhui = new Date().toISOString().slice(0, 10);
  return (
    "Tu es l'assistant intégré à une application d'écriture. " + QUEBECOIS +
    "Écris seulement en texte brut : pas de Markdown, pas d'astérisques, " +
    "pas de dièses, pas de tableaux. Pour une liste, utilise des tirets simples. " +
    "Fais une recherche web dès que la question touche l'actualité, des prix, " +
    "des horaires, la météo, des personnes ou n'importe quoi qui a pu changer récemment. " +
    "Quand ta réponse explique un plan d'action ou des étapes à suivre, termine-la " +
    "par un bloc exactement comme celui-ci (une étape courte par ligne, moins de 12 mots) :\n" +
    "[PLAN]\n1. Première étape\n2. Deuxième étape\n[/PLAN]\n" +
    "Ajoute ce bloc seulement s'il y a un vrai plan ou des étapes. " +
    `Date d'aujourd'hui : ${aujourdhui}.`
  );
}

/** Garde seulement ce qui est valide : rôles connus, texte non vide, taille bornée. */
function nettoyerMessages(brut) {
  if (!Array.isArray(brut)) return [];
  const messages = [];
  for (const m of brut.slice(-MESSAGES_MAX)) {
    if (!m || (m.role !== "user" && m.role !== "assistant")) continue;
    const contenu = typeof m.content === "string" ? m.content.trim() : "";
    if (contenu) messages.push({ role: m.role, content: contenu.slice(0, CARACTERES_MAX) });
  }
  while (messages.length && messages[0].role !== "user") messages.shift();
  return messages;
}

function messageErreur(err) {
  const code = err?.status ?? err?.statusCode;
  if (code === 401) return "La clé API du serveur est refusée. Le propriétaire du site doit la vérifier.";
  if (code === 429) return "Trop de questions d'un coup. Attends quelques secondes pis réessaie.";
  if (code === 400) return "La demande a été refusée : " + (err?.message || "requête invalide") + ".";
  if (code >= 500) return "Le service est surchargé en ce moment. Réessaie dans un instant.";
  if (err?.name === "APIConnectionTimeoutError") return "La réponse a pris trop de temps. Réessaie.";
  if (err?.name === "APIConnectionError") return "Le serveur n'arrive pas à joindre Claude. Réessaie.";
  return "Erreur : " + (err?.message || err);
}

/** Compare deux codes sans laisser le temps de réponse trahir les bons caractères. */
function memeCode(recu, attendu) {
  const a = Buffer.from(String(recu ?? ""), "utf8");
  const b = Buffer.from(String(attendu), "utf8");
  return a.length === b.length && timingSafeEqual(a, b);
}


export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ erreur: "Utilise POST." });
    return;
  }
  if (!process.env.ANTHROPIC_API_KEY) {
    res.status(500).json({
      erreur: "Le serveur n'a pas de clé API. Ajoute ANTHROPIC_API_KEY dans les " +
              "variables d'environnement Vercel, pis redéploie.",
    });
    return;
  }
  // Protection optionnelle : si CODE_ACCES est défini, il faut le fournir.
  const attendu = process.env.CODE_ACCES;
  if (attendu && !memeCode(req.headers["x-code-acces"], attendu)) {
    res.status(401).json({ erreur: "Code d'accès manquant ou invalide.", besoinCode: true });
    return;
  }

  const demande = String(req.body?.modele || "");
  const modele = MODELES.has(demande) ? demande : MODELE_DEFAUT;

  const messages = nettoyerMessages(req.body?.messages);
  if (!messages.length) {
    res.status(400).json({ erreur: "Aucune question à envoyer." });
    return;
  }

  res.writeHead(200, {
    "Content-Type": "text/event-stream; charset=utf-8",
    "Cache-Control": "no-cache, no-transform",
    Connection: "keep-alive",
    "X-Accel-Buffering": "no",
  });
  const envoyer = (objet) => res.write(`data: ${JSON.stringify(objet)}\n\n`);

  const client = new Anthropic();
  const sources = [];
  let conversation = messages;

  try {
    for (let tour = 0; tour < TOURS_MAX; tour++) {
      const flux = client.messages.stream({
        model: modele,
        max_tokens: MAX_TOKENS,
        system: instructionsSysteme(),
        messages: conversation,
        tools: [{ type: "web_search_20260209", name: "web_search", max_uses: RECHERCHES_MAX }],
      });

      flux.on("text", (bout) => envoyer({ type: "texte", t: bout }));
      const reponse = await flux.finalMessage();

      for (const bloc of reponse.content || []) {
        if (bloc.type !== "text") continue;
        for (const citation of bloc.citations || []) {
          if (citation.url && !sources.some((s) => s.url === citation.url)) {
            sources.push({ titre: citation.title || citation.url, url: citation.url });
          }
        }
      }

      // Longue recherche : l'API met la réponse sur pause, on la relance
      if (reponse.stop_reason === "pause_turn") {
        conversation = [...conversation, { role: "assistant", content: reponse.content }];
        continue;
      }
      if (reponse.stop_reason === "max_tokens") {
        envoyer({ type: "texte", t: "\n\n(Réponse coupée : elle était trop longue.)" });
      }
      break;
    }
    envoyer({ type: "fin", sources: sources.slice(0, 5) });
  } catch (err) {
    console.error("chat:", err);
    envoyer({ type: "erreur", message: messageErreur(err) });
  }
  res.end();
}
