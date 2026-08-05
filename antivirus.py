"""Analyse d'un fichier reçu, AVANT qu'il n'entre où que ce soit.

POURQUOI CE MODULE. Les deux chemins d'upload du site — base de connaissance et
pièces jointes clients — validaient l'EXTENSION et rien d'autre. Un exécutable
renommé « rapport.pdf » passait ; un classeur porteur de macros aussi, puisque
« xlsm » figure dans la liste des extensions admises et qu'un xlsm EST par
définition un classeur à macros. La porte est donc écrite ici, une fois, et
appelée par tous les chemins : trois validations séparées divergent, et c'est
toujours la moins stricte qui sert d'entrée.

CE QUE CE MODULE EST, ET CE QU'IL N'EST PAS. Il enchaîne deux portes :

  1. UN ANTIVIRUS À SIGNATURES, si l'environnement en expose un. ClamAV est
     interrogé par socket (CLAMAV_HOST/CLAMAV_PORT, ou CLAMAV_SOCKET pour un
     socket UNIX). Sans configuration, cette porte est ABSENTE — pas
     silencieusement réussie.

  2. UNE INSPECTION STRUCTURELLE, toujours exécutée, même quand l'antivirus a
     laissé passer. Elle ne connaît aucune signature : elle vérifie que le
     fichier est ce qu'il prétend être et qu'il ne porte pas les constructions
     dont un document bureautique n'a pas besoin — macros, JavaScript, objets
     OLE, cibles externes, archives disproportionnées.

Le verdict dit TOUJOURS quelles portes ont réellement tourné. Écrire « analysé
par antivirus » quand seule l'inspection structurelle a eu lieu serait le pire
défaut possible dans ce module : celui qui rassure à tort.

AUCUNE DÉPENDANCE. Ni python-magic, ni olefile, ni bibliothèque d'analyse : le
conteneur n'en a pas, et une dépendance absente en production ferait échouer la
porte au lieu de la faire refuser. Tout ce qui suit est de la lecture d'octets.
"""
import io
import os
import re
import socket
import zipfile

VERSION = "2026-08-a"

# Taille au-delà de laquelle on refuse sans lire : un fichier plus gros que ce
# que le stockage accepte n'a aucune raison d'être inspecté.
MAX_OCTETS = int(os.environ.get("DEPOT_MAX_MB", "30")) * 1024 * 1024

# Les extensions admises au dépôt. Volontairement PLUS ÉTROITE que celle de la
# base de connaissance : les formats à macros (xlsm, pptm, docm) en sont exclus.
# Un client qui a besoin d'envoyer un classeur avec macros peut l'envoyer sans,
# ou l'accompagner d'un export ; l'inverse — accepter des macros et espérer les
# détecter — n'est pas une position tenable.
EXTENSIONS = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain",
    "md": "text/plain",
    "csv": "text/csv",
    "json": "application/json",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "dwg": "application/acad",
}

# Les formats à macros, nommés pour pouvoir REFUSER EN L'EXPLIQUANT. Un refus
# « type non supporté » sur un .xlsm laisse croire à une limitation technique ;
# c'est une décision de sécurité, et elle se dit.
EXTENSIONS_MACROS = {"xlsm", "xlsb", "pptm", "docm", "dotm", "xltm", "potm"}

# Les octets de tête qui identifient réellement un format. Une extension est une
# déclaration de l'expéditeur ; ceci est une constatation.
_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    # Les formats OOXML sont des archives ZIP : PK.. en tête.
    "docx": [b"PK\x03\x04", b"PK\x05\x06"],
    "xlsx": [b"PK\x03\x04", b"PK\x05\x06"],
    "pptx": [b"PK\x03\x04", b"PK\x05\x06"],
    "dwg": [b"AC10", b"AC1."],
}

# Les en-têtes qu'aucun document bureautique ne porte, et qui trahissent un
# exécutable ou un script déguisé.
_EXECUTABLES = [
    (b"MZ", "exécutable Windows (PE/DOS)"),
    (b"\x7fELF", "exécutable Linux (ELF)"),
    (b"\xca\xfe\xba\xbe", "binaire Mach-O ou classe Java"),
    (b"\xfe\xed\xfa", "binaire Mach-O"),
    (b"#!", "script à interpréteur (shebang)"),
    (b"\xd0\xcf\x11\xe0", "document OLE ancien format (doc/xls/ppt) — "
                          "conteneur de macros"),
    (b"Rar!", "archive RAR"),
    (b"7z\xbc\xaf", "archive 7-Zip"),
    (b"\x1f\x8b", "archive gzip"),
]

# La chaîne d'essai EICAR. Elle n'est pas un virus : c'est le fichier que tout
# antivirus doit signaler, et c'est ce qui rend cette porte DÉMONTRABLE. Une
# protection qu'on ne peut pas déclencher à volonté ne se vérifie pas.
_EICAR = (b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-"
          b"ANTIVIRUS-TEST-FILE!$H+H*")

# Constructions actives d'un PDF. Aucune n'est nécessaire à un document destiné
# à être lu ; toutes ont servi de vecteur.
_PDF_ACTIF = [
    (rb"/JavaScript", "JavaScript embarqué"),
    (rb"/JS\b", "JavaScript embarqué"),
    (rb"/OpenAction", "action automatique à l'ouverture"),
    (rb"/AA\b", "action automatique sur événement"),
    (rb"/Launch", "lancement d'un programme externe"),
    (rb"/EmbeddedFile", "fichier embarqué"),
    (rb"/RichMedia", "contenu multimédia actif"),
    (rb"/XFA\b", "formulaire XFA (moteur de script)"),
]

# Un ZIP dont le contenu décompressé dépasse ces bornes est refusé sans être
# ouvert davantage : c'est la parade aux archives en bombe.
ZIP_MAX_ENTREES = 3000
ZIP_MAX_DECOMPRESSE = 600 * 1024 * 1024
ZIP_RATIO_MAX = 250


class Refus(Exception):
    """Un fichier refusé. `motif` est destiné à l'utilisateur, `code` au journal."""

    def __init__(self, code, motif):
        super().__init__(motif)
        self.code = code
        self.motif = motif


def extension(nom):
    return (nom.rsplit(".", 1)[-1] if "." in (nom or "") else "").lower()


# ── Porte 1 : l'antivirus à signatures ──────────────────────────────────────

def clamav_configure():
    """L'environnement expose-t-il un ClamAV ? Aucun réglage par défaut : on ne
    devine pas une adresse, et un ClamAV « supposé présent » qui ne répond pas
    donnerait exactement la fausse assurance qu'on veut éviter."""
    return bool(os.environ.get("CLAMAV_HOST") or os.environ.get("CLAMAV_SOCKET"))


def _clamav_flux(data, delai=20.0):
    """Analyse par ClamAV en INSTREAM. Renvoie (verdict, detail).

    verdict : "propre", "infecte" ou "indisponible". La distinction entre les
    deux derniers est capitale : un antivirus injoignable ne dit pas qu'un
    fichier est sain, et le traiter comme tel serait une panne silencieuse.
    """
    sock_path = os.environ.get("CLAMAV_SOCKET")
    hote = os.environ.get("CLAMAV_HOST")
    port = int(os.environ.get("CLAMAV_PORT", "3310"))
    s = None
    try:
        if sock_path:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(delai)
            s.connect(sock_path)
        else:
            s = socket.create_connection((hote, port), timeout=delai)
        s.sendall(b"zINSTREAM\0")
        vue = memoryview(data)
        for i in range(0, len(vue), 8192):
            bloc = vue[i:i + 8192]
            s.sendall(len(bloc).to_bytes(4, "big") + bytes(bloc))
        s.sendall((0).to_bytes(4, "big"))
        rep = b""
        while b"\0" not in rep and len(rep) < 4096:
            morceau = s.recv(4096)
            if not morceau:
                break
            rep += morceau
        texte = rep.split(b"\0")[0].decode("utf-8", "replace").strip()
        if texte.endswith("OK"):
            return "propre", texte
        if "FOUND" in texte:
            return "infecte", texte.replace("stream: ", "").replace(" FOUND", "")
        return "indisponible", texte or "réponse illisible"
    except Exception as exc:
        return "indisponible", "%s: %s" % (type(exc).__name__, exc)
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


# ── Porte 2 : l'inspection structurelle ─────────────────────────────────────

def _verifier_entete(ext, data):
    """Le fichier est-il ce qu'il prétend être ?"""
    tete = data[:16]
    for motif, quoi in _EXECUTABLES:
        if tete.startswith(motif):
            raise Refus("entete_executable",
                        "Le contenu est un %s, quelle que soit l'extension "
                        "annoncée." % quoi)
    attendues = _SIGNATURES.get(ext)
    if not attendues:
        return                      # formats texte : contrôlés autrement
    for sig in attendues:
        if sig.endswith(b".") and tete.startswith(sig[:-1]):
            return
        if tete.startswith(sig):
            return
    raise Refus("entete_incoherent",
                "Le contenu ne correspond pas à l'extension « .%s » annoncée." % ext)


def _verifier_texte(data):
    """Un format texte doit se décoder et ne pas contenir d'octet nul."""
    if b"\x00" in data[:65536]:
        raise Refus("texte_binaire",
                    "Ce fichier est annoncé comme du texte mais contient des "
                    "octets binaires.")
    try:
        data[:65536].decode("utf-8")
    except UnicodeDecodeError:
        try:
            data[:65536].decode("latin-1")
        except Exception:
            raise Refus("texte_illisible", "Ce texte n'est pas décodable.")


def _verifier_pdf(data):
    trouve = []
    for motif, quoi in _PDF_ACTIF:
        if re.search(motif, data):
            trouve.append(quoi)
    if trouve:
        raise Refus("pdf_actif",
                    "Ce PDF contient du contenu actif (%s). Un document destiné "
                    "à être lu n'en a pas besoin ; réenregistrez-le en PDF "
                    "simple ou en PDF/A." % ", ".join(sorted(set(trouve))))


def _verifier_ooxml(data):
    """docx / xlsx / pptx : des archives ZIP, avec ce que cela suppose."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except Exception:
        raise Refus("archive_illisible",
                    "Ce document Office est illisible : son archive interne est "
                    "corrompue ou tronquée.")
    infos = z.infolist()
    if len(infos) > ZIP_MAX_ENTREES:
        raise Refus("archive_trop_d_entrees",
                    "Ce document contient %d éléments internes, bien au-delà de "
                    "ce qu'un document réel comporte." % len(infos))
    total = 0
    for i in infos:
        nom = i.filename.replace("\\", "/")
        if nom.startswith("/") or ".." in nom.split("/"):
            raise Refus("archive_chemin",
                        "Ce document contient un chemin interne anormal (« %s »)."
                        % i.filename[:60])
        total += i.file_size
        if i.compress_size > 0 and i.file_size / max(1, i.compress_size) > ZIP_RATIO_MAX:
            raise Refus("archive_ratio",
                        "Un élément interne se décompresse dans une proportion "
                        "anormale — signature d'une archive en bombe.")
    if total > ZIP_MAX_DECOMPRESSE:
        raise Refus("archive_volume",
                    "Ce document se décompresse en %d Mo, ce qui n'est pas "
                    "plausible." % (total // (1024 * 1024)))
    noms = [i.filename.lower() for i in infos]
    if any("vbaproject.bin" in n for n in noms):
        raise Refus("macro",
                    "Ce document contient des macros VBA. Elles ne sont pas "
                    "acceptées : enregistrez-le au format sans macros (.docx, "
                    ".xlsx, .pptx).")
    if any(re.search(r"embeddings/.*\.(bin|ole)$", n) for n in noms):
        raise Refus("objet_ole",
                    "Ce document contient un objet incorporé (OLE). Ces objets "
                    "peuvent embarquer un exécutable ; retirez-le ou fournissez "
                    "la pièce séparément.")
    # Les relations externes : une cible distante rapatriée à l'ouverture est un
    # canal de sortie autant qu'un vecteur d'entrée.
    for i in infos:
        if not i.filename.lower().endswith(".rels"):
            continue
        try:
            xml = z.read(i).decode("utf-8", "replace")
        except Exception:
            continue
        for m in re.finditer(r'Target="([^"]+)"[^>]*TargetMode="External"', xml):
            cible = m.group(1)
            if re.match(r"^(?:file|smb|ftp|jar|ms-msdt|mhtml|res)\b", cible, re.I) \
               or cible.startswith("\\\\"):
                raise Refus("lien_externe",
                            "Ce document pointe vers une ressource externe "
                            "inhabituelle (« %s »)." % cible[:60])


def _verifier_png_jpg(ext, data):
    """Une image ne doit pas cacher du script. On borne la recherche à un
    préfixe : lire un JPEG entier à la recherche de « <script » coûte cher et
    n'apporte rien, la charge utile étant en tête dans les cas connus."""
    tete = data[:8192].lower()
    for motif in (b"<script", b"<?php", b"<%", b"<!doctype html"):
        if motif in tete:
            raise Refus("image_polyglotte",
                        "Cette image contient du code interprétable en tête de "
                        "fichier.")


def inspecter(nom, data):
    """L'inspection structurelle seule. Lève Refus, ou renvoie l'extension."""
    if not data:
        raise Refus("vide", "Le fichier est vide.")
    if len(data) > MAX_OCTETS:
        raise Refus("trop_gros", "Le fichier dépasse %d Mo."
                    % (MAX_OCTETS // (1024 * 1024)))
    ext = extension(nom)
    if ext in EXTENSIONS_MACROS:
        raise Refus("format_macros",
                    "Le format « .%s » porte des macros par construction. Ce "
                    "n'est pas une limitation technique mais une décision de "
                    "sécurité : enregistrez le document au format sans macros."
                    % ext)
    if ext not in EXTENSIONS:
        raise Refus("type_non_supporte",
                    "Le format « .%s » n'est pas accepté au dépôt." % (ext or "?"))
    # EICAR AVANT tout le reste : c'est le contrôle qui rend la chaîne
    # démontrable, et il doit se déclencher quel que soit le format annoncé.
    if _EICAR in data[:4096]:
        raise Refus("eicar",
                    "Fichier d'essai EICAR détecté. C'est le comportement "
                    "attendu : la chaîne d'analyse fonctionne.")
    _verifier_entete(ext, data)
    if ext in ("txt", "md", "csv", "json"):
        _verifier_texte(data)
    elif ext == "pdf":
        _verifier_pdf(data)
    elif ext in ("docx", "xlsx", "pptx"):
        _verifier_ooxml(data)
    elif ext in ("png", "jpg", "jpeg"):
        _verifier_png_jpg(ext, data)
    return ext


def analyser(nom, data):
    """Les deux portes, dans l'ordre. Renvoie un verdict complet.

    Le verdict porte TOUJOURS `portes`, la liste de ce qui a réellement tourné.
    Une interface qui écrirait « analysé par antivirus » sans le consulter
    rassurerait à tort — c'est le défaut le plus grave qu'un tel module puisse
    avoir, parce qu'il ne se voit jamais.
    """
    portes, alertes = [], []
    # ── Porte 1 ──
    if clamav_configure():
        verdict, detail = _clamav_flux(data)
        if verdict == "infecte":
            return {"accepte": False, "code": "antivirus",
                    "motif": "Analyse antivirus : menace détectée (%s)." % detail,
                    "portes": ["antivirus"], "antivirus": "infecte",
                    "signature": detail, "version": VERSION}
        if verdict == "propre":
            portes.append("antivirus")
        else:
            # Injoignable : on ne prétend pas avoir analysé. Le dépôt reste
            # possible parce que l'inspection structurelle, elle, a tourné —
            # mais le verdict le dit, et le journal le garde.
            alertes.append("Antivirus configuré mais injoignable (%s) : seule "
                           "l'inspection structurelle a été appliquée." % detail)
    else:
        alertes.append("Aucun antivirus à signatures n'est configuré sur ce "
                       "serveur : l'analyse porte sur la structure du fichier, "
                       "pas sur des signatures de menaces connues.")
    # ── Porte 2 ──
    try:
        ext = inspecter(nom, data)
    except Refus as r:
        return {"accepte": False, "code": r.code, "motif": r.motif,
                "portes": portes + ["structure"], "version": VERSION,
                "alertes": alertes}
    portes.append("structure")
    return {"accepte": True, "extension": ext,
            "type_mime": EXTENSIONS[ext],
            "portes": portes, "alertes": alertes,
            "antivirus": "propre" if "antivirus" in portes else "absent",
            "version": VERSION}


def etat():
    """Ce que vaut la chaîne d'analyse en ce moment. Exposé pour l'affichage et
    le contrôle de santé : l'utilisateur qui dépose un document a le droit de
    savoir ce qui sera réellement appliqué."""
    conf = clamav_configure()
    joignable = None
    if conf:
        joignable = _clamav_flux(b"conseilprev-sonde")[0] != "indisponible"
    return {
        "version": VERSION,
        "antivirus_configure": conf,
        "antivirus_joignable": joignable,
        "inspection_structurelle": True,
        "extensions_admises": sorted(EXTENSIONS),
        "formats_macros_refuses": sorted(EXTENSIONS_MACROS),
        "taille_max_mo": MAX_OCTETS // (1024 * 1024),
        "resume": ("Antivirus à signatures + inspection structurelle."
                   if conf and joignable else
                   ("Antivirus configuré mais INJOIGNABLE — seule l'inspection "
                    "structurelle s'applique." if conf else
                    "Inspection structurelle seule : aucun antivirus à "
                    "signatures n'est configuré sur ce serveur.")),
    }
