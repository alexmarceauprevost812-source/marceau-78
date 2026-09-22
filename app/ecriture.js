// Écriture — version web. Même comportement que l'application de bureau.
// La clé API n'est jamais ici : c'est /api/chat, côté serveur, qui parle à Claude.
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

let messages = [];        // la conversation en cours
let sessionId = null;
let occupe = false;
let generation = 0;       // change à chaque « Nouveau » : les réponses d'avant sont ignorées

/* ---------- Conversations gardées dans le navigateur ---------- */
const CLE = "ecriture.sessions";

function lireSessions() {
  try { return JSON.parse(localStorage.getItem(CLE)) || []; } catch { return []; }
}
function ecrireSessions(liste) {
  try { localStorage.setItem(CLE, JSON.stringify(liste.slice(0, 60))); } catch { /* mode privé */ }
}
function sauverSession() {
  if (!messages.length) return;
  const liste = lireSessions().filter((s) => s.id !== sessionId);
  if (!sessionId) sessionId = String(Date.now());
  const premiere = messages.find((m) => m.role === "user")?.content || "Conversation";
  const titre = premiere.replace(/\s+/g, " ").slice(0, 42);
  liste.unshift({ id: sessionId, titre, modifie: Date.now(), messages });
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
      if (s.id === sessionId) nouveau();
      else dessinerSessions();
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

/* ---------- Mise en page : la saisie glisse vers le bas ---------- */
function mesurer() {
  // On mesure seulement ce qui reste une fois démarré (le logo et l'invite s'effacent) :
  // sinon la descente est sous-estimée et la saisie s'arrête trop haut.
  const h = $(".rangee").offsetHeight + $(".options").offsetHeight + 8;
  const marge = parseInt(getComputedStyle(document.documentElement)
    .getPropertyValue("--marge")) || 25;
  document.documentElement.style.setProperty(
    "--descente", `${Math.round(window.innerHeight / 2 - h / 2 - marge)}px`);
  document.documentElement.style.setProperty("--bas-doc", `${h + marge + 18}px`);
}
function demarrer() {
  mesurer();
  corps.classList.add("demarre");
}
addEventListener("resize", mesurer);

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

const DUREE_LIEN = 850;   // temps que le courant met à passer d'une étape à l'autre

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
    if (!bloc.isConnected) return;   // le schéma a été effacé
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
    a.href = s.url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    ligne.append(document.createTextNode("- "), a);
    bloc.append(ligne);
  }
  return bloc;
}

/* ---------- Envoyer une question ---------- */
function codeAcces() {
  try { return localStorage.getItem("ecriture.code") || ""; } catch { return ""; }
}

/** Ce qu'on montre pendant que ça arrive : on cache le bloc [PLAN] avant qu'il s'affiche. */
function texteVisible(brut, fini) {
  const i = brut.search(/\[PLAN/i);
  if (i >= 0) return brut.slice(0, i).trimEnd();
  return fini ? brut : brut.slice(0, Math.max(0, brut.length - 6));
}

async function envoyer() {
  if (occupe) return;
  const question = saisie.value.trim();
  if (!question) return;

  const mien = ++generation;
  saisie.value = "";
  doc.append(creer("p", "question", question));
  messages.push({ role: "user", content: question });
  if (!corps.classList.contains("demarre")) demarrer();

  const attente = creer("p", "attente", "Marceau réfléchit");
  doc.append(attente);
  doc.scrollTop = doc.scrollHeight;
  let points = 0;
  const minuterie = setInterval(() => {
    attente.textContent = "Marceau réfléchit" + ".".repeat(++points % 4);
  }, 400);
  occupe = true;

  const fini = (garder) => {
    clearInterval(minuterie);
    attente.remove();
    if (!garder) messages.pop();
    occupe = false;
    doc.scrollTop = doc.scrollHeight;
  };

  try {
    const entetes = { "content-type": "application/json" };
    const code = codeAcces();
    if (code) entetes["x-code-acces"] = code;
    const reponse = await fetch("/api/chat", {
      method: "POST", headers: entetes,
      body: JSON.stringify({ messages: messages.map((m) => ({ role: m.role, content: m.content })) }),
    });

    if (!reponse.ok) {
      const data = await reponse.json().catch(() => ({}));
      if (data.besoinCode) {
        const saisi = prompt("Ce site demande un code d'accès :");
        if (saisi) { try { localStorage.setItem("ecriture.code", saisi.trim()); } catch {} }
      }
      fini(false);
      doc.append(creer("p", "reponse", data.erreur || `Le serveur a répondu ${reponse.status}.`));
      doc.scrollTop = doc.scrollHeight;
      return;
    }

    clearInterval(minuterie);
    attente.remove();
    const para = creer("p", "reponse");
    const curseur = creer("span", "curseur", "▌");
    doc.append(para, curseur);

    const lecteur = reponse.body.getReader();
    const decodeur = new TextDecoder();
    let tampon = "", brut = "", sources = [], erreur = null;

    for (;;) {
      const { value, done } = await lecteur.read();
      if (done) break;
      tampon += decodeur.decode(value, { stream: true });
      const morceaux = tampon.split("\n\n");
      tampon = morceaux.pop();
      for (const morceau of morceaux) {
        const ligne = morceau.trim();
        if (!ligne.startsWith("data:")) continue;
        let evenement;
        try { evenement = JSON.parse(ligne.slice(5)); } catch { continue; }
        if (evenement.type === "texte") {
          brut += evenement.t;
          para.textContent = texteVisible(brut, false);
          doc.scrollTop = doc.scrollHeight;
        } else if (evenement.type === "fin") {
          sources = evenement.sources || [];
        } else if (evenement.type === "erreur") {
          erreur = evenement.message;
        }
      }
    }
    curseur.remove();
    if (mien !== generation) return;   // « Nouveau » a été cliqué pendant la réponse

    if (erreur) { para.textContent = erreur; fini(false); return; }

    const [texte, etapes] = extrairePlan(brut, question);
    para.textContent = texte || (etapes.length ? "Voici le plan :" : "Pas de réponse cette fois-ci.");
    if (etapes.length) doc.append(schema(etapes));
    if (sources.length) doc.append(blocSources(sources));
    messages.push({ role: "assistant", content: para.textContent, etapes, sources });
    fini(true);
    sauverSession();
  } catch (err) {
    fini(false);
    doc.append(creer("p", "reponse",
      "La connexion a été coupée avant la fin de la réponse. Réessaie."));
    console.error(err);
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
  const contenu = messages
    .map((m) => (m.role === "user" ? m.content : m.content +
      (m.etapes?.length ? "\n" + m.etapes.map((e, i) => `${i + 1}. ${e}`).join("\n") : "") +
      (m.sources?.length ? "\nSources :\n" + m.sources.map((s) => `- ${s.titre} ${s.url}`).join("\n") : "")))
    .join("\n\n");
  const lien = creer("a");
  lien.href = URL.createObjectURL(new Blob([contenu], { type: "text/plain;charset=utf-8" }));
  lien.download = "ecriture.txt";
  lien.click();
  URL.revokeObjectURL(lien.href);
}

function basculerMenu() { menu.classList.toggle("ouvert"); if (menu.classList.contains("ouvert")) dessinerSessions(); }
function fermerMenu() { menu.classList.remove("ouvert"); }

/* ---------- Branchements ---------- */
$("#envoyer").onclick = envoyer;
$("#nouveau").onclick = () => nouveau();
$("#nouveau-menu").onclick = () => nouveau();
$("#sauvegarder").onclick = sauvegarder;
$("#menu-bouton").onclick = basculerMenu;

saisie.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); envoyer(); }
});
addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); sauvegarder(); }
  if (e.key === "Escape") fermerMenu();
});
doc.addEventListener("click", () => fermerMenu());

mesurer();
dessinerSessions();
saisie.focus();
