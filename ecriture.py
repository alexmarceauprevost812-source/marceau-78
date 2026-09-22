#!/usr/bin/env python3
# Écriture — espace d'écriture + assistant IA
#   - IA gratuites en local avec Ollama (mistral, llama, qwen, gemma, deepseek…)
#   - Claude + recherche web (payant, clé API)
# Thème gris mat, texte noir, boutons orange.
# Rien à installer à part python3-tk. Lancer : python3 ecriture.py

import datetime
import json
import math
import os
import queue
import re
import threading
import tkinter as tk
from tkinter import font as tkfont
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

# ---------- Fichiers ----------
DOSSIER = Path(__file__).resolve().parent
LOGO = DOSSIER / "logo.png"                  # le logo, en 512 px
LOGO_PETIT = DOSSIER / "logo_64.png"         # le même en petit, pour la barre des tâches
LOGO_ACCUEIL = DOSSIER / "logo_accueil.png"  # découpé en rond, pour l'accueil

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

RAYON_BOUTON = 11  # arrondi des boutons
RAYON_ZONE = 16    # arrondi des zones d'écriture

MARGE = 25        # espace entre la zone d'écriture et le bas de l'écran
LARGEUR = 0.70    # largeur des zones (70 % de la fenêtre)
HAUT_DOC = 70     # où commence le texte en haut de l'écran

# ---------- Réglages des IA ----------
MODELE_CLAUDE = "claude-sonnet-5"
URL_CLAUDE = "https://api.anthropic.com/v1/messages"
URL_OLLAMA = "http://localhost:11434"
FICHIER_CLE = Path.home() / ".config" / "ecriture" / "cle_api"
RECHERCHES_MAX = 5                     # recherches web max par question (Claude)
NOM_CLAUDE = "Claude + web (payant)"   # nom affiché dans le menu


def instructions_systeme(web):
    aujourdhui = datetime.date.today().isoformat()
    texte = (
        "Tu es l'assistant intégré à une application d'écriture. "
        "Réponds en français, de façon claire et directe. "
        "Écris seulement en texte brut : pas de Markdown, pas d'astérisques, "
        "pas de dièses, pas de tableaux. Pour une liste, utilise des tirets simples. "
    )
    if web:
        texte += ("Fais une recherche web dès que la question touche l'actualité, des prix, "
                  "des horaires, la météo, des personnes ou n'importe quoi qui a pu changer récemment. ")
    else:
        texte += ("Tu n'as pas accès à Internet. Si la question demande des infos récentes "
                  "(actualité, météo, prix, horaires), dis-le franchement au lieu d'inventer "
                  f"et suggère de choisir « {NOM_CLAUDE} » dans le menu. ")
    return texte + f"Date d'aujourd'hui : {aujourdhui}."


# ---------- Clé API Claude ----------
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


# ---------- Ollama (gratuit, local) ----------
def modeles_ollama():
    """Liste les modèles installés dans Ollama (vide si Ollama roule pas)."""
    try:
        with urllib.request.urlopen(URL_OLLAMA + "/api/tags", timeout=2) as rep:
            data = json.loads(rep.read().decode("utf-8"))
        noms = [m["name"] for m in data.get("models", [])]
        return sorted(n for n in noms if "embed" not in n)  # les modèles « embed » jasent pas
    except Exception:
        return []


def appeler_ollama(modele, historique):
    corps = {
        "model": modele,
        "stream": False,
        "messages": [{"role": "system", "content": instructions_systeme(web=False)}] + historique,
    }
    requete = urllib.request.Request(
        URL_OLLAMA + "/api/chat", data=json.dumps(corps).encode("utf-8"), method="POST",
        headers={"content-type": "application/json"})
    with urllib.request.urlopen(requete, timeout=600) as rep:
        data = json.loads(rep.read().decode("utf-8"))
    texte = data.get("message", {}).get("content", "")
    # Certains modèles (deepseek-r1, qwen3) écrivent leur réflexion entre <think> : on l'enlève
    texte = re.sub(r"<think>.*?</think>", "", texte, flags=re.S).strip()
    return texte, []


# ---------- Claude + recherche web (payant) ----------
def appeler_claude(cle, historique):
    conversation = list(historique)
    morceaux, sources = [], []
    for _ in range(5):
        corps = {
            "model": MODELE_CLAUDE,
            "max_tokens": 2048,
            "system": instructions_systeme(web=True),
            "messages": conversation,
            "tools": [{"type": "web_search_20250305", "name": "web_search",
                       "max_uses": RECHERCHES_MAX}],
        }
        requete = urllib.request.Request(
            URL_CLAUDE, data=json.dumps(corps).encode("utf-8"), method="POST",
            headers={"x-api-key": cle, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"})
        with urllib.request.urlopen(requete, timeout=180) as rep:
            data = json.loads(rep.read().decode("utf-8"))

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


def message_erreur(err, type_moteur, modele):
    ollama = type_moteur == "ollama"
    if isinstance(err, urllib.error.HTTPError):
        detail = ""
        try:
            e = json.loads(err.read().decode("utf-8")).get("error")
            detail = e.get("message", "") if isinstance(e, dict) else str(e or "")
        except Exception:
            pass
        if ollama:
            if err.code == 404:
                return f"Le modèle « {modele} » n'est pas installé. Dans un terminal : ollama pull {modele}"
            return f"Ollama a renvoyé l'erreur {err.code} : {detail or err.reason}"
        if err.code == 401:
            return "Clé API invalide. Clique sur « Clé API » en haut pour la changer."
        if err.code == 429:
            return "Trop de questions d'un coup. Attends quelques secondes et réessaie."
        if err.code in (500, 529):
            return "Le service est surchargé en ce moment. Réessaie dans un instant."
        return f"Erreur {err.code} : {detail or err.reason}"
    if isinstance(err, urllib.error.URLError):
        if ollama:
            return "Ollama ne répond pas. Démarre-le dans un terminal avec : ollama serve"
        return "Pas de connexion Internet. Vérifie ton réseau et réessaie."
    if isinstance(err, TimeoutError):
        return "La réponse a pris trop de temps. Réessaie, ou prends un modèle plus léger."
    return f"Erreur : {err}"


# ---------- Interface ----------
def bouton_orange(parent, texte, commande):
    return BoutonRond(parent, texte, commande)


def style_zone():
    return dict(
        bg=GRIS_ZONE, fg=NOIR, insertbackground=NOIR,
        selectbackground=ORANGE, selectforeground=NOIR,
        font=POLICE, relief="flat", bd=0, wrap="word",
        highlightthickness=0,   # le contour arrondi est dessiné par ZoneRonde
        padx=14, pady=10,
    )


# ---------- Coins ronds ----------
# Tkinter sait pas arrondir un bouton ni une boîte de texte : on dessine la
# forme sur un Canvas, et pour le texte on pose le widget par-dessus, en retrait.

def points_arrondis(x1, y1, x2, y2, r, pas=10):
    """Le contour d'un rectangle à coins ronds, pour create_polygon."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    points = []
    coins = ((x2 - r, y1 + r, -90), (x2 - r, y2 - r, 0),
             (x1 + r, y2 - r, 90), (x1 + r, y1 + r, 180))
    for cx, cy, depart in coins:
        for i in range(pas + 1):
            angle = math.radians(depart + 90 * i / pas)
            points.extend((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return points


class BoutonRond(tk.Canvas):
    """Un bouton orange à coins ronds, dessiné à la main."""

    def __init__(self, parent, texte, commande, police=POLICE_BOUTON,
                 rayon=RAYON_BOUTON, padx=16, pady=8):
        self.police = tkfont.Font(font=police)
        self.padx, self.rayon, self.commande = padx, rayon, commande
        larg = self.police.measure(texte) + 2 * padx
        haut = self.police.metrics("linespace") + 2 * pady
        super().__init__(parent, width=larg, height=haut, bg=parent["bg"],
                         highlightthickness=0, bd=0, cursor="hand2", takefocus=0)
        self.forme = self.create_polygon(points_arrondis(0, 0, larg, haut, rayon),
                                         fill=ORANGE, outline="")
        self.etiquette = self.create_text(larg / 2, haut / 2, text=texte,
                                          fill=NOIR, font=self.police)
        self.bind("<Configure>", self.redessiner)
        self.bind("<ButtonPress-1>", lambda e: self.itemconfig(self.forme, fill=ORANGE_FONCE))
        self.bind("<ButtonRelease-1>", self.relacher)
        self.bind("<Leave>", lambda e: self.itemconfig(self.forme, fill=ORANGE))

    def redessiner(self, event=None):
        larg, haut = self.winfo_width(), self.winfo_height()
        self.coords(self.forme, *points_arrondis(0, 0, larg, haut, self.rayon))
        self.coords(self.etiquette, larg / 2, haut / 2)

    def relacher(self, event):
        self.itemconfig(self.forme, fill=ORANGE)
        # on déclenche seulement si on relâche encore sur le bouton
        if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self.commande()

    def changer_texte(self, texte):
        self.itemconfig(self.etiquette, text=texte)
        self.config(width=self.police.measure(texte) + 2 * self.padx)


class MenuRond(BoutonRond):
    """Même bouton, mais qui fait apparaître un menu au-dessus de lui."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, kwargs.pop("texte", " "), self.ouvrir, **kwargs)
        self.menu = None

    def ouvrir(self):
        if self.menu is None:
            return
        self.menu.update_idletasks()
        self.menu.post(self.winfo_rootx(),
                       self.winfo_rooty() - self.menu.winfo_reqheight())


class ZoneRonde(tk.Frame):
    """Un tk.Text posé dans un rectangle à coins ronds. Le Text est dans .texte"""

    def __init__(self, parent, rayon=RAYON_ZONE, lignes=None, **options_texte):
        super().__init__(parent, bg=parent["bg"])
        self.rayon = rayon
        self.fond = tk.Canvas(self, bg=parent["bg"], highlightthickness=0, bd=0)
        self.fond.pack(fill="both", expand=True)
        self.forme = self.fond.create_polygon((0, 0, 0, 0, 0, 0), fill=GRIS_ZONE,
                                              outline=GRIS_BORD, width=2)
        # un coin carré rentre dans l'arrondi à partir de 0,3 fois le rayon : on prend large
        self.retrait = int(rayon * 0.38) + 2
        self.texte = tk.Text(self, **options_texte)
        self.texte.place(x=self.retrait, y=self.retrait, relwidth=1.0, relheight=1.0,
                         width=-2 * self.retrait, height=-2 * self.retrait)
        if lignes:   # hauteur fixe : le Text est en place(), il pousse pas le cadre
            police = tkfont.Font(font=options_texte.get("font", POLICE))
            self.config(height=lignes * police.metrics("linespace")
                        + 2 * options_texte.get("pady", 0) + 2 * self.retrait + 4)
            self.pack_propagate(False)
        self.fond.bind("<Configure>", self.redessiner)
        self.texte.bind("<FocusIn>", lambda e: self.fond.itemconfig(self.forme, outline=ORANGE))
        self.texte.bind("<FocusOut>", lambda e: self.fond.itemconfig(self.forme, outline=GRIS_BORD))
        # cliquer sur la marge arrondie donne quand même le curseur au texte
        self.fond.bind("<Button-1>", lambda e: self.texte.focus_set())

    def redessiner(self, event=None):
        larg, haut = self.fond.winfo_width(), self.fond.winfo_height()
        self.fond.coords(self.forme, *points_arrondis(1, 1, larg - 1, haut - 1, self.rayon))


class AppEcriture(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Écriture")
        self.geometry("1000x700")
        self.minsize(720, 450)
        self.configure(bg=GRIS_FOND)
        self.mettre_icone()

        self.premiere_ligne = True
        self.en_animation = False
        self.occupe = False          # une réponse est en route
        self.generation = 0          # change à chaque « Nouveau »
        self.historique = []         # la conversation envoyée à l'IA
        self.resultats = queue.Queue()
        self.compteur = 0
        self.nb_liens = 0
        self.texte_attente = ""

        # --- Boutons du haut (cachés au début) ---
        self.barre = tk.Frame(self, bg=GRIS_FOND)
        bouton_orange(self.barre, "Clé API", self.changer_cle).pack(side="left", padx=(0, 10))
        bouton_orange(self.barre, "Sauvegarder", self.sauvegarder).pack(side="left", padx=(0, 10))
        bouton_orange(self.barre, "Nouveau", self.nouveau).pack(side="left")

        # --- La conversation, au-dessus (cachée au début, modifiable) ---
        self.cadre_document = ZoneRonde(self, **style_zone())
        self.document = self.cadre_document.texte
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
        self.logo_accueil = self.creer_logo_accueil()

        self.ligne = tk.Frame(self.zone_saisie, bg=GRIS_FOND)
        self.ligne.pack(fill="x")
        bouton_orange(self.ligne, "Envoyer", self.envoyer).pack(
            side="right", padx=(10, 0), fill="y")

        self.cadre_saisie = ZoneRonde(self.ligne, lignes=2, **style_zone())
        self.saisie = self.cadre_saisie.texte
        self.cadre_saisie.pack(side="left", fill="x", expand=True)

        # Choix de l'IA, sous la boîte (les modèles Ollama gratuits en premier)
        self.options = tk.Frame(self.zone_saisie, bg=GRIS_FOND)
        self.options.pack(fill="x", pady=(8, 0))
        self.moteurs = self.trouver_moteurs()
        self.choix = tk.StringVar()
        self.bouton_moteur = MenuRond(
            self.options, police=(FAMILLE, 10, "bold"), rayon=9, padx=12, pady=5)
        self.menu_moteur = tk.Menu(
            self.bouton_moteur, tearoff=0, bg=GRIS_ZONE, fg=NOIR,
            activebackground=ORANGE, activeforeground=NOIR, font=(FAMILLE, 11),
            bd=0, relief="flat",
            postcommand=self.rafraichir_moteurs)  # relit Ollama chaque fois qu'on ouvre le menu
        self.bouton_moteur.menu = self.menu_moteur
        self.bouton_moteur.pack(side="left")
        self.choix.trace_add("write", lambda *a: self.bouton_moteur.changer_texte(
            f"{self.choix.get()}  ▾"))
        self.rafraichir_moteurs(premiere_fois=True)

        # Entrée = envoyer, Shift+Entrée = saut de ligne, Ctrl+S = sauvegarder
        self.saisie.bind("<Return>", self.envoyer)
        self.saisie.bind("<Shift-Return>", self.saut_de_ligne)
        self.bind("<Control-s>", lambda e: self.sauvegarder())

        self.montrer_accueil()
        self.centrer_saisie()
        self.saisie.focus_set()

    # ---------- Icône et logo ----------
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

    def creer_logo_accueil(self):
        """Le logo rond montré au-dessus de l'invite, tant qu'on a rien demandé."""
        if not LOGO_ACCUEIL.exists():
            return None
        try:
            self.image_accueil = tk.PhotoImage(file=str(LOGO_ACCUEIL))
        except tk.TclError:
            return None
        return tk.Label(self.zone_saisie, image=self.image_accueil, bg=GRIS_FOND)

    def montrer_accueil(self):
        self.invite.pack(pady=(0, 14), before=self.ligne)
        if self.logo_accueil is not None:
            self.logo_accueil.pack(pady=(0, 12), before=self.invite)

    def cacher_accueil(self):
        self.invite.pack_forget()
        if self.logo_accueil is not None:
            self.logo_accueil.pack_forget()

    # ---------- Choix de l'IA ----------
    def trouver_moteurs(self):
        moteurs = {}
        for nom in modeles_ollama():
            court = nom.removesuffix(":latest")
            moteurs[f"{court} (gratuit)"] = ("ollama", nom)
        moteurs[NOM_CLAUDE] = ("claude", MODELE_CLAUDE)
        return moteurs

    def rafraichir_moteurs(self, premiere_fois=False):
        if not premiere_fois:
            self.moteurs = self.trouver_moteurs()
        self.menu_moteur.delete(0, "end")
        for etiquette in self.moteurs:
            self.menu_moteur.add_command(
                label=etiquette, command=lambda e=etiquette: self.choix.set(e))
        if self.choix.get() not in self.moteurs:
            self.choix.set(next(iter(self.moteurs)))

    # ---------- Positions ----------
    def centrer_saisie(self):
        self.zone_saisie.place(relx=0.5, rely=0.5, y=0, anchor="center", relwidth=LARGEUR)

    def saisie_en_bas(self):
        self.zone_saisie.place(relx=0.5, rely=1.0, y=-MARGE, anchor="s", relwidth=LARGEUR)

    def afficher_document(self):
        self.update_idletasks()
        h_saisie = self.zone_saisie.winfo_height()
        self.cadre_document.place(relx=0.5, y=HAUT_DOC, anchor="n", relwidth=LARGEUR,
                                  relheight=1.0, height=-(HAUT_DOC + h_saisie + MARGE + 15))
        self.barre.place(relx=1.0, x=-20, y=15, anchor="ne")
        self.document.see("end")

    # ---------- La descente vers le bas ----------
    def descendre(self):
        self.en_animation = True
        self.cacher_accueil()
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
        moteur = self.moteurs.get(self.choix.get())
        if moteur is None:
            return "break"
        cle = ""
        if moteur[0] == "claude":
            cle = lire_cle() or self.demander_cle()
            if not cle:
                return "break"

        self.saisie.delete("1.0", "end")
        self.document.insert("end", texte + "\n", "question")
        self.historique.append({"role": "user", "content": texte})
        nom = "Claude" if moteur[0] == "claude" else moteur[1].removesuffix(":latest")
        self.montrer_attente(nom)
        self.occupe = True
        threading.Thread(target=self.travail,
                         args=(moteur, cle, list(self.historique), self.generation),
                         daemon=True).start()
        self.after(100, self.verifier_resultat)

        if self.premiere_ligne:
            self.premiere_ligne = False
            self.descendre()
        self.document.see("end")
        return "break"

    def travail(self, moteur, cle, historique, generation):
        # Roule dans un fil à part pour que la fenêtre gèle pas pendant que l'IA réfléchit
        type_moteur, modele = moteur
        try:
            if type_moteur == "claude":
                texte, sources = appeler_claude(cle, historique)
            else:
                texte, sources = appeler_ollama(modele, historique)
            self.resultats.put((generation, "ok", texte, sources))
        except Exception as err:
            self.resultats.put((generation, "erreur", message_erreur(err, type_moteur, modele), []))

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

    def montrer_attente(self, nom):
        self.compteur = 0
        self.texte_attente = f"{nom} réfléchit"
        self.document.insert("end", self.texte_attente + "\n", "attente")

    def animer_attente(self):
        self.compteur += 1
        if self.compteur % 4:
            return
        points = "." * ((self.compteur // 4) % 4)
        zone = self.document.tag_ranges("attente")
        if zone:
            self.document.delete(zone[0], zone[1])
            self.document.insert(zone[0], f"{self.texte_attente}{points}\n", "attente")

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
        self.cadre_document.place_forget()
        self.barre.place_forget()
        self.montrer_accueil()
        self.premiere_ligne = True
        self.title("Écriture")
        self.centrer_saisie()
        self.saisie.focus_set()


if __name__ == "__main__":
    AppEcriture().mainloop()
