// Écriture — version web.
// Trois façons de répondre, et dans deux cas sur trois rien ne passe par le serveur :
//   • Ollama       : le navigateur parle à http://localhost:11434 sur TON ordi
//   • Claude (ta clé) : le navigateur parle à api.anthropic.com, ta clé reste chez toi
//   • Claude (clé du site) : passe par /api/chat, avec la clé du propriétaire
const $ = (sel) => document.querySelector(sel);
const creer = (balise, classe, texte) => {
  const e = document.createElement(balise);
  if (classe) e.className = classe;
  if (texte != null) e.textContent = texte;
  return e;
};

const corps = document.body;
const doc = $("#doc");
const saisie = $("#saisie");
const menu = $("#menu");
const listeSessions = $("#sessions");
const choixMoteur = $("#moteur");
const moteurCodex = $("#codex-moteur");

const URL_OLLAMA = "http://localhost:11434";
// Les modèles Claude offerts. Prix par million de mots-jetons (entrée / sortie).
const MODELES_CLAUDE = [
  { id: "claude-opus-5",    nom: "Opus 5",    note: "le plus capable",                prix: "5 $ / 25 $" },
  { id: "claude-sonnet-5",  nom: "Sonnet 5",  note: "bon partout, moins cher",        prix: "2 $ / 10 $" },
  { id: "claude-haiku-4-5", nom: "Haiku 4.5", note: "le plus rapide et le moins cher", prix: "1 $ / 5 $" },
  { id: "claude-fable-5-1", nom: "Fable 5.1", note: "pour les tâches longues",        prix: "10 $ / 50 $" },
];
// Les IA gratuites qu'on propose d'installer, de la plus légère à la plus lourde.
const OLLAMA_SUGGERES = [
  ["llama3.2",    "2 Go",   "Léger et rapide. Le meilleur premier choix."],
  ["gemma3",      "3,3 Go", "Compact, répond vite, correct en français."],
  ["mistral",     "4,1 Go", "Équilibré. Bon en français, bon partout."],
  ["qwen3",       "5,2 Go", "Le plus fort pour le code et le raisonnement."],
  ["deepseek-r1", "5,2 Go", "Réfléchit avant de répondre. Plus lent, plus posé."],
];
let modelesEnLigne = [];   // rempli par l'API quand une clé est branchée
const URL_CLAUDE = "https://api.anthropic.com/v1/messages";
const MODELE_CLAUDE = "claude-sonnet-5";
const MAX_TOKENS = 8000;
const RECHERCHES_MAX = 4;
const VITESSE_MS = 10;        // un paquet de lettres aux 10 ms, comme la version bureau
const TOURS_ECRITURE = 150;   // ≈ 1,5 s pour écrire une réponse, quelle que soit sa longueur

let messages = [];
let sessionId = null;
let occupe = false;
let generation = 0;
let moteurs = [];             // [{id, nom, type, modele}]

/* ---------- Ce qui reste sur l'appareil ---------- */
const CLE_SESSIONS = "ecriture.sessions";
const CLE_CLAUDE = "ecriture.cleClaude";
const CLE_CODE = "ecriture.code";
const CLE_MOTEUR = "ecriture.moteur";

const lire = (cle) => { try { return localStorage.getItem(cle) || ""; } catch { return ""; } };
const ecrire = (cle, valeur) => {
  try { valeur ? localStorage.setItem(cle, valeur) : localStorage.removeItem(cle); }
  catch { /* navigation privée */ }
};

/* ---------- Les consignes données à l'IA ---------- */
const QUEBECOIS =
  "Tu es un vrai Québécois. Tu parles pis tu écris en français québécois familier, " +
  "comme quelqu'un d'ici qui jase avec un chum : tu tutoies, tu utilises les tournures " +
  "orales (y'a, j'suis, t'sais, c'est-tu, faque, pis, ben, là, pantoute, tantôt, astheure) " +
  "et les expressions d'ici quand ça sonne naturel (c'est l'fun, ça a pas d'allure, " +
  "lâche pas, c'est correct, mets-en). Garde ça clair et facile à lire, sans en beurrer " +
  "trop épais : pas de caricature, pas de sacres à moins que la personne en utilise. " +
  "Les termes techniques, les commandes et le code restent exacts et bien écrits. ";

function instructionsSysteme(web) {
  const aujourdhui = new Date().toISOString().slice(0, 10);
  return "Tu es l'assistant intégré à une application d'écriture. " + QUEBECOIS +
    "Écris seulement en texte brut : pas de Markdown, pas d'astérisques, " +
    "pas de dièses, pas de tableaux. Pour une liste, utilise des tirets simples. " +
    (web
      ? "Fais une recherche web dès que la question touche l'actualité, des prix, " +
        "des horaires, la météo, des personnes ou n'importe quoi qui a pu changer récemment. "
      : "Tu n'as pas accès à Internet. Si la question demande des infos récentes " +
        "(actualité, météo, prix, horaires), dis-le franchement au lieu d'inventer. ") +
    "Quand ta réponse explique un plan d'action ou des étapes à suivre, termine-la " +
    "par un bloc exactement comme celui-ci (une étape courte par ligne, moins de 12 mots) :\n" +
    "[PLAN]\n1. Première étape\n2. Deuxième étape\n[/PLAN]\n" +
    "Ajoute ce bloc seulement s'il y a un vrai plan ou des étapes. " +
    `Date d'aujourd'hui : ${aujourdhui}.`;
}

/* ---------- Les moteurs offerts ---------- */
async function modelesOllama() {
  try {
    const stop = new AbortController();
    const minuterie = setTimeout(() => stop.abort(), 1800);
    const rep = await fetch(URL_OLLAMA + "/api/tags", { signal: stop.signal });
    clearTimeout(minuterie);
    if (!rep.ok) return [];
    const data = await rep.json();
    return (data.models || []).map((m) => m.name)
      .filter((n) => !n.includes("embed")).sort();
  } catch {
    return [];   // Ollama éteint, ou il n'autorise pas ce site
  }
}

/** Demande à l'API la liste des modèles que CETTE clé peut utiliser. */
async function chargerModelesClaude() {
  const cle = lire(CLE_CLAUDE);
  if (!cle) return;
  try {
    const rep = await fetch("https://api.anthropic.com/v1/models?limit=100", {
      headers: {
        "x-api-key": cle,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true",
      },
    });
    if (!rep.ok) return;                      // clé refusée : on garde la liste d'en haut
    const data = await rep.json();
    const connus = Object.fromEntries(MODELES_CLAUDE.map((m) => [m.id, m]));
    modelesEnLigne = (data.data || []).map((m) => ({
      id: m.id,
      nom: (m.display_name || m.id).replace(/^Claude /, ""),
      note: connus[m.id]?.note || "",
      prix: connus[m.id]?.prix || "",
    }));
  } catch { /* hors ligne : tant pis */ }
}

function modelesClaude() {
  return modelesEnLigne.length ? modelesEnLigne : MODELES_CLAUDE;
}

async function construireMoteurs() {
  const installes = await modelesOllama();
  moteurs = installes.map((nom) => ({
    id: "ollama:" + nom, nom: nom.replace(/:latest$/, "") + " (gratuit, sur ton ordi)",
    type: "ollama", modele: nom,
  }));
  for (const m of modelesClaude()) {
    moteurs.push({
      id: "claude:" + m.id, type: "claude", modele: m.id,
      nom: `Claude ${m.nom} + web${m.note ? " — " + m.note : ""}`,
    });
  }

  const garde = lire(CLE_MOTEUR);
  const choisi = moteurs.some((m) => m.id === garde) ? garde
    : (installes.length ? moteurs[0].id : "claude:claude-sonnet-5");
  // Deux sélecteurs, le même choix : celui sous la boîte et celui du Codex.
  for (const select of [choixMoteur, moteurCodex]) {
    if (!select) continue;
    select.replaceChildren(...moteurs.map((m) => {
      const option = creer("option", null, m.nom);
      option.value = m.id;
      return option;
    }));
    select.value = choisi;
  }
  majAstuceMoteur();
  return installes;
}

/** Garde les deux sélecteurs d'accord, d'où que vienne le changement. */
function choisirMoteur(id) {
  ecrire(CLE_MOTEUR, id);
  if (choixMoteur) choixMoteur.value = id;
  if (moteurCodex) moteurCodex.value = id;
  majAstuceMoteur();
}

function moteurActuel() {
  return moteurs.find((m) => m.id === choixMoteur.value) || moteurs[moteurs.length - 1];
}

function majAstuceMoteur() {
  const m = moteurActuel();
  const astuce = $("#astuce-moteur");
  if (!m) return;
  if (m.type === "ollama") {
    astuce.textContent = "Gratuit. Rien ne sort de ton ordinateur.";
  } else if (lire(CLE_CLAUDE)) {
    astuce.textContent = "Ta clé, gardée ici : le navigateur appelle Claude directement.";
  } else {
    astuce.textContent = "Sans ta clé, c'est celle du site qui paie (un code peut être demandé).";
  }
}

/* ---------- Les trois transports ----------
   Chacun livre la même chose : {type:"texte"|"fin"|"erreur", …} */

async function* revelerParPaquets(texte, sources) {
  const paquet = Math.max(1, Math.ceil(texte.length / TOURS_ECRITURE));
  for (let i = 0; i < texte.length; i += paquet) {
    yield { type: "texte", t: texte.slice(i, i + paquet) };
    await new Promise((r) => setTimeout(r, VITESSE_MS));
  }
  yield { type: "fin", sources };
}

/** Ollama, sur la machine de la personne. Le serveur du site ne voit rien passer. */
async function* fluxOllama(messages, modele, systeme) {
  let rep;
  try {
    rep = await fetch(URL_OLLAMA + "/api/chat", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({
        model: modele, stream: true,
        messages: [{ role: "system", content: systeme || instructionsSysteme(false) }, ...messages],
      }),
    });
  } catch {
    yield { type: "erreur", message:
      "Ollama n'a pas répondu. Vérifie qu'il tourne, et qu'il autorise ce site " +
      "(voir Paramètres)." };
    return;
  }
  if (!rep.ok) {
    const detail = await rep.text().catch(() => "");
    yield { type: "erreur", message: rep.status === 404
      ? `Le modèle « ${modele} » n'est pas installé. Dans un terminal : ollama pull ${modele}`
      : `Ollama a renvoyé l'erreur ${rep.status}. ${detail.slice(0, 120)}` };
    return;
  }
  const lecteur = rep.body.getReader();
  const decodeur = new TextDecoder();
  let tampon = "";
  for (;;) {
    const { value, done } = await lecteur.read();
    if (done) break;
    tampon += decodeur.decode(value, { stream: true });
    const lignes = tampon.split("\n");
    tampon = lignes.pop();
    for (const ligne of lignes) {
      if (!ligne.trim()) continue;
      let objet;
      try { objet = JSON.parse(ligne); } catch { continue; }
      const bout = objet.message?.content;
      if (bout) yield { type: "texte", t: bout };
    }
  }
  yield { type: "fin", sources: [] };
}

/** Claude appelé directement par le navigateur, avec la clé de la personne. */
async function* fluxClaudeDirect(messages, cle, modele, systeme) {
  let conversation = messages;
  const morceaux = [];
  const sources = [];
  for (let tour = 0; tour < 5; tour++) {
    let rep;
    try {
      rep = await fetch(URL_CLAUDE, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-api-key": cle,
          "anthropic-version": "2023-06-01",
          "anthropic-dangerous-direct-browser-access": "true",
        },
        body: JSON.stringify({
          model: modele || MODELE_CLAUDE, max_tokens: MAX_TOKENS,
          system: systeme || instructionsSysteme(true), messages: conversation,
          tools: [{ type: "web_search_20260209", name: "web_search", max_uses: RECHERCHES_MAX }],
        }),
      });
    } catch {
      yield { type: "erreur", message:
        "Le navigateur n'a pas pu joindre Claude. Vérifie ta connexion." };
      return;
    }
    if (!rep.ok) {
      const data = await rep.json().catch(() => ({}));
      const detail = data?.error?.message || "";
      yield { type: "erreur", message:
        rep.status === 401 ? "Ta clé Claude est refusée. Change-la dans Paramètres."
        : rep.status === 429 ? "Trop de questions d'un coup. Attends un peu pis réessaie."
        : rep.status >= 500 ? "Le service est surchargé. Réessaie dans un instant."
        : `Claude a refusé la demande (${rep.status}). ${detail}` };
      return;
    }
    const data = await rep.json();
    for (const bloc of data.content || []) {
      if (bloc.type !== "text") continue;
      morceaux.push(bloc.text || "");
      for (const citation of bloc.citations || []) {
        if (citation.url && !sources.some((s) => s.url === citation.url)) {
          sources.push({ titre: citation.title || citation.url, url: citation.url });
        }
      }
    }
    // Longue recherche : l'API met la réponse sur pause, on la relance
    if (data.stop_reason === "pause_turn") {
      conversation = [...conversation, { role: "assistant", content: data.content }];
      continue;
    }
    if (data.stop_reason === "max_tokens") morceaux.push("\n\n(Réponse coupée : trop longue.)");
    break;
  }
  yield* revelerParPaquets(morceaux.join("").trim(), sources.slice(0, 5));
}

/** La clé du propriétaire, côté serveur. Un code d'accès peut être demandé. */
async function* fluxServeur(messages, modele, mode) {
  // On envoie un simple mot-clé, jamais des consignes écrites ici : sans ça,
  // n'importe qui pourrait se servir de la clé du site pour faire n'importe quoi.
  const envoi = JSON.stringify({ messages, modele, mode });
  const appeler = () => {
    const entetes = { "content-type": "application/json" };
    const code = lire(CLE_CODE);
    if (code) entetes["x-code-acces"] = code;
    return fetch("/api/chat", { method: "POST", headers: entetes, body: envoi });
  };

  let rep;
  try { rep = await appeler(); }
  catch { yield { type: "erreur", message: "Le serveur du site n'a pas répondu." }; return; }

  if (rep.status === 401) {
    const data = await rep.clone().json().catch(() => ({}));
    if (data.besoinCode) {
      const saisi = prompt("Ce site demande un code d'accès :");
      if (saisi && saisi.trim()) {
        ecrire(CLE_CODE, saisi.trim());
        try { rep = await appeler(); } catch { /* on tombera dans le !ok */ }
      }
    }
  }
  if (!rep.ok) {
    const data = await rep.json().catch(() => ({}));
    yield { type: "erreur",
            message: data.erreur || `Le serveur a répondu ${rep.status}.` };
    return;
  }

  const lecteur = rep.body.getReader();
  const decodeur = new TextDecoder();
  let tampon = "";
  for (;;) {
    const { value, done } = await lecteur.read();
    if (done) break;
    tampon += decodeur.decode(value, { stream: true });
    const morceaux = tampon.split("\n\n");
    tampon = morceaux.pop();
    for (const morceau of morceaux) {
      const ligne = morceau.trim();
      if (!ligne.startsWith("data:")) continue;
      try { yield JSON.parse(ligne.slice(5)); } catch { /* morceau incomplet */ }
    }
  }
}

function flux(moteur, messages, options = {}) {
  const { systeme, mode } = options;
  if (moteur.type === "ollama") return fluxOllama(messages, moteur.modele, systeme);
  const cle = lire(CLE_CLAUDE);
  // Ta clé si tu en as une — elle ne touche alors jamais le serveur du site.
  return cle ? fluxClaudeDirect(messages, cle, moteur.modele, systeme)
             : fluxServeur(messages, moteur.modele, mode);
}

/* ---------- Le plan et son schéma ---------- */
const MOTS_PLAN =
  /\b(plan|étapes?|etapes?|stratégie|marche à suivre|comment (faire|je|on|lancer|commencer))\b/i;

function nettoyerEtape(ligne) {
  let l = ligne.replace(/\*\*/g, "").trim();
  for (;;) {
    const propre = l.replace(/^(?:[-•*]|\d+[.)]|étape\s*\d+\s*[:\-–]?)\s*/i, "");
    if (propre === l) return l;
    l = propre;
  }
}
function raccourcir(texte, maxi = 90) {
  const phrase = texte.split(/(?<=[.!?])\s/)[0];
  return phrase.length <= maxi ? phrase : phrase.slice(0, maxi - 1).trimEnd() + "…";
}
function extrairePlan(texte, question) {
  const m = /\[PLAN\]([\s\S]*?)(\[\/PLAN\]|$)/i.exec(texte);
  if (m) {
    const etapes = m[1].split("\n").map((l) => raccourcir(nettoyerEtape(l))).filter(Boolean);
    const reste = (texte.slice(0, m.index) + texte.slice(m.index + m[0].length)).trim();
    return [reste, etapes.length >= 2 ? etapes.slice(0, 12) : []];
  }
  if (MOTS_PLAN.test(question)) {
    const items = [...texte.matchAll(/^\s*\d+[.)]\s+(.+)$/gm)].map((x) => x[1]);
    if (items.length >= 3) return [texte, items.slice(0, 12).map((i) => raccourcir(nettoyerEtape(i)))];
  }
  return [texte, []];
}

const DUREE_LIEN = 850;

function schema(etapes) {
  const bloc = creer("div", "schema");
  etapes.forEach((texte, i) => {
    if (i) {
      const lien = creer("div", "lien");
      lien.append(creer("div", "courant"), creer("div", "etincelle"));
      bloc.append(lien);
    }
    const etape = creer("div", "etape");
    etape.append(creer("div", "numero", String(i + 1)), creer("div", null, texte));
    bloc.append(etape);
  });
  requestAnimationFrame(() => animerSchema(bloc));
  return bloc;
}

function animerSchema(bloc) {
  const liens = [...bloc.querySelectorAll(".lien")];
  const etapes = [...bloc.querySelectorAll(".etape")];
  if (!liens.length) return;
  let i = 0;
  const remettre = () => {
    for (const e of etapes) e.classList.remove("allumee");
    for (const l of liens) {
      l.classList.remove("passe");
      const c = l.querySelector(".courant"), e = l.querySelector(".etincelle");
      c.style.transition = e.style.transition = "none";
      c.style.height = "0"; e.style.top = "0"; e.style.opacity = "0";
    }
    i = 0;
    etapes[0].classList.add("allumee");
  };
  const avancer = () => {
    if (!bloc.isConnected) return;
    if (i >= liens.length) {
      setTimeout(() => { remettre(); setTimeout(avancer, 500); }, 1400);
      return;
    }
    const lien = liens[i];
    const courant = lien.querySelector(".courant");
    const etincelle = lien.querySelector(".etincelle");
    courant.style.transition = `height ${DUREE_LIEN}ms linear`;
    etincelle.style.transition = `top ${DUREE_LIEN}ms linear, opacity .15s`;
    courant.style.height = "100%";
    etincelle.style.opacity = "1";
    etincelle.style.top = "100%";
    setTimeout(() => {
      lien.classList.add("passe");
      etincelle.style.opacity = "0";
      i += 1;
      etapes[i]?.classList.add("allumee");
      avancer();
    }, DUREE_LIEN + 30);
  };
  etapes[0].classList.add("allumee");
  setTimeout(avancer, 500);
}

function blocSources(sources) {
  const bloc = creer("div", "sources");
  bloc.append(creer("div", null, "Sources :"));
  for (const s of sources) {
    const ligne = creer("div");
    const a = creer("a", null, s.titre);
    a.href = s.url; a.target = "_blank"; a.rel = "noopener noreferrer";
    ligne.append(document.createTextNode("- "), a);
    bloc.append(ligne);
  }
  return bloc;
}

/* ---------- Conversations gardées dans le navigateur ---------- */
function lireSessions() {
  try { return JSON.parse(localStorage.getItem(CLE_SESSIONS)) || []; } catch { return []; }
}
function ecrireSessions(liste) {
  try { localStorage.setItem(CLE_SESSIONS, JSON.stringify(liste.slice(0, 60))); } catch {}
}
function sauverSession() {
  if (!messages.length) return;
  const liste = lireSessions().filter((s) => s.id !== sessionId);
  if (!sessionId) sessionId = String(Date.now());
  const premiere = messages.find((m) => m.role === "user")?.content || "Conversation";
  liste.unshift({ id: sessionId, titre: premiere.replace(/\s+/g, " ").slice(0, 42),
                  modifie: Date.now(), messages });
  ecrireSessions(liste);
  dessinerSessions();
}
function dessinerSessions() {
  listeSessions.replaceChildren();
  const liste = lireSessions();
  if (!liste.length) {
    listeSessions.append(creer("p", "vide", "Aucune conversation encore"));
    return;
  }
  for (const s of liste) {
    const ligne = creer("div", "session" + (s.id === sessionId ? " active" : ""));
    const nom = creer("span", null, s.titre);
    nom.onclick = () => ouvrirSession(s.id);
    const suppr = creer("button", null, "×");
    suppr.title = "Supprimer";
    suppr.onclick = (e) => {
      e.stopPropagation();
      ecrireSessions(lireSessions().filter((x) => x.id !== s.id));
      if (s.id === sessionId) nouveau(); else dessinerSessions();
    };
    ligne.append(nom, suppr);
    listeSessions.append(ligne);
  }
}
function ouvrirSession(id) {
  const s = lireSessions().find((x) => x.id === id);
  if (!s) return;
  nouveau(false);
  sessionId = s.id;
  messages = s.messages || [];
  for (const m of messages) {
    if (m.role === "user") doc.append(creer("p", "question", m.content));
    else {
      doc.append(creer("p", "reponse", m.content));
      if (m.etapes?.length) doc.append(schema(m.etapes));
      if (m.sources?.length) doc.append(blocSources(m.sources));
    }
  }
  demarrer();
  dessinerSessions();
  fermerMenu();
  doc.scrollTop = doc.scrollHeight;
}

/* ---------- Mise en page ---------- */
function mesurer() {
  // Seulement ce qui reste une fois démarré : le logo et l'invite s'effacent.
  const h = $(".rangee").offsetHeight + $(".options").offsetHeight + 8;
  const marge = parseInt(getComputedStyle(document.documentElement)
    .getPropertyValue("--marge")) || 25;
  document.documentElement.style.setProperty(
    "--descente", `${Math.round(window.innerHeight / 2 - h / 2 - marge)}px`);
  document.documentElement.style.setProperty("--bas-doc", `${h + marge + 18}px`);
}
function demarrer() { mesurer(); corps.classList.add("demarre"); }
addEventListener("resize", mesurer);

/* ---------- Envoyer une question ---------- */
/** Enlève la réflexion que certains modèles écrivent entre <think>. */
function sansReflexion(brut) {
  const t = brut.replace(/<think>[\s\S]*?<\/think>/gi, "");
  const ouvert = t.search(/<think>/i);
  return ouvert >= 0 ? t.slice(0, ouvert) : t;
}

/** Ce qu'on montre PENDANT que ça arrive : le bloc [PLAN] reste caché, il
    deviendra un schéma. Le texte final, lui, passe par extrairePlan(). */
function texteVisible(brut, fini) {
  const t = sansReflexion(brut);
  const plan = t.search(/\[PLAN/i);
  if (plan >= 0) return t.slice(0, plan).trimEnd();
  return fini ? t : t.slice(0, Math.max(0, t.length - 6));
}

async function envoyer() {
  if (occupe) return;
  const question = saisie.value.trim();
  if (!question) return;
  const moteur = moteurActuel();
  if (!moteur) return;

  const mien = ++generation;
  saisie.value = "";
  doc.append(creer("p", "question", question));
  messages.push({ role: "user", content: question });
  if (!corps.classList.contains("demarre")) demarrer();

  const nom = moteur.type === "ollama" ? moteur.modele.replace(/:latest$/, "") : "Marceau";
  const attente = creer("p", "attente", `${nom} réfléchit`);
  doc.append(attente);
  doc.scrollTop = doc.scrollHeight;
  let points = 0;
  const minuterie = setInterval(() => {
    attente.textContent = `${nom} réfléchit` + ".".repeat(++points % 4);
  }, 400);
  occupe = true;

  const envoyes = messages.map((m) => ({ role: m.role, content: m.content }));
  let para = null, curseur = null, brut = "", sources = [], erreur = null;

  const enlever = () => {
    clearInterval(minuterie);
    attente.remove();
    curseur?.remove();
  };

  try {
    for await (const ev of flux(moteur, envoyes)) {
      if (mien !== generation) { enlever(); return; }   // « Nouveau » pendant la réponse
      if (ev.type === "texte") {
        if (!para) {
          clearInterval(minuterie);
          attente.remove();
          para = creer("p", "reponse");
          curseur = creer("span", "curseur", "▌");
          doc.append(para, curseur);
        }
        brut += ev.t;
        para.textContent = texteVisible(brut, false);
        doc.scrollTop = doc.scrollHeight;
      } else if (ev.type === "fin") {
        sources = ev.sources || [];
      } else if (ev.type === "erreur") {
        erreur = ev.message;
      }
    }
  } catch (err) {
    erreur = "La réponse a été coupée avant la fin. Réessaie.";
    console.error(err);
  }
  enlever();
  if (mien !== generation) return;

  if (erreur) {
    messages.pop();
    (para || doc.appendChild(creer("p", "reponse"))).textContent = erreur;
    occupe = false;
    doc.scrollTop = doc.scrollHeight;
    return;
  }

  // On garde le bloc [PLAN] ici : c'est extrairePlan qui le transforme en schéma.
  const [texte, etapes] = extrairePlan(sansReflexion(brut).trim(), question);
  if (!para) { para = creer("p", "reponse"); doc.append(para); }
  para.textContent = texte || (etapes.length ? "Voici le plan :" : "Pas de réponse cette fois-ci.");
  if (etapes.length) doc.append(schema(etapes));
  if (sources.length) doc.append(blocSources(sources));
  messages.push({ role: "assistant", content: para.textContent, etapes, sources });
  occupe = false;
  doc.scrollTop = doc.scrollHeight;
  sauverSession();
}

/* ---------- Paramètres, dans le menu ---------- */
const CLE_GITHUB = "ecriture.tokenGithub";

function majParametres() {
  const token = lire(CLE_GITHUB);
  $("#etat-github").textContent = token
    ? `Token enregistré sur cet appareil (finit par ${token.slice(-4)})`
    : "Aucun token sur cet appareil";
  $("#etat-github").className = "etat " + (token ? "oui" : "non");
  const cle = lire(CLE_CLAUDE);
  $("#etat-cle").textContent = cle
    ? `Clé enregistrée sur cet appareil (finit par ${cle.slice(-4)})`
    : "Aucune clé sur cet appareil";
  $("#etat-cle").className = "etat " + (cle ? "oui" : "non");
  majAstuceMoteur();
}

async function majOllama() {
  const etat = $("#etat-ollama");
  const aide = $("#aide-ollama");
  const installes = await construireMoteurs();
  dessinerModelesGratuits(installes);
  if (installes.length) {
    etat.textContent = `Ollama répond ✓ — ${installes.length} modèle(s) : `
      + installes.map((n) => n.replace(/:latest$/, "")).join(", ");
    etat.className = "etat oui";
    aide.hidden = true;
  } else {
    etat.textContent = "Ollama ne répond pas depuis ce site";
    etat.className = "etat non";
    aide.hidden = false;
    $("#commande-ollama").textContent =
      `OLLAMA_ORIGINS=${location.origin} ollama serve`;
  }
}

/* ---------- Boutons ---------- */
function nouveau(refermer = true) {
  generation += 1;
  occupe = false;
  messages = [];
  sessionId = null;
  doc.replaceChildren();
  corps.classList.remove("demarre");
  saisie.value = "";
  dessinerSessions();
  if (refermer) fermerMenu();
  saisie.focus();
}

function sauvegarder() {
  if (!messages.length) { alert("Écris au moins une question avant de sauvegarder."); return; }
  const contenu = messages.map((m) => m.role === "user" ? m.content :
    m.content
    + (m.etapes?.length ? "\n" + m.etapes.map((e, i) => `${i + 1}. ${e}`).join("\n") : "")
    + (m.sources?.length ? "\nSources :\n" + m.sources.map((s) => `- ${s.titre} ${s.url}`).join("\n") : "")
  ).join("\n\n");
  const lien = creer("a");
  lien.href = URL.createObjectURL(new Blob([contenu], { type: "text/plain;charset=utf-8" }));
  lien.download = "ecriture.txt";
  lien.click();
  URL.revokeObjectURL(lien.href);
}

function ouvrirMenu() { menu.classList.add("ouvert"); dessinerSessions(); majParametres(); majOllama(); }
function fermerMenu() { menu.classList.remove("ouvert"); }
function basculerMenu() { menu.classList.contains("ouvert") ? fermerMenu() : ouvrirMenu(); }

/* ---------- Les trois modes du menu ---------- */
const pages = $("#pages");

function allerPage(nom) {
  const parametres = nom === "parametres";
  pages.classList.toggle("parametres", parametres);
  if (parametres) { majParametres(); majOllama(); majApp(); }
}

function majModes() {
  const codex = corps.classList.contains("en-codex");
  $("#nav-chat").classList.toggle("actif", !codex);
  $("#nav-codex").classList.toggle("actif", codex);
}

function ouvrirCodex() {
  fermerMenu();
  corps.classList.add("en-codex");
  majModes();
  window.Codex?.ouvrir();
}
function fermerCodex() {
  corps.classList.remove("en-codex");
  majModes();
}

function allerChat() { fermerCodex(); fermerMenu(); saisie.focus(); }

/* ---------- Les IA gratuites qu'on conseille ---------- */
function dessinerModelesGratuits(installes = []) {
  const liste = $("#modeles-gratuits");
  const dejaLa = new Set(installes.map((n) => n.replace(/:.*$/, "")));
  liste.replaceChildren(...OLLAMA_SUGGERES.map(([nom, taille, quoi]) => {
    const li = creer("li");
    const installe = dejaLa.has(nom);
    if (installe) li.className = "installe";
    const ligne = creer("div", "ligne");
    const bouton = creer("button", "bouton petit", installe ? "✓ installé" : "Copier");
    bouton.onclick = () => {
      navigator.clipboard?.writeText(`ollama pull ${nom}`);
      bouton.textContent = "copié !";
      setTimeout(() => { bouton.textContent = installe ? "✓ installé" : "Copier"; }, 1600);
    };
    ligne.append(creer("span", "nom", nom), creer("span", "taille", taille), bouton);
    li.append(ligne, creer("p", "quoi", quoi));
    return li;
  }));
}

/* ---------- L'app : s'installer, pis se tenir à jour ---------- */
const VERSION_APP = "1.3.0";
let inviteInstall = null;      // le navigateur nous prête son « Installer »
let rechargeFaite = false;

function annoncer(texte, duree = 4000) {
  const boite = $("#annonce");
  boite.textContent = texte;
  boite.hidden = false;
  clearTimeout(annoncer.minuterie);
  if (duree) annoncer.minuterie = setTimeout(() => { boite.hidden = true; }, duree);
}

function majApp() {
  const installee = matchMedia("(display-mode: standalone)").matches;
  const etat = $("#etat-app");
  etat.textContent = `Version ${VERSION_APP}`
    + (installee ? " — installée sur cet appareil" : "")
    + (navigator.onLine ? "" : " — hors ligne");
  etat.className = "etat " + (navigator.onLine ? "oui" : "non");
  $("#installer-app").hidden = !inviteInstall;
}

async function brancherServiceWorker() {
  if (!("serviceWorker" in navigator)) return null;
  // Un service worker demande une page servie en https (ou en local).
  if (location.protocol !== "https:" && location.hostname !== "localhost") return null;
  try {
    const inscription = await navigator.serviceWorker.register("/app/sw.js", { scope: "/app/" });
    inscription.addEventListener("updatefound", () => {
      const neuf = inscription.installing;
      if (!neuf) return;
      neuf.addEventListener("statechange", () => {
        // Un contrôleur existait déjà : c'est donc une vraie mise à jour, pas la pose initiale.
        if (neuf.state === "installed" && navigator.serviceWorker.controller) {
          annoncer("Nouvelle version — ça se recharge…", 0);
          neuf.postMessage("saute-la-file");
        }
      });
    });
    // On regarde s'il y a du neuf en revenant sur l'app, pis aux demi-heures.
    addEventListener("focus", () => inscription.update().catch(() => {}));
    setInterval(() => inscription.update().catch(() => {}), 30 * 60 * 1000);
    return inscription;
  } catch (e) {
    console.warn("service worker :", e);
    return null;
  }
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    // La toute première pose prend le contrôle sans qu'il y ait rien à recharger.
    if (rechargeFaite || !brancherServiceWorker.avaitUnControleur) return;
    rechargeFaite = true;
    location.reload();
  });
  brancherServiceWorker.avaitUnControleur = !!navigator.serviceWorker.controller;
}

addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();          // on garde l'invite pour notre propre bouton
  inviteInstall = e;
  $("#installer-app").hidden = false;
});
addEventListener("appinstalled", () => {
  inviteInstall = null;
  annoncer("Écriture est installée. Tu peux l'ouvrir comme n'importe quelle app.");
  majApp();
});
addEventListener("online", majApp);
addEventListener("offline", majApp);

/* ---------- Ce que le Codex emprunte ici ---------- */
window.Ecriture = {
  $, creer, lire, ecrire, flux, moteurActuel, sansReflexion, annoncer,
  CLE_GITHUB,
  QUEBECOIS,
  fermerMenu: () => fermerMenu(),
};

/* ---------- Branchements ---------- */
$("#envoyer").onclick = envoyer;
$("#nouveau").onclick = () => nouveau();
$("#nouveau-menu").onclick = () => nouveau();
$("#sauvegarder").onclick = sauvegarder;
$("#menu-bouton").onclick = basculerMenu;
choixMoteur.onchange = () => choisirMoteur(choixMoteur.value);
moteurCodex.onchange = () => choisirMoteur(moteurCodex.value);

$("#enregistrer-cle").onclick = () => {
  const champ = $("#cle-claude");
  const valeur = champ.value.trim();
  if (!valeur) { $("#mot-cle").textContent = "Colle d'abord ta clé dans la case."; return; }
  ecrire(CLE_CLAUDE, valeur);
  champ.value = "";
  $("#mot-cle").textContent = "C'est enregistré, et ça reste ici.";
  majParametres();
};
$("#supprimer-cle").onclick = () => {
  ecrire(CLE_CLAUDE, "");
  $("#mot-cle").textContent = "Clé supprimée de cet appareil.";
  majParametres();
};
$("#enregistrer-token").onclick = () => {
  const champ = $("#token-github");
  const valeur = champ.value.trim();
  if (!valeur) { $("#mot-token").textContent = "Colle d'abord ton token dans la case."; return; }
  ecrire(CLE_GITHUB, valeur);
  champ.value = "";
  $("#mot-token").textContent = "C'est enregistré, et ça reste ici.";
  majParametres();
};
$("#supprimer-token").onclick = () => {
  ecrire(CLE_GITHUB, "");
  window.Codex?.oublierDepot();
  $("#mot-token").textContent = "Token supprimé de cet appareil.";
  majParametres();
};
$("#montrer-token").onchange = (e) => {
  $("#token-github").type = e.target.checked ? "text" : "password";
};
$("#montrer-cle").onchange = (e) => {
  $("#cle-claude").type = e.target.checked ? "text" : "password";
};
$("#copier-ollama").onclick = () => {
  const commande = $("#commande-ollama").textContent;
  navigator.clipboard?.writeText(commande);
  $("#mot-cle").textContent = "Commande copiée.";
};
$("#rafraichir-ollama").onclick = majOllama;
$("#nav-chat").onclick = allerChat;
$("#nav-codex").onclick = ouvrirCodex;
$("#nav-param").onclick = () => allerPage("parametres");
$("#retour").onclick = () => allerPage("principale");
$("#codex-fermer").onclick = fermerCodex;

$("#installer-app").onclick = async () => {
  if (!inviteInstall) { annoncer("Ton navigateur ne propose pas l'installation ici."); return; }
  inviteInstall.prompt();
  const { outcome } = await inviteInstall.userChoice;
  if (outcome !== "accepted") annoncer("Correct — tu pourras l'installer plus tard.");
  inviteInstall = null;
  majApp();
};
$("#verifier-maj").onclick = async () => {
  annoncer("On regarde s'il y a du neuf…", 2500);
  const inscription = await navigator.serviceWorker?.getRegistration("/app/");
  if (!inscription) { annoncer("Les mises à jour auto marchent une fois le site en ligne."); return; }
  await inscription.update().catch(() => {});
  if (!inscription.installing && !inscription.waiting) annoncer(`Version ${VERSION_APP} — t'es à jour.`);
};

saisie.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); envoyer(); }
});
addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); sauvegarder(); }
  if (e.key === "Escape") { if (corps.classList.contains("en-codex")) fermerCodex(); else fermerMenu(); }
});
doc.addEventListener("click", fermerMenu);

/* ---------- Démarrage ---------- */
mesurer();
dessinerSessions();
majParametres();
construireMoteurs().then((installes) => {
  majAstuceMoteur();
  dessinerModelesGratuits(installes);
});
majApp();
majModes();
brancherServiceWorker();
saisie.focus();
