# -*- coding: utf-8 -*-
"""L'acheteur et l'objet — les formulations que le relevé manquait, MESURÉES.

CE QUI A ÉTÉ MESURÉ AVANT D'AJOUTER QUOI QUE CE SOIT. Sur des règlements écrits
comme les vrais, trois façons de nommer l'acheteur et deux de nommer l'objet
rendaient « non relevé » — la case du DC1/DC2 repartait vide sur un dossier qui
les porte en toutes lettres :

  · « Le pouvoir adjudicateur EST la Communauté… » (sans deux-points) ;
  · « Nom et adresse officiels de l'organisme acheteur : … » (formule BOAMP) ;
  · « Identification de l'acheteur : … » (l'intitulé du cadre A, en prose) ;
  · « Objet : … » nu ; « La consultation a pour objet … » sans « présente ».

CE QUE CES RÈGLES TIENNENT AUSSI, ET C'EST LE POINT : la précision. Le motif
« acheteur » nu avait été retiré parce qu'il attrapait « Profil d'acheteur :
https://… » et proposait une adresse web comme pouvoir adjudicateur. Les ajouts
ne rouvrent PAS ce piège, et « objet : » nu ne prend pas « objet social : ». On
mesure les deux côtés — sinon un motif trop large passerait la première règle
en cassant l'autre.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc as A                                                  # noqa: E402

PAR_CLE = {r["cle"]: r for r in A.RELEVES}


def _val(cle, phrase):
    for c in A._extraire(phrase, PAR_CLE[cle]["motifs"], maxi=4):
        if c["valeur"]:
            return c["valeur"]
    return None


ACHETEUR = {
    # sans deux-points
    "Le pouvoir adjudicateur est la Communauté de communes du Val.":
        "la Communauté de communes du Val",
    # formule BOAMP
    "Nom et adresse officiels de l'organisme acheteur : Mairie de Meudon.":
        "Mairie de Meudon",
    # intitulé du cadre A repris en prose
    "Identification de l'acheteur : Département du Rhône.":
        "Département du Rhône",
    # les deux formes qui marchaient déjà — non-régression
    "Pouvoir adjudicateur : Ville de Lyon.": "Ville de Lyon",
    "Maître d'ouvrage : SEM Patrimoniale de l'Est.":
        "SEM Patrimoniale de l'Est",
}

OBJET = {
    "Objet : rénovation énergétique du centre de données.":
        "rénovation énergétique du centre de données",
    "La consultation a pour objet la construction d'un data center.":
        "la construction d'un data center",
    # non-régression : la forme spécifique reste captée par SON motif
    "Objet du marché : maîtrise d'oeuvre pour un data center.":
        "maîtrise d'oeuvre pour un data center",
    "Objet de la consultation : audit énergétique.": "audit énergétique",
}


def test_acheteur_formulations_supplementaires():
    """Les cinq formulations rendent le nom de l'acheteur — les trois neuves
    comme les deux qui marchaient déjà."""
    for phrase, attendu in ACHETEUR.items():
        assert _val("acheteur", phrase) == attendu, (
            "« %s » rend %r au lieu de %r"
            % (phrase, _val("acheteur", phrase), attendu))


def test_objet_formulations_supplementaires():
    """« Objet : » nu et « La consultation a pour objet … » rendent l'objet ;
    la forme spécifique « Objet du marché : » reste captée sans que la nue la
    lui vole."""
    for phrase, attendu in OBJET.items():
        assert _val("objet", phrase) == attendu, (
            "« %s » rend %r au lieu de %r"
            % (phrase, _val("objet", phrase), attendu))


def test_acheteur_ne_ROUVRE_PAS_le_piege_du_profil_url():
    """LE TÉMOIN DE PRÉCISION, ET C'EST L'HISTOIRE DE CE RELEVÉ. « acheteur »
    nu attrapait « Profil d'acheteur : https://… ». Les ajouts ne doivent pas
    le rouvrir : aucune valeur d'acheteur ne doit être une adresse web."""
    v = _val("acheteur",
             "Profil d'acheteur : https://marches.vallee-agglo.fr/2026-014")
    assert v is None or "http" not in v, (
        "l'acheteur relevé est une adresse web : le piège du profil est "
        "rouvert — %r" % v)


def test_objet_nu_ne_prend_PAS_objet_social():
    """« Objet : » nu est borné au DÉBUT DE LIGNE, pour ne pas attraper
    « objet social » ni « l'objet de la visite » au fil d'une phrase."""
    assert _val("objet", "Notre objet social : conseil en ingénierie.") is None
    assert _val("objet", "L'objet de la visite : reconnaissance du site.") is None
