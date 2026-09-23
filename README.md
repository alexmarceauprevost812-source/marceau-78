# marceau-78

**Marceau** — un espace d'écriture minimaliste en Python/Tkinter, doublé d'un
assistant qui répond aux questions.

Page de présentation : <https://marceau-78.vercel.app>

> **Le nom.** L'application s'appelle **Marceau**. Le fichier, lui, reste
> `ecriture.py`, et tes réglages restent dans `~/.config/ecriture/` et
> `~/.local/share/ecriture/` : c'est ce qui permet à la mise à jour
> automatique de continuer de marcher et à ta clé API, tes conversations
> pis tes images de rester en place.

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
| `requirements.txt` | ce qu'il faut installer pour les images et les pouvoirs magiques |
| `logo.png` | le logo MARCEAU en 512 px : c'est l'icône de la fenêtre et de la barre des tâches |
| `logo_64.png` | le même en 64 px, pour la barre des tâches |
| `logo_accueil.png` | le logo découpé en rond, affiché sur l'accueil |
| `logo_marceau.png` | le logo de l'agent, en 320 px, qui glisse du centre vers la gauche |
| `logo_192.png`, `logo_maskable.png` | les icônes de l'app installable |
| `index.html` | la page de présentation publiée sur Vercel |
| `app/` | la version web de Marceau (`/app` sur le site) |
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

Le cœur de l'application n'a besoin de rien d'autre que la bibliothèque
standard (les appels réseau passent par `urllib`). Tkinter est généralement
livré avec Python ; sur Debian/Ubuntu, s'il manque :

```bash
sudo apt install python3-tk
```

Les images et les sept **pouvoirs magiques** demandent chacun leur
bibliothèque — voir `requirements.txt` et la section
[Les pouvoirs magiques](#les-pouvoirs-magiques--magie). Rien n'est
obligatoire : ce qui manque est simplement expliqué au lieu de planter.

## Le « + » dans la boîte où tu écris

La boîte où tu écris a un **+** orange dedans, en bas à gauche. Un clic ouvre
un petit menu :

| Dans le menu | Ce que ça fait |
| --- | --- |
| **Ajouter des images…** | joint jusqu'à 4 images à ta question ; l'IA les regarde |
| **Créer un fichier…** | fait un PDF, une page web ou un texte avec la conversation (voir plus bas) |
| **Mes fichiers** | la liste des fichiers que t'as créés (ordi seulement) |

Les images jointes apparaissent en petit dans la boîte, chacune avec un **×**
pour l'enlever. Tu peux envoyer une image sans rien écrire : la question
devient « Regarde mon image. ».

Sur le **site web**, ça marche pareil, pis en plus :

- tu peux **coller** une image (`Ctrl` + `V`) ou la **glisser** sur la page ;
- sur un téléphone, « Ajouter des images… » offre aussi l'appareil photo ;
- une photo de téléphone « couchée » est remise debout, une image
  transparente reçoit un fond blanc, pis tout est réduit à 1568 pixels au plus
  (ce que Claude recommande) avant de partir.

**Qui voit tes images.** Claude les voit toujours. Parmi les IA gratuites,
seulement celles qui voient les images (gemma3, llava, llama3.2-vision…) :
Marceau le demande à Ollama. Sinon, l'IA reçoit ton texte avec une note qui
dit qu'il y avait une image, pis Marceau te le dit sous la réponse. L'IA revoit
les images des trois derniers messages qui en ont, pas plus.

**Ce qui est gardé.** Sur le site, une conversation gardée dans le navigateur
garde seulement une **vignette** de chaque image (quelques Ko) : la place y
est comptée (environ 5 Mo pour tout). Si ça déborde quand même, les vieilles
conversations perdent leurs vignettes avant qu'on en perde une seule. Par le
serveur du site (« clé du site »), une demande est limitée à 4,5 Mo : ce sont
les plus vieilles images qui sautent en premier.

## Faire un fichier à envoyer (Fichier ▸ Créer)

Le bouton **Fichier** de la barre du haut — ou **Créer un fichier…** dans le
**+** de la boîte — transforme ce que t'as écrit en un document que tu peux
remettre ou envoyer — un devoir, un rapport, une note.

**Fichier ▸ Créer un fichier…** ouvre une fenêtre avec :

- le **titre**, proposé à partir de ta première question ;
- le **contenu**, pré-rempli avec ta sélection, ou tout le texte si t'as rien
  sélectionné ;
- **les images de la conversation** — celles que t'as jointes et celles que le
  Studio a faites — chacune avec une case à cocher ;
- la **sorte de fichier**.

| Sorte | Ce que ça donne |
| --- | --- |
| **PDF** | un vrai PDF A4, texte et images, à imprimer ou à remettre |
| **Page web** | un seul fichier `.html`, images incluses, s'ouvre partout |
| **Texte brut** | un `.txt` ; les images sont nommées `[Image 1]`, pas incluses |

**Fichier ▸ Mes fichiers** liste tout ce que t'as créé, du plus récent au plus
vieux, avec un bouton pour l'ouvrir ou ouvrir le dossier. Par défaut, ça va
dans `~/.local/share/ecriture/fichiers/`.

### Le PDF est écrit à la main

Pas de librairie à installer : le PDF est construit directement, avec la
police Helvetica intégrée au format (aucune police à embarquer). Les lignes
sont coupées avec les vraies largeurs de lettres, les accents passent en
WinAnsi, les pages se suivent toutes seules, et les images sont mises telles
quelles en JPEG (`DCTDecode`), ce que le PDF sait lire nativement. Une image
trop haute est réduite pour rentrer dans la page.

Sans Pillow, le texte marche pareil ; ce sont seulement les images qui
manquent.

### Sur le site web

Le **+** de la boîte offre le même **Créer un fichier…**, avec les trois mêmes
sortes. Le fichier est fait **dans ton navigateur** (`app/fichiers.js`, le même
moteur traduit en JavaScript : il donne le même PDF, octet pour octet) pis il
arrive dans tes téléchargements. Rien passe par le serveur du site, pis ça
marche sans Internet.

## Les pouvoirs magiques (✨ Magie)

Sept pouvoirs qui roulent **sur ton ordi**, gratuitement, sans compte et
sans que ton texte parte sur Internet. Le menu **✨ Magie** s'ouvre de trois
façons : le bouton dans la barre du haut, le bouton sous la boîte d'écriture,
ou un **clic droit** sur ton texte.

Chaque pouvoir travaille sur **ta sélection**. Si t'as rien sélectionné, il
prend tout le texte du document.

| Pouvoir | Ce qu'il fait | Ce qui le fait rouler |
| --- | --- | --- |
| ✨ Continuer mon texte | écrit la suite, dans ton ton à toi | Ollama |
| 🪄 Corriger les fautes | les montre une par une, tu acceptes ou refuses | LanguageTool |
| 🎭 Changer le style | réécrit en québécois, formel, drôle ou poétique | Ollama |
| 📜 Résumer | ajoute un résumé **sous** ton texte, sans rien effacer | Ollama |
| 🎤 Dicter | ta voix devient du texte, là où est ton curseur | faster-whisper |
| 🔊 Lire à voix haute | lit ton texte avec une voix française | Piper, ou la voix du système |
| 🌍 Traduire | français ↔ anglais, sans Internet | Argos Translate |

Tout roule **en arrière-plan** : la fenêtre ne gèle jamais, et les trois
points qui sautent montrent que ça travaille. **Ctrl+Z** ramène ton texte
d'avant, en une seule fois, pour n'importe quel pouvoir.

Si quelque chose manque — Ollama pas démarré, modèle pas téléchargé, micro
introuvable, Java absent — l'app te le dit en français avec la commande
exacte à copier-coller, au lieu de planter.

### Installer les pouvoirs magiques (Ubuntu / Debian)

Rien n'est obligatoire : installe seulement les pouvoirs qui t'intéressent.
L'app marche pareil sans eux.

**1. Un environnement Python à part** (Ubuntu récent refuse que `pip`
installe dans le Python du système) :

```bash
sudo apt install python3-venv python3-tk
python3 -m venv ~/ecriture-venv
~/ecriture-venv/bin/pip install -r requirements.txt
```

Ensuite, lance Marceau avec ce Python-là :

```bash
~/ecriture-venv/bin/python ecriture.py
```

**2. Ollama** — pour Continuer, Changer le style et Résumer :

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
ollama serve
```

Le modèle se choisit dans le menu orange sous la boîte d'écriture : les
pouvoirs se servent de celui que t'as choisi. `llama3.2` est léger et
rapide ; `mistral` ou `gemma3` écrivent mieux mais demandent plus de RAM.

**3. Java** — pour Corriger les fautes :

```bash
sudo apt install default-jre
```

Au premier usage, LanguageTool télécharge son correcteur (~250 Mo). Après,
il marche sans Internet.

**4. Le micro** — pour Dicter :

```bash
sudo apt install libportaudio2
arecord -l          # pour voir si ton micro est reconnu
```

Au premier usage, faster-whisper télécharge son modèle (~500 Mo pour
`small`). Pour un modèle plus léger ou plus précis, change `MODELE_WHISPER`
en haut de `ecriture.py` : `tiny`, `base`, `small`, `medium`, `large-v3`.

**5. La voix française** — pour Lire à voix haute :

```bash
sudo apt install alsa-utils
~/ecriture-venv/bin/python -m piper.download_voices fr_FR-siwis-medium \
  --download-dir ~/.local/share/ecriture/voix
```

L'app peut aussi la télécharger toute seule : clique **🔊 Lire à voix
haute**, elle te le proposera.

**6. Les langues de traduction** — pour Traduire :

L'app les télécharge toute seule la première fois que tu cliques
**🌍 Traduire** (environ 100 Mo par sens). Après, ça marche hors ligne.

### Essayer chaque pouvoir

Écris ou colle un texte dans le document du haut, puis :

| Pouvoir | Comment l'essayer | Ce que tu dois voir |
| --- | --- | --- |
| ✨ Continuer | écris deux phrases, ne sélectionne rien, **✨ Magie → Continuer** | un paragraphe s'ajoute à la fin |
| 🪄 Corriger | écris « Je sui aller a la maison », **→ Corriger** | une fenêtre : « Faute 1 sur 3 », avec Accepter / Refuser |
| 🎭 Style | sélectionne une phrase, **→ Changer le style → Drôle** | la phrase est remplacée ; Ctrl+Z la ramène |
| 📜 Résumer | colle un long texte, **→ Résumer** | « Résumé : » apparaît **sous** ton texte |
| 🎤 Dicter | clique où écrire, **→ Dicter**, parle, **Arrêter** | tes mots s'écrivent au curseur |
| 🔊 Lire | sélectionne une phrase, **→ Lire à voix haute** | tu l'entends ; le menu offre alors « Arrêter la lecture » |
| 🌍 Traduire | sélectionne une phrase, **→ Traduire → Français → English** | la phrase devient anglaise |

Si un pouvoir ne répond pas, c'est qu'il manque quelque chose : l'app ouvre
une fenêtre qui dit exactement quoi taper.

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
| Joindre des images, créer un fichier | le **+** dans la boîte |
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
du même logo précède chaque réponse — dans le chat **et dans le Codex**, même
un message d'erreur. La version web fait pareil.

## L'IA lit ses réponses à voix haute

Le bouton **🔊 Voix**, sous la boîte d'écriture du chat comme du Codex, fait
lire chaque réponse à voix haute une fois qu'elle est écrite. Il est **allumé
par défaut**.

| Le bouton dit | Ça veut dire | Un clic… |
| --- | --- | --- |
| 🔊 Voix | la voix est allumée | la coupe |
| 🔇 Voix (gris) | la voix est coupée | la rallume |
| ⏹ Silence | elle est en train de lire | fait taire **cette** réponse ; la voix reste allumée |

Une nouvelle question, **Nouveau** ou fermer l'app font taire la réponse en
cours. Le choix allumé/coupé est gardé pour la prochaine fois.

Ce qui est lu : le texte de la réponse, **jamais** le code (dans le Codex, on
entend l'explication, pas les fichiers), ni les adresses web, ni les émojis,
ni les blocs `[PLAN]`, `[MÉTÉO]`, `[FICHIER]`. Une très longue réponse est
coupée à la fin d'une phrase, vers 4000 caractères.

### Quelle voix

L'app prend la meilleure qu'elle trouve, dans cet ordre :

1. **Piper** — une voix naturelle (voir « La voix française » plus haut).
2. **spd-say** — la voix du système, déjà là sur la plupart des Ubuntu de
   bureau ; elle suit tes réglages d'accessibilité.
3. **espeak-ng** — plus robotique, mais toujours là.

S'il n'y en a aucune, l'app le dit **une seule fois** avec la commande à taper :

```bash
sudo apt install speech-dispatcher espeak-ng
```

Piper lit **phrase par phrase** : la première se dit pendant que les suivantes
se préparent, et **⏹ Silence** coupe entre deux. Aucun fichier son ne reste
sur ton disque.

Dans la **version web**, c'est la voix du navigateur (rien à installer, ça
marche sur un téléphone) : une voix `fr-CA` si ton appareil en a une, sinon une
autre voix française.

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

Depuis le menu de gauche, **Codex** ouvre **un seul écran, centré** : tu écris
en bas, les réponses arrivent au milieu. Pas de panneau à gauche, pas de
panneau à droite — comme Claude Code sur un téléphone.

Pour tes projets GitHub, il faut un token *fine-grained* avec la permission
**Contents : Read and write** (Paramètres, ou la variable `GITHUB_TOKEN`).
Ensuite **Projet ▾** liste tes dépôts. Pour un dossier de ton ordi, pas besoin
de token : c'est OpenCode qui travaille (voir plus bas).

Tu dis ce que tu veux changer. **T'as rien à ouvrir** : l'assistant trouve les
fichiers tout seul. Sur un petit projet il lit tout; sur un gros, il demande
d'abord à l'IA lesquels lire (bloc `[LIRE]`), pis il peut en redemander
d'autres avant d'écrire — deux tours au maximum, pour pas tourner en rond.

### Les cartes de fichiers

Chaque fichier touché arrive dans la conversation en **carte fermée** :

```
▸ src/app.py    +2 −1                   [Projet] [Modifier]
▸ src/neuf.py   nouveau fichier  +1     [Projet] [Modifier]
```

Un clic l'ouvre et montre **ce qui a changé**, pas juste le fichier :

- les lignes **ajoutées** en vert, avec un `+` et leur numéro ;
- les lignes **enlevées** en rouge, avec un `−` ;
- le reste en gris, pour le contexte ;
- les longs bouts pareils repliés en `⋯ 14 lignes pareilles`, pour pas noyer
  les changements.

Un fichier neuf s'affiche tout en vert. Le bouton **Modifier** ouvre l'éditeur
par-dessus l'écran, avec la coloration et les onglets; **‹ Retour** te ramène.
**Projet** garde le code du fichier dans un de tes projets (voir « Les
projets » plus bas).

Si l'éditeur est ouvert pendant que l'IA travaille, tu vois ses fichiers
**s'écrire en direct, un après l'autre**. Fermé, ils arrivent d'un coup.

**Fichiers** ouvre la liste du projet dans une fenêtre, si tu veux aller voir
un fichier toi-même. **Enregistrer (N)** dit combien attendent d'être envoyés.

### Pendant que ça travaille

Trois points sautent en vague à côté du texte, en passant du rouge au jaune au
vert. Le texte change au fil du travail — « Codex cherche les bons fichiers »,
« Codex lit 3 fichier(s) : app.py, README.md », « Codex écrit le code » — sans
que les points arrêtent de sauter. Les mêmes points servent dans le chat et
pendant que la météo se charge.

### Le Codex web

Le Codex de `/app` a **exactement le même écran** que celui d'ordinateur : une
seule colonne, centrée, pas de panneau de côté. Tu écris en bas, les fichiers
touchés arrivent en cartes fermées avec leurs comptes, pis un clic montre les
lignes ajoutées en vert et celles enlevées en rouge. **Modifier** ouvre
l'éditeur par-dessus, **‹ Retour** le referme, **Fichiers** ouvre la liste du
projet.

Il est **agentique** : au lieu de répondre à partir de ce qu'on lui montre, il
se sert lui-même de cinq outils (six si tu coches « Pousser tout seul »).

| Outil | Ce qu'il fait |
| --- | --- |
| `lister_fichiers` | voit le projet, avec un filtre |
| `chercher` | trouve un bout de texte partout, sans tout lire |
| `lire_fichier` | ouvre un fichier au complet |
| `ecrire_fichier` | réécrit un fichier |
| `remplacer_dans_fichier` | corrige un passage précis, s'il n'apparaît qu'une fois |
| `pousser_sur_github` | envoie tout d'un coup — **seulement si tu as coché la case** |

Il boucle jusqu'à quatorze tours, et chaque geste s'affiche pendant qu'il
travaille (`✓ lit src/app.py`, `✓ corrige src/app.py`).

Ça marche avec Claude (blocs `tool_use`) et avec les modèles Ollama qui gèrent
les outils, comme `qwen3`, `llama3.2` ou `mistral`. Un modèle local sans
support d'outils répondra quand même, mais sans se servir du projet.

**Le token GitHub ne quitte jamais ton appareil.** `api.github.com` répond avec
`Access-Control-Allow-Origin: *`, faque le navigateur l'appelle directement :
le serveur du site ne voit ni ton token, ni ton code.

### OpenCode : un dossier de ton ordi

[OpenCode](https://opencode.ai) est un agent de code **gratuit pis open source**.
Marceau le pilote pour toi : il travaille **directement dans un dossier de ton
ordi**. Il lit tes fichiers, les change, pis lance des commandes (des tests, par
exemple).

**L'installer** (une seule fois), dans un terminal :

```bash
curl -fsSL https://opencode.ai/install | bash
```

Pas besoin de le configurer : **Marceau lui passe l'IA que t'as choisie en
bas**. Ça peut être ta clé Claude, ou un modèle Ollama gratuit.

**S'en servir** :

1. Dans le Codex, clique **Projet ▾ → Un dossier sur mon ordi (avec OpenCode)…**
   pis choisis le dossier de ton projet. Pas besoin de token GitHub.
2. Écris ce que tu veux, comme d'habitude (« ajoute un bouton pour vider la
   liste », « lance les tests pis corrige ce qui plante »).
3. Pendant qu'il travaille, tu vois ce qu'il fait (« OpenCode lit app.py »,
   « OpenCode lance : npm test »). Le bouton **Envoyer** devient **Arrêter** :
   un clic l'arrête, lui pis les commandes qu'il a lancées.
4. À la fin, tu as sa réponse, les fichiers qu'il a lus, les commandes lancées,
   pis **une carte par fichier changé**. Les mêmes cartes qu'avant : un clic
   montre les lignes en vert et en rouge.

Ses changements sont **déjà enregistrés dans ton dossier**. Si t'aimes pas ça,
**Remettre comme avant** défait tout ce qu'il vient de changer. Un fichier que
t'as retouché depuis est laissé tel quel, par prudence. OpenCode se souvient de
la conversation d'une demande à l'autre, pis il sait quand t'as défait ses
changements.

Tu peux aussi ouvrir un fichier (**Fichiers**), le changer à la main pis
cliquer **Enregistrer** : ça s'écrit direct dans ton dossier.

Pour **mettre OpenCode à jour** : `opencode upgrade` dans un terminal.

#### Ta sécurité avec OpenCode

- **Jamais en dehors de ton dossier.** Marceau lui interdit de toucher à
  quoi que ce soit ailleurs sur ton ordi. S'il essaie, c'est bloqué, pis tu
  le vois : « Bloqué pour te protéger : … ».
- **Ta clé Claude reste dans son fichier protégé** (`~/.config/ecriture/cle_api`,
  que toi seul peux lire). Marceau dit juste à OpenCode où la lire : elle est
  jamais copiée dans sa config ni dans l'environnement, faque les commandes
  qu'OpenCode lance la voient pas. Elle part seulement chez Claude, comme avec
  le reste de Marceau.
- La config d'OpenCode passe **en mémoire**, rien d'écrit sur ton disque. Le
  partage de conversations d'OpenCode est coupé.
- OpenCode peut lancer des commandes dans ton dossier : c'est ce qui lui
  permet de rouler tes tests. Choisis le dossier de ton projet, pas ton
  dossier personnel au complet.

#### Avec Ollama

OpenCode a de longues consignes. Avec la mémoire par défaut d'Ollama, le modèle
les voit coupées, pis il se sert pas de ses outils. Marceau fait donc tout seul
une **copie du modèle avec plus de mémoire** (16 384 jetons), nommée par
exemple `qwen3:opencode`. Ça prend pas de place : c'est juste une fiche qui
pointe sur le même modèle. Elle est cachée dans le menu de Marceau, mais tu la
vois dans `ollama list`. Si ça rame, prends un modèle plus petit.

Prends un modèle qui sait se servir d'outils : `qwen3`, `llama3.2`,
`mistral`… Si Ollama est éteint, Marceau te le dit tout de suite au lieu
d'attendre.

La version web peut pas lancer OpenCode : c'est un programme qui roule sur ton
ordi, pis un site a pas le droit de lancer des programmes sur ton ordi.

## Le Studio d'applications : l'IA construit une petite app

Demande au chat une petite application — « fais-moi un compteur », « un jeu de
tic-tac-toe », « une calculatrice de pourboire » — pis regarde-la se construire.

L'IA l'écrit au complet dans **un seul fichier HTML** (le CSS pis le JavaScript
dedans), dans un bloc `[APP titre]…[/APP]`. L'app lit aussi un ` ```html ` ou une
page `<!DOCTYPE html>` écrite telle quelle, parce que les modèles ne suivent pas
toujours les consignes. La conversation garde l'explication ; le code, lui,
s'en va dans une carte **Studio** :

| | App de bureau | Version web |
| --- | --- | --- |
| Pendant que ça s'écrit | le code s'écrit sous tes yeux, en couleurs | l'app elle-même se construit, en direct, dans la carte |
| Voir l'app | **▶ Voir l'app** l'ouvre dans ton navigateur (toute seule la 1re fois) | elle tourne dans la carte ; **⛶ Plein écran** pour la voir en grand |
| La garder | **Enregistrer** — avec tes fichiers (Fichier ▸ Mes fichiers) | **⤓ Télécharger** |
| Le reste | **Mettre dans le Codex** en fait le `index.html` de ton projet | **</> Code** montre son code |

### Changer une app

Dis-lui juste quoi changer : « fais-le plus gros », « mets-le en bleu ». L'IA
revoit le code de **sa dernière app** pour le modifier (les plus vieilles sont
seulement nommées, pour ne pas repayer leur code à chaque message), et la
réécrit avec le même titre.

Sur le bureau, **l'onglet déjà ouvert se recharge tout seul** : l'aperçu est
servi par un petit serveur sur ton ordi (`127.0.0.1` seulement — personne
d'autre peut s'y connecter), pis la page regarde aux 0,8 s si l'app a changé.

### Ta sécurité

Sur la version web, **ta clé Claude pis ton token GitHub sont gardés dans le
navigateur**. Le code écrit par l'IA tourne donc dans un cadre isolé (un
`iframe` `sandbox` **sans** `allow-same-origin`) : il a sa propre origine, vide,
et ne peut pas les lire. **Plein écran** garde le même cadre isolé dans une
fenêtre neuve, pis coupe le lien vers l'onglet de Marceau. Les tests vérifient
qu'une app qui essaie de lire ta clé se fait bloquer, pour vrai.

## Les projets

Un projet garde **tes conversations, tes fichiers pis tes notes au même
endroit**, pis l'IA s'en sert quand tu travailles dedans. Pratique pour un
devoir, un livre, un projet d'école.

**L'ouvrir** : menu ☰, clique **Chat** : **→ Projets** sort en dessous.

**Créer** : **+ Nouveau projet**, donne-lui un nom. Ensuite :

- **Instructions pour l'IA** : ce qu'elle doit savoir (« Devoir de 5e année,
  réponds simplement »). Clique **Enregistrer les instructions**.
- **Conversations** : **+ Ajouter** en met une qui existe déjà.
- **Fichiers** : **+ Fichier** copie un fichier de ton ordi dans le projet.
- **Notes** : **+ Note** (du texte ou du code, deviné tout seul) pis **+ Lien**.
- **Ouvrir** montre ce que t'as choisi (le code en couleurs, les liens dans ton
  navigateur), **Retirer** l'enlève.

**Travailler dans ce projet** commence une conversation dedans. En haut,
**Projet : …** te rappelle où t'es : un clic ouvre le projet, **×** en sort.
L'IA reçoit les instructions, le texte de tes fichiers pis tes notes (jusqu'à
60 000 caractères avec Claude, 8 000 avec un modèle Ollama).

Pour mettre des affaires dans un projet :

- **Garder dans le projet**, sous chaque réponse : la réponse devient une note.
- **Clic droit** sur du texte sélectionné → **Garder la sélection dans un
  projet**. Les pouvoirs ✨ Magie sont toujours là, en dessous de Copier.
- **Clic droit** sur une conversation du menu → **Mettre dans un projet** (ou
  **Sortir du projet**).
- **Garder dans le projet** dans le Studio, **Projet** sous une image trouvée,
  **Projet** sur une carte du Codex.

Si t'es pas dans un projet, un petit menu te demande lequel (ou d'en créer un).

Tout est gardé sur ton ordi, dans `~/.local/share/ecriture/projets/` : un
dossier par projet, avec `projet.json` pis un dossier `fichiers`. Les dossiers
faits par l'ancien « Garder dans le projet » deviennent des projets tout seuls,
avec leurs images.

## Les images libres de droits

Demande « montre-moi des images de panda roux » : Marceau cherche des images
**libres de droits** dans [Openverse](https://openverse.org) (Flickr,
Wikimedia, des musées…). Si Openverse répond pas, il essaie
[Wikimedia Commons](https://commons.wikimedia.org). Tu vois 4 images, chacune
avec :

- son **titre** : un clic ouvre la page d'origine;
- son **auteur** pis sa **licence** (CC BY, CC BY-SA…). Si tu publies une image,
  nomme son auteur comme la licence le demande;
- **Studio** : l'image s'ouvre dans le Studio, pour la modifier;
- **Projet** : elle va dans un de tes projets.

L'IA choisit des mots-clés en anglais : les banques d'images le comprennent
mieux. Si elle oublie, Marceau cherche avec les mots de ta question. Sans
Internet, il te le dit.

Les projets pis les images libres sont dans Marceau sur l'ordi. Le site web les
a pas encore.

## Le Studio : les images

Le bouton **+ Image** sous la boîte joint jusqu'à 4 images à ta question
(PNG, JPEG, WebP, GIF, BMP, TIFF). Une petite vignette s'affiche à côté du
bouton, avec un **×** pour l'enlever. Envoyer une image sans rien écrire
marche : la question devient « Regarde mon image. »

Les images sont copiées dans `~/.local/share/ecriture/images/`, et ce sont ces
copies que la conversation retient — rouvrir une conversation les remontre.

### Qui voit quoi

| Moteur | Voit l'image ? |
| --- | --- |
| Claude (tous les modèles) | oui |
| Ollama : `gemma3`, `llava`, `moondream`, `minicpm-v`, `qwen2-vl`… | oui, détecté par `/api/show` |
| Les autres modèles locaux | non — l'app le dit, et propose `ollama pull gemma3` |

Une IA qui ne voit pas les images peut quand même les **modifier** : le Studio
travaille sur l'image, pas sur ce que l'IA en perçoit. Seules les 3 dernières
images de la conversation partent à l'IA, redimensionnées à 1568 px au plus.

### Modifier une image

Quand tu demandes un changement, l'assistant termine sa réponse par un bloc
que l'app exécute elle-même avec Pillow :

```
[STUDIO]
noir_et_blanc
contraste 1.3
texte "Bonne fête!" bas blanc
[/STUDIO]
```

Les opérations, une par ligne, dans l'ordre : `luminosite X`, `contraste X`,
`saturation X`, `nettete X`, `noir_et_blanc`, `sepia`, `inverser`, `flou X`,
`rotation X`, `miroir`, `miroir_vertical`, `recadrer G H D B`, `carre`,
`taille L`, `texte "…" haut|centre|bas couleur`, `bordure N couleur`,
`vignette X`, `chaud`, `froid`, `pixeliser N`, `posteriser N`.

La lecture est tolérante : `noir et blanc`, `Noir-Et-Blanc` et `noir_et_blanc`
donnent la même chose, et pour les quatre réglages d'intensité un nombre signé
ou en pourcentage (`contraste +35`, `luminosite -20 %`) se lit comme un écart,
pas comme un facteur. Une opération qu'on ne comprend pas est sautée sans
empêcher les autres.

**Garder dans le projet** range l'image sur ton ordi, dans
`~/.local/share/ecriture/projets/<nom>/`. Le nom du dernier projet est
proposé la fois d'après, pour empiler plusieurs images au même endroit.

Le résultat s'affiche dans une carte **Studio** qui s'ouvre en glissant :
l'image, la liste de ce qui a été fait, un bouton **Voir l'avant / Voir
l'après**, **Enregistrer** (sur l'ordi) et **Mettre dans le Codex**. Chaque
modification part de l'image précédente : on peut enchaîner les demandes.

### Le code qui s'écrit en direct

Quand l'éditeur est **ouvert**, le fichier écrit par l'assistant s'écrit
sous tes yeux, lettre par lettre, avec les couleurs qui suivent —
`DUREE_CODE` secondes au plus, quelle que soit la longueur. Quand il est
**fermé**, le code arrive d'un coup : ça sert à rien d'attendre pour
quelque chose qu'on ne voit pas. Un seul Ctrl+Z ramène l'ancien contenu
dans les deux cas.

### Les images dans le Codex

Le Codex a le même bouton **+ Image** sous sa boîte, et un **+ Image** dans la
barre de l'éditeur pour prendre une image de ton ordi. Ouvrir une image du
projet l'affiche au lieu d'essayer de la lire comme du texte. Pour mettre une
image jointe dans le projet, l'assistant écrit une ligne
`[IMAGE 1 images/logo.png]` ; elle part sur GitHub en binaire avec
**Enregistrer**, comme n'importe quel autre fichier.

Sans Pillow (`pip install pillow`), tout le reste de l'app marche pareil : les
boutons d'image expliquent simplement ce qu'il manque.

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
| **Claude (ta clé)** | ton navigateur → `api.anthropic.com` | ta question (pis tes images), vers Anthropic |
| **Claude (clé du site)** | ton navigateur → `/api/chat` → Anthropic | ta question (pis tes images), via le serveur |
| **Codex** | ton navigateur → `api.github.com` | rien : ton token reste ici |

Quand le Codex se sert de la clé du site, il passe par `/api/codex`, qui écrit
ses propres consignes et n'accepte que les cinq noms d'outils connus : la clé du
propriétaire ne devient pas un passe-partout.

Les images jointes avec le **+** passent par `/api/chat` en format simple
(`{type, data}`) : c'est le serveur qui bâtit les blocs pour Claude, jamais le
navigateur. Il garde seulement du JPEG, PNG, WebP ou GIF en vrai base64, 4 par
question pis 12 par demande au plus ; le reste est laissé de côté.

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

Marceau connaît son propre numéro de version (`VERSION`, en haut du script).
Les deux versions se mettent à jour toutes seules, chacune à sa manière.

### La version de bureau

La mise à jour est **allumée par défaut** : quand une nouvelle version existe,
elle s'installe toute seule, sans rien demander. L'application revérifie au
démarrage **et aux `HEURES_MAJ` heures** (6 par défaut), pour que ça marche
même si tu la laisses ouverte des jours.

Au démarrage, en arrière-plan, l'application va lire le `ecriture.py` publié sur
GitHub et compare les deux numéros. S'il y a du neuf :

1. elle **vérifie que le code téléchargé compile** — un fichier brisé est refusé
   avant qu'il touche à quoi que ce soit ;
2. elle **garde ton ancienne version** à côté, sous `ecriture_precedent.py` ;
3. elle **remplace le fichier d'un seul coup** (`os.replace`), jamais en deux
   morceaux : il n'y a pas d'instant où le script est à moitié écrit.

Puis elle te dit de redémarrer. Elle ne redémarre jamais toute seule pendant que
t'écris.

L'adresse est **écrite en dur dans le script** : Marceau ne téléchargera jamais
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

## La police de ton système

Marceau écrit avec **la même police que ton ordi**. Au démarrage, elle la
demande au système, dans cet ordre :

1. **GNOME, Ubuntu, Cinnamon, Budgie** — `gsettings` (la police de l'interface,
   pis celle du code) ;
2. **KDE** — `~/.config/kdeglobals` ;
3. **partout ailleurs** — `fc-match sans-serif` et `fc-match monospace`.

Elle prend la première que Tkinter connaît pour vrai ; une police annoncée
mais pas installée est sautée. Tout suit : le texte, les boutons, les menus,
les fenêtres de dialogue, l'éditeur du Codex (avec la police de code du
système), pis le texte que le Studio écrit sur les images. Si rien ne répond,
c'est `DejaVu Sans`, qui est sur presque tous les Linux.

La version web fait pareil avec `system-ui` : la police d'Ubuntu, de Windows,
de macOS ou d'Android, selon l'appareil.

Seul le **PDF** garde Helvetica : c'est la police intégrée au format, celle qui
s'affiche pareil partout sans rien embarquer dans le fichier.

## Le mode nuit

Dans le menu ☰, **☾ Mode nuit** met l'écran **tout noir**, pis le texte en
**vert lime**. Les boutons gardent **le même orange**, avec leur texte noir pour
bien se lire. Un autre clic sur **☼ Mode jour** ramène le gris mat.

Ça marche partout : le chat, le Codex, les cartes de fichiers, les schémas, la
météo, les fenêtres pis les menus. Marceau s'en souvient pis se rouvre dans le
même mode : sur l'ordi, c'est gardé dans `~/.config/ecriture/reglages.json`;
sur le web, dans ton navigateur. Sur le web, la page est noire dès
l'ouverture (pas de flash gris), pis la barre du téléphone devient noire aussi.

Pour changer les couleurs de nuit : en haut d'`ecriture.py` (`VERT_NUIT`,
`FONDS_NUIT`, `TEXTES_NUIT`) pis à la fin d'`app/ecriture.css`.

## Personnaliser

Les couleurs, les polices et les proportions sont regroupées en haut de
`ecriture.py` :

- `GRIS_FOND`, `GRIS_ZONE`, `GRIS_BORD`, `NOIR`, `ORANGE`, `ORANGE_FONCE`
- `LIME`, `LIME_LUEUR`, `GRIS_BOITE`, `GRIS_LIEN` — les couleurs des schémas
- `POLICE_PERSO`, `POLICE_CODE_PERSO` — vides par défaut : l'app prend la police
  de ton système (voir plus bas). Écris un nom de police pour en forcer une.
- `FAMILLE`, `FAMILLE_CODE` — les polices de secours, si on n'en trouve aucune
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
