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

/* ---------- L'assistant ---------- */
function consignes() {
  const ouvert = actif ? `Le fichier ouvert est ${actif.chemin}.` : "Aucun fichier n'est ouvert.";
  return "Tu es l'assistant Codex d'une application d'écriture. " + window.Ecriture.QUEBECOIS +
    "Tu aides à lire, écrire pis corriger du code. " +
    `Le projet est ${depot || "(aucun)"}, branche ${branche || "(aucune)"}. ${ouvert} ` +
    "Quand tu donnes du code, mets-le dans un bloc ```langage. " +
    "Quand tu réécris un fichier au complet, commence le bloc par une ligne " +
    "« // fichier: chemin/du/fichier » pour que je sache où le mettre.";
}

function contexte() {
  const bouts = [];
  if (actif) bouts.push(`Fichier ouvert — ${actif.chemin} :\n\`\`\`\n${$("#codex-code").value.slice(0, 24000)}\n\`\`\``);
  else if (arbre.length) bouts.push("Fichiers du projet :\n" + arbre.slice(0, FICHIERS_SCAN).map((f) => "- " + f.chemin).join("\n"));
  return bouts.join("\n\n");
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

async function envoyer() {
  if (occupe) return;
  const saisie = $("#codex-saisie");
  const question = saisie.value.trim();
  if (!question) return;
  saisie.value = "";
  occupe = true;
  jase.push({ role: "user", content: question });
  dessinerJase();

  const boite = $("#codex-chat");
  const para = creer("div", "codex-reponse");
  para.textContent = "…";
  boite.append(para);
  boite.scrollTop = boite.scrollHeight;

  const pourLIA = jase.map((m) => ({ role: m.role, content: m.content }));
  const bout = contexte();
  if (bout) pourLIA[pourLIA.length - 1] = {
    role: "user", content: `${bout}\n\nMa question : ${question}`,
  };

  let brut = "";
  try {
    for await (const bloc of flux(moteurActuel(), pourLIA, { systeme: consignes(), mode: "codex" })) {
      if (bloc.type === "texte") { brut += bloc.t; para.textContent = sansReflexion(brut); }
      else if (bloc.type === "erreur") { para.textContent = bloc.message; brut = ""; break; }
      boite.scrollTop = boite.scrollHeight;
    }
  } catch (err) { para.textContent = "Erreur : " + err.message; brut = ""; }

  const reponse = sansReflexion(brut).trim();
  if (reponse) {
    jase.push({ role: "assistant", content: reponse });
    para.textContent = reponse;
    ajouterBoutonsCode(para, reponse);
  }
  occupe = false;
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
