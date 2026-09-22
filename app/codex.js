// Le Codex, version web : ouvrir un projet GitHub, lire le code, le modifier,
// pis le renvoyer — avec l'IA à côté.
//
// Rien de tout ça ne passe par le serveur du site. Le navigateur appelle
// api.github.com directement (GitHub autorise ça : Access-Control-Allow-Origin: *),
// faque ton token reste sur ton appareil, exactement comme ta clé Claude.
(function () {
const { $, creer, lire, ecrire, flux, moteurActuel, sansReflexion, annoncer, CLE_GITHUB } = window.Ecriture;

const CLE_DEPOT = "ecriture.codexDepot";
const OCTETS_MAX = 400 * 1024;     // au-delà, c'est pas du code qu'on lit dans un onglet
const FICHIERS_SCAN = 40;          // ce qu'on donne à l'IA quand elle scanne le projet

let depot = "";                    // « monde/mon-projet »
let branche = "";
let arbre = [];                    // [{chemin, sha, taille}]
let onglets = [];                  // [{chemin, contenu, origine, sha}]
let actif = null;
let jase = [];                     // la conversation avec l'assistant
let occupe = false;

/* ---------- Parler à GitHub ---------- */
async function github(methode, chemin, corps) {
  const token = lire(CLE_GITHUB);
  if (!token) throw new Error("PAS_DE_TOKEN");
  const rep = await fetch("https://api.github.com" + chemin, {
    method: methode,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      ...(corps ? { "Content-Type": "application/json" } : {}),
    },
    body: corps ? JSON.stringify(corps) : undefined,
  });
  if (!rep.ok) {
    const detail = await rep.json().catch(() => ({}));
    const e = new Error(detail.message || rep.statusText);
    e.code = rep.status;
    throw e;
  }
  const texte = await rep.text();
  return texte ? JSON.parse(texte) : null;
}

function direErreur(err) {
  if (err.message === "PAS_DE_TOKEN")
    return "Il faut ton token GitHub. Menu ☰ → Paramètres → Token GitHub.";
  if (err.code === 401) return "Token GitHub refusé ou expiré. Refais-en un dans Paramètres.";
  if (err.code === 403) return "GitHub refuse : il manque la permission « Contents : Read and write », "
                             + "ou t'as tapé trop de requêtes d'un coup.";
  if (err.code === 404) return "Introuvable — ou ton token n'a pas accès à ce projet-là.";
  if (err.code === 409 || err.code === 422)
    return "Le fichier a changé sur GitHub depuis que tu l'as ouvert. Rouvre-le avant d'enregistrer.";
  return "GitHub : " + err.message;
}

/** Du base64 de GitHub vers du texte, en passant par UTF-8 comme il faut. */
function versTexte(base64) {
  const binaire = atob(base64.replace(/\s/g, ""));
  const octets = Uint8Array.from(binaire, (c) => c.charCodeAt(0));
  return new TextDecoder("utf-8", { fatal: true }).decode(octets).replace(/\r\n/g, "\n");
}

function versBase64(texte) {
  const octets = new TextEncoder().encode(texte);
  let binaire = "";
  for (const o of octets) binaire += String.fromCharCode(o);
  return btoa(binaire);
}

/* ---------- L'état affiché en haut ---------- */
function etat(message, sorte = "") {
  const e = $("#codex-etat");
  e.textContent = message;
  e.className = "codex-etat " + sorte;
}

/* ---------- Choisir un projet ---------- */
async function choisirProjet() {
  etat("On va chercher tes projets…");
  let depots;
  try {
    depots = await github("GET", "/user/repos?per_page=100&sort=updated");
  } catch (err) { etat(direErreur(err), "mal"); return; }
  if (!depots.length) { etat("Ton token ne voit aucun projet.", "mal"); return; }

  const liste = $("#codex-projets");
  liste.replaceChildren(...depots.map((d) => {
    const li = creer("li");
    const b = creer("button", "codex-projet-ligne");
    b.append(creer("span", "nom", d.full_name),
             creer("span", "det", `${d.private ? "privé" : "public"} · ${d.default_branch}`));
    b.onclick = () => { $("#codex-choix").hidden = true; ouvrirDepot(d.full_name, d.default_branch); };
    li.append(b);
    return li;
  }));
  $("#codex-choix").hidden = false;
  $("#codex-filtre").value = "";
  $("#codex-filtre").focus();
  etat(`${depots.length} projets`);
}

function filtrerProjets() {
  const mot = $("#codex-filtre").value.toLowerCase();
  for (const li of $("#codex-projets").children) {
    li.hidden = !li.textContent.toLowerCase().includes(mot);
  }
}

/* ---------- Ouvrir un projet ---------- */
async function ouvrirDepot(nom, sonBranche) {
  etat(`Ouverture de ${nom}…`);
  try {
    const data = await github(
      "GET", `/repos/${nom}/git/trees/${encodeURIComponent(sonBranche)}?recursive=1`);
    depot = nom;
    branche = sonBranche;
    arbre = (data.tree || [])
      .filter((n) => n.type === "blob" && n.size <= OCTETS_MAX)
      .map((n) => ({ chemin: n.path, sha: n.sha, taille: n.size }))
      .sort((a, b) => a.chemin.localeCompare(b.chemin, "fr"));
    onglets = []; actif = null; jase = [];
    ecrire(CLE_DEPOT, JSON.stringify({ depot, branche }));
    $("#codex-nom").textContent = `${nom} · ${sonBranche}`;
    dessinerArbre();
    dessinerOnglets();
    dessinerJase();
    etat(`${arbre.length} fichiers${data.truncated ? " (projet trop gros : liste coupée par GitHub)" : ""}`,
         data.truncated ? "mal" : "");
  } catch (err) { etat(direErreur(err), "mal"); }
}

function dessinerArbre() {
  const mot = $("#codex-cherche").value.trim().toLowerCase();
  const vus = mot ? arbre.filter((f) => f.chemin.toLowerCase().includes(mot)) : arbre;
  const liste = $("#codex-arbre");
  if (!vus.length) {
    liste.replaceChildren(creer("p", "vide", arbre.length ? "Rien qui ressemble à ça." : "Ouvre un projet."));
    return;
  }
  liste.replaceChildren(...vus.slice(0, 600).map((f) => {
    const b = creer("button", "codex-fichier", f.chemin);
    b.title = `${f.chemin} — ${Math.max(1, Math.round(f.taille / 1024))} Ko`;
    if (actif && actif.chemin === f.chemin) b.classList.add("actif");
    b.onclick = () => ouvrirFichier(f);
    return b;
  }));
}

/* ---------- Ouvrir un fichier ---------- */
async function ouvrirFichier(f) {
  const deja = onglets.find((o) => o.chemin === f.chemin);
  if (deja) { activer(deja); return; }
  etat(`Lecture de ${f.chemin}…`);
  try {
    const data = await github("GET", `/repos/${depot}/git/blobs/${f.sha}`);
    let contenu;
    try { contenu = versTexte(data.content); }
    catch { etat(`${f.chemin} n'est pas du texte.`, "mal"); return; }
    const onglet = { chemin: f.chemin, contenu, origine: contenu, sha: f.sha };
    onglets.push(onglet);
    activer(onglet);
    etat(`${f.chemin} ouvert`);
  } catch (err) { etat(direErreur(err), "mal"); }
}

function activer(onglet) {
  if (actif) actif.contenu = $("#codex-code").value;
  actif = onglet;
  $("#codex-code").value = onglet ? onglet.contenu : "";
  $("#codex-code").disabled = !onglet;
  dessinerOnglets();
  dessinerArbre();
}

function modifie(o) { return o.contenu !== o.origine; }

function dessinerOnglets() {
  if (actif) actif.contenu = $("#codex-code").value;
  const barre = $("#codex-onglets");
  barre.replaceChildren(...onglets.map((o) => {
    const t = creer("div", "codex-onglet" + (o === actif ? " actif" : ""));
    const nom = creer("button", "titre", o.chemin.split("/").pop() + (modifie(o) ? " •" : ""));
    nom.title = o.chemin;
    nom.onclick = () => activer(o);
    const x = creer("button", "x", "×");
    x.title = "Fermer";
    x.onclick = (e) => { e.stopPropagation(); fermerOnglet(o); };
    t.append(nom, x);
    return t;
  }));
  const n = onglets.filter(modifie).length;
  $("#codex-enregistrer").disabled = !n;
  $("#codex-enregistrer").textContent = n ? `Enregistrer (${n})` : "Enregistrer";
}

function fermerOnglet(o) {
  if (modifie(o) && !confirm(`« ${o.chemin} » n'est pas enregistré. Le fermer pareil ?`)) return;
  onglets = onglets.filter((x) => x !== o);
  if (actif === o) activer(onglets[onglets.length - 1] || null);
  else dessinerOnglets();
}

/* ---------- Renvoyer sur GitHub ---------- */
async function enregistrer() {
  if (actif) actif.contenu = $("#codex-code").value;
  const aFaire = onglets.filter(modifie);
  if (!aFaire.length) return;
  const message = prompt("Message du commit :",
    aFaire.length === 1 ? `Modifie ${aFaire[0].chemin}` : `Modifie ${aFaire.length} fichiers`);
  if (message === null) return;
  etat(`Envoi de ${aFaire.length} fichier(s)…`);
  let faits = 0;
  for (const o of aFaire) {
    try {
      const rep = await github("PUT", `/repos/${depot}/contents/${o.chemin.split("/").map(encodeURIComponent).join("/")}`, {
        message: message || `Modifie ${o.chemin}`,
        content: versBase64(o.contenu),
        sha: o.sha,
        branch: branche,
      });
      o.sha = rep.content.sha;
      o.origine = o.contenu;
      faits += 1;
    } catch (err) { etat(`${o.chemin} : ${direErreur(err)}`, "mal"); dessinerOnglets(); return; }
  }
  dessinerOnglets();
  etat(`${faits} fichier(s) enregistré(s) sur GitHub ✓`, "bien");
}

/* ---------- Nouveau fichier ---------- */
function nouveauFichier() {
  if (!depot) { etat("Ouvre d'abord un projet.", "mal"); return; }
  const chemin = prompt("Chemin du nouveau fichier (ex. : src/allo.js)");
  if (!chemin) return;
  if (onglets.some((o) => o.chemin === chemin)) { etat("Ce fichier est déjà ouvert."); return; }
  const onglet = { chemin: chemin.replace(/^\/+/, ""), contenu: "", origine: null, sha: undefined };
  onglets.push(onglet);
  activer(onglet);
  etat(`${onglet.chemin} — nouveau, pas encore sur GitHub`);
}

/* ---------- Les outils que l'IA peut se servir elle-même ---------- */
// Chaque outil est décrit une fois, pis traduit dans les deux formats :
// celui de Claude et celui d'Ollama (qui suit le style OpenAI).
const cacheBlobs = new Map();      // sha -> texte, pour pas relire deux fois

async function lireParChemin(chemin) {
  const ouvert = onglets.find((o) => o.chemin === chemin);
  if (ouvert) return ouvert === actif ? $("#codex-code").value : ouvert.contenu;
  const f = arbre.find((x) => x.chemin === chemin);
  if (!f) throw new Error(`Pas de fichier « ${chemin} » dans ce projet.`);
  if (cacheBlobs.has(f.sha)) return cacheBlobs.get(f.sha);
  const data = await github("GET", `/repos/${depot}/git/blobs/${f.sha}`);
  let texte;
  try { texte = versTexte(data.content); }
  catch { throw new Error(`« ${chemin} » n'est pas du texte.`); }
  cacheBlobs.set(f.sha, texte);
  return texte;
}

/** Met un contenu dans un onglet (sans toucher à GitHub : c'est toi qui commites). */
function poserDansOnglet(chemin, contenu) {
  let o = onglets.find((x) => x.chemin === chemin);
  if (!o) {
    const f = arbre.find((x) => x.chemin === chemin);
    o = { chemin, contenu: "", origine: f ? null : null, sha: f ? f.sha : undefined };
    if (f) o.origine = cacheBlobs.get(f.sha) ?? "";
    onglets.push(o);
  }
  o.contenu = contenu;
  if (o === actif) $("#codex-code").value = contenu;
  activer(o);
  return o;
}

const OUTILS = [
  {
    nom: "lister_fichiers",
    quoi: "Donne la liste des fichiers du projet. Sers-toi de « motif » pour filtrer "
        + "(ex. : « .js » ou « src/ »). Commence toujours par ça pour voir le projet.",
    params: { motif: { type: "string", description: "Filtre optionnel sur le chemin." } },
    requis: [],
    async faire({ motif }) {
      const vus = motif ? arbre.filter((f) => f.chemin.toLowerCase().includes(motif.toLowerCase())) : arbre;
      if (!vus.length) return "Aucun fichier qui correspond.";
      return `${vus.length} fichier(s) :\n` + vus.slice(0, 400)
        .map((f) => `${f.chemin} (${Math.max(1, Math.round(f.taille / 1024))} Ko)`).join("\n");
    },
    dire: ({ motif }) => motif ? `liste les fichiers « ${motif} »` : "liste le projet",
  },
  {
    nom: "lire_fichier",
    quoi: "Lit un fichier du projet au complet.",
    params: { chemin: { type: "string", description: "Le chemin exact, tel que listé." } },
    requis: ["chemin"],
    async faire({ chemin }) {
      const texte = await lireParChemin(chemin);
      return `--- ${chemin} ---\n${texte.slice(0, 60000)}`;
    },
    dire: ({ chemin }) => `lit ${chemin}`,
  },
  {
    nom: "chercher",
    quoi: "Cherche un bout de texte dans tout le projet et dit dans quels fichiers "
        + "et à quelles lignes il apparaît. C'est comme ça que tu scannes un gros projet "
        + "sans tout lire.",
    params: {
      texte: { type: "string", description: "Ce qu'on cherche." },
      motif: { type: "string", description: "Filtre optionnel sur les chemins de fichiers." },
    },
    requis: ["texte"],
    async faire({ texte, motif }) {
      const cibles = (motif ? arbre.filter((f) => f.chemin.includes(motif)) : arbre)
        .filter((f) => f.taille < 200 * 1024).slice(0, 120);
      const bas = texte.toLowerCase();
      const trouves = [];
      for (const f of cibles) {
        let contenu;
        try { contenu = await lireParChemin(f.chemin); } catch { continue; }
        contenu.split("\n").forEach((ligne, i) => {
          if (ligne.toLowerCase().includes(bas) && trouves.length < 60) {
            trouves.push(`${f.chemin}:${i + 1}: ${ligne.trim().slice(0, 200)}`);
          }
        });
      }
      return trouves.length
        ? `${trouves.length} résultat(s) :\n` + trouves.join("\n")
        : `Rien trouvé pour « ${texte} » dans ${cibles.length} fichier(s).`;
    },
    dire: ({ texte }) => `cherche « ${texte} »`,
  },
  {
    nom: "ecrire_fichier",
    quoi: "Écrit un fichier au complet. Ça ouvre le fichier dans un onglet marqué "
        + "modifié — c'est la personne qui clique Enregistrer pour l'envoyer sur GitHub. "
        + "Sers-toi de remplacer_dans_fichier pour une petite correction.",
    params: {
      chemin: { type: "string", description: "Le chemin du fichier." },
      contenu: { type: "string", description: "Tout le nouveau contenu." },
    },
    requis: ["chemin", "contenu"],
    async faire({ chemin, contenu }) {
      if (arbre.some((f) => f.chemin === chemin)) await lireParChemin(chemin);  // pour garder l'original
      poserDansOnglet(chemin, contenu);
      return `${chemin} écrit dans un onglet (${contenu.split("\n").length} lignes). `
           + "Pas encore sur GitHub : la personne doit cliquer Enregistrer.";
    },
    dire: ({ chemin }) => `écrit ${chemin}`,
  },
  {
    nom: "remplacer_dans_fichier",
    quoi: "Remplace un bout de texte exact dans un fichier. Le texte cherché doit "
        + "apparaître une seule fois. C'est la meilleure façon de corriger quelque chose.",
    params: {
      chemin: { type: "string", description: "Le chemin du fichier." },
      avant: { type: "string", description: "Le texte exact à remplacer, tel quel." },
      apres: { type: "string", description: "Ce qui le remplace." },
    },
    requis: ["chemin", "avant", "apres"],
    async faire({ chemin, avant, apres }) {
      const texte = await lireParChemin(chemin);
      const combien = texte.split(avant).length - 1;
      if (combien === 0) return `Ce texte-là n'est pas dans ${chemin}. Relis le fichier avant.`;
      if (combien > 1) return `Ce texte apparaît ${combien} fois dans ${chemin}. `
                            + "Donne-m'en un plus long, qui n'apparaît qu'une fois.";
      poserDansOnglet(chemin, texte.replace(avant, apres));
      return `${chemin} corrigé. Pas encore sur GitHub : la personne doit cliquer Enregistrer.`;
    },
    dire: ({ chemin }) => `corrige ${chemin}`,
  },
];

const parNom = Object.fromEntries(OUTILS.map((o) => [o.nom, o]));

function schema(o) {
  return { type: "object", properties: o.params, required: o.requis };
}
const outilsClaude = () => OUTILS.map((o) => ({ name: o.nom, description: o.quoi, input_schema: schema(o) }));
const outilsOllama = () => OUTILS.map((o) => ({
  type: "function", function: { name: o.nom, description: o.quoi, parameters: schema(o) },
}));

async function executer(nom, args) {
  const outil = parNom[nom];
  if (!outil) return `Outil inconnu : ${nom}.`;
  try { return await outil.faire(args || {}); }
  catch (err) { return "Erreur : " + (err.message === "PAS_DE_TOKEN" ? direErreur(err) : err.message); }
}

/* ---------- L'assistant ---------- */
function consignes() {
  const ouvert = actif ? `Le fichier ouvert est ${actif.chemin}.` : "Aucun fichier n'est ouvert.";
  return "Tu es l'assistant Codex : tu travailles dans un vrai projet GitHub. "
    + window.Ecriture.QUEBECOIS
    + `Le projet est ${depot || "(aucun)"}, branche ${branche || "(aucune)"}. ${ouvert} `
    + "T'as des outils : lister_fichiers pour voir le projet, chercher pour trouver du "
    + "texte partout sans tout lire, lire_fichier pour en ouvrir un, ecrire_fichier pour "
    + "en réécrire un au complet, et remplacer_dans_fichier pour une correction précise. "
    + "Sers-t'en au lieu de deviner : avant de changer quelque chose, lis-le. "
    + "Pour une petite correction, prends remplacer_dans_fichier plutôt que de réécrire "
    + "tout le fichier. "
    + "Tes changements vont dans des onglets, pas directement sur GitHub : c'est la "
    + "personne qui clique Enregistrer. Dis-le-lui quand t'as fini. "
    + "Écris en texte brut, sans Markdown, sauf les blocs de code en ```.";
}

function dessinerJase() {
  const boite = $("#codex-chat");
  if (!jase.length) {
    boite.replaceChildren(creer("p", "attente",
      "Demande-moi d'expliquer un fichier, d'écrire du code ou de corriger un bogue. "
      + "J'vois le fichier que t'as ouvert."));
    return;
  }
  boite.replaceChildren(...jase.map((m) => {
    const p = creer("div", m.role === "user" ? "codex-question" : "codex-reponse");
    p.textContent = m.content;
    return p;
  }));
  boite.scrollTop = boite.scrollHeight;
}

const TOURS_AGENT = 14;        // assez pour scanner un projet, pas assez pour tourner en rond

/* ---------- Appeler l'IA, avec les outils ---------- */
async function appelerClaude(conversation, modele) {
  const cle = lire("ecriture.cleClaude");
  const entetes = { "content-type": "application/json" };
  let url, corps;
  if (cle) {
    url = "https://api.anthropic.com/v1/messages";
    Object.assign(entetes, {
      "x-api-key": cle, "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    });
    corps = { model: modele, max_tokens: 8000, system: consignes(),
              messages: conversation, tools: outilsClaude() };
  } else {
    // Pas de clé à toi : c'est le serveur du site qui paie, donc c'est lui qui
    // écrit les consignes. On ne lui envoie que la conversation et les outils.
    url = "/api/codex";
    const code = lire("ecriture.code");
    if (code) entetes["x-code-acces"] = code;
    corps = { messages: conversation, modele, outils: outilsClaude() };
  }
  const rep = await fetch(url, { method: "POST", headers: entetes, body: JSON.stringify(corps) });
  const data = await rep.json().catch(() => ({}));
  if (!rep.ok) throw new Error(data?.error?.message || data?.erreur || `Erreur ${rep.status}`);
  return data;
}

async function appelerOllama(conversation, modele) {
  const rep = await fetch("http://localhost:11434/api/chat", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({
      model: modele, stream: false, tools: outilsOllama(),
      messages: [{ role: "system", content: consignes() }, ...conversation],
    }),
  });
  if (!rep.ok) throw new Error(`Ollama a répondu ${rep.status}.`);
  return rep.json();
}

/* ---------- La boucle : l'IA se sert de ses outils jusqu'à avoir fini ---------- */
async function envoyer() {
  if (occupe) return;
  const saisie = $("#codex-saisie");
  const question = saisie.value.trim();
  if (!question) return;
  if (!depot) { etat("Ouvre d'abord un projet.", "mal"); return; }

  saisie.value = "";
  occupe = true;
  $("#codex-envoyer").disabled = true;
  jase.push({ role: "user", content: question });
  dessinerJase();

  const boite = $("#codex-chat");
  const travaux = creer("div", "codex-travaux");
  boite.append(travaux);
  const para = creer("div", "codex-reponse", "…");
  boite.append(para);
  const versLeBas = () => { boite.scrollTop = boite.scrollHeight; };
  versLeBas();

  const geste = (texte, sorte = "") => {
    const l = creer("div", "codex-geste " + sorte, texte);
    travaux.append(l);
    versLeBas();
    return l;
  };

  const moteur = moteurActuel();
  const ollama = moteur.type === "ollama";
  // Le contexte de départ : la liste des fichiers, pour qu'il sache où il est.
  const depart = `Projet ${depot} (branche ${branche}), ${arbre.length} fichiers.\n`
    + arbre.slice(0, 120).map((f) => "- " + f.chemin).join("\n")
    + (arbre.length > 120 ? `\n… et ${arbre.length - 120} autres (sers-toi de lister_fichiers).` : "")
    + (actif ? `\n\nLe fichier ouvert est ${actif.chemin}.` : "")
    + `\n\nMa demande : ${question}`;

  let conversation = ollama
    ? [{ role: "user", content: depart }]
    : [{ role: "user", content: depart }];
  let reponse = "";

  try {
    for (let tour = 0; tour < TOURS_AGENT; tour++) {
      para.textContent = tour ? "…" : "Je regarde le projet…";
      const data = ollama
        ? await appelerOllama(conversation, moteur.modele)
        : await appelerClaude(conversation, moteur.modele);

      /* ----- Ollama : style OpenAI ----- */
      if (ollama) {
        const m = data.message || {};
        const texte = sansReflexion(m.content || "").trim();
        const appels = m.tool_calls || [];
        if (texte) reponse = texte;
        if (!appels.length) break;
        conversation.push({ role: "assistant", content: m.content || "", tool_calls: appels });
        for (const a of appels) {
          const nom = a.function?.name;
          let args = a.function?.arguments;
          if (typeof args === "string") { try { args = JSON.parse(args); } catch { args = {}; } }
          const ligne = geste("⟳ " + (parNom[nom]?.dire(args || {}) ?? nom));
          const resultat = await executer(nom, args);
          ligne.textContent = "✓ " + (parNom[nom]?.dire(args || {}) ?? nom);
          conversation.push({ role: "tool", content: String(resultat).slice(0, 40000) });
        }
        continue;
      }

      /* ----- Claude : blocs tool_use ----- */
      const blocs = data.content || [];
      const texte = blocs.filter((b) => b.type === "text").map((b) => b.text).join("").trim();
      if (texte) { reponse = texte; para.textContent = texte; versLeBas(); }
      const appels = blocs.filter((b) => b.type === "tool_use");
      if (!appels.length) break;

      conversation.push({ role: "assistant", content: blocs });
      const resultats = [];
      for (const a of appels) {
        const ligne = geste("⟳ " + (parNom[a.name]?.dire(a.input || {}) ?? a.name));
        const resultat = await executer(a.name, a.input);
        ligne.textContent = "✓ " + (parNom[a.name]?.dire(a.input || {}) ?? a.name);
        resultats.push({ type: "tool_result", tool_use_id: a.id,
                         content: String(resultat).slice(0, 40000) });
      }
      conversation.push({ role: "user", content: resultats });
      if (tour === TOURS_AGENT - 1) {
        geste("J'arrête ici : ça fait pas mal de tours. Redemande si c'est pas fini.", "mal");
      }
    }
  } catch (err) {
    para.textContent = "Erreur : " + err.message;
    if (ollama) geste("Ce modèle-là ne sait peut-être pas se servir d'outils. "
                    + "Essaie qwen3, llama3.2 ou mistral — ou Claude.", "mal");
    occupe = false;
    $("#codex-envoyer").disabled = false;
    return;
  }

  if (reponse) {
    jase.push({ role: "assistant", content: reponse });
    para.textContent = reponse;
    ajouterBoutonsCode(para, reponse);
  } else {
    para.textContent = "C'est fait.";
  }
  dessinerOnglets();
  versLeBas();
  occupe = false;
  $("#codex-envoyer").disabled = false;
}

/** Chaque bloc de code de la réponse reçoit un bouton pour l'appliquer. */
function ajouterBoutonsCode(para, reponse) {
  const blocs = [...reponse.matchAll(/```[^\n]*\n([\s\S]*?)```/g)].map((m) => m[1]);
  if (!blocs.length || !actif) return;
  const rang = creer("div", "codex-actions");
  blocs.forEach((code, i) => {
    const b = creer("button", "bouton petit", blocs.length > 1 ? `Copier le bloc ${i + 1}` : "Copier le code");
    b.onclick = () => { navigator.clipboard?.writeText(code); b.textContent = "copié !"; };
    rang.append(b);
  });
  const remplacer = creer("button", "bouton petit", `Remplacer ${actif.chemin.split("/").pop()}`);
  remplacer.onclick = () => {
    if (!confirm(`Remplacer tout le contenu de ${actif.chemin} par le premier bloc de code ?`)) return;
    $("#codex-code").value = blocs[0];
    dessinerOnglets();
    etat("Remplacé. Clique Enregistrer pour l'envoyer sur GitHub.", "bien");
  };
  rang.append(remplacer);
  para.append(rang);
}

/* ---------- Ouverture ---------- */
function ouvrir() {
  if (!lire(CLE_GITHUB)) {
    etat("Il faut ton token GitHub — menu ☰ → Paramètres.", "mal");
    $("#codex-arbre").replaceChildren(creer("p", "vide",
      "Le Codex a besoin d'un token GitHub pour voir tes projets. "
      + "Il reste sur cet appareil : le navigateur parle à GitHub directement."));
    return;
  }
  if (!depot) {
    const garde = lire(CLE_DEPOT);
    if (garde) {
      try { const g = JSON.parse(garde); ouvrirDepot(g.depot, g.branche); return; } catch {}
    }
    choisirProjet();
  }
}

/* ---------- Branchements ---------- */
$("#codex-projet").onclick = choisirProjet;
$("#codex-choix-fermer").onclick = () => { $("#codex-choix").hidden = true; };
$("#codex-filtre").oninput = filtrerProjets;
$("#codex-cherche").oninput = dessinerArbre;
$("#codex-enregistrer").onclick = enregistrer;
$("#codex-nouveau").onclick = nouveauFichier;
$("#codex-envoyer").onclick = envoyer;
$("#codex-code").addEventListener("input", dessinerOnglets);
$("#codex-code").addEventListener("keydown", (e) => {
  if (e.key === "Tab") {           // du code, ça s'indente avec Tab, pas ça saute ailleurs
    e.preventDefault();
    const t = e.target, d = t.selectionStart;
    t.value = t.value.slice(0, d) + "  " + t.value.slice(t.selectionEnd);
    t.selectionStart = t.selectionEnd = d + 2;
  }
  if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); enregistrer(); }
});
$("#codex-saisie").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); envoyer(); }
});

window.Codex = { ouvrir, oublierDepot: () => { depot = ""; ecrire(CLE_DEPOT, ""); } };
})();
