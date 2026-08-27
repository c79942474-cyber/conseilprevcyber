"""CE QUE VAUT UNE PERFORMANCE — et ce qu'on refuse d'en dire.

CE QUI A DÉCLENCHÉ CE FICHIER. Une recherche sur les six modules de la pratique
centre de données, 835 187 octets de code d'ingénierie, avec frontières de mot :

    subvention  0     CEE    0     ROI, payback  0
    aides       0     TICFE  0     financement   2

Le moteur calcule une énergie, une eau, un carbone. Onze leviers disent quoi
changer et ce que cela déplace. AUCUN NE DIT CE QUE CELA RAPPORTE — quelle
exonération se déclenche, quelle aide s'ouvre, à quel financement on accède.
C'est le chaînon qui sépare un bureau d'études d'un cabinet de conseil.

CE QUE CES CONTRÔLES GARDENT, ET C'EST L'INVERSE DE L'HABITUDE. Ils ne
vérifient pas que le module calcule juste : ils vérifient QU'IL NE CALCULE
RIEN. Les taux qui circulent sur ces dispositifs — « jusqu'à 50 % des audits »,
« 25 % du CAPEX », « un PUE inférieur à 1,2 » — viennent de notes de synthèse
professionnelles. Aucune source primaire n'a pu être consultée. Or ces chiffres
entrent dans des plans de financement, et les plans de financement passent
devant des comités d'engagement.

La règle centrale est donc `test_aucun_dispositif_ne_porte_de_chiffre` : elle
relit toutes les chaînes déclarées et refuse un pourcentage, un montant ou un
seuil. Elle est faite pour gêner — c'est-à-dire pour être la première chose qui
casse le jour où quelqu'un recopiera un taux depuis un article.

CE QUE CES CONTRÔLES NE PEUVENT PAS FAIRE. Vérifier qu'un dispositif existe
vraiment, ou que sa condition est bien celle annoncée. Cela suppose de lire les
textes, et c'est la prestation elle-même — pas une recette.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import decarbonation as decarb  # noqa: E402
import valorisation_dc as v  # noqa: E402


def _chaines(d):
    """Toutes les chaînes déclarées d'un dispositif, à plat."""
    sortie = []
    for val in d.values():
        if isinstance(val, str):
            sortie.append(val)
        elif isinstance(val, (list, tuple)):
            sortie += [x for x in val if isinstance(x, str)]
    return sortie


# ── LA RÈGLE CENTRALE : AUCUN CHIFFRE ────────────────────────────────────

#: Ce qu'on refuse. Un taux, un montant, un seuil — jamais une référence légale.
#: « Règlement (UE) 2024/573 » et « activité 8.1 » DOIVENT passer : ce sont des
#: identifiants, pas des quantités. La distinction est le tout de la règle.
#:
#: « UN TIERS » N'EST PAS DANS LA LISTE, ET C'EST DÉLIBÉRÉ. Le mot est un
#: homonyme : « livrer la chaleur à un tiers » désigne une PERSONNE, pas une
#: fraction. La première version de cette règle refusait la phrase
#: « à un réseau ou à un tiers » — un français parfaitement ordinaire. Une règle
#: qui oblige à écrire de travers finit par être contournée, et c'est alors
#: toute la règle qu'on perd. Le quart et la moitié, eux, n'ont pas de second
#: sens.
_CHIFFRES_INTERDITS = [
    (r'\d+\s*(?:,\d+)?\s*%', "un pourcentage"),
    (r'\d[\d\s.,]*\s*(?:€|EUR\b|euros?\b)', "un montant en euros"),
    (r'\b(?:PUE|WUE|CUE)\b[^.]{0,24}?[\d]+[,.]\d', "un seuil d'indicateur"),
    (r'\b(?:un\s+quart|la\s+moiti[ée]|moiti[ée]\s+d)\b', "une fraction en toutes lettres"),
]


@pytest.mark.parametrize('d', v.DISPOSITIFS, ids=[d['cle'] for d in v.DISPOSITIFS])
def test_aucun_dispositif_ne_porte_de_chiffre(d):
    """LA RÈGLE QUI COMPTE. Un taux d'aide faux entre dans un plan de
    financement, et un plan de financement faux passe devant un comité
    d'engagement. Tant qu'un dispositif n'est pas instruit sur source primaire,
    il n'a pas de montant : il a une source à consulter."""
    for texte in _chaines(d):
        for motif, quoi in _CHIFFRES_INTERDITS:
            m = re.search(motif, texte, re.IGNORECASE)
            assert not m, (
                "« %s » porte %s : « %s ». Aucune source primaire n'a été "
                "consultée — ce chiffre ne peut pas être publié."
                % (d['cle'], quoi, m.group(0)))


def test_la_regle_mordrait_sur_un_vrai_chiffre():
    """UNE RÈGLE QU'ON NE VOIT JAMAIS ÉCHOUER NE PROUVE RIEN. On lui soumet
    exactement ce qu'elle est censée arrêter : les trois formulations relevées
    dans la note professionnelle qui a servi de matière."""
    for piege in ("jusqu'à 50 % des audits et travaux",
                  "un taux d'aide pouvant atteindre 25 % du CAPEX",
                  "un PUE inférieur à 1,2",
                  "une aide de 300 000 €"):
        assert any(re.search(m, piege, re.IGNORECASE) for m, _ in _CHIFFRES_INTERDITS), (
            "la règle laisserait passer « %s »" % piege)


@pytest.mark.parametrize('reference', [
    "Règlement (UE) 2024/573 relatif aux gaz à effet de serre fluorés",
    "Règlement (UE) 2020/852 et règlement délégué (UE) 2021/2139",
    "activité 8.1 (traitement de données, hébergement)",
    "Loi n° 2021-1485 du 15 novembre 2021",
    "Décret n° 2019-771",
    # Le mot « tiers » au sens de personne — la phrase que la première version
    # de la règle refusait à tort.
    "Projet de livraison de chaleur fatale à un réseau ou à un tiers.",
])
def test_la_regle_laisse_passer_une_reference_legale(reference):
    """L'INVERSE EST AUSSI IMPORTANT. Une règle qui refuserait tout chiffre
    interdirait de citer un texte par son numéro — et rendrait le module
    inutilisable pour ce qu'il doit précisément faire."""
    for motif, quoi in _CHIFFRES_INTERDITS:
        m = re.search(motif, reference, re.IGNORECASE)
        assert not m, ("la règle prend « %s » pour %s dans une référence légale"
                       % (m.group(0), quoi))


def test_le_module_refuse_explicitement_de_chiffrer():
    """Quelqu'un cherchera un jour à calculer une aide depuis ce module. Il doit
    apprendre POURQUOI il n'y parviendra pas, pas se heurter à un attribut
    manquant."""
    with pytest.raises(NotImplementedError) as e:
        v.montant()
    assert 'instruction()' in str(e.value)


def test_la_sante_annonce_quaucun_montant_nest_calcule():
    assert v.sante()['calcule_des_montants'] is False


# ── L'ÉTAT D'INSTRUCTION EST PUBLIÉ, PAS DISSIMULÉ ───────────────────────

def test_chaque_dispositif_nomme_sa_source_primaire():
    """Un dispositif sans source à consulter n'est pas un dispositif : c'est
    une rumeur avec un nom propre."""
    for d in v.DISPOSITIFS:
        assert d.get('source'), "%s : aucune source primaire nommée" % d['cle']


def test_chaque_dispositif_non_instruit_dit_dou_vient_laffirmation():
    """« À instruire » ne suffit pas : il faut savoir ce qui est affirmé, et par
    qui, sans quoi personne ne peut juger de l'effort d'instruction."""
    for d in v.DISPOSITIFS:
        if d['etat'] != 'instruit':
            assert d.get('annonce'), (
                "%s : non instruit et sans mention de l'origine" % d['cle'])


def test_linstruction_restante_est_rendue_publiquement():
    r = v.instruction()
    assert len(r['a_instruire']) == len(
        [d for d in v.DISPOSITIFS if d['etat'] != 'instruit'])
    for e in r['a_instruire']:
        assert e['source'] and e['annonce'] and e['pays']
    assert 0 <= r['part_instruite'] <= 100


def test_letat_dun_dispositif_est_lun_des_etats_declares():
    for d in v.DISPOSITIFS:
        assert d['etat'] in v.INSTRUCTION, d['cle']


# ── LA LIAISON AVEC LE MOTEUR — LE POINT D'INTÉGRATION ───────────────────

def test_chaque_levier_cite_existe_dans_le_moteur():
    """UNE LIAISON MORTE NE SE VOIT PAS. Si un levier est renommé dans
    `decarbonation`, `pour_levier` devient muet et aucune page ne change
    d'apparence : le module cesse simplement de servir."""
    reels = {L['cle'] for L in decarb.LEVIERS}
    for d in v.DISPOSITIFS:
        for l in d['leviers']:
            assert l in reels, (
                "%s renvoie au levier « %s », absent du moteur de "
                "décarbonation" % (d['cle'], l))


def test_la_liste_attendue_colle_au_moteur():
    """Le garde-fou ci-dessus s'appuie sur `LEVIERS_ATTENDUS`. Si cette liste
    dérivait du moteur, elle validerait des liaisons mortes."""
    assert set(v.LEVIERS_ATTENDUS) == {L['cle'] for L in decarb.LEVIERS}


def test_aucun_dispositif_nest_orphelin():
    """Un dispositif relié à aucun levier est invisible depuis l'ingénierie :
    il n'apparaîtrait jamais au moment où l'arbitrage se fait."""
    for d in v.DISPOSITIFS:
        assert d['leviers'], "%s n'est relié à aucun levier" % d['cle']


def test_un_levier_qui_nouvre_rien_le_dit():
    """UN AXE QUI NE TROUVE RIEN DOIT LE DIRE. Renoncer à de la puissance
    installée est le levier le plus efficace du moteur, et aucun guichet ne le
    récompense. Taire ce constat laisserait croire à un oubli — ou pire,
    laisserait vendre une aide qui n'existe pas."""
    c = v.leviers_couverts()
    assert 'puissance' in c['sans_dispositif'], (
        "la puissance non installée s'est vu attribuer un dispositif : sur "
        "quelle source ?")
    assert c['sans_dispositif'], "aucun levier déclaré sans dispositif"
    assert set(c['ouvrants']) | set(c['sans_dispositif']) == set(v.LEVIERS_ATTENDUS)


def test_pour_levier_rend_ce_que_le_levier_ouvre():
    ouverts = {d['cle'] for d in v.pour_levier('chaleur')}
    assert 'fonds_chaleur' in ouverts
    assert 'ticfe_chaleur' in ouverts
    assert v.pour_levier('puissance') == []
    assert v.pour_levier('levier_qui_nexiste_pas') == []


# ── LES FILTRES ──────────────────────────────────────────────────────────

def test_un_regime_multi_pays_sort_pour_chacun_de_ses_pays():
    """Le régime nordique est déclaré « DK,FI ». Interroger le Danemark doit le
    trouver — sinon le filtre ne sert qu'à ceux qui connaissent déjà la clé."""
    for p in ('DK', 'FI', 'dk'):
        assert any(d['cle'] == 'chaleur_nordique' for d in v.dispositifs(pays=p)), p
    assert not any(d['cle'] == 'chaleur_nordique' for d in v.dispositifs(pays='FR'))


def test_les_natures_declarees_sont_toutes_connues():
    for d in v.DISPOSITIFS:
        assert d['nature'] in v.NATURES, d['cle']


def test_les_quatre_natures_sont_toutes_representees():
    """Un allègement, une subvention, un financement et un accès au marché ne
    s'instruisent pas de la même façon et ne se plaident pas devant le même
    interlocuteur. N'en couvrir que trois laisserait un angle mort."""
    vues = {d['nature'] for d in v.DISPOSITIFS}
    assert vues == set(v.NATURES), "natures absentes : %s" % (set(v.NATURES) - vues)


def test_aucune_cle_en_double():
    cles = [d['cle'] for d in v.DISPOSITIFS]
    assert len(cles) == len(set(cles))


def test_la_sante_ne_signale_aucun_probleme():
    assert v.sante()['problemes'] == []


# ── LES QUATRE CADRES QUI MANQUAIENT ─────────────────────────────────────

@pytest.mark.parametrize('cle,pourquoi', [
    ('reen', "loi française de sobriété numérique"),
    ('ddadue', "véhicule par lequel l'EED entre en droit français"),
    ('fgas', "contraint le choix des groupes froids"),
    ('commande_publique', "décide de l'admissibilité à concourir"),
])
def test_le_cadre_manquant_est_declare(cle, pourquoi):
    """Relevé en confrontant la table des textes à ce que suit réellement une
    mission de mise en conformité de centre de données."""
    assert cle in decarb.TEXTES, "%s absent — %s" % (cle, pourquoi)
    t = decarb.TEXTES[cle]
    assert t.get('nom') and t.get('dit') and t.get('portee')


@pytest.mark.parametrize('cle', ['reen', 'ddadue', 'fgas', 'commande_publique'])
def test_le_cadre_manquant_porte_sa_reserve(cle):
    """Aucun des quatre n'a été relevé sur source primaire. Un texte cité sans
    réserve se lit comme un texte instruit."""
    assert decarb.TEXTES[cle].get('reserve'), (
        "%s est cité sans réserve alors qu'il n'est pas instruit" % cle)


@pytest.mark.parametrize('cle', ['reen', 'ddadue', 'fgas', 'commande_publique'])
def test_le_cadre_manquant_est_rattache_a_une_etape(cle):
    """Le module refuse déjà à l'import un texte cité par aucune étape — et
    c'est ce garde-fou qui a arrêté ces quatre-là quand ils ont été ajoutés en
    vrac. La règle rend l'intention explicite plutôt que de dépendre d'un
    contrôle interne qu'on pourrait relâcher."""
    etapes = [e['code'] for e in decarb.ETAPES if cle in (e.get('textes') or [])]
    assert etapes, "%s n'est rattaché à aucune étape" % cle
