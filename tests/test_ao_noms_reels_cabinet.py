# -*- coding: utf-8 -*-
"""LES NOMS QUE PORTENT VRAIMENT LES FICHIERS — et non ceux qu'on inventerait.

CE QUI EST ARRIVÉ EN PRODUCTION LE 16 SEPTEMBRE 2026. Deux fichiers déposés,
deux refusés :

    extrait_k_bis_extrait_k_ou_extrait_l_bis_datant_de_moins_de_trois_mois.pdf
    Doc synthèse INPI2026.pdf

Le premier est le nom EXACT sous lequel le greffe délivre un Kbis ; le second
celui de l'INPI. Le message disait « renommez-le », ce qui revient à demander
à l'utilisateur de faire le travail de reconnaissance à la place de l'outil.

LE DÉFAUT DERRIÈRE, ET IL ÉTAIT PLUS LARGE. `THEME_CABINET` mappait déjà
« kbis » vers « Cabinet / Identité & existence légale » — et AUCUN motif ne
menait à cette clé. Le rayon était déclaré, affiché sur l'étagère, et
rigoureusement inatteignable. Sur vingt-deux noms de fichiers réalistes, ONZE
étaient refusés.

POURQUOI CES NOMS-LÀ ET PAS D'AUTRES. Ils viennent de qui délivre la pièce :
le greffe, l'INPI, l'URSSAF, l'administration fiscale (l'imprimé « 3666 »),
l'OPQIBI, l'assureur, l'expert-comptable. Aucun ne porte le vocabulaire du
formulaire DC2 — « aptitude technique et professionnelle », « régularité
fiscale » — qui était pourtant ce que les motifs cherchaient. Un banc bâti sur
des noms inventés aurait mesuré mon imagination ; celui-ci mesure ce qui se
dépose.

ET LE TITRE EST DÉRIVÉ, PAS SUBI. Le nom du greffe finissait tel quel dans la
consigne de rédaction, à la ligne « Documents du cabinet : … ». Le fichier
garde son nom — c'est lui qu'on retrouve au greffe — mais il se range sous un
intitulé lisible.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                     # noqa: E402
import dossier_cabinet                                           # noqa: E402
import rag_store                                                 # noqa: E402

import pytest                                                    # noqa: E402


# CHAQUE LIGNE EST UN NOM DE FICHIER TEL QU'IL ARRIVE, et la pièce ou le rayon
# où il doit aller. Les deux premiers sont les refus mesurés en production.
NOMS = [
    ("extrait_k_bis_extrait_k_ou_extrait_l_bis_datant_de_moins_de_trois_"
     "mois.pdf", "Cabinet / Identité & existence légale"),
    ("Doc synthèse INPI2026.pdf", "Cabinet / Identité & existence légale"),
    ("Kbis CONSEILPREV 2026.pdf", "Cabinet / Identité & existence légale"),
    ("extrait-rcs-conseilprev.pdf", "Cabinet / Identité & existence légale"),
    ("avis-de-situation-sirene.pdf", "Cabinet / Identité & existence légale"),
    ("INPI - fiche d'identite entreprise.pdf",
     "Cabinet / Identité & existence légale"),
    ("immatriculation-registre-du-commerce.pdf",
     "Cabinet / Identité & existence légale"),
    ("Attestation RC Pro 2026 AXA.pdf", "Cabinet / Assurances"),
    ("attestation-decennale-2026.pdf", "Cabinet / Assurances"),
    ("attestation_vigilance_urssaf_2026T2.pdf",
     "Cabinet / Régularité fiscale & sociale"),
    ("attestation-fiscale-3666.pdf", "Cabinet / Régularité fiscale & sociale"),
    ("comptes annuels 2025 - CONSEILPREV.pdf",
     "Cabinet / Comptes, bilans & chiffre d'affaires"),
    ("liasse-fiscale-2024.pdf", "Cabinet / Comptes, bilans & chiffre d'affaires"),
    ("CV Christophe CERF 2026.pdf", "Cabinet / Moyens humains, CV & organigramme"),
    ("organigramme fonctionnel mission.pdf",
     "Cabinet / Moyens humains, CV & organigramme"),
    ("note de presentation de l'equipe.docx",
     "Cabinet / Moyens humains, CV & organigramme"),
    ("references clients 2021-2026.docx",
     "Cabinet / Références & attestations de bonne exécution"),
    ("attestation-bonne-execution-mairie-de-X.pdf",
     "Cabinet / Références & attestations de bonne exécution"),
    ("certificat ISO 9001 CONSEILPREV.pdf",
     "Cabinet / Qualifications, certifications & QSE"),
    ("qualification OPQIBI 1301.pdf",
     "Cabinet / Qualifications, certifications & QSE"),
    ("delegation de signature gerant.pdf",
     "Cabinet / Pouvoirs, délégations & groupement"),
    # UN FICHIER QUI PORTE LES DEUX SE RANGE SOUS LA PIÈCE À PRODUIRE. Une
    # pièce du dossier de réponse se JOINT ; un Kbis nourrit la fiche. C'est
    # pourquoi `piece_du_cabinet` passe avant `rayon_du_cabinet`.
    ("KBIS + pouvoirs signataire.pdf",
     "Cabinet / Pouvoirs, délégations & groupement"),
    # ── LA DOCUMENTATION, pour que la règle d'atteignabilité couvre TOUS les
    #    rayons déclarés. C'est elle qui a signalé qu'il en manquait quatre
    #    dans ce banc : sans eux, elle aurait pu virer au vert en laissant un
    #    rayon mort, ce qu'elle est précisément là pour empêcher.
    ("fiche-technique-groupe-froid-carrier.pdf",
     "Cabinet / Fiches techniques & documentation produit"),
    ("guide-anssi-hygiene-informatique.pdf",
     "Cabinet / Normes, guides & référentiels"),
    ("methodologie-de-commissionnement.pdf",
     "Cabinet / Mémoires techniques & notes méthodologiques"),
    ("note sur les moyens materiels du cabinet.docx",
     "Cabinet / Moyens matériels & techniques"),
]


def _destination(nom):
    return dossier_cabinet.destination(ao_dc.piece_du_cabinet(nom), nom)


# L'IDENTIFIANT DE CHAQUE CAS EST LE NOM DU FICHIER, SANS ESPACE. Sans cela
# pytest compose l'identifiant avec le rayon, le tronque au premier espace, et
# une batterie de mutations ne peut plus viser un cas précis : elle croit la
# règle mal visée alors qu'elle est tombée.
@pytest.mark.parametrize("nom,rayon", NOMS,
                         ids=[n.replace(" ", "_") for n, _r in NOMS])
def test_chaque_nom_REEL_trouve_son_rayon(nom, rayon):
    """LA RÈGLE QUI PORTE LE TOUR. Onze de ces vingt-deux étaient refusés — et
    le refus demandait à l'utilisateur de renommer le fichier, c'est-à-dire de
    faire à la main la reconnaissance que l'outil doit faire."""
    d = _destination(nom)
    assert not d["refus"], "%s : %s" % (nom, d["dit"])
    assert d["rayon"] == rayon, (nom, d["rayon"])


def test_les_DEUX_refus_de_production_se_rangent_desormais():
    """NOMMÉE À PART parce que c'est le cas réel, et qu'il doit rester
    mesuré même si quelqu'un allège la liste ci-dessus."""
    for nom in ("extrait_k_bis_extrait_k_ou_extrait_l_bis_datant_de_moins_de_"
                "trois_mois.pdf", "Doc synthèse INPI2026.pdf"):
        d = _destination(nom)
        assert d["rayon"] == "Cabinet / Identité & existence légale", (nom, d)


def test_le_rayon_de_l_identite_est_ATTEIGNABLE():
    """IL ÉTAIT DÉCLARÉ ET MORT. `THEME_CABINET` le nommait, aucun motif n'y
    menait : l'étagère affichait un rayon où rien ne pouvait entrer.

    ON MESURE L'ATTEIGNABILITÉ DE CHAQUE RAYON, pas seulement de celui-ci : le
    même oubli se reproduira au prochain rayon ajouté, et il ne se voit pas."""
    atteints = set()
    for nom, _r in NOMS:
        d = _destination(nom)
        if d["rayon"]:
            atteints.add(d["rayon"])
    declares = set(ao_dc.THEME_CABINET.values()) | {
        r for r, _m in ao_dc.RAYON_MOTIFS}
    morts = sorted(declares - atteints)
    assert not morts, (
        "ces rayons sont déclarés et aucun nom de fichier réaliste n'y mène — "
        "ils s'affichent sur l'étagère et rien ne peut y entrer : %s" % morts)


def test_un_nom_qui_ne_dit_RIEN_est_toujours_refusé():
    """L'ÉLARGISSEMENT N'EST PAS UNE OUVERTURE. Un motif trop large ferait
    entrer n'importe quoi dans un rayon, et un document mal rangé est pire
    qu'un document refusé : il remonte dans un brouillon sans qu'on l'ait
    voulu."""
    for nom in ("photo-du-pot-de-depart.jpg", "IMG_20260916_114233.jpg",
                "sans-titre (3).pdf", "scan0001.pdf"):
        assert _destination(nom)["refus"] == "piece_inconnue", nom


# ═══════════════════════════════════════════════════════════════════════════
#  LE TITRE — dérivé, pour que l'étagère et la consigne restent lisibles.
# ═══════════════════════════════════════════════════════════════════════════
def test_le_titre_NE_SUBIT_PAS_le_nom_du_greffe():
    """CE NOM-LÀ FINISSAIT DANS LA CONSIGNE DE RÉDACTION, à la ligne
    « Documents du cabinet : … » — soixante-douze signes qui ne disent rien de
    plus que « Kbis »."""
    nom = ("extrait_k_bis_extrait_k_ou_extrait_l_bis_datant_de_moins_de_"
           "trois_mois.pdf")
    d = _destination(nom)
    t = dossier_cabinet.titre_pour(nom, ao_dc.piece_du_cabinet(nom), d["rayon"])
    assert t.startswith("Identité & existence légale"), t
    assert len(t) <= dossier_cabinet.TITRE_MAX, len(t)
    assert "_" not in t and ".pdf" not in t, t


def test_le_titre_DISTINGUE_deux_documents_de_la_meme_piece():
    """SANS LE FICHIER DANS LE TITRE, quinze documents porteraient cinq
    intitulés — et l'on ne saurait plus lequel retirer quand l'étagère est
    pleine."""
    a = dossier_cabinet.titre_pour("CV Christophe CERF 2026.pdf", "cv", "")
    b = dossier_cabinet.titre_pour("CV Marie Dupont 2026.pdf", "cv", "")
    assert a != b, (a, b)
    assert "CERF" in a and "Dupont" in b


def test_le_titre_NE_SE_REPETE_PAS():
    """« Organigramme fonctionnel de la mission — organigramme fonctionnel
    mission » se lit comme un bogue. La comparaison est mot à mot : l'ordre des
    mots suffisait à tromper une comparaison de chaînes."""
    t = dossier_cabinet.titre_pour("organigramme fonctionnel mission.pdf",
                                   "organigramme", "")
    assert t == "Organigramme fonctionnel de la mission", t


def test_le_titre_fourni_par_l_operateur_L_EMPORTE():
    """LE JOUR OÙ LA PAGE OFFRIRA DE LE SAISIR, ce que l'opérateur écrit doit
    gagner sur ce que le nom de fichier suggère."""
    rag = rag_store.MemoryRagStore()
    r = dossier_cabinet.ranger(rag, "Kbis CONSEILPREV 2026.txt",
                               b"Extrait Kbis du greffe.",
                               ao_dc.piece_du_cabinet("Kbis CONSEILPREV.txt"),
                               titre="Kbis de janvier")
    assert r["document"]["titre"] == "Kbis de janvier", r


def test_le_rangement_POSE_le_titre_derive():
    """LE FIL, ET PAS SEULEMENT LA FONCTION. `titre_pour` peut être juste et
    `ranger` ne pas l'appeler : le magasin garderait le nom de fichier, et
    aucune des règles ci-dessus ne le verrait."""
    rag = rag_store.MemoryRagStore()
    nom = "Doc synthèse INPI2026.txt"
    r = dossier_cabinet.ranger(rag, nom, "Fiche d'identite INPI.".encode("utf-8"),
                               ao_dc.piece_du_cabinet(nom))
    assert r["document"]["titre"].startswith(
        "Identité & existence légale"), r["document"]
    assert r["document"]["titre"] != nom
    # ET LE FICHIER GARDE SON NOM : c'est lui qu'on retrouve au greffe.
    docs = rag.list_documents()
    assert any(d.get("filename") == nom for d in docs), docs
