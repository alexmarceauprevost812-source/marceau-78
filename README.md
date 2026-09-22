# marceau-78

**Écriture** — un espace d'écriture minimaliste en Python/Tkinter, doublé d'un
assistant qui répond aux questions et cherche sur le web.

La zone de saisie démarre au centre de la fenêtre. Dès la première question
envoyée, elle glisse vers le bas et la conversation apparaît au-dessus, dans un
document que l'on peut relire, modifier et sauvegarder.

Thème gris mat, texte noir, boutons orange.

## Lancer

```bash
python3 ecriture.py
```

Aucune dépendance à installer : seule la bibliothèque standard est utilisée
(l'appel à l'API passe par `urllib`). Tkinter est généralement livré avec
Python ; sur Debian/Ubuntu, s'il manque :

```bash
sudo apt install python3-tk
```

## Clé API

L'assistant appelle l'API Claude, qui est payante. Il faut une clé
(`sk-ant-…`) obtenue sur <https://console.anthropic.com>.

À la première question, l'application la demande et l'enregistre dans
`~/.config/ecriture/cle_api`, en clair, avec les droits `600` (lisible
uniquement par ton compte). Le bouton **Clé API** permet de la changer.

Si aucun fichier n'existe, la variable d'environnement `ANTHROPIC_API_KEY` est
utilisée à la place :

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Utilisation

| Action | Raccourci |
| --- | --- |
| Envoyer la question | `Entrée` (ou le bouton **Envoyer**) |
| Saut de ligne dans la saisie | `Maj` + `Entrée` |
| Sauvegarder la conversation | `Ctrl` + `S` (ou le bouton **Sauvegarder**) |
| Repartir de zéro | bouton **Nouveau** |

L'assistant garde le fil de la conversation et fait une recherche web quand la
question porte sur l'actualité, des prix, des horaires ou la météo. Les sources
citées s'affichent sous la réponse ; un clic ouvre le lien dans le navigateur.

Pendant qu'une réponse arrive, « Réflexion en cours… » s'anime et la saisie est
mise en pause. L'appel tourne dans un fil séparé pour que la fenêtre reste
réactive. **Nouveau** efface la conversation, remet la saisie au centre et
ignore la réponse en cours si elle arrive après coup.

Le document du haut est éditable : on peut y corriger le texte avant de le
sauvegarder en `.txt`.

## Personnaliser

Les couleurs, les polices et les proportions sont regroupées en haut de
`ecriture.py` :

- `GRIS_FOND`, `GRIS_ZONE`, `GRIS_BORD`, `NOIR`, `ORANGE`, `ORANGE_FONCE`
- `FAMILLE`, `POLICE`, `POLICE_BOUTON`, `POLICE_INVITE`
- `MARGE` (espace sous la saisie), `LARGEUR` (largeur des zones, en fraction de
  la fenêtre), `HAUT_DOC` (hauteur à laquelle commence le document)

Juste en dessous, les réglages de l'assistant :

- `MODELE` — le modèle appelé (`claude-sonnet-5`)
- `RECHERCHES_MAX` — nombre maximum de recherches web par question
- `FICHIER_CLE` — où la clé est rangée
- `instructions_systeme()` — le ton et les consignes données à l'assistant
