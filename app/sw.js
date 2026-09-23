// Le service worker : c'est lui qui fait que l'app s'installe, marche sans
// Internet, pis se met à jour toute seule.
//
// Le principe : on essaie TOUJOURS le réseau en premier pour les fichiers de
// l'app. Comme ça, dès que tu es en ligne, tu as la dernière version — pas
// besoin d'attendre qu'un cache expire. Le cache sert juste de filet quand la
// connexion n'est pas là.
const VERSION = "2.7.1";
const CACHE = `ecriture-${VERSION}`;

// Ce qu'on garde d'avance pour que l'app démarre même hors ligne.
const ESSENTIELS = [
  "/app/",
  "/app/index.html",
  "/app/ecriture.css",
  "/app/ecriture.js",
  "/app/codex.js",
  "/app/manifest.webmanifest",
  "/logo_marceau.png",
  "/logo_64.png",
  "/logo_192.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      // addAll() abandonne tout si un seul fichier manque : on y va un par un.
      .then((cache) => Promise.all(ESSENTIELS.map((u) => cache.add(u).catch(() => {}))))
      .then(() => self.skipWaiting())   // la nouvelle version prend la place tout de suite
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((noms) => Promise.all(noms.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

/** Réseau d'abord, cache si ça ne répond pas. C'est ça qui met l'app à jour. */
async function reseauDabord(requete) {
  try {
    // « cache: reload » est essentiel : sans ça, le navigateur nous ressert sa
    // propre copie gardée en mémoire et on ne verrait jamais la nouvelle version.
    const reponse = await fetch(requete, { cache: "reload" });
    if (reponse && reponse.ok && reponse.type === "basic") {
      const copie = reponse.clone();
      caches.open(CACHE).then((c) => c.put(requete, copie)).catch(() => {});
    }
    return reponse;
  } catch (err) {
    const garde = await caches.match(requete);
    if (garde) return garde;
    // Une page demandée hors ligne : on ressort l'app au lieu d'une erreur du navigateur.
    if (requete.mode === "navigate") {
      const accueil = await caches.match("/app/index.html");
      if (accueil) return accueil;
    }
    throw err;
  }
}

self.addEventListener("fetch", (e) => {
  const requete = e.request;
  if (requete.method !== "GET") return;                 // les questions à l'IA passent tout droit
  const url = new URL(requete.url);
  if (url.origin !== self.location.origin) return;      // Ollama, Claude : jamais touchés
  if (url.pathname.startsWith("/api/")) return;
  e.respondWith(reseauDabord(requete));
});

// La page peut demander « regarde s'il y a du neuf » sans attendre un rechargement.
self.addEventListener("message", (e) => {
  if (e.data === "saute-la-file") self.skipWaiting();
});
