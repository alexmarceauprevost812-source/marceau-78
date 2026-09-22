#!/usr/bin/env python3
# Écriture — espace d'écriture + assistant IA québécois + Codex GitHub
#   - Menu à gauche (☰) : tes conversations sauvegardées + le Codex
#   - IA gratuites en local avec Ollama, ou Claude + recherche web (payant)
#   - Schémas animés quand l'IA explique un plan d'action
#   - Codex : ouvre un projet GitHub, colore le code, pis l'IA peut le scanner, l'écrire et le corriger
# Rien à installer à part python3-tk. Lancer : python3 ecriture.py

import base64
import datetime
import json
import math
import os
import queue
import random
import re
import threading
import tkinter as tk
import tkinter.font as tkfont
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from bisect import bisect_right
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

try:   # Pillow rend le logo plus doux quand il change de taille (optionnel)
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

# ---------- Couleurs & style (change-les ici) ----------
GRIS_FOND = "#8c8c8c"      # fond gris mat
GRIS_ZONE = "#a6a6a6"      # zones d'écriture, un peu plus pâles
GRIS_BORD = "#7a7a7a"      # contour des zones
GRIS_MENU = "#767676"      # menu de gauche et panneau des fichiers
GRIS_INACTIF = "#9a9a9a"   # onglets et boutons pas actifs
NOIR = "#000000"
ORANGE = "#ff7a1a"
ORANGE_FONCE = "#e0620a"   # orange quand on clique
LIME = "#7fff00"           # le courant vert lime dans les schémas
LIME_LUEUR = "#92d253"     # halo autour du courant
GRIS_BOITE = "#b8b8b8"     # boîtes des étapes
GRIS_LIEN = "#6e6e6e"      # lignes entre les étapes (avant le courant)

FAMILLE = "DejaVu Sans"
FAMILLE_CODE = "DejaVu Sans Mono"
POLICE = (FAMILLE, 14)
POLICE_BOUTON = (FAMILLE, 11, "bold")
POLICE_INVITE = (FAMILLE, 18)
POLICE_CODE = (FAMILLE_CODE, 12)
TAILLE_AGENT = 16    # taille du texte des réponses de l'agent (tes questions : 14)
COULEUR_LIEN = "#6e2a00"   # liens web cliquables

MARGE = 25            # espace entre la zone d'écriture et le bas de l'écran
LARGEUR = 0.70        # largeur des zones (70 % de la fenêtre)
HAUT_DOC = 70         # où commence le texte en haut de l'écran
LARGEUR_MENU = 270    # largeur du menu de gauche

# ---------- Logo de l'agent ----------
FICHIER_LOGO = Path(__file__).with_name("logo_marceau.png")   # le logo va à côté du script
LOGO_CENTRE = 160     # taille du logo au milieu de l'écran, au début
LOGO_GAUCHE = 110     # taille une fois rendu à gauche
LOGO_AVATAR = 34      # petit logo devant chaque réponse de l'agent

# ---------- Couleurs du code dans le Codex ----------
CODE_FOND = "#262626"          # gris mat foncé
CODE_TEXTE = "#e8e8e8"
CODE_NUMEROS_FOND = "#1f1f1f"
CODE_NUMEROS = "#6c6c6c"
CODE_LIGNE_ACTIVE = "#303030"
CODE_SELECTION = "#7a3f12"
COULEURS_CODE = {
    # étiquette:    (couleur, style)
    "motcle":      ("#ff5fd7", "bold"),     # rose : if, def, return, const…
    "fonction":    ("#ffd75f", "bold"),     # jaune : nom d'une fonction qu'on crée
    "classe":      ("#5fffd7", "bold"),     # turquoise : nom d'une classe, sélecteurs CSS
    "appel":       ("#82aaff", ""),         # bleu : appel d'une fonction
    "interne":     ("#00d7ff", ""),         # cyan : print, len, console, Math…
    "chaine":      ("#a6ff4d", ""),         # vert lime : "du texte"
    "nombre":      ("#ffaf5f", ""),         # orange pâle : 42, 3.14, #ff7a1a
    "constante":   ("#ff875f", "bold"),     # corail : True, None, null…
    "commentaire": ("#8a929a", "italic"),   # gris : # un commentaire
    "decorateur":  ("#d787ff", ""),         # mauve : @decorateur, @media
    "operateur":   ("#ff6b6b", ""),         # rouge : = + - * / < >
    "ponctuation": ("#ffd700", ""),         # or : ( ) [ ] { }
    "soi":         ("#ff9e64", "italic"),   # self, this
    "balise":      ("#ff6b6b", ""),         # < > en HTML
    "nombalise":   ("#ff5fd7", "bold"),     # div, span, script…
    "attribut":    ("#ffd75f", ""),         # class=, href=…
    "propriete":   ("#5fd7ff", ""),         # color:, margin: en CSS
    "cle":         ("#82aaff", "bold"),     # clés en JSON
    "variable":    ("#d787ff", ""),         # $VARIABLE en shell
    "titre":       ("#ff7a1a", "bold"),     # # Titre en Markdown
}

# ---------- Réglages des IA et de GitHub ----------
MODELES_CLAUDE = (
    ("claude-opus-5",    "Opus 5",    "le plus capable",            "5 $ / 25 $"),
    ("claude-sonnet-5",  "Sonnet 5",  "bon partout, moins cher",    "2 $ / 10 $"),
    ("claude-haiku-4-5", "Haiku 4.5", "le plus rapide et le moins cher", "1 $ / 5 $"),
    ("claude-fable-5-1", "Fable 5.1", "pour les tâches longues",    "10 $ / 50 $"),
)
_modeles_claude_en_ligne = []   # rempli par l'API quand une clé est branchée
MODELE_CLAUDE = "claude-sonnet-5"   # celui choisi au démarrage
URL_CLAUDE = "https://api.anthropic.com/v1/messages"
URL_OLLAMA = "http://localhost:11434"
URL_GITHUB = "https://api.github.com"
DOSSIER_CONFIG = Path.home() / ".config" / "ecriture"
FICHIER_CLE = DOSSIER_CONFIG / "cle_api"
FICHIER_TOKEN = DOSSIER_CONFIG / "github_token"
FICHIER_REGLAGES = DOSSIER_CONFIG / "reglages.json"   # ta ville pour la météo
DOSSIER_SESSIONS = Path.home() / ".local" / "share" / "ecriture" / "sessions"
FICHIER_MAJ = DOSSIER_CONFIG / "maj_auto"      # "non" dedans = tu as coupé l'auto

# ---------- Mises à jour ----------
# L'app va se chercher elle-même sur GitHub. Un seul lien, écrit en dur : elle ne
# téléchargera jamais rien d'ailleurs, même si un fichier de config disait le contraire.
VERSION = "1.4.0"
URL_MAJ = ("https://raw.githubusercontent.com/alexmarceauprevost812-source/"
           "marceau-78/refs/heads/claude/bold-gates-5onh76/ecriture.py")
RECHERCHES_MAX = 5                     # recherches web max par question (Claude)
NOM_CLAUDE = "Claude + web (payant)"   # nom affiché dans le menu
STYLE_QUEBECOIS = True                 # False = l'IA parle en français standard
DUREE_ECRITURE = 1.5                   # secondes max pour écrire une réponse à l'écran
VITESSE_MS = 10                        # une lettre (ou un petit paquet) aux 10 ms
CONTEXTE_CLAUDE = 150_000              # caractères de code max envoyés à Claude par demande Codex
CONTEXTE_OLLAMA = 24_000               # … et aux modèles gratuits (leur mémoire est plus petite)
CTX_OLLAMA_CODEX = 16384               # mémoire (tokens) demandée à Ollama pour le Codex

# Les IA gratuites qu'on propose d'installer, de la plus légère à la plus lourde.
MODELES_SUGGERES = (
    ("llama3.2",    "2 Go",  "Léger et rapide. Le meilleur premier choix sur un ordi ordinaire."),
    ("gemma3",      "3,3 Go", "Compact, répond vite, correct en français."),
    ("mistral",     "4,1 Go", "Équilibré. Bon en français, bon partout."),
    ("qwen3",       "5,2 Go", "Le plus fort pour le code et le raisonnement."),
    ("deepseek-r1", "5,2 Go", "Réfléchit avant de répondre. Plus lent, plus posé."),
)


QUEBECOIS = (
    "Tu es un vrai Québécois. Tu parles pis tu écris en français québécois familier, "
    "comme quelqu'un d'ici qui jase avec un chum : tu tutoies, tu utilises les tournures "
    "orales (y'a, j'suis, t'sais, c'est-tu, faque, pis, ben, là, pantoute, tantôt, astheure) "
    "et les expressions d'ici quand ça sonne naturel (c'est l'fun, ça a pas d'allure, "
    "lâche pas, c'est correct, mets-en). Garde ça clair et facile à lire, sans en beurrer "
    "trop épais : pas de caricature, pas de sacres à moins que la personne en utilise. "
    "Les termes techniques, les commandes et le code restent exacts et bien écrits. "
)


def instructions_systeme(web):
    aujourdhui = datetime.date.today().isoformat()
    texte = (
        "Tu es l'assistant intégré à une application d'écriture. "
        + (QUEBECOIS if STYLE_QUEBECOIS else "Réponds en français, de façon claire et directe. ")
        + "Écris seulement en texte brut : pas de Markdown, pas d'astérisques, "
        "pas de dièses, pas de tableaux. Pour une liste, utilise des tirets simples. "
    )
    if web:
        texte += ("Fais une recherche web dès que la question touche l'actualité, des prix, "
                  "des horaires, des personnes ou n'importe quoi qui a pu changer récemment. ")
    else:
        texte += ("Tu n'as pas accès à Internet (sauf pour la météo, que l'application affiche "
                  "elle-même). Si la question demande des infos récentes (actualité, prix, horaires), "
                  "dis-le franchement au lieu d'inventer "
                  f"et suggère de choisir « {NOM_CLAUDE} » dans le menu. ")
    ville = lire_reglages().get("ville", "")
    texte += (
        "Pouvoir spécial : l'application affiche elle-même la météo en direct. Quand on te demande "
        "la météo, la température ou s'il va pleuvoir ou neiger quelque part, n'invente aucun chiffre "
        "et ne fais pas de recherche web : écris une phrase courte (ex. : « Voici la météo à "
        "Chicoutimi! ») et termine par un bloc comme [METEO Chicoutimi, Québec, Canada] "
        "(ville, province ou état, pays). Si la personne ne dit pas où, écris juste [METEO]. "
        + (f"La ville de la personne est {ville}. " if ville else "")
        + "Quand c'est utile, partage des liens web complets qui commencent par https:// "
        "(sites officiels, documentation), seulement si tu es sûr qu'ils existent. "
    )
    texte += (
        "Quand ta réponse explique un plan d'action ou des étapes à suivre, termine-la "
        "par un bloc exactement comme celui-ci (une étape courte par ligne, moins de 12 mots) :\n"
        "[PLAN]\n1. Première étape\n2. Deuxième étape\n[/PLAN]\n"
        "Ajoute ce bloc seulement s'il y a un vrai plan ou des étapes. "
    )
    return texte + f"Date d'aujourd'hui : {aujourdhui}."


def instructions_codex():
    return (
        "Tu es Codex, l'assistant de programmation de l'application. "
        + (QUEBECOIS if STYLE_QUEBECOIS else "Réponds en français, clairement. ")
        + "Tu reçois l'arborescence du projet et le contenu de certains fichiers. "
        "Pour créer ou modifier un fichier, écris le fichier AU COMPLET (jamais juste un morceau) "
        "dans un bloc exactement comme celui-ci :\n"
        "[FICHIER chemin/du/fichier.ext]\n(tout le contenu du fichier)\n[/FICHIER]\n"
        "Pour un fichier qui existe déjà, utilise son chemin exact de l'arborescence. "
        "Pas de ``` dans ces blocs. Avant les blocs, explique en quelques phrases ce que tu changes "
        "et pourquoi, en texte brut sans Markdown. Touche seulement aux fichiers nécessaires. "
        "Si on te pose juste une question, réponds sans bloc. "
        "Si tu dois voir d'autres fichiers du projet avant de les modifier, réponds seulement avec "
        "un bloc [LIRE] qui liste leurs chemins (un par ligne), terminé par [/LIRE]."
    )


# ---------- Clés et tokens (gardés dans ~/.config/ecriture, lisibles juste par toi) ----------
def lire_secret(fichier, variable_env):
    if fichier.exists():
        valeur = fichier.read_text(encoding="utf-8").strip()
        if valeur:
            return valeur
    return os.environ.get(variable_env, "").strip()


def enregistrer_secret(fichier, valeur):
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(valeur, encoding="utf-8")
    os.chmod(fichier, 0o600)


def lire_reglages():
    try:
        return json.loads(FICHIER_REGLAGES.read_text(encoding="utf-8"))
    except Exception:
        return {}


def pousser_auto():
    """True si le Codex a le droit d'envoyer ses changements sur GitHub tout seul."""
    return bool(lire_reglages().get("pousser_auto"))


def regler_pousser_auto(actif):
    reglages = lire_reglages()
    reglages["pousser_auto"] = bool(actif)
    enregistrer_reglages(reglages)


def enregistrer_reglages(reglages):
    DOSSIER_CONFIG.mkdir(parents=True, exist_ok=True)
    FICHIER_REGLAGES.write_text(json.dumps(reglages, ensure_ascii=False, indent=1), encoding="utf-8")


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


def ollama_repond():
    """True si le service Ollama répond sur la machine."""
    try:
        with urllib.request.urlopen(URL_OLLAMA + "/api/tags", timeout=2):
            return True
    except Exception:
        return False


def modeles_claude_en_ligne(cle):
    """Demande à l'API la liste des modèles que CETTE clé peut utiliser."""
    requete = urllib.request.Request(
        "https://api.anthropic.com/v1/models?limit=100",
        headers={"x-api-key": cle, "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(requete, timeout=10) as rep:
        data = json.loads(rep.read().decode("utf-8"))
    return [(m["id"], m.get("display_name") or m["id"]) for m in data.get("data", [])]


def modeles_claude():
    """(identifiant, nom, note) pour chaque Claude offert."""
    if _modeles_claude_en_ligne:
        connus = {i: (n, p) for i, _, n, p in MODELES_CLAUDE}
        return [(i, nom.replace("Claude ", ""), *connus.get(i, ("", "")))
                for i, nom in _modeles_claude_en_ligne]
    return [(i, nom, note, prix) for i, nom, note, prix in MODELES_CLAUDE]


def nom_court(moteur):
    """Le nom à montrer pendant que ça réfléchit."""
    type_moteur, modele = moteur
    if type_moteur != "claude":
        return modele.removesuffix(":latest")
    for identifiant, nom, *_ in modeles_claude():
        if identifiant == modele:
            return f"Claude {nom}"
    return "Claude"


def trouver_moteurs():
    """Les IA du menu : les modèles Ollama gratuits en premier, les Claude ensuite."""
    moteurs = {}
    for nom in modeles_ollama():
        moteurs[f"{nom.removesuffix(':latest')} (gratuit)"] = ("ollama", nom)
    for identifiant, nom, note, prix in modeles_claude():
        detail = f" — {note}" if note else ""
        moteurs[f"Claude {nom} + web{detail}"] = ("claude", identifiant)
    return moteurs


def appeler_ollama(modele, messages, systeme, num_ctx=None):
    corps = {
        "model": modele,
        "stream": False,
        "messages": [{"role": "system", "content": systeme}] + messages,
    }
    if num_ctx:
        corps["options"] = {"num_ctx": num_ctx}
    requete = urllib.request.Request(
        URL_OLLAMA + "/api/chat", data=json.dumps(corps).encode("utf-8"), method="POST",
        headers={"content-type": "application/json"})
    with urllib.request.urlopen(requete, timeout=900) as rep:
        data = json.loads(rep.read().decode("utf-8"))
    texte = data.get("message", {}).get("content", "")
    # Certains modèles (deepseek-r1, qwen3) écrivent leur réflexion entre <think> : on l'enlève
    texte = re.sub(r"<think>.*?</think>", "", texte, flags=re.S).strip()
    return texte, []


# ---------- Claude (payant, avec recherche web) ----------
def appeler_claude(cle, messages, systeme, web=True, max_tokens=2048, timeout=180,
                   modele=None):
    conversation = list(messages)
    morceaux, sources = [], []
    for _ in range(5):
        corps = {
            "model": modele or MODELE_CLAUDE,
            "max_tokens": max_tokens,
            "system": systeme,
            "messages": conversation,
        }
        if web:
            corps["tools"] = [{"type": "web_search_20250305", "name": "web_search",
                               "max_uses": RECHERCHES_MAX}]
        requete = urllib.request.Request(
            URL_CLAUDE, data=json.dumps(corps).encode("utf-8"), method="POST",
            headers={"x-api-key": cle, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"})
        with urllib.request.urlopen(requete, timeout=timeout) as rep:
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
            return "Clé API invalide. Change-la dans Paramètres (menu ☰, tout en bas)."
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


# ---------- Conversations sauvegardées (sessions) ----------
def lister_sessions():
    if not DOSSIER_SESSIONS.exists():
        return []
    sessions = []
    for fichier in DOSSIER_SESSIONS.glob("*.json"):
        try:
            sessions.append(json.loads(fichier.read_text(encoding="utf-8")))
        except Exception:
            pass
    return sorted(sessions, key=lambda s: s.get("modifie", ""), reverse=True)


# ---------- GitHub ----------
def github(methode, chemin, token, corps=None):
    entetes = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Ecriture-Codex"}
    donnees = None
    if corps is not None:
        donnees = json.dumps(corps).encode("utf-8")
        entetes["Content-Type"] = "application/json"
    requete = urllib.request.Request(URL_GITHUB + chemin, data=donnees, method=methode,
                                     headers=entetes)
    with urllib.request.urlopen(requete, timeout=60) as rep:
        brut = rep.read().decode("utf-8")
    return json.loads(brut) if brut else None


def lire_blob(depot, sha, token):
    """Lit un fichier du projet GitHub. Lance UnicodeDecodeError si c'est un fichier binaire."""
    data = github("GET", f"/repos/{depot}/git/blobs/{sha}", token)
    return base64.b64decode(data["content"]).decode("utf-8").replace("\r\n", "\n")


def erreur_github(err):
    if isinstance(err, urllib.error.HTTPError):
        if err.code == 401:
            return "Token GitHub invalide ou expiré. Change-le dans Paramètres (menu ☰, tout en bas)."
        if err.code == 403:
            return ("GitHub refuse : le token n'a pas la permission (Contents : Read and write) "
                    "ou la limite de requêtes est atteinte.")
        if err.code == 404:
            return "Introuvable sur GitHub (ou le token n'a pas accès à ce projet)."
        if err.code in (409, 422):
            return ("Le fichier a changé sur GitHub depuis que tu l'as ouvert. "
                    "Ferme-le et rouvre-le avant d'enregistrer.")
        return f"Erreur GitHub {err.code} : {err.reason}"
    if isinstance(err, UnicodeDecodeError):
        return "Ce fichier est binaire (image, police…), l'éditeur ne peut pas l'ouvrir."
    if isinstance(err, urllib.error.URLError):
        return "Pas de connexion à GitHub. Vérifie ton Internet."
    return f"Erreur : {err}"


EXT_TEXTE = set(".py .pyw .js .jsx .ts .tsx .mjs .cjs .html .htm .css .scss .json .md .txt .sh "
                ".bash .sql .yml .yaml .toml .ini .cfg .xml .svg .vue .env .gitignore .csv".split())
NOMS_TEXTE = {"Dockerfile", "Makefile", "README", "LICENSE", "Procfile"}


def est_texte(chemin):
    p = Path(chemin)
    return p.suffix.lower() in EXT_TEXTE or p.name in NOMS_TEXTE


def extraire_fichiers(texte):
    """Sort les blocs [FICHIER chemin]…[/FICHIER] d'une réponse du Codex.
    Retourne (explication, [(chemin, contenu), …])."""
    fichiers = []

    def garder(m):
        chemin = m.group(1).strip().strip("`\"' ")
        contenu = re.sub(r"^\s*```[\w+.-]*\n", "", m.group(2))  # enlève ``` si l'IA en met pareil
        contenu = re.sub(r"\n```\s*$", "", contenu)
        fichiers.append((chemin, contenu.strip("\n") + "\n"))
        return ""

    explication = re.sub(r"\[FICHIER\s+([^\]\n]+)\]\n?(.*?)\[/FICHIER\]", garder, texte,
                         flags=re.S | re.I)
    explication = re.sub(r"\[PLAN\].*?(\[/PLAN\]|$)", "", explication, flags=re.S | re.I)
    explication = re.sub(r"\[LIRE\].*?(\[/LIRE\]|$)", "", explication, flags=re.S | re.I)
    return explication.strip(), fichiers


# ---------- Moteur de couleurs pour le code ----------
LANGAGES = {
    ".py": "python", ".pyw": "python",
    ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js", ".mjs": "js", ".cjs": "js",
    ".html": "html", ".htm": "html", ".xml": "html", ".svg": "html", ".vue": "html",
    ".css": "css", ".scss": "css", ".json": "json",
    ".sh": "shell", ".bash": "shell", ".sql": "sql", ".md": "markdown",
}


def langage_de(chemin):
    return LANGAGES.get(Path(chemin).suffix.lower(), "generique")


def _mots(liste):
    return r"\b(?:" + "|".join(liste.split()) + r")\b"


CHAINES = r'"(?:\\.|[^"\\\n])*"|' + r"'(?:\\.|[^'\\\n])*'"
NOMBRE = r"\b(?:0[xX][0-9a-fA-F_]+|\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?)\b"
PONCTUATION = r"[()\[\]{}]"

PY_MOTS = ("and as assert async await break continue del elif else except finally for from "
           "global if import in is lambda nonlocal not or pass raise return try while with "
           "yield match case")
PY_INTERNES = ("print len range str int float list dict set tuple open super isinstance "
               "enumerate zip map filter sorted min max sum abs any all type bool input round "
               "reversed getattr setattr hasattr iter next format repr Exception ValueError "
               "TypeError KeyError IndexError RuntimeError")
JS_MOTS = ("const let var function return if else for while do switch case break continue "
           "new class extends import export from default async await try catch finally throw "
           "typeof instanceof in of yield delete void super static get set")
JS_INTERNES = ("console document window Math JSON Promise Array Object String Number Boolean "
               "Date fetch setTimeout setInterval localStorage require module")
SH_MOTS = ("if then else elif fi for do done case esac function while until in export local "
           "return echo sudo cd exit source alias")
SQL_MOTS = ("select from where insert into values update set delete create table alter drop "
            "join left right inner outer on and or not null primary key references as order by "
            "group limit policy enable row level security using with check default unique "
            "index view grant revoke returning begin commit")

# Chaque langage : une liste de (étiquette, motif). La première règle qui marche gagne,
# donc les commentaires et les textes passent avant le reste (pas de mots-clés colorés dedans).
REGLES = {
    "python": [
        ("commentaire", r"#[^\n]*"),
        ("chaine", r"[rRbBuUfF]{0,2}(?:\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|" + CHAINES + ")"),
        ("decorateur", r"@[\w.]+"),
        (None, r"(?P<motcle__d>\bdef\b)\s+(?P<fonction__d>\w+)"),
        (None, r"(?P<motcle__c>\bclass\b)\s+(?P<classe__c>\w+)"),
        ("constante", _mots("True False None")),
        ("soi", _mots("self cls")),
        ("motcle", _mots(PY_MOTS)),
        ("interne", _mots(PY_INTERNES)),
        ("appel", r"\b[A-Za-z_]\w*(?=\s*\()"),
        ("nombre", NOMBRE),
        ("operateur", r"[+\-*/%=<>!&|^~]+"),
        ("ponctuation", PONCTUATION),
    ],
    "js": [
        ("commentaire", r"//[^\n]*|/\*[\s\S]*?\*/"),
        ("chaine", r"`(?:\\.|[^`\\])*`|" + CHAINES),
        (None, r"(?P<motcle__f>\bfunction\b)\s*\*?\s*(?P<fonction__f>[A-Za-z_$][\w$]*)"),
        (None, r"(?P<motcle__c>\bclass\b)\s+(?P<classe__c>[A-Za-z_$][\w$]*)"),
        ("constante", _mots("true false null undefined NaN Infinity")),
        ("soi", _mots("this")),
        ("motcle", _mots(JS_MOTS)),
        ("interne", _mots(JS_INTERNES)),
        ("appel", r"\b[A-Za-z_$][\w$]*(?=\s*\()"),
        ("nombre", NOMBRE),
        ("operateur", r"=>|[+\-*/%=<>!&|^~?:]+"),
        ("ponctuation", PONCTUATION),
    ],
    "html": [
        ("commentaire", r"<!--[\s\S]*?-->"),
        (None, r"(?P<balise__o></?!?)(?P<nombalise__o>[\w:-]+)"),
        ("balise", r"/?>"),
        ("chaine", CHAINES),
        ("attribut", r"[\w:@.-]+(?==)"),
        ("constante", r"&#?\w+;"),
    ],
    "css": [
        ("commentaire", r"/\*[\s\S]*?\*/"),
        ("chaine", CHAINES),
        ("decorateur", r"@[\w-]+"),
        ("propriete", r"(?<![\w-])[\w-]+(?=\s*:(?!:))"),
        ("interne", r"\b(?:var|calc|rgba?|hsla?|url|linear-gradient|radial-gradient|min|max|clamp)(?=\()"),
        ("nombre", r"#[0-9a-fA-F]{3,8}\b|-?\b\d+(?:\.\d+)?(?:px|em|rem|%|vh|vw|s|ms|deg|fr)?"),
        ("classe", r"[.#][A-Za-z_-][\w-]*"),
        ("constante", r"!important"),
        ("ponctuation", r"[{}()\[\];]"),
    ],
    "json": [
        ("cle", r'"(?:\\.|[^"\\\n])*"(?=\s*:)'),
        ("chaine", r'"(?:\\.|[^"\\\n])*"'),
        ("constante", _mots("true false null")),
        ("nombre", r"-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b"),
        ("ponctuation", r"[{}\[\]]"),
    ],
    "shell": [
        ("commentaire", r"(?<![\w$])#[^\n]*"),
        ("chaine", CHAINES),
        ("variable", r"\$\{?[\w@#?*!-]+\}?"),
        ("motcle", _mots(SH_MOTS)),
        ("nombre", NOMBRE),
        ("operateur", r"[|&;<>]+"),
        ("ponctuation", PONCTUATION),
    ],
    "sql": [
        ("commentaire", r"--[^\n]*|/\*[\s\S]*?\*/"),
        ("chaine", r"'(?:''|[^'])*'"),
        ("motcle", _mots(SQL_MOTS)),
        ("interne", r"\b(?:count|sum|avg|min|max|now|coalesce|lower|upper|auth\.uid)\b"),
        ("nombre", NOMBRE),
        ("operateur", r"[=<>!]+|::"),
        ("ponctuation", PONCTUATION),
    ],
    "markdown": [
        ("chaine", r"```[\s\S]*?```|`[^`\n]+`"),
        ("titre", r"^#{1,6}\s.*$"),
        ("motcle", r"\*\*[^*\n]+\*\*|__[^_\n]+__"),
        ("soi", r"\*[^*\n]+\*"),
        ("appel", r"\[[^\]\n]+\]\([^)\n]+\)"),
        ("operateur", r"^\s*(?:[-*+]|\d+\.)\s"),
    ],
    "generique": [
        ("commentaire", r"(?:#|//)[^\n]*"),
        ("chaine", CHAINES),
        ("nombre", NOMBRE),
        ("ponctuation", PONCTUATION),
    ],
}
_MOTIFS = {}


def motif_de(langage):
    if langage not in _MOTIFS:
        morceaux = []
        for i, (nom, motif) in enumerate(REGLES[langage]):
            morceaux.append(f"(?P<{nom}__{i}>{motif})" if nom else f"(?:{motif})")
        options = re.M | (re.I if langage == "sql" else 0)
        _MOTIFS[langage] = re.compile("|".join(morceaux), options)
    return _MOTIFS[langage]


def _jetons_simples(texte, langage, decalage):
    resultat = []
    for m in motif_de(langage).finditer(texte):
        for nom, valeur in m.groupdict().items():
            if valeur:
                resultat.append((m.start(nom) + decalage, m.end(nom) + decalage,
                                 nom.split("__")[0]))
    return resultat


def jetons(texte, langage):
    """Découpe le code en morceaux colorés : liste de (début, fin, étiquette)."""
    if langage != "html":
        return _jetons_simples(texte, langage, 0)
    # En HTML, le JavaScript des <script> et le CSS des <style> ont leurs propres couleurs
    resultat, position = [], 0
    for m in re.finditer(r"<(script|style)\b[^>]*>([\s\S]*?)(?=</\1>|$)", texte, re.I):
        debut, fin = m.start(2), m.end(2)
        resultat += _jetons_simples(texte[position:debut], "html", position)
        resultat += _jetons_simples(texte[debut:fin],
                                    "js" if m.group(1).lower() == "script" else "css", debut)
        position = fin
    return resultat + _jetons_simples(texte[position:], "html", position)


# ---------- Pouvoir magique : la météo en direct (Open-Meteo, gratuit, sans clé) ----------
URL_GEO = "https://geocoding-api.open-meteo.com/v1/search"
URL_METEO = "https://api.open-meteo.com/v1/forecast"
PAYS_PREFERE = "CA"   # en cas d'égalité (ex. : Alma), on prend la ville au Canada

CODES_METEO = {
    0: ("Ciel dégagé", "soleil"), 1: ("Plutôt dégagé", "soleil_nuage"),
    2: ("Partiellement nuageux", "soleil_nuage"), 3: ("Couvert", "nuage"),
    45: ("Brouillard", "brouillard"), 48: ("Brouillard givrant", "brouillard"),
    51: ("Bruine légère", "pluie"), 53: ("Bruine", "pluie"), 55: ("Forte bruine", "pluie"),
    56: ("Bruine verglaçante", "pluie"), 57: ("Bruine verglaçante", "pluie"),
    61: ("Pluie faible", "pluie"), 63: ("Pluie", "pluie"), 65: ("Forte pluie", "pluie"),
    66: ("Pluie verglaçante", "pluie"), 67: ("Pluie verglaçante", "pluie"),
    71: ("Neige faible", "neige"), 73: ("Neige", "neige"), 75: ("Forte neige", "neige"),
    77: ("Grains de neige", "neige"), 80: ("Averses", "pluie"), 81: ("Averses", "pluie"),
    82: ("Fortes averses", "pluie"), 85: ("Averses de neige", "neige"),
    86: ("Fortes averses de neige", "neige"), 95: ("Orage", "orage"),
    96: ("Orage avec grêle", "orage"), 99: ("Orage avec grêle", "orage"),
}
JOURS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
MOTS_METEO = re.compile(r"m[ée]t[ée]o|quel(?:le)?s? temps|kel temps|pleuv|il pleut|neiger|"
                        r"il neige|pr[ée]visions?", re.I)
MOTS_PAS_LIEU = set("demain demin aujourd'hui aujourdhui auj ce cette cet soir matin midi "
                    "semaine fin weekend week-end maintenant svp stp là la le les prochain "
                    "prochaine prochains météo meteo temps quoi quel quelle stp".split())


class PasDeLieu(Exception):
    pass


class LieuIntrouvable(Exception):
    pass


def decrire_meteo(code, jour=True):
    description, icone = CODES_METEO.get(int(code), ("Météo inconnue", "nuage"))
    if not jour:
        icone = {"soleil": "lune", "soleil_nuage": "lune_nuage"}.get(icone, icone)
    return description, icone


def extraire_meteo(texte, question):
    """Retourne (texte sans le bloc [METEO …], lieu demandé). Lieu = None si pas de météo demandée,
    "" si la météo est demandée sans dire où (on prendra la ville des Paramètres)."""
    m = re.search(r"\[M[ÉE]T[ÉE]O(?:\s*[:\-]?\s*([^\]\n]*))?\]", texte, re.I)
    if m:
        return (texte[:m.start()] + texte[m.end():]).strip(), (m.group(1) or "").strip()
    if MOTS_METEO.search(question):   # l'IA a oublié le bloc : on devine le lieu dans la question
        return texte, lieu_dans_question(question)
    return texte, None


def lieu_dans_question(question):
    motif = r"\b(?:à|a|au|aux|en|pour|sur|dans|de|du)\s+(?:la\s+|le\s+|l['’])?([a-zà-ÿ'’\-]+(?:[\s\-][a-zà-ÿ'’\-]+){0,2})"
    for m in re.finditer(motif, question, re.I):
        mots = []
        for mot in re.split(r"\s+", m.group(1)):
            if mot.lower().strip("'’") in MOTS_PAS_LIEU:
                break
            mots.append(mot)
        if mots:
            return " ".join(mots)
    return ""


def sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte.lower())
                   if unicodedata.category(c) != "Mn")


def lire_json(url):
    requete = urllib.request.Request(url, headers={"User-Agent": "Ecriture-app"})
    with urllib.request.urlopen(requete, timeout=15) as rep:
        return json.loads(rep.read().decode("utf-8"))


def trouver_lieu(lieu):
    parties = [p.strip() for p in lieu.split(",") if p.strip()]
    if not parties:
        raise PasDeLieu()
    indices = [sans_accents(p) for p in parties[1:]]
    mots = parties[0].split()
    essais = [parties[0]] + [" ".join(mots[:n]) for n in range(len(mots) - 1, 0, -1)]
    for essai in dict.fromkeys(essais):   # sans doublons, dans l'ordre
        data = lire_json(URL_GEO + "?" + urllib.parse.urlencode(
            {"name": essai, "count": 10, "language": "fr", "format": "json"}))
        resultats = data.get("results") or []
        if not resultats:
            continue

        def score(r):
            texte = sans_accents(" ".join(str(r.get(k) or "") for k in
                                          ("admin1", "admin2", "country", "country_code")))
            return (sum(1 for i in indices if i and i in texte),
                    r.get("country_code") == PAYS_PREFERE, r.get("population") or 0)

        return max(resultats, key=score)
    raise LieuIntrouvable(lieu)


def obtenir_meteo(lieu, ville_par_defaut=""):
    lieu = lieu or ville_par_defaut
    if not lieu:
        raise PasDeLieu()
    endroit = trouver_lieu(lieu)
    data = lire_json(URL_METEO + "?" + urllib.parse.urlencode({
        "latitude": endroit["latitude"], "longitude": endroit["longitude"],
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,"
                   "wind_speed_10m,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "auto", "forecast_days": 5,
    }))
    region = ", ".join(x for x in (endroit.get("admin1"), endroit.get("country")) if x)
    return {"nom": endroit.get("name", lieu), "region": region,
            "actuel": data.get("current", {}), "jours": data.get("daily", {})}


def message_meteo(err, lieu):
    if isinstance(err, PasDeLieu):
        return "Dis-moi pour quelle ville, ou ajoute ta ville dans Paramètres (menu ☰)."
    if isinstance(err, LieuIntrouvable):
        return f"J'ai pas trouvé « {lieu} ». Essaie avec le nom de la ville pis la province."
    if isinstance(err, urllib.error.URLError):
        return "Pas de connexion Internet pour aller chercher la météo."
    return f"Météo pas disponible : {err}"


# ---------- Liens web cliquables ----------
URL_WEB = re.compile(r"(?:https?://|www\.)[^\s<>\"'«»]+", re.I)


def nettoyer_url(url):
    while url and url[-1] in ".,;:!?]}»'\"":
        url = url[:-1]
    if url.endswith(")") and url.count("(") < url.count(")"):
        url = url[:-1]
    return url


def liens_markdown_en_texte(texte):
    # « [ti-lex](https://ti-lex.ca) » devient « ti-lex (https://ti-lex.ca) »
    return re.sub(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)", r"\1 (\2)", texte)


def rectangle_arrondi(canvas, x0, y0, x1, y1, r, **options):
    points = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
              x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return canvas.create_polygon(points, smooth=True, **options)


def arrondi(valeur):
    return "–" if valeur is None else str(round(valeur))


class CarteMeteo(tk.Canvas):
    """Carte météo animée : le soleil tourne, la pluie pis la neige tombent, les nuages flottent."""
    HAUTEUR = 262
    PAS_MS = 40

    def __init__(self, parent, meteo, largeur):
        super().__init__(parent, bg=GRIS_ZONE, highlightthickness=0, bd=0,
                         width=largeur, height=self.HAUTEUR, cursor="arrow")
        self.rayons, self.nuages, self.gouttes, self.flocons, self.eclairs, self.brumes = [], [], [], [], [], []
        self.t = 0
        self.dessiner(meteo, largeur)
        self.after(self.PAS_MS, self.animer)

    def dessiner(self, meteo, largeur):
        a, j = meteo["actuel"], meteo["jours"]
        description, icone = decrire_meteo(a.get("weather_code", 3), bool(a.get("is_day", 1)))
        W, H = largeur, self.HAUTEUR
        rectangle_arrondi(self, 4, 4, W - 4, H - 4, 18, fill=GRIS_BOITE, outline=ORANGE, width=2)
        self.create_text(W - 24, 22, anchor="ne", text=meteo["nom"], fill=NOIR, font=(FAMILLE, 15, "bold"))
        self.create_text(W - 24, 46, anchor="ne", text=meteo["region"], fill="#2e2e2e", font=(FAMILLE, 10))
        self.icone(icone, 80, 82, 108, anime=True)
        self.create_text(152, 26, anchor="nw", text=f"{arrondi(a.get('temperature_2m'))}°",
                         fill=NOIR, font=(FAMILLE, 44, "bold"))
        self.create_text(154, 98, anchor="nw", text=description, fill=NOIR, font=(FAMILLE, 13, "bold"))
        self.create_text(154, 122, anchor="nw", fill="#2e2e2e", font=(FAMILLE, 10), text=(
            f"Ressenti {arrondi(a.get('apparent_temperature'))}°    "
            f"Vent {arrondi(a.get('wind_speed_10m'))} km/h    "
            f"Humidité {arrondi(a.get('relative_humidity_2m'))} %"))
        self.create_line(24, 152, W - 24, 152, fill=GRIS_BORD)
        dates = j.get("time") or []
        colonne = (W - 48) / max(len(dates), 1)
        for i, date in enumerate(dates):
            cx = 24 + colonne * (i + 0.5)
            nom = "Auj." if i == 0 else JOURS[datetime.date.fromisoformat(date).weekday()]
            self.create_text(cx, 168, text=nom, fill=NOIR, font=(FAMILLE, 10, "bold"))
            self.icone(decrire_meteo(j["weather_code"][i])[1], cx, 198, 38, anime=False)
            self.create_text(cx, 230, fill=NOIR, font=(FAMILLE, 10, "bold"), text=(
                f"{arrondi(j['temperature_2m_max'][i])}° / {arrondi(j['temperature_2m_min'][i])}°"))
            proba = (j.get("precipitation_probability_max") or [None] * len(dates))[i]
            if proba is not None:
                self.create_text(cx, 246, text=f"Précip. {proba} %", fill="#2e2e2e", font=(FAMILLE, 8))

    # ----- Les icônes, dessinées avec des formes -----
    def icone(self, sorte, cx, cy, s, anime):
        if sorte in ("soleil", "soleil_nuage"):
            self.soleil(*((cx, cy, s) if sorte == "soleil" else (cx - 0.16 * s, cy - 0.14 * s, 0.72 * s)), anime)
        if sorte in ("lune", "lune_nuage"):
            self.lune(*((cx, cy, s) if sorte == "lune" else (cx - 0.16 * s, cy - 0.14 * s, 0.72 * s)))
        if sorte in ("soleil_nuage", "lune_nuage"):
            self.nuage(cx + 0.06 * s, cy + 0.1 * s, 0.8 * s, "#f4f4f4", anime)
        elif sorte == "nuage":
            self.nuage(cx - 0.14 * s, cy - 0.08 * s, 0.68 * s, "#cfcfcf", anime)
            self.nuage(cx + 0.06 * s, cy + 0.06 * s, 0.86 * s, "#f4f4f4", anime)
        elif sorte == "pluie":
            self.nuage(cx, cy - 0.14 * s, 0.92 * s, "#dcdcdc", anime)
            self.chute(cx, cy, s, anime, flocons=False)
        elif sorte == "neige":
            self.nuage(cx, cy - 0.14 * s, 0.92 * s, "#eeeeee", anime)
            self.chute(cx, cy, s, anime, flocons=True)
        elif sorte == "orage":
            self.nuage(cx, cy - 0.16 * s, 0.92 * s, "#a9a9a9", anime)
            self.eclair(cx, cy, s, anime)
        elif sorte == "brouillard":
            self.brume(cx, cy, s, anime)

    def soleil(self, cx, cy, s, anime):
        rayons = []
        for k in range(8):
            ligne = self.create_line(0, 0, 0, 0, fill="#ff9f00", width=max(2, s / 24), capstyle="round")
            rayons.append((ligne, k * math.pi / 4))
        r = 0.24 * s
        self.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#ffc21a", outline="#ff9800", width=max(1, s / 40))
        groupe = (cx, cy, s, rayons)
        self.placer_rayons(groupe, 0, 0)
        if anime:
            self.rayons.append(groupe)

    def placer_rayons(self, groupe, angle, pulsation):
        cx, cy, s, rayons = groupe
        for ligne, base in rayons:
            a = base + angle
            r1, r2 = 0.33 * s, 0.47 * s + pulsation
            self.coords(ligne, cx + r1 * math.cos(a), cy + r1 * math.sin(a),
                        cx + r2 * math.cos(a), cy + r2 * math.sin(a))

    def lune(self, cx, cy, s):
        r = 0.27 * s
        self.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#f3e7a8", outline="#d9c56a")
        self.create_oval(cx - r + 0.13 * s, cy - r - 0.08 * s, cx + r + 0.13 * s, cy + r - 0.08 * s,
                         fill=GRIS_BOITE, outline=GRIS_BOITE)

    def nuage(self, cx, cy, s, couleur, anime):
        morceaux = [self.create_oval(cx + x0 * s, cy + y0 * s, cx + x1 * s, cy + y1 * s, fill=couleur, outline="")
                    for x0, y0, x1, y1 in ((-0.42, -0.02, -0.04, 0.3), (-0.2, -0.24, 0.2, 0.16),
                                           (0.0, -0.1, 0.42, 0.3))]
        morceaux.append(self.create_rectangle(cx - 0.24 * s, cy + 0.08 * s, cx + 0.24 * s, cy + 0.3 * s,
                                              fill=couleur, outline=""))
        morceaux.append(self.create_line(cx - 0.26 * s, cy + 0.3 * s, cx + 0.26 * s, cy + 0.3 * s,
                                         fill="#9a9a9a"))
        if anime:
            self.nuages.append({"ids": morceaux, "phase": random.random() * 6, "decalage": 0.0,
                                "ampleur": max(2.0, s / 30)})

    def chute(self, cx, cy, s, anime, flocons):
        haut, bas = cy + 0.2 * s, cy + 0.5 * s
        positions = (-0.26, -0.09, 0.08, 0.25)
        for n, px in enumerate(positions):
            x = cx + px * s
            y = haut + (bas - haut) * ((n * 0.37) % 1)
            if flocons:
                r = max(2, s / 26)
                item = self.create_oval(x - r, y - r, x + r, y + r, fill="#ffffff", outline="#8c8c8c")
            else:
                item = self.create_line(x, y, x - 0.03 * s, y + 0.1 * s, fill="#2f6fd6",
                                        width=max(2, s / 30), capstyle="round")
            if anime:
                (self.flocons if flocons else self.gouttes).append(
                    {"id": item, "x": x, "y": y, "haut": haut, "bas": bas, "s": s,
                     "vitesse": s / (160 if flocons else 60), "phase": n * 1.7})

    def eclair(self, cx, cy, s, anime):
        points = [(0.02, 0.08), (-0.1, 0.32), (0.0, 0.32), (-0.07, 0.52), (0.13, 0.22), (0.03, 0.22), (0.09, 0.08)]
        item = self.create_polygon([v for x, y in points for v in (cx + x * s, cy + y * s)],
                                   fill="#ffd000", outline="#d49b00")
        if anime:
            self.eclairs.append(item)

    def brume(self, cx, cy, s, anime):
        for n, (dy, largeur) in enumerate(((-0.2, 0.36), (-0.05, 0.42), (0.1, 0.34), (0.25, 0.4))):
            item = self.create_line(cx - largeur * s, cy + dy * s, cx + largeur * s, cy + dy * s,
                                    fill="#e8e8e8", width=max(3, s / 14), capstyle="round")
            if anime:
                self.brumes.append({"id": item, "phase": n * 1.3, "decalage": 0.0, "ampleur": s / 14})

    # ----- L'animation -----
    def animer(self):
        try:
            if not self.winfo_exists():
                return
            self.t += 1
            t = self.t
            for groupe in self.rayons:
                self.placer_rayons(groupe, t * 0.025, 0.035 * groupe[2] * math.sin(t * 0.12))
            for n in self.nuages + self.brumes:
                nouveau = n["ampleur"] * math.sin(t * 0.045 + n["phase"])
                for item in n.get("ids", [n.get("id")]):
                    self.move(item, nouveau - n["decalage"], 0)
                n["decalage"] = nouveau
            for g in self.gouttes:
                g["y"] += g["vitesse"]
                if g["y"] > g["bas"]:
                    g["y"] = g["haut"]
                self.coords(g["id"], g["x"], g["y"], g["x"] - 0.03 * g["s"], g["y"] + 0.1 * g["s"])
            for f in self.flocons:
                f["y"] += f["vitesse"]
                if f["y"] > f["bas"]:
                    f["y"] = f["haut"]
                x = f["x"] + 3 * math.sin(t * 0.08 + f["phase"])
                r = max(2, f["s"] / 26)
                self.coords(f["id"], x - r, f["y"] - r, x + r, f["y"] + r)
            flash = (t % 70) in (0, 1, 4, 5)   # l'éclair clignote de temps en temps
            for item in self.eclairs:
                self.itemconfig(item, fill="#fff6b0" if flash else "#ffd000")
            self.after(self.PAS_MS, self.animer)
        except tk.TclError:
            return   # la carte a été effacée


# ---------- L'agent Codex : il trouve tout seul les fichiers à lire pis à modifier ----------
def instructions_selection():
    return (
        "Tu es Codex. On te donne l'arborescence d'un projet (avec la taille des fichiers) et une "
        "demande. Choisis les fichiers que tu dois lire pour faire la demande : ceux à modifier, "
        "pis ceux qui aident à comprendre. Réponds SEULEMENT avec un bloc comme celui-ci :\n"
        "[LIRE]\nchemin/exact/fichier1.py\nchemin/exact/fichier2.js\n[/LIRE]\n"
        "Maximum 10 fichiers, avec les chemins exacts de l'arborescence. Si la demande crée juste "
        "un nouveau fichier sans avoir besoin des autres, réponds [LIRE][/LIRE]."
    )


def taille_lisible(octets):
    return f"{octets} o" if octets < 1024 else f"{octets / 1024:.0f} Ko"


def demande_selection(question, historique, arbre, ouverts):
    lignes = [f"{c} ({taille_lisible(i['taille'])})" for c, i in sorted(arbre.items())]
    texte = f"Arborescence du projet ({len(arbre)} fichiers) :\n" + "\n".join(lignes[:800])
    if len(lignes) > 800:
        texte += "\n…"
    if ouverts:
        texte += "\n\nFichiers ouverts à l'écran : " + ", ".join(ouverts)
    recents = [f"{m['role']} : {m['content'][:400]}" for m in historique[:-1][-4:]]
    if recents:
        texte += "\n\nConversation récente :\n" + "\n".join(recents)
    return texte + f"\n\nDemande : {question}"


def extraire_lire(texte, strict=True):
    """Les chemins demandés dans un bloc [LIRE]…[/LIRE]."""
    m = re.search(r"\[LIRE\](.*?)(?:\[/LIRE\]|$)", texte or "", re.S | re.I)
    if m:
        return m.group(1).splitlines()
    return [] if strict else (texte or "").splitlines()


def associer_chemins(noms, arbre):
    """Retrouve les vrais chemins du projet, même si l'IA les écrit un peu croche."""
    en_minuscules = {c.lower(): c for c in arbre}
    par_nom = {}
    for c in arbre:
        par_nom.setdefault(Path(c).name.lower(), []).append(c)
    trouves = []
    for nom in noms:
        nom = re.sub(r"\s*\(.*\)\s*$", "", nom.strip().strip("-*•`'\" ")).strip()
        nom = nom[2:] if nom.startswith("./") else nom
        nom = nom.lstrip("/")
        if not nom:
            continue
        chemin = arbre.get(nom) and nom or en_minuscules.get(nom.lower())
        if not chemin:
            pareils = par_nom.get(Path(nom).name.lower(), [])
            chemin = pareils[0] if len(pareils) == 1 else None
        if chemin and chemin not in trouves:
            trouves.append(chemin)
    return trouves


def deviner_fichiers(question, arbre):
    """Plan B si l'IA choisit rien : les fichiers dont le nom revient dans la demande."""
    mots = {m.lower() for m in re.findall(r"[\w\-]{3,}", question)}
    scores = []
    for c, info in arbre.items():
        if not est_texte(c):
            continue
        nom = Path(c).stem.lower()
        score = 3 * (nom in mots) + sum(1 for m in mots if m in c.lower())
        if score:
            scores.append((score, -info["taille"], c))
    return [c for _, _, c in sorted(scores, reverse=True)[:6]]


def contexte_codex(depot, branche, arbre, fichiers, budget):
    """Prépare ce que l'IA voit : l'arborescence + le contenu des fichiers (tant qu'il reste de la place).
    Retourne (texte, chemins vraiment inclus)."""
    if depot:
        chemins = sorted(arbre)
        liste = "\n".join(chemins[:600]) + ("\n…" if len(chemins) > 600 else "")
        parties = [f"Projet GitHub : {depot} (branche {branche}), {len(chemins)} fichiers.\n"
                   f"Arborescence :\n{liste}"]
    else:
        parties = ["Pas de projet GitHub ouvert. Les fichiers que tu écris vont s'ouvrir dans l'éditeur."]
    total, inclus, omis = len(parties[0]), [], []
    for chemin, contenu, note in fichiers:
        bloc = f"--- {chemin} ({note}) ---\n{contenu}"
        if total + len(bloc) > budget:
            omis.append(chemin)
            continue
        parties.append(bloc)
        total += len(bloc)
        inclus.append(chemin)
    if omis:
        parties.append(f"(Pas inclus, faute de place : {', '.join(omis[:30])})")
    return "\n\n".join(parties), inclus


def agent_codex(question, historique, onglets, cache, arbre, depot, branche, token, budget, ia, progres):
    """Roule dans un fil à part. Choisit les fichiers, les lit sur GitHub, pis demande le code à l'IA.
    Retourne {"texte": réponse de l'IA, "lus": fichiers lus sur GitHub, "vus": fichiers montrés à l'IA}."""
    connus = dict(cache)
    connus.update(dict(onglets))    # un onglet ouvert a peut-être des changements pas enregistrés
    ouverts = [c for c, _ in onglets]
    lus = {}

    def lire(chemins):
        manquants = [c for c in chemins if c not in connus and c in arbre]
        if manquants:
            noms = ", ".join(Path(c).name for c in manquants[:5]) + ("…" if len(manquants) > 5 else "")
            progres(f"Codex lit {len(manquants)} fichier(s) : {noms}")
        for c in manquants:
            try:
                connus[c] = lus[c] = lire_blob(depot, arbre[c]["sha"], token)
            except UnicodeDecodeError:
                pass   # fichier binaire : on le saute

    choisis = []
    if depot:
        textes = [c for c, i in arbre.items() if est_texte(c) and i["taille"] <= 300_000]
        if sum(arbre[c]["taille"] for c in textes) <= budget * 0.7 and len(textes) <= 60:
            choisis = sorted(textes)   # petit projet : Codex lit tout
        else:
            progres("Codex cherche les bons fichiers…")
            reponse = ia([{"role": "user", "content": demande_selection(question, historique, arbre, ouverts)}],
                         instructions_selection(), 800)
            choisis = associer_chemins(extraire_lire(reponse, strict=False), arbre)[:10]
            choisis = choisis or deviner_fichiers(question, arbre)
        lire(choisis)

    texte, vus = "", []
    for tour in range(2):
        fichiers = [(c, connus[c], "ouvert à l'écran" if c in ouverts else "lu par Codex")
                    for c in dict.fromkeys(ouverts + choisis) if c in connus]
        contexte, vus = contexte_codex(depot, branche, arbre, fichiers, budget)
        envoi = [dict(m) for m in historique]
        envoi[-1]["content"] = contexte + "\n\nDemande : " + question
        progres("Codex écrit le code…")
        texte = ia(envoi, instructions_codex(), 16000)
        # L'IA peut demander d'autres fichiers avant d'écrire : on les lit pis on recommence une fois
        nouveaux = [c for c in associer_chemins(extraire_lire(texte), arbre) if c not in choisis] if depot else []
        if tour == 0 and nouveaux and "[FICHIER" not in texte.upper():
            choisis += nouveaux[:6]
            lire(nouveaux[:6])
            continue
        break
    return {"texte": texte, "lus": lus, "vus": vus}


# ---------- Moteur de schéma ----------
MOTS_PLAN = re.compile(
    r"\b(plan|étapes?|etapes?|stratégie|marche à suivre|comment (faire|je|on|lancer|commencer))\b",
    re.I)


def nettoyer_etape(ligne):
    # Enlève « - », « 1. », « 2) », « Étape 3 : »… (même s'il y en a plusieurs de suite)
    ligne = ligne.replace("**", "").strip()
    while True:
        propre = re.sub(r"^(?:[-•*]|\d+[.)]|étape\s*\d+\s*[:\-–]?)\s*", "", ligne, flags=re.I)
        if propre == ligne:
            return ligne
        ligne = propre


def raccourcir(texte, maxi=90):
    phrase = re.split(r"(?<=[.!?])\s", texte)[0]  # garde la première phrase
    return phrase if len(phrase) <= maxi else phrase[:maxi - 1].rstrip() + "…"


def extraire_plan(texte, question):
    """Sort les étapes d'un plan de la réponse. Retourne (texte_sans_le_bloc, étapes)."""
    m = re.search(r"\[PLAN\](.*?)(\[/PLAN\]|$)", texte, re.S | re.I)
    if m:
        etapes = [raccourcir(nettoyer_etape(l)) for l in m.group(1).splitlines()]
        etapes = [e for e in etapes if e]
        texte = (texte[:m.start()] + texte[m.end():]).strip()
        return texte, (etapes[:12] if len(etapes) >= 2 else [])
    # Plan de secours : une liste 1. 2. 3. quand la question parle d'un plan
    if MOTS_PLAN.search(question):
        items = re.findall(r"^\s*\d+[.)]\s+(.+)$", texte, re.M)
        if len(items) >= 3:
            return texte, [raccourcir(nettoyer_etape(i)) for i in items[:12]]
    return texte, []


class SchemaAnime(tk.Canvas):
    """Schéma d'un plan : des boîtes reliées par des lignes où passe un courant vert lime."""
    PAS_MS = 30            # vitesse de l'animation (plus petit = plus fluide)
    IMAGES_PAR_LIEN = 28   # temps pour que le courant passe d'une étape à l'autre
    PAUSE_FIN = 40         # pause quand le courant arrive à la dernière étape
    ESPACE = 44            # hauteur des lignes entre les boîtes

    def __init__(self, parent, etapes, largeur):
        super().__init__(parent, bg=GRIS_ZONE, highlightthickness=0, bd=0,
                         width=largeur, height=10, cursor="arrow")
        self.boites = []
        self.liens = []
        self.dessiner(etapes, largeur)
        self.lien_actif = 0
        self.progression = 0.0
        self.pause = 0
        self.allumer(0)
        self.after(500, self.animer)

    def rectangle_arrondi(self, x0, y0, x1, y1, r, **options):
        points = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
                  x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.create_polygon(points, smooth=True, **options)

    def dessiner(self, etapes, largeur):
        l_boite = min(largeur - 40, 560)
        x0 = (largeur - l_boite) / 2
        x1 = x0 + l_boite
        cx = largeur / 2
        y = 12
        bords = []   # (haut, bas) de chaque boîte
        for i, texte in enumerate(etapes):
            id_texte = self.create_text(x0 + 60, y, text=texte, anchor="nw", fill=NOIR,
                                        width=l_boite - 80, font=(FAMILLE, 12))
            gauche, haut, droite, bas = self.bbox(id_texte)
            h_texte = bas - haut
            h = max(h_texte + 28, 54)
            self.coords(id_texte, x0 + 60, y + (h - h_texte) / 2)
            boite = self.rectangle_arrondi(x0, y, x1, y + h, 14, fill=GRIS_BOITE,
                                           outline=GRIS_BORD, width=2)
            self.tag_lower(boite, id_texte)
            ny = y + h / 2
            self.create_oval(x0 + 16, ny - 15, x0 + 46, ny + 15, fill=ORANGE, outline="")
            self.create_text(x0 + 31, ny, text=str(i + 1), fill=NOIR, font=(FAMILLE, 11, "bold"))
            self.boites.append(boite)
            bords.append((y, y + h))
            y += h + self.ESPACE

        for (haut1, bas1), (haut2, bas2) in zip(bords, bords[1:]):
            ya, yb = bas1 + 2, haut2 - 2
            base = self.create_line(cx, ya, cx, yb, fill=GRIS_LIEN, width=3,
                                    arrow="last", arrowshape=(10, 12, 5))
            lueur = self.create_line(cx, ya, cx, ya, fill=LIME_LUEUR, width=10,
                                     capstyle="round", state="hidden")
            courant = self.create_line(cx, ya, cx, ya, fill=LIME, width=3,
                                       capstyle="round", state="hidden")
            etincelle = self.create_oval(cx - 5, ya - 5, cx + 5, ya + 5, fill="#eaffc4",
                                         outline=LIME, width=2, state="hidden")
            self.liens.append((cx, ya, yb, base, lueur, courant, etincelle))
        self.config(height=y - self.ESPACE + 12)

    def allumer(self, i):
        if i < len(self.boites):
            self.itemconfig(self.boites[i], outline=LIME, width=3)

    def reinitialiser(self):
        for boite in self.boites:
            self.itemconfig(boite, outline=GRIS_BORD, width=2)
        for cx, ya, yb, base, lueur, courant, etincelle in self.liens:
            self.itemconfig(base, fill=GRIS_LIEN)
            for item in (lueur, courant, etincelle):
                self.itemconfig(item, state="hidden")
        self.lien_actif = 0
        self.progression = 0.0
        self.allumer(0)

    def animer(self):
        try:
            if not self.winfo_exists() or not self.liens:
                return
            if self.pause > 0:
                self.pause -= 1
                if self.pause == 0:
                    self.reinitialiser()   # on recommence du début
            else:
                cx, ya, yb, base, lueur, courant, etincelle = self.liens[self.lien_actif]
                self.progression = min(1.0, self.progression + 1 / self.IMAGES_PAR_LIEN)
                yc = ya + (yb - ya) * self.progression
                self.coords(lueur, cx, ya, cx, yc)
                self.coords(courant, cx, ya, cx, yc)
                self.coords(etincelle, cx - 5, yc - 5, cx + 5, yc + 5)
                for item in (lueur, courant, etincelle):
                    self.itemconfig(item, state="normal")
                if self.progression >= 1:
                    # Le courant arrive : la ligne et la prochaine étape s'allument
                    self.itemconfig(base, fill=LIME)
                    self.itemconfig(etincelle, state="hidden")
                    self.lien_actif += 1
                    self.progression = 0.0
                    self.allumer(self.lien_actif)
                    if self.lien_actif >= len(self.liens):
                        self.pause = self.PAUSE_FIN
            self.after(self.PAS_MS, self.animer)
        except tk.TclError:
            return   # le schéma a été effacé


# ---------- Petits morceaux d'interface ----------
def numeros(version):
    """« 1.10.2 » devient (1, 10, 2), pour comparer deux versions comme du monde."""
    return tuple(int(n) for n in re.findall(r"\d+", version)) or (0,)


def version_du_texte(texte):
    """Lit le numéro de version écrit dans un ecriture.py."""
    trouve = re.search(r'^VERSION\s*=\s*"([^"]+)"', texte, re.M)
    return trouve.group(1) if trouve else ""


def chercher_maj(timeout=20):
    """Va voir sur GitHub s'il y a du neuf.

    Retourne (version, code_source) si une version plus récente existe,
    (None, "") si t'es déjà à jour, et lève une erreur si ça n'a pas marché.
    """
    requete = urllib.request.Request(URL_MAJ, headers={"User-Agent": f"Ecriture/{VERSION}"})
    with urllib.request.urlopen(requete, timeout=timeout) as reponse:
        texte = reponse.read().decode("utf-8")
    version = version_du_texte(texte)
    if not version:
        raise ValueError("Le fichier téléchargé n'a pas de numéro de version.")
    if numeros(version) <= numeros(VERSION):
        return None, ""
    return version, texte


def installer_maj(texte):
    """Remplace le script par la version téléchargée. Retourne le chemin de la sauvegarde.

    On vérifie que le code compile avant de toucher à quoi que ce soit, pis on garde
    l'ancienne version à côté : si jamais la nouvelle bogue, t'as juste à la renommer.
    """
    compile(texte, "ecriture.py", "exec")          # un fichier brisé ne passe pas
    moi = Path(__file__).resolve()
    neuf = moi.with_name(moi.name + ".neuf")
    neuf.write_text(texte, encoding="utf-8")
    sauvegarde = moi.with_name(moi.stem + "_precedent.py")
    sauvegarde.write_text(moi.read_text(encoding="utf-8"), encoding="utf-8")
    os.replace(neuf, moi)                          # remplacement d'un coup, sans trou
    moi.chmod(0o755)
    return sauvegarde


def maj_auto_active():
    """Par défaut oui : l'app se tient à jour toute seule."""
    if FICHIER_MAJ.exists():
        return FICHIER_MAJ.read_text(encoding="utf-8").strip() != "non"
    return True


def regler_maj_auto(active):
    DOSSIER_CONFIG.mkdir(parents=True, exist_ok=True)
    FICHIER_MAJ.write_text("oui" if active else "non", encoding="utf-8")


def bouton_orange(parent, texte, commande, taille=11):
    return tk.Button(
        parent, text=texte, command=commande,
        bg=ORANGE, fg=NOIR, activebackground=ORANGE_FONCE, activeforeground=NOIR,
        font=(FAMILLE, taille, "bold"), relief="flat", bd=0, highlightthickness=0,
        padx=16 if taille >= 11 else 9, pady=8 if taille >= 11 else 3, cursor="hand2",
    )


def style_zone(taille=14):
    return dict(
        bg=GRIS_ZONE, fg=NOIR, insertbackground=NOIR,
        selectbackground=ORANGE, selectforeground=NOIR,
        font=(FAMILLE, taille), relief="flat", bd=0, wrap="word",
        highlightthickness=2, highlightbackground=GRIS_BORD, highlightcolor=ORANGE,
        padx=14 if taille >= 14 else 10, pady=10 if taille >= 14 else 8,
    )


def barre_defilement(parent, orientation, fond=GRIS_MENU, command=None):
    return tk.Scrollbar(parent, orient=orientation, command=command, bg="#5f5f5f",
                        troughcolor=fond, activebackground=ORANGE, relief="flat", bd=0,
                        width=12, elementborderwidth=0, highlightthickness=0)


class IAGratuites(tk.Toplevel):
    """Explique comment avoir des IA gratuites, pis laisse choisir laquelle installer."""

    def __init__(self, app):
        super().__init__(app, bg=GRIS_FOND, padx=24, pady=16)
        self.app = app
        self.title("IA gratuites")
        self.resizable(False, False)
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.fermer)
        self.bind("<Escape>", lambda e: self.fermer())

        tk.Label(self, text="IA gratuites", bg=GRIS_FOND, fg=NOIR,
                 font=(FAMILLE, 16, "bold")).pack(anchor="w")
        tk.Label(self, bg=GRIS_FOND, fg=NOIR, justify="left", font=(FAMILLE, 10),
                 wraplength=520,
                 text="Elles tournent sur ton ordi, sans compte ni carte de crédit, et sans "
                      "Internet. Il faut Ollama, pis au moins un modèle téléchargé.").pack(
            anchor="w", pady=(2, 10))

        self.etat = tk.Label(self, bg=GRIS_ZONE, fg=NOIR, font=(FAMILLE, 11), anchor="w",
                             padx=14, pady=8, justify="left")
        self.etat.pack(fill="x", pady=(0, 10))

        self.marche_a_suivre = tk.Frame(self, bg=GRIS_FOND)
        self.marche_a_suivre.pack(fill="x")

        tk.Label(self, text="Choisis un modèle à installer", bg=GRIS_FOND, fg=NOIR,
                 font=(FAMILLE, 12, "bold")).pack(anchor="w", pady=(2, 1))
        tk.Label(self, bg=GRIS_FOND, fg=NOIR, font=(FAMILLE, 10), justify="left",
                 wraplength=520,
                 text="« Copier » met la commande dans le presse-papier : colle-la dans un "
                      "terminal. Le modèle apparaît ensuite tout seul dans le menu.").pack(
            anchor="w", pady=(0, 6))

        self.rangs = {}
        for nom, taille, description in MODELES_SUGGERES:
            self.construire_rang(nom, taille, description)

        self.mot = tk.Label(self, text="", bg=GRIS_FOND, fg=NOIR, font=(FAMILLE, 10), anchor="w")
        self.mot.pack(fill="x", pady=(8, 6))
        rang = tk.Frame(self, bg=GRIS_FOND)
        rang.pack(fill="x")
        bouton_orange(rang, "Fermer", self.fermer).pack(side="right")
        bouton_orange(rang, "Rafraîchir", self.rafraichir).pack(side="right", padx=(0, 10))

        self.rafraichir()
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = max(app.winfo_rooty() + 30, 0)
        self.geometry(f"+{max(x, 0)}+{y}")

    def construire_rang(self, nom, taille, description):
        cadre = tk.Frame(self, bg=GRIS_ZONE, padx=14, pady=6)
        cadre.pack(fill="x", pady=(0, 5))
        haut = tk.Frame(cadre, bg=GRIS_ZONE)
        haut.pack(fill="x")
        tk.Label(haut, text=nom, bg=GRIS_ZONE, fg=NOIR,
                 font=(FAMILLE, 12, "bold")).pack(side="left")
        tk.Label(haut, text=f"   {taille}", bg=GRIS_ZONE, fg="#4a4a4a",
                 font=(FAMILLE, 10)).pack(side="left")
        marque = tk.Label(haut, text="", bg=GRIS_ZONE, font=(FAMILLE, 10, "bold"))
        marque.pack(side="right", padx=(8, 0))
        bouton = bouton_orange(haut, "Copier", lambda n=nom: self.copier(n), taille=9)
        bouton.pack(side="right")
        tk.Label(cadre, text=description, bg=GRIS_ZONE, fg=NOIR, font=(FAMILLE, 10),
                 anchor="w", justify="left", wraplength=500).pack(fill="x", pady=(1, 0))
        self.rangs[nom] = (marque, bouton)

    def copier(self, nom):
        commande = f"ollama pull {nom}"
        self.clipboard_clear()
        self.clipboard_append(commande)
        self.mot.config(text=f"Copié : {commande}   — colle-le dans un terminal.")

    def rafraichir(self):
        installes = modeles_ollama()
        courts = {n.removesuffix(":latest").split(":")[0] for n in installes}
        if not ollama_repond():
            self.etat.config(
                text="Ollama ne répond pas sur cet ordi.\n"
                     "Installe-le, puis démarre-le : c'est expliqué juste en dessous.")
            self.montrer_marche_a_suivre(True)
        elif installes:
            self.etat.config(text=f"Ollama répond ✓   {len(installes)} modèle(s) installé(s) : "
                                  + ", ".join(n.removesuffix(":latest") for n in installes[:6]))
            self.montrer_marche_a_suivre(False)
        else:
            self.etat.config(text="Ollama répond ✓   mais aucun modèle n'est téléchargé.\n"
                                  "Choisis-en un dans la liste, en bas.")
            self.montrer_marche_a_suivre(False)
        for nom, (marque, bouton) in self.rangs.items():
            pose = nom in courts
            marque.config(text="installé ✓" if pose else "", fg="#1d5e00")
            bouton.config(text="Réinstaller" if pose else "Copier")
        self.app.rafraichir_moteurs_partout()

    def montrer_marche_a_suivre(self, visible):
        for w in self.marche_a_suivre.winfo_children():
            w.destroy()
        if not visible:
            return
        tk.Label(self.marche_a_suivre, text="1.  Installe Ollama (gratuit, quelques clics)",
                 bg=GRIS_FOND, fg=NOIR, font=(FAMILLE, 11), anchor="w").pack(fill="x")
        bouton_orange(self.marche_a_suivre, "Ouvrir ollama.com",
                      lambda: webbrowser.open("https://ollama.com/download"),
                      taille=9).pack(anchor="w", pady=(3, 7))
        tk.Label(self.marche_a_suivre, text="2.  Démarre-le dans un terminal :",
                 bg=GRIS_FOND, fg=NOIR, font=(FAMILLE, 11), anchor="w").pack(fill="x")
        rang = tk.Frame(self.marche_a_suivre, bg=GRIS_FOND)
        rang.pack(fill="x", pady=(3, 9))
        tk.Label(rang, text="  ollama serve  ", bg=GRIS_ZONE, fg=NOIR,
                 font=(FAMILLE_CODE, 11)).pack(side="left", ipady=4)
        bouton_orange(rang, "Copier", self.copier_serve, taille=9).pack(side="left", padx=(8, 0))

    def copier_serve(self):
        self.clipboard_clear()
        self.clipboard_append("ollama serve")
        self.mot.config(text="Copié : ollama serve   — colle-le dans un terminal.")

    def fermer(self):
        self.app.fenetre_ia = None
        self.destroy()


# ---------- Le logo de l'agent ----------
# ---------- Le logo de l'agent ----------
class LogoAgent:
    """Le logo Marceau : au centre au début, il glisse à gauche quand l'agent commence à répondre."""
    ETAPES = 32   # nombre d'images de l'animation (plus = plus lent et plus doux)

    def __init__(self, app):
        self.app = app
        self.images = {}   # taille -> image
        if Image is not None:
            # « RGBa » : la transparence reste propre quand on rapetisse le logo
            source = Image.open(FICHIER_LOGO).convert("RGBa")
            for taille in set(range(LOGO_GAUCHE, LOGO_CENTRE + 1, 2)) | {LOGO_CENTRE, LOGO_AVATAR}:
                petit = source.resize((taille, taille), Image.LANCZOS).convert("RGBA")
                self.images[taille] = ImageTk.PhotoImage(petit, master=app)
        else:
            # Sans Pillow : Tkinter peut juste diviser la taille par un nombre entier
            base = tk.PhotoImage(file=str(FICHIER_LOGO), master=app)
            for facteur in range(2, 25):
                image = base.subsample(facteur)
                self.images[image.width()] = image
        self.label = tk.Label(app, bg=GRIS_FOND, bd=0, highlightthickness=0)
        self.position = "cache"
        self.suivi = False      # True = le logo se tient à côté de la réponse de l'agent
        self.y_actuel = HAUT_DOC + LOGO_GAUCHE / 2

    def image(self, taille):
        return self.images[min(self.images, key=lambda t: abs(t - taille))]

    def decalage_centre(self):
        # Juste au-dessus de la boîte d'écriture centrée
        self.app.update_idletasks()
        return -(self.app.zone_saisie.winfo_reqheight() / 2 + 22 + LOGO_CENTRE / 2)

    def au_centre(self):
        self.label.config(image=self.image(LOGO_CENTRE))
        self.label.place(relx=0.5, rely=0.5, x=0, y=self.decalage_centre(), anchor="center")
        self.position = "centre"

    def a_gauche(self):
        self.label.config(image=self.image(LOGO_GAUCHE))
        self.position = "gauche"
        self.recaler(anime=True)

    def placer_gauche(self, y):
        self.y_actuel = y
        self.label.place(relx=(1 - LARGEUR) / 4, rely=0, x=0, y=y, anchor="center")

    def suivre(self, index, anime=True):
        """Le logo va se placer à côté de la réponse qui commence à cet endroit."""
        doc = self.app.document
        doc.mark_set("logo_suivi", index)
        doc.mark_gravity("logo_suivi", "left")
        self.suivi = True
        self.recaler(anime)

    def arreter_suivi(self):
        self.suivi = False

    def y_cible(self):
        doc = self.app.document
        if not self.suivi or not doc.winfo_ismapped():
            return HAUT_DOC + LOGO_GAUCHE / 2
        haut, hauteur = doc.winfo_y(), doc.winfo_height()
        info = doc.bbox("logo_suivi")
        if info:
            y = haut + info[1]
        elif doc.compare("logo_suivi", "<", "@0,0"):
            y = haut                          # la réponse est plus haut : le logo reste en haut
        else:
            y = haut + hauteur - LOGO_GAUCHE  # plus bas : il attend en bas
        y = max(haut, min(y, haut + hauteur - LOGO_GAUCHE))
        return y + LOGO_GAUCHE / 2

    def recaler(self, anime=False):
        """Replace le logo à côté de la réponse (appelé quand la conversation défile)."""
        if self.position != "gauche":
            return
        if "logo_suivi" in self.app._anims:
            return   # il est déjà en train de bouger; il se recalera en arrivant
        cible = self.y_cible()
        if anime and abs(cible - self.y_actuel) > 2:
            self.app.animer("logo_suivi", self.y_actuel, cible, self.placer_gauche,
                            lambda: self.recaler(False), etapes=18, douce=True)
        else:
            self.placer_gauche(cible)

    def glisser(self, vers_gauche=True):
        """Fait glisser le logo en douceur (il rapetisse en allant à gauche, grossit en revenant)."""
        app = self.app
        app.update_idletasks()
        largeur, hauteur = app.winfo_width(), app.winfo_height()
        centre = (largeur / 2, hauteur / 2 + self.decalage_centre(), LOGO_CENTRE)
        gauche = (largeur * (1 - LARGEUR) / 4, HAUT_DOC + LOGO_GAUCHE / 2, LOGO_GAUCHE)
        (x0, y0, t0), (x1, y1, t1) = (centre, gauche) if vers_gauche else (gauche, centre)
        self.position = "en route"

        def appliquer(p):
            self.y_actuel = y0 + (y1 - y0) * p
            self.label.config(image=self.image(t0 + (t1 - t0) * p))
            self.label.place(relx=0, rely=0, x=x0 + (x1 - x0) * p, y=self.y_actuel, anchor="center")

        app.animer("logo", 0.0, 1.0, appliquer, self.a_gauche if vers_gauche else self.au_centre,
                   etapes=self.ETAPES, ms=14, douce=True)


# ---------- Un fichier ouvert dans l'éditeur du Codex ----------
class Onglet:
    def __init__(self, codex, chemin, contenu, sha=None):
        self.codex = codex
        self.chemin = chemin
        self.sha = sha               # version sur GitHub (None = fichier pas encore sur GitHub)
        self.modifie = False
        self.langage = langage_de(chemin)
        self.minuterie = None

        self.cadre = tk.Frame(codex.zone_editeur, bg=CODE_FOND)
        self.numeros = tk.Canvas(self.cadre, width=56, bg=CODE_NUMEROS_FOND,
                                 highlightthickness=0, bd=0)
        self.defil_y = barre_defilement(self.cadre, "vertical", CODE_FOND)
        self.defil_x = barre_defilement(self.cadre, "horizontal", CODE_FOND)
        self.texte = tk.Text(
            self.cadre, wrap="none", undo=True, maxundo=-1, bg=CODE_FOND, fg=CODE_TEXTE,
            insertbackground=ORANGE, insertwidth=2, selectbackground=CODE_SELECTION,
            selectforeground="#ffffff", font=POLICE_CODE, relief="flat", bd=0,
            highlightthickness=0, padx=10, pady=6)
        self.texte.config(yscrollcommand=self.defilement, xscrollcommand=self.defil_x.set)
        self.defil_y.config(command=self.texte.yview)
        self.defil_x.config(command=self.texte.xview)
        self.numeros.grid(row=0, column=0, sticky="ns")
        self.texte.grid(row=0, column=1, sticky="nsew")
        self.defil_y.grid(row=0, column=2, sticky="ns")
        self.defil_x.grid(row=1, column=1, sticky="ew")
        self.cadre.grid_rowconfigure(0, weight=1)
        self.cadre.grid_columnconfigure(1, weight=1)

        self.texte.tag_configure("ligne_active", background=CODE_LIGNE_ACTIVE)
        for etiquette, (couleur, style) in COULEURS_CODE.items():
            police = (FAMILLE_CODE, POLICE_CODE[1], style) if style else POLICE_CODE
            self.texte.tag_configure(etiquette, foreground=couleur, font=police)
        self.texte.tag_raise("sel")

        self.texte.insert("1.0", contenu)
        self.texte.edit_reset()
        self.texte.edit_modified(False)
        self.texte.mark_set("insert", "1.0")

        self.texte.bind("<<Modified>>", self.sur_modification)
        self.texte.bind("<KeyRelease>", lambda e: self.planifier())
        self.texte.bind("<ButtonRelease-1>", lambda e: self.planifier())
        self.texte.bind("<Configure>", lambda e: self.planifier())
        self.texte.bind("<Tab>", self.tabulation)
        self.texte.bind("<Return>", self.entree)
        self.cadre.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.planifier()

    def contenu(self):
        return self.texte.get("1.0", "end-1c")

    def remplacer(self, contenu):
        """Met un nouveau contenu (celui de l'IA). Ctrl+Z revient à l'ancien."""
        self.texte.edit_separator()
        self.texte.delete("1.0", "end")
        self.texte.insert("1.0", contenu)
        self.texte.edit_separator()
        self.texte.mark_set("insert", "1.0")
        self.texte.see("1.0")
        self.planifier()

    def set_modifie(self, valeur):
        if valeur != self.modifie:
            self.modifie = valeur
            self.codex.dessiner_onglets()

    def sur_modification(self, event=None):
        if self.texte.edit_modified():
            self.set_modifie(True)
            self.texte.edit_modified(False)

    def tabulation(self, event):
        self.texte.insert("insert", "    ")
        return "break"

    def entree(self, event):
        # Garde l'indentation de la ligne d'avant (et en ajoute après « : » ou « { »)
        ligne = self.texte.get("insert linestart", "insert")
        retrait = re.match(r"[ \t]*", ligne).group(0)
        if ligne.rstrip().endswith((":", "{", "[", "(")):
            retrait += "    "
        self.texte.insert("insert", "\n" + retrait)
        self.texte.see("insert")
        self.planifier()
        return "break"

    def defilement(self, *args):
        self.defil_y.set(*args)
        if hasattr(self, "texte"):
            self.dessiner_numeros()
            self.planifier()

    def planifier(self):
        if self.minuterie:
            self.texte.after_cancel(self.minuterie)
        self.minuterie = self.texte.after(60, self.rafraichir)

    def rafraichir(self):
        self.minuterie = None
        try:
            self.colorer()
            self.texte.tag_remove("ligne_active", "1.0", "end")
            self.texte.tag_add("ligne_active", "insert linestart", "insert lineend+1c")
            self.texte.tag_lower("ligne_active")
            self.dessiner_numeros()
        except tk.TclError:
            pass   # l'onglet a été fermé

    def colorer(self):
        # On colore juste ce qui est à l'écran (± 200 lignes) : ça reste rapide même pour un gros fichier
        t = self.texte
        haut = int(t.index("@0,0").split(".")[0])
        bas = int(t.index(f"@0,{max(t.winfo_height(), 1)}").split(".")[0])
        debut, fin = max(1, haut - 200), bas + 200
        segment = t.get(f"{debut}.0", f"{fin}.end")
        for etiquette in COULEURS_CODE:
            t.tag_remove(etiquette, f"{debut}.0", f"{fin}.end")
        departs = [0] + [m.end() for m in re.finditer("\n", segment)]
        for a, b, etiquette in jetons(segment, self.langage):
            la = bisect_right(departs, a) - 1
            lb = bisect_right(departs, b) - 1
            t.tag_add(etiquette, f"{debut + la}.{a - departs[la]}", f"{debut + lb}.{b - departs[lb]}")

    def dessiner_numeros(self):
        c, t = self.numeros, self.texte
        c.delete("all")
        courante = t.index("insert").split(".")[0]
        i = t.index("@0,0")
        while True:
            info = t.dlineinfo(i)
            if info is None:
                break
            num = i.split(".")[0]
            c.create_text(48, info[1] + 1, anchor="ne", text=num, font=(FAMILLE_CODE, 11),
                          fill=ORANGE if num == courante else CODE_NUMEROS)
            suivant = t.index(f"{i}+1line")
            if suivant == i:
                break
            i = suivant


# ---------- Le code écrit par l'IA, dans un panneau qui s'ouvre d'un clic ----------
def colorer_tout(widget, texte, langage, taille):
    """Colore un texte au complet (pour les panneaux de code de l'assistant)."""
    for etiquette, (couleur, style) in COULEURS_CODE.items():
        widget.tag_configure(etiquette, foreground=couleur,
                             font=(FAMILLE_CODE, taille, style) if style else (FAMILLE_CODE, taille))
    texte = texte[:200_000]   # un fichier géant reste lisible, juste pas coloré au complet
    departs = [0] + [m.end() for m in re.finditer("\n", texte)]
    for a, b, etiquette in jetons(texte, langage):
        la = bisect_right(departs, a) - 1
        lb = bisect_right(departs, b) - 1
        widget.tag_add(etiquette, f"{1 + la}.{a - departs[la]}", f"{1 + lb}.{b - departs[lb]}")


class PanneauCode(tk.Frame):
    """Un fichier écrit par Codex : fermé au début, un clic sur la barre l'ouvre pis montre tout le code."""
    FOND_BARRE = "#333333"
    HAUTEUR_MAX = 380      # hauteur max du code une fois ouvert (après, ça défile)
    TAILLE = 10            # taille du code dans le panneau

    def __init__(self, parent, app, chemin, contenu, largeur, nouveau, ouvrir_editeur):
        super().__init__(parent, bg=self.FOND_BARRE)
        self.app = app
        self.ouvert = False
        lignes = contenu.count("\n") + (0 if contenu.endswith("\n") else 1)
        tk.Frame(self, width=largeur, height=0, bg=self.FOND_BARRE).pack()   # fixe la largeur

        # La barre garde toujours la même largeur, même avec un long nom de fichier
        barre = tk.Frame(self, bg=self.FOND_BARRE, cursor="hand2", width=largeur, height=36)
        barre.pack(fill="x")
        barre.pack_propagate(False)
        bouton_orange(barre, "Éditeur", lambda: ouvrir_editeur(chemin), taille=9).pack(side="right", padx=8)
        self.fleche = tk.Label(barre, text="▸", bg=self.FOND_BARRE, fg=ORANGE, font=(FAMILLE, 13, "bold"))
        self.fleche.pack(side="left", padx=(10, 6))
        titre = Path(chemin).name
        nom = tk.Label(barre, text=titre if len(titre) <= 26 else titre[:25] + "…", bg=self.FOND_BARRE,
                       fg="#f0f0f0", font=(FAMILLE, 10, "bold"), anchor="w")
        nom.pack(side="left")
        info = tk.Label(barre, text=f"{lignes} ligne{'s' if lignes > 1 else ''} · "
                                    f"{'nouveau' if nouveau else 'modifié'}",
                        bg=self.FOND_BARRE, fg="#a0a0a0", font=(FAMILLE, 9), anchor="w")
        info.pack(side="left", padx=(8, 0), fill="x", expand=True)
        for w in (barre, self.fleche, nom, info):
            w.bind("<Button-1>", self.basculer)

        # Le code (caché tant que le panneau est fermé)
        self.corps = tk.Frame(self, bg=CODE_FOND, height=1)
        self.corps.pack_propagate(False)
        defil_y = barre_defilement(self.corps, "vertical", CODE_FOND)
        defil_x = barre_defilement(self.corps, "horizontal", CODE_FOND)
        self.texte = tk.Text(self.corps, wrap="none", bg=CODE_FOND, fg=CODE_TEXTE,
                             font=(FAMILLE_CODE, self.TAILLE), relief="flat", bd=0, highlightthickness=0,
                             padx=10, pady=6, selectbackground=CODE_SELECTION, selectforeground="#ffffff",
                             insertwidth=0, yscrollcommand=defil_y.set, xscrollcommand=defil_x.set)
        defil_y.config(command=self.texte.yview)
        defil_x.config(command=self.texte.xview)
        defil_y.pack(side="right", fill="y")
        defil_x.pack(side="bottom", fill="x")
        self.texte.pack(side="left", fill="both", expand=True)
        self.texte.insert("1.0", contenu)
        colorer_tout(self.texte, contenu, langage_de(chemin), self.TAILLE)
        self.texte.config(state="disabled")   # on lit ici; on modifie dans l'éditeur
        hauteur_ligne = tkfont.Font(family=FAMILLE_CODE, size=self.TAILLE).metrics("linespace")
        self.cible = min(self.HAUTEUR_MAX, lignes * hauteur_ligne + 12 + 14)

    def basculer(self, event=None):
        self.ouvert = not self.ouvert
        self.fleche.config(text="▾" if self.ouvert else "▸")
        if self.ouvert and not self.corps.winfo_manager():
            self.corps.config(height=1)
            self.corps.pack(fill="x")
        depart = max(1, self.corps.winfo_height()) if self.corps.winfo_manager() else 1

        def fini():
            if not self.ouvert:
                self.corps.pack_forget()

        self.app.animer(f"panneau{id(self)}", depart, self.cible if self.ouvert else 1,
                        lambda v: self.corps.config(height=max(1, int(v))), fini, etapes=14)


# ---------- Le Codex : fichiers GitHub à gauche, éditeur au centre, assistant à droite ----------
class CodexVue(tk.Frame):
    L_FICHIERS = 250
    L_ASSISTANT = 380

    def __init__(self, app):
        super().__init__(app, bg=GRIS_FOND)
        self.app = app
        self.token = lire_secret(FICHIER_TOKEN, "GITHUB_TOKEN")
        self.depot = None            # « propriétaire/projet »
        self.branche = None
        self.arbre = {}              # chemin -> {"sha": …, "taille": …}
        self.cache = {}              # chemin -> contenu déjà lu sur GitHub
        self.depots = []
        self.onglets = []
        self.actif = None
        self.messages = []           # conversation avec l'assistant Codex
        self.occupe = False
        self.nb_liens = 0
        self.ouverts = {"fichiers": True, "assistant": True}

        self.construire_barre()
        self.etat_label = tk.Label(self, text="", anchor="w", bg=GRIS_MENU, fg=NOIR,
                                   font=(FAMILLE, 10), padx=14, pady=5)
        self.etat_label.pack(side="bottom", fill="x")
        self.construire_saisie()
        self.zone_bas.pack(side="bottom", fill="x")
        self.corps = tk.Frame(self, bg=GRIS_FOND)
        self.corps.pack(fill="both", expand=True)
        self.construire_fichiers()
        self.construire_assistant()
        self.construire_centre()
        self.panneau_fichiers.pack(side="left", fill="y")
        self.panneau_assistant.pack(side="right", fill="y")
        self.centre.pack(side="left", fill="both", expand=True)
        if self.token:
            self.etat("Choisis un projet GitHub en haut pour commencer.")
        else:
            self.etat("Ajoute ton token GitHub dans Paramètres (menu ☰, tout en bas) pour ouvrir tes projets.")

    # ----- Construction -----
    def construire_barre(self):
        barre = tk.Frame(self, bg=GRIS_FOND, height=64)
        barre.pack(side="top", fill="x")
        barre.pack_propagate(False)
        tk.Label(barre, text="Codex", bg=GRIS_FOND, fg=NOIR,
                 font=(FAMILLE, 16, "bold")).pack(side="left", padx=(74, 16))
        self.bouton_projet = bouton_orange(barre, "Projet  ▾", self.menu_projets)
        self.bouton_projet.pack(side="left", pady=13)
        bouton_orange(barre, "Scanner", self.scanner).pack(side="left", padx=(10, 0), pady=13)
        bouton_orange(barre, "Enregistrer", self.enregistrer_tout).pack(side="left", padx=(10, 0), pady=13)
        self.auto_push = tk.BooleanVar(value=pousser_auto())
        tk.Checkbutton(barre, text="Pousser tout seul", variable=self.auto_push,
                       command=self.changer_auto_push, bg=GRIS_FOND, fg=NOIR,
                       activebackground=GRIS_FOND, activeforeground=NOIR, selectcolor=GRIS_ZONE,
                       font=(FAMILLE, 9), relief="flat", bd=0, highlightthickness=0,
                       cursor="hand2").pack(side="left", padx=(12, 0), pady=13)
        bouton_orange(barre, "Fermer", self.app.fermer_codex).pack(side="right", padx=(10, 18), pady=13)
        self.bouton_assistant = bouton_orange(barre, "Assistant", lambda: self.basculer("assistant"))
        self.bouton_assistant.pack(side="right", padx=(10, 0), pady=13)
        self.bouton_fichiers = bouton_orange(barre, "Fichiers", lambda: self.basculer("fichiers"))
        self.bouton_fichiers.pack(side="right", pady=13)

    def construire_fichiers(self):
        p = self.panneau_fichiers = tk.Frame(self.corps, bg=GRIS_MENU, width=self.L_FICHIERS)
        p.pack_propagate(False)
        haut = tk.Frame(p, bg=GRIS_MENU)
        haut.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(haut, text="Fichiers", bg=GRIS_MENU, fg=NOIR,
                 font=(FAMILLE, 11, "bold")).pack(side="left")
        bouton_orange(haut, "+ Fichier", self.nouveau_fichier, taille=9).pack(side="right")

        style = ttk.Style(self)
        style.configure("Codex.Treeview", background=GRIS_MENU, fieldbackground=GRIS_MENU,
                        foreground=NOIR, font=(FAMILLE, 10), rowheight=24, borderwidth=0)
        style.map("Codex.Treeview", background=[("selected", ORANGE)],
                  foreground=[("selected", NOIR)])
        style.layout("Codex.Treeview", [("Codex.Treeview.treearea", {"sticky": "nswe"})])

        zone = tk.Frame(p, bg=GRIS_MENU)
        zone.pack(fill="both", expand=True, padx=(6, 0), pady=(0, 8))
        self.arbre_vue = ttk.Treeview(zone, style="Codex.Treeview", show="tree", selectmode="browse")
        defil = barre_defilement(zone, "vertical", command=self.arbre_vue.yview)
        self.arbre_vue.config(yscrollcommand=defil.set)
        defil.pack(side="right", fill="y")
        self.arbre_vue.pack(side="left", fill="both", expand=True)
        self.arbre_vue.bind("<<TreeviewSelect>>", self.sur_selection_fichier)
        self.vide_fichiers = tk.Label(zone, text="Choisis un projet GitHub\nen haut pour voir\nses fichiers.",
                                      bg=GRIS_MENU, fg=NOIR, font=(FAMILLE, 10), justify="center")
        self.vide_fichiers.place(relx=0.5, rely=0.3, anchor="center")

    def construire_assistant(self):
        p = self.panneau_assistant = tk.Frame(self.corps, bg=GRIS_FOND, width=self.L_ASSISTANT)
        p.pack_propagate(False)
        tk.Label(p, text="Assistant Codex", bg=GRIS_FOND, fg=NOIR, anchor="w",
                 font=(FAMILLE, 11, "bold")).pack(fill="x", padx=12, pady=(10, 6))
        self.chat = tk.Text(p, width=1, **style_zone(12))
        self.chat.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.app.configurer_tags(self.chat, 12, taille_reponse=13)
        self.chat.insert("end", "Demande-moi ce que tu veux changer dans ton projet. Pas besoin "
                                "d'ouvrir les fichiers : j'trouve moi-même les bons, j'les lis "
                                "pis j'les corrige.\n", "attente")

    def construire_saisie(self):
        """La boîte où tu écris, en bas au centre de l'écran, comme dans le chat."""
        zone = self.zone_bas = tk.Frame(self, bg=GRIS_FOND, height=118)
        zone.pack_propagate(False)
        centre = tk.Frame(zone, bg=GRIS_FOND)
        centre.place(relx=0.5, rely=0.5, anchor="center", relwidth=LARGEUR)
        ligne = tk.Frame(centre, bg=GRIS_FOND)
        ligne.pack(fill="x")
        bouton_orange(ligne, "Envoyer", self.envoyer).pack(side="right", padx=(10, 0), fill="y")
        self.saisie = tk.Text(ligne, height=2, width=1, **style_zone())
        self.saisie.pack(side="left", fill="x", expand=True)
        options = tk.Frame(centre, bg=GRIS_FOND)
        options.pack(fill="x", pady=(8, 0))
        self.app.creer_bouton_moteur(options).pack(side="left")
        self.saisie.bind("<Return>", self.envoyer)
        self.saisie.bind("<Shift-Return>", lambda e: (self.saisie.insert("insert", "\n"), "break")[1])

    def construire_centre(self):
        c = self.centre = tk.Frame(self.corps, bg=CODE_FOND)
        self.barre_onglets = tk.Frame(c, bg=GRIS_FOND, height=38)
        self.barre_onglets.pack(fill="x")
        self.barre_onglets.pack_propagate(False)
        self.zone_editeur = tk.Frame(c, bg=CODE_FOND)
        self.zone_editeur.pack(fill="both", expand=True)
        self.vide_editeur = tk.Label(self.zone_editeur, bg=CODE_FOND, fg="#8a8a8a",
                                     text="Ouvre un fichier à gauche,\nou demande du code à l'assistant.",
                                     font=(FAMILLE, 13), justify="center")
        self.vide_editeur.place(relx=0.5, rely=0.45, anchor="center")

    def etat(self, message):
        self.etat_label.config(text=message)

    def changer_auto_push(self):
        """Quand c'est coché, le Codex envoie ses changements sur GitHub sans rien demander."""
        actif = self.auto_push.get()
        regler_pousser_auto(actif)
        self.etat("Le Codex va pousser ses changements sur GitHub tout seul." if actif else
                  "Le Codex écrit dans les onglets; c'est toi qui cliques Enregistrer.")

    # ----- Panneaux qui s'ouvrent et se ferment -----
    def basculer(self, quel):
        if quel == "fichiers":
            p, largeur, bouton, cote = self.panneau_fichiers, self.L_FICHIERS, self.bouton_fichiers, "left"
        else:
            p, largeur, bouton, cote = self.panneau_assistant, self.L_ASSISTANT, self.bouton_assistant, "right"
        ouvrir = not self.ouverts[quel]
        self.ouverts[quel] = ouvrir
        bouton.config(bg=ORANGE if ouvrir else GRIS_INACTIF)
        if ouvrir and not p.winfo_manager():
            p.config(width=1)
            p.pack(side=cote, fill="y", before=self.centre)
        depart = p.winfo_width() if p.winfo_width() > 1 else 1

        def fini():
            if not ouvrir:
                p.pack_forget()

        self.app.animer(quel, depart, largeur if ouvrir else 1,
                        lambda v: p.config(width=max(1, int(v))), fini, etapes=14)

    # ----- GitHub : projets -----
    def nouveau_token(self, token):
        """Appelé par Paramètres quand le token change."""
        self.token = token
        self.depots = []
        self.etat("Token enregistré. Choisis un projet en haut." if token else
                  "Plus de token GitHub. Ajoutes-en un dans Paramètres pour ouvrir tes projets.")

    def menu_projets(self):
        if not self.token:
            self.etat("Ajoute d'abord ton token GitHub dans Paramètres.")
            self.app.ouvrir_parametres("github")
            return
        if self.depots:
            self.afficher_menu_projets()
            return
        self.etat("Chargement de tes projets GitHub…")
        token = self.token
        self.app.en_arriere_plan(
            lambda: github("GET", "/user/repos?per_page=100&sort=updated", token), self.depots_recus)

    def depots_recus(self, depots, err):
        if err:
            self.etat(erreur_github(err))
            return
        self.depots = depots or []
        if not self.depots:
            self.etat("Aucun projet trouvé avec ce token.")
            return
        self.etat(f"{len(self.depots)} projets trouvés.")
        self.afficher_menu_projets()

    def afficher_menu_projets(self):
        menu = tk.Menu(self, tearoff=0, bg=GRIS_ZONE, fg=NOIR, activebackground=ORANGE,
                       activeforeground=NOIR, font=(FAMILLE, 11), bd=0, relief="flat")
        for d in self.depots[:40]:
            menu.add_command(label=d["full_name"], command=lambda d=d: self.ouvrir_depot(
                d["full_name"], d.get("default_branch") or "main"))
        menu.add_separator()
        menu.add_command(label="Recharger la liste", command=self.recharger_depots)
        b = self.bouton_projet
        menu.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())

    def recharger_depots(self):
        self.depots = []
        self.menu_projets()

    def ouvrir_depot(self, nom, branche):
        if any(o.modifie for o in self.onglets) and not messagebox.askyesno(
                "Changer de projet", "Des fichiers ont des changements pas enregistrés.\n"
                "Changer de projet quand même?", parent=self):
            return
        self.etat(f"Chargement de {nom}…")
        token = self.token

        def travail():
            data = github("GET", f"/repos/{nom}/git/trees/{urllib.parse.quote(branche, safe='')}"
                                 "?recursive=1", token)
            arbre = {e["path"]: {"sha": e["sha"], "taille": e.get("size", 0)}
                     for e in data.get("tree", []) if e.get("type") == "blob"}
            return arbre, data.get("truncated", False)

        self.app.en_arriere_plan(travail, lambda r, err: self.depot_recu(nom, branche, r, err))

    def depot_recu(self, nom, branche, resultat, err):
        if err:
            self.etat(erreur_github(err))
            return
        arbre, tronque = resultat
        for o in self.onglets:
            o.cadre.destroy()
        self.onglets, self.actif = [], None
        self.dessiner_onglets()
        self.vide_editeur.place(relx=0.5, rely=0.45, anchor="center")
        self.depot, self.branche, self.arbre, self.cache = nom, branche, arbre, {}
        self.bouton_projet.config(text=f"{nom.split('/')[-1][:22]}  ▾")
        self.remplir_arbre()
        self.etat(f"{nom} ({branche}) : {len(arbre)} fichiers."
                  + (" Liste incomplète (projet très gros)." if tronque else "")
                  + " Demande à l'assistant ce que tu veux changer : il trouve les fichiers tout seul.")

    def remplir_arbre(self):
        v = self.arbre_vue
        v.delete(*v.get_children())

        def cle_tri(chemin):   # dossiers avant fichiers, en ordre alphabétique
            parties = chemin.lower().split("/")
            return [(0, p) for p in parties[:-1]] + [(1, parties[-1])]

        for chemin in sorted(self.arbre, key=cle_tri):
            self.ajouter_au_arbre(chemin)
        if self.arbre:
            self.vide_fichiers.place_forget()

    def ajouter_au_arbre(self, chemin):
        v = self.arbre_vue
        parties = chemin.split("/")
        parent = ""
        for i, nom in enumerate(parties[:-1]):
            iid = "d:" + "/".join(parties[:i + 1])
            if not v.exists(iid):
                v.insert(parent, "end", iid=iid, text=nom + "/", open=False)
            parent = iid
        if not v.exists(chemin):
            v.insert(parent, "end", iid=chemin, text=parties[-1])

    # ----- Onglets -----
    def sur_selection_fichier(self, event=None):
        choix = self.arbre_vue.selection()
        if choix and not choix[0].startswith("d:"):
            self.ouvrir_fichier(choix[0])

    def trouver_onglet(self, chemin):
        return next((o for o in self.onglets if o.chemin == chemin), None)

    def creer_onglet(self, chemin, contenu, sha=None):
        o = Onglet(self, chemin, contenu, sha)
        self.onglets.append(o)
        return o

    def ouvrir_fichier(self, chemin):
        o = self.trouver_onglet(chemin)
        if o:
            self.activer(o)
            return
        info = self.arbre.get(chemin)
        if info is None:
            return
        if info["taille"] > 2_000_000:
            self.etat("Fichier trop gros pour l'éditeur (plus de 2 Mo).")
            return
        if chemin in self.cache:
            self.activer(self.creer_onglet(chemin, self.cache[chemin], info["sha"]))
            return
        self.etat(f"Ouverture de {chemin}…")
        depot, token, sha = self.depot, self.token, info["sha"]
        self.app.en_arriere_plan(lambda: lire_blob(depot, sha, token),
                                 lambda texte, err: self.fichier_recu(depot, chemin, sha, texte, err))

    def fichier_recu(self, depot, chemin, sha, texte, err):
        if err:
            self.etat(erreur_github(err))
            return
        if depot != self.depot:
            return   # on a changé de projet entre-temps
        self.cache[chemin] = texte
        self.activer(self.trouver_onglet(chemin) or self.creer_onglet(chemin, texte, sha))

    def activer(self, onglet):
        self.actif = onglet
        onglet.cadre.tkraise()
        self.vide_editeur.place_forget()
        self.dessiner_onglets()
        onglet.texte.focus_set()
        onglet.planifier()
        self.etat(onglet.chemin + ("" if onglet.sha else "   (pas encore sur GitHub)"))

    def activer_chemin(self, chemin):
        o = self.trouver_onglet(chemin)
        if o:
            self.activer(o)

    def dessiner_onglets(self):
        for w in self.barre_onglets.winfo_children():
            w.destroy()
        for o in self.onglets:
            actif = o is self.actif
            fond = ORANGE if actif else GRIS_INACTIF
            cadre = tk.Frame(self.barre_onglets, bg=fond)
            cadre.pack(side="left", padx=(6, 0), pady=(6, 0), fill="y")
            nom = Path(o.chemin).name + ("  ●" if o.modifie else "")
            for texte, action, police in (
                    (nom, lambda o=o: self.activer(o), (FAMILLE, 10, "bold" if actif else "normal")),
                    ("×", lambda o=o: self.fermer_onglet(o), (FAMILLE, 12, "bold"))):
                tk.Button(cadre, text=texte, command=action, bg=fond, fg=NOIR,
                          activebackground=ORANGE_FONCE, relief="flat", bd=0, highlightthickness=0,
                          font=police, padx=8, cursor="hand2").pack(side="left", fill="y")

    def fermer_onglet(self, onglet):
        if onglet.modifie and not messagebox.askyesno(
                "Fermer", f"{onglet.chemin} a des changements pas enregistrés.\n"
                          "Fermer quand même?", parent=self):
            return
        i = self.onglets.index(onglet)
        self.onglets.remove(onglet)
        onglet.cadre.destroy()
        if self.actif is onglet:
            self.actif = None
            if self.onglets:
                self.activer(self.onglets[min(i, len(self.onglets) - 1)])
                return
            self.vide_editeur.place(relx=0.5, rely=0.45, anchor="center")
        self.dessiner_onglets()

    def nouveau_fichier(self):
        chemin = simpledialog.askstring("Nouveau fichier",
                                        "Chemin du fichier dans le projet (ex. : src/app.py) :",
                                        parent=self)
        if not chemin or not chemin.strip():
            return
        chemin = chemin.strip().lstrip("/")
        if chemin in self.arbre:
            self.ouvrir_fichier(chemin)   # il existe déjà : on l'ouvre au lieu de l'écraser
            return
        o = self.trouver_onglet(chemin) or self.creer_onglet(chemin, "")
        o.set_modifie(True)
        self.activer(o)

    # ----- Enregistrer sur GitHub -----
    def enregistrer_actif(self):
        self.enregistrer([self.actif] if self.actif else [])

    def enregistrer_tout(self):
        self.enregistrer(self.onglets)

    def enregistrer(self, onglets):
        onglets = [o for o in onglets if o.modifie]
        if not onglets:
            self.etat("Rien à enregistrer : aucun fichier modifié.")
            return
        if not self.depot:   # pas de projet GitHub ouvert : on sauvegarde sur l'ordi
            for o in onglets:
                chemin = filedialog.asksaveasfilename(title="Enregistrer sur l'ordi",
                                                      initialfile=Path(o.chemin).name, parent=self)
                if chemin:
                    Path(chemin).write_text(o.contenu(), encoding="utf-8")
                    o.set_modifie(False)
            return
        envois = [(o, o.chemin, o.contenu(), o.sha) for o in onglets]
        depot, branche, token = self.depot, self.branche, self.token
        self.etat(f"Envoi sur GitHub de {len(envois)} fichier(s)…")

        def travail():
            resultats = []
            for o, chemin, contenu, sha in envois:
                corps = {"message": f"Codex : {'mise à jour' if sha else 'création'} de {chemin}",
                         "content": base64.b64encode(contenu.encode("utf-8")).decode("ascii"),
                         "branch": branche}
                if sha:
                    corps["sha"] = sha
                try:
                    rep = github("PUT", f"/repos/{depot}/contents/{urllib.parse.quote(chemin)}",
                                 token, corps)
                    resultats.append((o, chemin, contenu, rep["content"]["sha"], None))
                except Exception as e:
                    resultats.append((o, chemin, contenu, None, e))
            return resultats

        self.app.en_arriere_plan(travail, lambda r, err: self.enregistre(depot, r, err))

    def enregistre(self, depot, resultats, err):
        if err:
            self.etat(erreur_github(err))
            return
        reussis, erreur = [], None
        for o, chemin, contenu, sha, e in resultats:
            if e:
                erreur = erreur or f"{chemin} : {erreur_github(e)}"
                continue
            reussis.append(Path(chemin).name)
            if depot == self.depot:
                self.arbre[chemin] = {"sha": sha, "taille": len(contenu.encode("utf-8"))}
                self.cache[chemin] = contenu
                self.ajouter_au_arbre(chemin)
            o.sha = sha
            if o.contenu() == contenu:   # pas retouché pendant l'envoi
                o.set_modifie(False)
        message = f"Enregistré sur GitHub : {', '.join(reussis)}." if reussis else ""
        self.etat((message + "  " + erreur) if erreur else message)
        if self.auto_push.get() and (reussis or erreur):
            self.chat.insert("end", (message or "") + ("  " + erreur if erreur else "") + "\n",
                             "sources")
            self.chat.see("end")

    # ----- Scanner tout le projet -----
    def scanner(self):
        if not self.depot:
            self.etat("Choisis un projet GitHub d'abord.")
            return
        a_lire = {c: i["sha"] for c, i in sorted(self.arbre.items())
                  if est_texte(c) and i["taille"] <= 150_000 and c not in self.cache}
        a_lire = dict(list(a_lire.items())[:250])
        if not a_lire:
            self.etat(f"Projet déjà scanné : {len(self.cache)} fichiers lus.")
            return
        depot, token, total = self.depot, self.token, len(a_lire)
        self.etat(f"Scan du projet : 0 / {total} fichiers…")

        def travail():
            lus = {}
            for n, (chemin, sha) in enumerate(a_lire.items(), 1):
                try:
                    lus[chemin] = lire_blob(depot, sha, token)
                except UnicodeDecodeError:
                    pass
                if n % 5 == 0 or n == total:
                    self.app.depuis_fil(lambda n=n: self.etat(f"Scan du projet : {n} / {total} fichiers…"))
            return lus

        def fini(lus, err):
            if err:
                self.etat(erreur_github(err))
                return
            if depot == self.depot:
                self.cache.update(lus)
                self.etat(f"Projet scanné : {len(self.cache)} fichiers lus. "
                          "L'assistant voit maintenant tout le code.")

        self.app.en_arriere_plan(travail, fini)

    # ----- L'assistant Codex -----
    def maj_attente(self, message):
        zone = self.chat.tag_ranges("attente")
        if zone:
            self.chat.delete(zone[0], zone[1])
            self.chat.insert(zone[0], message + "\n", "attente")
            self.chat.see("end")

    def envoyer(self, event=None):
        if self.occupe:
            return "break"
        question = self.saisie.get("1.0", "end-1c").strip()
        if not question:
            return "break"
        moteur = self.app.moteurs.get(self.app.choix.get())
        if moteur is None:
            return "break"
        type_moteur, modele = moteur
        cle = ""
        if type_moteur == "claude":
            cle = lire_secret(FICHIER_CLE, "ANTHROPIC_API_KEY")
            if not cle:
                self.etat("Ajoute ta clé API Claude dans Paramètres, pis renvoie ta demande.")
                self.app.ouvrir_parametres("claude")
                return "break"
        self.saisie.delete("1.0", "end")
        if not self.ouverts["assistant"]:
            self.basculer("assistant")   # pour voir la réponse arriver
        if not self.messages:
            self.chat.delete("1.0", "end")   # enlève le mot d'accueil
        self.chat.insert("end", question + "\n", "question")
        self.messages.append({"role": "user", "content": question})
        historique = [dict(m) for m in self.messages[-8:]]
        while historique and historique[0]["role"] != "user":
            historique.pop(0)
        budget = CONTEXTE_CLAUDE if type_moteur == "claude" else CONTEXTE_OLLAMA
        # Une photo de ce qu'on a déjà (le fil à part touche pas à l'interface)
        ordre = ([self.actif] if self.actif else []) + [o for o in self.onglets if o is not self.actif]
        onglets = [(o.chemin, o.contenu()) for o in ordre]
        depot, branche, token = self.depot, self.branche, self.token
        arbre, cache = dict(self.arbre), dict(self.cache)
        self.chat.insert("end", f"Codex ({nom_court(moteur)}) regarde ton projet…\n", "attente")
        self.chat.see("end")
        self.occupe = True

        def ia(messages, systeme, max_tokens):
            if type_moteur == "claude":
                return appeler_claude(cle, messages, systeme, web=False, max_tokens=max_tokens,
                                      timeout=600, modele=modele)[0]
            return appeler_ollama(modele, messages, systeme, num_ctx=CTX_OLLAMA_CODEX)[0]

        def progres(message):
            self.app.depuis_fil(lambda: self.maj_attente(message))

        self.app.en_arriere_plan(
            lambda: agent_codex(question, historique, onglets, cache, arbre, depot, branche,
                                token, budget, ia, progres),
            lambda r, err: self.reponse(r, err, type_moteur, modele, depot))
        return "break"

    def reponse(self, resultat, err, type_moteur, modele, depot):
        zone = self.chat.tag_ranges("attente")
        if zone:
            self.chat.delete(zone[0], zone[1])
        if err:
            self.messages.pop()
            message = erreur_github(err) if "github" in str(getattr(err, "url", "")) else \
                message_erreur(err, type_moteur, modele)
            self.app.ecrire(self.chat, message, lambda: True, self.fin_reponse)
            return
        if depot != self.depot:
            self.messages.pop()
            self.app.ecrire(self.chat, "T'as changé de projet pendant que je travaillais, faque "
                                       "j'ai rien touché. Renvoie ta demande.", lambda: True, self.fin_reponse)
            return
        self.cache.update(resultat["lus"])
        explication, fichiers = extraire_fichiers(resultat["texte"] or "")
        ecrits = []   # (chemin, contenu, nouveau fichier?)
        for chemin, contenu in fichiers:
            nouveau = chemin.removeprefix("./").lstrip("/") not in self.arbre
            ecrits.append((self.appliquer_fichier(chemin, contenu), contenu, nouveau))
        resume = explication or ("C'est fait, regarde les fichiers." if ecrits else
                                 "Pas de réponse cette fois-ci. Reformule ta demande.")
        note = f"\n(Fichiers écrits : {', '.join(c for c, _, _ in ecrits)})" if ecrits else ""
        self.messages.append({"role": "assistant", "content": resume + note})
        self.app.ecrire(self.chat, resume, lambda: True,
                        lambda: self.fin_reponse(ecrits, resultat["vus"]))

    def appliquer_fichier(self, chemin, contenu):
        """Met le fichier écrit par l'IA dans un onglet (rien part sur GitHub avant « Enregistrer »)."""
        if chemin.startswith("./"):
            chemin = chemin[2:]
        chemin = chemin.lstrip("/")
        o = self.trouver_onglet(chemin)
        if o:
            o.remplacer(contenu)
        else:
            o = self.creer_onglet(chemin, contenu, self.arbre.get(chemin, {}).get("sha"))
        o.set_modifie(True)
        self.activer(o)
        return chemin

    def fin_reponse(self, ecrits=(), vus=()):
        if vus:
            noms = ", ".join(Path(c).name for c in vus[:8]) + (f" (+{len(vus) - 8})" if len(vus) > 8 else "")
            self.chat.insert("end", f"Fichiers lus : {noms}\n", "sources")
        chemins = [c for c, _, _ in ecrits]
        # Si t'as coché « Pousser tout seul », ça part sur GitHub sans rien demander.
        if chemins and self.depot and self.auto_push.get():
            self.chat.insert("end", "J'envoie ça sur GitHub…\n", "sources")
            self.chat.see("end")
            self.enregistrer([o for o in self.onglets if o.chemin in set(chemins)])
            self.occupe = False
            return
        largeur = max(self.chat.winfo_width() - 30, 260)
        for chemin, contenu, nouveau in ecrits:
            panneau = PanneauCode(self.chat, self.app, chemin, contenu, largeur, nouveau,
                                  self.activer_chemin)
            self.chat.window_create("end", window=panneau, pady=4)
            self.chat.insert("end", "\n")
        if ecrits:
            self.chat.insert("end", "Vérifie les changements, pis clique « Enregistrer » pour les "
                             "envoyer sur GitHub.\n" if self.depot else
                             "Clique « Enregistrer » pour les sauvegarder sur ton ordi.\n", "sources")
        self.chat.see("end")
        self.occupe = False


# ---------- L'application ----------
class AppEcriture(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Écriture")
        self.geometry("1100x720")
        self.minsize(960, 560)
        self.configure(bg=GRIS_FOND)
        ttk.Style(self).theme_use("clam")

        self.premiere_ligne = True
        self.en_animation = False
        self.occupe = False          # une réponse est en route
        self.generation = 0          # change à chaque nouvelle conversation
        self.messages = []           # la conversation (avec ses schémas et ses sources)
        self.session_id = None
        self.session_cree = None
        self.resultats = queue.Queue()
        self.taches = queue.Queue()  # travaux finis en arrière-plan (Codex, GitHub)
        self._anims = {}
        self.compteur = 0
        self.nb_liens = 0
        self.texte_attente = ""
        self.schemas = []
        self.question_en_cours = ""
        self.menu_ouvert = False
        self.menu_x = -LARGEUR_MENU
        self.page_x = 0              # 0 = page principale du menu, -LARGEUR_MENU = Paramètres
        self.champs = {}
        self.codex = None
        self.fenetre_ia = None
        self.boutons_moteur = []
        self.ids_sessions = []

        # --- Boutons du haut (cachés au début) ---
        self.barre = tk.Frame(self, bg=GRIS_FOND)
        bouton_orange(self.barre, "Sauvegarder", self.sauvegarder).pack(side="left", padx=(0, 10))
        bouton_orange(self.barre, "Nouveau", self.nouveau).pack(side="left")

        # --- Le logo de l'agent (s'il est à côté du script) ---
        self.logo = None
        if FICHIER_LOGO.exists():
            try:
                self.logo = LogoAgent(self)
            except Exception as e:
                print("Logo pas chargé :", e)

        # --- La conversation (cachée au début, modifiable) ---
        self.document = tk.Text(self, **style_zone())
        self.configurer_tags(self.document, retrait=LOGO_AVATAR + 12 if self.logo else 0,
                             taille_reponse=TAILLE_AGENT)
        self.document.config(yscrollcommand=self.sur_defilement_doc)
        self.document.bind("<Configure>", lambda e: self.sur_defilement_doc())
        self.nb_meteo = 0

        # --- La zone où on écrit (centrée au début) ---
        self.zone_saisie = tk.Frame(self, bg=GRIS_FOND)
        self.invite = tk.Label(self.zone_saisie, text="Pose une question…",
                               bg=GRIS_FOND, fg=NOIR, font=POLICE_INVITE)
        self.invite.pack(pady=(0, 14))
        self.ligne = tk.Frame(self.zone_saisie, bg=GRIS_FOND)
        self.ligne.pack(fill="x")
        bouton_orange(self.ligne, "Envoyer", self.envoyer).pack(side="right", padx=(10, 0), fill="y")
        self.saisie = tk.Text(self.ligne, height=2, width=1, **style_zone())
        self.saisie.pack(side="left", fill="x", expand=True)

        # --- Choix de l'IA, sous la boîte ---
        self.moteurs = trouver_moteurs()
        self.choix = tk.StringVar(value=self.moteur_de_depart())
        self.choix.trace_add("write", self.maj_boutons_moteur)
        self.options = tk.Frame(self.zone_saisie, bg=GRIS_FOND)
        self.options.pack(fill="x", pady=(8, 0))
        self.creer_bouton_moteur(self.options).pack(side="left")

        # --- Menu de gauche + bouton ☰ (toujours par-dessus le reste) ---
        self.construire_menu_lateral()

        self.saisie.bind("<Return>", self.envoyer)
        self.saisie.bind("<Shift-Return>", self.saut_de_ligne)
        self.bind("<Control-s>", self.ctrl_s)
        self.bind("<Escape>", lambda e: self.fermer_menu())
        self.protocol("WM_DELETE_WINDOW", self.quitter)

        self.centrer_saisie()
        if self.logo:
            self.logo.au_centre()
        self.saisie.focus_set()
        self.after(80, self.traiter_taches)
        self.after(300, self.charger_modeles_claude)
        self.after(1500, self.verifier_maj)   # sans déranger : ça se fait en arrière-plan

    def moteur_de_depart(self):
        """Un modèle gratuit s'il y en a un, sinon celui écrit dans MODELE_CLAUDE.
        Sans ça, on partirait sur Opus 5 — le plus cher — juste parce qu'il est premier."""
        for etiquette, (type_moteur, _) in self.moteurs.items():
            if type_moteur == "ollama":
                return etiquette
        for etiquette, (type_moteur, modele) in self.moteurs.items():
            if modele == MODELE_CLAUDE:
                return etiquette
        return next(iter(self.moteurs))

    # ---------- Outils ----------
    def configurer_tags(self, widget, taille=14, retrait=0, taille_reponse=None):
        taille_reponse = taille_reponse or taille
        widget.tag_configure("question", font=(FAMILLE, taille, "bold"), spacing1=14 if taille >= 14 else 10)
        widget.tag_configure("reponse", font=(FAMILLE, taille_reponse), spacing1=6, spacing3=4,
                             lmargin1=retrait, lmargin2=retrait)
        widget.tag_configure("attente", font=(FAMILLE, taille_reponse, "italic"), spacing1=6,
                             lmargin1=retrait, lmargin2=retrait)
        widget.tag_configure("sources", font=(FAMILLE, max(taille - 3, 9)), spacing1=2,
                             lmargin1=retrait, lmargin2=retrait)
        widget.tag_configure("avatar", spacing1=8)
        widget.tag_configure("lien", underline=True, foreground=COULEUR_LIEN)
        widget.tag_configure("curseur", foreground=ORANGE)
        widget.tag_bind("lien", "<Enter>", lambda e: widget.config(cursor="hand2"))
        widget.tag_bind("lien", "<Leave>", lambda e: widget.config(cursor="xterm"))

    def animer(self, cle, depart, fin, appliquer, apres=None, etapes=14, ms=12, douce=False):
        """Anime une valeur en douceur. Une nouvelle animation remplace l'ancienne.
        douce=True : part doucement, accélère, pis ralentit en arrivant."""
        self.annuler_animation(cle)

        def pas(i):
            x = i / etapes
            if douce:
                t = 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
            else:
                t = 1 - (1 - x) ** 3
            appliquer(depart + (fin - depart) * t)
            if i < etapes:
                self._anims[cle] = self.after(ms, pas, i + 1)
            else:
                self._anims.pop(cle, None)
                if apres:
                    apres()

        pas(1)

    def annuler_animation(self, cle):
        precedent = self._anims.pop(cle, None)
        if precedent:
            self.after_cancel(precedent)

    def en_arriere_plan(self, travail, rappel):
        """Roule travail() dans un fil à part, pis rappel(résultat, erreur) une fois fini."""
        def fil():
            try:
                resultat = travail()
                self.taches.put(lambda: rappel(resultat, None))
            except Exception as e:
                self.taches.put(lambda e=e: rappel(None, e))
        threading.Thread(target=fil, daemon=True).start()

    def depuis_fil(self, action):
        self.taches.put(action)

    def traiter_taches(self):
        try:
            while True:
                self.taches.get_nowait()()
        except queue.Empty:
            pass
        self.after(80, self.traiter_taches)

    def ecrire(self, widget, texte, continuer, suite):
        """Écrit un texte lettre par lettre, vite pis fluide, avec un curseur orange."""
        texte = liens_markdown_en_texte(texte)
        debut = widget.index("end-1c")
        widget.insert("end", "▌", "curseur")
        tours = max(1, int(DUREE_ECRITURE * 1000 / VITESSE_MS))
        paquet = max(1, -(-len(texte) // tours))   # plus c'est long, plus ça écrit de lettres à la fois
        position = 0

        def tour():
            nonlocal position
            if not continuer():
                return
            try:
                curseur = widget.tag_ranges("curseur")
            except tk.TclError:
                return
            if not curseur:
                return
            if position < len(texte):
                widget.insert(curseur[0], texte[position:position + paquet], "reponse")
                position += paquet
                widget.see("end")
                self.after(VITESSE_MS, tour)
            else:
                widget.delete(curseur[0], curseur[1])
                widget.insert("end", "\n", "reponse")
                self.lier_liens(widget, debut, "end-1c")
                suite()

        tour()

    def lier_liens(self, widget, debut, fin):
        """Rend cliquables les adresses web (https://… ou www.…) : un clic ouvre le site."""
        texte = widget.get(debut, fin)
        for m in URL_WEB.finditer(texte):
            url = nettoyer_url(m.group(0))
            if len(url) < 8:
                continue
            a, b = f"{debut}+{m.start()}c", f"{debut}+{m.start() + len(url)}c"
            etiquette = f"lien{self.nb_liens}"
            self.nb_liens += 1
            widget.tag_add("lien", a, b)
            widget.tag_add(etiquette, a, b)
            cible = url if url.lower().startswith("http") else "https://" + url
            widget.tag_bind(etiquette, "<Button-1>", lambda e, u=cible: webbrowser.open(u))

    def sur_defilement_doc(self, *args):
        if self.logo:
            self.logo.recaler()

    # ---------- Choix de l'IA ----------
    def creer_bouton_moteur(self, parent):
        bouton = tk.Menubutton(
            parent, text=f"{self.choix.get()}  ▾", bg=ORANGE, fg=NOIR,
            activebackground=ORANGE_FONCE, activeforeground=NOIR, font=(FAMILLE, 10, "bold"),
            relief="flat", bd=0, highlightthickness=0, padx=12, pady=5, cursor="hand2",
            direction="above")
        menu = tk.Menu(bouton, tearoff=0, bg=GRIS_ZONE, fg=NOIR, activebackground=ORANGE,
                       activeforeground=NOIR, font=(FAMILLE, 11), bd=0, relief="flat")
        menu.config(postcommand=lambda: self.remplir_menu_moteurs(menu))  # relit Ollama à chaque ouverture
        bouton["menu"] = menu
        self.remplir_menu_moteurs(menu, relire=False)
        self.boutons_moteur.append(bouton)
        return bouton

    def remplir_menu_moteurs(self, menu, relire=True):
        if relire:
            self.moteurs = trouver_moteurs()
        menu.delete(0, "end")
        for etiquette in self.moteurs:
            menu.add_command(label=etiquette, command=lambda e=etiquette: self.choix.set(e))
        if self.choix.get() not in self.moteurs:
            self.choix.set(next(iter(self.moteurs)))

    def maj_boutons_moteur(self, *args):
        for bouton in self.boutons_moteur:
            bouton.config(text=f"{self.choix.get()}  ▾")

    def ouvrir_ia_gratuites(self):
        if self.fenetre_ia is not None and self.fenetre_ia.winfo_exists():
            self.fenetre_ia.lift()
            self.fenetre_ia.focus_set()
        else:
            self.fenetre_ia = IAGratuites(self)
        self.fermer_menu()

    def charger_modeles_claude(self):
        """Si une clé est branchée, on remplace la liste d'en haut par celle de l'API."""
        cle = lire_secret(FICHIER_CLE, "ANTHROPIC_API_KEY")
        if not cle:
            return

        def recu(liste, err):
            global _modeles_claude_en_ligne
            if err or not liste:
                return   # pas grave : on garde la liste écrite dans le fichier
            _modeles_claude_en_ligne = liste
            self.rafraichir_moteurs_partout()

        self.en_arriere_plan(lambda: modeles_claude_en_ligne(cle), recu)

    def rafraichir_moteurs_partout(self):
        """Relit Ollama et remet les noms à jour sur tous les boutons de choix."""
        self.moteurs = trouver_moteurs()
        if self.choix.get() not in self.moteurs:
            self.choix.set(next(iter(self.moteurs)))
        self.maj_boutons_moteur()

    # ---------- Menu de gauche ----------
    def construire_menu_lateral(self):
        m = self.menu_lateral = tk.Frame(self, bg=GRIS_MENU)
        m.place(x=self.menu_x, y=0, width=LARGEUR_MENU, relheight=1)
        # Deux pages côte à côte : le menu principal pis Paramètres (qui glisse par-dessus)
        self.page_principale = tk.Frame(m, bg=GRIS_MENU)
        self.page_principale.place(x=0, y=0, width=LARGEUR_MENU, relheight=1)
        self.page_parametres = tk.Frame(m, bg=GRIS_MENU)
        self.page_parametres.place(x=LARGEUR_MENU, y=0, width=LARGEUR_MENU, relheight=1)
        self.construire_page_principale(self.page_principale)
        self.construire_page_parametres(self.page_parametres)
        bord = tk.Frame(m, bg="#5e5e5e", width=2)
        bord.place(relx=1, x=-2, y=0, relheight=1)
        bord.lift()

        self.bouton_menu = tk.Button(
            self, text="☰", command=self.basculer_menu, bg=ORANGE, fg=NOIR,
            activebackground=ORANGE_FONCE, activeforeground=NOIR, font=(FAMILLE, 16, "bold"),
            relief="flat", bd=0, highlightthickness=0, cursor="hand2")
        self.bouton_menu.place(x=15, y=14, width=46, height=38)

    # ---------- Menu de gauche ----------
    def construire_menu_lateral(self):
        m = self.menu_lateral = tk.Frame(self, bg=GRIS_MENU)
        m.place(x=self.menu_x, y=0, width=LARGEUR_MENU, relheight=1)
        # Deux pages côte à côte : le menu principal pis Paramètres (qui glisse par-dessus)
        self.page_principale = tk.Frame(m, bg=GRIS_MENU)
        self.page_principale.place(x=0, y=0, width=LARGEUR_MENU, relheight=1)
        self.page_parametres = tk.Frame(m, bg=GRIS_MENU)
        self.page_parametres.place(x=LARGEUR_MENU, y=0, width=LARGEUR_MENU, relheight=1)
        self.construire_page_principale(self.page_principale)
        self.construire_page_parametres(self.page_parametres)
        bord = tk.Frame(m, bg="#5e5e5e", width=2)
        bord.place(relx=1, x=-2, y=0, relheight=1)
        bord.lift()

        self.bouton_menu = tk.Button(
            self, text="☰", command=self.basculer_menu, bg=ORANGE, fg=NOIR,
            activebackground=ORANGE_FONCE, activeforeground=NOIR, font=(FAMILLE, 16, "bold"),
            relief="flat", bd=0, highlightthickness=0, cursor="hand2")
        self.bouton_menu.place(x=15, y=14, width=46, height=38)

    def bouton_nav(self, parent, icone, texte, commande):
        """Un des trois grands boutons du menu : pictogramme à gauche, nom à côté."""
        return tk.Button(parent, text=f"  {icone}   {texte}", command=commande, anchor="w",
                         bg=GRIS_INACTIF, fg=NOIR,
                         activebackground=ORANGE_FONCE, activeforeground=NOIR,
                         font=(FAMILLE, 13, "bold"), relief="flat", bd=0, highlightthickness=0,
                         padx=12, pady=12, cursor="hand2")

    def cadre_defilant(self, parent):
        """Un cadre qui défile : Paramètres tient même sur un écran de portable."""
        toile = tk.Canvas(parent, bg=GRIS_MENU, highlightthickness=0, bd=0)
        toile.pack(fill="both", expand=True)
        dedans = tk.Frame(toile, bg=GRIS_MENU)
        fenetre = toile.create_window((0, 0), window=dedans, anchor="nw")

        def redimensionner(_=None):
            toile.configure(scrollregion=toile.bbox("all"))
            toile.itemconfigure(fenetre, width=toile.winfo_width())

        dedans.bind("<Configure>", redimensionner)
        toile.bind("<Configure>", redimensionner)
        # La molette ne marche que quand la souris est au-dessus : ailleurs, elle
        # continue de faire défiler le texte comme d'habitude.
        def rouler(e):
            toile.yview_scroll(-1 if e.num == 4 or e.delta > 0 else 1, "units")

        def suivre(_):
            for touche in ("<Button-4>", "<Button-5>", "<MouseWheel>"):
                toile.bind_all(touche, rouler)

        def lacher(_):
            for touche in ("<Button-4>", "<Button-5>", "<MouseWheel>"):
                toile.unbind_all(touche)

        toile.bind("<Enter>", suivre)
        toile.bind("<Leave>", lacher)
        return dedans

    def separateur(self, parent, **pack):
        tk.Frame(parent, bg="#5e5e5e", height=2).pack(fill="x", padx=14, **pack)


    def separateur(self, parent, **pack):
        tk.Frame(parent, bg="#5e5e5e", height=2).pack(fill="x", padx=14, **pack)

    def construire_page_principale(self, p):
        tk.Frame(p, bg=GRIS_MENU, height=70).pack(fill="x")   # la place du bouton ☰
        # Les trois modes, de la même grosseur, en haut : on les voit d'un coup d'œil.
        self.nav_chat = self.bouton_nav(p, "\u270e", "Chat", self.aller_chat)
        self.nav_chat.pack(fill="x", padx=14, pady=(0, 8))
        self.nav_codex = self.bouton_nav(p, "\u25a4", "Codex", self.ouvrir_codex)
        self.nav_codex.pack(fill="x", padx=14, pady=(0, 8))
        self.nav_param = self.bouton_nav(p, "\u2699", "Paramètres",
                                         lambda: self.aller_page("parametres"))
        self.nav_param.pack(fill="x", padx=14)
        self.separateur(p, pady=18)
        # En dessous : juste tes conversations. Tout le réglage est dans Paramètres.
        bouton_orange(p, "+ Nouvelle conversation", self.nouveau).pack(
            fill="x", padx=14, pady=(0, 12))
        tk.Label(p, text="Conversations", bg=GRIS_MENU, fg=NOIR, anchor="w",
                 font=(FAMILLE, 10, "bold")).pack(fill="x", padx=16)
        self.liste_sessions = tk.Listbox(
            p, bg=GRIS_MENU, fg=NOIR, selectbackground=ORANGE, selectforeground=NOIR,
            font=(FAMILLE, 11), relief="flat", bd=0, highlightthickness=0, activestyle="none")
        self.liste_sessions.pack(fill="both", expand=True, padx=(8, 10), pady=6)
        self.liste_sessions.bind("<<ListboxSelect>>", self.sur_choix_session)
        self.liste_sessions.bind("<Button-3>", self.menu_session)
        self.maj_navigation()

    def construire_page_parametres(self, page):
        tk.Frame(page, bg=GRIS_MENU, height=70).pack(fill="x")
        haut = tk.Frame(page, bg=GRIS_MENU)
        haut.pack(fill="x", padx=14, pady=(0, 6))
        bouton_orange(haut, "‹ Retour", lambda: self.aller_page("principale"), taille=9).pack(side="left")
        tk.Label(haut, text="\u2699  Paramètres", bg=GRIS_MENU, fg=NOIR,
                 font=(FAMILLE, 13, "bold")).pack(side="left", padx=10)
        tk.Frame(page, bg="#5e5e5e", height=2).pack(fill="x", padx=14, pady=(8, 0))
        p = self.cadre_defilant(page)   # tout ce qui suit défile

        tk.Label(p, text="Tout ce qui se règle est ici. Le menu, lui, reste simple.",
                 bg=GRIS_MENU, fg="#2e2e2e", anchor="w", justify="left",
                 font=(FAMILLE, 9), wraplength=LARGEUR_MENU - 36).pack(fill="x", padx=16, pady=(8, 0))

        reglages = [
            ("claude", "Clé API Claude", FICHIER_CLE, "ANTHROPIC_API_KEY",
             "Pour « Claude + web ». Crée ta clé sur console.anthropic.com."),
            ("github", "Token GitHub", FICHIER_TOKEN, "GITHUB_TOKEN",
             "Pour le Codex. Sur github.com : Settings > Developer settings > Fine-grained "
             "tokens, avec la permission « Contents : Read and write »."),
        ]
        for quoi, titre, fichier, variable, aide in reglages:
            tk.Label(p, text=titre, bg=GRIS_MENU, fg=NOIR, anchor="w",
                     font=(FAMILLE, 11, "bold")).pack(fill="x", padx=16, pady=(14, 2))
            statut = tk.Label(p, bg=GRIS_MENU, fg=NOIR, anchor="w", justify="left",
                              font=(FAMILLE, 9), wraplength=LARGEUR_MENU - 36)
            statut.pack(fill="x", padx=16)
            entree = tk.Entry(p, show="•", bg=GRIS_ZONE, fg=NOIR, insertbackground=NOIR,
                              relief="flat", bd=0, font=(FAMILLE, 11), highlightthickness=2,
                              highlightbackground=GRIS_BORD, highlightcolor=ORANGE)
            entree.pack(fill="x", padx=16, pady=(6, 6), ipady=5)
            entree.bind("<Return>", lambda e, q=quoi: self.enregistrer_parametre(q))
            rang = tk.Frame(p, bg=GRIS_MENU)
            rang.pack(fill="x", padx=16)
            bouton_orange(rang, "Enregistrer", lambda q=quoi: self.enregistrer_parametre(q),
                          taille=9).pack(side="left")
            bouton_orange(rang, "Supprimer", lambda q=quoi: self.supprimer_parametre(q),
                          taille=9).pack(side="left", padx=(8, 0))
            tk.Label(p, text=aide, bg=GRIS_MENU, fg="#2e2e2e", anchor="w", justify="left",
                     font=(FAMILLE, 9), wraplength=LARGEUR_MENU - 36).pack(fill="x", padx=16, pady=(6, 4))
            self.champs[quoi] = {"titre": titre, "fichier": fichier, "variable": variable,
                                 "statut": statut, "entree": entree}

        tk.Frame(p, bg="#5e5e5e", height=2).pack(fill="x", padx=14, pady=(14, 0))
        # Ta ville, pour la météo quand tu dis pas où
        tk.Label(p, text="Ta ville (météo)", bg=GRIS_MENU, fg=NOIR, anchor="w",
                 font=(FAMILLE, 11, "bold")).pack(fill="x", padx=16, pady=(12, 2))
        self.statut_ville = tk.Label(p, bg=GRIS_MENU, fg=NOIR, anchor="w", justify="left",
                                     font=(FAMILLE, 9), wraplength=LARGEUR_MENU - 36)
        self.statut_ville.pack(fill="x", padx=16)
        self.entree_ville = tk.Entry(p, bg=GRIS_ZONE, fg=NOIR, insertbackground=NOIR, relief="flat",
                                     bd=0, font=(FAMILLE, 11), highlightthickness=2,
                                     highlightbackground=GRIS_BORD, highlightcolor=ORANGE)
        self.entree_ville.pack(fill="x", padx=16, pady=(6, 6), ipady=5)
        self.entree_ville.bind("<Return>", lambda e: self.enregistrer_ville())
        rang = tk.Frame(p, bg=GRIS_MENU)
        rang.pack(fill="x", padx=16)
        bouton_orange(rang, "Enregistrer", self.enregistrer_ville, taille=9).pack(side="left")
        bouton_orange(rang, "Supprimer", self.supprimer_ville, taille=9).pack(side="left", padx=(8, 0))
        tk.Label(p, text="Pour la météo quand tu dis pas où. Ex. : Normandin, Québec",
                 bg=GRIS_MENU, fg="#2e2e2e", anchor="w", justify="left", font=(FAMILLE, 9),
                 wraplength=LARGEUR_MENU - 36).pack(fill="x", padx=16, pady=(6, 4))
        tk.Frame(p, bg="#5e5e5e", height=2).pack(fill="x", padx=14, pady=(14, 0))
        tk.Label(p, text="IA gratuites", bg=GRIS_MENU, fg=NOIR, anchor="w",
                 font=(FAMILLE, 11, "bold")).pack(fill="x", padx=16, pady=(12, 2))
        tk.Label(p, text="Elles tournent sur ton ordi, sans clé pis sans payer une cenne.",
                 bg=GRIS_MENU, fg="#2e2e2e", anchor="w", justify="left",
                 font=(FAMILLE, 9), wraplength=LARGEUR_MENU - 36).pack(fill="x", padx=16)
        bouton_orange(p, "Ajouter des IA gratuites…", self.ouvrir_ia_gratuites, taille=9).pack(
            fill="x", padx=16, pady=(8, 4))

        tk.Frame(p, bg="#5e5e5e", height=2).pack(fill="x", padx=14, pady=(14, 0))
        tk.Label(p, text="Mises à jour", bg=GRIS_MENU, fg=NOIR, anchor="w",
                 font=(FAMILLE, 11, "bold")).pack(fill="x", padx=16, pady=(12, 2))
        self.statut_maj = tk.Label(p, text=f"Version {VERSION}", bg=GRIS_MENU, fg=NOIR,
                                   anchor="w", justify="left", font=(FAMILLE, 9),
                                   wraplength=LARGEUR_MENU - 36)
        self.statut_maj.pack(fill="x", padx=16)
        self.auto_maj = tk.BooleanVar(value=maj_auto_active())
        tk.Checkbutton(p, text="Se mettre à jour toute seule", variable=self.auto_maj,
                       command=lambda: regler_maj_auto(self.auto_maj.get()),
                       bg=GRIS_MENU, fg=NOIR, activebackground=GRIS_MENU, activeforeground=NOIR,
                       selectcolor=GRIS_ZONE, font=(FAMILLE, 9), anchor="w", relief="flat",
                       highlightthickness=0, bd=0, cursor="hand2").pack(fill="x", padx=13, pady=(4, 0))
        bouton_orange(p, "\u27f3  Vérifier maintenant",
                      lambda: self.verifier_maj(annoncer=True), taille=9).pack(
            fill="x", padx=16, pady=(6, 16))
        self.maj_statuts()

    # ---------- Mises à jour ----------
    # ---------- Mises à jour ----------
    def verifier_maj(self, annoncer=False):
        """Regarde s'il y a du neuf sur GitHub. Si l'auto est allumée, ça s'installe tout seul.

        annoncer=True : c'est toi qui as cliqué, donc on te répond même s'il n'y a rien.
        """
        if annoncer:
            self.dire_maj("Vérification…")

        def travailler():
            try:
                version, code = chercher_maj()
            except Exception as e:
                if annoncer:
                    self.taches.put(lambda: self.dire_maj(f"Vérification impossible : {e}"))
                return
            if not version:
                if annoncer:
                    self.taches.put(lambda: self.dire_maj(f"Version {VERSION} — t'es à jour."))
                return
            if not maj_auto_active():
                self.taches.put(lambda v=version: self.dire_maj(
                    f"Version {v} disponible. Allume l'auto ou clique Vérifier pour l'installer."))
                if annoncer:
                    self.taches.put(lambda v=version, c=code: self.proposer_maj(v, c))
                return
            try:
                sauvegarde = installer_maj(code)
            except Exception as e:
                self.taches.put(lambda: self.dire_maj(f"Installation impossible : {e}"))
                return
            self.taches.put(lambda v=version, g=sauvegarde: self.maj_installee(v, g))

        threading.Thread(target=travailler, daemon=True).start()

    def dire_maj(self, texte):
        if getattr(self, "statut_maj", None):
            self.statut_maj.config(text=texte)

    def proposer_maj(self, version, code):
        if not messagebox.askyesno(
                "Mise à jour", f"La version {version} est prête (t'as la {VERSION}).\n\n"
                               "L'installer maintenant ?"):
            return
        try:
            sauvegarde = installer_maj(code)
        except Exception as e:
            messagebox.showerror("Mise à jour", f"Ça n'a pas marché : {e}")
            return
        self.maj_installee(version, sauvegarde)

    def maj_installee(self, version, sauvegarde):
        self.dire_maj(f"Version {version} installée. Redémarre l'app pour l'avoir.")
        messagebox.showinfo(
            "Mise à jour installée",
            f"La version {version} est installée.\n\n"
            f"Ferme pis rouvre l'app pour t'en servir.\n"
            f"L'ancienne est gardée ici au cas où :\n{sauvegarde}")

    def aller_page(self, nom):
        """Fait glisser le menu vers une page : « principale » ou « parametres »."""
        if nom == "parametres":
            self.maj_statuts()

        def appliquer(v):
            self.page_x = int(v)
            self.page_principale.place_configure(x=self.page_x)
            self.page_parametres.place_configure(x=self.page_x + LARGEUR_MENU)

        self.animer("pages", self.page_x, 0 if nom == "principale" else -LARGEUR_MENU,
                    appliquer, etapes=14)

    # ---------- Paramètres : clé API et token ----------
    def maj_statuts(self):
        for quoi, c in self.champs.items():
            cle = quoi == "claude"
            valeur = c["fichier"].read_text(encoding="utf-8").strip() if c["fichier"].exists() else ""
            if valeur:
                texte = f"{'Clé enregistrée' if cle else 'Token enregistré'} (finit par {valeur[-4:]})"
            elif os.environ.get(c["variable"]):
                texte = f"Vient de la variable {c['variable']}"
            else:
                texte = "Aucune clé enregistrée" if cle else "Aucun token enregistré"
            c["statut"].config(text=texte)
        if hasattr(self, "statut_ville"):
            ville = lire_reglages().get("ville", "")
            self.statut_ville.config(text=f"Ville : {ville}" if ville else "Aucune ville enregistrée")

    def enregistrer_ville(self):
        ville = " ".join(self.entree_ville.get().split())
        if not ville:
            self.statut_ville.config(text="Écris d'abord le nom de ta ville dans la case.")
            return
        reglages = lire_reglages()
        reglages["ville"] = ville
        enregistrer_reglages(reglages)
        self.entree_ville.delete(0, "end")
        self.maj_statuts()

    def supprimer_ville(self):
        reglages = lire_reglages()
        reglages.pop("ville", None)
        enregistrer_reglages(reglages)
        self.maj_statuts()

    def enregistrer_parametre(self, quoi):
        c = self.champs[quoi]
        valeur = c["entree"].get().strip()
        if not valeur:
            c["statut"].config(text="Colle d'abord la valeur dans la case.")
            c["entree"].focus_set()
            return
        enregistrer_secret(c["fichier"], valeur)
        c["entree"].delete(0, "end")
        self.maj_statuts()
        if quoi == "github" and self.codex is not None:
            self.codex.nouveau_token(valeur)

    def supprimer_parametre(self, quoi):
        c = self.champs[quoi]
        if not c["fichier"].exists():
            self.maj_statuts()
            return
        if not messagebox.askyesno("Supprimer", f"Supprimer {c['titre'].lower()} de cet ordi?"):
            return
        c["fichier"].unlink(missing_ok=True)
        self.maj_statuts()
        if quoi == "github" and self.codex is not None:
            self.codex.nouveau_token(lire_secret(FICHIER_TOKEN, "GITHUB_TOKEN"))

    def ouvrir_parametres(self, focus=None):
        """Ouvre le menu directement sur Paramètres (ex. : quand la clé manque)."""
        if not self.menu_ouvert:
            self.basculer_menu()
        self.aller_page("parametres")
        if focus in self.champs:
            self.champs[focus]["entree"].focus_set()

    # ---------- Ouvrir / fermer le menu ----------
    def basculer_menu(self):
        self.menu_ouvert = not self.menu_ouvert
        if self.menu_ouvert:
            self.rafraichir_sessions()
            self.maj_navigation()
            self.menu_lateral.lift()
            self.bouton_menu.lift()

        def appliquer(v):
            self.menu_x = int(v)
            self.menu_lateral.place_configure(x=self.menu_x)

        def apres():
            if not self.menu_ouvert and self.page_x != 0:   # la prochaine fois : page principale
                self.annuler_animation("pages")
                self.page_x = 0
                self.page_principale.place_configure(x=0)
                self.page_parametres.place_configure(x=LARGEUR_MENU)

        self.animer("menu", self.menu_x, 0 if self.menu_ouvert else -LARGEUR_MENU, appliquer,
                    apres, etapes=16)

    def maj_navigation(self):
        codex = self.codex_visible()
        self.nav_chat.config(bg=GRIS_INACTIF if codex else ORANGE)
        self.nav_codex.config(bg=ORANGE if codex else GRIS_INACTIF)

    def aller_chat(self):
        self.fermer_codex()
        self.fermer_menu()
        self.saisie.focus_set()

    def fermer_menu(self):
        if self.menu_ouvert:
            self.basculer_menu()

    def rafraichir_sessions(self):
        liste = self.liste_sessions
        liste.delete(0, "end")
        self.ids_sessions = []
        sessions = lister_sessions()
        if not sessions:
            liste.insert("end", "  Aucune conversation encore")
            liste.itemconfig(0, fg="#3a3a3a")
            self.ids_sessions.append(None)
            return
        for i, s in enumerate(sessions):
            titre = s.get("titre", "Sans titre")
            liste.insert("end", "  " + (titre if len(titre) <= 28 else titre[:27].rstrip() + "…"))
            self.ids_sessions.append(s.get("id"))
            if s.get("id") == self.session_id:
                liste.selection_set(i)

    def sur_choix_session(self, event=None):
        choix = self.liste_sessions.curselection()
        if not choix:
            return
        sid = self.ids_sessions[choix[0]]
        if sid is None:
            return
        if sid == self.session_id:
            self.fermer_codex()
            self.fermer_menu()
        else:
            self.ouvrir_session(sid)

    def menu_session(self, event):
        i = self.liste_sessions.nearest(event.y)
        if i < 0 or i >= len(self.ids_sessions) or self.ids_sessions[i] is None:
            return
        sid = self.ids_sessions[i]
        menu = tk.Menu(self, tearoff=0, bg=GRIS_ZONE, fg=NOIR, activebackground=ORANGE,
                       activeforeground=NOIR, font=(FAMILLE, 11))
        menu.add_command(label="Supprimer la conversation", command=lambda: self.supprimer_session(sid))
        menu.tk_popup(event.x_root, event.y_root)

    def supprimer_session(self, sid):
        if not messagebox.askyesno("Supprimer", "Supprimer cette conversation pour de bon?"):
            return
        (DOSSIER_SESSIONS / f"{sid}.json").unlink(missing_ok=True)
        if sid == self.session_id:
            self.session_id = None
        self.rafraichir_sessions()

    # ---------- Sessions ----------
    def sauver_session(self):
        if not self.messages:
            return
        maintenant = datetime.datetime.now()
        if not self.session_id:
            self.session_id = maintenant.strftime("%Y%m%d-%H%M%S-%f")
            self.session_cree = maintenant.isoformat(timespec="seconds")
        premiere = next((m["content"] for m in self.messages if m["role"] == "user"), "Conversation")
        titre = " ".join(premiere.split())
        titre = titre if len(titre) <= 42 else titre[:41].rstrip() + "…"
        DOSSIER_SESSIONS.mkdir(parents=True, exist_ok=True)
        (DOSSIER_SESSIONS / f"{self.session_id}.json").write_text(json.dumps({
            "id": self.session_id, "titre": titre, "cree": self.session_cree,
            "modifie": maintenant.isoformat(timespec="seconds"), "messages": self.messages,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        if self.menu_ouvert:
            self.rafraichir_sessions()

    def ouvrir_session(self, sid):
        try:
            data = json.loads((DOSSIER_SESSIONS / f"{sid}.json").read_text(encoding="utf-8"))
        except Exception:
            messagebox.showerror("Conversation", "Impossible d'ouvrir cette conversation.")
            return
        self.fermer_codex()
        self.vider_conversation()
        self.session_id, self.session_cree = data["id"], data.get("cree")
        self.messages = data.get("messages", [])
        if self.premiere_ligne:
            self.annuler_animation("descente")
            self.en_animation = False
            self.premiere_ligne = False
            self.invite.pack_forget()
            self.saisie_en_bas()
            self.afficher_document()
        if self.logo:
            self.annuler_animation("logo")
            self.logo.a_gauche()
        dernier = None
        for m in self.messages:
            if m["role"] == "user":
                self.document.insert("end", m["content"] + "\n", "question")
            else:
                dernier = self.avatar()
                debut = self.document.index("end-1c")
                self.document.insert("end", m["content"] + "\n", "reponse")
                self.lier_liens(self.document, debut, "end-1c")
                self.ajouter_schema_et_sources(m.get("etapes") or [],
                                               [tuple(s) for s in m.get("sources") or []])
                if m.get("meteo") is not None:
                    self.ajouter_meteo(m["meteo"])   # la météo d'astheure, en direct
        self.document.see("end")
        if self.logo and dernier:
            self.update_idletasks()
            self.logo.suivre(dernier, anime=False)
        self.fermer_menu()
        self.saisie.focus_set()

    def vider_conversation(self):
        self.generation += 1
        self.occupe = False
        self.messages = []
        self.session_id = self.session_cree = None
        for schema in self.schemas:
            schema.destroy()
        self.schemas = []
        self.document.delete("1.0", "end")
        self.title("Écriture")
        if self.logo:
            self.logo.arreter_suivi()

    def historique_api(self):
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]

    # ---------- Codex ----------
    def ouvrir_codex(self):
        if self.codex is None:
            self.codex = CodexVue(self)
        self.codex.place(x=0, y=0, relwidth=1, relheight=1)
        self.codex.lift()
        self.menu_lateral.lift()
        self.bouton_menu.lift()
        self.maj_navigation()
        self.fermer_menu()
        self.codex.saisie.focus_set()

    def fermer_codex(self):
        if self.codex is not None:
            self.codex.place_forget()
        self.maj_navigation()

    def codex_visible(self):
        return self.codex is not None and bool(self.codex.winfo_manager())

    def ctrl_s(self, event=None):
        if self.codex_visible():
            self.codex.enregistrer_actif()
        else:
            self.sauvegarder()
        return "break"

    def quitter(self):
        if self.codex and any(o.modifie for o in self.codex.onglets):
            if not messagebox.askyesno("Quitter", "Des fichiers du Codex ont des changements "
                                                  "pas enregistrés.\nQuitter quand même?"):
                return
        self.destroy()

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

    def descendre(self):
        self.en_animation = True
        self.invite.pack_forget()
        self.update_idletasks()
        cible = 1 - (self.zone_saisie.winfo_height() / 2 + MARGE) / self.winfo_height()

        def fini():
            self.saisie_en_bas()
            self.afficher_document()
            self.en_animation = False

        self.animer("descente", 0.5, cible, lambda v: self.zone_saisie.place_configure(rely=v),
                    fini, etapes=24)

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
            cle = lire_secret(FICHIER_CLE, "ANTHROPIC_API_KEY")
            if not cle:
                self.ouvrir_parametres("claude")   # ta question reste dans la boîte
                return "break"

        self.saisie.delete("1.0", "end")
        self.document.insert("end", texte + "\n", "question")
        self.messages.append({"role": "user", "content": texte})
        self.question_en_cours = texte
        self.montrer_attente(nom_court(moteur))
        self.occupe = True
        threading.Thread(target=self.travail, args=(moteur, cle, self.historique_api(), self.generation),
                         daemon=True).start()
        self.after(100, self.verifier_resultat)

        if self.premiere_ligne:
            self.premiere_ligne = False
            if self.logo:
                self.logo.glisser(vers_gauche=True)
            self.descendre()
        self.document.see("end")
        return "break"

    def travail(self, moteur, cle, historique, generation):
        # Roule dans un fil à part pour que la fenêtre gèle pas pendant que l'IA réfléchit
        type_moteur, modele = moteur
        try:
            if type_moteur == "claude":
                texte, sources = appeler_claude(cle, historique, instructions_systeme(web=True),
                                                modele=modele)
            else:
                texte, sources = appeler_ollama(modele, historique, instructions_systeme(web=False))
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
            # Réponse d'une conversation qu'on a quittée : on l'ignore
            if self.occupe:
                self.after(100, self.verifier_resultat)
            return

        zone = self.document.tag_ranges("attente")
        if zone:
            self.document.delete(zone[0], zone[1])
        continuer = lambda: generation == self.generation

        if statut == "ok":
            texte, etapes = extraire_plan(texte, self.question_en_cours)
            texte, lieu_meteo = extraire_meteo(texte, self.question_en_cours)
            texte = liens_markdown_en_texte(texte) or (
                "Voici la météo :" if lieu_meteo is not None else "Voici le plan :" if etapes else
                "Pas de réponse cette fois-ci. Reformule ta question.")
            self.messages.append({"role": "assistant", "content": texte, "etapes": etapes,
                                  "sources": [list(s) for s in sources], "meteo": lieu_meteo})
            self.sauver_session()

            def apres_ecriture():
                # Le schéma, les sources pis la météo arrivent une fois le texte fini d'écrire
                index = self.ajouter_schema_et_sources(etapes, sources)
                if lieu_meteo is not None:
                    self.ajouter_meteo(lieu_meteo)
                self.fin_reponse(index)

            self.ecrire(self.document, texte, continuer, apres_ecriture)
        else:
            self.messages.pop()  # la question n'a pas eu de réponse, on la retire
            self.ecrire(self.document, texte, continuer, self.fin_reponse)

    def ajouter_schema_et_sources(self, etapes, sources):
        index_schema = None
        if etapes:
            largeur = max(self.document.winfo_width() - 40, 360)
            schema = SchemaAnime(self.document, etapes, largeur)
            self.schemas.append(schema)
            index_schema = self.document.index("end-1c")
            self.document.window_create("end", window=schema, pady=8)
            self.document.insert("end", "\n")
        if sources:
            self.document.insert("end", "Sources :\n", "sources")
            for titre, url in sources[:5]:
                etiquette = f"lien{self.nb_liens}"
                self.nb_liens += 1
                self.document.insert("end", "- ", "sources")
                self.document.insert("end", titre + "\n", ("sources", "lien", etiquette))
                self.document.tag_bind(etiquette, "<Button-1>", lambda e, u=url: webbrowser.open(u))
        return index_schema

    def fin_reponse(self, index_a_montrer=None):
        self.occupe = False
        self.document.see("end")
        if index_a_montrer:
            self.document.see(index_a_montrer)   # montre le haut du schéma

    def avatar(self):
        """Petit logo Marceau devant la réponse de l'agent. Retourne où il est."""
        if not self.logo:
            return None
        index = self.document.index("end-1c")
        self.document.image_create(index, image=self.logo.image(LOGO_AVATAR), padx=3, align="center")
        self.document.tag_add("avatar", index)
        return index

    def ajouter_meteo(self, lieu):
        """Pouvoir magique : va chercher la météo en direct pis l'affiche en carte animée."""
        self.nb_meteo += 1
        marque, etiquette = f"meteo{self.nb_meteo}", f"attente_meteo{self.nb_meteo}"
        self.document.mark_set(marque, "end-1c")
        self.document.mark_gravity(marque, "left")
        self.document.insert("end", "Je regarde la météo…\n", ("attente", etiquette))
        generation, ville = self.generation, lire_reglages().get("ville", "")

        def fini(meteo, err):
            if generation != self.generation:
                return   # on a changé de conversation entre-temps
            zone = self.document.tag_ranges(etiquette)
            if zone:
                self.document.delete(zone[0], zone[1])
            if err:
                self.document.insert(marque, message_meteo(err, lieu or ville) + "\n", "reponse")
                return
            carte = CarteMeteo(self.document, meteo, max(self.document.winfo_width() - 40, 460))
            self.schemas.append(carte)   # effacée avec la conversation
            self.document.window_create(marque, window=carte, pady=8)
            self.document.insert(f"{marque}+1c", "\n")
            self.document.see("end")
            self.document.see(marque)

        self.en_arriere_plan(lambda: obtenir_meteo(lieu, ville), fini)

    def montrer_attente(self, nom):
        self.compteur = 0
        index = self.avatar()
        if index:
            self.logo.suivre(index)   # le gros logo vient se placer à côté de la réponse
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
        # La conversation d'avant est déjà sauvegardée dans le menu de gauche
        self.fermer_codex()
        self.vider_conversation()
        self.annuler_animation("descente")
        self.en_animation = False
        self.document.place_forget()
        self.barre.place_forget()
        if not self.invite.winfo_manager():
            self.invite.pack(pady=(0, 14), before=self.ligne)
        self.premiere_ligne = True
        self.centrer_saisie()
        if self.logo and self.logo.position != "centre":
            self.logo.glisser(vers_gauche=False)
        self.saisie.focus_set()
        self.fermer_menu()


if __name__ == "__main__":
    AppEcriture().mainloop()
