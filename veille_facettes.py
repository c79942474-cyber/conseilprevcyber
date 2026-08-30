# -*- coding: utf-8 -*-
"""Les six axes par lesquels on cherche dans la veille.

CE QUE CE MODULE REMPLACE, ET POURQUOI IL NE L'ÉTEND PAS. La page portait huit
règles de classement écrites dans son propre script : « Microsoft & Windows »,
« Linux & Unix », « Bases de données », « Mobile ». Ce sont les facettes d'un
flux de VULNÉRABILITÉS — elles disent quel produit est touché. Elles n'ont
aucun sens devant un communiqué de la Commission européenne ou une révision de
norme ISO. Une veille réglementaire mondiale ne se range pas par système
d'exploitation.

DEUX DES SIX AXES EXISTENT DÉJÀ DANS LA MAISON, ET ON NE LES RÉÉCRIT PAS.
Les thèmes et les standards viennent de `rag_store.THEME_FAMILLES` — le même
vocabulaire que la base documentaire, celui dans lequel vos livrables sont
classés. Les secteurs viennent de la page `secteurs.html`. Inventer ici un
second jeu de noms donnerait deux vocabulaires pour une seule maison, et c'est
l'exemplaire qu'on oublie de corriger qui reste en place.

LE CLASSEMENT SE FAIT À LA LECTURE, PAS À L'INGESTION. Une taxonomie par motifs
se corrige tous les mois ; rangée en base, chaque correction demanderait de
reprendre tout le fonds — donc ne se ferait pas. Le prix est de quelques
centaines d'expressions régulières sur soixante éléments, une fois par
affichage.

CE QUI N'EST PAS RECONNU RESTE VISIBLE. Aucun élément n'est écarté faute
d'être classé : les facettes FILTRENT quand on les demande, elles ne trient pas
en amont. Un communiqué que nos motifs ne savent pas lire est exactement celui
qu'il ne faut pas cacher.
"""
import re

import rag_store
import veille_sources

VERSION = "2026-08-a"


def _r(motif):
    return re.compile(motif, re.I)


# ── STANDARDS ──────────────────────────────────────────────────────────────
# Le nom rendu est CELUI DE `rag_store.THEMES`, à la lettre. Une règle le
# vérifie au chargement : un standard qui n'y figurerait pas créerait un
# vocabulaire parallèle, et un filtre de la veille ne désignerait plus rien
# dans la base documentaire.
STANDARDS = [
    ("IEC 62443", _r(r"62443|isa[- ]?99")),
    ("ISO 27001 / 27002", _r(r"27001|27002|27019|iso[/ ]?iec 27")),
    ("NIST CSF / SP 800-82", _r(r"\bcsf\b|sp ?800|cybersecurity framework")),
    ("NIS2", _r(r"\bnis ?2\b|nis2|directive nis")),
    ("DORA", _r(r"\bdora\b|digital operational resilience")),
    ("RGPD", _r(r"\brgpd\b|\bgdpr\b")),
    ("AI Act", _r(r"ai act|règlement (sur l'|européen sur l')?ia\b|artificial intelligence act")),
    ("Cyber Resilience Act", _r(r"cyber resilience act|\bcra\b")),
    ("Sûreté fonctionnelle (IEC 61508/61511)", _r(r"61508|61511|\bsil ?[1-4]\b|functional safety")),
    ("Normes IEC", _r(r"\biec ?6(0870|1850|2351)\b|\bcei ?6")),
    ("ISO Standards", _r(r"\biso[/ ]?(iec )?\d{4,5}\b")),
    ("Data center / Normes (EN 50600, ISO/IEC 30134, ASHRAE)",
     _r(r"50600|30134|ashrae")),
    ("Data center / Réglementation UE (EED, taxonomie, CSRD)",
     _r(r"\beed\b|energy efficiency directive|\bcsrd\b|taxonomie|taxonomy")),
]

# ── THÈMES ─────────────────────────────────────────────────────────────────
THEMES = [
    ("Automates, SCADA & DCS", _r(r"scada|automate|\bplc\b|\bics\b|\bdcs\b|modbus|profinet|opc[ -]?ua|codesys|simatic")),
    ("Sécurité réseau & pare-feu", _r(r"pare-?feu|firewall|\bvpn\b|passerelle|routeur|router")),
    ("Gestion des correctifs", _r(r"correctif|patch|mise à jour de sécurité|security update|hotfix")),
    ("Réponse à incident", _r(r"incident|rançongiciel|ransomware|compromission|breach|attaque|attack")),
    ("Supervision & détection", _r(r"détection|detection|\bsoc\b|\bsiem\b|surveillance|monitoring")),
    ("Gestion des accès & identités", _r(r"identité|identity|authentification|authentication|\bmfa\b|\bsso\b|privilège")),
    ("Accès distant & télémaintenance", _r(r"accès distant|remote access|télémaintenance|\brdp\b")),
    ("Cryptographie & PKI", _r(r"cryptograph|chiffrement|encryption|\bpki\b|post-?quantique|post-?quantum")),
    ("Analyse de risques", _r(r"analyse de risque|risk assessment|ebios|menace|threat landscape")),
    ("Continuité & résilience (PRA/PCA)", _r(r"continuité|résilience|resilience|\bpra\b|\bpca\b|disaster recovery")),
    ("Gouvernance & CSMS", _r(r"gouvernance|governance|\bcsms\b|politique de sécurité")),
    ("Conformité & audit", _r(r"conformité|compliance|\baudit\b|certification|sanction|amende|fine\b")),
    ("Gestion des prestataires", _r(r"sous-?traitan|supply chain|chaîne d'approvisionnement|fournisseur|third[- ]party")),
    ("IIoT & objets connectés", _r(r"\biiot\b|\biot\b|objets connectés|connected device")),
    ("Inventaire & cartographie", _r(r"inventaire|cartographie|asset inventory|\bsbom\b")),
    ("Data center / Énergie & électricité", _r(r"électricité|electricity|réseau électrique|\bgrid\b|mégawatt|megawatt|\bmw\b|raccordement")),
    ("Data center / Raccordement & production sur site", _r(r"raccordement|grid connection|on-?site generation|production sur site|\bsmr\b|nuclear power")),
    ("Data center / Thermique & refroidissement", _r(r"refroidissement|cooling|thermique|liquid cooling|immersion")),
    ("Data center / Eau & stress hydrique", _r(r"\beau\b|water|hydrique|\bwue\b")),
    ("Data center / Carbone & analyse de cycle de vie", _r(r"carbone|carbon|\bges\b|\bacv\b|life ?cycle|net[- ]zero|bas carbone|low[- ]carbon")),
    ("Data center / Efficacité & indicateurs (PUE, WUE, CUE, ERE)", _r(r"\bpue\b|\bwue\b|\bcue\b|\bere\b|efficacité énergétique|energy efficiency")),
    ("Data center / Chaleur fatale & réseaux de chaleur", _r(r"chaleur fatale|waste heat|réseau de chaleur|district heating")),
]

# ── SECTEURS ───────────────────────────────────────────────────────────────
# Les neuf secteurs de la maison, tels que `secteurs.html` les nomme. Une règle
# compare les deux listes : un nom écrit à deux endroits finit par diverger, et
# la divergence serait muette — un filtre qui ne rend jamais rien.
SECTEURS = [
    ("Énergie & utilities", _r(r"énergie|energy|électric|electric|\bgrid\b|utility|utilities|réseau de distribution|power")),
    ("Eau & assainissement", _r(r"\beau\b|water|assainissement|wastewater|potable")),
    ("Manufacturing & usine connectée", _r(r"manufactur|usine|factory|industrie 4|production line|\boem\b")),
    ("Agroalimentaire", _r(r"agroaliment|food|agri|agroindustr")),
    ("Chimie & pharma", _r(r"chimie|chemical|pharma|seveso|biotech")),
    ("Transport & logistique", _r(r"transport|ferroviaire|railway|maritime|port\b|aéroport|airport|logistique|logistics")),
    ("Assurance & services financiers", _r(r"banque|bank|assurance|insurance|financ|\beba\b|\besma\b|\bdora\b")),
    ("Nucléaire", _r(r"nucléaire|nuclear|\biaea\b|\basn\b|réacteur|reactor")),
    ("Aerospace & défense", _r(r"aéronautique|aerospace|défense|defence|defense|spatial|\bsatellite\b")),
]

# ── ENTREPRISES ────────────────────────────────────────────────────────────
# Le seul axe réellement nouveau. La moitié venait déjà des motifs de la page :
# ils sont repris, pas réinventés.
ENTREPRISES = [
    ("Siemens", _r(r"siemens|simatic")),
    ("Schneider Electric", _r(r"schneider")),
    ("Rockwell Automation", _r(r"rockwell|allen[- ]bradley")),
    ("ABB", _r(r"\babb\b")),
    ("Honeywell", _r(r"honeywell")),
    ("Emerson", _r(r"emerson")),
    ("Yokogawa", _r(r"yokogawa")),
    ("Mitsubishi Electric", _r(r"mitsubishi")),
    ("Omron", _r(r"omron")),
    ("Phoenix Contact", _r(r"phoenix contact")),
    ("Moxa", _r(r"\bmoxa\b")),
    ("Hirschmann", _r(r"hirschmann")),
    ("WAGO", _r(r"\bwago\b")),
    ("Fortinet", _r(r"fortinet|fortios|fortigate|fortimanager")),
    ("Cisco", _r(r"\bcisco\b")),
    ("Palo Alto Networks", _r(r"palo ?alto")),
    ("Ivanti", _r(r"ivanti")),
    ("Citrix", _r(r"citrix|netscaler")),
    ("Microsoft", _r(r"microsoft|windows|azure|exchange")),
    ("VMware / Broadcom", _r(r"vmware|vcenter|\besxi\b|broadcom")),
    ("Oracle", _r(r"\boracle\b")),
    ("NVIDIA", _r(r"nvidia")),
    ("Google", _r(r"\bgoogle\b|alphabet")),
    ("Amazon Web Services", _r(r"\baws\b|amazon web")),
    ("Meta", _r(r"\bmeta\b(?! ?donnée)")),
    ("Equinix", _r(r"equinix")),
    ("Digital Realty", _r(r"digital realty|interxion")),
    ("Vertiv", _r(r"vertiv")),
    ("Eaton", _r(r"\beaton\b")),
    ("Legrand", _r(r"legrand")),
    ("OVHcloud", _r(r"ovhcloud|\bovh\b")),
    ("Scaleway", _r(r"scaleway|\bfree pro\b")),
    ("DATA4", _r(r"\bdata4\b")),
]

# ── ACTUALITÉ RÉGLEMENTAIRE ────────────────────────────────────────────────
# Un axe BOOLÉEN, et il se fonde d'abord sur la NATURE DE L'ÉMETTEUR — fait
# déclaré — avant de regarder le texte. Un communiqué de la CNIL est
# réglementaire parce qu'il vient de la CNIL, pas parce qu'il contient un mot.
_MOTIFS_REGLEMENTAIRES = _r(
    r"règlement|reglement|directive|décret|decret|arrêté|arrete|loi\b|"
    r"transposition|consultation publique|ligne[s]? directrice|guideline|"
    r"regulation|\bact\b|amendement|amendment|entrée en vigueur|"
    r"entry into force|norme|standard|révision|revision|publication de la norme|"
    r"sanction|amende|\bfine\b|mise en demeure|délibération|deliberation")

_NATURES_REGLEMENTAIRES = ("officiel", "normalisation")

AXES = ("themes", "standards", "secteurs", "entreprises", "pays", "reglementaire")


def _trouver(table, texte):
    return [nom for nom, motif in table if motif.search(texte)]


def classer(item, source=None):
    """Les facettes d'un élément. Plusieurs valeurs par axe, aucune forcée.

    Un élément peut relever de trois thèmes et d'aucun secteur — c'est le cas
    ordinaire, et forcer une valeur par axe fabriquerait un classement faux
    pour donner l'impression d'un classement complet.
    """
    if source is None:
        source = veille_sources.source(item.get("source") or "")
    texte = "%s %s" % (item.get("title") or "", item.get("resume") or "")
    facettes = {
        "themes": _trouver(THEMES, texte),
        "standards": _trouver(STANDARDS, texte),
        "secteurs": _trouver(SECTEURS, texte),
        "entreprises": _trouver(ENTREPRISES, texte),
        # LE PAYS VIENT DE L'ÉMETTEUR. Un titre qui cite le Japon ne rend pas
        # japonaise une publication de la Commission : le pays est un fait
        # déclaré par le catalogue, jamais une déduction du texte.
        "pays": source["pays"] if source else None,
        "reglementaire": bool(
            (source and source["nature"] in _NATURES_REGLEMENTAIRES)
            or _MOTIFS_REGLEMENTAIRES.search(texte)),
    }
    return facettes


def enrichir(items):
    """Chaque élément reçoit ses facettes, son émetteur et le libellé de lien."""
    sortie = []
    for it in items:
        s = veille_sources.source(it.get("source") or "")
        d = dict(it)
        d["facettes"] = classer(it, s)
        d["emetteur"] = s["nom"] if s else (it.get("source") or "Source")
        d["domaine"] = s["domaine"] if s else None
        d["nature"] = s["nature"] if s else None
        d["lien_libelle"] = (veille_sources.NATURES[s["nature"]]["libelle"]
                             if s else "Source")
        sortie.append(d)
    return sortie


def facettes(items):
    """Les valeurs présentes par axe, avec leurs effectifs.

    On ne rend QUE ce qui est présent : proposer au filtre un choix qui ne
    donnerait aucun résultat fait douter de la page, pas du choix.
    """
    comptes = {"themes": {}, "standards": {}, "secteurs": {},
               "entreprises": {}, "pays": {}, "domaines": {}}
    reglementaires = 0
    for it in items:
        f = it.get("facettes") or {}
        for axe in ("themes", "standards", "secteurs", "entreprises"):
            for v in f.get(axe) or []:
                comptes[axe][v] = comptes[axe].get(v, 0) + 1
        if f.get("pays"):
            comptes["pays"][f["pays"]] = comptes["pays"].get(f["pays"], 0) + 1
        if it.get("domaine"):
            comptes["domaines"][it["domaine"]] = comptes["domaines"].get(it["domaine"], 0) + 1
        if f.get("reglementaire"):
            reglementaires += 1
    ordonne = {axe: [{"valeur": v, "n": n}
                     for v, n in sorted(d.items(), key=lambda x: (-x[1], x[0]))]
               for axe, d in comptes.items()}
    ordonne["reglementaire"] = reglementaires
    ordonne["libelles_pays"] = veille_sources.PAYS
    ordonne["libelles_domaines"] = veille_sources.DOMAINES
    return ordonne


def glossaire():
    return {
        "facette": "un axe de recherche : thème, standard, secteur, entreprise, "
                   "pays, actualité réglementaire",
        "pays": "celui de l'ÉMETTEUR, jamais celui que le texte évoque",
        "reglementaire": "l'élément vient d'un régulateur ou d'un organisme de "
                         "normalisation, ou son texte porte un acte normatif",
        "non classé": "un élément dont aucun motif ne reconnaît rien reste "
                      "affiché : les facettes filtrent, elles ne trient pas",
    }


def referentiel():
    return {"version": VERSION, "axes": AXES,
            "themes": len(THEMES), "standards": len(STANDARDS),
            "secteurs": [n for n, _ in SECTEURS],
            "entreprises": len(ENTREPRISES)}


def _verifier():
    fautes = []
    for table, nom in ((THEMES, "thème"), (STANDARDS, "standard")):
        for valeur, _motif in table:
            if valeur not in rag_store.THEMES:
                fautes.append(
                    "%s « %s » absent de rag_store.THEMES : la veille et la "
                    "base documentaire parleraient deux langues" % (nom, valeur))
    for table, nom in ((THEMES, "thème"), (STANDARDS, "standard"),
                       (SECTEURS, "secteur"), (ENTREPRISES, "entreprise")):
        vus = set()
        for valeur, _motif in table:
            if valeur in vus:
                fautes.append("%s en double : %s" % (nom, valeur))
            vus.add(valeur)
    for nature in _NATURES_REGLEMENTAIRES:
        if nature not in veille_sources.NATURES:
            fautes.append("nature réglementaire inconnue du catalogue : %s" % nature)
    return fautes


_FAUTES = _verifier()
if _FAUTES:                                              # pragma: no cover
    raise RuntimeError("veille_facettes : vocabulaire incohérent — "
                       + " ; ".join(_FAUTES))
