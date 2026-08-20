"""LE FIL DES GESTES — il doit nommer TOUTE la page, et se laisser parcourir.

CE QUI MANQUAIT. Le fil comptait huit gestes et se déclarait « terminé » sans
avoir jamais nommé deux sections entières : le prix de la maîtrise d'œuvre et
le coût des travaux poste par poste. Un lecteur guidé de bout en bout pouvait
ignorer que la page savait chiffrer une opération.

LES TROIS RÈGLES QUE CES CONTRÔLES TIENNENT

  1. LES SECTIONS D'ARGENT SONT DANS LE FIL. Rien ne doit pouvoir les en
     retirer en silence — c'est exactement ainsi qu'elles en étaient absentes.

  2. LE FIL SE PARCOURT EN ENTIER. Un préalable qu'aucun geste antérieur ne
     produit arrête le fil définitivement, sans rien dire.

  3. PASSER N'EST PAS FAIRE. Les prix unitaires viennent du bordereau du
     client : sans le droit de passer, le fil resterait bloqué sur une étape
     que le lecteur ne PEUT pas franchir, et ne proposerait plus jamais de
     rédiger une pièce. Mais une étape passée ne remplit AUCUN préalable —
     sinon on enverrait le lecteur calculer des honoraires sur des travaux
     qu'il n'a pas chiffrés, où il ne trouverait qu'un refus.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ingenierie_dc as G  # noqa: E402

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lire(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


# ── 1. Le fil nomme toute la page ──────────────────────────────────────────

def test_LE_POINT_QUI_DECIDE_les_sections_d_argent_sont_DANS_le_fil():
    """Sans elles, le parcours se déclarait terminé en ayant tu deux sections
    entières — et le lecteur guidé de bout en bout ne savait pas que la page
    chiffrait une opération."""
    ids = [g["id"] for g in G.GESTES]
    for cle in ("moe", "travaux", "honoraires"):
        assert cle in ids, ids
    par = {g["id"]: g for g in G.GESTES}
    assert par["moe"]["fleche"] == "Section 6"
    assert par["travaux"]["fleche"] == "Section 7"
    assert par["honoraires"]["fleche"] == "Section 7"


def test_chaque_ancre_du_fil_EXISTE_dans_la_page():
    """Une ancre qui ne désigne rien fait un « M'y conduire » qui ne conduit
    nulle part, et une flèche verticale qui ne se pose jamais."""
    page = _lire("ingenierie-datacenter.html")
    for g in G.GESTES:
        assert g["ancre"].startswith("#"), g["id"]
        assert 'id="%s"' % g["ancre"][1:] in page, (g["id"], g["ancre"])


def test_les_gestes_d_argent_visent_les_BOUTONS_qui_calculent():
    """La cible d'un geste est ce sur quoi on clique. Viser la section entière
    ferait battre un bloc de six cents pixels, ce qui ne désigne rien."""
    page = _lire("ingenierie-datacenter.html")
    par = {g["id"]: g for g in G.GESTES}
    for cle, bouton in (("moe", "ig-moe-go"), ("travaux", "ig-eco-go"),
                        ("honoraires", "ig-pont-go")):
        assert par[cle]["cible"] == "#" + bouton, par[cle]["cible"]
        assert 'id="%s"' % bouton in page, bouton


def test_l_ordre_des_gestes_d_argent_est_celui_qui_CONTRAINT():
    """On chiffre des travaux avant des honoraires : le pont s'assied sur
    l'assiette que l'économiste vient de produire. L'ordre inverse enverrait
    sur un calcul qui ne peut que refuser."""
    ids = [g["id"] for g in G.GESTES]
    assert ids.index("travaux") < ids.index("honoraires")
    par = {g["id"]: g for g in G.GESTES}
    assert par["honoraires"]["exige"] == ["travaux"]
    # …et ils viennent APRÈS le niveau de disponibilité, qui commande les
    # quantités, donc le coût.
    assert ids.index("disponibilite") < ids.index("travaux")


# ── 2. Le fil se parcourt en entier ────────────────────────────────────────

def test_aucun_prealable_n_est_produit_TROP_TARD():
    """Un préalable produit par un geste POSTÉRIEUR ne serait jamais rempli à
    temps : le fil s'arrêterait là, définitivement et en silence."""
    produits = set()
    for g in G.GESTES:
        for k in g["exige"]:
            assert k in produits, (g["id"], k)
        produits.add(g["fait_si"])


def test_le_fil_se_deroule_JUSQU_AU_BOUT_geste_apres_geste():
    """Le contrôle qui vérifie que l'enchaînement complet est franchissable :
    on part de rien, on accomplit ce qu'on propose, et on doit arriver à la
    fin — sans jamais repasser deux fois par le même geste."""
    etat, vus, tour = {}, [], 0
    while tour < 40:
        g = G.prochain_geste(etat)
        if g is None:
            break
        assert g["id"] not in vus, "le fil propose deux fois %s" % g["id"]
        vus.append(g["id"])
        etat[g["fait_si"]] = True
        tour += 1
    assert g is None, "le fil ne se termine pas"
    assert len(vus) == len(G.GESTES), (len(vus), len(G.GESTES))


# ── 3. Passer n'est pas faire ──────────────────────────────────────────────

def test_les_gestes_facultatifs_disent_ce_qu_on_perd_a_les_passer():
    for g in G.GESTES:
        if g.get("facultatif"):
            assert len(g.get("passer", "")) > 40, g["id"]
        else:
            assert not g.get("passer"), g["id"]
    assert G.gestes_referentiel()["facultatifs"] == ["moe", "travaux", "honoraires"]


def test_LE_POINT_QUI_DECIDE_sans_le_droit_de_passer_le_fil_se_BLOQUE():
    """Le geste des travaux exige des prix unitaires qui viennent du bordereau
    du client. S'il était obligatoire, le fil resterait posé dessus et ne
    proposerait plus JAMAIS de rédiger une pièce."""
    etat = {"projet": True, "profil": True, "phase": True, "disponibilite": True}
    # Sans rien passer, le fil s'arrête sur le premier geste d'argent…
    assert G.prochain_geste(etat)["id"] == "moe"
    # …et il y resterait indéfiniment.
    assert G.prochain_geste(etat)["id"] == "moe"
    # Les passer rend la main au travail de rédaction.
    suite = G.prochain_geste(etat, passes=["moe", "travaux"])
    assert suite["id"] == "piece", suite["id"]


def test_LE_POINT_QUI_DECIDE_une_etape_passee_ne_remplit_AUCUN_prealable():
    """Confondre « passé » et « fait » enverrait calculer des honoraires sur
    des travaux qu'on n'a pas chiffrés — où l'on ne trouverait qu'un refus."""
    etat = {"projet": True, "profil": True, "phase": True, "disponibilite": True}
    suite = G.prochain_geste(etat, passes=["moe", "travaux"])
    assert suite["id"] != "honoraires", (
        "le pont est proposé alors que son assiette n'existe pas")
    # Fait pour de bon, en revanche, il ouvre bien la suite.
    etat["moe"] = True
    etat["travaux"] = True
    assert G.prochain_geste(etat)["id"] == "honoraires"


def test_un_geste_passe_INCONNU_est_refuse_et_non_ignore():
    """Un identifiant qui ne correspond à rien viendrait d'un stockage
    périmé : l'ignorer ferait sauter une étape sans que personne le sache."""
    with pytest.raises(ValueError):
        G.prochain_geste({"profil": True}, passes=["etape_qui_n_existe_plus"])


def test_le_reste_annonce_NE_COMPTE_PAS_ce_qui_a_ete_passe():
    """« Il reste huit étapes » alors que trois ont été écartées ferait lire un
    retard qui n'existe pas."""
    etat = {"projet": True, "profil": True, "phase": True, "disponibilite": True}
    sans = G.prochain_geste(etat)
    avec = G.prochain_geste(etat, passes=["moe", "travaux", "honoraires"])
    assert len(avec["reste"]) < len(sans["reste"])
    for cle in ("moe", "travaux", "honoraires"):
        assert cle not in avec["reste"]


# ── 4. La page sait constater ces trois gestes ─────────────────────────────

def test_la_page_CONSTATE_les_trois_gestes_d_argent():
    """Un geste que la page ne sait pas constater reste proposé pour toujours,
    même une fois accompli."""
    js = _lire("ingenierie-dc.js")
    for cle in ("moe:", "travaux:", "honoraires:"):
        assert cle in js, cle
    # Le constat porte sur un RÉSULTAT produit, pas sur un bouton cliqué : un
    # chiffrage refusé laisse la zone vide, et l'étape doit rester à faire.
    assert '#ig-moe-out table' in js
    assert '#ig-eco-out .ig-eco-t' in js
    assert '#ig-pont-out .ig-moe-kpi' in js


def test_les_deux_calculs_d_honoraires_ecrivent_dans_des_zones_DISTINCTES():
    """La section 6 chiffre sur une enveloppe reportée, la section 7 sur les
    travaux chiffrés dans la page. Partager une zone de résultat ferait que
    chacun efface l'autre — et le fil ne saurait plus lequel a été fait."""
    page = _lire("ingenierie-datacenter.html")
    for ident in ("ig-moe-out", "ig-pont-out", "ig-moe-go", "ig-pont-go"):
        assert page.count('id="%s"' % ident) == 1, ident
