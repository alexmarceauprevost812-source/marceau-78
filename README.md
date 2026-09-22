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
| `index.html` | la page de présentation publiée sur Vercel |
| `vercel.json` | fait télécharger `ecriture.py` au lieu de l'afficher |
| `captures/` | les captures d'écran utilisées par la page |

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
