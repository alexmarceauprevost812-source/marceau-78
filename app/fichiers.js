/* Marceau — faire un fichier à envoyer : un PDF, une page web ou du texte.
   C'est le même moteur que l'app de bureau (ecriture.py), traduit en JavaScript. Le PDF est
   écrit à la main, avec l'Helvetica que tous les lecteurs de PDF ont déjà : rien à aller
   chercher sur Internet, ça marche même sans connexion. */
(() => {
  "use strict";

  const PDF_LARGEUR = 595, PDF_HAUTEUR = 842;   // une page A4, en points
  const PDF_MARGE = 56;                          // 2 cm de marge
  const PDF_CORPS = 11, PDF_INTERLIGNE = 15.5, PDF_TITRE = 20;

  // Largeur de chaque lettre en Helvetica (millièmes de la taille), des codes 32 à 126.
  const HELVETICA = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584];
  const HELVETICA_GRAS = [
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
    975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
    611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584];

  /** Largeur d'une lettre. « é » est large comme « e » : les accents changent rien. */
  function largeurLettre(c, table) {
    let code = c.codePointAt(0);
    if (code >= 32 && code <= 126) return table[code - 32];
    const sans = c.normalize("NFD")[0];
    code = sans ? sans.codePointAt(0) : 110;
    return code >= 32 && code <= 126 ? table[code - 32] : table[110 - 32];
  }

  function largeurTexte(texte, taille, gras = false) {
    const table = gras ? HELVETICA_GRAS : HELVETICA;
    let somme = 0;
    for (const c of texte) somme += largeurLettre(c, table);
    return somme * taille / 1000;
  }

  /** Coupe le texte pour qu'il rentre dans la largeur, sans couper les mots en deux. */
  function couperLignes(texte, taille, largeurMax, gras = false) {
    const lignes = [];
    for (const paragraphe of texte.split("\n")) {
      if (!paragraphe.trim()) { lignes.push(""); continue; }
      let ligne = "";
      for (const mot of paragraphe.split(" ")) {
        const essai = `${ligne} ${mot}`.trim();
        if (ligne && largeurTexte(essai, taille, gras) > largeurMax) {
          lignes.push(ligne);
          ligne = mot;
        } else {
          ligne = essai;
        }
        // Un mot plus long que la ligne (une longue adresse web) : on le coupe
        let lettres = Array.from(ligne);
        while (largeurTexte(ligne, taille, gras) > largeurMax && lettres.length > 1) {
          let coupe = lettres.length - 1;
          while (coupe > 1 && largeurTexte(lettres.slice(0, coupe).join(""), taille, gras) > largeurMax) coupe--;
          lignes.push(lettres.slice(0, coupe).join(""));
          lettres = lettres.slice(coupe);
          ligne = lettres.join("");
        }
      }
      lignes.push(ligne);
    }
    return lignes;
  }

  // Les lettres de Windows-1252 qui sont pas à la même place qu'en Unicode
  const WINANSI = new Map(Object.entries({
    "€": 0x80, "‚": 0x82, "ƒ": 0x83, "„": 0x84, "…": 0x85, "†": 0x86, "‡": 0x87, "ˆ": 0x88,
    "‰": 0x89, "Š": 0x8a, "‹": 0x8b, "Œ": 0x8c, "Ž": 0x8e, "‘": 0x91, "’": 0x92, "“": 0x93,
    "”": 0x94, "•": 0x95, "–": 0x96, "—": 0x97, "˜": 0x98, "™": 0x99, "š": 0x9a, "›": 0x9b,
    "œ": 0x9c, "ž": 0x9e, "Ÿ": 0x9f }));

  /** Encode le texte comme le PDF l'attend (WinAnsi), avec les parenthèses protégées. */
  function textePdf(texte) {
    const octets = [];
    for (const c of texte) {
      const code = c.codePointAt(0);
      let o;
      if (WINANSI.has(c)) o = WINANSI.get(c);
      else if (code < 0x80 || (code >= 0xa0 && code <= 0xff)) o = code;
      else o = 0x3f;                                   // « ? » : pas dans la police
      if (o === 0x5c || o === 0x28 || o === 0x29) octets.push(0x5c);   // \ ( )
      octets.push(o);
    }
    return Uint8Array.from(octets);
  }

  /** Des octets à assembler : du texte (ASCII) pis du binaire, en comptant les positions. */
  class Octets {
    constructor() { this.parts = []; this.longueur = 0; }
    ajouter(morceau) {
      const o = typeof morceau === "string" ? Uint8Array.from(morceau, (c) => c.charCodeAt(0)) : morceau;
      this.parts.push(o);
      this.longueur += o.length;
      return this;
    }
    tout() {
      const sortie = new Uint8Array(this.longueur);
      let i = 0;
      for (const p of this.parts) { sortie.set(p, i); i += p.length; }
      return sortie;
    }
  }

  const g = (n) => String(Number(n.toPrecision(6)));   // comme {taille:g} en Python
  const f1 = (n) => n.toFixed(1), f2 = (n) => n.toFixed(2);

  /** Écrit un vrai PDF : un titre, des paragraphes, des images. Retourne ses octets.
      blocs : [{sorte: "texte", valeur}, {sorte: "image", jpeg (Uint8Array), largeur, hauteur}] */
  function pdf(titre, blocs) {
    const largeurUtile = PDF_LARGEUR - 2 * PDF_MARGE;
    const pages = [];
    let page = [], y = PDF_HAUTEUR - PDF_MARGE;
    const images = [];
    const nouvellePage = () => { if (page.length) pages.push(page); page = []; y = PDF_HAUTEUR - PDF_MARGE; };
    const place = (hauteur) => { if (y - hauteur < PDF_MARGE) nouvellePage(); };

    if (titre.trim()) {
      for (const ligne of couperLignes(titre.trim(), PDF_TITRE, largeurUtile, true)) {
        place(PDF_TITRE * 1.3);
        y -= PDF_TITRE;
        page.push({ sorte: "texte", x: PDF_MARGE, y, ligne, taille: PDF_TITRE, gras: true });
        y -= PDF_TITRE * 0.3;
      }
      y -= PDF_INTERLIGNE;
    }
    for (const bloc of blocs) {
      if (bloc.sorte === "texte") {
        for (const ligne of couperLignes(bloc.valeur, PDF_CORPS, largeurUtile)) {
          place(PDF_INTERLIGNE);
          y -= PDF_INTERLIGNE;
          if (ligne) page.push({ sorte: "texte", x: PDF_MARGE, y, ligne, taille: PDF_CORPS, gras: false });
        }
      } else if (bloc.sorte === "image") {
        let largeur = Math.min(largeurUtile, bloc.largeur);
        let hauteur = bloc.hauteur * largeur / bloc.largeur;
        const maxi = PDF_HAUTEUR - 2 * PDF_MARGE;
        if (hauteur > maxi) { largeur = largeur * maxi / hauteur; hauteur = maxi; }   // une image très haute rentre quand même
        place(hauteur + 12);
        y -= hauteur + 6;
        images.push(bloc);
        page.push({ sorte: "image", x: PDF_MARGE + (largeurUtile - largeur) / 2, y, largeur, hauteur,
                    indice: images.length - 1 });
        y -= 8;
      }
    }
    if (page.length || !pages.length) pages.push(page);

    // ----- On assemble les objets du PDF -----
    const nPages = pages.length;
    const premierContenu = 5, premiereImage = premierContenu + nPages;
    const premierePage = premiereImage + images.length;
    const objets = new Map();
    const enfants = Array.from({ length: nPages }, (_, i) => `${premierePage + i} 0 R`).join(" ");
    objets.set(1, ["<< /Type /Catalog /Pages 2 0 R >>"]);
    objets.set(2, [`<< /Type /Pages /Count ${nPages} /Kids [${enfants}] >>`]);
    objets.set(3, ["<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]);
    objets.set(4, ["<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"]);
    images.forEach((im, i) => {
      objets.set(premiereImage + i, [
        `<< /Type /XObject /Subtype /Image /Width ${im.largeur} /Height ${im.hauteur}` +
        ` /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${im.jpeg.length} >>\nstream\n`,
        im.jpeg, "\nendstream"]);
    });
    pages.forEach((contenuPage, i) => {
      const flux = new Octets();
      const utilisees = [];
      contenuPage.forEach((e, k) => {
        if (k) flux.ajouter("\n");
        if (e.sorte === "texte") {
          flux.ajouter(`BT /${e.gras ? "F2" : "F1"} ${g(e.taille)} Tf ${f1(e.x)} ${f1(e.y)} Td (`)
              .ajouter(textePdf(e.ligne)).ajouter(") Tj ET");
        } else {
          const nom = `Im${e.indice}`;
          utilisees.push([nom, premiereImage + e.indice]);
          flux.ajouter(`q ${f2(e.largeur)} 0 0 ${f2(e.hauteur)} ${f2(e.x)} ${f2(e.y)} cm /${nom} Do Q`);
        }
      });
      const octets = flux.tout();
      objets.set(premierContenu + i, [`<< /Length ${octets.length} >>\nstream\n`, octets, "\nendstream"]);
      const xobjets = utilisees.length
        ? " /XObject << " + utilisees.map(([nom, num]) => `/${nom} ${num} 0 R`).join(" ") + " >>" : "";
      objets.set(premierePage + i, [
        `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${PDF_LARGEUR} ${PDF_HAUTEUR}] /Resources << /Font << /F1 3 0 R ` +
        `/F2 4 0 R >>${xobjets} >> /Contents ${premierContenu + i} 0 R >>`]);
    });

    const sortie = new Octets().ajouter("%PDF-1.4\n%").ajouter(Uint8Array.of(0xe2, 0xe3, 0xcf, 0xd3)).ajouter("\n");
    const positions = new Map();
    const numeros = [...objets.keys()].sort((a, b) => a - b);
    for (const numero of numeros) {
      positions.set(numero, sortie.longueur);
      sortie.ajouter(`${numero} 0 obj\n`);
      for (const morceau of objets.get(numero)) sortie.ajouter(morceau);
      sortie.ajouter("\nendobj\n");
    }
    const debutXref = sortie.longueur;
    const total = Math.max(...numeros) + 1;
    sortie.ajouter(`xref\n0 ${total}\n0000000000 65535 f \n`);
    for (let n = 1; n < total; n++) sortie.ajouter(`${String(positions.get(n)).padStart(10, "0")} 00000 n \n`);
    sortie.ajouter(`trailer\n<< /Size ${total} /Root 1 0 R >>\nstartxref\n${debutXref}\n%%EOF\n`);
    return sortie.tout();
  }

  const proteger = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  /** Une page web d'un seul fichier : les images sont dedans, ça s'ouvre partout. */
  function html(titre, blocs) {
    const corps = [];
    for (const bloc of blocs) {
      if (bloc.sorte === "texte") {
        for (const paragraphe of bloc.valeur.split("\n")) {
          corps.push(paragraphe.trim() ? `<p>${proteger(paragraphe)}</p>` : "");
        }
      } else if (bloc.sorte === "image") {
        corps.push(`<img src="${bloc.dataUrl}" alt="">`);
      }
    }
    return "<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n<meta charset=\"utf-8\">\n" +
      `<meta name="viewport" content="width=device-width, initial-scale=1">\n` +
      `<title>${proteger(titre) || "Document"}</title>\n` +
      "<style>\n" +
      "  body { background: #8c8c8c; color: #000000; font-family: system-ui, sans-serif;\n" +
      "         margin: 0; padding: 40px 20px; line-height: 1.6; }\n" +
      "  main { max-width: 760px; margin: 0 auto; background: #a6a6a6;\n" +
      "          padding: 40px; border-radius: 14px; }\n" +
      "  h1 { margin-top: 0; border-bottom: 3px solid #ff7a1a; padding-bottom: 12px; }\n" +
      "  img { max-width: 100%; height: auto; border-radius: 10px; margin: 18px 0;\n" +
      "        display: block; }\n" +
      "  p { margin: 0 0 14px; white-space: pre-wrap; }\n" +
      "</style>\n</head>\n<body>\n<main>\n" +
      (titre.trim() ? `<h1>${proteger(titre)}</h1>\n` : "") +
      corps.join("\n") +
      "\n</main>\n</body>\n</html>\n";
  }

  /** Du texte brut. Les images sont nommées, pas incluses : un .txt en contient pas. */
  function texte(titre, blocs) {
    const parties = [];
    if (titre.trim()) parties.push(titre.trim() + "\n" + "=".repeat(Array.from(titre.trim()).length));
    let images = 0;
    for (const bloc of blocs) {
      if (bloc.sorte === "texte") parties.push(bloc.valeur.replace(/^\n+|\n+$/g, ""));
      else parties.push(`[Image ${++images}]`);
    }
    return parties.filter(Boolean).join("\n\n") + "\n";
  }

  const api = { pdf, html, texte, couperLignes, largeurTexte, textePdf };
  if (typeof window !== "undefined") window.MarceauFichiers = api;
  if (typeof module !== "undefined") module.exports = api;       // pour les essais dans Node
})();
