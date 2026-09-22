#!/usr/bin/env python3
# Écriture — espace d'écriture minimaliste (Tkinter, marche sur Linux)
# Thème gris mat, texte noir, boutons orange.
# Lancer : python3 ecriture.py

import os
import tkinter as tk
from tkinter import filedialog, messagebox

# ---------- Couleurs & style (change-les ici) ----------
GRIS_FOND = "#8c8c8c"      # fond gris mat
GRIS_ZONE = "#a6a6a6"      # zones d'écriture, un peu plus pâles
GRIS_BORD = "#7a7a7a"      # contour des zones
NOIR = "#000000"
ORANGE = "#ff7a1a"
ORANGE_FONCE = "#e0620a"   # orange quand on clique

POLICE = ("DejaVu Sans", 14)
POLICE_BOUTON = ("DejaVu Sans", 11, "bold")
POLICE_INVITE = ("DejaVu Sans", 18)

MARGE = 25        # espace entre la zone d'écriture et le bas de l'écran
LARGEUR = 0.65    # largeur des zones (65 % de la fenêtre)
HAUT_DOC = 70     # où commence le texte en haut de l'écran


def bouton_orange(parent, texte, commande):
    return tk.Button(
        parent, text=texte, command=commande,
        bg=ORANGE, fg=NOIR, activebackground=ORANGE_FONCE, activeforeground=NOIR,
        font=POLICE_BOUTON, relief="flat", bd=0, highlightthickness=0,
        padx=16, pady=8, cursor="hand2",
    )


def style_zone():
    return dict(
        bg=GRIS_ZONE, fg=NOIR, insertbackground=NOIR,
        selectbackground=ORANGE, selectforeground=NOIR,
        font=POLICE, relief="flat", bd=0, wrap="word",
        highlightthickness=2, highlightbackground=GRIS_BORD, highlightcolor=ORANGE,
        padx=14, pady=10,
    )


class AppEcriture(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Écriture")
        self.geometry("1000x700")
        self.minsize(600, 400)
        self.configure(bg=GRIS_FOND)

        self.premiere_ligne = True
        self.en_animation = False

        # --- Boutons du haut (cachés au début) ---
        self.barre = tk.Frame(self, bg=GRIS_FOND)
        bouton_orange(self.barre, "Sauvegarder", self.sauvegarder).pack(side="left", padx=(0, 10))
        bouton_orange(self.barre, "Nouveau", self.nouveau).pack(side="left")

        # --- Le texte écrit, au-dessus (caché au début, modifiable) ---
        self.document = tk.Text(self, **style_zone())

        # --- La zone où on écrit (centrée au début) ---
        self.zone_saisie = tk.Frame(self, bg=GRIS_FOND)
        self.invite = tk.Label(self.zone_saisie, text="Commence à écrire…",
                               bg=GRIS_FOND, fg=NOIR, font=POLICE_INVITE)
        self.invite.pack(pady=(0, 14))

        self.ligne = tk.Frame(self.zone_saisie, bg=GRIS_FOND)
        self.ligne.pack(fill="x")
        bouton_orange(self.ligne, "Écrire", self.ajouter_ligne).pack(
            side="right", padx=(10, 0), fill="y")
        self.saisie = tk.Text(self.ligne, height=2, width=1, **style_zone())
        self.saisie.pack(side="left", fill="x", expand=True)

        # Entrée = ajoute la ligne, Shift+Entrée = saut de ligne, Ctrl+S = sauvegarder
        self.saisie.bind("<Return>", self.ajouter_ligne)
        self.saisie.bind("<Shift-Return>", self.saut_de_ligne)
        self.bind("<Control-s>", lambda e: self.sauvegarder())

        self.centrer_saisie()
        self.saisie.focus_set()

    # ---------- Positions ----------
    def centrer_saisie(self):
        self.zone_saisie.place(relx=0.5, rely=0.5, y=0, anchor="center", relwidth=LARGEUR)

    def saisie_en_bas(self):
        self.zone_saisie.place(relx=0.5, rely=1.0, y=-MARGE, anchor="s", relwidth=LARGEUR)

    def afficher_document(self):
        self.update_idletasks()
        h_saisie = self.zone_saisie.winfo_height()
        self.document.place(relx=0.5, y=HAUT_DOC, anchor="n", relwidth=LARGEUR,
                            relheight=1.0, height=-(HAUT_DOC + h_saisie + MARGE + 15))
        self.barre.place(relx=1.0, x=-20, y=15, anchor="ne")
        self.document.see("end")

    # ---------- La descente vers le bas ----------
    def descendre(self):
        self.en_animation = True
        self.invite.pack_forget()
        self.update_idletasks()
        h_fenetre = self.winfo_height()
        h_saisie = self.zone_saisie.winfo_height()
        depart = 0.5
        cible = 1 - (h_saisie / 2 + MARGE) / h_fenetre
        etapes = 24

        def pas(i):
            t = i / etapes
            t = 1 - (1 - t) ** 3  # ralentit en arrivant en bas
            self.zone_saisie.place_configure(rely=depart + (cible - depart) * t)
            if i < etapes:
                self.after(12, pas, i + 1)
            else:
                self.saisie_en_bas()
                self.afficher_document()
                self.en_animation = False

        pas(1)

    # ---------- Actions ----------
    def ajouter_ligne(self, event=None):
        if self.en_animation:
            return "break"
        texte = self.saisie.get("1.0", "end-1c")
        if not texte.strip():
            return "break"
        self.document.insert("end", texte.rstrip() + "\n")
        self.document.see("end")
        self.saisie.delete("1.0", "end")
        if self.premiere_ligne:
            self.premiere_ligne = False
            self.descendre()
        return "break"

    def saut_de_ligne(self, event=None):
        self.saisie.insert("insert", "\n")
        return "break"

    def sauvegarder(self):
        contenu = self.document.get("1.0", "end-1c")
        if not contenu.strip():
            messagebox.showinfo("Sauvegarder", "Écris au moins une ligne avant de sauvegarder.")
            return
        chemin = filedialog.asksaveasfilename(
            title="Sauvegarder", defaultextension=".txt",
            filetypes=[("Texte", "*.txt"), ("Tous les fichiers", "*.*")])
        if chemin:
            with open(chemin, "w", encoding="utf-8") as f:
                f.write(contenu)
            self.title(f"Écriture — {os.path.basename(chemin)}")

    def nouveau(self):
        if self.document.get("1.0", "end-1c").strip():
            if not messagebox.askyesno("Nouveau", "Effacer le texte et recommencer?"):
                return
        self.document.delete("1.0", "end")
        self.document.place_forget()
        self.barre.place_forget()
        self.invite.pack(pady=(0, 14), before=self.ligne)
        self.premiere_ligne = True
        self.title("Écriture")
        self.centrer_saisie()
        self.saisie.focus_set()


if __name__ == "__main__":
    AppEcriture().mainloop()
