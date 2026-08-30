# -*- coding: utf-8 -*-
"""Une adresse venue du dehors n'est pas une adresse.

DEUX DANGERS DISTINCTS, ET UN SEUL ÉCHAPPEMENT NE COUVRE NI L'UN NI L'AUTRE.

  · À L'AFFICHAGE. Échapper protège du BALISAGE, pas du SCHÉMA. Une adresse
    `javascript:…` parfaitement échappée s'exécute au clic : les guillemets
    sont neutralisés, le schéma ne l'est pas. La page de jurisprudence tenait
    déjà cette garde — « on n'ouvre que http et https » — et elle n'avait été
    appliquée nulle part ailleurs. Depuis que la veille lit trente-six flux
    extérieurs, chaque titre d'article apporte une adresse écrite par un tiers.

  · AU TÉLÉCHARGEMENT. Une adresse qu'on va CHERCHER depuis le serveur porte un
    autre risque : elle désigne ce que le serveur peut joindre, et non ce que
    l'internaute peut joindre. Une adresse pointant sur 169.254.169.254, sur
    127.0.0.1 ou sur un réseau privé fait interroger l'infrastructure elle-même
    — son service de métadonnées, ses bases, ses pages d'administration — par
    un serveur qui, lui, a le droit. La requête part de l'intérieur : aucun
    pare-feu ne la voit passer.

CE MODULE NE FAIT PAS DE RÉSOLUTION DNS, et le dit plutôt que de le laisser
croire. Un nom de domaine public qui résout vers une adresse privée passerait
cette garde : c'est la limite connue de tout contrôle fait sur la chaîne. La
défense complète demanderait de résoudre puis d'épingler l'adresse jusqu'à la
connexion. Ce qui est tenu ici, c'est le cas fréquent — une adresse littérale —
et il vaut mieux le tenir en le disant que le manquer en se croyant couvert.
"""
import ipaddress
import re

VERSION = "2026-08-a"

# Le seul jeu de schémas qu'un lien affiché a le droit de porter. Liste
# BLANCHE : une liste noire de `javascript:` oublierait `data:`, `vbscript:`,
# et le schéma que le prochain navigateur inventera.
SCHEMAS = ("http", "https")

_ADRESSE = re.compile(r"^\s*([a-z][a-z0-9+.\-]*):", re.I)
# UNE ADRESSE IPv6 S'ÉCRIT ENTRE CROCHETS, et ses deux-points font partie de
# l'adresse. Une expression qui découperait sur le premier « : » rendrait « [ »
# comme nom d'hôte — que `ip_address` refuse, et que la garde laisserait donc
# passer pour un nom de domaine. `https://[::1]/` franchissait ce contrôle : la
# boucle locale, écrite dans l'autre notation.
_HOTE = re.compile(r"^\s*[a-z][a-z0-9+.\-]*://(?:[^/@]*@)?"
                   r"(?:\[([0-9a-f:.]+)\]|([^/:\s\[\]]+))", re.I)

# Ce qu'un serveur ne doit pas aller chercher pour le compte d'un tiers.
_METADONNEES = ("169.254.169.254", "metadata.google.internal", "metadata")


def schema(url):
    m = _ADRESSE.match(url or "")
    return (m.group(1).lower() if m else "")


def sur(url):
    """L'adresse si elle est affichable, sinon une chaîne vide.

    Rendre une chaîne vide plutôt que de lever : un lien absent se rend comme
    un titre sans lien, ce qui dégrade l'affichage d'un cran. Refuser
    l'élément entier ferait disparaître une actualité pour une adresse fautive,
    et le lecteur ne saurait pas qu'elle a existé.
    """
    u = (url or "").strip()
    return u if schema(u) in SCHEMAS else ""


def hote(url):
    m = _HOTE.match(url or "")
    if not m:
        return ""
    return (m.group(1) or m.group(2) or "").strip().lower().rstrip(".")


def joignable(url):
    """L'adresse peut-elle être TÉLÉCHARGÉE par le serveur ?

    Plus strict que `sur()` : on écarte en outre ce qui désigne la machine
    elle-même ou son réseau. Ce contrôle est nécessaire, jamais suffisant —
    voir l'en-tête sur la résolution de noms.
    """
    if not sur(url):
        return False
    h = hote(url)
    if not h or h in _METADONNEES:
        return False
    if h == "localhost" or h.endswith(".localhost") or h.endswith(".internal"):
        return False
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return True                  # un nom : on ne résout pas, cf. en-tête
    return not (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


def glossaire():
    return {
        "sur": "l'adresse est affichable dans un lien — schéma http ou https, "
               "seuls schémas qui ne s'exécutent pas au clic",
        "joignable": "le serveur peut aller la chercher : ni la machine "
                     "elle-même, ni son réseau privé, ni un service de "
                     "métadonnées d'hébergeur",
        "limite": "aucune résolution de nom n'est faite : un domaine public "
                  "qui pointe vers une adresse privée franchit cette garde",
    }


def referentiel():
    return {"version": VERSION, "schemas": list(SCHEMAS)}
