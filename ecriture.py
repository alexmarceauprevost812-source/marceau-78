#!/usr/bin/env python3
# Marceau — espace d'écriture + assistant IA québécois + Codex GitHub
#   - Menu à gauche (☰) : tes conversations sauvegardées + le Codex
#   - IA gratuites en local avec Ollama, ou Claude + recherche web (payant)
#   - Schémas animés quand l'IA explique un plan d'action
#   - Codex : ouvre un projet GitHub, colore le code, pis l'IA peut le scanner, l'écrire et le corriger
# Rien à installer à part python3-tk. Lancer : python3 ecriture.py

import base64
import datetime
import difflib
import http.server
import io
import json
import math
import os
import queue
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import wave
import webbrowser
from bisect import bisect_right
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

try:   # Pillow : le logo, pis tout le Studio d'images (optionnel)
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageTk
except ImportError:
    Image = ImageTk = ImageDraw = ImageEnhance = ImageFilter = ImageFont = ImageOps = None

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

# La police : celle de ton système (Ubuntu, GNOME, KDE…), trouvée au démarrage.
# Pour en forcer une autre, écris son nom ici (ex. : "Noto Sans"). Vide = celle du système.
POLICE_PERSO = ""
POLICE_CODE_PERSO = ""
FAMILLE = "DejaVu Sans"             # si on trouve rien : celle-là, qui est sur presque tous les Linux
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
FICHIERS_ICONE = ("logo.png", "logo_192.png", "logo_marceau.png", "logo_64.png")
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
DOSSIER_IMAGES = Path.home() / ".local" / "share" / "ecriture" / "images"
DOSSIER_PROJETS = Path.home() / ".local" / "share" / "ecriture" / "projets"
FICHIER_MAJ = DOSSIER_CONFIG / "maj_auto"      # "non" dedans = tu as coupé l'auto

# ---------- Mises à jour ----------
# L'app va se chercher elle-même sur GitHub. Un seul lien, écrit en dur : elle ne
# téléchargera jamais rien d'ailleurs, même si un fichier de config disait le contraire.
VERSION = "2.6.0"
HEURES_MAJ = 6         # on revérifie les mises à jour aux 6 heures, même si l'app reste ouverte
URL_MAJ = ("https://raw.githubusercontent.com/alexmarceauprevost812-source/"
           "marceau-78/refs/heads/claude/bold-gates-5onh76/ecriture.py")
RECHERCHES_MAX = 5                     # recherches web max par question (Claude)
NOM_CLAUDE = "Claude + web (payant)"   # nom affiché dans le menu
STYLE_QUEBECOIS = True                 # False = l'IA parle en français standard
DUREE_ECRITURE = 1.5                   # secondes max pour écrire une réponse à l'écran
VITESSE_MS = 10                        # une lettre (ou un petit paquet) aux 10 ms
DUREE_CODE = 1.2                       # secondes max pour écrire un fichier dans l'éditeur du Codex
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
        "Pouvoir spécial, le Studio : la personne peut partager des images. Si elle te demande de "
        "modifier une image (plus claire, noir et blanc, recadrer, tourner, ajouter du texte, un "
        "filtre…), explique en une phrase ce que tu fais pis termine par un bloc comme :\n"
        "[STUDIO]\nluminosite 1.2\ntexte \"Bonne fête!\" bas blanc\n[/STUDIO]\n"
        "Opérations possibles, une par ligne, dans l'ordre où les faire : luminosite X, contraste X, "
        "saturation X (0 = noir et blanc, 2 = couleurs vives), nettete X (1 = pareil), noir_et_blanc, "
        "sepia, inverser, flou X (pixels), rotation X (degrés : 90 = vers la gauche, -90 = vers la "
        "droite), miroir, miroir_vertical, recadrer G H D B (pourcentages à enlever à gauche, en "
        "haut, à droite, en bas), carre, taille L (largeur en pixels), texte \"…\" haut|centre|bas "
        "couleur, bordure N couleur, vignette X (0 à 1), chaud, froid, pixeliser N, posteriser N. "
        "Les modifications se font sur la dernière image de la conversation. Si on te pose juste "
        "une question sur une image, réponds sans bloc. "
    )
    texte += (
        "Pouvoir spécial, le Studio d'applications : si on te demande de construire une petite "
        "application, un jeu, un outil, une calculatrice, une page web ou n'importe quoi qui s'ouvre "
        "dans un navigateur, écris-la AU COMPLET dans UN SEUL fichier HTML — le CSS dans <style>, le "
        "JavaScript dans <script>, sans image ni librairie à aller chercher sur Internet si tu peux "
        "t'en passer — dans un bloc exactement comme celui-ci :\n"
        "[APP Titre court de l'app]\n<!DOCTYPE html>\n…\n[/APP]\n"
        "Avant le bloc, dis en deux ou trois phrases ce que fait l'app pis comment s'en servir. "
        "Pour changer une app déjà faite, réécris-la au complet dans un nouveau bloc [APP] avec le "
        "MÊME titre : elle se met à jour toute seule dans le Studio. "
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
        "un bloc [LIRE] qui liste leurs chemins (un par ligne), terminé par [/LIRE]. "
        "Des images peuvent être jointes à la demande (image 1, image 2…). Pour mettre une image "
        "jointe dans le projet, écris une ligne comme [IMAGE 1 images/logo.png] (le numéro de "
        "l'image, puis son chemin dans le projet)."
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
        # Les modèles « embed » jasent pas, pis les copies faites pour OpenCode sont pas à montrer
        return sorted(n for n in noms if "embed" not in n and not est_variante_opencode(n))
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
    envoi = []
    for m in messages:
        message = {"role": m["role"], "content": m["content"]}
        if m.get("images"):
            message["images"] = [i["data"] for i in m["images"]]   # les modèles qui voient (llava, gemma3…)
        envoi.append(message)
    corps = {
        "model": modele,
        "stream": False,
        "messages": [{"role": "system", "content": systeme}] + envoi,
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
    conversation = []
    for m in messages:
        if m.get("images"):   # Claude voit les images : on les met avant le texte
            contenu = [{"type": "image", "source": {"type": "base64", "media_type": i["media_type"],
                                                    "data": i["data"]}} for i in m["images"]]
            contenu.append({"type": "text", "text": m["content"] or "Regarde l'image."})
            conversation.append({"role": m["role"], "content": contenu})
        else:
            conversation.append({"role": m["role"], "content": m["content"]})
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
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Marceau-Codex"}
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


def lire_blob_octets(depot, sha, token):
    """Lit un fichier du projet tel quel (images, etc.)."""
    data = github("GET", f"/repos/{depot}/git/blobs/{sha}", token)
    return base64.b64decode(data["content"])


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
    explication = re.sub(r"\[IMAGE\s+\d+[^\]\n]*\]", "", explication, flags=re.I)
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
    requete = urllib.request.Request(url, headers={"User-Agent": "Marceau-app"})
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


def agent_codex(question, historique, onglets, cache, arbre, depot, branche, token, budget, ia, progres,
                images=()):
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
            progres("Codex cherche les bons fichiers")
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
        if images:
            envoi[-1]["images"] = list(images)   # Codex voit les images jointes
        progres("Codex écrit le code")
        texte = ia(envoi, instructions_codex(), 16000)
        # L'IA peut demander d'autres fichiers avant d'écrire : on les lit pis on recommence une fois
        nouveaux = [c for c in associer_chemins(extraire_lire(texte), arbre) if c not in choisis] if depot else []
        if tour == 0 and nouveaux and "[FICHIER" not in texte.upper():
            choisis += nouveaux[:6]
            lire(nouveaux[:6])
            continue
        break
    return {"texte": texte, "lus": lus, "vus": vus}


# ---------- Images : pièces jointes, pouvoir de voir, pis le Studio ----------
EXT_IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
TYPES_IMAGES = [("Images", "*.png *.jpg *.jpeg *.gif *.webp *.bmp *.PNG *.JPG *.JPEG"),
                ("Tous les fichiers", "*.*")]
MESSAGE_PILLOW = "Pour les images, installe Pillow :\nsudo apt install python3-pil python3-pil.imagetk"
COULEURS_NOMS = {"blanc": "#ffffff", "noir": "#000000", "rouge": "#ff3b30", "orange": ORANGE,
                 "jaune": "#ffd60a", "vert": "#34c759", "bleu": "#0a84ff", "violet": "#8e44ad",
                 "mauve": "#b57edc", "rose": "#ff6fae", "gris": "#8e8e93", "brun": "#8b5a2b",
                 "or": "#d4af37", "lime": LIME, "turquoise": "#1abc9c"}
POLICES_TEXTE = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"]


def ouvrir_image(source):
    """Ouvre une image (chemin ou octets), tournée comme il faut, en RGB ou RGBA."""
    img = Image.open(io.BytesIO(source) if isinstance(source, bytes) else source)
    img = ImageOps.exif_transpose(img)
    if getattr(img, "is_animated", False):
        img.seek(0)
    transparente = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    return img.convert("RGBA" if transparente else "RGB")


def garder_image(img, prefixe="image"):
    """Garde une copie de l'image dans ~/.local/share/ecriture/images (pour les conversations)."""
    DOSSIER_IMAGES.mkdir(parents=True, exist_ok=True)
    copie = img.copy()
    copie.thumbnail((2560, 2560))
    nom = f"{prefixe}-{datetime.datetime.now():%Y%m%d-%H%M%S-%f}"
    if copie.mode == "RGBA":
        chemin = DOSSIER_IMAGES / f"{nom}.png"
        copie.save(chemin, "PNG")
    else:
        chemin = DOSSIER_IMAGES / f"{nom}.jpg"
        copie.save(chemin, "JPEG", quality=92)
    return str(chemin)


def image_pour_ia(img):
    """Prépare une image pour que l'IA la voie (pas plus de 1568 px, comme Claude le recommande)."""
    copie = img.copy()
    copie.thumbnail((1568, 1568))
    tampon = io.BytesIO()
    if copie.mode == "RGBA":
        copie.save(tampon, "PNG", optimize=True)
        type_media = "image/png"
    if copie.mode != "RGBA" or tampon.tell() > 3_500_000:
        tampon = io.BytesIO()
        copie.convert("RGB").save(tampon, "JPEG", quality=88)
        type_media = "image/jpeg"
    return {"media_type": type_media, "data": base64.b64encode(tampon.getvalue()).decode("ascii")}


def octets_pour(chemin, img):
    """Convertit une image dans le format de son nom de fichier (.png, .jpg, .webp…)."""
    ext = Path(chemin).suffix.lower()
    tampon = io.BytesIO()
    if ext in (".jpg", ".jpeg"):
        img.convert("RGB").save(tampon, "JPEG", quality=90)
    elif ext == ".webp":
        img.save(tampon, "WEBP", quality=90)
    elif ext == ".gif":
        img.convert("P", palette=Image.Palette.ADAPTIVE).save(tampon, "GIF")
    elif ext == ".bmp":
        img.convert("RGB").save(tampon, "BMP")
    else:
        img.save(tampon, "PNG", optimize=True)
    return tampon.getvalue()


def vignette_tk(img, largeur, hauteur):
    copie = img.copy()
    copie.thumbnail((largeur, hauteur))
    return ImageTk.PhotoImage(copie)


_VISION = {}


def modele_voit_images(modele):
    """Demande à Ollama si ce modèle voit les images (llava, llama3.2-vision, gemma3…)."""
    if modele not in _VISION:
        try:
            requete = urllib.request.Request(
                URL_OLLAMA + "/api/show", data=json.dumps({"model": modele}).encode("utf-8"),
                method="POST", headers={"content-type": "application/json"})
            with urllib.request.urlopen(requete, timeout=5) as rep:
                data = json.loads(rep.read().decode("utf-8"))
            capacites = data.get("capabilities")
            if capacites is not None:
                _VISION[modele] = "vision" in capacites
            else:   # vieux Ollama : on regarde la famille du modèle
                familles = " ".join((data.get("details") or {}).get("families") or []).lower()
                _VISION[modele] = "projector_info" in data or any(k in familles for k in ("clip", "mllama"))
        except Exception:
            _VISION[modele] = True   # on le sait pas : on essaie quand même
    return _VISION[modele]


def preparer_historique(historique, voit):
    """Ajoute les vraies images aux messages (juste les 3 derniers messages avec images)."""
    resultat = [dict(m) for m in historique]
    avec_images = [i for i, m in enumerate(resultat) if m.get("images_chemins")]
    garder = set(avec_images[-3:])
    for i, m in enumerate(resultat):
        chemins = m.pop("images_chemins", None)
        if not chemins:
            continue
        if voit and i in garder and Image is not None:
            images = []
            for chemin in chemins:
                try:
                    images.append(image_pour_ia(ouvrir_image(chemin)))
                except Exception:
                    pass
            if images:
                m["images"] = images
                continue
        note = ("(La personne a joint une image que tu ne peux pas voir. Tu peux quand même la "
                "modifier avec le Studio.)" if not voit else "(Une image avait été jointe ici.)")
        m["content"] = (m["content"] + "\n" if m["content"] else "") + note
    return resultat


# ----- Le Studio : les modifications d'image -----
def extraire_studio(texte):
    """Sort le bloc [STUDIO]…[/STUDIO]. Retourne (texte sans le bloc, liste d'opérations)."""
    m = re.search(r"\[STUDIO\](.*?)(?:\[/STUDIO\]|$)", texte, re.S | re.I)
    if not m:
        return texte, []
    operations = [l.strip() for l in m.group(1).splitlines() if l.strip()]
    return (texte[:m.start()] + texte[m.end():]).strip(), operations


def couleur_dans(mots, defaut):
    for mot in mots:
        mot = mot.strip(",.;")
        if re.fullmatch(r"#[0-9a-fA-F]{6}", mot):
            return mot
        nom = sans_accents(mot)
        if nom in COULEURS_NOMS:
            return COULEURS_NOMS[nom]
    return defaut


def police_texte(taille):
    for chemin in [fichier_police_systeme()] + POLICES_TEXTE:
        if not chemin:
            continue
        try:
            return ImageFont.truetype(chemin, taille)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=taille)
    except Exception:
        return ImageFont.load_default()


def sur_rgb(img, action):
    """Applique une retouche de couleur sans briser la transparence."""
    if img.mode == "RGBA":
        alpha = img.getchannel("A")
        resultat = action(img.convert("RGB")).convert("RGB")
        resultat.putalpha(alpha)
        return resultat
    return action(img.convert("RGB")).convert("RGB")


def borne(valeur, mini, maxi):
    return max(mini, min(maxi, valeur))


# Les noms d'opérations qu'on connaît : ça sert à lire « noir et blanc » comme « noir_et_blanc ».
NOMS_STUDIO = frozenset((
    "luminosite", "lumiere", "contraste", "saturation", "couleurs", "nettete", "noir_et_blanc",
    "noiretblanc", "gris", "sepia", "inverser", "flou", "rotation", "miroir", "miroir_vertical",
    "recadrer", "carre", "taille", "texte", "bordure", "vignette", "chaud", "froid",
    "pixeliser", "posteriser"))


def nom_studio(ligne):
    """Sort le nom de l'opération pis ses arguments.

    Les instructions demandent « noir_et_blanc », mais une IA écrit souvent « noir et blanc ».
    On essaie donc les trois premiers mots, pis les deux, avant de garder juste le premier.
    """
    for k in (3, 2, 1):
        m = re.match(r"\s*" + r"\s+".join([r"([^\s\"«“]+)"] * k), ligne)
        if m is None:
            continue
        nom = "_".join(sans_accents(x) for x in m.groups()).replace("-", "_").rstrip(":").lower()
        if nom in NOMS_STUDIO or k == 1:
            return nom, ligne[m.end():].strip()
    return "", ""


def appliquer_studio(image, operations):
    """Fait les modifications demandées par l'IA. Retourne (nouvelle image, liste de ce qui a été fait)."""
    img, fait = image.copy(), []
    for ligne in operations:
        ligne = ligne.strip().strip("-•* ")
        nom, reste = nom_studio(ligne)
        if not nom:
            continue
        nombres = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", reste.replace(",", "."))]
        mots = reste.split()

        def n(i, defaut):
            return nombres[i] if len(nombres) > i else defaut

        def facteur(defaut):
            """« 1.3 » c'est un facteur. « +30 » ou « 40 % », c'est un pourcentage en plus ou en moins."""
            if not nombres:
                return defaut
            if re.search(r"[+-]\s*\d|\d\s*%", reste):
                return 1 + nombres[0] / 100
            return nombres[0]

        try:
            w, h = img.size
            if nom in ("luminosite", "lumiere"):
                x = borne(facteur(1.2), 0.1, 3)
                img = sur_rgb(img, lambda r: ImageEnhance.Brightness(r).enhance(x))
                fait.append(f"luminosité ×{x:g}")
            elif nom == "contraste":
                x = borne(facteur(1.2), 0.1, 3)
                img = sur_rgb(img, lambda r: ImageEnhance.Contrast(r).enhance(x))
                fait.append(f"contraste ×{x:g}")
            elif nom in ("saturation", "couleurs"):
                x = borne(facteur(1.3), 0, 3)
                img = sur_rgb(img, lambda r: ImageEnhance.Color(r).enhance(x))
                fait.append(f"saturation ×{x:g}")
            elif nom == "nettete":
                x = borne(facteur(1.5), 0, 4)
                img = sur_rgb(img, lambda r: ImageEnhance.Sharpness(r).enhance(x))
                fait.append(f"netteté ×{x:g}")
            elif nom in ("noir_et_blanc", "noiretblanc", "gris"):
                img = sur_rgb(img, ImageOps.grayscale)
                fait.append("noir et blanc")
            elif nom == "sepia":
                img = sur_rgb(img, lambda r: ImageOps.colorize(ImageOps.grayscale(r), "#2e1f0f", "#f5e6c8"))
                fait.append("sépia")
            elif nom == "inverser":
                img = sur_rgb(img, ImageOps.invert)
                fait.append("couleurs inversées")
            elif nom == "flou":
                x = borne(n(0, 3), 0.5, 40)
                img = img.filter(ImageFilter.GaussianBlur(x))
                fait.append(f"flou {x:g} px")
            elif nom == "rotation":
                angle = n(0, 90)
                if angle % 90 == 0:
                    tours = int(angle // 90) % 4
                    if tours:
                        img = img.transpose([None, Image.Transpose.ROTATE_90, Image.Transpose.ROTATE_180,
                                             Image.Transpose.ROTATE_270][tours])
                else:
                    fond = (0, 0, 0, 0) if img.mode == "RGBA" else (255, 255, 255)
                    img = img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC, fillcolor=fond)
                fait.append(f"rotation {angle:g}°")
            elif nom == "miroir":
                img = ImageOps.mirror(img)
                fait.append("miroir")
            elif nom == "miroir_vertical":
                img = ImageOps.flip(img)
                fait.append("miroir vertical")
            elif nom == "recadrer":
                g, hh, d, b = (borne(n(i, 0), 0, 45) for i in range(4))
                img = img.crop((round(w * g / 100), round(h * hh / 100),
                                round(w * (1 - d / 100)), round(h * (1 - b / 100))))
                fait.append("recadrée")
            elif nom == "carre":
                cote = min(w, h)
                img = img.crop(((w - cote) // 2, (h - cote) // 2, (w + cote) // 2, (h + cote) // 2))
                fait.append("carré")
            elif nom == "taille":
                largeur = int(borne(n(0, w), 16, 4000))
                img = img.resize((largeur, max(1, round(h * largeur / w))), Image.Resampling.LANCZOS)
                fait.append(f"largeur {largeur} px")
            elif nom == "texte":
                trouve = re.search(r"[\"«“](.+?)[\"»”]", reste)
                texte = trouve.group(1).strip() if trouve else reste
                apres = reste[trouve.end():].split() if trouve else []
                position = next((sans_accents(x) for x in apres if sans_accents(x) in
                                 ("haut", "bas", "centre", "milieu")), "bas")
                couleur = couleur_dans(apres, "#ffffff")
                img = ecrire_sur_image(img, texte, position, couleur)
                fait.append(f"texte « {texte} »")
            elif nom == "bordure":
                epaisseur = int(borne(n(0, 20), 1, 200))
                couleur = couleur_dans(mots, "#ffffff")
                remplissage = couleur if img.mode != "RGBA" else couleur + "ff"
                img = ImageOps.expand(img, border=epaisseur, fill=remplissage)
                fait.append(f"bordure {epaisseur} px")
            elif nom == "vignette":
                force = borne(n(0, 0.5), 0, 1)
                masque = Image.radial_gradient("L").resize(img.size)
                masque = masque.point(lambda v: int(min(255, v * force * 1.3)))
                img = sur_rgb(img, lambda r: Image.composite(Image.new("RGB", r.size, "black"), r, masque))
                fait.append("vignette")
            elif nom in ("chaud", "froid"):
                chaud = nom == "chaud"

                def filtre(r):
                    rouge, vert, bleu = r.split()
                    rouge = rouge.point(lambda v: min(255, int(v * (1.08 if chaud else 0.92) + (8 if chaud else 0))))
                    bleu = bleu.point(lambda v: min(255, int(v * (0.9 if chaud else 1.1) + (0 if chaud else 8))))
                    return Image.merge("RGB", (rouge, vert, bleu))

                img = sur_rgb(img, filtre)
                fait.append("filtre chaud" if chaud else "filtre froid")
            elif nom == "pixeliser":
                taille = int(borne(n(0, 10), 2, 100))
                petit = img.resize((max(1, w // taille), max(1, h // taille)), Image.Resampling.BILINEAR)
                img = petit.resize((w, h), Image.Resampling.NEAREST)
                fait.append("pixelisée")
            elif nom == "posteriser":
                bits = int(borne(n(0, 3), 1, 8))
                img = sur_rgb(img, lambda r: ImageOps.posterize(r, bits))
                fait.append("postérisée")
        except Exception:
            continue   # une opération qui marche pas n'empêche pas les autres
    return img, fait


def ecrire_sur_image(img, texte, position, couleur):
    img = img.copy()
    dessin = ImageDraw.Draw(img)
    taille = max(14, img.width // 12)
    for _ in range(6):   # rapetisse le texte s'il dépasse
        police = police_texte(taille)
        contour = max(1, taille // 14)
        boite = dessin.textbbox((0, 0), texte, font=police, stroke_width=contour)
        largeur, hauteur = boite[2] - boite[0], boite[3] - boite[1]
        if largeur <= img.width * 0.92:
            break
        taille = int(taille * img.width * 0.9 / largeur)
    x = (img.width - largeur) / 2 - boite[0]
    y = {"haut": img.height * 0.05, "bas": img.height * 0.95 - hauteur}.get(
        position, (img.height - hauteur) / 2) - boite[1]
    r, g, b = (int(couleur[i:i + 2], 16) for i in (1, 3, 5))
    bordure = "#000000" if (r * 299 + g * 587 + b * 114) / 1000 > 140 else "#ffffff"
    dessin.text((x, y), texte, font=police, fill=couleur, stroke_width=contour, stroke_fill=bordure)
    return img


class StudioImage(tk.Frame):
    """Le Studio : l'image partagée, avec les modifications demandées. Avant/Après d'un clic."""
    HAUTEUR_IMAGE = 420

    def __init__(self, parent, app, avant, apres, resume, largeur, anime=True, hauteur_image=None,
                 suivre=None):
        super().__init__(parent, bg=GRIS_BOITE, highlightthickness=2, highlightbackground=ORANGE)
        self.app, self.avant, self.apres = app, avant, apres
        self.montre_apres = apres is not None
        haut = tk.Frame(self, bg=GRIS_BOITE)
        haut.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(haut, text="Studio", bg=GRIS_BOITE, fg=NOIR, font=(FAMILLE, 14, "bold")).pack(side="left")
        details = " · ".join(resume) if resume else ("Ton image" if apres is None else "")
        tk.Label(haut, text=details, bg=GRIS_BOITE, fg="#2e2e2e", font=(FAMILLE, 10), anchor="w",
                 justify="left", wraplength=largeur - 140).pack(side="left", padx=(12, 0), fill="x")
        cote = (largeur - 28, hauteur_image or self.HAUTEUR_IMAGE)
        self.img_avant = vignette_tk(avant, *cote)
        self.img_apres = vignette_tk(apres, *cote) if apres is not None else None
        self.affichage = tk.Label(self, bg=GRIS_BOITE, image=self.img_apres or self.img_avant)
        self.affichage.pack(padx=12, pady=6)
        boutons = tk.Frame(self, bg=GRIS_BOITE)
        boutons.pack(fill="x", padx=12, pady=(4, 12))
        if apres is not None:
            self.bouton_bascule = bouton_orange(boutons, "Voir l'avant", self.basculer, taille=9)
            self.bouton_bascule.pack(side="left")
            self.etiquette = tk.Label(boutons, text="Après", bg=GRIS_BOITE, fg=NOIR, font=(FAMILLE, 10, "bold"))
            self.etiquette.pack(side="left", padx=10)
        bouton_orange(boutons, "Mettre dans le Codex", self.vers_codex, taille=9).pack(side="right")
        self.bouton_projet = bouton_orange(boutons, "Garder dans le projet", self.vers_projet, taille=9)
        self.bouton_projet.pack(side="right", padx=(0, 8))
        bouton_orange(boutons, "Enregistrer", self.enregistrer, taille=9).pack(side="right", padx=(0, 8))
        if anime:   # le Studio s'ouvre en glissant vers le bas
            self.update_idletasks()
            hauteur = self.winfo_reqheight()
            self.pack_propagate(False)
            self.config(width=largeur, height=1)

            def grandir(v):
                self.config(height=max(1, int(v)))
                if suivre:
                    suivre()   # la conversation défile pour suivre le Studio qui s'ouvre

            app.animer(f"studio{id(self)}", 1, hauteur, grandir, etapes=20, douce=True)

    def image_montree(self):
        return self.apres if (self.montre_apres and self.apres is not None) else self.avant

    def basculer(self):
        self.montre_apres = not self.montre_apres
        self.affichage.config(image=self.img_apres if self.montre_apres else self.img_avant)
        self.bouton_bascule.config(text="Voir l'avant" if self.montre_apres else "Voir l'après")
        self.etiquette.config(text="Après" if self.montre_apres else "Avant")

    def enregistrer(self):
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer l'image", defaultextension=".png", initialfile="studio.png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg"), ("WebP", "*.webp")])
        if chemin:
            Path(chemin).write_bytes(octets_pour(chemin, self.image_montree()))

    def vers_codex(self):
        self.app.mettre_image_dans_codex(self.image_montree())

    def vers_projet(self):
        self.app.garder_image_projet(
            self.image_montree(),
            lambda nom: self.bouton_projet.config(text=f"Gardée dans « {nom[:18]} »"))


# ---------- Les pouvoirs magiques : tout roule sur ton ordi, gratuitement ----------
# Chaque pouvoir s'installe à part. S'il en manque un, l'app le dit au lieu de planter :
# c'est le même patron que Pillow plus haut.

def manque(quoi, commande, pourquoi=""):
    """Le message quand un pouvoir n'est pas installé : clair, en français, avec la commande."""
    return (f"{quoi} n'est pas installé sur ton ordi.\n\n"
            f"Pour l'ajouter, copie-colle ça dans un terminal :\n\n{commande}\n\n"
            + (pourquoi + "\n\n" if pourquoi else "")
            + "Ensuite, ferme pis rouvre Marceau.")


MESSAGE_OLLAMA = (
    "Ollama ne répond pas sur ton ordi.\n\n"
    "1. Installe-le :  curl -fsSL https://ollama.com/install.sh | sh\n"
    "2. Télécharge un modèle :  ollama pull llama3.2\n"
    "3. Démarre-le :  ollama serve\n\n"
    "Ollama est gratuit et tourne seulement chez vous : rien ne part sur Internet.")

# Les quatre façons de réécrire un texte (pouvoir « Changer le style »)
STYLES = (
    ("quebecois", "Québécois", "en bon français québécois familier, comme quelqu'un d'ici qui jase "
                               "avec un chum : tutoiement, tournures orales (y'a, j'suis, faque, pis, "
                               "ben, là), expressions d'ici quand ça sonne naturel"),
    ("formel", "Formel", "dans un français soutenu et professionnel : vouvoiement, phrases complètes, "
                         "vocabulaire précis, aucune tournure familière"),
    ("drole", "Drôle", "de façon drôle et légère : images cocasses, exagérations amusantes, clins "
                       "d'œil — sans jamais changer ce que le texte veut dire"),
    ("poetique", "Poétique", "de façon poétique : images, rythme, musicalité des phrases, sans rimes "
                             "forcées"),
)


def instructions_pouvoir(quoi, style=None):
    """Les consignes qu'on donne à l'IA locale selon le pouvoir demandé."""
    base = ("Tu es un outil d'écriture. Tu réponds SEULEMENT avec le texte demandé : "
            "pas d'explication, pas de préambule, pas de guillemets autour, pas de Markdown. ")
    if quoi == "continuer":
        return base + ("On te donne un texte. Écris la SUITE de ce texte, dans la même langue, "
                       "le même ton et le même style, sans répéter ce qui est déjà écrit. "
                       "Un ou deux paragraphes, pas plus. Commence directement par la suite.")
    if quoi == "style":
        return base + (f"On te donne un texte. Réécris-le {style}. Garde exactement le même sens et "
                       "les mêmes informations : tu changes la façon de le dire, pas ce qui est dit. "
                       "Garde à peu près la même longueur.")
    if quoi == "resumer":
        return base + ("On te donne un texte. Résume-le en quelques lignes, dans la langue du texte. "
                       "Va à l'essentiel : trois à six phrases courtes, ou des tirets s'il y a "
                       "plusieurs points distincts.")
    return base


def texte_par_ollama(modele, texte, quoi, style=None):
    """Envoie le texte à Ollama avec les consignes du pouvoir, pis rend ce qui revient."""
    reponse, _ = appeler_ollama(modele, [{"role": "user", "content": texte}],
                                instructions_pouvoir(quoi, style), num_ctx=CTX_OLLAMA_CODEX)
    return nettoyer_sortie(reponse)


def nettoyer_sortie(texte):
    """Enlève ce qu'un modèle local ajoute malgré les consignes : guillemets, ```, préambule."""
    texte = re.sub(r"<think>.*?</think>", "", texte or "", flags=re.S).strip()
    for _ in range(2):   # « Voici la suite : » PUIS ```…``` : il faut enlever les deux, dans l'ordre
        texte = re.sub(r"^(voici|voilà|bien sûr|certainement)[^\n:]{0,40}:\s*\n+", "",
                       texte, flags=re.I).strip()
        bloc = re.match(r"^```[a-zA-Z]*\n(.*?)\n?```$", texte, re.S)
        if bloc:
            texte = bloc.group(1).strip()
    if len(texte) > 1 and texte[0] in "\"«“" and texte[-1] in "\"»”":
        texte = texte[1:-1]
    return texte.strip()


# ----- 🎤 Dicter (faster-whisper) pis 🔊 Lire à voix haute (Piper) : les deux hors ligne -----
DOSSIER_VOIX = Path.home() / ".local" / "share" / "ecriture" / "voix"
MODELE_WHISPER = "small"          # tiny, base, small, medium, large-v3 — plus gros = meilleur, plus lent
VOIX_PIPER = "fr_FR-siwis-medium"  # la voix française par défaut
TAUX = 16000                      # 16 kHz mono : ce que Whisper attend

MESSAGE_WHISPER = manque(
    "faster-whisper (la dictée)",
    "pip install faster-whisper sounddevice numpy\nsudo apt install libportaudio2",
    "Au premier usage, il télécharge le modèle de reconnaissance (environ 500 Mo pour\n"
    "« small ») : après, la dictée marche sans Internet.\n\n"
    "Sur Ubuntu récent, pip refuse d'installer dans le Python du système. Fais plutôt :\n"
    "    python3 -m venv ~/ecriture-venv\n"
    "    ~/ecriture-venv/bin/pip install faster-whisper sounddevice numpy")

MESSAGE_MICRO = (
    "Aucun micro trouvé.\n\n"
    "Vérifie que ton micro est branché, puis :\n\n"
    "1. Installe la librairie audio :  sudo apt install libportaudio2\n"
    "2. Regarde si le système le voit :  arecord -l\n"
    "3. Choisis-le dans Paramètres → Son → Entrée\n\n"
    "Ensuite, ferme pis rouvre Marceau.")

_whisper = None
_voix_piper = None


def micro_pret():
    """Rend (True, "") si on peut enregistrer, sinon (False, le message à montrer)."""
    try:
        import sounddevice
    except ImportError:
        return False, MESSAGE_WHISPER
    except OSError:
        return False, MESSAGE_MICRO     # la librairie PortAudio manque au système
    try:
        if not any(a["max_input_channels"] > 0 for a in sounddevice.query_devices()):
            return False, MESSAGE_MICRO
    except Exception:
        return False, MESSAGE_MICRO
    return True, ""


def enregistreur():
    """Ouvre le micro en 16 kHz mono. Rend (le flux, la liste où les morceaux s'accumulent)."""
    import sounddevice
    morceaux = []
    flux = sounddevice.InputStream(
        samplerate=TAUX, channels=1, dtype="float32",
        callback=lambda donnees, n, t, statut: morceaux.append(donnees.copy()))
    flux.start()
    return flux, morceaux


def whisper_francais():
    """Charge le modèle de reconnaissance. On le garde : il est long à ouvrir."""
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel(MODELE_WHISPER, device="cpu", compute_type="int8")
    return _whisper


def transcrire(morceaux):
    """Transforme ce qui a été enregistré en texte français."""
    import numpy
    if not morceaux:
        return ""
    son = numpy.concatenate(morceaux).flatten().astype("float32")
    if len(son) < TAUX // 3:        # moins d'un tiers de seconde : y'a rien là
        return ""
    bouts, _ = whisper_francais().transcribe(son, language="fr", beam_size=5,
                                             vad_filter=True)
    return " ".join(b.text.strip() for b in bouts).strip()


def fichier_voix():
    """Le fichier .onnx de la voix française, s'il est téléchargé."""
    for dossier in (DOSSIER_VOIX, Path.cwd()):
        fichier = dossier / f"{VOIX_PIPER}.onnx"
        if fichier.exists():
            return fichier
    return None


def charger_voix():
    """Charge la voix Piper. On la garde : elle est longue à ouvrir."""
    global _voix_piper
    if _voix_piper is None:
        from piper import PiperVoice
        chemin = fichier_voix()
        if chemin is None:
            raise FileNotFoundError("voix")
        _voix_piper = PiperVoice.load(chemin)
    return _voix_piper


def telecharger_voix():
    """Télécharge la voix française (une seule fois : après, ça marche sans Internet)."""
    DOSSIER_VOIX.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "piper.download_voices", VOIX_PIPER,
                    "--download-dir", str(DOSSIER_VOIX)], check=True, capture_output=True)
    if fichier_voix() is None:
        raise RuntimeError("La voix ne s'est pas téléchargée.")
    return True


def arreter_son():
    """Coupe la lecture en cours, s'il y en a une."""
    try:
        import sounddevice
        sounddevice.stop()
    except Exception:
        pass


# ----- La voix qui lit les réponses de l'IA (chat pis Codex) -----
LONGUEUR_VOIX = 4000        # on lit un bon bout, pas un roman : au-delà, on coupe à la fin d'une phrase
VOIX_SYSTEME = ("spd-say", "espeak-ng", "espeak")   # déjà sur la plupart des Ubuntu de bureau

MESSAGE_VOIX = (
    "Aucune voix n'est installée sur ton ordi.\n\n"
    "La plus simple, la voix du système :\n"
    "    sudo apt install speech-dispatcher espeak-ng\n\n"
    "Pour une voix plus naturelle (Piper) — sur Ubuntu récent, pip refuse d'installer dans\n"
    "le Python du système, faque on passe par un environnement à part :\n"
    "    python3 -m venv ~/ecriture-venv\n"
    "    ~/ecriture-venv/bin/pip install piper-tts\n"
    f"    ~/ecriture-venv/bin/python -m piper.download_voices {VOIX_PIPER} \\\n"
    "        --download-dir ~/.local/share/ecriture/voix\n\n"
    "Ensuite, ferme pis rouvre Marceau.")


def texte_pour_voix(texte):
    """Ce qui se dit bien à voix haute : pas de code, pas d'adresse web, pas de symboles."""
    texte = re.sub(r"```.*?(```|$)", " ", texte or "", flags=re.S)
    texte = re.sub(r"\[(PLAN|STUDIO|LIRE)\].*?(\[/\1\]|$)", " ", texte, flags=re.S | re.I)
    texte = re.sub(r"\[FICHIER[^\]]*\].*?(\[/FICHIER\]|$)", " ", texte, flags=re.S | re.I)
    texte = re.sub(r"\[APP[^\]]*\].*?(\[/APP\]|$)", " ", texte, flags=re.S | re.I)
    texte = re.sub(r"\[(M[ÉE]T[ÉE]O|IMAGE)[^\]]*\]", " ", texte, flags=re.I)
    texte = URL_WEB.sub(" ", texte)                   # « h t t p s deux-points… » : non merci
    texte = re.sub(r"`([^`]*)`", r"\1", texte)
    texte = re.sub(r"^\s*(?:[-•*]|\d+[.)])\s+", "", texte, flags=re.M)   # les puces de liste
    texte = re.sub(r"[*_#>|~=\[\]{}<]+", " ", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "So")   # les émojis
    texte = re.sub(r"\(\s*\)", " ", texte)
    texte = re.sub(r"[ \t]+", " ", texte)
    texte = re.sub(r"\s*\n\s*", "\n", texte).strip()
    texte = texte.lstrip("-–—•,.;: ")        # jamais de « - » au début : ça passerait pour une option
    if len(texte) > LONGUEUR_VOIX:
        coupe = texte[:LONGUEUR_VOIX]
        fin = max(coupe.rfind(". "), coupe.rfind("! "), coupe.rfind("? "), coupe.rfind("\n"))
        texte = coupe[:fin + 1] if fin > LONGUEUR_VOIX // 2 else coupe
    return texte.strip()


def decouper_phrases(texte):
    """Des phrases pas trop courtes : la première se dit vite, pis on peut couper entre deux."""
    phrases = []
    for morceau in re.split(r"(?<=[.!?…:;])\s+|\n+", texte):
        morceau = morceau.strip()
        if not morceau:
            continue
        if phrases and len(phrases[-1]) < 40:
            phrases[-1] += " " + morceau     # une phrase de trois mots se colle à la suivante
        else:
            phrases.append(morceau)
    return phrases


def piper_installe():
    """Piper est-il là? On regarde sans l'importer : l'importer gèlerait la fenêtre une seconde."""
    import importlib.util
    return importlib.util.find_spec("piper") is not None


def moteur_voix():
    """La voix qu'on a : Piper (naturelle) si elle est là, sinon celle du système. None : aucune."""
    if fichier_voix() is not None and piper_installe():
        return "piper"
    for outil in VOIX_SYSTEME:
        if shutil.which(outil):
            return outil
    return None


def synthese_piper(phrase):
    """Une phrase lue par Piper, dans un fichier temporaire (effacé après l'avoir joué)."""
    descripteur, chemin = tempfile.mkstemp(suffix=".wav", prefix="marceau-voix-")
    os.close(descripteur)
    with wave.open(chemin, "wb") as f:
        charger_voix().synthesize_wav(phrase, f)
    return chemin


class Voix:
    """Lit à voix haute dans un fil à part. Une nouvelle lecture coupe l'ancienne.

    parle : True pendant qu'une lecture est en cours.
    sur_changement : appelé quand ça commence ou finit de parler (pour les boutons).
    """
    SONDE = 0.05       # aux combien de secondes on regarde si on doit se taire

    def __init__(self, sur_changement=None):
        self.generation = 0
        self.parle = False
        self.processus = None
        self.dernier_moteur = None
        self.sur_changement = sur_changement or (lambda: None)
        self.verrou = threading.Lock()

    def moteur(self):
        return moteur_voix()

    def parler(self, texte):
        """Commence à lire. Rend False s'il n'y a rien à dire, ou pas de voix."""
        texte = texte_pour_voix(texte)
        moteur = self.moteur() if texte else None
        if not moteur:
            return False
        with self.verrou:
            self.generation += 1
            generation = self.generation
            self._couper()
            self.parle = True
            self.dernier_moteur = moteur
        self.sur_changement()
        threading.Thread(target=self._lire, args=(texte, generation, moteur), daemon=True).start()
        return True

    def taire(self):
        """Arrête tout de suite ce qui se lit."""
        with self.verrou:
            self.generation += 1
            self._couper()
            parlait, self.parle = self.parle, False
        if parlait:
            self.sur_changement()

    def _couper(self):
        """Coupe le son en cours (appelé avec le verrou)."""
        if self.processus is not None and self.processus.poll() is None:
            try:
                self.processus.kill()
            except OSError:
                pass
        self.processus = None
        if self.dernier_moteur == "piper":
            arreter_son()
        elif self.dernier_moteur == "spd-say":
            try:   # spd-say parle par un service : tuer le petit programme suffit pas
                subprocess.run(["spd-say", "-C"], capture_output=True, timeout=3)
            except Exception:
                pass

    def _encore(self, generation):
        return generation == self.generation

    def _lancer(self, commande, generation):
        """Lance un programme pis attend qu'il finisse — ou le tue si on doit se taire."""
        with self.verrou:
            if not self._encore(generation):
                return
            self.processus = subprocess.Popen(commande, stdout=subprocess.DEVNULL,
                                              stderr=subprocess.DEVNULL)
            processus = self.processus
        while processus.poll() is None:
            if not self._encore(generation):
                try:
                    processus.kill()
                except OSError:
                    pass
                return
            time.sleep(self.SONDE)

    def _jouer(self, chemin, generation):
        """Joue un .wav : sounddevice si possible, sinon le lecteur du système."""
        try:
            import numpy
            import sounddevice
            with wave.open(str(chemin), "rb") as f:
                taux = f.getframerate()
                son = numpy.frombuffer(f.readframes(f.getnframes()), dtype="int16")
            sounddevice.play(son, taux)
            while sounddevice.get_stream().active:
                if not self._encore(generation):
                    sounddevice.stop()
                    return
                time.sleep(self.SONDE)
            return
        except Exception:
            pass        # pas de PortAudio, ou pas de sortie de son : on passe au lecteur du système
        for outil in ("paplay", "aplay", "ffplay"):
            if shutil.which(outil):
                options = ["-nodisp", "-autoexit", "-loglevel", "quiet"] if outil == "ffplay" else []
                self._lancer([outil] + options + [str(chemin)], generation)
                return
        raise RuntimeError("Aucun lecteur de son trouvé. Installe-en un :  sudo apt install alsa-utils")

    def _lire(self, texte, generation, moteur):
        try:
            if moteur == "piper":
                for phrase in decouper_phrases(texte):   # la 1re phrase se dit pendant que Piper prépare les autres
                    if not self._encore(generation):
                        break
                    chemin = synthese_piper(phrase)
                    try:
                        self._jouer(chemin, generation)
                    finally:
                        Path(chemin).unlink(missing_ok=True)   # pas de .wav qui s'empilent
            elif moteur == "spd-say":
                self._lancer(["spd-say", "-w", "-l", "fr", texte], generation)
            else:
                self._lancer([moteur, "-v", "fr", texte], generation)
        except Exception:
            pass        # une voix qui marche pas ne doit jamais faire planter l'app
        finally:
            with self.verrou:
                fini = self._encore(generation) and self.parle
                if fini:
                    self.parle = False
            if fini:
                self.sur_changement()


class FenetreDictee(tk.Toplevel):
    """Pendant que ça enregistre : le temps qui passe, pis un bouton pour arrêter."""

    def __init__(self, app, arreter):
        super().__init__(app, bg=GRIS_MENU)
        self.app, self.arreter, self.debut = app, arreter, time.time()
        self.title("Dicter")
        self.transient(app)
        self.resizable(False, False)
        cadre = tk.Frame(self, bg=GRIS_MENU)
        cadre.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(cadre, text="\U0001f3a4  J'écoute…", bg=GRIS_MENU, fg=NOIR,
                 font=(FAMILLE, 15, "bold")).pack()
        self.temps = tk.Label(cadre, text="0:00", bg=GRIS_MENU, fg="#2e2e2e", font=(FAMILLE, 12))
        self.temps.pack(pady=(6, 0))
        tk.Label(cadre, text="Parle, pis clique Arrêter quand t'as fini.", bg=GRIS_MENU,
                 fg="#2e2e2e", font=(FAMILLE, 10), wraplength=300).pack(pady=(4, 14))
        bouton_orange(cadre, "⏹  Arrêter", self.fermer).pack()
        self.protocol("WM_DELETE_WINDOW", self.fermer)
        self.bind("<Escape>", lambda e: self.fermer())
        self.minuterie = None
        self.tictac()
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_reqwidth()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.grab_set()

    def tictac(self):
        secondes = int(time.time() - self.debut)
        self.temps.config(text=f"{secondes // 60}:{secondes % 60:02d}")
        self.minuterie = self.after(250, self.tictac)

    def fermer(self):
        if self.minuterie:
            self.after_cancel(self.minuterie)
            self.minuterie = None
        action, self.arreter = self.arreter, None
        self.destroy()
        if action:
            action()


# ----- 🪄 Corriger les fautes (LanguageTool : hors ligne, gratuit) -----
MESSAGE_LANGUETOOL = manque(
    "LanguageTool (le correcteur)",
    "sudo apt install default-jre\npip install language_tool_python",
    "LanguageTool a besoin de Java. Au premier lancement, il télécharge le correcteur\n"
    "(environ 250 Mo) : après, il marche sans Internet.\n\n"
    "Sur Ubuntu récent, pip refuse d'installer dans le Python du système. Fais plutôt :\n"
    "    python3 -m venv ~/ecriture-venv\n"
    "    ~/ecriture-venv/bin/pip install language_tool_python")

_correcteur = None


def correcteur_francais():
    """Ouvre LanguageTool en français. On le garde ouvert : il est long à démarrer."""
    global _correcteur
    if _correcteur is None:
        import language_tool_python
        _correcteur = language_tool_python.LanguageTool("fr")
    return _correcteur


def fermer_correcteur():
    global _correcteur
    if _correcteur is not None:
        try:
            _correcteur.close()
        except Exception:
            pass
        _correcteur = None


def trouver_fautes(texte):
    """Rend la liste des fautes : (début, fin, mauvais, proposé, explication)."""
    fautes = []
    for f in correcteur_francais().check(texte):
        debut, fin = f.offset, f.offset + f.errorLength
        propose = (f.replacements or [None])[0]
        if not propose or propose == texte[debut:fin]:
            continue          # rien à proposer : on n'en parle pas
        fautes.append((debut, fin, texte[debut:fin], propose,
                       (f.message or "").strip() or "Faute"))
    # De la fin vers le début : corriger une faute ne bouge pas les positions des autres
    fautes.sort(key=lambda f: f[0], reverse=True)
    return fautes


class FenetreFautes(tk.Toplevel):
    """Les fautes une par une : tu acceptes ou tu refuses chacune."""

    def __init__(self, app, fautes, appliquer):
        super().__init__(app, bg=GRIS_MENU)
        self.app, self.fautes, self.appliquer = app, fautes, appliquer
        self.acceptees = []
        self.i = 0
        self.title("Corriger les fautes")
        self.transient(app)
        self.resizable(False, False)

        cadre = tk.Frame(self, bg=GRIS_MENU)
        cadre.pack(fill="both", expand=True, padx=20, pady=18)
        self.compteur = tk.Label(cadre, bg=GRIS_MENU, fg="#2e2e2e", anchor="w", font=(FAMILLE, 10))
        self.compteur.pack(fill="x")
        self.explication = tk.Label(cadre, bg=GRIS_MENU, fg=NOIR, anchor="w", justify="left",
                                    font=(FAMILLE, 11, "bold"), wraplength=510)
        self.explication.pack(fill="x", pady=(6, 12))
        self.phrase = tk.Label(cadre, bg=GRIS_ZONE, fg=NOIR, anchor="w", justify="left",
                               font=(FAMILLE, 11), wraplength=496, padx=12, pady=10)
        self.phrase.pack(fill="x")
        boutons = tk.Frame(cadre, bg=GRIS_MENU)
        boutons.pack(fill="x", pady=(18, 0))
        bouton_orange(boutons, "✓  Accepter", self.accepter).pack(side="left")
        bouton_orange(boutons, "✗  Refuser", self.refuser).pack(side="left", padx=(10, 0))
        bouton_orange(boutons, "Tout accepter", self.tout_accepter, taille=9).pack(side="right")
        self.bind("<Escape>", lambda e: self.terminer())
        self.protocol("WM_DELETE_WINDOW", self.terminer)
        self.montrer()
        self.centrer(app)
        self.grab_set()        # on répond à la fenêtre avant de retourner au texte

    def centrer(self, app):
        """La fenêtre prend juste la place qu'il faut, au milieu de l'app."""
        self.update_idletasks()
        largeur, hauteur = 560, self.winfo_reqheight()
        x = app.winfo_rootx() + (app.winfo_width() - largeur) // 2
        y = app.winfo_rooty() + (app.winfo_height() - hauteur) // 3
        self.geometry(f"{largeur}x{hauteur}+{max(0, x)}+{max(0, y)}")

    def montrer(self):
        if self.i >= len(self.fautes):
            self.terminer()
            return
        debut, fin, mauvais, propose, message = self.fautes[self.i]
        self.compteur.config(text=f"Faute {self.i + 1} sur {len(self.fautes)}")
        self.explication.config(text=message)
        self.phrase.config(text=f"{mauvais}   →   {propose}")

    def accepter(self):
        self.acceptees.append(self.fautes[self.i])
        self.i += 1
        self.montrer()

    def refuser(self):
        self.i += 1
        self.montrer()

    def tout_accepter(self):
        self.acceptees.extend(self.fautes[self.i:])
        self.i = len(self.fautes)
        self.terminer()

    def terminer(self):
        self.appliquer(self.acceptees)
        self.destroy()


# ----- 🌍 Traduire (Argos Translate : hors ligne, gratuit) -----
MESSAGE_ARGOS = manque(
    "Argos Translate (la traduction hors ligne)",
    "pip install argostranslate",
    "Sur Ubuntu récent, pip refuse d'installer dans le Python du système. Fais plutôt :\n"
    "    python3 -m venv ~/ecriture-venv\n"
    "    ~/ecriture-venv/bin/pip install argostranslate")

LANGUES = {"fr": "français", "en": "anglais"}


def argos_traduction():
    """Charge Argos juste quand on en a besoin : l'app démarre vite pareil."""
    import argostranslate.translate
    return argostranslate.translate


def argos_paquets():
    import argostranslate.package
    return argostranslate.package


def argos_installe():
    """Rend True si Argos Translate est sur l'ordi."""
    try:
        argos_traduction()
        return True
    except Exception:
        return False


def paires_installees():
    """Les traductions déjà téléchargées, ex. {('fr', 'en'), ('en', 'fr')}."""
    try:
        paires = set()
        for langue in argos_traduction().get_installed_languages():
            for vers in getattr(langue, "translations_to", []) or []:
                paires.add((langue.code, vers.to_lang.code))
            # Selon la version d'Argos, la liste s'appelle autrement
            for t in getattr(langue, "translations", []) or []:
                cible = getattr(getattr(t, "to_lang", None), "code", None)
                if cible:
                    paires.add((langue.code, cible))
        return paires
    except Exception:
        return set()


def telecharger_langue(de, vers):
    """Télécharge une paire de langues (une seule fois : après, ça marche sans Internet)."""
    paquets = argos_paquets()
    paquets.update_package_index()
    for p in paquets.get_available_packages():
        if p.from_code == de and p.to_code == vers:
            paquets.install_from_path(p.download())
            return True
    raise RuntimeError(f"Argos n'offre pas la traduction {de} vers {vers}.")


def traduire_texte(texte, de, vers):
    resultat = argos_traduction().translate(texte, de, vers)
    return (resultat or "").strip()


# ---------- Le moteur de fichiers : faire un document qu'on peut envoyer ----------
# Tout est écrit à la main avec la bibliothèque standard : pas de librairie à installer.
DOSSIER_FICHIERS = Path.home() / ".local" / "share" / "ecriture" / "fichiers"

PDF_LARGEUR, PDF_HAUTEUR = 595, 842     # une page A4, en points
PDF_MARGE = 56                          # 2 cm de marge
PDF_CORPS, PDF_INTERLIGNE = 11, 15.5
PDF_TITRE = 20

# Largeur de chaque lettre en Helvetica (millièmes de la taille), des codes 32 à 126.
# C'est ce qui permet de couper les lignes au bon endroit, sans police à installer.
LARGEURS_HELVETICA = (
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584)
LARGEURS_HELVETICA_GRAS = (
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
    975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
    611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584)


def _largeur_lettre(c, table):
    """Largeur d'une lettre. « é » est large comme « e » : les accents changent rien."""
    code = ord(c)
    if 32 <= code <= 126:
        return table[code - 32]
    sans = unicodedata.normalize("NFD", c)[:1]
    code = ord(sans) if sans else 110
    return table[code - 32] if 32 <= code <= 126 else table[ord("n") - 32]


def largeur_texte(texte, taille, gras=False):
    table = LARGEURS_HELVETICA_GRAS if gras else LARGEURS_HELVETICA
    return sum(_largeur_lettre(c, table) for c in texte) * taille / 1000


def couper_lignes(texte, taille, largeur_max, gras=False):
    """Coupe le texte pour qu'il rentre dans la largeur, sans couper les mots en deux."""
    lignes = []
    for paragraphe in texte.split("\n"):
        if not paragraphe.strip():
            lignes.append("")
            continue
        ligne = ""
        for mot in paragraphe.split(" "):
            essai = f"{ligne} {mot}".strip()
            if ligne and largeur_texte(essai, taille, gras) > largeur_max:
                lignes.append(ligne)
                ligne = mot
            else:
                ligne = essai
            # Un mot plus long que la ligne (une longue adresse web) : on le coupe
            while largeur_texte(ligne, taille, gras) > largeur_max and len(ligne) > 1:
                coupe = len(ligne) - 1
                while coupe > 1 and largeur_texte(ligne[:coupe], taille, gras) > largeur_max:
                    coupe -= 1
                lignes.append(ligne[:coupe])
                ligne = ligne[coupe:]
        lignes.append(ligne)
    return lignes


def _texte_pdf(texte):
    """Encode le texte comme le PDF l'attend (WinAnsi), avec les parenthèses protégées."""
    brut = texte.encode("cp1252", "replace")
    for avant, apres in ((b"\\", b"\\\\"), (b"(", b"\\("), (b")", b"\\)")):
        brut = brut.replace(avant, apres)
    return brut


def _jpeg_pour_pdf(image):
    """Le PDF sait lire le JPEG tel quel : on lui donne les octets sans les retoucher."""
    copie = image.convert("RGB")
    copie.thumbnail((1600, 1600))
    tampon = io.BytesIO()
    copie.save(tampon, "JPEG", quality=85)
    return tampon.getvalue(), copie.width, copie.height


def ecrire_pdf(chemin, titre, blocs):
    """Écrit un vrai PDF : un titre, des paragraphes, des images. Retourne le nombre de pages.

    blocs : liste de ("texte", "…") et ("image", une image Pillow).
    """
    largeur_utile = PDF_LARGEUR - 2 * PDF_MARGE
    pages, page, y = [], [], PDF_HAUTEUR - PDF_MARGE
    images_pdf = []            # (octets JPEG, largeur, hauteur)

    def nouvelle_page():
        nonlocal page, y
        if page:
            pages.append(page)
        page, y = [], PDF_HAUTEUR - PDF_MARGE

    def place(hauteur):
        """Assure qu'il reste la place voulue, sinon passe à la page suivante."""
        nonlocal y
        if y - hauteur < PDF_MARGE:
            nouvelle_page()

    if titre.strip():
        for ligne in couper_lignes(titre.strip(), PDF_TITRE, largeur_utile, gras=True):
            place(PDF_TITRE * 1.3)
            y -= PDF_TITRE
            page.append(("texte", PDF_MARGE, y, ligne, PDF_TITRE, True))
            y -= PDF_TITRE * 0.3
        y -= PDF_INTERLIGNE

    for sorte, valeur in blocs:
        if sorte == "texte":
            for ligne in couper_lignes(valeur, PDF_CORPS, largeur_utile):
                place(PDF_INTERLIGNE)
                y -= PDF_INTERLIGNE
                if ligne:
                    page.append(("texte", PDF_MARGE, y, ligne, PDF_CORPS, False))
        elif sorte == "image" and Image is not None:
            octets, li, hi = _jpeg_pour_pdf(valeur)
            largeur = min(largeur_utile, li)
            hauteur = hi * largeur / li
            maxi = PDF_HAUTEUR - 2 * PDF_MARGE
            if hauteur > maxi:                       # une image très haute rentre quand même
                hauteur, largeur = maxi, largeur * maxi / hauteur
            place(hauteur + 12)
            y -= hauteur + 6
            images_pdf.append(octets)
            page.append(("image", PDF_MARGE + (largeur_utile - largeur) / 2, y,
                         largeur, hauteur, len(images_pdf) - 1))
            y -= 8
    if page or not pages:
        pages.append(page)

    # ----- On assemble les objets du PDF -----
    n_pages = len(pages)
    premier_contenu = 5
    premiere_image = premier_contenu + n_pages
    premiere_page = premiere_image + len(images_pdf)
    objets = {}

    objets[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    enfants = b" ".join(f"{premiere_page + i} 0 R".encode() for i in range(n_pages))
    objets[2] = (b"<< /Type /Pages /Count " + str(n_pages).encode()
                 + b" /Kids [" + enfants + b"] >>")
    objets[3] = (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                 b"/Encoding /WinAnsiEncoding >>")
    objets[4] = (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
                 b"/Encoding /WinAnsiEncoding >>")

    for i, octets in enumerate(images_pdf):
        largeur, hauteur = Image.open(io.BytesIO(octets)).size
        objets[premiere_image + i] = (
            b"<< /Type /XObject /Subtype /Image /Width " + str(largeur).encode()
            + b" /Height " + str(hauteur).encode()
            + b" /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length "
            + str(len(octets)).encode() + b" >>\nstream\n" + octets + b"\nendstream")

    for i, contenu_page in enumerate(pages):
        morceaux, utilisees = [], []
        for element in contenu_page:
            if element[0] == "texte":
                _, x, ty, ligne, taille, gras = element
                morceaux.append(b"BT /" + (b"F2" if gras else b"F1") + b" "
                                + f"{taille:g}".encode() + b" Tf "
                                + f"{x:.1f} {ty:.1f}".encode() + b" Td ("
                                + _texte_pdf(ligne) + b") Tj ET")
            else:
                _, x, iy, largeur, hauteur, indice = element
                nom = f"Im{indice}".encode()
                utilisees.append((nom, premiere_image + indice))
                morceaux.append(b"q " + f"{largeur:.2f} 0 0 {hauteur:.2f} {x:.2f} {iy:.2f}".encode()
                                + b" cm /" + nom + b" Do Q")
        flux = b"\n".join(morceaux)
        objets[premier_contenu + i] = (b"<< /Length " + str(len(flux)).encode() + b" >>\nstream\n"
                                       + flux + b"\nendstream")
        xobjets = b""
        if utilisees:
            xobjets = (b" /XObject << " + b" ".join(b"/" + nom + b" " + str(num).encode() + b" 0 R"
                                                    for nom, num in utilisees) + b" >>")
        objets[premiere_page + i] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 "
            + f"{PDF_LARGEUR} {PDF_HAUTEUR}".encode() + b"] /Resources << /Font << /F1 3 0 R "
            b"/F2 4 0 R >>" + xobjets + b" >> /Contents "
            + str(premier_contenu + i).encode() + b" 0 R >>")

    sortie = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    positions = {}
    for numero in sorted(objets):
        positions[numero] = len(sortie)
        sortie += str(numero).encode() + b" 0 obj\n" + objets[numero] + b"\nendobj\n"
    debut_xref = len(sortie)
    total = max(objets) + 1
    sortie += b"xref\n0 " + str(total).encode() + b"\n0000000000 65535 f \n"
    for numero in range(1, total):
        sortie += f"{positions[numero]:010d} 00000 n \n".encode()
    sortie += (b"trailer\n<< /Size " + str(total).encode() + b" /Root 1 0 R >>\nstartxref\n"
               + str(debut_xref).encode() + b"\n%%EOF\n")
    Path(chemin).write_bytes(bytes(sortie))
    return n_pages


def ecrire_html(chemin, titre, blocs):
    """Une page web d'un seul fichier : les images sont dedans, ça s'ouvre partout."""
    def proteger(t):
        return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    corps = []
    for sorte, valeur in blocs:
        if sorte == "texte":
            for paragraphe in valeur.split("\n"):
                corps.append(f"<p>{proteger(paragraphe)}</p>" if paragraphe.strip() else "")
        elif sorte == "image" and Image is not None:
            donnees = image_pour_ia(valeur)
            corps.append(f'<img src="data:{donnees["media_type"]};base64,{donnees["data"]}" alt="">')
    Path(chemin).write_text(
        "<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{proteger(titre) or 'Document'}</title>\n"
        "<style>\n"
        f"  body {{ background: {GRIS_FOND}; color: {NOIR}; font-family: system-ui, sans-serif;\n"
        "         margin: 0; padding: 40px 20px; line-height: 1.6; }\n"
        f"  main {{ max-width: 760px; margin: 0 auto; background: {GRIS_ZONE};\n"
        "          padding: 40px; border-radius: 14px; }\n"
        f"  h1 {{ margin-top: 0; border-bottom: 3px solid {ORANGE}; padding-bottom: 12px; }}\n"
        "  img { max-width: 100%; height: auto; border-radius: 10px; margin: 18px 0;\n"
        "        display: block; }\n"
        "  p { margin: 0 0 14px; white-space: pre-wrap; }\n"
        "</style>\n</head>\n<body>\n<main>\n"
        + (f"<h1>{proteger(titre)}</h1>\n" if titre.strip() else "")
        + "\n".join(corps)
        + "\n</main>\n</body>\n</html>\n", encoding="utf-8")
    return 1


def ecrire_texte(chemin, titre, blocs):
    """Du texte brut. Les images sont nommées, pas incluses : un .txt en contient pas."""
    parties = []
    if titre.strip():
        parties.append(titre.strip() + "\n" + "=" * len(titre.strip()))
    images = 0
    for sorte, valeur in blocs:
        if sorte == "texte":
            parties.append(valeur.strip("\n"))
        else:
            images += 1
            parties.append(f"[Image {images}]")
    texte = "\n\n".join(p for p in parties if p) + "\n"
    Path(chemin).write_text(texte, encoding="utf-8")
    return images


FORMATS = (
    ("pdf", "PDF — à imprimer ou à remettre", ".pdf", [("PDF", "*.pdf")], ecrire_pdf),
    ("html", "Page web — un seul fichier, images dedans", ".html", [("Page web", "*.html")], ecrire_html),
    ("txt", "Texte brut — sans les images", ".txt", [("Texte", "*.txt")], ecrire_texte),
)


class FenetreFichier(tk.Toplevel):
    """« Fichier ▸ Créer » : tu bâtis un document, tu choisis le format, pis tu l'envoies."""

    def __init__(self, app, titre, contenu, images):
        super().__init__(app, bg=GRIS_MENU)
        self.app, self.images = app, images
        self.title("Créer un fichier")
        self.transient(app)
        self.minsize(620, 520)
        cadre = tk.Frame(self, bg=GRIS_MENU)
        cadre.pack(fill="both", expand=True, padx=20, pady=18)

        tk.Label(cadre, text="Titre du document", bg=GRIS_MENU, fg=NOIR, anchor="w",
                 font=(FAMILLE, 11, "bold")).pack(fill="x")
        self.titre = tk.Entry(cadre, bg=GRIS_ZONE, fg=NOIR, insertbackground=NOIR, relief="flat",
                              bd=0, font=(FAMILLE, 12), highlightthickness=2,
                              highlightbackground=GRIS_BORD, highlightcolor=ORANGE)
        self.titre.insert(0, titre)
        self.titre.pack(fill="x", ipady=6, pady=(4, 14))

        tk.Label(cadre, text="Ce qu'il y a dedans", bg=GRIS_MENU, fg=NOIR, anchor="w",
                 font=(FAMILLE, 11, "bold")).pack(fill="x")
        zone = tk.Frame(cadre, bg=GRIS_MENU)
        zone.pack(fill="both", expand=True, pady=(4, 14))
        defil = barre_defilement(zone, "vertical")
        self.contenu = tk.Text(zone, height=10, width=1, yscrollcommand=defil.set, **style_zone(12))
        defil.config(command=self.contenu.yview)
        defil.pack(side="right", fill="y")
        self.contenu.pack(side="left", fill="both", expand=True)
        self.contenu.insert("1.0", contenu)

        self.choix_images = []
        if images:
            tk.Label(cadre, text=f"Les images de la conversation ({len(images)})", bg=GRIS_MENU,
                     fg=NOIR, anchor="w", font=(FAMILLE, 11, "bold")).pack(fill="x")
            rangee = tk.Frame(cadre, bg=GRIS_MENU)
            rangee.pack(fill="x", pady=(6, 14))
            self.vignettes = []
            for i, image in enumerate(images[:8]):
                case = tk.BooleanVar(value=True)
                self.choix_images.append(case)
                boite = tk.Frame(rangee, bg=GRIS_MENU)
                boite.pack(side="left", padx=(0, 10))
                # Un carré fixe : une image large pis une image carrée gardent leurs cases alignées
                carre = tk.Frame(boite, bg=GRIS_MENU, width=76, height=76)
                carre.pack()
                carre.pack_propagate(False)
                vignette = vignette_tk(image, 72, 72)
                self.vignettes.append(vignette)
                tk.Label(carre, image=vignette, bg=GRIS_MENU).place(relx=0.5, rely=0.5, anchor="center")
                tk.Checkbutton(boite, text=f"Image {i + 1}", variable=case, bg=GRIS_MENU, fg=NOIR,
                               activebackground=GRIS_MENU, activeforeground=NOIR,
                               selectcolor=GRIS_ZONE, font=(FAMILLE, 9), relief="flat", bd=0,
                               highlightthickness=0, cursor="hand2").pack()

        tk.Label(cadre, text="Sorte de fichier", bg=GRIS_MENU, fg=NOIR, anchor="w",
                 font=(FAMILLE, 11, "bold")).pack(fill="x")
        self.format = tk.StringVar(value="pdf")
        for cle, description, *_ in FORMATS:
            tk.Radiobutton(cadre, text=description, variable=self.format, value=cle, bg=GRIS_MENU,
                           fg=NOIR, activebackground=GRIS_MENU, activeforeground=NOIR,
                           selectcolor=GRIS_ZONE, font=(FAMILLE, 10), anchor="w", relief="flat",
                           bd=0, highlightthickness=0, cursor="hand2").pack(fill="x", padx=2)

        boutons = tk.Frame(cadre, bg=GRIS_MENU)
        boutons.pack(fill="x", pady=(16, 0))
        bouton_orange(boutons, "Créer le fichier", self.creer).pack(side="left")
        bouton_orange(boutons, "Annuler", self.destroy, taille=9).pack(side="left", padx=(10, 0))
        self.mot = tk.Label(boutons, text="", bg=GRIS_MENU, fg=NOIR, font=(FAMILLE, 9), anchor="w")
        self.mot.pack(side="left", padx=(14, 0), fill="x", expand=True)

        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_reqwidth()) // 2
        y = app.winfo_rooty() + max(20, (app.winfo_height() - self.winfo_reqheight()) // 3)
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.titre.focus_set()

    def blocs(self):
        """Ce qui va dans le fichier : ton texte, pis les images que t'as cochées."""
        texte = self.contenu.get("1.0", "end-1c").strip()
        blocs = [("texte", texte)] if texte else []
        for case, image in zip(self.choix_images, self.images):
            if case.get():
                blocs.append(("image", image))
        return blocs

    def creer(self):
        blocs = self.blocs()
        if not blocs:
            self.mot.config(text="Écris quelque chose, ou coche une image.")
            return
        cle = self.format.get()
        _, _, extension, types, ecrire = next(f for f in FORMATS if f[0] == cle)
        titre = self.titre.get().strip()
        DOSSIER_FICHIERS.mkdir(parents=True, exist_ok=True)
        propose = re.sub(r'[<>:"/\\|?*]', "-", titre)[:60].strip() or "document"
        chemin = filedialog.asksaveasfilename(
            title="Créer le fichier", parent=self, defaultextension=extension,
            initialdir=str(DOSSIER_FICHIERS), initialfile=propose + extension,
            filetypes=types + [("Tous les fichiers", "*.*")])
        if not chemin:
            return
        try:
            ecrire(chemin, titre, blocs)
        except Exception as e:
            messagebox.showerror("Créer un fichier", f"Ça n'a pas marché : {e}", parent=self)
            return
        self.app.fichier_cree(chemin)
        self.destroy()


# ---------- Le Studio d'applications : l'IA construit une petite app, pis tu la vois ----------
def extraire_app(texte):
    """Sort l'app HTML d'une réponse. Rend (texte sans l'app, {"titre", "html"} ou None).

    D'abord le bloc [APP titre]…[/APP] demandé dans les consignes; sinon un ```html avec une
    vraie page dedans; sinon une page <!DOCTYPE html>…</html> écrite telle quelle.
    """
    m = re.search(r"\[APP(?:[ \t:\-]+([^\]\n]*))?\][ \t]*\n?(.*?)(?:\[/APP\]|$)", texte, re.S | re.I)
    if m:
        titre, html = (m.group(1) or "").strip(), m.group(2)
    else:
        m = re.search(r"```(?:html|htm)?[ \t]*\n(.*?)(?:```|$)", texte, re.S | re.I)
        if m and re.search(r"<(!doctype|html|body)\b", m.group(1), re.I):
            titre, html = "", m.group(1)
        else:
            m = re.search(r"<!doctype html.*?(?:</html>|$)", texte, re.S | re.I)
            if not m:
                return texte, None
            titre, html = "", m.group(0)
    reste = (texte[:m.start()] + texte[m.end():]).strip()
    html = re.sub(r"^\s*```[\w-]*[ \t]*\n", "", html)        # des ``` que l'IA aurait mis dans le bloc
    html = re.sub(r"\n\s*```\s*$", "", html).strip()
    if not re.search(r"<[a-z!]", html, re.I):
        return texte, None                                     # un bloc sans HTML dedans : c'est pas une app
    if not titre:
        t = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        titre = re.sub(r"\s+", " ", t.group(1)).strip() if t else ""
    return reste, {"titre": (titre or "Mon app")[:60], "html": html + "\n"}


def identifiant_app(titre):
    """« Mon Jeu de Tic-Tac-Toé! » → « mon-jeu-de-tic-tac-toe » : l'adresse de l'app dans l'aperçu."""
    return re.sub(r"[^a-z0-9]+", "-", sans_accents(titre)).strip("-")[:40] or "app"


class ApercuApps:
    """Le serveur d'aperçu : chaque app du Studio a son adresse sur ton ordi.

    Il écoute seulement sur 127.0.0.1 : personne d'autre peut s'y connecter. Quand l'IA
    refait une app (même titre), l'onglet déjà ouvert dans ton navigateur se recharge tout seul.
    """
    # Glissé à la fin de la page : il regarde aux 0,8 s si l'app a une nouvelle version
    RECHARGE = ("<script>/* Aperçu Marceau : se recharge tout seul quand l'IA refait l'app */"
                "(function(){{var v={version};setInterval(function(){{"
                "fetch('/v/{ident}',{{cache:'no-store'}}).then(function(r){{return r.json();}})"
                ".then(function(n){{if(n.version!==v)location.reload();}}).catch(function(){{}});"
                "}},800);}})();</script>")

    def __init__(self):
        self.apps = {}              # identifiant -> {"titre", "html", "version"}
        self.verrou = threading.Lock()
        self.serveur = None

    def publier(self, titre, html):
        """Met une app (ou sa nouvelle version) en ligne. Rend (identifiant, version)."""
        ident = identifiant_app(titre)
        with self.verrou:
            vieille = self.apps.get(ident)
            if vieille is None:
                version = 1
            elif vieille["html"] == html:
                version = vieille["version"]          # la même : pas besoin de recharger
            else:
                version = vieille["version"] + 1
            self.apps[ident] = {"titre": titre, "html": html, "version": version}
        self.demarrer()
        return ident, version

    def adresse(self, ident):
        self.demarrer()
        return f"http://127.0.0.1:{self.serveur.server_address[1]}/a/{ident}"

    def page(self, ident):
        with self.verrou:
            app = self.apps.get(ident)
        if app is None:
            return None
        script = self.RECHARGE.format(version=app["version"], ident=ident)
        html = app["html"]
        fin = html.lower().rfind("</body>")
        return html[:fin] + script + html[fin:] if fin >= 0 else html + script

    def version(self, ident):
        with self.verrou:
            app = self.apps.get(ident)
        return None if app is None else app["version"]

    def demarrer(self):
        if self.serveur is not None:
            return
        apercu = self

        class Gestion(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                morceaux = self.path.split("?")[0].strip("/").split("/")
                if len(morceaux) == 2 and morceaux[0] == "a":
                    page = apercu.page(morceaux[1])
                    if page is not None:
                        return self.envoyer(200, "text/html; charset=utf-8", page.encode("utf-8"))
                if len(morceaux) == 2 and morceaux[0] == "v":
                    version = apercu.version(morceaux[1])
                    if version is not None:
                        return self.envoyer(200, "application/json",
                                            json.dumps({"version": version}).encode("utf-8"))
                self.envoyer(404, "text/plain; charset=utf-8", "Pas d'app ici.".encode("utf-8"))

            def envoyer(self, code, sorte, corps):
                self.send_response(code)
                self.send_header("Content-Type", sorte)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(corps)))
                self.end_headers()
                self.wfile.write(corps)

            def log_message(self, *args):
                pass            # pas de journal dans le terminal à chaque rechargement

        self.serveur = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Gestion)
        self.serveur.daemon_threads = True
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def arreter(self):
        if self.serveur is not None:
            self.serveur.shutdown()
            self.serveur.server_close()
            self.serveur = None


class StudioApp(tk.Frame):
    """Le Studio d'une app : son code qui s'écrit sous tes yeux, pis de quoi la voir, la garder, l'envoyer."""
    LIGNES = 14            # hauteur du code dans la carte (après, ça défile)
    TAILLE = 10

    def __init__(self, parent, app, titre, html, ident, version, largeur, anime=True, fini=None):
        super().__init__(parent, bg=GRIS_BOITE, highlightthickness=2, highlightbackground=ORANGE)
        self.app, self.titre, self.html, self.ident = app, titre, html, ident
        haut = tk.Frame(self, bg=GRIS_BOITE)
        haut.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(haut, text="Studio", bg=GRIS_BOITE, fg=NOIR, font=(FAMILLE, 14, "bold")).pack(side="left")
        lignes = html.count("\n") or 1
        details = (f"{titre}" + (f"  ·  version {version}" if version > 1 else "")
                   + f"  ·  {lignes} lignes  ·  {taille_lisible(len(html.encode('utf-8')))}")
        tk.Label(haut, text=details, bg=GRIS_BOITE, fg="#2e2e2e", font=(FAMILLE, 10), anchor="w",
                 justify="left", wraplength=max(largeur - 140, 200)).pack(side="left", padx=(12, 0))

        cadre = tk.Frame(self, bg=CODE_FOND, width=largeur - 28)
        cadre.pack(fill="x", padx=12)
        hauteur = min(self.LIGNES, max(4, lignes + 1))   # une petite app : un petit cadre
        self.code = tk.Text(cadre, height=hauteur, width=1, wrap="none", bg=CODE_FOND, fg=CODE_TEXTE,
                            font=(FAMILLE_CODE, self.TAILLE), relief="flat", bd=0, highlightthickness=0,
                            padx=10, pady=6, insertwidth=0, selectbackground=CODE_SELECTION,
                            selectforeground="#ffffff")
        defil = barre_defilement(cadre, "vertical", CODE_FOND, command=self.code.yview)
        self.code.config(yscrollcommand=defil.set)
        defil.pack(side="right", fill="y")
        self.code.pack(side="left", fill="both", expand=True)
        for etiquette, (couleur, style) in COULEURS_CODE.items():
            self.code.tag_configure(etiquette, foreground=couleur,
                                    font=(FAMILLE_CODE, self.TAILLE, style) if style else (FAMILLE_CODE, self.TAILLE))
        tk.Frame(self, width=largeur, height=0, bg=GRIS_BOITE).pack()   # fixe la largeur de la carte

        boutons = tk.Frame(self, bg=GRIS_BOITE)
        boutons.pack(fill="x", padx=12, pady=(8, 12))
        bouton_orange(boutons, "\u25b6  Voir l'app", self.voir, taille=9).pack(side="left")
        self.etat = tk.Label(boutons, text="", bg=GRIS_BOITE, fg="#2e2e2e", font=(FAMILLE, 9), anchor="w")
        self.etat.pack(side="left", padx=10)
        bouton_orange(boutons, "Mettre dans le Codex", self.vers_codex, taille=9).pack(side="right")
        bouton_orange(boutons, "Enregistrer", self.enregistrer, taille=9).pack(side="right", padx=(0, 8))

        if anime:
            self.etat.config(text="L'app se construit…")
            self.after(10, lambda: self.ecrire(fini))
        else:
            self.code.insert("1.0", html)
            self.colorer()
            self.code.config(state="disabled")

    def colorer(self):
        texte = self.code.get("1.0", "end-1c")[:120_000]
        for etiquette in COULEURS_CODE:
            self.code.tag_remove(etiquette, "1.0", "end")
        departs = [0] + [m.end() for m in re.finditer("\n", texte)]
        for a, b, etiquette in jetons(texte, "html"):
            la, lb = bisect_right(departs, a) - 1, bisect_right(departs, b) - 1
            self.code.tag_add(etiquette, f"{1 + la}.{a - departs[la]}", f"{1 + lb}.{b - departs[lb]}")

    def ecrire(self, fini=None):
        """Le code s'écrit en direct, vite, avec les couleurs qui suivent : on voit l'app se construire."""
        html = self.html
        tours = max(1, int(DUREE_CODE * 1000 / VITESSE_MS))
        paquet = max(1, -(-len(html) // tours))
        etat = {"position": 0, "tic": 0}

        def tour():
            try:
                if not self.code.winfo_exists():
                    return
                morceau = html[etat["position"]:etat["position"] + paquet]
                if morceau:
                    self.code.insert("end", morceau)
                    etat["position"] += paquet
                    etat["tic"] += 1
                    self.code.see("end")
                    if etat["tic"] % 10 == 0:
                        self.colorer()
                    self.code.after(VITESSE_MS, tour)
                    return
                self.colorer()
                self.code.see("1.0")
                self.code.config(state="disabled")
                self.etat.config(text="")
                if fini:
                    fini()
            except tk.TclError:
                return       # la carte a été effacée pendant que ça s'écrivait

        tour()

    def voir(self):
        self.app.voir_app(self.ident)
        self.etat.config(text="Ouverte dans ton navigateur. Elle se met à jour toute seule.")

    def enregistrer(self):
        chemin = self.app.enregistrer_app(self.titre, self.html)
        if chemin:
            self.etat.config(text=f"Enregistrée : {Path(chemin).name}")

    def vers_codex(self):
        self.app.app_dans_codex(self.titre, self.html)


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


# ---------- La police du système ----------
STYLES_POLICE = {"bold", "italic", "oblique", "regular", "medium", "light", "semibold", "semi-bold",
                 "book", "normal", "condensed", "thin", "heavy", "black", "extrabold", "extralight"}


def _famille_de(nom_complet):
    """« 'Ubuntu Sans Bold 11' » (comme gsettings l'écrit) → « Ubuntu Sans »."""
    nom = nom_complet.strip().strip("'\"")
    nom = re.sub(r"\s+\d+(?:\.\d+)?$", "", nom)          # la taille, à la fin
    mots = nom.split()
    while len(mots) > 1 and mots[-1].lower() in STYLES_POLICE:
        mots.pop()                                    # « Bold », « Italic »… à la fin
    return " ".join(mots)


def _sortie(commande):
    """Ce qu'une commande répond, ou "" si elle existe pas ou se plaint."""
    try:
        r = subprocess.run(commande, capture_output=True, text=True, timeout=2)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def polices_du_systeme():
    """Les polices de ton bureau, de la plus sûre à la moins sûre : (texte, code)."""
    texte, code = [], []
    # GNOME, Ubuntu, Cinnamon, Budgie, MATE récents : gsettings sait
    if shutil.which("gsettings"):
        for cle, liste in (("font-name", texte), ("monospace-font-name", code),
                           ("document-font-name", texte)):
            brut = _sortie(["gsettings", "get", "org.gnome.desktop.interface", cle])
            if brut:
                liste.append(_famille_de(brut))
    # KDE : c'est écrit dans ~/.config/kdeglobals (« font=Noto Sans,10,… »)
    kde = Path.home() / ".config" / "kdeglobals"
    try:
        for ligne in kde.read_text(errors="ignore").splitlines():
            if ligne.startswith("font="):
                texte.append(ligne[5:].split(",")[0].strip())
            elif ligne.startswith("fixed="):
                code.append(ligne[6:].split(",")[0].strip())
    except OSError:
        pass
    # Partout ailleurs : fontconfig dit quelle police le système prend pour « sans-serif »
    if shutil.which("fc-match"):
        for motif, liste in (("sans-serif", texte), ("monospace", code)):
            famille = _sortie(["fc-match", "-f", "%{family[0]}", motif])
            if famille:
                liste.append(famille)
    return texte, code


def choisir_polices(racine):
    """Prend la police du système — si Tk la connaît pour vrai — pour toute l'app.

    Ça doit rouler avant de bâtir la fenêtre : chaque morceau lit FAMILLE en se créant.
    """
    global FAMILLE, FAMILLE_CODE, POLICE, POLICE_BOUTON, POLICE_INVITE, POLICE_CODE
    connues = {f.lower(): f for f in tkfont.families(racine)}
    texte, code = polices_du_systeme()

    def premiere(candidats, defaut):
        for c in candidats:
            if c and c.lower() in connues:
                return connues[c.lower()]
        return defaut

    FAMILLE = premiere([POLICE_PERSO] + texte, FAMILLE)
    FAMILLE_CODE = premiere([POLICE_CODE_PERSO] + code, FAMILLE_CODE)
    POLICE, POLICE_BOUTON = (FAMILLE, 14), (FAMILLE, 11, "bold")
    POLICE_INVITE, POLICE_CODE = (FAMILLE, 18), (FAMILLE_CODE, 12)
    # Les polices de Tk lui-même suivent : les menus pis les petites fenêtres de dialogue
    for nom in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont",
                "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
        try:
            tkfont.nametofont(nom, root=racine).configure(family=FAMILLE)
        except tk.TclError:
            pass
    try:
        tkfont.nametofont("TkFixedFont", root=racine).configure(family=FAMILLE_CODE)
    except tk.TclError:
        pass
    return FAMILLE, FAMILLE_CODE


def fichier_police_systeme():
    """Le fichier de la police du système, en gras : pour écrire sur les images du Studio."""
    if not shutil.which("fc-match"):
        return None
    chemin = _sortie(["fc-match", "-f", "%{file}", f"{FAMILLE}:bold"])
    return chemin if chemin and Path(chemin).is_file() else None


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
    requete = urllib.request.Request(URL_MAJ, headers={"User-Agent": f"Marceau/{VERSION}"})
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


# ---------- Les 3 points d'attente : ils sautent pis passent du rouge au jaune au vert ----------
class PointsAttente(tk.Canvas):
    ROUGE, JAUNE, VERT = (255, 59, 48), (255, 214, 10), (60, 220, 60)
    PAS_MS = 30

    def __init__(self, parent, taille=16, fond=GRIS_ZONE):
        self.r = max(3, round(taille / 3.0))            # rayon des points
        espace = self.r * 3.2
        hauteur = int(taille * 1.7)
        super().__init__(parent, width=int(espace * 2 + self.r * 2 + 8), height=hauteur,
                         bg=fond, highlightthickness=0, bd=0)
        self.x = [4 + self.r + i * espace for i in range(3)]
        self.bas = hauteur - self.r - 3                  # où les points se posent
        self.saut = hauteur - 2 * self.r - 6             # hauteur du saut
        self.points = [self.create_oval(0, 0, 0, 0, outline="#3a3a3a", width=1) for _ in range(3)]
        self.t = 0.0
        self.animer()

    def couleur(self, p):
        """p = 0 : rouge, 0.5 : jaune, 1 : vert (avec toutes les couleurs entre les deux)."""
        a, b, k = (self.ROUGE, self.JAUNE, p / 0.5) if p < 0.5 else (self.JAUNE, self.VERT, (p - 0.5) / 0.5)
        return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * k) for i in range(3))

    def animer(self):
        try:
            if not self.winfo_exists():
                return
            self.t += 0.06
            for i, point in enumerate(self.points):
                bond = max(0.0, math.sin(self.t * 2.4 - i * 0.8)) ** 1.5   # chacun son tour, comme une vague
                y = self.bas - self.saut * bond
                self.coords(point, self.x[i] - self.r, y - self.r, self.x[i] + self.r, y + self.r)
                self.itemconfig(point, fill=self.couleur((math.sin(self.t * 1.1 - i * 0.6) + 1) / 2))
            self.after(self.PAS_MS, self.animer)
        except tk.TclError:
            return   # les points ont été effacés


def ajouter_ligne_attente(widget, texte, taille, etiquettes):
    """Ajoute « texte ● ● ● » (points animés) à la fin. Retourne les points pour les effacer après."""
    widget.insert("end", texte + " ", etiquettes + ("attente_texte",))
    points = PointsAttente(widget, taille)
    index = widget.index("end-1c")
    widget.window_create(index, window=points, align="center")
    for etiquette in etiquettes:
        widget.tag_add(etiquette, index)
    widget.insert("end", "\n", etiquettes)
    widget.see("end")
    return points


def enlever_ligne_attente(widget, etiquette, points):
    zone = widget.tag_ranges(etiquette)
    if zone:
        widget.delete(zone[0], zone[-1])
    if points is not None:
        points.destroy()


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
    est_image = False

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

    def recharger(self, contenu):
        """Le fichier a changé sur le disque (OpenCode) : l'onglet suit, sans « ● »."""
        self.remplacer(contenu)
        self.texte.edit_modified(False)   # sinon <<Modified>> le remarquerait « pas enregistré »
        self.set_modifie(False)

    def ecrire_code(self, contenu, duree=None, fini=None):
        """Écrit le code en direct dans l'éditeur, vite pis fluide, avec les couleurs qui suivent."""
        self.texte.edit_separator()
        self.texte.delete("1.0", "end")
        tours = max(1, int((duree or DUREE_CODE) * 1000 / VITESSE_MS))
        paquet = max(1, -(-len(contenu) // tours))
        etat = {"position": 0, "tic": 0}

        def tour():
            try:
                if not self.texte.winfo_exists():
                    return
                morceau = contenu[etat["position"]:etat["position"] + paquet]
                if morceau:
                    self.texte.insert("end", morceau)
                    etat["position"] += paquet
                    etat["tic"] += 1
                    self.texte.see("end")
                    if etat["tic"] % 8 == 0:
                        self.rafraichir()   # les couleurs suivent pendant que ça s'écrit
                    self.texte.after(VITESSE_MS, tour)
                else:
                    self.texte.edit_separator()
                    self.texte.mark_set("insert", "1.0")
                    self.texte.see("1.0")
                    self.rafraichir()
                    if fini:
                        fini()
            except tk.TclError:
                return   # l'onglet a été fermé pendant l'écriture

        tour()

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


# ---------- Une image ouverte dans le Codex (pour la voir, pis l'envoyer dans le projet) ----------
class OngletImage:
    """Pareil qu'un onglet de code, mais ça montre l'image au lieu du texte."""
    est_image = True

    def __init__(self, codex, chemin, octets, sha=None):
        self.codex, self.chemin, self.octets, self.sha = codex, chemin, octets, sha
        self.modifie = False
        self.cadre = tk.Frame(codex.zone_editeur, bg=CODE_FOND)
        self.cadre.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.texte = tk.Label(self.cadre, bg=CODE_FOND)   # « texte » : pour que le reste marche pareil
        self.texte.pack(expand=True)
        try:
            self.image = ouvrir_image(octets)
            info = f"{self.image.width} × {self.image.height} px · {taille_lisible(len(octets))}"
        except Exception:
            self.image, info = None, "Image impossible à afficher"
        tk.Label(self.cadre, text=f"{chemin}   ({info})", bg=CODE_FOND, fg="#9a9a9a",
                 font=(FAMILLE, 10)).pack(side="bottom", pady=8)
        self.cadre.bind("<Configure>", lambda e: self.planifier())
        self.image_tk = None

    def contenu(self):
        return None      # une image, ça n'a pas de texte

    def planifier(self):
        if self.image is None:
            return
        largeur = max(self.cadre.winfo_width() - 40, 100)
        hauteur = max(self.cadre.winfo_height() - 70, 100)
        self.image_tk = vignette_tk(self.image, largeur, hauteur)
        self.texte.config(image=self.image_tk)

    def set_modifie(self, valeur):
        if valeur != self.modifie:
            self.modifie = valeur
            self.codex.dessiner_onglets()


# ---------- Voir ce qui a changé dans un fichier ----------
COULEUR_AJOUT = "#a6ff4d"       # les lignes ajoutées, en vert lime
FOND_AJOUT = "#1d3312"
COULEUR_RETRAIT = "#ff8a80"     # celles qui partent, en rouge
FOND_RETRAIT = "#3a1b18"
COULEUR_PAREIL = "#9aa0a6"      # le reste, en gris pâle
COULEUR_SAUT = "#6c6c6c"


def calculer_diff(avant, apres, contexte=3):
    """Compare deux versions d'un fichier, ligne par ligne.

    Retourne (lignes, ajouts, retraits). Chaque ligne est
    (sorte, numéro, texte) où sorte vaut « ajout », « retrait », « pareil » ou « saut ».
    Les longs bouts pareils sont repliés en un « ⋯ » pour pas noyer les changements.
    """
    a, b = avant.splitlines(), apres.splitlines()
    lignes, ajouts, retraits = [], 0, 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            combien = i2 - i1
            if combien > contexte * 2 + 1:
                for k in range(contexte):
                    lignes.append(("pareil", j1 + k + 1, b[j1 + k]))
                lignes.append(("saut", 0, f"⋯ {combien - contexte * 2} lignes pareilles"))
                for k in range(combien - contexte, combien):
                    lignes.append(("pareil", j1 + k + 1, b[j1 + k]))
            else:
                for k in range(combien):
                    lignes.append(("pareil", j1 + k + 1, b[j1 + k]))
        else:
            for k in range(i1, i2):
                lignes.append(("retrait", 0, a[k]))
                retraits += 1
            for k in range(j1, j2):
                lignes.append(("ajout", k + 1, b[k]))
                ajouts += 1
    return lignes, ajouts, retraits


class CarteFichier(tk.Frame):
    """Un fichier touché par Codex : fermé, un clic l'ouvre pis montre ce qui a changé."""
    FOND_BARRE = "#3a3a3a"
    HAUTEUR_MAX = 460
    TAILLE = 10

    def __init__(self, parent, app, chemin, avant, apres, nouveau, largeur, ouvrir_editeur,
                 supprime=False):
        super().__init__(parent, bg=self.FOND_BARRE, highlightthickness=1,
                         highlightbackground="#5e5e5e")
        self.app = app
        self.chemin, self.nouveau, self.supprime = chemin, nouveau, supprime
        self.ouvert = False
        lignes, ajouts, retraits = calculer_diff(avant or "", apres)
        # Un cadre vide qui impose la largeur : sans ça, la carte s'écrase sur son contenu
        # et on voit juste un trait dans la conversation.
        tk.Frame(self, width=largeur, height=0, bg=self.FOND_BARRE).pack()

        # ----- La barre qu'on clique -----
        barre = tk.Frame(self, bg=self.FOND_BARRE, cursor="hand2", height=40)
        barre.pack(fill="x")
        barre.pack_propagate(False)
        if not supprime:     # un fichier supprimé, y'a plus rien à modifier
            bouton_orange(barre, "Modifier", lambda: ouvrir_editeur(chemin),
                          taille=9).pack(side="right", padx=8)
        self.fleche = tk.Label(barre, text="▸", bg=self.FOND_BARRE, fg=ORANGE,
                               font=(FAMILLE, 13, "bold"))
        self.fleche.pack(side="left", padx=(12, 8))
        nom = tk.Label(barre, text=chemin, bg=self.FOND_BARRE, fg="#f0f0f0",
                       font=(FAMILLE_CODE, 10, "bold"), anchor="w")
        nom.pack(side="left")
        compte = tk.Frame(barre, bg=self.FOND_BARRE)
        compte.pack(side="left", padx=12)
        etiquettes = [nom, self.fleche, barre, compte]
        if nouveau or supprime:
            e = tk.Label(compte, text="nouveau fichier" if nouveau else "fichier supprimé",
                         bg=self.FOND_BARRE, fg=COULEUR_AJOUT if nouveau else COULEUR_RETRAIT,
                         font=(FAMILLE, 9, "bold"))
            e.pack(side="left", padx=(0, 10))
            etiquettes.append(e)
        for texte, couleur in ((f"+{ajouts}", COULEUR_AJOUT), (f"−{retraits}", COULEUR_RETRAIT)):
            if texte in ("+0", "−0"):
                continue
            e = tk.Label(compte, text=texte, bg=self.FOND_BARRE, fg=couleur,
                         font=(FAMILLE_CODE, 10, "bold"))
            e.pack(side="left", padx=(0, 8))
            etiquettes.append(e)
        for w in etiquettes:
            w.bind("<Button-1>", self.basculer)

        # ----- Le code (caché tant que la carte est fermée) -----
        self.corps = tk.Frame(self, bg=CODE_FOND, height=1)
        self.corps.pack_propagate(False)
        defil = barre_defilement(self.corps, "vertical", CODE_FOND)
        self.texte = tk.Text(self.corps, wrap="none", bg=CODE_FOND, fg=COULEUR_PAREIL,
                             font=(FAMILLE_CODE, self.TAILLE), relief="flat", bd=0,
                             highlightthickness=0, padx=0, pady=6, insertwidth=0,
                             selectbackground=CODE_SELECTION, selectforeground="#ffffff",
                             yscrollcommand=defil.set)
        defil.config(command=self.texte.yview)
        defil.pack(side="right", fill="y")
        self.texte.pack(side="left", fill="both", expand=True)
        self.remplir(lignes)
        self.texte.config(state="disabled")
        hauteur_ligne = tkfont.Font(family=FAMILLE_CODE, size=self.TAILLE).metrics("linespace")
        self.cible = min(self.HAUTEUR_MAX, len(lignes) * hauteur_ligne + 16)

    def remplir(self, lignes):
        t = self.texte
        t.tag_configure("ajout", foreground=COULEUR_AJOUT, background=FOND_AJOUT)
        t.tag_configure("retrait", foreground=COULEUR_RETRAIT, background=FOND_RETRAIT)
        t.tag_configure("pareil", foreground=COULEUR_PAREIL)
        t.tag_configure("saut", foreground=COULEUR_SAUT, font=(FAMILLE_CODE, self.TAILLE, "italic"))
        t.tag_configure("numero", foreground=CODE_NUMEROS)
        for sorte, numero, contenu in lignes:
            if sorte == "saut":
                t.insert("end", f"      {contenu}\n", "saut")
                continue
            signe = {"ajout": "+", "retrait": "−", "pareil": " "}[sorte]
            t.insert("end", f"{numero or '':>4} ", ("numero", sorte))
            t.insert("end", f"{signe} {contenu}\n", sorte)

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

        self.app.animer(f"carte{id(self)}", depart, self.cible if self.ouvert else 1,
                        lambda v: self.corps.config(height=max(1, int(v))), fini, etapes=14)


# ---------- OpenCode : un agent de code open source qui travaille dans un dossier de ton ordi ----------
# OpenCode (opencode.ai) lit tes fichiers, les change pis lance des commandes, directement dans le
# dossier que tu choisis. Marceau le pilote avec l'IA choisie en bas (ta clé Claude ou un modèle
# Ollama) : t'as rien à configurer dans OpenCode. Sa config lui est passée en mémoire, pis ta clé
# reste dans son fichier protégé : OpenCode va la lire là, elle est jamais copiée ailleurs.
COMMANDE_OPENCODE = "curl -fsSL https://opencode.ai/install | bash"
CTX_OLLAMA_OPENCODE = 16384      # OpenCode a de longues consignes : il faut de la mémoire au modèle
DOSSIERS_IGNORES = {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
                    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".next", ".nuxt",
                    ".cache", ".gradle", ".dart_tool", ".idea", "dist", "build", "target"}
PHOTO_FICHIERS_MAX = 5000        # fichiers texte gardés en photo avant/après une demande
PHOTO_TAILLE_MAX = 500_000       # … d'au plus 500 Ko chacun


def trouver_opencode():
    """Le programme opencode : dans le PATH, sinon aux places où ses installateurs le mettent
    (lancé du menu, Marceau voit pas toujours le PATH de ton terminal)."""
    trouve = shutil.which("opencode")
    if trouve:
        return trouve
    maison = Path.home()
    for chemin in (maison / ".opencode" / "bin" / "opencode", maison / ".local" / "bin" / "opencode",
                   maison / ".npm-global" / "bin" / "opencode", maison / ".bun" / "bin" / "opencode",
                   Path("/usr/local/bin/opencode")):
        if chemin.is_file() and os.access(chemin, os.X_OK):
            return str(chemin)
    return None


def variante_opencode(modele):
    """Le nom de la copie d'un modèle Ollama qui a plus de mémoire, faite pour OpenCode."""
    nom, deux_points, etiquette = modele.rpartition(":")
    if not deux_points or "/" in etiquette:
        nom, etiquette = modele, "latest"
    return f"{nom}:opencode" if etiquette == "latest" else f"{nom}:{etiquette}-opencode"


def est_variante_opencode(nom):
    return nom.endswith(":opencode") or nom.endswith("-opencode")


def ollama_post(chemin, corps, timeout=30):
    requete = urllib.request.Request(URL_OLLAMA + chemin, data=json.dumps(corps).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(requete, timeout=timeout) as rep:
        return json.loads(rep.read().decode("utf-8") or "{}")


_variantes_pretes = {}   # modèle → le modèle à donner à OpenCode (vérifié une fois par lancement)


def modele_ollama_pour_opencode(modele):
    """Le modèle Ollama à donner à OpenCode.

    Avec la mémoire d'Ollama par défaut, les consignes d'OpenCode arrivent coupées pis le modèle
    se sert pas de ses outils. On fait donc une copie du modèle avec plus de mémoire : ça prend
    pas de place, c'est juste une fiche qui pointe sur le même modèle. Si ça marche pas (un vieil
    Ollama), on garde le modèle tel quel.
    """
    if est_variante_opencode(modele):
        return modele
    if modele not in _variantes_pretes:
        choisi = modele
        try:
            info = ollama_post("/api/show", {"model": modele}, timeout=10)
            memoire = re.search(r"^num_ctx\s+(\d+)", info.get("parameters") or "", re.M)
            if not (memoire and int(memoire.group(1)) >= CTX_OLLAMA_OPENCODE):
                variante = variante_opencode(modele)
                ollama_post("/api/create", {"model": variante, "from": modele, "stream": False,
                                            "parameters": {"num_ctx": CTX_OLLAMA_OPENCODE}},
                            timeout=120)
                choisi = variante
        except Exception:
            pass
        _variantes_pretes[modele] = choisi
    return _variantes_pretes[modele]


def config_opencode(type_moteur, modele):
    """La config d'OpenCode pour une demande, passée en mémoire (rien d'écrit sur le disque).

    Retourne (config, « fournisseur/modèle »).
    """
    if type_moteur == "claude":
        # OpenCode va lire ta clé dans le fichier protégé de Marceau : comme ça, elle traîne pas
        # dans l'environnement, où les commandes qu'il lance pourraient la voir.
        dans_fichier = FICHIER_CLE.exists() and FICHIER_CLE.read_text(encoding="utf-8").strip()
        cle = "{file:" + str(FICHIER_CLE) + "}" if dans_fichier else "{env:ANTHROPIC_API_KEY}"
        fournisseur = "anthropic"
        reglage = {"options": {"apiKey": cle},
                   "models": {modele: {"name": modele, "attachment": True}}}
    else:
        fournisseur = "ollama"
        reglage = {"npm": "@ai-sdk/openai-compatible", "name": "Ollama (sur ton ordi)",
                   "options": {"baseURL": URL_OLLAMA.rstrip("/") + "/v1"},
                   "models": {modele: {"name": modele, "tool_call": True}}}
    nom = f"{fournisseur}/{modele}"
    return {"provider": {fournisseur: reglage}, "model": nom, "share": "disabled",
            # Jamais en dehors du dossier que t'as choisi
            "permission": {"external_directory": "deny"}}, nom


def etape_opencode(partie, dossier):
    """Un outil qu'OpenCode vient d'utiliser, résumé en français : {outil, ligne, fichier, …}."""
    outil = partie.get("tool") or ""
    etat = partie.get("state") or {}
    entree = etat.get("input") or {}
    fichier = entree.get("filePath") or entree.get("path") or ""
    if fichier:
        try:
            fichier = Path(fichier).resolve().relative_to(Path(dossier).resolve()).as_posix()
        except (ValueError, OSError):
            pass
    commande = " ".join(str(entree.get("command") or "").split())
    if len(commande) > 70:
        commande = commande[:69] + "…"
    if outil == "read":
        ligne = f"lit {fichier}"
    elif outil == "write":
        ligne = f"écrit {fichier}"
    elif outil in ("edit", "multiedit", "patch", "apply_patch"):
        ligne = f"change {fichier}" if fichier else "change des fichiers"
    elif outil == "bash":
        ligne = f"lance : {commande}"
    elif outil in ("glob", "grep", "list", "ls", "codesearch"):
        ligne = "cherche " + (entree.get("pattern") or entree.get("query") or fichier or "dans tes fichiers")
    elif outil == "webfetch":
        ligne = "lit la page " + str(entree.get("url") or "")
    elif outil == "websearch":
        ligne = "cherche sur le web : " + str(entree.get("query") or "")
    elif outil in ("todowrite", "todoread"):
        ligne = "met son plan à jour"
    elif outil == "task":
        ligne = "confie une partie à un assistant : " + str(entree.get("description") or "")
    else:
        ligne = f"utilise l'outil {outil}"
    erreur = str(etat.get("error") or "") if etat.get("status") == "error" else ""
    refuse = bool(erreur) and any(m in erreur.lower() for m in ("rule", "rejected", "permission"))
    if erreur:
        ligne += " (refusé)" if refuse else " (erreur)"
    return {"outil": outil, "ligne": ligne, "fichier": fichier, "commande": commande,
            "refuse": refuse}


def lancer_opencode(programme, dossier, demande, type_moteur, modele, session=None, images=(),
                    progres=lambda ligne: None, garder=lambda processus: None,
                    arreter=lambda: False):
    """Fait faire une demande à OpenCode dans le dossier. Roule dans un fil à part.

    progres(ligne) est appelé à chaque étape (« lit app.py », « lance : npm test »…) ;
    garder(processus) reçoit le programme lancé, pour pouvoir l'arrêter.
    Retourne {"texte", "session", "etapes", "erreur", "code", "journal", "session_perdue"}.
    """
    resultat = {"texte": "", "session": session, "etapes": [], "erreur": None, "code": 0,
                "journal": "", "session_perdue": False}
    if type_moteur == "ollama":
        if not ollama_repond():   # sinon OpenCode réessaie longtemps avant d'abandonner
            resultat["erreur"] = {"name": "APIError", "data": {"message": "Cannot connect to Ollama"}}
            return resultat
        progres("prépare le modèle")
        modele = modele_ollama_pour_opencode(modele)
    if arreter():
        return resultat
    config, nom = config_opencode(type_moteur, modele)
    env = dict(os.environ, OPENCODE_CONFIG_CONTENT=json.dumps(config))
    commande = [programme, "run", "--format", "json", "--dir", str(dossier), "-m", nom,
                "--title", "Marceau : " + " ".join(demande.split())[:60]]
    if session:
        commande += ["--session", session]
    for image in images:
        commande += ["--file", str(image)]
    p = subprocess.Popen(commande, cwd=str(dossier), env=env, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         encoding="utf-8", errors="replace", start_new_session=True)
    garder(p)
    if arreter():   # « Arrêter » cliqué juste pendant le départ
        try:
            if hasattr(os, "killpg"):
                os.killpg(p.pid, signal.SIGTERM)
            else:
                p.terminate()
        except OSError:
            pass
    erreurs = []
    lecteur = threading.Thread(target=lambda: erreurs.append(p.stderr.read()), daemon=True)
    lecteur.start()
    try:
        # La demande passe par l'entrée du programme : les guillemets, les « - » pis les
        # retours de ligne arrivent tels quels.
        p.stdin.write(demande)
        p.stdin.close()
    except OSError:
        pass
    textes = []
    for ligne in p.stdout:
        try:
            evenement = json.loads(ligne)
        except ValueError:
            continue
        resultat["session"] = evenement.get("sessionID") or resultat["session"]
        sorte, partie = evenement.get("type"), evenement.get("part") or {}
        if sorte == "text" and (partie.get("text") or "").strip():
            textes.append(partie["text"].strip())
        elif sorte == "tool_use":
            etape = etape_opencode(partie, dossier)
            resultat["etapes"].append(etape)
            progres(etape["ligne"])
        elif sorte == "error":
            resultat["erreur"] = evenement.get("error") or {"name": "Erreur"}
    resultat["code"] = p.wait()
    lecteur.join(timeout=2)
    journal = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", "".join(erreurs)).strip()
    resultat["journal"] = journal[-1500:]
    resultat["texte"] = "\n\n".join(textes)
    resultat["session_perdue"] = bool(session and resultat["code"] and not textes
                                      and "session not found" in journal.lower())
    return resultat


def descendants(pid):
    """Les programmes lancés par pid, pis ceux qu'eux ont lancés (sur Linux, via /proc).

    OpenCode lance ses commandes dans leur propre groupe : arrêter OpenCode seul les laisserait
    rouler toutes seules.
    """
    enfants = {}
    try:
        numeros = [d for d in os.listdir("/proc") if d.isdigit()]
    except OSError:
        return []
    for d in numeros:
        try:
            with open(f"/proc/{d}/stat", "rb") as f:
                stat = f.read().decode("utf-8", "replace")
            parent = int(stat.rsplit(")", 1)[1].split()[1])   # « pid (nom) état parent … »
        except (OSError, ValueError, IndexError):
            continue
        enfants.setdefault(parent, []).append(int(d))
    trouves, a_voir = [], [pid]
    while a_voir:
        for enfant in enfants.get(a_voir.pop(), []):
            trouves.append(enfant)
            a_voir.append(enfant)
    return trouves


def message_opencode(erreur, type_moteur, modele):
    """Traduit une erreur d'OpenCode en français clair."""
    donnees = erreur.get("data") or {}
    texte = str(donnees.get("message") or erreur.get("name") or "")
    bas = texte.lower()
    statut = donnees.get("statusCode")
    if statut in (401, 403) or "api key" in bas or "x-api-key" in bas or "authentication" in bas:
        return ("Ta clé API Claude est refusée. Vérifie-la dans Paramètres (menu ☰), "
                "pis renvoie ta demande.")
    if "connect" in bas or "econnrefused" in bas or "fetch failed" in bas:
        if type_moteur == "ollama":
            return "OpenCode trouve pas Ollama sur ton ordi.\n\n" + MESSAGE_OLLAMA
        return "OpenCode arrive pas à joindre Claude. Vérifie ton Internet, pis réessaie."
    if statut == 429 or "rate limit" in bas:
        return "Trop de demandes d'un coup pour ta clé. Attends une minute, pis réessaie."
    if "credit" in bas or "billing" in bas:
        return "Ton compte Claude a plus de crédit. Ajoutes-en sur console.anthropic.com."
    if statut in (500, 502, 503, 529) or "overloaded" in bas:
        return "L'IA est débordée en ce moment. Réessaie dans une minute."
    return (f"OpenCode a eu un problème avec {modele} : {texte or 'erreur inconnue'}. "
            "Si ça recommence, essaie une autre IA dans le menu en bas.")


def fichiers_du_dossier(dossier):
    """Chaque fichier du dossier (chemin relatif, chemin complet), sans les dossiers lourds
    que personne touche à la main (.git, node_modules…)."""
    for racine, sous, fichiers in os.walk(dossier):
        sous[:] = sorted(d for d in sous if d not in DOSSIERS_IGNORES)
        for nom in sorted(fichiers):
            chemin = Path(racine) / nom
            yield chemin.relative_to(dossier).as_posix(), chemin


def arbre_local(dossier, maximum=20_000):
    """La liste des fichiers d'un dossier de ton ordi, pareille à celle d'un projet GitHub."""
    arbre = {}
    for relatif, chemin in fichiers_du_dossier(dossier):
        try:
            if chemin.is_symlink() or not chemin.is_file():
                continue
            arbre[relatif] = {"sha": None, "taille": chemin.stat().st_size}
        except OSError:
            continue
        if len(arbre) >= maximum:
            break
    return arbre


def photo_dossier(dossier):
    """Ce qu'il y a dans les fichiers texte du dossier, pour voir après ce qu'OpenCode a changé.

    Retourne (photo, complète?) : un dossier géant est photographié en partie seulement.
    """
    photo = {}
    for relatif, chemin in fichiers_du_dossier(dossier):
        try:
            if chemin.is_symlink() or not chemin.is_file() or \
                    chemin.stat().st_size > PHOTO_TAILLE_MAX:
                continue
            octets = chemin.read_bytes()
        except OSError:
            continue
        if b"\0" in octets[:8192]:
            continue                   # un fichier binaire (image, programme…)
        try:
            photo[relatif] = octets.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if len(photo) >= PHOTO_FICHIERS_MAX:
            return photo, False
    return photo, True


def changements_dossier(avant, apres, complete=True):
    """Ce qui a changé entre deux photos : [(chemin, avant, après, nouveau?, supprimé?)]."""
    liste = []
    for chemin in sorted(set(avant) | set(apres)):
        a, b = avant.get(chemin), apres.get(chemin)
        if a == b or (not complete and (a is None or b is None)):
            continue       # dossier géant : un fichier hors de la photo, c'est pas un changement
        liste.append((chemin, a or "", b or "", a is None, b is None))
    return liste


def remettre_comme_avant(dossier, liste):
    """Défait des changements. Un fichier retouché depuis est laissé tel quel, par prudence.

    Retourne (remis, laissés).
    """
    remis, laisses = [], []
    for chemin, avant, apres, nouveau, supprime in liste:
        cible = Path(dossier) / chemin
        try:
            actuel = cible.read_bytes().decode("utf-8") if cible.is_file() else None
            if actuel != (None if supprime else apres):
                laisses.append(chemin)
                continue
            if nouveau:
                cible.unlink()
            else:
                cible.parent.mkdir(parents=True, exist_ok=True)
                cible.write_bytes(avant.encode("utf-8"))
            remis.append(chemin)
        except (OSError, UnicodeDecodeError):
            laisses.append(chemin)
    return remis, laisses


# ---------- Le Codex : fichiers GitHub à gauche, éditeur au centre, assistant à droite ----------
class CodexVue(tk.Frame):
    """Le Codex : un seul écran, centré. Tu écris en bas, les fichiers touchés
    arrivent en cartes qu'un clic déplie pour montrer ce qui a changé."""

    def __init__(self, app):
        super().__init__(app, bg=GRIS_FOND)
        self.app = app
        self.token = lire_secret(FICHIER_TOKEN, "GITHUB_TOKEN")
        self.depot = None            # « propriétaire/projet »
        self.branche = None
        self.arbre = {}              # chemin -> {"sha": …, "taille": …}
        self.cache = {}              # chemin -> contenu déjà lu sur GitHub
        self.avant = {}              # chemin -> contenu d'avant, pour montrer les changements
        self.depots = []
        self.onglets = []
        self.actif = None
        self.messages = []           # conversation avec l'assistant Codex
        self.occupe = False
        self.nb_liens = 0
        self.pieces = []             # images jointes à la prochaine demande
        self.dossier = None          # un dossier de ton ordi (OpenCode) au lieu d'un projet GitHub
        self.oc_session = None       # la conversation d'OpenCode dans ce dossier
        self.oc_processus = None     # OpenCode en train de travailler (pour pouvoir l'arrêter)
        self.oc_en_cours = False
        self.oc_arrete = False
        self.oc_note = ""            # un mot à glisser à OpenCode dans ta prochaine demande

        self.construire_barre()
        self.etat_label = tk.Label(self, text="", anchor="w", bg=GRIS_MENU, fg=NOIR,
                                   font=(FAMILLE, 10), padx=14, pady=5)
        self.etat_label.pack(side="bottom", fill="x")
        self.construire_saisie()
        self.zone_bas.pack(side="bottom", fill="x")
        self.construire_conversation()
        self.construire_editeur()
        if self.token:
            self.etat("Choisis un projet en haut (GitHub, ou un dossier de ton ordi avec OpenCode), "
                      "pis dis-moi quoi changer.")
        else:
            self.etat("Choisis un dossier de ton ordi dans « Projet ▾ » (OpenCode travaille dedans), "
                      "ou ajoute ton token GitHub dans Paramètres (menu ☰) pour tes projets GitHub.")

    # ----- Construction -----
    def construire_barre(self):
        barre = tk.Frame(self, bg=GRIS_FOND, height=64)
        barre.pack(side="top", fill="x")
        barre.pack_propagate(False)
        tk.Label(barre, text="Codex", bg=GRIS_FOND, fg=NOIR,
                 font=(FAMILLE, 16, "bold")).pack(side="left", padx=(74, 16))
        self.bouton_projet = bouton_orange(barre, "Projet  ▾", self.menu_projets)
        self.bouton_projet.pack(side="left", pady=13)
        bouton_orange(barre, "Fichiers", self.ouvrir_liste_fichiers).pack(side="left", padx=(10, 0), pady=13)
        self.bouton_enregistrer = bouton_orange(barre, "Enregistrer", self.enregistrer_tout)
        self.bouton_enregistrer.pack(side="left", padx=(10, 0), pady=13)
        self.auto_push = tk.BooleanVar(value=pousser_auto())
        tk.Checkbutton(barre, text="Pousser tout seul", variable=self.auto_push,
                       command=self.changer_auto_push, bg=GRIS_FOND, fg=NOIR,
                       activebackground=GRIS_FOND, activeforeground=NOIR, selectcolor=GRIS_ZONE,
                       font=(FAMILLE, 9), relief="flat", bd=0, highlightthickness=0,
                       cursor="hand2").pack(side="left", padx=(12, 0), pady=13)
        bouton_orange(barre, "Fermer", self.app.fermer_codex).pack(side="right", padx=(10, 18), pady=13)

    def construire_conversation(self):
        """L'écran du milieu : une seule colonne, centrée, où tout se passe."""
        zone = self.zone_chat = tk.Frame(self, bg=GRIS_FOND)
        zone.pack(fill="both", expand=True)
        centre = tk.Frame(zone, bg=GRIS_FOND)
        centre.place(relx=0.5, rely=0, anchor="n", relwidth=LARGEUR, relheight=1)
        defil = barre_defilement(centre, "vertical", GRIS_FOND)
        self.chat = tk.Text(centre, width=1, yscrollcommand=defil.set, **style_zone(12))
        defil.config(command=self.chat.yview)
        defil.pack(side="right", fill="y", pady=(8, 10))
        self.chat.pack(side="left", fill="both", expand=True, pady=(8, 10))
        # Le retrait laisse la place au petit logo Marceau devant chaque réponse
        self.app.configurer_tags(self.chat, 12, retrait=LOGO_AVATAR + 12 if self.app.logo else 0,
                                 taille_reponse=14)
        self.mot_accueil()

    def mot_accueil(self):
        """Le début d'une session : le logo Marceau au milieu de l'écran, le mot d'accueil dessous.

        C'est posé par-dessus la conversation, pis ça s'efface à ta première demande.
        """
        # Même fond que la zone de conversation : sinon le cadre ferait une boîte grise
        self.accueil = tk.Frame(self.zone_chat, bg=GRIS_ZONE)
        self.accueil.place(relx=0.5, rely=0.44, anchor="center")
        logo = getattr(self.app, "logo", None)
        if logo is not None:
            tk.Label(self.accueil, image=logo.image(LOGO_CENTRE), bg=GRIS_ZONE, bd=0,
                     highlightthickness=0).pack()
        tk.Label(self.accueil,
                 text="Dis-moi ce que tu veux changer dans ton projet. Pas besoin d'ouvrir les "
                      "fichiers : j'trouve les bons tout seul, j'les lis pis j'les corrige. "
                      "Tu vas voir chaque fichier touché icitte, avec ce qui a changé dedans.",
                 bg=GRIS_ZONE, fg=NOIR, font=(FAMILLE, 13, "italic"), justify="center",
                 wraplength=520).pack(pady=(18, 0))
        self.accueil.lift()

    def effacer_accueil(self):
        """Le logo d'accueil s'en va dès que la conversation commence."""
        if getattr(self, "accueil", None) is not None:
            self.accueil.destroy()
            self.accueil = None

    def construire_saisie(self):
        """La boîte où tu écris, en bas au centre, comme dans le chat."""
        zone = self.zone_bas = tk.Frame(self, bg=GRIS_FOND, height=118)
        zone.pack_propagate(False)
        centre = tk.Frame(zone, bg=GRIS_FOND)
        centre.place(relx=0.5, rely=0.5, anchor="center", relwidth=LARGEUR)
        ligne = tk.Frame(centre, bg=GRIS_FOND)
        ligne.pack(fill="x")
        self.bouton_envoyer = bouton_orange(ligne, "Envoyer", self.clic_envoyer)
        self.bouton_envoyer.pack(side="right", padx=(10, 0), fill="y")
        self.saisie = tk.Text(ligne, height=2, width=1, **style_zone())
        self.saisie.pack(side="left", fill="x", expand=True)
        options = tk.Frame(centre, bg=GRIS_FOND)
        options.pack(fill="x", pady=(8, 0))
        self.app.creer_bouton_moteur(options).pack(side="left")
        self.app.bouton_image(options, self.joindre_images).pack(side="left", padx=(8, 0))
        self.app.creer_bouton_voix(options).pack(side="left", padx=(8, 0))
        self.cadre_pieces = tk.Frame(options, bg=GRIS_FOND)
        self.cadre_pieces.pack(side="left")
        self.saisie.bind("<Return>", self.envoyer)
        self.saisie.bind("<Shift-Return>", lambda e: (self.saisie.insert("insert", "\n"), "break")[1])

    def construire_editeur(self):
        """L'éditeur : caché, il vient par-dessus quand tu cliques « Modifier »."""
        e = self.editeur = tk.Frame(self, bg=CODE_FOND)
        haut = tk.Frame(e, bg=GRIS_FOND, height=44)
        haut.pack(fill="x")
        haut.pack_propagate(False)
        # padx=74 à gauche : la place du bouton ☰, qui passe par-dessus tout
        bouton_orange(haut, "‹ Retour", self.fermer_editeur, taille=9).pack(
            side="left", padx=(74, 12), pady=8)
        tk.Label(haut, text="Éditeur", bg=GRIS_FOND, fg=NOIR,
                 font=(FAMILLE, 11, "bold")).pack(side="left")
        bouton_orange(haut, "+ Fichier", self.nouveau_fichier, taille=9).pack(side="right", padx=12, pady=8)
        bouton_orange(haut, "+ Image", self.image_vers_projet, taille=9).pack(side="right", pady=8)
        self.barre_onglets = tk.Frame(e, bg=GRIS_FOND, height=38)
        self.barre_onglets.pack(fill="x")
        self.barre_onglets.pack_propagate(False)
        self.zone_editeur = tk.Frame(e, bg=CODE_FOND)
        self.zone_editeur.pack(fill="both", expand=True)
        self.vide_editeur = tk.Label(self.zone_editeur, bg=CODE_FOND, fg="#8a8a8a",
                                     text="Aucun fichier ouvert.", font=(FAMILLE, 13))
        self.vide_editeur.place(relx=0.5, rely=0.45, anchor="center")

    def ouvrir_editeur(self):
        self.editeur.place(x=0, y=0, relwidth=1, relheight=1)
        self.editeur.lift()
        self.app.bouton_menu.lift()

    def fermer_editeur(self):
        self.editeur.place_forget()
        self.saisie.focus_set()

    def editeur_visible(self):
        return bool(self.editeur.winfo_manager())

    # ----- La liste des fichiers du projet (une fenêtre, pas un panneau) -----
    def ouvrir_liste_fichiers(self):
        if not self.arbre:
            self.etat("Ouvre d'abord un projet avec le bouton Projet.")
            return
        fen = tk.Toplevel(self, bg=GRIS_MENU)
        fen.title("Fichiers du projet")
        fen.geometry("560x520")
        fen.transient(self.winfo_toplevel())
        cadre = tk.Frame(fen, bg=GRIS_MENU)
        cadre.pack(fill="both", expand=True, padx=14, pady=14)
        champ = tk.Entry(cadre, bg=GRIS_ZONE, fg=NOIR, insertbackground=NOIR, relief="flat", bd=0,
                         font=(FAMILLE, 11), highlightthickness=2,
                         highlightbackground=GRIS_BORD, highlightcolor=ORANGE)
        champ.pack(fill="x", ipady=5)
        champ.focus_set()
        zone = tk.Frame(cadre, bg=GRIS_MENU)
        zone.pack(fill="both", expand=True, pady=(10, 0))
        liste = tk.Listbox(zone, bg=GRIS_MENU, fg=NOIR, selectbackground=ORANGE,
                           selectforeground=NOIR, font=(FAMILLE_CODE, 10), relief="flat", bd=0,
                           highlightthickness=0, activestyle="none")
        defil = barre_defilement(zone, "vertical", command=liste.yview)
        liste.config(yscrollcommand=defil.set)
        defil.pack(side="right", fill="y")
        liste.pack(side="left", fill="both", expand=True)
        chemins = []

        def remplir(*_):
            mot = champ.get().strip().lower()
            chemins.clear()
            chemins.extend(c for c in sorted(self.arbre) if mot in c.lower())
            liste.delete(0, "end")
            for c in chemins[:800]:
                liste.insert("end", "  " + c)

        def choisir(*_):
            choix = liste.curselection()
            if not choix:
                return
            fen.destroy()
            self.ouvrir_fichier(chemins[choix[0]])

        champ.bind("<KeyRelease>", remplir)
        champ.bind("<Return>", lambda e: (liste.selection_set(0), choisir()))
        liste.bind("<Double-Button-1>", choisir)
        liste.bind("<Return>", choisir)
        fen.bind("<Escape>", lambda e: fen.destroy())
        remplir()

    def etat(self, message):
        self.etat_label.config(text=message)

    def changer_auto_push(self):
        """Quand c'est coché, le Codex envoie ses changements sur GitHub sans rien demander."""
        actif = self.auto_push.get()
        regler_pousser_auto(actif)
        self.etat("Le Codex va pousser ses changements sur GitHub tout seul." if actif else
                  "Le Codex écrit dans les onglets; c'est toi qui cliques Enregistrer.")

    # ----- Panneaux qui s'ouvrent et se ferment -----
    def nouveau_token(self, token):
        """Appelé par Paramètres quand le token change."""
        self.token = token
        self.depots = []
        self.etat("Token enregistré. Choisis un projet en haut." if token else
                  "Plus de token GitHub. Ajoutes-en un dans Paramètres pour ouvrir tes projets.")

    def menu_projets(self):
        if self.token and not self.depots:
            self.etat("Chargement de tes projets GitHub…")
            token = self.token
            self.app.en_arriere_plan(
                lambda: github("GET", "/user/repos?per_page=100&sort=updated", token),
                self.depots_recus)
            return
        self.afficher_menu_projets()

    def depots_recus(self, depots, err):
        if err:
            self.etat(erreur_github(err))
        else:
            self.depots = depots or []
            self.etat(f"{len(self.depots)} projets trouvés." if self.depots else
                      "Aucun projet trouvé avec ce token.")
        self.afficher_menu_projets()   # le dossier de ton ordi reste offert, même si GitHub bloque

    def afficher_menu_projets(self):
        menu = tk.Menu(self, tearoff=0, bg=GRIS_ZONE, fg=NOIR, activebackground=ORANGE,
                       activeforeground=NOIR, font=(FAMILLE, 11), bd=0, relief="flat")
        menu.add_command(label="Un dossier sur mon ordi (avec OpenCode)…", command=self.choisir_dossier)
        menu.add_separator()
        if not self.token:
            menu.add_command(label="Brancher mes projets GitHub (Paramètres)…",
                             command=lambda: self.app.ouvrir_parametres("github"))
        for d in self.depots[:40]:
            menu.add_command(label=d["full_name"], command=lambda d=d: self.ouvrir_depot(
                d["full_name"], d.get("default_branch") or "main"))
        if self.token:
            menu.add_separator()
            menu.add_command(label="Recharger la liste", command=self.recharger_depots)
        self.menu_projet = menu        # gardé pour les essais
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
        self.vider_onglets()
        self.depot, self.branche, self.arbre, self.cache = nom, branche, arbre, {}
        self.avant = {}
        self.dossier, self.oc_session, self.oc_note = None, None, ""
        self.bouton_projet.config(text=f"{nom.split('/')[-1][:22]}  ▾")
        self.etat(f"{nom} ({branche}) : {len(arbre)} fichiers."
                  + (" Liste incomplète (projet très gros)." if tronque else "")
                  + " Demande à l'assistant ce que tu veux changer : il trouve les fichiers tout seul.")

    # ----- Onglets -----
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
        if self.dossier is not None:
            self.ouvrir_fichier_local(chemin)
            return
        if chemin in self.cache:
            self.activer(self.creer_onglet(chemin, self.cache[chemin], info["sha"]))
            return
        self.etat(f"Ouverture de {chemin}…")
        depot, token, sha = self.depot, self.token, info["sha"]
        if Path(chemin).suffix.lower() in EXT_IMAGES and Image is not None:
            def image_recue(octets, err):
                if err:
                    self.etat(erreur_github(err))
                elif depot == self.depot:
                    self.ajouter_image_octets(chemin, octets, sha=sha, modifie=False)
            self.app.en_arriere_plan(lambda: lire_blob_octets(depot, sha, token), image_recue)
            return
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

    def activer(self, onglet, montrer=True):
        """Rend l'onglet actif. montrer=True fait apparaître l'éditeur par-dessus l'écran."""
        self.actif = onglet
        onglet.cadre.tkraise()
        self.vide_editeur.place_forget()
        self.dessiner_onglets()
        onglet.planifier()
        if montrer:
            self.ouvrir_editeur()
            onglet.texte.focus_set()
        if self.dossier is not None:
            self.etat(str(self.dossier / onglet.chemin) + ("   (pas enregistré)" if onglet.modifie else ""))
        else:
            self.etat(onglet.chemin + ("" if onglet.sha else "   (pas encore sur GitHub)"))

    def activer_chemin(self, chemin):
        o = self.trouver_onglet(chemin)
        if o:
            self.activer(o)

    def dessiner_onglets(self):
        n = sum(1 for o in self.onglets if o.modifie)
        self.bouton_enregistrer.config(text=f"Enregistrer ({n})" if n else "Enregistrer")
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
        if self.dossier is not None:   # un dossier de ton ordi : on écrit directement dedans
            self.enregistrer_local(onglets)
            return
        if not self.depot:   # pas de projet GitHub ouvert : on sauvegarde sur l'ordi
            for o in onglets:
                chemin = filedialog.asksaveasfilename(title="Enregistrer sur l'ordi",
                                                      initialfile=Path(o.chemin).name, parent=self)
                if chemin:
                    if o.est_image:
                        Path(chemin).write_bytes(o.octets)
                    else:
                        Path(chemin).write_text(o.contenu(), encoding="utf-8")
                    o.set_modifie(False)
            return
        envois = [(o, o.chemin, o.octets if o.est_image else o.contenu(), o.sha) for o in onglets]
        depot, branche, token = self.depot, self.branche, self.token
        self.etat(f"Envoi sur GitHub de {len(envois)} fichier(s)…")

        def travail():
            resultats = []
            for o, chemin, contenu, sha in envois:
                octets = contenu if isinstance(contenu, bytes) else contenu.encode("utf-8")
                corps = {"message": f"Codex : {'mise à jour' if sha else 'création'} de {chemin}",
                         "content": base64.b64encode(octets).decode("ascii"),
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
            image = isinstance(contenu, bytes)
            if depot == self.depot:
                self.arbre[chemin] = {"sha": sha,
                                      "taille": len(contenu if image else contenu.encode("utf-8"))}
                if not image:
                    self.cache[chemin] = contenu
            o.sha = sha
            if image or o.contenu() == contenu:   # pas retouché pendant l'envoi
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
        """Change le texte à côté des points, sans arrêter leur saut."""
        zone = self.chat.tag_ranges("attente_texte")
        if zone:
            self.chat.delete(zone[0], zone[1])
            self.chat.insert(zone[0], message + " ", ("attente", "attente_codex", "attente_texte"))
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
        if self.dossier is not None and not trouver_opencode():
            self.montrer_manque_opencode()
            return "break"
        self.saisie.delete("1.0", "end")
        if not self.messages:
            self.effacer_accueil()           # le logo d'accueil s'en va
            self.chat.delete("1.0", "end")
        self.chat.insert("end", question + "\n", "question")
        self.messages.append({"role": "user", "content": question})
        if self.dossier is not None:
            self.envoyer_opencode(question, moteur)
            return "break"
        historique = [dict(m) for m in self.messages[-8:]]
        while historique and historique[0]["role"] != "user":
            historique.pop(0)
        budget = CONTEXTE_CLAUDE if type_moteur == "claude" else CONTEXTE_OLLAMA
        # Une photo de ce qu'on a déjà (le fil à part touche pas à l'interface)
        ordre = ([self.actif] if self.actif else []) + [o for o in self.onglets if o is not self.actif]
        onglets = [(o.chemin, o.contenu()) for o in ordre if not o.est_image]
        pieces, self.pieces = self.pieces, []
        self.app.dessiner_pieces(self.cadre_pieces, self.pieces, self.retirer_piece)
        if pieces:   # l'IA sait quel numéro va avec quelle image
            self.app.montrer_vignettes(self.chat, pieces, 90)
        depot, branche, token = self.depot, self.branche, self.token
        arbre, cache = dict(self.arbre), dict(self.cache)
        self.app.voix.taire()           # on arrête de lire l'ancienne réponse
        self.app.avatar(self.chat)      # le logo Marceau devant la réponse qui s'en vient
        self.points = ajouter_ligne_attente(self.chat, f"Codex ({nom_court(moteur)}) regarde ton projet",
                                            14, ("attente", "attente_codex"))
        self.occupe = True

        def ia(messages, systeme, max_tokens):
            if type_moteur == "claude":
                return appeler_claude(cle, messages, systeme, web=False, max_tokens=max_tokens,
                                      timeout=600, modele=modele)[0]
            return appeler_ollama(modele, messages, systeme, num_ctx=CTX_OLLAMA_CODEX)[0]

        def progres(message):
            self.app.depuis_fil(lambda: self.maj_attente(message))

        voit = type_moteur == "claude" or modele_voit_images(modele)
        images = [image_pour_ia(p["image"]) for p in pieces] if voit else []
        demande = question
        if pieces:
            demande += "\n(Images jointes : " + ", ".join(
                f"{i} = {p['nom']}" for i, p in enumerate(pieces, 1)) + ")"
            if not voit:
                demande += ("\n(Tu peux pas les voir, ce modèle-là, mais tu peux quand même les "
                            "mettre dans le projet avec [IMAGE n chemin].)")
        self.app.en_arriere_plan(
            lambda: agent_codex(demande, historique, onglets, cache, arbre, depot, branche,
                                token, budget, ia, progres, images),
            lambda r, err: self.reponse(r, err, type_moteur, modele, depot, pieces))
        return "break"

    def reponse(self, resultat, err, type_moteur, modele, depot, pieces=()):
        enlever_ligne_attente(self.chat, "attente_codex", getattr(self, "points", None))
        self.points = None
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
        images_ajoutees = []
        for numero, chemin in re.findall(r"\[IMAGE\s+(\d+)\s*[:\-]?\s*([^\]\n]+)\]",
                                         resultat["texte"] or "", re.I):
            numero, chemin = int(numero), chemin.strip().strip("`\"' ").lstrip("/")
            if 1 <= numero <= len(pieces) and chemin:
                piece = pieces[numero - 1]
                self.ajouter_image(chemin, piece["image"], piece.get("original"))
                images_ajoutees.append((chemin, piece))
        explication, fichiers = extraire_fichiers(resultat["texte"] or "")
        ecrits = []   # (chemin, avant, apres, nouveau fichier?)
        for chemin, contenu in fichiers:
            propre = chemin.removeprefix("./").lstrip("/")
            nouveau = propre not in self.arbre
            # La version d'avant : ce qu'il y a dans l'onglet ouvert, sinon ce qu'on a lu
            # sur GitHub. Il faut la prendre AVANT d'écrire par-dessus.
            onglet = self.trouver_onglet(propre)
            avant = onglet.contenu() if onglet else self.cache.get(propre, "")
            ecrits.append((self.appliquer_fichier(chemin, contenu), avant, contenu, nouveau))
        resume = explication or ("C'est fait, regarde les fichiers." if ecrits or images_ajoutees else
                                 "Pas de réponse cette fois-ci. Reformule ta demande.")
        tous = [c for c, _, _, _ in ecrits] + [c for c, _ in images_ajoutees]
        note = f"\n(Fichiers écrits : {', '.join(tous)})" if tous else ""
        self.messages.append({"role": "assistant", "content": resume + note})
        def fini():
            self.fin_reponse(ecrits, resultat["vus"], images_ajoutees)
            # L'explication, pas le code (ça, ça se lit mal). Un avertissement va dans le Codex,
            # pas dans le chat caché en dessous.
            self.app.dire_a_voix_haute(resume, self.chat)

        self.app.ecrire(self.chat, resume, lambda: True, fini)

    def appliquer_fichier(self, chemin, contenu):
        """Met le fichier écrit par l'IA dans un onglet (rien part sur GitHub avant « Enregistrer »)."""
        if chemin.startswith("./"):
            chemin = chemin[2:]
        chemin = chemin.lstrip("/")
        o = self.trouver_onglet(chemin)
        if o is not None and o.est_image:
            self.onglets.remove(o)
            o.cadre.destroy()
            o = None
        # L'éditeur ouvert : on voit le code s'écrire. Fermé : instantané, ça sert à rien d'attendre.
        visible = self.editeur_visible()
        if o is None:
            o = self.creer_onglet(chemin, "" if visible else contenu,
                                  self.arbre.get(chemin, {}).get("sha"))
        elif not visible:
            o.remplacer(contenu)
        o.set_modifie(True)
        self.activer(o, montrer=False)
        if visible:
            o.ecrire_code(contenu)
        return chemin

    # ----- Les images -----
    def joindre_images(self):
        """Le trombone : tu choisis des images à envoyer avec ta demande."""
        self.pieces += self.app.choisir_images(self)
        self.pieces = self.pieces[:4]
        self.app.dessiner_pieces(self.cadre_pieces, self.pieces, self.retirer_piece)
        self.saisie.focus_set()

    def retirer_piece(self, i):
        del self.pieces[i]
        self.app.dessiner_pieces(self.cadre_pieces, self.pieces, self.retirer_piece)

    def image_vers_projet(self):
        """« + Image » : prend une image de ton ordi pour l'ajouter au projet."""
        if Image is None:
            messagebox.showinfo("Images", MESSAGE_PILLOW, parent=self)
            return
        fichier = filedialog.askopenfilename(title="Image à ajouter au projet", filetypes=TYPES_IMAGES,
                                             parent=self)
        if not fichier:
            return
        chemin = simpledialog.askstring("Image dans le projet", "Chemin de l'image dans le projet :",
                                        initialvalue=f"images/{Path(fichier).name}", parent=self)
        if chemin and chemin.strip():
            self.ajouter_image(chemin.strip().lstrip("/"), ouvrir_image(fichier), fichier)

    def ajouter_image(self, chemin, image, original=None, montrer=False):
        """Prépare une image pour le projet (elle part sur GitHub avec « Enregistrer »)."""
        if not Path(chemin).suffix:
            chemin += ".png"
        if original and Path(original).suffix.lower() == Path(chemin).suffix.lower():
            octets = Path(original).read_bytes()   # même format : on garde le fichier tel quel
        else:
            octets = octets_pour(chemin, image)
        self.ajouter_image_octets(chemin, octets, sha=self.arbre.get(chemin, {}).get("sha"),
                                  montrer=montrer)

    def ajouter_image_octets(self, chemin, octets, sha=None, modifie=True, montrer=True):
        vieux = self.trouver_onglet(chemin)
        if vieux is not None:
            self.onglets.remove(vieux)
            vieux.cadre.destroy()
        onglet = OngletImage(self, chemin, octets, sha)
        self.onglets.append(onglet)
        onglet.set_modifie(modifie)
        self.activer(onglet, montrer=montrer)
        if modifie:
            self.etat(f"Image prête : {chemin}. Clique « Enregistrer » pour l'envoyer sur GitHub.")

    def fin_reponse(self, ecrits=(), vus=(), images_ajoutees=()):
        if vus:
            noms = ", ".join(Path(c).name for c in vus[:8]) + (f" (+{len(vus) - 8})" if len(vus) > 8 else "")
            self.chat.insert("end", f"Fichiers lus : {noms}\n", "sources")
        chemins = [c for c, _, _, _ in ecrits] + [c for c, _ in images_ajoutees]
        # Si t'as coché « Pousser tout seul », ça part sur GitHub sans rien demander.
        if chemins and self.depot and self.auto_push.get():
            self.cartes(ecrits)
            self.vignettes_ajoutees(images_ajoutees)
            self.chat.insert("end", "J'envoie ça sur GitHub…\n", "sources")
            self.chat.see("end")
            self.enregistrer([o for o in self.onglets if o.chemin in set(chemins)])
            self.occupe = False
            return
        self.cartes(ecrits)
        self.vignettes_ajoutees(images_ajoutees)
        if ecrits or images_ajoutees:
            self.chat.insert("end", "Clique un fichier pour voir ce qui a changé. "
                             + ("Quand c'est correct, clique « Enregistrer ».\n" if self.depot else
                                "Clique « Enregistrer » pour les sauvegarder sur ton ordi.\n"),
                             "sources")
        self.chat.see("end")
        self.occupe = False

    def vignettes_ajoutees(self, images_ajoutees):
        """Chaque image mise dans le projet s'affiche en petit, pis son nom s'ouvre d'un clic."""
        for chemin, piece in images_ajoutees:
            etiquette = f"image{self.nb_liens}"
            self.nb_liens += 1
            self.app.montrer_vignettes(self.chat, [piece], 70)
            self.chat.insert("end", "Image ajoutée : ", "sources")
            self.chat.insert("end", chemin + "\n", ("sources", "lien", etiquette))
            self.chat.tag_bind(etiquette, "<Button-1>", lambda e, c=chemin: self.activer_chemin(c))

    def cartes(self, ecrits):
        """Ajoute une carte par fichier touché, fermée, dans la conversation."""
        self.chat.update_idletasks()
        largeur = max(self.chat.winfo_width() - 34, 320)
        for chemin, avant, apres, nouveau in ecrits:
            carte = CarteFichier(self.chat, self.app, chemin, avant, apres, nouveau, largeur,
                                 self.activer_chemin)
            self.chat.window_create("end", window=carte, pady=5)
            self.chat.insert("end", "\n")

    # ----- OpenCode : il travaille dans un dossier de ton ordi -----
    def clic_envoyer(self):
        """Le bouton sous la boîte : « Envoyer », ou « Arrêter » pendant qu'OpenCode travaille."""
        if self.oc_en_cours:
            self.arreter_opencode()
        else:
            self.envoyer()

    def arreter_opencode(self):
        """Arrête OpenCode, pis les commandes qu'il a lancées. Ce qu'il a déjà changé reste montré."""
        if not self.oc_en_cours:
            return
        self.oc_arrete = True
        self.maj_attente("J'arrête OpenCode")
        p = self.oc_processus
        if p is None or p.poll() is not None:
            return
        # La liste AVANT d'arrêter OpenCode : après, ses commandes auraient plus de parent
        lances = descendants(p.pid)

        def tuer(sorte):
            for pid in lances:
                try:
                    os.kill(pid, sorte)
                except OSError:
                    pass       # déjà fini
            if p.poll() is None:
                try:
                    if hasattr(os, "killpg"):
                        os.killpg(p.pid, sorte)   # OpenCode pis son groupe
                    else:
                        p.kill()
                except OSError:
                    pass

        tuer(signal.SIGTERM)
        self.after(3000, lambda: tuer(getattr(signal, "SIGKILL", signal.SIGTERM)))

    def choisir_dossier(self):
        """« Un dossier sur mon ordi » : OpenCode va travailler dedans."""
        if not trouver_opencode():
            self.montrer_manque_opencode()
            return
        dossier = filedialog.askdirectory(title="Le dossier où OpenCode va travailler",
                                          mustexist=True, parent=self)
        if dossier:
            self.ouvrir_dossier(dossier)

    def montrer_manque_opencode(self):
        """OpenCode est pas installé : on explique quoi faire, avec la commande à copier."""
        fen = tk.Toplevel(self, bg=GRIS_MENU)
        fen.title("Installer OpenCode")
        fen.transient(self.winfo_toplevel())
        fen.resizable(False, False)
        cadre = tk.Frame(fen, bg=GRIS_MENU)
        cadre.pack(padx=24, pady=20)
        style = dict(bg=GRIS_MENU, fg=NOIR, font=(FAMILLE, 11), justify="left", wraplength=470)
        tk.Label(cadre, text="OpenCode n'est pas installé sur ton ordi.", bg=GRIS_MENU, fg=NOIR,
                 font=(FAMILLE, 13, "bold")).pack(anchor="w")
        tk.Label(cadre, text="OpenCode, c'est un agent de code gratuit pis open source : il travaille "
                             "directement dans un dossier de ton ordi (il lit tes fichiers, les change "
                             "pis lance des commandes).\n\nPour l'installer, copie-colle ça dans un "
                             "terminal :", **style).pack(anchor="w", pady=(10, 6))
        champ = tk.Entry(cadre, font=(FAMILLE_CODE, 11), bg=GRIS_ZONE, fg=NOIR, relief="flat", bd=0,
                         readonlybackground=GRIS_ZONE, highlightthickness=0, width=46)
        champ.insert(0, COMMANDE_OPENCODE)
        champ.config(state="readonly")
        champ.pack(fill="x", ipady=6)
        tk.Label(cadre, text="Ensuite, reviens ici pis choisis ton dossier dans « Projet ▾ ». Pas "
                             "besoin de le configurer : Marceau lui passe l'IA que t'as choisie en bas.",
                 **style).pack(anchor="w", pady=(10, 0))
        boutons = tk.Frame(cadre, bg=GRIS_MENU)
        boutons.pack(fill="x", pady=(16, 0))

        def copier():
            self.clipboard_clear()
            self.clipboard_append(COMMANDE_OPENCODE)
            copie.config(text="Copié!")

        copie = bouton_orange(boutons, "Copier la commande", copier, taille=10)
        copie.pack(side="left")
        bouton_orange(boutons, "Fermer", fen.destroy, taille=10).pack(side="right")
        fen.bind("<Escape>", lambda e: fen.destroy())
        self.fenetre_opencode = fen
        self.etat("OpenCode est pas installé : la marche à suivre est dans la petite fenêtre.")

    def ouvrir_dossier(self, dossier):
        """Ouvre un dossier de ton ordi : c'est OpenCode qui va travailler dedans."""
        dossier = Path(dossier).expanduser().resolve()
        if any(o.modifie for o in self.onglets) and not messagebox.askyesno(
                "Changer de projet", "Des fichiers ont des changements pas enregistrés.\n"
                "Changer de projet quand même?", parent=self):
            return
        self.etat(f"Ouverture de {dossier}…")
        self.app.en_arriere_plan(lambda: arbre_local(dossier),
                                 lambda arbre, err: self.dossier_recu(dossier, arbre, err))

    def dossier_recu(self, dossier, arbre, err):
        if err:
            self.etat(f"Impossible d'ouvrir ce dossier : {err}")
            return
        self.vider_onglets()
        self.depot, self.branche, self.arbre, self.cache, self.avant = None, None, arbre, {}, {}
        self.dossier, self.oc_session, self.oc_note = dossier, None, ""
        self.bouton_projet.config(text=f"{(dossier.name or str(dossier))[:22]}  ▾")
        moteur = self.app.moteurs.get(self.app.choix.get())
        avec = f" avec {nom_court(moteur)}" if moteur else ""
        self.etat(f"{dossier} : {len(arbre)} fichiers. OpenCode va travailler dedans{avec} "
                  "(l'IA choisie en bas). Dis-moi quoi faire."
                  + (" C'est un gros dossier : choisis plutôt celui de ton projet."
                     if len(arbre) >= 20_000 else ""))

    def vider_onglets(self):
        for o in self.onglets:
            o.cadre.destroy()
        self.onglets, self.actif = [], None
        self.dessiner_onglets()
        self.vide_editeur.place(relx=0.5, rely=0.45, anchor="center")

    def ouvrir_fichier_local(self, chemin):
        """Ouvre un fichier du dossier dans l'éditeur (le texte, ou l'image)."""
        try:
            octets = (self.dossier / chemin).read_bytes()
        except OSError as e:
            self.etat(f"Impossible d'ouvrir {chemin} : {e.strerror or e}")
            return
        if Path(chemin).suffix.lower() in EXT_IMAGES and Image is not None:
            self.ajouter_image_octets(chemin, octets, modifie=False)
            return
        try:
            texte = octets.decode("utf-8")
        except UnicodeDecodeError:
            self.etat(f"{chemin} n'est pas du texte : l'éditeur peut pas l'ouvrir.")
            return
        self.activer(self.creer_onglet(chemin, texte))

    def ouvrir_chemin_local(self, chemin, dossier):
        """« Modifier » sur une carte : l'onglet s'il est ouvert, sinon le fichier du disque."""
        if dossier != self.dossier:
            self.etat("Ce fichier-là est dans un autre dossier que celui ouvert.")
            return
        o = self.trouver_onglet(chemin)
        if o:
            self.activer(o)
        else:
            self.ouvrir_fichier(chemin)

    def enregistrer_local(self, onglets):
        """« Enregistrer » dans un dossier de ton ordi : ça s'écrit directement dedans."""
        faits = []
        for o in onglets:
            cible = (self.dossier / o.chemin).resolve()
            if not cible.is_relative_to(self.dossier):
                self.etat(f"{o.chemin} sort du dossier : pas enregistré.")
                continue
            try:
                cible.parent.mkdir(parents=True, exist_ok=True)
                cible.write_bytes(o.octets if o.est_image else o.contenu().encode("utf-8"))
            except OSError as e:
                self.etat(f"Impossible d'enregistrer {o.chemin} : {e.strerror or e}")
                return
            o.set_modifie(False)
            self.arbre[o.chemin] = {"sha": None, "taille": cible.stat().st_size}
            faits.append(Path(o.chemin).name)
        if faits:
            self.etat(f"Enregistré dans ton dossier : {', '.join(faits)}.")

    def envoyer_opencode(self, question, moteur):
        """La demande part à OpenCode, qui travaille directement dans ton dossier."""
        type_moteur, modele = moteur
        programme, dossier, session = trouver_opencode(), self.dossier, self.oc_session
        pieces, self.pieces = self.pieces, []
        self.app.dessiner_pieces(self.cadre_pieces, self.pieces, self.retirer_piece)
        images = []
        if pieces:
            self.app.montrer_vignettes(self.chat, pieces, 90)
            if type_moteur == "claude":
                images = [p["chemin"] for p in pieces if p.get("chemin")]
        demande = question
        if pieces and not images:
            demande += "\n(J'avais joint des images, mais ce modèle-là peut pas les voir.)"
        if self.oc_note:
            demande, self.oc_note = self.oc_note + "\n\n" + demande, ""
        self.app.voix.taire()           # on arrête de lire l'ancienne réponse
        self.app.avatar(self.chat)      # le logo Marceau devant la réponse qui s'en vient
        self.points = ajouter_ligne_attente(
            self.chat, f"OpenCode ({nom_court(moteur)}) travaille dans « {dossier.name} »", 14,
            ("attente", "attente_codex"))
        self.occupe, self.oc_en_cours, self.oc_arrete = True, True, False
        self.bouton_envoyer.config(text="Arrêter")

        def progres(ligne):
            self.app.depuis_fil(lambda: self.maj_attente("OpenCode " + ligne))

        def garder(processus):
            self.oc_processus = processus

        def travail():
            avant, complete = photo_dossier(dossier)
            resultat = lancer_opencode(programme, dossier, demande, type_moteur, modele, session,
                                       images, progres, garder, lambda: self.oc_arrete)
            if resultat["session_perdue"]:   # OpenCode a oublié la conversation : on en recommence une
                resultat = lancer_opencode(programme, dossier, demande, type_moteur, modele, None,
                                           images, progres, garder, lambda: self.oc_arrete)
            apres, complete_apres = photo_dossier(dossier)
            resultat["changements"] = changements_dossier(avant, apres, complete and complete_apres)
            resultat["arbre"] = arbre_local(dossier)
            return resultat

        self.app.en_arriere_plan(travail, lambda r, err: self.reponse_opencode(
            r, err, dossier, type_moteur, modele))

    def reponse_opencode(self, resultat, err, dossier, type_moteur, modele):
        enlever_ligne_attente(self.chat, "attente_codex", getattr(self, "points", None))
        self.points, self.oc_processus, self.oc_en_cours = None, None, False
        arrete, self.oc_arrete = self.oc_arrete, False
        self.bouton_envoyer.config(text="Envoyer")
        if err:
            self.messages.pop()
            self.app.ecrire(self.chat, f"OpenCode a pas pu partir : {err}", lambda: True,
                            self.fin_opencode)
            return
        changements = resultat["changements"]
        if dossier == self.dossier:
            self.arbre = resultat["arbre"]
            if resultat["session"]:
                self.oc_session = resultat["session"]
            for chemin, avant, apres, nouveau, supprime in changements:
                o = self.trouver_onglet(chemin)      # un onglet ouvert suit le fichier changé
                if o is not None and not o.est_image and not o.modifie and not supprime:
                    o.recharger(apres)
        if arrete:
            texte = "Arrêté. " + ("Voici ce qu'OpenCode avait déjà changé." if changements else
                                  "OpenCode avait rien changé.")
        elif resultat["erreur"]:
            texte = message_opencode(resultat["erreur"], type_moteur, modele)
        elif resultat["texte"]:
            texte = resultat["texte"]
        elif changements:
            texte = "C'est fait, regarde les fichiers."
        elif resultat["code"]:
            derniere = (resultat["journal"].splitlines() or [""])[-1]
            texte = "OpenCode s'est arrêté sans répondre." + (f" Il dit : {derniere}" if derniere else "")
        else:
            texte = "OpenCode a rien répondu cette fois-ci. Reformule ta demande."
        noms = [c for c, *_ in changements]
        self.messages.append({"role": "assistant", "content": texte + (
            f"\n(Fichiers changés : {', '.join(noms)})" if noms else "")})

        def fini():
            self.fin_opencode(resultat["etapes"], changements, dossier)
            if not arrete:
                self.app.dire_a_voix_haute(texte, self.chat)

        self.app.ecrire(self.chat, texte, lambda: True, fini)

    def fin_opencode(self, etapes=(), changements=(), dossier=None):
        """Après la réponse : ce qu'OpenCode a fait, en petit, pis une carte par fichier changé."""
        lus = list(dict.fromkeys(e["fichier"] for e in etapes if e["outil"] == "read" and e["fichier"]))
        commandes = [e["commande"] for e in etapes if e["outil"] == "bash" and e["commande"]]
        bloques = [e["ligne"].removesuffix(" (refusé)") for e in etapes if e["refuse"]]
        if lus:
            noms = ", ".join(Path(c).name for c in lus[:8]) + (f" (+{len(lus) - 8})" if len(lus) > 8 else "")
            self.chat.insert("end", f"OpenCode a lu : {noms}\n", "sources")
        if commandes:
            self.chat.insert("end", "Commandes lancées : " + "  ·  ".join(commandes[:6])
                             + (f" (+{len(commandes) - 6})" if len(commandes) > 6 else "") + "\n",
                             "sources")
        if bloques:
            self.chat.insert("end", "Bloqué pour te protéger : " + "; ".join(bloques[:4]) + "\n",
                             "sources")
        if changements:
            self.cartes_opencode(changements, dossier)
        self.chat.see("end")
        self.occupe = False

    def cartes_opencode(self, changements, dossier):
        """Une carte par fichier changé, pis un bouton pour tout remettre comme avant."""
        self.chat.update_idletasks()
        largeur = max(self.chat.winfo_width() - 34, 320)
        for chemin, avant, apres, nouveau, supprime in changements:
            carte = CarteFichier(self.chat, self.app, chemin, avant, apres, nouveau, largeur,
                                 lambda c, d=dossier: self.ouvrir_chemin_local(c, d),
                                 supprime=supprime)
            self.chat.window_create("end", window=carte, pady=5)
            self.chat.insert("end", "\n")
        bouton = bouton_orange(self.chat, "Remettre comme avant", None, taille=9)
        bouton.config(command=lambda: self.annuler_opencode(dossier, changements, bouton))
        self.chat.window_create("end", window=bouton, pady=4)
        self.chat.insert("end", "  C'est déjà enregistré dans ton dossier. Clique un fichier pour "
                                "voir ce qui a changé.\n", "sources")

    def annuler_opencode(self, dossier, changements, bouton):
        """« Remettre comme avant » : défait ce qu'OpenCode vient de changer."""
        if self.oc_en_cours:
            self.etat("Attends qu'OpenCode ait fini avant de remettre comme avant.")
            return
        remis, laisses = remettre_comme_avant(dossier, changements)
        bouton.config(text="Remis comme avant" if remis else "Rien à remettre", state="disabled",
                      cursor="")
        if dossier == self.dossier:
            self.arbre = arbre_local(dossier)
            for chemin, avant, apres, nouveau, supprime in changements:
                o = self.trouver_onglet(chemin)
                if chemin not in remis or o is None or o.est_image or o.modifie:
                    continue
                if nouveau:
                    self.fermer_onglet(o)      # le fichier existe plus
                else:
                    o.recharger(avant)
            if remis:   # OpenCode le saura à ta prochaine demande
                self.oc_note = ("(Note de Marceau : j'ai défait tes derniers changements. Ces "
                                f"fichiers sont revenus comme avant : {', '.join(remis)}.)")
        message = f"Remis comme avant : {', '.join(Path(c).name for c in remis)}." if remis else ""
        if laisses:
            message += ((" " if message else "") + "Pas touché, parce que changé depuis : "
                        + ", ".join(Path(c).name for c in laisses) + ".")
        self.etat(message or "Rien à remettre.")
        self.chat.insert("end", (message or "Rien à remettre.") + "\n", "sources")
        self.chat.see("end")


# ---------- L'application ----------
class AppEcriture(tk.Tk):
    def __init__(self):
        super().__init__()
        choisir_polices(self)   # la police du système, avant de bâtir la moindre affaire
        self.title("Marceau")
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
        self.nb_liens = 0
        self.points_ia = None        # les 3 points animés pendant que l'IA réfléchit
        self.pieces = []             # images jointes à la prochaine question
        self.images_tk = []          # vignettes affichées (Tkinter les efface si on les garde pas)
        self.image_courante = None   # la dernière image de la conversation (pour le Studio)
        self.image_courante_chemin = None
        self.occupe_magie = False    # un pouvoir magique est en train de travailler
        self.boutons_voix = []       # le bouton 🔊 du chat pis celui du Codex
        self.voix_active = lire_reglages().get("voix", True)   # l'IA lit ses réponses à voix haute
        self.voix_avertie = False    # on explique une seule fois comment avoir une voix
        self.voix = Voix(sur_changement=lambda: self.depuis_fil(self.maj_boutons_voix))
        self.apercu = ApercuApps()   # les apps du Studio, visibles dans ton navigateur
        self.apps_ouvertes = set()   # celles déjà ouvertes : la prochaine version recharge l'onglet
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
        self.bouton_fichier = bouton_orange(self.barre, "Fichier  \u25be", self.ouvrir_menu_fichier)
        self.bouton_fichier.pack(side="left", padx=(10, 0))
        self.bouton_magie = bouton_orange(self.barre, "\u2728  Magie", self.ouvrir_menu_magie)
        self.bouton_magie.pack(side="left", padx=(10, 0))

        # --- Le logo de l'agent (s'il est à côté du script) ---
        self.logo = None
        if FICHIER_LOGO.exists():
            try:
                self.logo = LogoAgent(self)
            except Exception as e:
                print("Logo pas chargé :", e)

        # --- La conversation (cachée au début, modifiable) ---
        # undo=True : Ctrl+Z ramène le texte d'avant quand un pouvoir magique le change
        self.document = tk.Text(self, undo=True, maxundo=-1, **style_zone())
        self.configurer_tags(self.document, retrait=LOGO_AVATAR + 12 if self.logo else 0,
                             taille_reponse=TAILLE_AGENT)
        self.document.config(yscrollcommand=self.sur_defilement_doc)
        self.document.bind("<Configure>", lambda e: self.sur_defilement_doc())
        self.document.bind("<Button-3>", self.clic_droit_document)     # clic droit : le menu Magie
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
        self.bouton_image(self.options, self.joindre_images).pack(side="left", padx=(8, 0))
        bouton_orange(self.options, "\u2728  Magie", self.ouvrir_menu_magie, taille=10).pack(
            side="left", padx=(8, 0))
        self.creer_bouton_voix(self.options).pack(side="left", padx=(8, 0))
        self.cadre_pieces = tk.Frame(self.options, bg=GRIS_FOND)
        self.cadre_pieces.pack(side="left")

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
        self.mettre_icone()
        self.saisie.focus_set()
        self.after(80, self.traiter_taches)
        self.after(300, self.charger_modeles_claude)
        self.after(1500, self.verifier_maj)   # sans déranger : ça se fait en arrière-plan
        self.after(HEURES_MAJ * 3600_000, self.remaj)   # pis on revérifie de temps en temps

    def remaj(self):
        """L'app peut rester ouverte des jours : on revérifie sans attendre un redémarrage."""
        self.verifier_maj()
        self.after(HEURES_MAJ * 3600_000, self.remaj)

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
                images = [c for c in m.get("images") or [] if Path(c).exists()]
                if images and Image is not None:
                    pieces = [{"image": ouvrir_image(c), "chemin": c} for c in images]
                    self.montrer_vignettes(self.document, pieces, 130)
                    self.image_courante = pieces[0]["image"]
                    self.image_courante_chemin = pieces[0]["chemin"]
            else:
                dernier = self.avatar()
                debut = self.document.index("end-1c")
                self.document.insert("end", m["content"] + "\n", "reponse")
                self.lier_liens(self.document, debut, "end-1c")
                self.ajouter_schema_et_sources(m.get("etapes") or [],
                                               [tuple(s) for s in m.get("sources") or []])
                if m.get("meteo") is not None:
                    self.ajouter_meteo(m["meteo"])   # la météo d'astheure, en direct
                if m.get("studio") and Image is not None:
                    self.remontrer_studio(m["studio"])
                if m.get("app"):
                    self.ajouter_app(m["app"], m, anime=False)
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
        if self.points_ia is not None:
            self.points_ia.destroy()
            self.points_ia = None
        self.images_tk = []
        self.image_courante = self.image_courante_chemin = None
        self.voix.taire()
        self.document.delete("1.0", "end")
        self.document.edit_reset()   # on repart à neuf : Ctrl+Z ne ramène pas l'ancienne conversation
        self.title("Marceau")
        if self.logo:
            self.logo.arreter_suivi()

    def historique_api(self):
        historique = []
        # L'IA doit revoir le code de sa DERNIÈRE app pour la modifier (« fais-le plus gros »).
        # Les plus vieilles sont juste nommées : pas besoin de repayer leur code à chaque message.
        derniere_app = max((i for i, m in enumerate(self.messages) if m.get("app")), default=None)
        for i, m in enumerate(self.messages):
            contenu = m["content"]
            if m.get("app"):
                app = m["app"]
                contenu += (f"\n[APP {app['titre']}]\n{app['html']}[/APP]" if i == derniere_app
                            else f"\n(L'app « {app['titre']} » était ici.)")
            message = {"role": m["role"], "content": contenu}
            if m.get("images"):
                message["images_chemins"] = m["images"]
            historique.append(message)
        return historique

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
        self.voix.taire()      # sinon la voix du système continue de parler, l'app fermée
        self.apercu.arreter()
        if self.codex:
            self.codex.arreter_opencode()   # OpenCode s'arrête avec l'app
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
        if not texte and not self.pieces:
            return "break"
        texte = texte or "Regarde mon image."
        moteur = self.moteurs.get(self.choix.get())
        if moteur is None:
            return "break"
        cle = ""
        if moteur[0] == "claude":
            cle = lire_secret(FICHIER_CLE, "ANTHROPIC_API_KEY")
            if not cle:
                self.ouvrir_parametres("claude")   # ta question reste dans la boîte
                return "break"

        self.voix.taire()          # on arrête de lire l'ancienne réponse
        self.saisie.delete("1.0", "end")
        self.document.insert("end", texte + "\n", "question")
        message = {"role": "user", "content": texte}
        pieces, self.pieces = self.pieces, []
        self.dessiner_pieces(self.cadre_pieces, self.pieces, self.retirer_piece)
        if pieces:
            self.montrer_vignettes(self.document, pieces, 130)
            message["images"] = [p["chemin"] for p in pieces]
            self.image_courante, self.image_courante_chemin = pieces[0]["image"], pieces[0]["chemin"]
        self.messages.append(message)
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
            avis = ""
            if any(m.get("images_chemins") for m in historique):
                voit = type_moteur == "claude" or modele_voit_images(modele)
                if not voit and historique[-1].get("images_chemins"):
                    avis = (f"{nom_court(moteur)} voit pas les images, mais peut quand même "
                            "les modifier dans le Studio. Pour qu'il les voie : ollama pull gemma3, "
                            "ou choisis Claude.")
                historique = preparer_historique(historique, voit)
            if type_moteur == "claude":
                texte, sources = appeler_claude(cle, historique, instructions_systeme(web=True),
                                                max_tokens=16000, timeout=600, modele=modele)
            else:
                texte, sources = appeler_ollama(modele, historique, instructions_systeme(web=False))
            self.resultats.put((generation, "ok", texte, sources, avis))
        except Exception as err:
            self.resultats.put((generation, "erreur", message_erreur(err, type_moteur, modele), [], ""))

    def verifier_resultat(self):
        try:
            generation, statut, texte, sources, avis = self.resultats.get_nowait()
        except queue.Empty:
            if self.occupe:
                self.after(100, self.verifier_resultat)
            return

        if generation != self.generation:
            # Réponse d'une conversation qu'on a quittée : on l'ignore
            if self.occupe:
                self.after(100, self.verifier_resultat)
            return

        enlever_ligne_attente(self.document, "attente_ia", self.points_ia)
        self.points_ia = None
        continuer = lambda: generation == self.generation

        if statut == "ok":
            texte, app = extraire_app(texte)     # d'abord : son code pourrait ressembler à un plan
            texte, etapes = extraire_plan(texte, self.question_en_cours)
            texte, lieu_meteo = extraire_meteo(texte, self.question_en_cours)
            texte, operations = extraire_studio(texte)
            texte = liens_markdown_en_texte(texte) or (
                "Voilà ton app :" if app else
                "Voici la météo :" if lieu_meteo is not None else "Voici le plan :" if etapes else
                "Voilà ton image :" if operations else
                "Pas de réponse cette fois-ci. Reformule ta question.")
            avait_image = bool(self.messages and self.messages[-1].get("images"))
            reponse = {"role": "assistant", "content": texte, "etapes": etapes,
                       "sources": [list(s) for s in sources], "meteo": lieu_meteo}
            self.messages.append(reponse)
            self.sauver_session()

            def apres_ecriture():
                # Le schéma, les sources, la météo pis le Studio arrivent une fois le texte fini d'écrire
                index = self.ajouter_schema_et_sources(etapes, sources)
                if lieu_meteo is not None:
                    self.ajouter_meteo(lieu_meteo)
                if avis:
                    self.document.insert("end", avis + "\n", "sources")
                if operations or avait_image:
                    self.ajouter_studio(operations, reponse)
                if app:
                    self.ajouter_app(app, reponse)
                self.fin_reponse(index)
                self.dire_a_voix_haute(texte)

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

    def avatar(self, widget=None):
        """Petit logo Marceau devant la réponse de l'agent (dans le chat ou le Codex). Retourne où il est."""
        if not self.logo:
            return None
        widget = widget or self.document
        index = widget.index("end-1c")
        widget.image_create(index, image=self.logo.image(LOGO_AVATAR), padx=3, align="center")
        widget.tag_add("avatar", index)
        return index

    # ---------- L'icône de la fenêtre : le logo Marceau ----------
    def mettre_icone(self):
        """Le logo Marceau devient l'icône de la fenêtre pis de la barre des tâches."""
        for nom in FICHIERS_ICONE:
            chemin = Path(__file__).with_name(nom)
            if not chemin.exists():
                continue
            try:
                if Image is not None:
                    source = Image.open(chemin).convert("RGBA")
                    self.icones = [ImageTk.PhotoImage(source.resize((t, t), Image.LANCZOS), master=self)
                                   for t in (64, 128)]
                else:
                    self.icones = [tk.PhotoImage(file=str(chemin), master=self)]
                self.iconphoto(True, *self.icones)   # True : les autres fenêtres l'héritent
                return
            except Exception:
                continue   # ce fichier-là marche pas : on essaie le suivant

    # ---------- Le menu Fichier ----------
    def ouvrir_menu_fichier(self):
        menu = tk.Menu(self, tearoff=0, bg=GRIS_ZONE, fg=NOIR, activebackground=ORANGE,
                       activeforeground=NOIR, font=(FAMILLE, 11), bd=0, relief="flat")
        menu.add_command(label="➕  Créer un fichier…", command=self.creer_fichier)
        menu.add_separator()
        menu.add_command(label="\U0001f4c1  Mes fichiers", command=self.mes_fichiers)
        b = self.bouton_fichier
        menu.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())

    def images_de_la_conversation(self):
        """Toutes les images de la conversation, dans l'ordre : les tiennes pis celles du Studio."""
        if Image is None:
            return []
        chemins = []
        for m in self.messages:
            for c in m.get("images") or []:
                chemins.append(c)
            studio = m.get("studio") or {}
            for c in (studio.get("apres"), studio.get("avant")):
                if c and c not in chemins:
                    chemins.append(c)
                    break     # l'après suffit; l'avant sert juste s'il n'y a pas d'après
        images = []
        for c in dict.fromkeys(chemins):
            try:
                images.append(ouvrir_image(c))
            except Exception:
                pass          # l'image a été effacée de l'ordi
        return images

    def creer_fichier(self):
        """« Fichier ▸ Créer » : ce que t'as écrit devient un document à envoyer."""
        self.montrer_document()
        texte, _, _ = self.texte_choisi()
        titre = ""
        for m in self.messages:
            if m["role"] == "user" and m["content"].strip():
                titre = " ".join(m["content"].split())[:60]
                break
        FenetreFichier(self, titre or "Mon document", texte, self.images_de_la_conversation())

    def fichier_cree(self, chemin):
        """Quand le fichier est écrit : on le dit, pis on offre de l'ouvrir."""
        chemin = Path(chemin)
        taille = taille_lisible(chemin.stat().st_size)
        self.dire_magie(f"Fichier créé : {chemin}  ({taille})")
        if messagebox.askyesno("Fichier créé",
                               f"{chemin.name} est prêt ({taille}).\n\n{chemin}\n\nL'ouvrir?",
                               parent=self):
            self.ouvrir_dehors(chemin)

    def ouvrir_dehors(self, chemin):
        """Ouvre un fichier ou un dossier avec le programme du système."""
        try:
            webbrowser.open(Path(chemin).resolve().as_uri())
        except Exception as e:
            messagebox.showinfo("Ouvrir", f"J'ai pas réussi à l'ouvrir : {e}\n\n{chemin}", parent=self)

    def mes_fichiers(self):
        """La liste des fichiers que t'as créés : « on retrouve »."""
        fichiers = sorted(DOSSIER_FICHIERS.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True) \
            if DOSSIER_FICHIERS.exists() else []
        fichiers = [f for f in fichiers if f.is_file()]
        fen = tk.Toplevel(self, bg=GRIS_MENU)
        fen.title("Mes fichiers")
        fen.geometry("620x440")
        fen.transient(self)
        cadre = tk.Frame(fen, bg=GRIS_MENU)
        cadre.pack(fill="both", expand=True, padx=18, pady=16)
        tk.Label(cadre, text=str(DOSSIER_FICHIERS), bg=GRIS_MENU, fg="#2e2e2e", anchor="w",
                 font=(FAMILLE, 9)).pack(fill="x", pady=(0, 8))
        if not fichiers:
            tk.Label(cadre, text="Aucun fichier encore. Fais-en un avec « Créer un fichier… ».",
                     bg=GRIS_MENU, fg=NOIR, font=(FAMILLE, 12)).pack(pady=30)
        zone = tk.Frame(cadre, bg=GRIS_MENU)
        zone.pack(fill="both", expand=True)
        liste = tk.Listbox(zone, bg=GRIS_MENU, fg=NOIR, selectbackground=ORANGE,
                           selectforeground=NOIR, font=(FAMILLE, 11), relief="flat", bd=0,
                           highlightthickness=0, activestyle="none")
        defil = barre_defilement(zone, "vertical", command=liste.yview)
        liste.config(yscrollcommand=defil.set)
        defil.pack(side="right", fill="y")
        liste.pack(side="left", fill="both", expand=True)
        for f in fichiers:
            quand = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%d %b %Y, %H:%M")
            liste.insert("end", f"  {f.name}   —   {taille_lisible(f.stat().st_size)}   —   {quand}")

        def ouvrir(*_):
            choix = liste.curselection()
            if choix:
                self.ouvrir_dehors(fichiers[choix[0]])

        liste.bind("<Double-Button-1>", ouvrir)
        liste.bind("<Return>", ouvrir)
        boutons = tk.Frame(cadre, bg=GRIS_MENU)
        boutons.pack(fill="x", pady=(12, 0))
        bouton_orange(boutons, "Ouvrir", ouvrir).pack(side="left")
        bouton_orange(boutons, "Ouvrir le dossier",
                      lambda: self.ouvrir_dehors(DOSSIER_FICHIERS), taille=9).pack(side="left", padx=(10, 0))
        bouton_orange(boutons, "Fermer", fen.destroy, taille=9).pack(side="right")
        fen.bind("<Escape>", lambda e: fen.destroy())


    # ---------- La voix : l'IA lit ses réponses, dans le chat comme dans le Codex ----------
    def creer_bouton_voix(self, parent):
        """Le bouton 🔊 : allume ou coupe la voix. Pendant qu'elle parle, il la fait taire."""
        bouton = tk.Button(parent, command=self.clic_voix, fg=NOIR, activebackground=ORANGE_FONCE,
                           activeforeground=NOIR, font=(FAMILLE, 10, "bold"), relief="flat", bd=0,
                           highlightthickness=0, padx=12, pady=5, cursor="hand2")
        self.boutons_voix.append(bouton)
        self.maj_boutons_voix()
        return bouton

    def maj_boutons_voix(self):
        """Les deux boutons (chat pis Codex) disent toujours la même chose."""
        if self.voix.parle:
            texte, fond = "\u23f9  Silence", ORANGE
        elif self.voix_active:
            texte, fond = "\U0001f50a  Voix", ORANGE
        else:
            texte, fond = "\U0001f507  Voix", GRIS_INACTIF
        for bouton in list(self.boutons_voix):
            try:
                bouton.config(text=texte, bg=fond)
            except tk.TclError:
                self.boutons_voix.remove(bouton)     # son écran a été fermé

    def clic_voix(self):
        if self.voix.parle:
            self.voix.taire()          # juste cette réponse-là : la voix reste allumée
        else:
            self.voix_active = not self.voix_active
            reglages = lire_reglages()
            reglages["voix"] = self.voix_active
            enregistrer_reglages(reglages)
            if self.voix_active and self.voix.moteur() is None:
                self.offrir_une_voix()
        self.maj_boutons_voix()

    def dire_a_voix_haute(self, texte, widget=None):
        """Lit une réponse de l'IA, si la voix est allumée."""
        if not self.voix_active or not texte:
            return
        if self.voix.parler(texte) or self.voix.moteur() is not None:
            return
        if not self.voix_avertie:       # une seule fois, pas à chaque réponse
            self.voix_avertie = True
            (widget or self.document).insert(
                "end", "(Pour entendre les réponses, il faut une voix sur ton ordi : "
                       "sudo apt install speech-dispatcher espeak-ng — ou coupe la voix "
                       "avec le bouton \U0001f50a.)\n", "sources")

    def offrir_une_voix(self, ensuite=None):
        """Aucune voix : on offre de télécharger la voix Piper, sinon on explique quoi installer."""
        if not piper_installe():
            messagebox.showinfo("Voix", MESSAGE_VOIX, parent=self)
            return
        if not messagebox.askyesno(
                "Voix",
                f"La voix française ({VOIX_PIPER}) n'est pas encore sur ton ordi.\n\n"
                "La télécharger maintenant? Ça prend environ 60 Mo et une connexion "
                "Internet, une seule fois : après, la lecture marche hors ligne.",
                parent=self):
            return
        self.pouvoir("Je télécharge la voix française", telecharger_voix,
                     lambda _: ensuite() if ensuite else self.dire_magie("La voix française est prête."),
                     besoin_ollama=False)

    # ---------- Les pouvoirs magiques ----------
    def construire_menu_magie(self):
        """Le menu ✨ Magie : les pouvoirs qui roulent sur ton ordi, gratuitement."""
        menu = tk.Menu(self, tearoff=0, bg=GRIS_ZONE, fg=NOIR, activebackground=ORANGE,
                       activeforeground=NOIR, font=(FAMILLE, 11), bd=0, relief="flat")
        menu.add_command(label="✨  Continuer mon texte", command=self.magie_continuer)
        menu.add_command(label="\U0001fa84  Corriger les fautes", command=self.magie_corriger)
        styles = tk.Menu(menu, tearoff=0, bg=GRIS_ZONE, fg=NOIR, activebackground=ORANGE,
                         activeforeground=NOIR, font=(FAMILLE, 11), bd=0, relief="flat")
        for cle, nom, _ in STYLES:
            styles.add_command(label=nom, command=lambda c=cle: self.magie_style(c))
        menu.add_cascade(label="\U0001f3ad  Changer le style", menu=styles)
        menu.add_command(label="\U0001f4dc  Résumer", command=self.magie_resumer)
        menu.add_separator()
        menu.add_command(label="\U0001f3a4  Dicter", command=self.magie_dicter)
        menu.add_command(label="\u23f9  Arrêter la lecture" if self.voix.parle else
                               "\U0001f50a  Lire à voix haute", command=self.magie_lire)
        traduire = tk.Menu(menu, tearoff=0, bg=GRIS_ZONE, fg=NOIR, activebackground=ORANGE,
                           activeforeground=NOIR, font=(FAMILLE, 11), bd=0, relief="flat")
        traduire.add_command(label="Français → English",
                             command=lambda: self.magie_traduire("fr", "en"))
        traduire.add_command(label="English → Français",
                             command=lambda: self.magie_traduire("en", "fr"))
        menu.add_cascade(label="\U0001f30d  Traduire", menu=traduire)
        return menu

    def ouvrir_menu_magie(self, event=None):
        """Ouvre le menu : sous le bouton ✨ Magie, ou là où t'as cliqué à droite."""
        self.montrer_document()
        menu = self.construire_menu_magie()
        if event is not None:
            menu.tk_popup(event.x_root, event.y_root)
        else:
            b = self.bouton_magie
            menu.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())
        return "break"

    def montrer_document(self):
        """Sur l'écran d'accueil, le document est caché : les pouvoirs le font apparaître."""
        if self.premiere_ligne and not self.en_animation:
            self.premiere_ligne = False
            if self.logo:
                self.logo.glisser(vers_gauche=True)
            self.descendre()

    def clic_droit_document(self, event):
        """Clic droit sur le texte : si rien n'est sélectionné, on sélectionne le mot sous la souris."""
        if not self.document.tag_ranges("sel"):
            self.document.mark_set("insert", f"@{event.x},{event.y}")
        self.document.focus_set()
        return self.ouvrir_menu_magie(event)

    def texte_choisi(self):
        """Ce sur quoi le pouvoir travaille : ta sélection, ou tout le texte si t'as rien choisi.

        Rend (texte, début, fin) : les positions servent à remplacer le bon bout après.
        """
        zone = self.document.tag_ranges("sel")
        if zone:
            debut, fin = str(zone[0]), str(zone[1])
        else:
            debut, fin = "1.0", "end-1c"
        return self.document.get(debut, fin).strip(), debut, fin

    def moteur_local(self):
        """Le modèle Ollama à utiliser pour les pouvoirs. Rend None si Ollama ne répond pas."""
        choisi = self.moteurs.get(self.choix.get())
        if choisi and choisi[0] == "ollama":
            return choisi[1]        # celui que t'as choisi sous la boîte
        for type_moteur, modele in self.moteurs.values():
            if type_moteur == "ollama":
                return modele       # sinon le premier modèle local qu'on trouve
        return None

    def modele_local_ou_message(self):
        """Le modèle Ollama à utiliser. Rend None après avoir expliqué qu'Ollama ne répond pas.

        Il faut vérifier AVANT de bâtir le titre des points d'attente : celui-ci contient
        le nom du modèle, faque sans ça l'app plantait au lieu d'afficher le message.
        """
        modele = self.moteur_local()
        if modele is None:
            messagebox.showinfo("Magie", MESSAGE_OLLAMA, parent=self)
        return modele

    def pouvoir(self, titre, travail, fini, besoin_ollama=True):
        """Fait rouler un pouvoir en arrière-plan, avec les 3 points qui sautent.

        travail() roule dans un fil à part (l'app ne gèle pas).
        fini(resultat) roule dans la fenêtre, une fois que c'est prêt.
        """
        if self.occupe_magie:
            self.dire_magie("Un pouvoir travaille déjà. Attends qu'il finisse.")
            return
        if besoin_ollama and self.moteur_local() is None:
            messagebox.showinfo("Magie", MESSAGE_OLLAMA, parent=self)
            return
        self.occupe_magie = True
        self.nb_meteo += 1
        etiquette = f"attente_magie{self.nb_meteo}"
        self.document.see("end")
        points = ajouter_ligne_attente(self.document, titre, TAILLE_AGENT, ("attente", etiquette))
        generation = self.generation

        def apres(resultat, err):
            self.occupe_magie = False
            if generation != self.generation:
                points.destroy()
                return              # on a changé de conversation entre-temps
            enlever_ligne_attente(self.document, etiquette, points)
            if err:
                messagebox.showerror("Magie", self.message_magie(err), parent=self)
                return
            try:
                fini(resultat)
            except Exception as e:
                messagebox.showerror("Magie", f"Ça n'a pas marché : {e}", parent=self)

        self.en_arriere_plan(travail, apres)

    def message_magie(self, err):
        """Traduit une erreur technique en quelque chose qui se comprend."""
        texte = str(err)
        if isinstance(err, (urllib.error.URLError, ConnectionError, TimeoutError)) or \
                "11434" in texte or "Connection refused" in texte:
            return MESSAGE_OLLAMA
        return f"Ça n'a pas marché : {texte}"

    def dire_magie(self, message):
        """Un mot dans le document, en petit, sans déranger la conversation."""
        self.document.insert("end", message + "\n", "sources")
        self.document.see("end")

    def edition(self, action):
        """Fait un changement sur le document en UN seul coup de Ctrl+Z.

        Tkinter coupe l'annulation tout seul entre un effacement pis une insertion
        (c'est son réglage « autoseparators »). Sans ça, le premier Ctrl+Z après un
        remplacement effacerait le texte sans ramener l'ancien : le pire des deux
        mondes. On éteint la coupure automatique le temps du changement.
        """
        d = self.document
        d.edit_separator()
        d.config(autoseparators=False)
        try:
            action()
        finally:
            d.config(autoseparators=True)
            d.edit_separator()

    def remplacer_choix(self, debut, fin, texte, note=""):
        """Remplace le bout choisi. Un seul Ctrl+Z ramène l'ancien, le petit mot avec."""
        def changer():
            self.document.delete(debut, fin)
            self.document.insert(debut, texte)
            if note:
                self.document.insert("end", note + "\n", "sources")

        self.edition(changer)
        self.document.see("end" if note else debut)

    # --- 3. 🎭 Changer le style ---
    def magie_style(self, style):
        texte, debut, fin = self.texte_choisi()
        if not texte:
            self.dire_magie("Sélectionne le bout à réécrire (ou écris quelque chose).")
            return
        if len(texte) > 8000:
            self.dire_magie("C'est un gros morceau. Sélectionne un bout plus court à réécrire.")
            return
        modele = self.modele_local_ou_message()
        if modele is None:
            return
        nom, consigne = next((nom, c) for cle, nom, c in STYLES if cle == style)

        def fini(reecrit):
            if not reecrit:
                self.dire_magie("Le modèle n'a rien réécrit. Réessaie, ou prends un autre modèle.")
                return
            self.remplacer_choix(debut, fin, reecrit,
                                 f"Réécrit en style {nom.lower()}. Ctrl+Z ramène ton texte d'avant.")

        self.pouvoir(f"Je réécris en style {nom.lower()}",
                     lambda: texte_par_ollama(modele, texte, "style", consigne), fini)

    # --- 4. 📜 Résumer ---
    def magie_resumer(self):
        texte, _, fin = self.texte_choisi()
        if not texte:
            self.dire_magie("Écris ou sélectionne un texte à résumer.")
            return
        modele = self.modele_local_ou_message()
        if modele is None:
            return
        bout = texte[-12000:]

        def fini(resume):
            if not resume:
                self.dire_magie("Le modèle n'a rien résumé. Réessaie, ou prends un autre modèle.")
                return
            # Le résumé s'ajoute SOUS le texte : on n'efface jamais ce que t'as écrit.
            depart = self.document.index(fin)
            self.edition(lambda: self.document.insert(depart, "\n\nRésumé :\n" + resume + "\n",
                                                      "reponse"))
            self.document.see(depart)

        self.pouvoir("Je résume ton texte",
                     lambda: texte_par_ollama(modele, bout, "resumer"), fini)

    # --- 2. 🪄 Corriger les fautes ---
    def magie_corriger(self):
        texte, debut, fin = self.texte_choisi()
        if not texte:
            self.dire_magie("Écris ou sélectionne un texte à corriger.")
            return
        try:
            correcteur_francais()
        except ImportError:
            messagebox.showinfo("Corriger", MESSAGE_LANGUETOOL, parent=self)
            return
        except Exception as e:
            messagebox.showerror("Corriger", self.message_correcteur(e), parent=self)
            return

        def fini(fautes):
            if not fautes:
                self.dire_magie("Aucune faute trouvée. C'est bien écrit!")
                return
            FenetreFautes(self, fautes,
                          lambda acceptees: self.appliquer_corrections(debut, fin, texte, acceptees))

        self.pouvoir("Je cherche les fautes", lambda: trouver_fautes(texte), fini,
                     besoin_ollama=False)

    def appliquer_corrections(self, debut, fin, texte, acceptees):
        """Applique les corrections acceptées. Un seul Ctrl+Z ramène tout comme c'était."""
        if not acceptees:
            self.dire_magie("Aucune correction appliquée.")
            return
        corrige = texte
        # Les fautes sont déjà triées de la fin vers le début : les positions restent bonnes
        for a, b, _, propose, _ in acceptees:
            corrige = corrige[:a] + propose + corrige[b:]
        mot = "correction" if len(acceptees) == 1 else "corrections"
        self.remplacer_choix(debut, fin, corrige,
                             f"{len(acceptees)} {mot} appliquée{'s' if len(acceptees) > 1 else ''}. "
                             "Ctrl+Z ramène ton texte d'avant.")

    def message_correcteur(self, err):
        """Le message quand LanguageTool ne démarre pas — presque toujours Java qui manque."""
        texte = str(err)
        if "java" in texte.lower() or isinstance(err, FileNotFoundError):
            return ("LanguageTool a besoin de Java, qui n'est pas installé.\n\n"
                    "Dans un terminal :\n\n    sudo apt install default-jre\n\n"
                    "Ensuite, ferme pis rouvre Marceau.")
        return f"Le correcteur n'a pas démarré : {texte}"

    # --- 7. 🌍 Traduire (hors ligne) ---
    def magie_traduire(self, de, vers):
        texte, debut, fin = self.texte_choisi()
        if not texte:
            self.dire_magie("Sélectionne le texte à traduire (ou écris quelque chose).")
            return
        if not argos_installe():
            messagebox.showinfo("Traduire", MESSAGE_ARGOS, parent=self)
            return
        if (de, vers) not in paires_installees():
            if not messagebox.askyesno(
                    "Traduire",
                    f"La traduction {LANGUES[de]} vers {LANGUES[vers]} n'est pas encore sur ton "
                    "ordi.\n\nLa télécharger maintenant? Ça prend environ 100 Mo et une connexion "
                    "Internet, une seule fois : après, la traduction marche hors ligne.",
                    parent=self):
                return
            self.pouvoir(f"Je télécharge le {LANGUES[de]} vers {LANGUES[vers]}",
                         lambda: telecharger_langue(de, vers),
                         lambda _: self.magie_traduire(de, vers), besoin_ollama=False)
            return

        def fini(traduit):
            if not traduit:
                self.dire_magie("La traduction est revenue vide. Réessaie avec un texte plus court.")
                return
            self.remplacer_choix(debut, fin, traduit,
                                 f"Traduit en {LANGUES[vers]}. Ctrl+Z ramène ton texte d'avant.")

        self.pouvoir(f"Je traduis en {LANGUES[vers]}",
                     lambda: traduire_texte(texte, de, vers), fini, besoin_ollama=False)

    # --- 5. 🎤 Dicter ---
    def magie_dicter(self):
        pret, message = micro_pret()
        if not pret:
            messagebox.showinfo("Dicter", message, parent=self)
            return
        try:
            flux, morceaux = enregistreur()
        except Exception as e:
            messagebox.showerror("Dicter", MESSAGE_MICRO + f"\n\n(Détail : {e})", parent=self)
            return
        position = self.document.index("insert")   # on écrira là où ton curseur était

        def arrete():
            try:
                flux.stop()
                flux.close()
            except Exception:
                pass

            def fini(texte):
                if not texte:
                    self.dire_magie("J'ai rien entendu. Réessaie en parlant plus proche du micro.")
                    return
                # Un espace avant seulement s'il en manque un, pareil pour après :
                # sinon la dictée se colle au mot d'avant, ou fait un double espace.
                avant = self.document.get(f"{position}-1c", position)
                apres = self.document.get(position, f"{position}+1c")
                morceau = (("" if avant in ("", "\n", " ", "\t") else " ") + texte
                           + ("" if apres in ("", "\n", " ", "\t") else " "))
                self.edition(lambda: self.document.insert(position, morceau))
                self.document.mark_set("insert", f"{position}+{len(morceau)}c")
                self.document.see("insert")

            self.pouvoir("Je transcris ce que t'as dit", lambda: transcrire(morceaux), fini,
                         besoin_ollama=False)

        FenetreDictee(self, arrete)

    # --- 6. 🔊 Lire à voix haute ---
    def magie_lire(self):
        if self.voix.parle:
            self.voix.taire()
            self.dire_magie("Lecture arrêtée.")
            return
        texte, _, _ = self.texte_choisi()
        if not texte:
            self.dire_magie("Écris ou sélectionne un texte à lire.")
            return
        if self.voix.moteur() is None:
            self.offrir_une_voix(ensuite=self.magie_lire)
            return
        self.voix.parler(texte)      # même si la voix des réponses est coupée : tu l'as demandé

    # --- 1. ✨ Continuer mon texte ---
    def magie_continuer(self):
        texte, _, fin = self.texte_choisi()
        if not texte:
            self.dire_magie("Écris d'abord quelque chose, pis je continuerai.")
            return
        modele = self.modele_local_ou_message()
        if modele is None:
            return
        bout = texte[-6000:]        # un modèle local n'avale pas un roman d'un coup

        def fini(suite):
            if not suite:
                self.dire_magie("Le modèle n'a rien écrit. Réessaie, ou prends un autre modèle.")
                return
            depart = self.document.index(fin)
            separateur = "" if self.document.get(f"{depart}-1c", depart) in ("\n", "") else " "
            self.edition(lambda: self.document.insert(depart, separateur + suite + "\n", "reponse"))
            self.document.see(depart)

        self.pouvoir(f"{nom_court(('ollama', modele))} écrit la suite",
                     lambda: texte_par_ollama(modele, bout, "continuer"), fini)
    # ---------- Images ----------
    def bouton_image(self, parent, commande):
        return tk.Button(parent, text="+ Image", command=commande, bg=ORANGE, fg=NOIR,
                         activebackground=ORANGE_FONCE, activeforeground=NOIR, font=(FAMILLE, 10, "bold"),
                         relief="flat", bd=0, highlightthickness=0, padx=12, pady=5, cursor="hand2")

    def choisir_images(self, parent):
        if Image is None:
            messagebox.showinfo("Images", MESSAGE_PILLOW, parent=parent)
            return []
        fichiers = filedialog.askopenfilenames(title="Choisis une ou des images", filetypes=TYPES_IMAGES,
                                               parent=parent)
        return self.charger_pieces(fichiers)

    def charger_pieces(self, fichiers):
        pieces = []
        for fichier in list(fichiers)[:4]:
            try:
                image = ouvrir_image(fichier)
            except Exception:
                messagebox.showerror("Image", f"Impossible d'ouvrir {Path(fichier).name}.")
                continue
            pieces.append({"nom": Path(fichier).name, "image": image, "chemin": garder_image(image),
                           "original": str(fichier)})
        return pieces

    def dessiner_pieces(self, cadre, pieces, retirer):
        """Les petites images jointes, à côté du bouton « + Image » (× pour en enlever une)."""
        for w in cadre.winfo_children():
            w.destroy()
        for i, piece in enumerate(pieces):
            puce = tk.Frame(cadre, bg=GRIS_ZONE, highlightthickness=1, highlightbackground=GRIS_BORD)
            puce.pack(side="left", padx=(8, 0))
            puce.vignette = vignette_tk(piece["image"], 26, 26)
            tk.Label(puce, image=puce.vignette, bg=GRIS_ZONE).pack(side="left", padx=(3, 3), pady=2)
            nom = piece["nom"] if len(piece["nom"]) <= 16 else piece["nom"][:15] + "…"
            tk.Label(puce, text=nom, bg=GRIS_ZONE, fg=NOIR, font=(FAMILLE, 9)).pack(side="left")
            tk.Button(puce, text="×", command=lambda i=i: retirer(i), bg=GRIS_ZONE, fg=NOIR,
                      activebackground=ORANGE, relief="flat", bd=0, highlightthickness=0,
                      font=(FAMILLE, 10, "bold"), padx=5, cursor="hand2").pack(side="left")

    def montrer_vignettes(self, widget, pieces, taille):
        for piece in pieces:
            vignette = vignette_tk(piece["image"], taille, taille)
            self.images_tk.append(vignette)
            widget.image_create("end-1c", image=vignette, padx=4, pady=4)
        widget.insert("end", "\n")
        widget.see("end")

    def joindre_images(self):
        self.pieces = (self.pieces + self.choisir_images(self))[:4]
        self.dessiner_pieces(self.cadre_pieces, self.pieces, self.retirer_piece)
        self.saisie.focus_set()

    def retirer_piece(self, i):
        del self.pieces[i]
        self.dessiner_pieces(self.cadre_pieces, self.pieces, self.retirer_piece)

    def mettre_image_dans_codex(self, image):
        self.ouvrir_codex()
        chemin = simpledialog.askstring(
            "Mettre dans le Codex", "Chemin de l'image dans le projet :",
            initialvalue=f"images/studio-{datetime.datetime.now():%Y%m%d-%H%M%S}.png", parent=self)
        if chemin and chemin.strip():
            self.codex.ajouter_image(chemin.strip().lstrip("/"), image, montrer=True)

    def garder_image_projet(self, image, rappel=None):
        """« Garder dans le projet » : range l'image dans un dossier de projet, sur ton ordi."""
        reglages = lire_reglages()
        nom = simpledialog.askstring(
            "Garder dans le projet", "Nom du projet (c'est un dossier sur ton ordi) :",
            initialvalue=reglages.get("projet", "Mon projet"), parent=self)
        if not nom or not nom.strip():
            return
        nom = nom.strip()
        dossier = DOSSIER_PROJETS / (re.sub(r'[<>:"/\\|?*]', "-", nom)[:60] or "projet")
        try:
            dossier.mkdir(parents=True, exist_ok=True)
            # microsecondes : deux images gardées dans la même seconde s'écraseraient
            fichier = dossier / f"image-{datetime.datetime.now():%Y%m%d-%H%M%S-%f}.png"
            fichier.write_bytes(octets_pour(fichier.name, image))
        except OSError as e:
            messagebox.showerror("Garder dans le projet", f"Ça n'a pas marché : {e}", parent=self)
            return
        reglages["projet"] = nom
        enregistrer_reglages(reglages)
        self.dire_magie(f"Image gardée dans « {nom} » : {fichier}")
        if rappel:
            rappel(nom)

    # ---------- Le Studio d'applications ----------
    def ajouter_app(self, app, reponse, anime=True):
        """Une app construite par l'IA : sa carte dans la conversation, pis son aperçu dans le navigateur."""
        titre, html = app["titre"], app["html"]
        ident, version = self.apercu.publier(titre, html)
        if anime:
            reponse["app"] = {"titre": titre, "html": html}      # gardée avec la conversation
            self.sauver_session()
        largeur = max(self.document.winfo_width() - 60, 460)
        carte = None

        def construite():
            # La 1re fois, l'app s'ouvre toute seule. Après, l'onglet déjà ouvert se recharge.
            if ident not in self.apps_ouvertes:
                self.voir_app(ident)
                carte.etat.config(text="Ouverte dans ton navigateur.")
            else:
                carte.etat.config(text="L'aperçu ouvert vient de se mettre à jour tout seul.")

        carte = StudioApp(self.document, self, titre, html, ident, version, largeur, anime=anime,
                          fini=construite if anime else None)
        self.schemas.append(carte)     # effacée avec la conversation
        self.document.window_create("end-1c", window=carte, pady=8)
        self.document.insert("end", "\n")
        self.document.see("end")
        return carte

    def voir_app(self, ident):
        """Ouvre l'app dans ton navigateur (l'adresse est sur ton ordi seulement)."""
        self.apps_ouvertes.add(ident)
        adresse = self.apercu.adresse(ident)
        try:
            webbrowser.open(adresse)
        except Exception as e:
            messagebox.showinfo("Voir l'app", f"J'ai pas réussi à ouvrir ton navigateur : {e}\n\n"
                                              f"Ouvre cette adresse à la main :\n{adresse}", parent=self)

    def enregistrer_app(self, titre, html):
        """Enregistre l'app en .html — par défaut avec tes autres fichiers (Fichier ▸ Mes fichiers)."""
        DOSSIER_FICHIERS.mkdir(parents=True, exist_ok=True)
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer l'app", parent=self, defaultextension=".html",
            initialdir=str(DOSSIER_FICHIERS), initialfile=identifiant_app(titre) + ".html",
            filetypes=[("Page web", "*.html"), ("Tous les fichiers", "*.*")])
        if not chemin:
            return None
        Path(chemin).write_text(html, encoding="utf-8")
        return chemin

    def app_dans_codex(self, titre, html):
        """L'app devient un fichier de ton projet GitHub (index.html par défaut)."""
        chemin = simpledialog.askstring("Mettre dans le Codex", "Chemin du fichier dans le projet :",
                                        initialvalue="index.html", parent=self)
        if not chemin or not chemin.strip():
            return
        chemin = chemin.strip().lstrip("/")
        self.ouvrir_codex()
        self.codex.appliquer_fichier(chemin, html)
        self.codex.ouvrir_editeur()
        self.codex.etat(f"{chemin} est prêt. Clique « Enregistrer » pour l'envoyer sur GitHub.")

    # ---------- Le Studio ----------
    def ajouter_studio(self, operations, reponse):
        """Montre l'image dans le Studio, avec les modifications demandées (si y'en a)."""
        if self.image_courante is None:
            if operations:
                self.document.insert("end", "Partage d'abord une image avec le bouton « + Image », "
                                            "pis redemande-moi.\n", "reponse")
            return
        avant, avant_chemin = self.image_courante, self.image_courante_chemin
        self.nb_meteo += 1
        marque, etiquette = f"studio{self.nb_meteo}", f"attente_studio{self.nb_meteo}"
        self.document.mark_set(marque, "end-1c")
        self.document.mark_gravity(marque, "left")
        points = ajouter_ligne_attente(self.document, "Le Studio travaille", TAILLE_AGENT,
                                       ("attente", etiquette)) if operations else None
        generation = self.generation

        def travail():
            if not operations:
                return None, [], None
            apres, resume = appliquer_studio(avant, operations)
            return (apres, resume, garder_image(apres, "studio")) if resume else (None, [], None)

        def fini(resultat, err):
            if generation != self.generation:
                if points is not None:
                    points.destroy()
                return   # on a changé de conversation entre-temps
            if points is not None:
                enlever_ligne_attente(self.document, etiquette, points)
            if err:
                self.document.insert(marque, f"Le Studio a pas réussi : {err}\n", "reponse")
                return
            apres, resume, chemin = resultat
            self.placer_studio(marque, avant, apres, resume, anime=True)
            if apres is not None:
                self.image_courante, self.image_courante_chemin = apres, chemin
            reponse["studio"] = {"avant": avant_chemin, "apres": chemin, "resume": resume}
            self.sauver_session()

        if operations:
            self.en_arriere_plan(travail, fini)
        else:
            fini((None, [], None), None)

    def placer_studio(self, index, avant, apres, resume, anime):
        # L'image garde une taille qui rentre dans l'écran, pour voir le Studio au complet
        hauteur_image = max(160, min(StudioImage.HAUTEUR_IMAGE, self.document.winfo_height() - 150))
        a_la_fin = self.document.compare(index, ">=", "end-2c")
        studio = StudioImage(self.document, self, avant, apres, resume,
                             max(self.document.winfo_width() - 60, 440), anime=anime,
                             hauteur_image=hauteur_image,
                             suivre=(lambda: self.document.yview_moveto(1.0)) if a_la_fin else None)
        self.schemas.append(studio)   # effacé avec la conversation
        self.document.window_create(index, window=studio, pady=8)
        self.document.insert(f"{index}+1c", "\n")
        if a_la_fin:
            self.document.yview_moveto(1.0)

    def remontrer_studio(self, studio):
        try:
            avant = ouvrir_image(studio["avant"])
            apres = ouvrir_image(studio["apres"]) if studio.get("apres") else None
        except Exception:
            return   # les images ont été effacées de l'ordi
        self.placer_studio(self.document.index("end-1c"), avant, apres, studio.get("resume") or [], False)
        self.image_courante = apres or avant
        self.image_courante_chemin = studio.get("apres") or studio["avant"]

    def ajouter_meteo(self, lieu):
        """Pouvoir magique : va chercher la météo en direct pis l'affiche en carte animée."""
        self.nb_meteo += 1
        marque, etiquette = f"meteo{self.nb_meteo}", f"attente_meteo{self.nb_meteo}"
        self.document.mark_set(marque, "end-1c")
        self.document.mark_gravity(marque, "left")
        points = ajouter_ligne_attente(self.document, "Je regarde la météo", TAILLE_AGENT,
                                       ("attente", etiquette))
        generation, ville = self.generation, lire_reglages().get("ville", "")

        def fini(meteo, err):
            if generation != self.generation:
                points.destroy()
                return   # on a changé de conversation entre-temps
            enlever_ligne_attente(self.document, etiquette, points)
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
        index = self.avatar()
        if index:
            self.logo.suivre(index)   # le gros logo vient se placer à côté de la réponse
        self.points_ia = ajouter_ligne_attente(self.document, f"{nom} réfléchit", TAILLE_AGENT,
                                               ("attente", "attente_ia"))

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
            self.title(f"Marceau — {os.path.basename(chemin)}")

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
