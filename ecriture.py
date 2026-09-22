#!/usr/bin/env python3
# Écriture — espace d'écriture + assistant qui répond aux questions et cherche sur le web
# Thème gris mat, texte noir, boutons orange.
# Rien à installer à part python3-tk. Lancer : python3 ecriture.py

import datetime
import json
import os
import queue
import threading
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

# ---------- Fichiers ----------
DOSSIER = Path(__file__).resolve().parent
LOGO = DOSSIER / "logo.png"           # le logo, en 512 px
LOGO_PETIT = DOSSIER / "logo_64.png"  # le même en petit, pour la barre des tâches

# ---------- Couleurs & style (change-les ici) ----------
GRIS_FOND = "#8c8c8c"      # fond gris mat
GRIS_ZONE = "#a6a6a6"      # zones d'écriture, un peu plus pâles
GRIS_BORD = "#7a7a7a"      # contour des zones
NOIR = "#000000"
ORANGE = "#ff7a1a"
ORANGE_FONCE = "#e0620a"   # orange quand on clique

FAMILLE = "DejaVu Sans"
POLICE = (FAMILLE, 14)
POLICE_BOUTON = (FAMILLE, 11, "bold")
POLICE_INVITE = (FAMILLE, 18)

MARGE = 25        # espace entre la zone d'écriture et le bas de l'écran
LARGEUR = 0.65    # largeur des zones (65 % de la fenêtre)
HAUT_DOC = 70     # où commence le texte en haut de l'écran

# ---------- Réglages de l'IA ----------
MODELE = "claude-sonnet-5"
URL_API = "https://api.anthropic.com/v1/messages"
FICHIER_CLE = Path.home() / ".config" / "ecriture" / "cle_api"
RECHERCHES_MAX = 5   # nombre max de recherches web par question


def instructions_systeme():
    aujourdhui = datetime.date.today().isoformat()
    return (
        "Tu es l'assistant intégré à une application d'écriture. "
        "Réponds en français, de façon claire et directe. "
        "Écris seulement en texte brut : pas de Markdown, pas d'astérisques, "
        "pas de dièses, pas de tableaux. Pour une liste, utilise des tirets simples. "
        "Fais une recherche web dès que la question touche l'actualité, des prix, "
        "des horaires, la météo, des personnes ou n'importe quoi qui a pu changer récemment. "
        f"Date d'aujourd'hui : {aujourdhui}."
    )


# ---------- Clé API ----------
def lire_cle():
    if FICHIER_CLE.exists():
        cle = FICHIER_CLE.read_text(encoding="utf-8").strip()
        if cle:
            return cle
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def enregistrer_cle(cle):
    FICHIER_CLE.parent.mkdir(parents=True, exist_ok=True)
    FICHIER_CLE.write_text(cle, encoding="utf-8")
    os.chmod(FICHIER_CLE, 0o600)   # lisible juste par toi


# ---------- Appel à Claude (roule en arrière-plan) ----------
def appeler_claude(cle, historique):
    """Envoie la conversation à Claude avec la recherche web. Retourne (texte, sources)."""
    conversation = list(historique)
    morceaux, sources = [], []
    for _ in range(5):
        corps = {
            "model": MODELE,
            "max_tokens": 2048,
            "system": instructions_systeme(),
            "messages": conversation,
            "tools": [{"type": "web_search_20250305", "name": "web_search",
                       "max_uses": RECHERCHES_MAX}],
        }
        requete = urllib.request.Request(
            URL_API, data=json.dumps(corps).encode("utf-8"), method="POST",
            headers={"x-api-key": cle, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"})
        with urllib.request.urlopen(requete, timeout=180) as reponse:
            data = json.loads(reponse.read().decode("utf-8"))

        for bloc in data.get("content", []):
            if bloc.get("type") != "text":
                continue
            morceaux.append(bloc.get("text", ""))
            for citation in bloc.get("citations") or []:
                url = citation.get("url")
                if url and url not in [u for _, u in sources]:
                    sources.append((citation.get("title") or url, url))

        # Longue recherche : l'API met la réponse sur pause, on la relance
        if data.get("stop_reason") == "pause_turn":
            conversation = conversation + [{"role": "assistant", "content": data["content"]}]
            continue
        break
    return "".join(morceaux).strip(), sources


def message_erreur(err):
    if isinstance(err, urllib.error.HTTPError):
        try:
            detail = json.loads(err.read().decode("utf-8"))["error"]["message"]
        except Exception:
            detail = ""
        if err.code == 401:
            return "Clé API invalide. Clique sur « Clé API » en haut pour la changer."
        if err.code == 429:
            return "Trop de questions d'un coup. Attends quelques secondes et réessaie."
        if err.code in (500, 529):
            return "Le service est surchargé en ce moment. Réessaie dans un instant."
        return f"Erreur {err.code} : {detail or err.reason}"
    if isinstance(err, urllib.error.URLError):
        return "Pas de connexion Internet. Vérifie ton réseau et réessaie."
    if isinstance(err, TimeoutError):
        return "La réponse a pris trop de temps. Réessaie."
    return f"Erreur : {err}"


# ---------- Interface ----------
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
        self.mettre_icone()

        self.premiere_ligne = True
        self.en_animation = False
        self.occupe = False          # une réponse est en route
        self.generation = 0          # change à chaque « Nouveau »
        self.historique = []         # la conversation envoyée à Claude
        self.resultats = queue.Queue()
        self.compteur = 0
        self.nb_liens = 0

        # --- Boutons du haut (cachés au début) ---
        self.barre = tk.Frame(self, bg=GRIS_FOND)
        bouton_orange(self.barre, "Clé API", self.changer_cle).pack(side="left", padx=(0, 10))
        bouton_orange(self.barre, "Sauvegarder", self.sauvegarder).pack(side="left", padx=(0, 10))
        bouton_orange(self.barre, "Nouveau", self.nouveau).pack(side="left")

        # --- La conversation, au-dessus (cachée au début, modifiable) ---
        self.document = tk.Text(self, **style_zone())
        self.document.tag_configure("question", font=(FAMILLE, 14, "bold"), spacing1=14)
        self.document.tag_configure("reponse", spacing1=6, spacing3=4)
        self.document.tag_configure("attente", font=(FAMILLE, 14, "italic"), spacing1=6)
        self.document.tag_configure("sources", font=(FAMILLE, 11), spacing1=2)
        self.document.tag_configure("lien", underline=True)
        self.document.tag_bind("lien", "<Enter>", lambda e: self.document.config(cursor="hand2"))
        self.document.tag_bind("lien", "<Leave>", lambda e: self.document.config(cursor="xterm"))

        # --- La zone où on écrit (centrée au début) ---
        self.zone_saisie = tk.Frame(self, bg=GRIS_FOND)
        self.invite = tk.Label(self.zone_saisie, text="Pose une question…",
                               bg=GRIS_FOND, fg=NOIR, font=POLICE_INVITE)
        self.invite.pack(pady=(0, 14))

        self.ligne = tk.Frame(self.zone_saisie, bg=GRIS_FOND)
        self.ligne.pack(fill="x")
        bouton_orange(self.ligne, "Envoyer", self.envoyer).pack(
            side="right", padx=(10, 0), fill="y")
        self.saisie = tk.Text(self.ligne, height=2, width=1, **style_zone())
        self.saisie.pack(side="left", fill="x", expand=True)

        # Entrée = envoyer, Shift+Entrée = saut de ligne, Ctrl+S = sauvegarder
        self.saisie.bind("<Return>", self.envoyer)
        self.saisie.bind("<Shift-Return>", self.saut_de_ligne)
        self.bind("<Control-s>", lambda e: self.sauvegarder())

        self.centrer_saisie()
        self.saisie.focus_set()

    # ---------- Icône de la fenêtre ----------
    def mettre_icone(self):
        # Tk garde pas de référence aux images : on les range sur l'objet.
        # Deux tailles : le gestionnaire de fenêtres prend celle qui lui va.
        self.icones = []
        for chemin in (LOGO_PETIT, LOGO):
            if chemin.exists():
                try:
                    self.icones.append(tk.PhotoImage(file=str(chemin)))
                except tk.TclError:
                    pass   # Tk trop vieux pour lire le PNG : tant pis pour l'icône
        if self.icones:
            self.iconphoto(True, *self.icones)

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

    # ---------- Envoyer une question ----------
    def envoyer(self, event=None):
        if self.en_animation or self.occupe:
            return "break"
        texte = self.saisie.get("1.0", "end-1c").strip()
        if not texte:
            return "break"
        cle = lire_cle() or self.demander_cle()
        if not cle:
            return "break"

        self.saisie.delete("1.0", "end")
        self.document.insert("end", texte + "\n", "question")
        self.historique.append({"role": "user", "content": texte})
        self.montrer_attente()
        self.occupe = True
        threading.Thread(target=self.travail,
                         args=(cle, list(self.historique), self.generation),
                         daemon=True).start()
        self.after(100, self.verifier_resultat)

        if self.premiere_ligne:
            self.premiere_ligne = False
            self.descendre()
        self.document.see("end")
        return "break"

    def travail(self, cle, historique, generation):
        # Roule dans un fil à part pour que la fenêtre gèle pas pendant la recherche
        try:
            texte, sources = appeler_claude(cle, historique)
            self.resultats.put((generation, "ok", texte, sources))
        except Exception as err:
            self.resultats.put((generation, "erreur", message_erreur(err), []))

    def verifier_resultat(self):
        try:
            generation, statut, texte, sources = self.resultats.get_nowait()
        except queue.Empty:
            if self.occupe:
                self.animer_attente()
                self.after(100, self.verifier_resultat)
            return

        if generation != self.generation:
            # Réponse d'une conversation effacée avec « Nouveau » : on l'ignore
            if self.occupe:
                self.after(100, self.verifier_resultat)
            return

        self.occupe = False
        zone = self.document.tag_ranges("attente")
        if zone:
            self.document.delete(zone[0], zone[1])

        if statut == "ok":
            texte = texte or "Pas de réponse cette fois-ci. Reformule ta question."
            self.historique.append({"role": "assistant", "content": texte})
            self.document.insert("end", texte + "\n", "reponse")
            if sources:
                self.document.insert("end", "Sources :\n", "sources")
                for titre, url in sources[:5]:
                    etiquette = f"lien{self.nb_liens}"
                    self.nb_liens += 1
                    self.document.insert("end", "- ", "sources")
                    self.document.insert("end", titre + "\n", ("sources", "lien", etiquette))
                    self.document.tag_bind(etiquette, "<Button-1>",
                                           lambda e, u=url: webbrowser.open(u))
        else:
            self.historique.pop()  # la question a pas eu de réponse, on la retire
            self.document.insert("end", texte + "\n", "reponse")
        self.document.see("end")

    def montrer_attente(self):
        self.compteur = 0
        self.document.insert("end", "Réflexion en cours\n", "attente")

    def animer_attente(self):
        self.compteur += 1
        if self.compteur % 4:
            return
        points = "." * ((self.compteur // 4) % 4)
        zone = self.document.tag_ranges("attente")
        if zone:
            self.document.delete(zone[0], zone[1])
            self.document.insert(zone[0], f"Réflexion en cours{points}\n", "attente")

    def saut_de_ligne(self, event=None):
        self.saisie.insert("insert", "\n")
        return "break"

    # ---------- Clé API ----------
    def demander_cle(self):
        cle = simpledialog.askstring(
            "Clé API", "Colle ta clé API Claude (elle commence par sk-ant-) :",
            show="*", parent=self)
        if cle and cle.strip():
            enregistrer_cle(cle.strip())
            return cle.strip()
        return ""

    def changer_cle(self):
        if self.demander_cle():
            messagebox.showinfo("Clé API", "Clé enregistrée.")

    # ---------- Sauvegarder / Nouveau ----------
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
            if not messagebox.askyesno("Nouveau", "Effacer la conversation et recommencer?"):
                return
        self.generation += 1
        self.occupe = False
        self.historique = []
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
