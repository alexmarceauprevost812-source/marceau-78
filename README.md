# marceau-78

**Écriture** — un espace d'écriture minimaliste en Python/Tkinter, doublé d'un
assistant qui répond aux questions.

Page de présentation : <https://marceau-78.vercel.app>

Deux moteurs au choix, dans un menu sous la boîte de saisie :

- **les modèles locaux d'Ollama** — gratuits, hors ligne, sur ta machine
- **Claude + recherche web** — payant, mais il va chercher l'info à jour

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
| `index.html` | la page de présentation publiée sur Vercel |
| `app/` | la version web d'Écriture (`/app` sur le site) |
| `api/chat.js` | la fonction serverless qui parle à Claude, clé côté serveur |
| `package.json` | la seule dépendance : le SDK Anthropic, installé par Vercel |
| `vercel.json` | fait télécharger `ecriture.py` au lieu de l'afficher |
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

À la première question, l'application la demande et l'enregistre dans
`~/.config/ecriture/cle_api`, en clair, avec les droits `600` (lisible
uniquement par ton compte). Le bouton **Clé API** permet de la changer.

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
| Brancher la clé API ou le token | bouton **Paramètres ⚙** |

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

Le bouton **☰** en haut à gauche ouvre un panneau qui garde toutes tes
conversations. Elles sont enregistrées toutes seules dans
`~/.local/share/ecriture/sessions`, une par fichier JSON, avec leurs schémas et
leurs sources. Un clic rouvre une conversation, un clic droit la supprime.

## Paramètres

Le bouton **Paramètres ⚙**, en bas du menu de gauche (ou en haut de l'écran une
fois la conversation commencée), regroupe les deux branchements :

| | Pour quoi | Où la prendre |
| --- | --- | --- |
| Clé API Claude | l'IA payante avec recherche web | <https://console.anthropic.com> |
| Token GitHub | le Codex | *Settings → Developer settings → Fine-grained tokens*, permission **Contents : Read and write** |

La fenêtre dit pour chacune si elle est branchée et d'où elle vient (fichier sur
l'ordi, ou variable d'environnement) — **sans jamais réafficher la valeur**. Un
champ laissé vide n'est pas touché ; **Effacer** supprime ce qui est enregistré.

Les deux sont écrites dans `~/.config/ecriture`, en mode `600` : lisibles
uniquement par ton compte. Rien ne part ailleurs.

## Les IA gratuites

Si le menu sous la boîte d'écriture ne propose que Claude, c'est qu'Ollama ne
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

Ce qui ne suit pas : **Ollama** (il écoute sur `localhost`, un site hébergé ne
peut pas l'atteindre) et le **Codex** (il lui faudrait une connexion GitHub
côté serveur).

### La mettre en route

Il faut une variable d'environnement sur Vercel :

| Variable | Rôle |
| --- | --- |
| `ANTHROPIC_API_KEY` | obligatoire — la clé Claude, lue seulement par la fonction |
| `CODE_ACCES` | facultatif — un code demandé aux visiteurs avant chaque question |

**La clé ne part jamais dans le navigateur** : la page appelle `/api/chat`, et
c'est la fonction serverless qui parle à Claude.

⚠️ **Sans `CODE_ACCES`, n'importe qui ayant le lien peut poser des questions, à
tes frais.** Mets un code, ou garde la protection Vercel active sur `/app`.

La réponse arrive en flux (SSE) : le texte s'affiche pendant que Claude écrit,
plutôt que d'un bloc à la fin. La fonction est limitée à 60 secondes.

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

- `MODELE_CLAUDE`, `URL_CLAUDE`, `URL_OLLAMA`, `FICHIER_CLE`
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
