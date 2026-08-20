"""COMBIEN DE SERVEURS ? — une dérivation, et ce qu'elle refuse de dériver.

LE CHAMP ÉTAIT UN NOMBRE NU. Qui ne connaît pas déjà son parc répond au hasard
ou n'y touche pas — et le carbone incorporé des serveurs, qui ne dépend que de
lui, se calcule alors sur une estimation muette.

POURQUOI IL N'AVAIT AUCUNE PROPOSITION. Le module de balayage l'écrit sans
détour : « aucune plage défendable sans connaître la densité visée ». C'est
exact. La conséquence n'est pas de se taire, c'est que chaque proposition doit
DÉCLARER la densité qu'elle suppose — alors elle redevient défendable.

QUATRE PROPRIÉTÉS QUE CES CONTRÔLES PROTÈGENT

  1. LE MOTEUR RESTE SANS CHIFFRE DE FOURNISSEUR. Ces puissances par serveur
     sortent d'un livre blanc de fournisseur. Un contrôle interdit à
     `datacenter.py` d'importer l'état de l'art, précisément pour qu'un tel
     chiffre n'entre pas dans un résultat présenté comme normatif. La
     dérivation vit donc DANS l'état de l'art, et ne sert qu'à proposer.

  2. LA DIVISION SE REFAIT. Une puissance par serveur qu'on ne peut pas
     recalculer depuis la baie et son nombre de nœuds n'est plus une
     dérivation : c'est un chiffre posé là.

  3. CE QUI N'EST PAS DÉRIVABLE N'EST PAS DÉRIVÉ. La source donne deux baies
     sans leur nombre de nœuds. Supposer un remplissage fabriquerait un compte
     crédible et faux.

  4. LE COMPTE N'EST PAS UN ORDRE DE GRANDEUR. D'un profil à l'autre il varie
     d'un facteur vingt : c'est le profil qu'on choisit, pas le nombre.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import etat_art as EA  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE MOTEUR RESTE PROPRE
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_le_moteur_ne_porte_aucune_de_ces_puissances():
    """La règle existait avant cet ajout et vaut toujours : le moteur tient ses
    constantes de normes, pas de livres blancs. Y poser une puissance par
    serveur ferait entrer un chiffre de fournisseur dans un bilan carbone
    présenté comme normatif, sans que rien ne le signale."""
    with open(os.path.join(ICI, "datacenter.py"), encoding="utf-8") as f:
        src = f.read()
    assert "etat_art" not in src
    # LA TABLE ET SA FONCTION, PAS LES NOMBRES NUS. Chercher « 13 » ou « 22 »
    # dans le moteur ne prouvait rien : ces suites de chiffres y figurent dans
    # des numéros de norme et des millésimes. Le contrôle tombait donc sur du
    # bruit, et il aurait aussi bien pu passer sur une vraie fuite.
    for nom in ("PUISSANCE_PAR_SERVEUR", "SERVEURS_SANS_DERIVATION",
                "serveurs_possibles", "penguin"):
        assert nom not in src, nom


def test_la_source_est_NOMMEE_et_sa_nature_avec():
    """« Penguin Solutions » n'est pas une norme, et la page doit pouvoir le
    dire. Une source dont on tait la nature se lit comme une référence."""
    r = EA.serveurs_possibles(1000)
    assert r["source"]["editeur"] == "Penguin Solutions"
    assert r["source"]["nature"] == "livre_blanc_fournisseur"
    assert "fournisseur" in r["nature_source"].lower()


# ═══════════════════════════════════════════════════════════════════════════
#  2. LA DIVISION SE REFAIT
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_chaque_profil_derive_se_RECALCULE_depuis_sa_baie():
    """Sans ce contrôle, « dérivé » ne serait qu'une étiquette : on pourrait
    retoucher une puissance par serveur sans toucher la baie dont elle sort, et
    la page citerait une source qui ne dit plus ce qu'on lui fait dire."""
    derives = [d for d in EA.PUISSANCE_PAR_SERVEUR.values()
               if d["obtention"] == "derive"]
    assert len(derives) == 2, len(derives)
    for d in derives:
        assert abs(d["baie_kw"] / d["noeuds"] - d["kw"]) < 1e-9, d


def test_la_baie_H100_se_lit_DEUX_fois_et_donne_le_meme_nombre():
    """Le fait source donne la baie H100 à deux nœuds (22 kW) ET à quatre
    (44 kW). Les deux lectures doivent donner la même puissance par nœud —
    sinon ce n'est pas une mesure, c'est une coïncidence."""
    h = EA.PUISSANCE_PAR_SERVEUR["gpu_h100"]
    assert 22 / 2 == 44 / 4 == h["kw"]
    fait = next(f for f in EA.FAITS if f["cle"] == "baies_kw")
    assert "22 kW" in fait["enonce"] and "44 kW" in fait["enonce"]


def test_le_profil_reste_ACCROCHE_a_un_fait_qui_existe():
    par_cle = {f["cle"]: f for f in EA.FAITS}
    for cle, d in EA.PUISSANCE_PAR_SERVEUR.items():
        if d["obtention"] != "derive":
            continue
        assert d["fait"] in par_cle, cle
        assert ("%d kW" % d["baie_kw"]) in par_cle[d["fait"]]["enonce"], cle


# ═══════════════════════════════════════════════════════════════════════════
#  3. CE QUI N'EST PAS DÉRIVABLE
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_les_baies_sans_noeuds_ne_sont_PAS_derivees():
    """La source donne 8,6 kW pour une baie d'entreprise et 57 kW pour une baie
    B200, sans dire combien de serveurs chacune contient. En tirer un compte
    supposerait un remplissage que personne n'a mesuré."""
    assert set(EA.SERVEURS_SANS_DERIVATION) == {"baie_entreprise", "baie_b200"}
    for cle, d in EA.SERVEURS_SANS_DERIVATION.items():
        assert len(d["pourquoi"]) >= 40, cle
        assert d["baie_kw"] > 0
    # …et aucune ne s'est glissée parmi les profils chiffrés.
    for cle in EA.SERVEURS_SANS_DERIVATION:
        assert cle not in EA.PUISSANCE_PAR_SERVEUR
    # Le refus voyage AVEC la réponse : tu, il ne servirait à personne.
    assert EA.serveurs_possibles(1000)["sans_derivation"]
    assert EA.serveurs_possibles(0)["sans_derivation"]


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES COMPTES
# ═══════════════════════════════════════════════════════════════════════════

def test_les_comptes_se_REFONT_a_la_main():
    r = EA.serveurs_possibles(1500)
    assert r["ok"] is True
    par = {p["cle"]: p for p in r["profils"]}
    assert par["volume"]["nombre"] == 3000        # 1500 / 0,5
    assert par["gpu_a100"]["nombre"] == 231       # 1500 / 6,5
    assert par["gpu_h100"]["nombre"] == 136       # 1500 / 11
    for p in r["profils"]:
        assert p["nombre"] == max(1, round(1500 / p["kw_par_serveur"])), p["cle"]


def test_LE_POINT_QUI_DECIDE_l_ecart_entre_profils_est_ENORME_et_annonce():
    """C'est tout l'objet de ces propositions. Un « nombre de serveurs » sans
    profil ne veut rien dire : la même puissance porte 3 000 serveurs de volume
    ou 136 nœuds H100."""
    r = EA.serveurs_possibles(1500)
    n = [p["nombre"] for p in r["profils"]]
    assert max(n) / min(n) > 15, n
    assert "profil qu'il faut choisir" in r["lecture"]


def test_sans_puissance_le_module_REFUSE_au_lieu_de_proposer_zero():
    for vide in (None, 0, "", "abc", -5):
        r = EA.serveurs_possibles(vide)
        assert r["ok"] is False, vide
        assert r["erreur"] == "puissance_absente"
        assert "profils" not in r
        assert "saisissez-la d'abord" in r["message"]


def test_un_compte_ne_descend_JAMAIS_a_zero_quand_la_puissance_existe():
    """Une petite salle porte peu de nœuds GPU, pas zéro : « 0 serveur » se
    lirait comme « ce profil est impossible », ce que le module ne sait pas."""
    r = EA.serveurs_possibles(3)
    assert all(p["nombre"] >= 1 for p in r["profils"]), r["profils"]


def test_la_reserve_sur_le_stockage_et_le_reseau_est_DITE():
    """La puissance informatique ne porte pas que des serveurs. Taire ce point
    ferait passer un haut de fourchette pour un compte."""
    r = EA.serveurs_possibles(1000)
    assert "stockage" in r["reserve"] and "réseau" in r["reserve"]
    assert "haut de fourchette" in r["reserve"]


def test_les_profils_sont_SERVIS_a_la_page_avec_leur_source():
    e = EA.etat()
    assert e["puissance_par_serveur"] == EA.PUISSANCE_PAR_SERVEUR
    assert e["ordre_serveurs"] == EA.ORDRE_SERVEURS
    assert e["serveurs_sans_derivation"] == EA.SERVEURS_SANS_DERIVATION
    for d in e["puissance_par_serveur"].values():
        assert d["nom"] and d["source"] and d["obtention"]


def test_la_page_applique_la_MEME_division_que_le_module():
    """La page divise elle-même, pour que le menu suive la puissance sans aller
    au serveur. Les deux formules doivent donc rester identiques — c'est le
    genre d'écart qu'on ne voit jamais, parce que les deux ont l'air justes."""
    import re
    # LES DEUX PAGES portent ce formulaire — /ingenierie-datacenter et
    # /datacenter. N'en vérifier qu'une laisserait l'autre dériver sans bruit,
    # et le même champ proposerait deux comptes différents selon la page.
    for fichier in ("ingenierie-dc.js", "datacenter.js"):
        with open(os.path.join(ICI, fichier), encoding="utf-8") as f:
            js = f.read()
        assert 'idChamp === "nb_serveurs"' in js, fichier
        bloc = js[js.index('idChamp === "nb_serveurs"'):][:1200]
        assert re.search(r"Math\.max\(1,\s*Math\.round\(pit\s*/\s*d\.kw\)\)", bloc), fichier
        # …et elle lit bien l'état de l'art, pas le référentiel du moteur.
        assert "ART.puissance_par_serveur" in bloc, fichier
        assert "REF.puissance_par_serveur" not in js, fichier
