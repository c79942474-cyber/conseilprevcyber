# -*- coding: utf-8 -*-
"""Ce que la veille lit, et si elle le lit vraiment.

CE QUE CE MODULE REMPLACE. La veille lisait DEUX flux CERT-FR, nommés dans une
liste de deux paires au milieu du collecteur. Passer à l'échelle mondiale —
cyber industrielle, gouvernance de l'IA, GRC et centres de données — ce n'est
pas rallonger cette liste : c'est admettre qu'un catalogue de sources est une
DONNÉE, qui se corrige sans toucher au code, et qui doit dire elle-même si elle
tient ses promesses.

UNE SOURCE QU'ON NE PEUT PAS JOINDRE EST UNE INTENTION, PAS UNE SOURCE. Les
adresses ci-dessous ont été écrites hors ligne : seules les deux du CERT-FR ont
été éprouvées en production, et le champ `eprouve` le dit sans détour pour
chacune. Les autres seront justes ou fausses, et c'est le premier passage en
production qui tranchera. On ne fait donc pas semblant : chaque flux porte un
état, et ce qui n'a JAMAIS répondu se distingue de ce qui a CESSÉ de répondre —
la première situation désigne une adresse fautive, la seconde une panne. Les
confondre enverrait corriger ce qui marche.

CE QU'UN FLUX MUET COÛTE, ET POURQUOI IL FAUT LE VOIR. Ni une adresse fausse ni
un format mal lu ne lèvent d'exception : le lecteur rend une liste vide, la
collecte continue, et la page affiche simplement moins de choses. Une veille
amputée de sa moitié américaine ressemble à une veille qui va bien. C'est
précisément la panne que ce module rend visible.
"""
import threading
import time

VERSION = "2026-08-a"

# ── LES AXES DÉCLARÉS ──────────────────────────────────────────────────────
# Le pays est celui de l'ÉMETTEUR, et c'est un fait. Il ne se devine jamais du
# texte : un communiqué de la Commission qui cite le Japon reste européen, et
# une facette de filtre bâtie sur une supposition trompe plus qu'elle n'aide.
PAYS = {
    "FR": "France",
    "US": "États-Unis",
    "UK": "Royaume-Uni",
    "UE": "Union européenne",
    "monde": "International",
}

DOMAINES = {
    "cyber_industriel": "Cybersécurité industrielle (OT/ICS)",
    "ia_gouvernance": "Gouvernance de l'IA",
    "grc_normes": "GRC, normes & standards",
    "centres_donnees": "Centres de données, énergie & bas carbone",
}

# La nature commande deux choses : le libellé du lien, et surtout CE QU'ON A LE
# DROIT DE REPRENDRE. D'une source officielle on peut récupérer le texte
# intégral d'un bulletin ; d'un article de presse, jamais — titre, lien et
# chapeau du flux, ce que l'éditeur y met précisément pour être repris.
NATURES = {
    "officiel": {"libelle": "Publication officielle", "texte_integral": True},
    "normalisation": {"libelle": "Organisme de normalisation", "texte_integral": True},
    "organisme": {"libelle": "Publication d'organisme", "texte_integral": False},
    "presse_specialisee": {"libelle": "Article", "texte_integral": False},
}


def _s(cle, nom, url, pays, domaine, nature, eprouve=False):
    return {"cle": cle, "nom": nom, "url": url, "pays": pays,
            "domaine": domaine, "nature": nature, "eprouve": eprouve}


SOURCES = [
    # ── Cybersécurité industrielle ────────────────────────────────────────
    _s("certfr_alerte", "CERT-FR — alertes", "https://www.cert.ssi.gouv.fr/alerte/feed/",
       "FR", "cyber_industriel", "officiel", eprouve=True),
    _s("certfr_avis", "CERT-FR — avis", "https://www.cert.ssi.gouv.fr/avis/feed/",
       "FR", "cyber_industriel", "officiel", eprouve=True),
    _s("anssi", "ANSSI — actualités", "https://cyber.gouv.fr/actualites/feed",
       "FR", "cyber_industriel", "officiel"),
    _s("cisa_avis", "CISA — avis de sécurité", "https://www.cisa.gov/cybersecurity-advisories/all.xml",
       "US", "cyber_industriel", "officiel"),
    _s("cisa_ics", "CISA — avis systèmes industriels", "https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml",
       "US", "cyber_industriel", "officiel"),
    _s("ncsc_uk", "NCSC — Royaume-Uni", "https://www.ncsc.gov.uk/api/1/services/v1/news-rss-feed.xml",
       "UK", "cyber_industriel", "officiel"),
    _s("enisa", "ENISA — agence européenne", "https://www.enisa.europa.eu/media/news-items/news-wire/RSS",
       "UE", "cyber_industriel", "officiel"),
    _s("industrial_cyber", "Industrial Cyber", "https://industrialcyber.co/feed/",
       "monde", "cyber_industriel", "presse_specialisee"),
    _s("securityweek_ics", "SecurityWeek — ICS/OT", "https://www.securityweek.com/category/ics-ot/feed/",
       "US", "cyber_industriel", "presse_specialisee"),
    _s("the_record", "The Record", "https://therecord.media/feed",
       "US", "cyber_industriel", "presse_specialisee"),

    # ── Gouvernance de l'IA ───────────────────────────────────────────────
    _s("cnil", "CNIL — actualités", "https://www.cnil.fr/fr/rss.xml",
       "FR", "ia_gouvernance", "officiel"),
    _s("ec_numerique", "Commission européenne — stratégie numérique",
       "https://digital-strategy.ec.europa.eu/en/rss.xml",
       "UE", "ia_gouvernance", "officiel"),
    _s("nist", "NIST — actualités", "https://www.nist.gov/news-events/news/rss.xml",
       "US", "ia_gouvernance", "officiel"),
    _s("ico_uk", "ICO — Royaume-Uni", "https://ico.org.uk/rss/news-and-blogs/",
       "UK", "ia_gouvernance", "officiel"),
    _s("oecd_ai", "OCDE.AI", "https://oecd.ai/en/rss",
       "monde", "ia_gouvernance", "organisme"),
    _s("iapp", "IAPP — gouvernance des données et de l'IA", "https://iapp.org/news/rss",
       "monde", "ia_gouvernance", "presse_specialisee"),

    # ── GRC, normes & standards ───────────────────────────────────────────
    _s("iso", "ISO — actualités", "https://www.iso.org/contents/news.rss",
       "monde", "grc_normes", "normalisation"),
    _s("iec", "IEC — actualités", "https://www.iec.ch/rss/news",
       "monde", "grc_normes", "normalisation"),
    _s("nist_csrc", "NIST CSRC — publications", "https://csrc.nist.gov/Rss/Publications",
       "US", "grc_normes", "normalisation"),
    _s("eba", "EBA — résilience opérationnelle (DORA)", "https://www.eba.europa.eu/rss.xml",
       "UE", "grc_normes", "officiel"),
    _s("esma", "ESMA", "https://www.esma.europa.eu/rss.xml",
       "UE", "grc_normes", "officiel"),
    _s("edpb", "CEPD — comité européen de la protection des données",
       "https://www.edpb.europa.eu/rss.xml", "UE", "grc_normes", "officiel"),

    # ── Centres de données, énergie, bas carbone, innovation ──────────────
    _s("dcd", "DataCenterDynamics", "https://www.datacenterdynamics.com/rss/",
       "monde", "centres_donnees", "presse_specialisee"),
    _s("dcf", "Data Center Frontier", "https://www.datacenterfrontier.com/rss",
       "US", "centres_donnees", "presse_specialisee"),
    _s("dck", "Data Center Knowledge", "https://www.datacenterknowledge.com/rss.xml",
       "monde", "centres_donnees", "presse_specialisee"),
    _s("uptime", "Uptime Institute", "https://journal.uptimeinstitute.com/feed/",
       "monde", "centres_donnees", "organisme"),
    _s("iea", "AIE — Agence internationale de l'énergie", "https://www.iea.org/rss/news",
       "monde", "centres_donnees", "officiel"),
    _s("cre", "CRE — régulation de l'énergie", "https://www.cre.fr/rss",
       "FR", "centres_donnees", "officiel"),
    _s("ademe", "ADEME — presse", "https://presse.ademe.fr/feed",
       "FR", "centres_donnees", "officiel"),
    _s("rte", "RTE — réseau de transport d'électricité", "https://www.rte-france.com/rss",
       "FR", "centres_donnees", "officiel"),
    _s("green_software", "Green Software Foundation", "https://greensoftware.foundation/rss.xml",
       "monde", "centres_donnees", "organisme"),
    _s("carbon_brief", "Carbon Brief", "https://www.carbonbrief.org/feed",
       "UK", "centres_donnees", "presse_specialisee"),

    # ── La filière française des centres de données ───────────────────────
    # Elle manquait, et c'est elle qui couvre le mieux ce qui se décide ICI :
    # implantations, raccordements, investissements européens dans le calcul
    # pour l'IA. Les titres anglophones disent ce que font les hyperscalers ;
    # ceux-ci disent ce que fait le territoire.
    _s("dcmag", "DCmag", "https://dcmag.fr/feed/",
       "FR", "centres_donnees", "presse_specialisee"),
    _s("lemagit_dc", "LeMagIT — datacenter", "https://www.lemagit.fr/rss/Datacenter.html",
       "FR", "centres_donnees", "presse_specialisee"),
    _s("lmi_dc", "Le Monde Informatique — datacenter",
       "https://www.lemondeinformatique.fr/flux-rss/thematique/datacenter/rss.xml",
       "FR", "centres_donnees", "presse_specialisee"),
    # France Datacenter est l'association professionnelle de la filière : ses
    # publications sont celles d'un organisme, pas d'une rédaction. La nature
    # commande le libellé du lien ET le droit de reprise.
    _s("france_datacenter", "France Datacenter", "https://francedatacenter.com/feed/",
       "FR", "centres_donnees", "organisme"),
]

_PAR_CLE = {s["cle"]: s for s in SOURCES}


def source(cle):
    """La fiche d'un flux, ou None. Un élément dont la source a disparu du
    catalogue reste AFFICHABLE : on ne fait pas disparaître de la page ce qui a
    été collecté hier parce qu'on a renommé une clé aujourd'hui."""
    return _PAR_CLE.get(cle)


def sources(domaine=None, pays=None):
    return [s for s in SOURCES
            if (domaine is None or s["domaine"] == domaine)
            and (pays is None or s["pays"] == pays)]


def texte_integral_permis(cle):
    """Peut-on récupérer le corps de la publication, ou seulement son chapeau ?

    C'EST UNE LIMITE DE DROIT, PAS DE TECHNIQUE. Rien n'empêche de télécharger
    un article de presse ; ce qui l'interdit, c'est qu'en reprendre le corps
    n'est plus de l'agrégation. Le flux publie un chapeau — l'éditeur l'y met
    pour être repris —, et c'est ce chapeau qu'on affiche.
    """
    s = _PAR_CLE.get(cle)
    return bool(s and NATURES[s["nature"]]["texte_integral"])


# ── L'ÉTAT DE CHAQUE FLUX ──────────────────────────────────────────────────
# Sur le modèle du disjoncteur par pair de `rag_federe` : un état par source,
# tenu en mémoire du processus. Il n'a pas à survivre au redémarrage — ce qu'on
# veut savoir, c'est ce que les derniers passages ont donné.
MUET_APRES = 2          # passages consécutifs sans le moindre élément

_etats = {}
_verrou = threading.Lock()


def _etat_de(cle):
    return _etats.setdefault(cle, {
        "dernier_essai": 0.0, "dernier_succes": 0.0, "elements": None,
        "passages_vides": 0, "echecs": 0, "erreur": ""})


def noter_succes(cle, elements):
    """Un passage qui a abouti — même s'il n'a rien rapporté.

    ZÉRO ÉLÉMENT N'EST PAS UNE ERREUR, et c'est bien le problème : le flux a
    répondu, le lecteur n'a rien su en tirer, et rien ne lève. C'est le cas
    d'une adresse qui rend une page d'accueil au lieu d'un flux, et celui d'un
    flux Atom lu par un lecteur qui ne connaît que RSS.
    """
    with _verrou:
        e = _etat_de(cle)
        e["dernier_essai"] = time.time()
        e["elements"] = int(elements)
        e["echecs"] = 0
        e["erreur"] = ""
        if elements:
            e["dernier_succes"] = time.time()
            e["passages_vides"] = 0
        else:
            e["passages_vides"] += 1


def noter_echec(cle, erreur, a_repondu=False):
    """Un passage qui n'a rien pu tirer de la source.

    `a_repondu` DISTINGUE DEUX ÉCHECS QUE LE COMPTE NE DOIT PAS CONFONDRE.
    Quand l'adresse n'a pas répondu du tout — 404, 403, coupure réseau — on n'a
    RIEN compté, et `elements` doit rester None : c'est l'absence de mesure.
    Quand elle a répondu autre chose qu'un flux, on a bel et bien compté, et le
    compte est ZÉRO. Écrire None dans le second cas ferait dire au tableau
    « on ne sait pas » là où l'on sait parfaitement — et c'est une règle
    existante qui l'a relevé, à juste titre, sur une première version de ce
    correctif qui laissait le compte à None dans les deux cas.
    """
    with _verrou:
        e = _etat_de(cle)
        e["dernier_essai"] = time.time()
        e["echecs"] += 1
        e["erreur"] = str(erreur)[:200]
        if a_repondu:
            e["elements"] = 0
            e["passages_vides"] += 1


def etat():
    """Ce que chaque flux a donné — pour la console d'administration.

    LA DISTINCTION QUI COMPTE : « jamais joint » n'est pas « devenu muet ». Le
    premier désigne une adresse à corriger, le second une panne à attendre. Un
    tableau qui les confondrait ferait rechercher un défaut de réseau sur une
    URL fautive.
    """
    with _verrou:
        lignes = []
        for s in SOURCES:
            e = dict(_etat_de(s["cle"]))
            if e["dernier_succes"]:
                sante = "muet" if e["passages_vides"] >= MUET_APRES else "ok"
            elif e["dernier_essai"]:
                sante = "jamais_joint"
            else:
                sante = "pas_encore_essaye"
            lignes.append({
                "cle": s["cle"], "nom": s["nom"], "pays": s["pays"],
                "domaine": s["domaine"], "nature": s["nature"],
                "eprouve": s["eprouve"], "sante": sante,
                "elements": e["elements"], "echecs": e["echecs"],
                "erreur": e["erreur"],
                "vus_il_y_a_s": (int(time.time() - e["dernier_succes"])
                                 if e["dernier_succes"] else None)})
    return {"version": VERSION, "sources": lignes,
            "total": len(lignes),
            "a_regarder": len([l for l in lignes
                               if l["sante"] in ("muet", "jamais_joint")])}


def ordre_de_passage():
    """Les sources, LA MOINS RÉCEMMENT INTERROGÉE D'ABORD.

    POURQUOI L'ORDRE COMPTE MAINTENANT, ET PAS AVANT. Avec deux flux, l'ordre
    était sans objet : la collecte les prenait tous les deux à chaque passage.
    Avec trente-six, un passage peut être interrompu par son budget de temps —
    et s'il repartait toujours du début, les dernières du catalogue ne seraient
    JAMAIS lues. Elles ne remonteraient aucune erreur : elles seraient
    simplement absentes de la page.

    L'ancienneté du dernier essai est déjà tenue par l'état de chaque flux :
    trier dessus suffit, sans mémoriser d'index de reprise — un index qu'un
    redémarrage remettrait d'ailleurs à zéro, ce qui recréerait exactement la
    famine qu'il devait éviter.
    """
    with _verrou:
        return sorted(SOURCES, key=lambda s: _etat_de(s["cle"])["dernier_essai"])


def reinitialiser():
    """Pour les essais : un état vierge, sans rien savoir des passages passés."""
    with _verrou:
        _etats.clear()


def glossaire():
    return {
        "source": "un flux d'actualité, identifié par sa clé, son émetteur et son pays",
        "eprouve": "l'adresse a-t-elle déjà fonctionné en production, ou seulement "
                   "été écrite ? Deux flux seulement sont éprouvés à ce jour",
        "muet": "le flux répond, mais n'a rien rendu depuis plusieurs passages — "
                "adresse valide qui ne sert plus, ou format que le lecteur ignore",
        "jamais_joint": "on a essayé, on n'a jamais rien obtenu : l'adresse est "
                        "probablement fausse",
        "texte_integral": "a-t-on le droit de reprendre le corps de la publication, "
                          "ou seulement son titre, son lien et son chapeau",
    }


def referentiel():
    return {"version": VERSION, "sources": len(SOURCES),
            "domaines": DOMAINES, "pays": PAYS,
            "natures": {k: v["libelle"] for k, v in NATURES.items()},
            "eprouvees": len([s for s in SOURCES if s["eprouve"]])}


def _verifier():
    """La cohérence INTERNE du catalogue, et rien de plus.

    Ce contrôle ne peut pas dire qu'une adresse répond : il tourne au
    chargement, sans réseau, et devrait faire échouer le démarrage du service
    pour un flux en panne — ce qui serait exactement le défaut corrigé au
    chantier précédent. C'est `etat()` qui répond de la joignabilité, en
    production, avec ce que les passages ont réellement donné.
    """
    fautes = []
    vues = set()
    for s in SOURCES:
        if s["cle"] in vues:
            fautes.append("clé de source en double : %s" % s["cle"])
        vues.add(s["cle"])
        if not s["url"].startswith("https://"):
            fautes.append("%s : l'adresse doit être en HTTPS" % s["cle"])
        if s["pays"] not in PAYS:
            fautes.append("%s : pays inconnu (%s)" % (s["cle"], s["pays"]))
        if s["domaine"] not in DOMAINES:
            fautes.append("%s : domaine inconnu (%s)" % (s["cle"], s["domaine"]))
        if s["nature"] not in NATURES:
            fautes.append("%s : nature inconnue (%s)" % (s["cle"], s["nature"]))
        if not s["nom"].strip():
            fautes.append("%s : nom d'émetteur vide" % s["cle"])
    for domaine in DOMAINES:
        if not [s for s in SOURCES if s["domaine"] == domaine]:
            fautes.append("domaine « %s » annoncé mais sans aucune source : "
                          "le filtre proposerait un choix qui ne rend rien"
                          % domaine)
    for nature, regle in NATURES.items():
        if "texte_integral" not in regle:
            fautes.append("nature %s : le droit de reprise n'est pas tranché"
                          % nature)
    return fautes


_FAUTES = _verifier()
if _FAUTES:                                              # pragma: no cover
    raise RuntimeError("veille_sources : catalogue incohérent — "
                       + " ; ".join(_FAUTES))
