# marceau-78

**Écriture** — un espace d'écriture minimaliste en Python/Tkinter.

La zone de saisie démarre au centre de la fenêtre. Dès la première ligne envoyée,
elle glisse vers le bas et le texte déjà écrit apparaît au-dessus, dans un
document que l'on peut relire et modifier librement.

Thème gris mat, texte noir, boutons orange.

## Lancer

```bash
python3 ecriture.py
```

Aucune dépendance à installer : seule la bibliothèque standard est utilisée.
Tkinter est généralement livré avec Python ; sur Debian/Ubuntu, s'il manque :

```bash
sudo apt install python3-tk
```

## Utilisation

| Action | Raccourci |
| --- | --- |
| Ajouter la ligne au document | `Entrée` (ou le bouton **Écrire**) |
| Saut de ligne dans la saisie | `Maj` + `Entrée` |
| Sauvegarder dans un fichier | `Ctrl` + `S` (ou le bouton **Sauvegarder**) |
| Repartir de zéro | bouton **Nouveau** |

Le document du haut est éditable : on peut y corriger le texte avant de le
sauvegarder. **Nouveau** demande confirmation si du texte est présent, efface
tout et ramène la saisie au centre.

## Personnaliser

Les couleurs, les polices et les proportions sont regroupées en haut de
`ecriture.py` :

- `GRIS_FOND`, `GRIS_ZONE`, `GRIS_BORD`, `NOIR`, `ORANGE`, `ORANGE_FONCE`
- `POLICE`, `POLICE_BOUTON`, `POLICE_INVITE`
- `MARGE` (espace sous la saisie), `LARGEUR` (largeur des zones, en fraction de
  la fenêtre), `HAUT_DOC` (hauteur à laquelle commence le document)
