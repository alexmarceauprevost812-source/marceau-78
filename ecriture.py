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
import os
import queue
import re
import threading
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from bisect import bisect_right
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

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

MARGE = 25            # espace entre la zone d'écriture et le bas de l'écran
LARGEUR = 0.70        # largeur des zones (70 % de la fenêtre)
HAUT_DOC = 70         # où commence le texte en haut de l'écran
LARGEUR_MENU = 270    # largeur du menu de gauche

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
MODELE_CLAUDE = "claude-sonnet-5"
URL_CLAUDE = "https://api.anthropic.com/v1/messages"
URL_OLLAMA = "http://localhost:11434"
URL_GITHUB = "https://api.github.com"
DOSSIER_CONFIG = Path.home() / ".config" / "ecriture"
FICHIER_CLE = DOSSIER_CONFIG / "cle_api"
FICHIER_TOKEN = DOSSIER_CONFIG / "github_token"
DOSSIER_SESSIONS = Path.home() / ".local" / "share" / "ecriture" / "sessions"
RECHERCHES_MAX = 5                     # recherches web max par question (Claude)
NOM_CLAUDE = "Claude + web (payant)"   # nom affiché dans le menu
STYLE_QUEBECOIS = True                 # False = l'IA parle en français standard
DUREE_ECRITURE = 1.5                   # secondes max pour écrire une réponse à l'écran
VITESSE_MS = 10                        # une lettre (ou un petit paquet) aux 10 ms
CONTEXTE_CLAUDE = 150_000              # caractères de code max envoyés à Claude par demande Codex
CONTEXTE_OLLAMA = 24_000               # … et aux modèles gratuits (leur mémoire est plus petite)
CTX_OLLAMA_CODEX = 16384               # mémoire (tokens) demandée à Ollama pour le Codex

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
                  "des horaires, la météo, des personnes ou n'importe quoi qui a pu changer récemment. ")
    else:
        texte += ("Tu n'as pas accès à Internet. Si la question demande des infos récentes "
                  "(actualité, météo, prix, horaires), dis-le franchement au lieu d'inventer "
                  f"et suggère de choisir « {NOM_CLAUDE} » dans le menu. ")
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
        "Si on te pose juste une question, réponds sans bloc."
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


def trouver_moteurs():
    """Les IA du menu : les modèles Ollama gratuits en premier, Claude à la fin."""
    moteurs = {}
    for nom in modeles_ollama():
        moteurs[f"{nom.removesuffix(':latest')} (gratuit)"] = ("ollama", nom)
    moteurs[NOM_CLAUDE] = ("claude", MODELE_CLAUDE)
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
def appeler_claude(cle, messages, systeme, web=True, max_tokens=2048, timeout=180):
    conversation = list(messages)
    morceaux, sources = [], []
    for _ in range(5):
        corps = {
            "model": MODELE_CLAUDE,
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
            return "Token GitHub invalide ou expiré. Clique sur « Token GitHub » pour le changer."
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
            self.etat("Ajoute ton token GitHub (bouton « Token ») pour ouvrir tes projets.")

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
        bouton_orange(barre, "Fermer", self.app.fermer_codex).pack(side="right", padx=(10, 18), pady=13)
        bouton_orange(barre, "Token", self.demander_token).pack(side="right", padx=(10, 0), pady=13)
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
        bas = tk.Frame(p, bg=GRIS_FOND)
        bas.pack(side="bottom", fill="x", padx=12, pady=(6, 10))
        self.saisie = tk.Text(bas, height=3, width=1, **style_zone(12))
        self.saisie.pack(fill="x")
        rang = tk.Frame(bas, bg=GRIS_FOND)
        rang.pack(fill="x", pady=(8, 0))
        self.app.creer_bouton_moteur(rang).pack(side="left")
        bouton_orange(rang, "Envoyer", self.envoyer).pack(side="right")
        self.chat = tk.Text(p, width=1, **style_zone(12))
        self.chat.pack(fill="both", expand=True, padx=12)
        self.app.configurer_tags(self.chat, 12)
        self.chat.insert("end", "Demande-moi d'écrire du code, d'expliquer un fichier ou de corriger "
                                "un bug. Scanne le projet pis j'vas voir tout le code.\n", "attente")
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

    # ----- GitHub : token et projets -----
    def demander_token(self):
        token = simpledialog.askstring(
            "Token GitHub",
            "Colle ton token GitHub.\n\nCrée-le sur github.com : Settings > Developer settings >\n"
            "Personal access tokens > Fine-grained tokens,\n"
            "avec la permission « Contents : Read and write ».",
            show="*", parent=self)
        if not token or not token.strip():
            return False
        enregistrer_secret(FICHIER_TOKEN, token.strip())
        self.token = token.strip()
        self.depots = []
        self.etat("Token enregistré. Choisis un projet en haut.")
        return True

    def menu_projets(self):
        if not self.token and not self.demander_token():
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
                  + " Clique un fichier pour l'ouvrir.")

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
    def contexte(self, budget):
        parties = []
        if self.depot:
            chemins = sorted(self.arbre)
            liste = "\n".join(chemins[:600]) + ("\n…" if len(chemins) > 600 else "")
            parties.append(f"Projet GitHub : {self.depot} (branche {self.branche}), "
                           f"{len(chemins)} fichiers.\nArborescence :\n{liste}")
        else:
            parties.append("Pas de projet GitHub ouvert. Les fichiers que tu écris vont "
                           "s'ouvrir dans l'éditeur.")
        fichiers = []
        if self.actif:
            fichiers.append((self.actif.chemin, self.actif.contenu(), "fichier ouvert à l'écran"))
        fichiers += [(o.chemin, o.contenu(), "onglet ouvert") for o in self.onglets if o is not self.actif]
        deja = {f[0] for f in fichiers}
        fichiers += [(c, t, "projet scanné") for c, t in self.cache.items() if c not in deja]
        total, omis = sum(len(p) for p in parties), []
        for chemin, contenu, note in fichiers:
            bloc = f"--- {chemin} ({note}) ---\n{contenu}"
            if total + len(bloc) > budget:
                omis.append(chemin)
                continue
            parties.append(bloc)
            total += len(bloc)
        if omis:
            parties.append(f"(Pas inclus, faute de place : {', '.join(omis[:30])})")
        return "\n\n".join(parties)

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
            cle = lire_secret(FICHIER_CLE, "ANTHROPIC_API_KEY") or self.app.demander_cle()
            if not cle:
                return "break"
        self.saisie.delete("1.0", "end")
        if not self.messages:
            self.chat.delete("1.0", "end")   # enlève le mot d'accueil
        self.chat.insert("end", question + "\n", "question")
        self.messages.append({"role": "user", "content": question})
        envoi = [dict(m) for m in self.messages[-8:]]
        while envoi and envoi[0]["role"] != "user":
            envoi.pop(0)
        budget = CONTEXTE_CLAUDE if type_moteur == "claude" else CONTEXTE_OLLAMA
        envoi[-1]["content"] = self.contexte(budget) + "\n\nDemande : " + question
        nom = "Claude" if type_moteur == "claude" else modele.removesuffix(":latest")
        self.chat.insert("end", f"Codex ({nom}) travaille…\n", "attente")
        self.chat.see("end")
        self.occupe = True
        systeme = instructions_codex()

        def travail():
            if type_moteur == "claude":
                return appeler_claude(cle, envoi, systeme, web=False, max_tokens=16000, timeout=600)[0]
            return appeler_ollama(modele, envoi, systeme, num_ctx=CTX_OLLAMA_CODEX)[0]

        self.app.en_arriere_plan(travail, lambda t, err: self.reponse(t, err, type_moteur, modele))
        return "break"

    def reponse(self, texte, err, type_moteur, modele):
        zone = self.chat.tag_ranges("attente")
        if zone:
            self.chat.delete(zone[0], zone[1])
        if err:
            self.messages.pop()
            self.app.ecrire(self.chat, message_erreur(err, type_moteur, modele),
                            lambda: True, self.fin_reponse)
            return
        explication, fichiers = extraire_fichiers(texte or "")
        ecrits = [self.appliquer_fichier(chemin, contenu) for chemin, contenu in fichiers]
        resume = explication or ("C'est fait, regarde les fichiers." if ecrits else
                                 "Pas de réponse cette fois-ci. Reformule ta demande.")
        note = f"\n(Fichiers écrits : {', '.join(ecrits)})" if ecrits else ""
        self.messages.append({"role": "assistant", "content": resume + note})
        self.app.ecrire(self.chat, resume, lambda: True, lambda: self.fin_reponse(ecrits))

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

    def fin_reponse(self, ecrits=()):
        for chemin in ecrits:
            etiquette = f"fichier{self.nb_liens}"
            self.nb_liens += 1
            self.chat.insert("end", "Fichier écrit : ", "sources")
            self.chat.insert("end", chemin + "\n", ("sources", "lien", etiquette))
            self.chat.tag_bind(etiquette, "<Button-1>", lambda e, c=chemin: self.activer_chemin(c))
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
        self.codex = None
        self.boutons_moteur = []
        self.ids_sessions = []

        # --- Boutons du haut (cachés au début) ---
        self.barre = tk.Frame(self, bg=GRIS_FOND)
        bouton_orange(self.barre, "Clé API", self.changer_cle).pack(side="left", padx=(0, 10))
        bouton_orange(self.barre, "Sauvegarder", self.sauvegarder).pack(side="left", padx=(0, 10))
        bouton_orange(self.barre, "Nouveau", self.nouveau).pack(side="left")

        # --- La conversation (cachée au début, modifiable) ---
        self.document = tk.Text(self, **style_zone())
        self.configurer_tags(self.document)

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
        self.choix = tk.StringVar(value=next(iter(self.moteurs)))
        self.choix.trace_add("write", self.maj_boutons_moteur)
        self.options = tk.Frame(self.zone_saisie, bg=GRIS_FOND)
        self.options.pack(fill="x", pady=(8, 0))
        self.creer_bouton_moteur(self.options).pack(side="left")

        # --- Menu de gauche + bouton ☰ (toujours par-dessus le reste) ---
        self.construire_menu_lateral()

        self.saisie.bind("<Return>", self.envoyer)
        self.saisie.bind("<Shift-Return>", self.saut_de_ligne)
        self.bind("<Control-s>", self.ctrl_s)
        self.protocol("WM_DELETE_WINDOW", self.quitter)

        self.centrer_saisie()
        self.saisie.focus_set()
        self.after(80, self.traiter_taches)

    # ---------- Outils ----------
    def configurer_tags(self, widget, taille=14):
        widget.tag_configure("question", font=(FAMILLE, taille, "bold"), spacing1=14 if taille >= 14 else 10)
        widget.tag_configure("reponse", spacing1=6, spacing3=4)
        widget.tag_configure("attente", font=(FAMILLE, taille, "italic"), spacing1=6)
        widget.tag_configure("sources", font=(FAMILLE, max(taille - 3, 9)), spacing1=2)
        widget.tag_configure("lien", underline=True)
        widget.tag_configure("curseur", foreground=ORANGE)
        widget.tag_bind("lien", "<Enter>", lambda e: widget.config(cursor="hand2"))
        widget.tag_bind("lien", "<Leave>", lambda e: widget.config(cursor="xterm"))

    def animer(self, cle, depart, fin, appliquer, apres=None, etapes=14, ms=12):
        """Anime une valeur en douceur (ralentit à la fin). Une nouvelle animation remplace l'ancienne."""
        self.annuler_animation(cle)

        def pas(i):
            t = 1 - (1 - i / etapes) ** 3
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
                suite()

        tour()

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

    # ---------- Menu de gauche ----------
    def construire_menu_lateral(self):
        m = self.menu_lateral = tk.Frame(self, bg=GRIS_MENU)
        m.place(x=self.menu_x, y=0, width=LARGEUR_MENU, relheight=1)
        tk.Frame(m, bg="#5e5e5e", width=2).place(relx=1, x=-2, y=0, relheight=1)
        bouton_orange(m, "+ Nouvelle conversation", self.nouveau).pack(fill="x", padx=14, pady=(70, 12))
        tk.Label(m, text="Conversations", bg=GRIS_MENU, fg=NOIR, anchor="w",
                 font=(FAMILLE, 10, "bold")).pack(fill="x", padx=16)
        bouton_orange(m, "Codex  </>", self.ouvrir_codex).pack(side="bottom", fill="x", padx=14, pady=14)
        self.liste_sessions = tk.Listbox(
            m, bg=GRIS_MENU, fg=NOIR, selectbackground=ORANGE, selectforeground=NOIR,
            font=(FAMILLE, 11), relief="flat", bd=0, highlightthickness=0, activestyle="none")
        self.liste_sessions.pack(fill="both", expand=True, padx=(8, 10), pady=6)
        self.liste_sessions.bind("<<ListboxSelect>>", self.sur_choix_session)
        self.liste_sessions.bind("<Button-3>", self.menu_session)

        self.bouton_menu = tk.Button(
            self, text="☰", command=self.basculer_menu, bg=ORANGE, fg=NOIR,
            activebackground=ORANGE_FONCE, activeforeground=NOIR, font=(FAMILLE, 16, "bold"),
            relief="flat", bd=0, highlightthickness=0, cursor="hand2")
        self.bouton_menu.place(x=15, y=14, width=46, height=38)

    def basculer_menu(self):
        self.menu_ouvert = not self.menu_ouvert
        if self.menu_ouvert:
            self.rafraichir_sessions()
            self.menu_lateral.lift()
            self.bouton_menu.lift()

        def appliquer(v):
            self.menu_x = int(v)
            self.menu_lateral.place_configure(x=self.menu_x)

        self.animer("menu", self.menu_x, 0 if self.menu_ouvert else -LARGEUR_MENU, appliquer, etapes=16)

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
        for m in self.messages:
            if m["role"] == "user":
                self.document.insert("end", m["content"] + "\n", "question")
            else:
                self.document.insert("end", m["content"] + "\n", "reponse")
                self.ajouter_schema_et_sources(m.get("etapes") or [],
                                               [tuple(s) for s in m.get("sources") or []])
        self.document.see("end")
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
        self.fermer_menu()

    def fermer_codex(self):
        if self.codex is not None:
            self.codex.place_forget()

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
            cle = lire_secret(FICHIER_CLE, "ANTHROPIC_API_KEY") or self.demander_cle()
            if not cle:
                return "break"

        self.saisie.delete("1.0", "end")
        self.document.insert("end", texte + "\n", "question")
        self.messages.append({"role": "user", "content": texte})
        self.question_en_cours = texte
        nom = "Claude" if moteur[0] == "claude" else moteur[1].removesuffix(":latest")
        self.montrer_attente(nom)
        self.occupe = True
        threading.Thread(target=self.travail, args=(moteur, cle, self.historique_api(), self.generation),
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
                texte, sources = appeler_claude(cle, historique, instructions_systeme(web=True))
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
            texte = texte or ("Voici le plan :" if etapes else
                              "Pas de réponse cette fois-ci. Reformule ta question.")
            self.messages.append({"role": "assistant", "content": texte, "etapes": etapes,
                                  "sources": [list(s) for s in sources]})
            self.sauver_session()
            # Le schéma et les sources arrivent une fois le texte fini d'écrire
            self.ecrire(self.document, texte, continuer,
                        lambda: self.fin_reponse(self.ajouter_schema_et_sources(etapes, sources)))
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
            "Clé API", "Colle ta clé API Claude (elle commence par sk-ant-) :", show="*", parent=self)
        if cle and cle.strip():
            enregistrer_secret(FICHIER_CLE, cle.strip())
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
        self.saisie.focus_set()
        self.fermer_menu()


if __name__ == "__main__":
    AppEcriture().mainloop()
