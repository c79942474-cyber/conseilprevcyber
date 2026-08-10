"""Les périmètres types : une seule source, et une phrase qui ne ment plus.

DEUX DÉFAUTS, DONT UN VÉRIFIABLE PAR N'IMPORTE QUEL LECTEUR.

  1. LA LISTE ÉTAIT RECOPIÉE DANS LA PAGE. Dix-huit lignes de <datalist> écrites
     à la main dans le formulaire. Une liste recopiée ne se compare à rien :
     elle ne se vérifie pas, ne se réutilise pas ailleurs, et diverge sans que
     rien ne le signale.

  2. LA PHRASE QUI L'ACCOMPAGNAIT ÉTAIT FAUSSE, ET LE LIEN LE PROUVAIT.
     « Périmètres tirés de nos retours d'expérience », avec un lien vers les
     études de cas — où aucun des dix-huit ne figure. Le lecteur qui suivait le
     lien pour vérifier ne trouvait rien. Une affirmation vérifiable et démentie
     coûte plus cher qu'une absence d'affirmation : elle apprend au lecteur que
     les textes du site ne se vérifient pas.

CE QUE CES TESTS VERROUILLENT : que la migration n'ait rien perdu en route, que
la source reste unique, et que la promesse tenue par la phrase soit celle que
les données peuvent tenir.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import livrables as L  # noqa: E402

PAGE = os.path.join(ICI, "admin-livrables.html")


def page():
    with open(PAGE, encoding="utf-8") as f:
        return f.read()


def page_rendue():
    """La page SANS ses commentaires HTML.

    Les commentaires expliquent souvent le défaut corrigé en le citant — c'est
    leur rôle. Chercher une phrase interdite dans le fichier brut revient donc
    à la trouver dans sa propre explication, et à faire échouer le test sur le
    commentaire au lieu du contenu. Ce qui se juge ici, c'est ce que le lecteur
    voit."""
    return re.sub(r"<!--.*?-->", " ", page(), flags=re.S)


def tous():
    return [v for _, vals in L.PERIMETRES_TYPES for v in vals]


# ── 1. Le vocabulaire se tient ─────────────────────────────────────────────

def test_le_module_se_charge_sans_incoherence():
    assert L._verifier_perimetres() == []


def test_les_perimetres_sont_groupes_et_aucun_groupe_n_est_vide():
    assert len(L.PERIMETRES_TYPES) >= 4
    for nom, vals in L.PERIMETRES_TYPES:
        assert nom.strip(), "un groupe sans nom ne classe rien"
        assert vals, nom


def test_aucun_doublon_entre_groupes():
    """Le même périmètre dans deux natures ferait croire à une nuance
    inexistante, et le lecteur chercherait la différence."""
    t = tous()
    assert len(t) == len(set(t)), [x for x in t if t.count(x) > 1]


@pytest.mark.parametrize("v", tous())
def test_chaque_perimetre_est_un_perimetre_et_pas_une_etiquette(v):
    """« Cybersécurité » n'est pas un périmètre : un périmètre dit ce qui est
    DEDANS et, par là, ce qui est dehors."""
    assert len(v) >= 30, v
    assert v[0].isupper(), v
    assert not v.endswith("."), v


# ── 2. La migration n'a rien perdu ─────────────────────────────────────────

# Les dix-huit valeurs telles qu'elles étaient écrites dans la page avant que la
# liste ne rejoigne le module. Figées ici À DESSEIN : c'est le seul moyen de
# prouver qu'un déplacement de données n'en a pas égaré en chemin, et une perte
# d'option ne se voit pas à l'œil — le champ reste utilisable, simplement moins
# utile, et personne ne s'en aperçoit.
AVANT = [
    "Réseau OT SCADA et automates — 2 sites de production",
    "Systèmes de contrôle industriel (PLC, HMI, SCADA, DCS) d'une unité de production",
    "SI industriel d'un site classé — cartographie et maintien en condition de sécurité",
    "Sous-station électrique offshore — systèmes sous schéma de sécurité OT (IEC 62443)",
    "Poste électrique HT/BT et systèmes de protection",
    "Station de traitement d'eau — télégestion et postes locaux",
    "Réseau de distribution de gaz — télé-exploitation et postes de détente",
    "Réseau multi-services et systèmes de surveillance des espaces d'une ligne de métro",
    "Système de signalisation ferroviaire et centre de contrôle",
    "Véhicule connecté — périmètre CSMS / SUMS (UNECE R155/R156)",
    "Datacenters et réseaux du système d'information",
    "Applications exposées sur internet — surface d'exposition du groupe",
    "SOC et chaîne de détection / réponse à incident",
    "Chaîne de patching et de remédiation des vulnérabilités",
    "Environnement cloud et interconnexions avec le SI industriel",
    "EPCI et interfaces fournisseurs d'un projet d'infrastructure",
    "Chaîne de sous-traitance — exigences cascadées aux fournisseurs",
    "Périmètre groupe multi-filiales — SI et SI industriels",
]


def test_la_migration_n_a_perdu_aucun_perimetre():
    manquants = [v for v in AVANT if v not in tous()]
    assert not manquants, manquants


def test_la_liste_peut_s_enrichir_sans_casser_ce_controle():
    """Le contrôle ci-dessus vérifie une INCLUSION, pas une égalité : ajouter un
    périmètre demain ne doit pas obliger à réparer un test."""
    assert set(AVANT) <= set(tous())


# ── 3. Une seule source ────────────────────────────────────────────────────

def test_la_page_ne_recopie_plus_la_liste():
    """DÉFAUT CORRIGÉ. Tant que les valeurs restent dans le HTML, les deux
    exemplaires divergent au premier ajout — et c'est celui de la page que le
    lecteur voit."""
    h = page_rendue()
    dl = re.search(r'<datalist id="perimetres">(.*?)</datalist>', h, re.S)
    assert dl, "le datalist des périmètres a disparu de la page"
    assert "<option" not in dl.group(1), (
        "la liste est de nouveau écrite en dur dans la page")
    for v in AVANT[:5]:
        assert v not in h, v


def test_la_page_remplit_la_liste_depuis_le_serveur():
    h = page()
    assert "remplirPerimetres" in h
    assert "j.perimetres" in h


def test_le_champ_reste_utilisable_si_la_liste_n_arrive_pas():
    """Un repli silencieux est acceptable ICI, et seulement ici : un périmètre
    se saisit librement de toute façon. Ce qu'on vérifie, c'est qu'on ne vide
    pas la page ni ne bloque la saisie."""
    h = page()
    m = re.search(r"function remplirPerimetres\(p\)\{(.*?)\n    \}", h, re.S)
    assert m, "fonction introuvable"
    assert "if(!dl||!p||!p.groupes)return;" in m.group(1)
    assert 'id="perimetre"' in h and "readonly" not in h.split('id="perimetre"')[1][:200]


# ── 4. La phrase ne promet plus ce qu'elle ne peut pas tenir ───────────────

def test_la_page_ne_rattache_plus_les_perimetres_aux_etudes_de_cas():
    """LE DÉFAUT VÉRIFIABLE PAR LE LECTEUR. La phrase renvoyait aux études de
    cas pour justifier la liste ; aucun de ces périmètres n'y figure."""
    h = page_rendue()
    bloc = h.split('id="perimetre"')[1][:700]
    assert "retours d'expérience" not in bloc, (
        "l'affirmation est de retour, et elle reste invérifiable")
    assert "/etudes-de-cas" not in bloc


def test_les_perimetres_ne_figurent_effectivement_pas_dans_les_etudes_de_cas():
    """La preuve du défaut, pas son souvenir. Si un jour les études de cas
    portaient réellement ces périmètres, ce test tomberait — et il faudrait
    alors rétablir la phrase, qui serait devenue vraie."""
    cas = os.path.join(ICI, "etudes-de-cas.html")
    with open(cas, encoding="utf-8") as f:
        c = f.read()
    presents = [v for v in AVANT if v in c]
    assert not presents, (
        "ces périmètres figurent désormais dans les études de cas : la phrase "
        "d'origine serait redevenue exacte — %s" % presents)


def test_la_note_dit_ce_que_la_liste_est_vraiment():
    n = L.PERIMETRES_NOTE
    assert "courants" in n.lower()
    assert "libre" in n.lower(), "le champ reste libre, et cela doit se lire"
    # Elle ne doit revendiquer aucune mission menée.
    for mot in ("retours d'expérience", "nos missions", "nos références"):
        assert mot not in n.lower(), mot


# ── 5. Le service ──────────────────────────────────────────────────────────

def test_le_service_rend_les_groupes_et_la_note():
    p = L.perimetres()
    assert p["note"] == L.PERIMETRES_NOTE
    assert len(p["groupes"]) == len(L.PERIMETRES_TYPES)
    plat = [v for g in p["groupes"] for v in g["valeurs"]]
    assert plat == tous()


def test_le_service_ne_partage_pas_ses_listes_internes():
    """Rendre la liste elle-même laisserait un appelant la modifier pour tout le
    monde — le genre de bogue qu'on ne relie jamais à sa cause."""
    p = L.perimetres()
    p["groupes"][0]["valeurs"].append("intrus")
    assert "intrus" not in tous()
