# marceau-78

**Écriture** — un espace d'écriture minimaliste en Python/Tkinter, doublé d'un
assistant qui répond aux questions.

Page de présentation : <https://marceau-78.vercel.app>

Plusieurs agents au choix, dans un menu sous la boîte de saisie :

- **les modèles locaux d'Ollama** — gratuits, hors ligne, sur ta machine
- **les modèles Claude** — payants, mais avec la recherche web : Opus 5,
  Sonnet 5, Haiku 4.5, Fable 5.1

La zone de saisie démarre au centre, sous le logo. Dès la première question,
elle glisse vers le bas et la conversation apparaît au-dessus, dans un document
que l'on peut relire, modifier et sauvegarder.

Thème gris mat, texte noir, boutons orange à coins ronds.

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `ecriture.py` | toute l'application |
| `logo.png` | le logo MARCEAU en 512 px, icône de fenêtre |
| `logo_64.png` | le même en 64 px, pour la barre des tâches |
| `logo_accueil.png` | le logo découpé en rond, affiché sur l'accueil |
| `logo_marceau.png` | le logo de l'agent, en 320 px, qui glisse du centre vers la gauche |
| `logo_192.png`, `logo_maskable.png` | les icônes de l'app installable |
| `index.html` | la page de présentation publiée sur Vercel |
| `app/` | la version web d'Écriture (`/app` sur le site) |
| `app/sw.js` | le service worker : l'app hors ligne et ses mises à jour |
| `app/manifest.webmanifest` | ce qui rend la version web installable |
| `api/chat.js` | la fonction serverless qui parle à Claude, clé côté serveur |
| `package.json` | la seule dépendance : le SDK Anthropic, installé par Vercel |
| `vercel.json` | fait télécharger `ecriture.py`, et empêche le cache de figer `/app` |
| `captures/` | les deux captures d'écran utilisées par la page |

Les trois PNG sont cherchés à côté du script. S'ils manquent, l'application
démarre quand même, sans icône ni logo.

## Lancer

```bash
python3 ecriture.py
```

Aucune dépendance à installer : seule la bibliothèque standard est utilisée
(les appels réseau passent par `urllib`). Tkinter est généralement livré avec
Python ; sur Debian/Ubuntu, s'il manque :

```bash
sudo apt install python3-tk
```

## Les IA gratuites, avec Ollama

Ollama fait tourner des modèles sur ta machine, sans compte ni carte de crédit.
Installe-le depuis <https://ollama.com>, puis, dans un terminal :

```bash
ollama serve            # démarre le service
ollama pull mistral     # télécharge un modèle (une seule fois)
```

Quelques modèles qui marchent bien : `mistral`, `llama3.2`, `qwen3`, `gemma3`,
`deepseek-r1`. Les gros modèles répondent mieux mais demandent plus de mémoire.

L'application lit la liste des modèles installés à chaque ouverture du menu :
inutile de la relancer après un `ollama pull`. Si Ollama ne tourne pas, seul
Claude reste proposé.

Ces modèles n'ont **pas** accès à Internet. On leur demande de le dire plutôt
que d'inventer quand la question porte sur quelque chose de récent.

## Claude et la recherche web

Ce moteur appelle l'API Claude, qui est payante. Il faut une clé (`sk-ant-…`)
obtenue sur <https://console.anthropic.com>.

Branche-la dans **☰ → Paramètres**. Elle est enregistrée dans
`~/.config/ecriture/cle_api`, en clair, avec les droits `600` (lisible
uniquement par ton compte). Si tu poses une question sans clé, l'application
ouvre la page Paramètres toute seule et garde ta question dans la boîte.

Si aucun fichier n'existe, la variable d'environnement `ANTHROPIC_API_KEY` est
utilisée à la place :

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Les sources citées s'affichent sous la réponse ; un clic ouvre le lien dans le
navigateur.

## Utilisation

| Action | Raccourci |
| --- | --- |
| Envoyer la question | `Entrée` (ou le bouton **Envoyer**) |
| Saut de ligne dans la saisie | `Maj` + `Entrée` |
| Sauvegarder la conversation | `Ctrl` + `S` (ou le bouton **Sauvegarder**) |
| Changer d'IA | le menu orange sous la boîte |
| Repartir de zéro | bouton **Nouveau** |
| Ouvrir le menu des conversations | bouton **☰** |
| Brancher la clé API ou le token | **☰** puis **Paramètres** |

L'assistant garde le fil de la conversation, quel que soit le moteur — on peut
commencer avec un modèle local et passer à Claude en cours de route.

La réponse s'écrit à l'écran lettre par lettre, derrière un curseur orange,
en une seconde et demie quelle que soit sa longueur : plus c'est long, plus les
lettres arrivent par paquets. Par défaut l'assistant répond en français
québécois familier.

Pendant qu'une réponse arrive, « … réfléchit » s'anime et la saisie est mise en
pause. L'appel tourne dans un fil séparé pour que la fenêtre reste réactive.
**Nouveau** efface la conversation, ramène le logo et la saisie au centre, et
ignore la réponse en cours si elle arrive après coup.

Le document du haut est éditable : on peut y corriger le texte avant de le
sauvegarder en `.txt`.

## Le logo de l'agent

Au démarrage, le logo Marceau trône au-dessus de la boîte d'écriture. À la
première question, il glisse vers la gauche en rapetissant, et se réinstalle
en haut du document ; il revient au centre avec **Nouveau**. Un petit avatar
du même logo précède chaque réponse.

Pillow (`pip install pillow`) rend le redimensionnement plus doux, mais reste
facultatif : sans lui, Tkinter divise la taille par un nombre entier.

## Le menu de gauche

Le bouton **☰** en haut à gauche ouvre un panneau à deux pages qui glissent
l'une sur l'autre. La première ne montre que **trois modes**, de la même
grosseur, chacun avec son pictogramme :

| | Mode | Ce que ça fait |
| --- | --- | --- |
| ✎ | **Chat** | écrire et jaser avec l'IA |
| ▤ | **Codex** | ouvrir un projet GitHub et travailler le code |
| ⚙ | **Paramètres** | fait glisser la seconde page |

Le mode affiché est en orange. En dessous des trois boutons, il ne reste que
tes conversations : elles sont enregistrées toutes seules dans
`~/.local/share/ecriture/sessions`, une par fichier JSON, avec leurs schémas et
leurs sources. Un clic en rouvre une, un clic droit la supprime.

**Tout ce qui se règle ou s'écrit est dans Paramètres** — le menu, lui, reste
court. La version web a exactement le même menu.

## Paramètres

La page **Paramètres** du menu regroupe tout ce qui se règle : les deux
branchements, les IA gratuites, et les mises à jour. Elle défile, pour tenir
sur un écran de portable.

| | Pour quoi | Où la prendre |
| --- | --- | --- |
| Clé API Claude | l'IA payante avec recherche web | <https://console.anthropic.com> |
| Token GitHub | le Codex | *Settings → Developer settings → Fine-grained tokens*, permission **Contents : Read and write** |

Chaque ligne dit si c'est branché et d'où ça vient (fichier sur l'ordi, ou
variable d'environnement), **sans jamais réafficher la valeur** — seulement les
quatre derniers caractères. Quand une clé manque, l'application ouvre cette page
toute seule au lieu de refuser sans rien dire, et ta question reste dans la
boîte.

Les deux sont écrites dans `~/.config/ecriture`, en mode `600` : lisibles
uniquement par ton compte. Rien ne part ailleurs.

## Le choix de l'agent

Le menu sous la boîte de saisie liste, dans l'ordre :

1. les **modèles Ollama** installés, gratuits ;
2. les **modèles Claude**, payants — Opus 5 (le plus capable), Sonnet 5 (bon
   partout, moins cher), Haiku 4.5 (le plus rapide) et Fable 5.1 (les tâches
   longues), chacun avec ce qu'il vaut ;
3. **Ajouter des IA gratuites…**, pour en installer d'autres.

Dès qu'une clé Claude est branchée, la liste des Claude est remplacée en
arrière-plan par celle que l'API renvoie vraiment pour cette clé : tu ne vois
que ce à quoi tu as accès. Sans clé, c'est la liste écrite dans
`MODELES_CLAUDE`, en haut du fichier.

## Les IA gratuites

Si le menu ne propose aucun modèle gratuit, c'est qu'Ollama ne
tourne pas sur cette machine — le menu le dit maintenant en toutes lettres,
au lieu de laisser Claude tout seul sans explication.

**Ajouter des IA gratuites…**, au bas de ce menu (ou depuis Paramètres), ouvre
une fenêtre qui :

- dit si Ollama répond, et quels modèles sont déjà installés ;
- s'il ne répond pas, donne la marche à suivre — un bouton vers
  <https://ollama.com/download>, puis `ollama serve` à copier ;
- liste cinq modèles à choisir, du plus léger au plus lourd, avec leur taille et
  ce qu'ils valent. **Copier** met la commande `ollama pull …` dans le
  presse-papier ; ceux déjà installés sont marqués.

Une fois le téléchargement fini, le modèle apparaît tout seul dans le menu :
la liste est relue à chaque ouverture.

## Le Codex

Depuis le menu de gauche, **Codex </>** ouvre un éditeur de code relié à
GitHub : l'arborescence du projet à gauche, l'éditeur au centre, un assistant à
droite.

Il faut un token GitHub *fine-grained* avec la permission **Contents : Read and
write** (bouton **Token**, ou variable `GITHUB_TOKEN`). Ensuite **Projet ▾**
liste tes dépôts.

- le code est coloré pour Python, JavaScript, HTML, CSS, JSON, shell, SQL et
  Markdown — seulement la partie visible à l'écran, pour rester rapide même sur
  un gros fichier ;
- **Scanner** lit tout le projet pour que l'assistant voie le code en entier ;
- l'assistant écrit des fichiers complets dans des blocs `[FICHIER …]`, qui
  s'ouvrent en onglets **sans rien envoyer** sur GitHub ;
- **Enregistrer** (ou `Ctrl` + `S`) envoie les onglets modifiés sur GitHub.

Sans projet ouvert, **Enregistrer** écrit les fichiers sur ton ordinateur.

### Le Codex web

Le même Codex existe dans `/app`, et il est **agentique** : au lieu de répondre
à partir de ce qu'on lui a montré, il se sert lui-même de cinq outils.

| Outil | Ce qu'il fait |
| --- | --- |
| `lister_fichiers` | voit le projet, avec un filtre optionnel |
| `chercher` | trouve un bout de texte partout, sans tout lire |
| `lire_fichier` | ouvre un fichier au complet |
| `ecrire_fichier` | réécrit un fichier |
| `remplacer_dans_fichier` | corrige un passage précis, s'il n'apparaît qu'une fois |

Il boucle jusqu'à quatorze tours, et chaque geste s'affiche pendant qu'il
travaille (`✓ lit src/app.js`, `✓ corrige src/vieux.js`). Ses changements vont
dans des **onglets marqués modifiés** — jamais directement sur GitHub. C'est toi
qui cliques **Enregistrer**, avec ton message de commit.

Ça marche avec Claude (blocs `tool_use`) et avec les modèles Ollama qui gèrent
les outils, comme `qwen3`, `llama3.2` ou `mistral`. Un modèle local sans
support d'outils répondra quand même, mais sans se servir du projet.

**Le token GitHub ne quitte jamais ton appareil.** `api.github.com` répond avec
`Access-Control-Allow-Origin: *`, faque le navigateur l'appelle directement :
le serveur du site ne voit ni ton token, ni ton code.

## Les schémas de plan

Quand la réponse décrit des étapes à suivre, elles sont redessinées sous la
réponse en un schéma : une boîte numérotée par étape, reliées par des flèches
où circule un courant vert lime qui allume les étapes une à une, puis
recommence.

C'est l'assistant qui décide : on lui demande de terminer sa réponse par un
bloc `[PLAN] … [/PLAN]`, une étape courte par ligne. Le bloc est retiré du
texte affiché. À défaut, si la question parlait de plan ou d'étapes et que la
réponse contient une liste numérotée d'au moins trois points, elle sert de
repli.

Les réglages sont dans `SchemaAnime` : `PAS_MS` (fluidité), `IMAGES_PAR_LIEN`
(vitesse du courant), `PAUSE_FIN` (pause avant de reboucler), `ESPACE`
(hauteur des flèches).

## La version web

`/app` sur le site reprend l'essentiel dans le navigateur : l'accueil avec le
logo, la saisie qui glisse vers le bas, la réponse qui s'écrit au fur et à
mesure, les schémas de plan animés, les sources cliquables, et les
conversations gardées — cette fois dans le navigateur (`localStorage`), pas sur
le disque.

### Trois façons de répondre, au choix dans le menu sous la boîte

| Moteur | Qui appelle qui | Ce qui sort de ton appareil |
| --- | --- | --- |
| **Ollama** | ton navigateur → `localhost:11434` | rien |
| **Claude (ta clé)** | ton navigateur → `api.anthropic.com` | ta question, vers Anthropic |
| **Claude (clé du site)** | ton navigateur → `/api/chat` → Anthropic | ta question, via le serveur |
| **Codex** | ton navigateur → `api.github.com` | rien : ton token reste ici |

Quand le Codex se sert de la clé du site, il passe par `/api/codex`, qui écrit
ses propres consignes et n'accepte que les cinq noms d'outils connus : la clé du
propriétaire ne devient pas un passe-partout.

**Ta clé Claude ne quitte jamais ton appareil.** Elle est gardée dans le
navigateur, et c'est le navigateur qui appelle l'API directement — le serveur du
site ne la voit jamais passer. C'est l'en-tête
`anthropic-dangerous-direct-browser-access` qui le permet.

### Les IA gratuites depuis le navigateur

Ollama tourne sur ta machine, et le navigateur peut lui parler : l'appel ne
passe pas par le serveur du site. Il faut juste autoriser le site, sinon Ollama
refuse l'appel :

```bash
OLLAMA_ORIGINS=https://marceau-78.vercel.app ollama serve
```

Le panneau des réglages (bouton **☰**) affiche la commande toute faite avec la
bonne adresse, et un bouton pour la copier.

Ce qui ne suit pas dans le navigateur : le **Codex**, qui demanderait une
connexion GitHub côté serveur.

### La mettre en route

Il faut une variable d'environnement sur Vercel :

| Variable | Rôle |
| --- | --- |
| `ANTHROPIC_API_KEY` | pour le moteur « clé du site » seulement — lue uniquement par la fonction |
| `CODE_ACCES` | facultatif — un code demandé aux visiteurs avant chaque question |

Ces deux variables ne servent qu'au moteur **« Claude (clé du site) »**. Sans
elles, les deux autres moteurs marchent quand même : chaque visiteur apporte sa
propre clé, ou utilise ses modèles Ollama.

⚠️ **Sans `CODE_ACCES`, n'importe qui ayant le lien peut poser des questions, à
tes frais.** Mets un code, ou garde la protection Vercel active sur `/app`.

La réponse arrive en flux (SSE) : le texte s'affiche pendant que Claude écrit,
plutôt que d'un bloc à la fin. La fonction est limitée à 60 secondes.

## Se télécharger, pis se tenir à jour

Écriture connaît son propre numéro de version (`VERSION`, en haut du script).
Les deux versions se mettent à jour toutes seules, chacune à sa manière.

### La version de bureau

Au démarrage, en arrière-plan, l'application va lire le `ecriture.py` publié sur
GitHub et compare les deux numéros. S'il y a du neuf :

1. elle **vérifie que le code téléchargé compile** — un fichier brisé est refusé
   avant qu'il touche à quoi que ce soit ;
2. elle **garde ton ancienne version** à côté, sous `ecriture_precedent.py` ;
3. elle **remplace le fichier d'un seul coup** (`os.replace`), jamais en deux
   morceaux : il n'y a pas d'instant où le script est à moitié écrit.

Puis elle te dit de redémarrer. Elle ne redémarre jamais toute seule pendant que
t'écris.

L'adresse est **écrite en dur dans le script** : Écriture ne téléchargera jamais
de code venu d'ailleurs, même si un fichier de configuration disait le
contraire. Ça reste du code qui se remplace lui-même à partir d'Internet, faque
ça vaut ce que vaut ta confiance envers ce dépôt-là : si t'aimes mieux décider
toi-même, décoche **Se mettre à jour toute seule** dans Paramètres. Le bouton
**⟳ Vérifier maintenant** fait alors la job à la main.

### La version web

Elle s'installe comme une vraie application — le bouton **Installer l'app**
dans Paramètres, ou l'invite de ton navigateur. Une fois installée, elle
s'ouvre dans sa propre fenêtre, avec son icône.

Son service worker (`app/sw.js`) va **toujours voir le réseau en premier** et ne
garde le cache que comme filet : dès que t'es en ligne, t'as la dernière
version, et sans Internet l'app se charge quand même.

> Détail qui compte : un `fetch()` ordinaire dans un service worker se fait
> servir par le cache du navigateur, ce qui fait qu'un « réseau d'abord » naïf
> n'atteint jamais le réseau. Il faut `cache: "reload"`. C'est ce qui est fait
> ici, avec en plus des en-têtes `no-cache` sur `/app` (dans `vercel.json`) pour
> les navigateurs sans service worker.

Quand une nouvelle version arrive pendant que l'app est ouverte, elle prend la
place tout de suite (`skipWaiting`), le bandeau te le dit, et la page se
recharge une seule fois.

## Personnaliser

Les couleurs, les polices et les proportions sont regroupées en haut de
`ecriture.py` :

- `GRIS_FOND`, `GRIS_ZONE`, `GRIS_BORD`, `NOIR`, `ORANGE`, `ORANGE_FONCE`
- `LIME`, `LIME_LUEUR`, `GRIS_BOITE`, `GRIS_LIEN` — les couleurs des schémas
- `FAMILLE`, `POLICE`, `POLICE_BOUTON`, `POLICE_INVITE`
- `RAYON_BOUTON`, `RAYON_ZONE` — l'arrondi des coins, en pixels (0 = carré)
- `MARGE` (espace sous la saisie), `LARGEUR` (largeur des zones, en fraction de
  la fenêtre), `HAUT_DOC` (hauteur à laquelle commence le document)
- `LOGO`, `LOGO_PETIT`, `LOGO_ACCUEIL` — les fichiers d'image

Puis les réglages des IA :

- `MODELE_CLAUDE` (celui choisi au démarrage), `MODELES_CLAUDE` (ceux offerts
  dans le menu), `URL_CLAUDE`, `URL_OLLAMA`, `FICHIER_CLE`
- `RECHERCHES_MAX` — recherches web maximum par question
- `NOM_CLAUDE` — le nom affiché dans le menu
- `STYLE_QUEBECOIS` — `False` pour du français standard
- `DUREE_ECRITURE`, `VITESSE_MS` — l'effet machine à écrire (mettre
  `DUREE_ECRITURE = 0` affiche la réponse d'un coup)
- `instructions_systeme()` — le ton et les consignes données à l'assistant

### Les coins ronds

Tkinter ne sait arrondir ni un bouton ni une boîte de texte. La forme est donc
dessinée sur un `Canvas` (`points_arrondis`, `BoutonRond`, `MenuRond`), et pour
le texte, `ZoneRonde` pose un vrai `tk.Text` par-dessus, en retrait des coins
pour que son rectangle ne dépasse pas de l'arrondi.
