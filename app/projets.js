// Les projets, version web : un projet garde tes conversations, tes fichiers pis tes notes au
// même endroit, pis l'IA s'en sert quand tu travailles dedans. Comme sur l'ordi, mais gardé
// dans ce navigateur (localStorage) : rien passe par le serveur du site.
(function () {
const E = window.Ecriture;
const { $, creer, annoncer } = E;

const CLE_PROJETS = "ecriture.projets";
const TEXTE_MAX = 300_000;        // caractères par fichier texte gardé dans un projet
const COTE_IMAGE = 1024;          // une image gardée dans un projet est réduite : la place est comptée
const EXT_TEXTE = /\.(txt|md|markdown|csv|tsv|json|jsonl|xml|html?|css|scss|js|mjs|cjs|ts|tsx|jsx|py|rb|php|java|kt|c|h|cpp|hpp|cs|go|rs|swift|sh|bash|zsh|ps1|bat|sql|ya?ml|toml|ini|cfg|conf|env|log|tex|srt|vtt|svg)$/i;

let projetActif = null;           // le projet dans lequel tu travailles (ou null)
let montre = null;                // le projet montré dans l'écran des projets

const maintenant = () => new Date().toISOString().slice(0, 19);
const court = (nom, maxi) => (nom.length <= maxi ? nom : nom.slice(0, maxi - 1) + "…");

/* ---------- Ce qui est gardé ---------- */
function lireProjets() {
  try { return JSON.parse(localStorage.getItem(CLE_PROJETS)) || []; } catch { return []; }
}
function ecrireProjets(liste) {
  try { localStorage.setItem(CLE_PROJETS, JSON.stringify(liste)); return true; }
  catch {
    annoncer("Plus de place dans ce navigateur : enlève des fichiers ou des images d'un projet.", 6000);
    return false;
  }
}
const lireProjet = (pid) => (pid ? lireProjets().find((p) => p.id === pid) || null : null);
function ecrireProjet(projet) {
  projet.modifie = maintenant();
  const liste = lireProjets().filter((p) => p.id !== projet.id);
  liste.unshift(projet);                      // le dernier touché en haut, comme sur l'ordi
  return ecrireProjets(liste);
}
function nouveauProjet(nom) {
  const projet = { id: "p" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6), nom,
                   description: "", cree: maintenant(), fichiers: [], notes: [] };
  return ecrireProjet(projet) ? projet : null;
}
function ajouterNote(projet, titre, texte, sorte = "texte", url = "") {
  projet.notes.push({ titre: titre.replace(/\s+/g, " ").trim().slice(0, 60) || "Sans titre",
                      texte, sorte, url, date: maintenant() });
  return ecrireProjet(projet);
}

const conversationsDuProjet = (pid) => E.lireSessions().filter((s) => s.projet === pid);

/** Met une conversation dans un projet (pid = null : la sort du projet). */
function mettreSessionDansProjet(sid, pid) {
  const liste = E.lireSessions();
  const s = liste.find((x) => x.id === sid);
  if (!s) return;
  if (pid) s.projet = pid; else delete s.projet;
  E.ecrireSessions(liste);
  if (sid === E.session()) mettreActif(pid);
  E.dessinerSessions();
}

/** Devine si ce que tu gardes est un lien, du code ou du texte. */
function sorteDuTexte(texte) {
  const propre = texte.trim();
  if (/^(?:https?:\/\/|www\.)\S+$/.test(propre)) return "lien";
  const signes = ["def ", "class ", "function ", "import ", "const ", "return ", "{", "};", "</", "SELECT "];
  if (signes.filter((x) => propre.includes(x)).length >= 2 || (propre.match(/\n {4}/g) || []).length >= 2) return "code";
  return "texte";
}

/** Ce que l'IA sait du projet : ses instructions, ses fichiers texte pis ses notes. */
function contexte(pid, budget) {
  const projet = lireProjet(pid);
  if (!projet) return "";
  const parties = [`Tu travailles dans le projet « ${projet.nom} ».`];
  if (projet.description?.trim()) parties.push("Instructions du projet : " + projet.description.trim());
  let reste = budget;
  for (const f of projet.fichiers || []) {
    if (f.sorte === "texte") {
      const bloc = `--- Fichier du projet : ${f.nom} ---\n` + f.texte;
      if (bloc.length <= reste) { parties.push(bloc); reste -= bloc.length; continue; }
      parties.push(`(Le fichier ${f.nom} est trop long pour être inclus au complet.)`);
    } else {
      parties.push(`(Le projet contient aussi le fichier ${f.nom}.)`);
    }
  }
  const notes = (projet.notes || []).map((n) => `- ${n.titre} (${n.sorte || "texte"}) : ${(n.url || n.texte).slice(0, 1500)}`);
  if (notes.length) {
    const bloc = "Notes sauvegardées dans le projet :\n" + notes.join("\n");
    parties.push(bloc.slice(0, Math.max(reste, 500)));
  }
  return parties.join("\n\n");
}

/* ---------- Le projet dans lequel tu travailles ---------- */
function actif() {
  if (projetActif && !lireProjet(projetActif)) projetActif = null;   // effacé entre-temps
  return projetActif;
}
function mettreActif(pid) {
  projetActif = lireProjet(pid) ? pid : null;
  majBouton();
}
/** Choisi sous la boîte : la conversation en cours va dans le projet, pis l'IA connaît
    ses instructions, ses fichiers pis ses notes dès ta prochaine question. */
function choisirDepuisChat(pid) {
  const p = lireProjet(pid);
  if (!p) return;
  mettreActif(pid);
  if (E.messages().length) E.sauverSession();
  annoncer(`Tu travailles dans le projet « ${p.nom} » : l'IA connaît ses instructions, ses fichiers pis ses notes.`, 5000);
  E.focus();
}
function travaillerDans(pid) {        // une conversation neuve dans le projet
  fermerEcran();
  mettreActif(pid);
  E.nouveau();
}
function sortir() {                   // comme le × de l'ordi : une conversation neuve, hors projet
  mettreActif(null);
  E.nouveau();
}
function demanderNouveau() {
  const nom = prompt("Nom du projet :");
  return nom && nom.trim() ? nouveauProjet(nom.trim()) : null;
}

/** « Garder dans le projet » sous une réponse : elle devient une note du projet
    (pis l'app du Studio, s'il y en a une, avec son code au complet). */
function lienGarder(titre, texte, app) {
  const lien = creer("button", "garder", "Garder dans le projet");
  lien.type = "button";
  lien.onclick = () => {
    const p = lireProjet(actif());
    if (!p) { annoncer("Choisis d'abord un projet avec le bouton « Projet » sous la boîte."); return; }
    p.notes.push({ titre: titre.replace(/\s+/g, " ").trim().slice(0, 60) || "Réponse", texte,
                   sorte: "texte", url: "", date: maintenant() });
    if (app) p.notes.push({ titre: app.titre.slice(0, 55) + ".html", texte: app.html, sorte: "code", url: "",
                            date: maintenant() });
    if (ecrireProjet(p)) lien.replaceWith(creer("p", "sources garde", `Gardé dans « ${p.nom} »`));
  };
  return lien;
}

/* ---------- Le bouton « Projet ▾ » sous la boîte ---------- */
const bouton = $("#bouton-projet");
const menuProjet = $("#menu-projet");
let selectionGardee = "";         // ce que t'avais surligné dans la conversation, avant le clic

/** Du texte surligné dans une réponse (du code, un lien…) devient une note du projet. */
function garderSelection(pid, selection) {
  const p = lireProjet(pid);
  if (!p) return;
  const sorte = sorteDuTexte(selection);
  if (ajouterNote(p, selection, selection, sorte, sorte === "lien" ? selection.trim() : "")) {
    annoncer(`Gardé dans le projet « ${p.nom} ».`);
  }
}

function majBouton() {
  const p = lireProjet(projetActif);
  // Juste le nom se coupe (sur un téléphone) : le « ▾ » reste là, on voit que c'est un menu
  bouton.replaceChildren("📁 ", creer("span", "nom", p ? court(p.nom, 22) : "Projet"), " ▾");
  bouton.classList.toggle("dans-projet", !!p);
  bouton.title = p ? `Tu travailles dans le projet « ${p.nom} »` : "Travailler dans un projet";
}

function itemMenu(texte, action) {
  const b = creer("button", null, texte);
  b.type = "button";
  b.setAttribute("role", "menuitem");
  b.onclick = () => { fermerMenuProjet(); action(); };
  return b;
}

function ouvrirMenuProjet() {
  const p = lireProjet(actif());
  const selection = selectionGardee || E.selectionDansDoc();
  selectionGardee = "";
  const items = [];
  if (p && selection) items.push(itemMenu("Garder la sélection dans le projet", () => garderSelection(p.id, selection)));
  if (p) {
    items.push(itemMenu(`Voir le projet « ${court(p.nom, 28)} »`, () => ouvrirEcran(p.id)),
               itemMenu("Ajouter des fichiers au projet…", () => choisirFichiers(p.id)),
               itemMenu("Sortir du projet", sortir), creer("hr"));
  }
  const autres = lireProjets().filter((x) => x.id !== projetActif);
  if (autres.length) {
    items.push(creer("p", "menu-titre", p ? "Changer de projet :" : "Travailler dans un projet :"));
    for (const x of autres.slice(0, 15)) {
      const b = itemMenu(court(x.nom, 34), () => choisirDepuisChat(x.id));
      b.classList.add("menu-projet-nom");
      items.push(b);
    }
    items.push(creer("hr"));
  }
  items.push(itemMenu("Nouveau projet…", () => { const x = demanderNouveau(); if (x) choisirDepuisChat(x.id); }),
             itemMenu("Tous mes projets", () => ouvrirEcran()));
  menuProjet.replaceChildren(...items);
  menuProjet.hidden = false;
  bouton.setAttribute("aria-expanded", "true");
  // Au-dessus du bouton, sans dépasser de l'écran
  const rangee = menuProjet.offsetParent;
  const maxi = (rangee ? rangee.clientWidth : innerWidth) - menuProjet.offsetWidth;
  menuProjet.style.left = Math.max(0, Math.min(bouton.offsetLeft, maxi)) + "px";
}
function fermerMenuProjet() {
  menuProjet.hidden = true;
  bouton.setAttribute("aria-expanded", "false");
}

/* ---------- Ajouter des fichiers (texte, ou une image réduite) ---------- */
const choixFichiers = creer("input", "cache-fichier");
choixFichiers.type = "file";
choixFichiers.multiple = true;
choixFichiers.tabIndex = -1;
choixFichiers.setAttribute("aria-hidden", "true");
document.body.append(choixFichiers);
let fichiersPour = null;

function choisirFichiers(pid) {
  fichiersPour = pid;
  choixFichiers.click();
}
choixFichiers.onchange = async () => {
  const fichiers = [...choixFichiers.files];
  choixFichiers.value = "";
  const p = lireProjet(fichiersPour);
  if (!p || !fichiers.length) return;
  let ajoutes = 0;
  const refuses = [];
  for (const f of fichiers) {
    try {
      if (f.type.startsWith("image/") && !/svg/.test(f.type)) {
        const r = E.reduire(await E.chargerImage(f), COTE_IMAGE, 0.8);
        p.fichiers.push({ nom: f.name, sorte: "image", image: r.url, l: r.l, h: r.h, ajoute: maintenant() });
      } else {
        const texte = await f.text();
        // Un fichier binaire (PDF, Word…) lu comme du texte : plein de caractères de contrôle
        const bizarre = (texte.slice(0, 4000).match(/[\u0000-\u0008\u000e-\u001f�]/g) || []).length;
        if (!EXT_TEXTE.test(f.name) && (bizarre > 8 || !texte.trim())) { refuses.push(f.name); continue; }
        p.fichiers.push({ nom: f.name, sorte: "texte", texte: texte.slice(0, TEXTE_MAX), ajoute: maintenant() });
      }
      ajoutes += 1;
    } catch {
      refuses.push(f.name);
    }
  }
  if (ajoutes && !ecrireProjet(p)) return;
  if (montre === p.id) remplir();
  const s = ajoutes > 1 ? "s" : "";
  annoncer((ajoutes ? `${ajoutes} fichier${s} ajouté${s} au projet « ${p.nom} ».` : "")
    + (refuses.length ? ` Pas lu (ni texte ni image) : ${refuses.join(", ")}.` : ""), 6000);
};

/* ---------- L'écran des projets ---------- */
const ecran = $("#projets");
const liste = $("#projets-liste");
const detail = $("#projets-detail");

function ouvrirEcran(pid) {
  E.fermerMenu();
  E.fermerCodex();
  fermerMenuProjet();
  document.body.classList.add("en-projets");
  ecran.hidden = false;
  E.majModes();
  const cible = pid || (montre && lireProjet(montre) ? montre : null) || actif();
  dessinerListe();
  if (cible) montrer(cible);
  else { montre = null; ecran.classList.remove("detail-ouvert"); videDetail(); }
}
function fermerEcran() {
  document.body.classList.remove("en-projets");
  ecran.hidden = true;
  E.majModes();
}
const ecranOuvert = () => !ecran.hidden;

function dessinerListe() {
  const projets = lireProjets();
  liste.replaceChildren(...projets.map((p) => {
    const b = creer("button", "projets-ligne" + (p.id === montre ? " choisi" : ""));
    b.type = "button";
    b.append(creer("span", "nom", p.nom));
    if (p.id === projetActif) b.append(creer("span", "actif", "actif"));
    b.onclick = () => montrer(p.id);
    return b;
  }));
  if (!projets.length) liste.append(creer("p", "vide", "Aucun projet encore"));
}

function videDetail() {
  detail.replaceChildren(creer("p", "projets-vide",
    "Un projet garde tes conversations, tes fichiers pis tes notes au même endroit. "
    + "L'IA s'en sert quand tu travailles dedans.\n\nClique « + Nouveau projet » pour commencer."));
}

function montrer(pid) {
  const p = lireProjet(pid);
  if (!p) { montre = null; videDetail(); dessinerListe(); return; }
  montre = pid;
  ecran.classList.add("detail-ouvert");      // sur un téléphone : le détail prend l'écran
  dessinerListe();
  remplir();
}

function bout(texte, action, classe = "bouton petit") {
  const b = creer("button", classe, texte);
  b.type = "button";
  b.onclick = action;
  return b;
}

/** Le détail du projet montré : ses instructions, pis ses trois colonnes. */
function remplir() {
  const p = lireProjet(montre);
  if (!p) { videDetail(); return; }
  const tete = creer("div", "projet-tete");
  const retour = bout("‹ Projets", () => { ecran.classList.remove("detail-ouvert"); }, "bouton petit projets-retour");
  const titre = creer("h2", "projet-nom", p.nom);
  const actions = creer("div", "projet-actions");
  actions.append(
    bout(p.id === projetActif ? "Nouvelle conversation dans ce projet" : "Travailler dans ce projet",
         () => travaillerDans(p.id), "bouton"),
    bout("Renommer", () => {
      const nom = prompt("Nouveau nom du projet :", p.nom);
      if (!nom || !nom.trim()) return;
      p.nom = nom.trim();
      if (ecrireProjet(p)) { remplir(); dessinerListe(); majBouton(); }
    }),
    bout("Supprimer", () => {
      if (!confirm(`Supprimer le projet « ${p.nom} », ses fichiers pis ses notes?\n`
                   + "Les conversations restent dans le menu.")) return;
      for (const s of conversationsDuProjet(p.id)) mettreSessionDansProjet(s.id, null);
      ecrireProjets(lireProjets().filter((x) => x.id !== p.id));
      if (projetActif === p.id) mettreActif(null);
      montre = null;
      ecran.classList.remove("detail-ouvert");
      dessinerListe();
      videDetail();
    }));
  tete.append(retour, titre, actions);

  const etiquette = creer("label", "etiquette", "Instructions pour l'IA (ce qu'elle doit savoir sur ce projet)");
  // Ce que t'étais en train d'écrire (pas encore enregistré) reste là quand l'écran se redessine
  const avant = $("#projet-instructions");
  const brouillon = avant && avant.dataset.projet === p.id ? avant.value : null;
  const instructions = creer("textarea", "champ projet-instructions");
  instructions.id = "projet-instructions";
  instructions.dataset.projet = p.id;
  etiquette.htmlFor = instructions.id;
  instructions.rows = 4;
  instructions.value = brouillon ?? (p.description || "");
  const etat = creer("span", "projet-etat");
  const rang = creer("div", "rang-boutons");
  rang.append(bout("Enregistrer les instructions", () => {
    const q = lireProjet(p.id);
    if (!q) return;
    q.description = instructions.value.trim();
    if (ecrireProjet(q)) etat.textContent = "Instructions enregistrées.";
  }), etat);

  const conversations = conversationsDuProjet(p.id);
  const colonnes = creer("div", "projet-colonnes");
  colonnes.append(
    colonne("Conversations", conversations.map((s) => ({
      nom: s.titre || "Sans titre",
      ouvrir: () => { fermerEcran(); E.ouvrirSession(s.id); },
      retirer: () => { mettreSessionDansProjet(s.id, null); remplir(); },
    })), [bout("+ Ajouter", (e) => menuConversations(e.currentTarget, p.id, conversations))]),
    colonne("Fichiers", p.fichiers.map((f, i) => ({
      nom: f.nom,
      ouvrir: () => voirFichier(f),
      retirer: () => { const q = lireProjet(p.id); q.fichiers.splice(i, 1); ecrireProjet(q); remplir(); },
    })), [bout("+ Fichier", () => choisirFichiers(p.id))]),
    colonne("Notes", p.notes.map((n, i) => ({
      nom: (n.sorte && n.sorte !== "texte" ? `[${n.sorte}] ` : "") + n.titre,
      ouvrir: () => ouvrirNote(p.id, i),
      retirer: () => { const q = lireProjet(p.id); q.notes.splice(i, 1); ecrireProjet(q); remplir(); },
    })), [bout("+ Lien", () => ajouterLien(p.id)), bout("+ Note", () => editeurNote(p.id, null))]));

  detail.replaceChildren(tete, etiquette, instructions, rang, colonnes);
}

function colonne(titre, elements, boutons) {
  const bloc = creer("section", "projet-colonne");
  const tete = creer("header");
  tete.append(creer("h3", null, `${titre} (${elements.length})`), ...boutons);
  const ul = creer("ul");
  for (const el of elements) {
    const li = creer("li");
    const nom = bout(el.nom, el.ouvrir, "projet-element");
    nom.title = "Ouvrir";
    const x = bout("×", el.retirer, "retirer");
    x.title = "Retirer";
    x.setAttribute("aria-label", `Retirer ${el.nom}`);
    li.append(nom, x);
    ul.append(li);
  }
  if (!elements.length) ul.append(creer("li", "vide", "Rien encore"));
  bloc.append(tete, ul);
  return bloc;
}

/** « + Ajouter » : les autres conversations, pour en mettre une dans le projet. */
function menuConversations(ancre, pid, dedans) {
  const ids = new Set(dedans.map((s) => s.id));
  const autres = E.lireSessions().filter((s) => !ids.has(s.id));
  const menu = $("#menu-conversations");
  menu.replaceChildren(...(autres.length ? autres.slice(0, 30).map((s) => itemMenuSimple(
    s.titre || "Sans titre", () => { mettreSessionDansProjet(s.id, pid); remplir(); }))
    : [creer("p", "menu-titre", "Aucune autre conversation")]));
  const r = ancre.getBoundingClientRect();
  menu.hidden = false;
  menu.style.top = Math.min(r.bottom + 4, innerHeight - menu.offsetHeight - 8) + "px";
  menu.style.left = Math.max(8, Math.min(r.left, innerWidth - menu.offsetWidth - 8)) + "px";
}
function itemMenuSimple(texte, action) {
  const b = creer("button", null, texte);
  b.type = "button";
  b.onclick = () => { $("#menu-conversations").hidden = true; action(); };
  return b;
}

function ajouterLien(pid) {
  const url = prompt("Adresse du lien (https://…) :");
  if (!url || !url.trim()) return;
  const propre = url.trim();
  const defaut = propre.replace(/^https?:\/\/(www\.)?/, "").split("/")[0];
  const nom = prompt("Nom du lien :", defaut);
  const p = lireProjet(pid);
  if (p && ajouterNote(p, (nom || defaut).trim(), propre, "lien", propre)) remplir();
}

/* ---------- Les fenêtres : lire, écrire ---------- */
const fenetre = $("#fenetre-projet");
function ouvrirFenetre(titre, contenu, boutons) {
  $("#fenetre-projet-titre").textContent = titre;
  $("#fenetre-projet-corps").replaceChildren(...contenu);
  $("#fenetre-projet-boutons").replaceChildren(...boutons);
  fenetre.hidden = false;
}
function fermerFenetre() { fenetre.hidden = true; }

function voirFichier(f) {
  if (f.sorte === "image") {
    const img = creer("img", "projet-image");
    img.src = f.image;
    img.alt = f.nom;
    ouvrirFenetre(f.nom, [img], [bout("Fermer", fermerFenetre)]);
    return;
  }
  const pre = creer("pre", "projet-code", f.texte);
  ouvrirFenetre(f.nom, [pre], [bout("Copier", () => copier(f.texte)), bout("Fermer", fermerFenetre)]);
}

function copier(texte) {
  navigator.clipboard?.writeText(texte).then(() => annoncer("Copié."), () => annoncer("Copie refusée par le navigateur."));
}

function ouvrirNote(pid, i) {
  const n = lireProjet(pid)?.notes[i];
  if (!n) return;
  if (n.sorte === "lien") {
    const url = n.url || n.texte.trim();
    window.open(/^https?:\/\//i.test(url) ? url : "https://" + url, "_blank", "noopener");
    return;
  }
  if (n.sorte === "code") {
    ouvrirFenetre(n.titre, [creer("pre", "projet-code", n.texte)],
                  [bout("Copier", () => copier(n.texte)), bout("Modifier", () => editeurNote(pid, i)),
                   bout("Fermer", fermerFenetre)]);
    return;
  }
  editeurNote(pid, i);
}

/** Écrire une note, ou en modifier une (i = null : une nouvelle). */
function editeurNote(pid, i) {
  const note = i == null ? null : lireProjet(pid)?.notes[i];
  const lTitre = creer("label", "etiquette", "Titre");
  const titre = creer("input", "champ");
  titre.id = "note-titre";
  lTitre.htmlFor = titre.id;
  titre.value = note?.titre || "";
  const lTexte = creer("label", "etiquette", "Ce que tu gardes");
  const texte = creer("textarea", "champ note-texte");
  texte.id = "note-texte";
  lTexte.htmlFor = texte.id;
  texte.rows = 10;
  texte.value = note?.texte || "";
  ouvrirFenetre(note ? "Note du projet" : "Nouvelle note", [lTitre, titre, lTexte, texte], [
    bout("Enregistrer", () => {
      const p = lireProjet(pid);
      if (!p) return;
      const t = titre.value.trim() || "Sans titre";
      const contenu = texte.value;
      if (note && p.notes[i]) Object.assign(p.notes[i], { titre: t, texte: contenu, sorte: sorteDuTexte(contenu) });
      else p.notes.push({ titre: t, texte: contenu, sorte: sorteDuTexte(contenu), url: "", date: maintenant() });
      if (ecrireProjet(p)) { fermerFenetre(); if (montre === pid) remplir(); }
    }, "bouton"),
    bout("Annuler", fermerFenetre)]);
  titre.focus();
}

/* ---------- Branchements ---------- */
bouton.addEventListener("pointerdown", () => { selectionGardee = E.selectionDansDoc(); });
bouton.onclick = (e) => {
  e.stopPropagation();
  menuProjet.hidden ? ouvrirMenuProjet() : fermerMenuProjet();
};
document.addEventListener("click", (e) => {
  if (!menuProjet.hidden && !menuProjet.contains(e.target) && !bouton.contains(e.target)) fermerMenuProjet();
  const menuConv = $("#menu-conversations");
  if (!menuConv.hidden && !menuConv.contains(e.target) && !e.target.closest(".projet-colonne header")) menuConv.hidden = true;
});
$("#projets-nouveau").onclick = () => { const p = demanderNouveau(); if (p) montrer(p.id); };
$("#projets-fermer").onclick = () => { fermerEcran(); E.focus(); };
$("#fenetre-projet-fermer").onclick = fermerFenetre;
majBouton();

/** Échap : ce qui est ouvert se ferme, un à la fois. Rend vrai s'il a fermé quelque chose. */
function echap() {
  if (!fenetre.hidden) { fermerFenetre(); return true; }
  if (!$("#menu-conversations").hidden) { $("#menu-conversations").hidden = true; return true; }
  if (!menuProjet.hidden) { fermerMenuProjet(); bouton.focus(); return true; }
  if (ecranOuvert()) { fermerEcran(); E.focus(); return true; }
  return false;
}

window.Projets = {
  actif, mettreActif, contexte, lienGarder, ouvrirEcran, fermerEcran, ecranOuvert, echap,
  // pour les essais
  lireProjets, lireProjet, nouveauProjet, sorteDuTexte, choisirDepuisChat, mettreSessionDansProjet,
};
})();
