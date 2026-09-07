# -*- coding: utf-8 -*-
"""Les onze pièces mises en brouillon — et surtout CE QUI SORT DU CABINET.

CE QUE CES RÈGLES TIENNENT, ET CE QU'ELLES NE PEUVENT PAS TENIR. Elles
mesurent la CHARGE qui partirait chez Anthropic, la forme de la requête et les
barrières. Elles ne mesurent pas la qualité du brouillon : cela demande une
clé, un appel réel et un jugement humain. Le dire ici évite de croire cette
suite plus forte qu'elle n'est.

LA PROPRIÉTÉ CENTRALE : le texte des pièces du client ne sort pas. Ni en
entier, ni par citations. Une règle qui vérifierait « le module a l'air
prudent » ne vaudrait rien ; celles-ci prennent un vrai dossier de
consultation, construisent la charge, et cherchent dedans les phrases du
client.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                     # noqa: E402
import ao_redaction                                              # noqa: E402
import dossier_entreprise as _de                                 # noqa: E402

# UN VRAI DOSSIER, pas trois lignes : c'est le seul moyen que la recherche de
# fuite ait de quoi trouver. Chaque pièce porte des phrases qui n'existent
# nulle part ailleurs.
RC = """RÈGLEMENT DE LA CONSULTATION
Pouvoir adjudicateur : Communauté d'agglomération de l'Essai
Objet du marché : construction d'un centre de données de proximité
Procédure : procédure formalisée — appel d'offres ouvert
Allotissement : le marché est alloti en 3 lots.
Critères de jugement : valeur technique 60 %, prix 40 %.
Date limite de remise des offres : 30 novembre 2026 à 12h00
La visite du site est obligatoire et conditionne la recevabilité de l'offre.
Les candidats produiront une attestation d'assurance décennale nominative.
"""
CCAP = """CAHIER DES CLAUSES ADMINISTRATIVES PARTICULIÈRES
Pénalités de retard : 1/3000e du montant par jour calendaire de retard.
Retenue de garantie : 5 % du montant du marché, libérable à la levée des
réserves prononcée par le maître d'ouvrage après visite contradictoire.
Ordre de priorité des pièces : l'acte d'engagement prime le présent cahier.
"""
CCTP = """CAHIER DES CLAUSES TECHNIQUES PARTICULIÈRES
Performances exigées : PUE annualisé inférieur ou égal à 1,25 en régime établi.
La récupération de chaleur fatale alimentera le réseau urbain de la commune
voisine, avec un rendement de restitution mesuré au point de livraison.
"""


def _dossier():
    an = ao_dc.analyser([{"nom": "01_RC.pdf", "texte": RC},
                         {"nom": "02_CCAP.pdf", "texte": CCAP},
                         {"nom": "03_CCTP.pdf", "texte": CCTP}])
    r = ao_dc.remplir(fiche=_de.fiche_candidat()["fiche"], analyse=an,
                      saisies={})
    return an, r


def _phrases(texte, mini=34):
    """Les phrases du client, assez longues pour qu'un recoupement fortuit
    soit improbable."""
    out = []
    for ligne in re.split(r"[.\n]", texte):
        p = " ".join(ligne.split())
        if len(p) >= mini:
            out.append(p)
    return out


# ── 1. CE QUI SORT ────────────────────────────────────────────────────────

def test_le_TEXTE_des_pieces_du_client_ne_sort_PAS_du_cabinet():
    """LA RÈGLE CENTRALE, et la seule dont l'échec serait grave.

    Le contexte porte les VALEURS relevées — « procédure formalisée », « 3
    lots » —, jamais les phrases où elles ont été lues. On prend les phrases
    des trois pièces et l'on vérifie qu'aucune n'apparaît dans la charge.

    ON ÉNUMÈRE LES ONZE PIÈCES : la charge dépend de la pièce visée, et une
    fuite qui ne toucherait que le mémoire technique passerait sur un
    échantillon."""
    import json
    an, r = _dossier()
    attendues = _phrases(RC) + _phrases(CCAP) + _phrases(CCTP)
    assert len(attendues) >= 10, "le dossier d'essai est trop pauvre : %d" % len(attendues)
    fuites = []
    for piece in ao_redaction.pieces_redigeables(r):
        charge = json.dumps(ao_redaction.contexte(r, an, piece),
                            ensure_ascii=False)
        for p in attendues:
            if p in charge:
                fuites.append("%s : « %s »" % (piece["cle"], p[:60]))
    assert not fuites, "le texte du client sort : " + " · ".join(fuites[:5])


def test_les_CITATIONS_ne_sortent_pas_non_plus():
    """UNE CITATION EST UN EXTRAIT DE QUATRE CENTS CARACTÈRES du document de
    l'acheteur. La joindre au relevé enverrait le dossier par petits bouts —
    ce qui est le même défaut, en plus discret. On vérifie que l'analyse EN
    PRODUIT (sans quoi la règle ne mesurerait rien) et qu'aucune n'est
    transmise."""
    import json
    an, r = _dossier()
    idx = ao_dc._index_releves(an)
    # CE QU'ON MESURE : le CONTEXTE de la citation, pas la citation entière.
    #
    # POURQUOI LA RÈGLE A ÉTÉ REFORMULÉE. Écrite « aucune citation n'apparaît »,
    # elle tombait sur « procédure formalisée » — où la citation EST la valeur.
    # Exiger son absence reviendrait à interdire de transmettre le relevé
    # lui-même, c'est-à-dire tout le contexte. Ce qui ne doit pas sortir est ce
    # que la citation porte EN PLUS de la valeur : la phrase de l'acheteur
    # autour d'elle.
    autour = []
    for props in idx.values():
        for c in props:
            texte = " ".join((c.get("citation") or "").split())
            valeur = " ".join(str(c.get("valeur") or "").split())
            # LE SEUIL EST BAS — DOUZE CARACTÈRES — ET C'EST VOULU : ce qui
            # entoure une valeur dans le document du client est souvent son
            # INTITULÉ (« Objet du marché : … », « Date limite de remise des
            # offres : … »). C'est précisément ce qu'on ne veut pas voir
            # partir, et un seuil large le laisserait hors mesure.
            if len(texte) < len(valeur) + 12:
                continue
            autour.append((texte, valeur))
    assert len(autour) >= 3, (
        "aucune citation ne porte plus de contexte que sa valeur : la règle "
        "ne mesure plus la fuite (%d)" % len(autour))
    piece = next(p for p in ao_redaction.pieces_redigeables(r)
                 if p["cle"] == "memoire_technique")
    charge = json.dumps(ao_redaction.contexte(r, an, piece), ensure_ascii=False)
    for texte, valeur in autour:
        assert texte not in charge, (
            "une citation entière sort : « %s »" % texte[:70])
        # ET LE TÉMOIN FIN : les vingt caractères qui suivent la valeur dans la
        # phrase du client ne doivent pas la suivre dans la charge.
        i = texte.find(valeur) if valeur else -1
        if i >= 0:
            suite = texte[i + len(valeur):i + len(valeur) + 24].strip()
            if len(suite) >= 12:
                assert suite not in charge, (
                    "le texte qui entoure « %s » sort avec elle : « %s »"
                    % (valeur[:30], suite))


def test_seuls_les_releves_DECLARES_sortent():
    """UNE LISTE EXPLICITE, PAS « TOUS LES RELEVÉS ». Un relevé ajouté demain
    ne doit pas partir sans que quelqu'un l'ait décidé : c'est ce qui rend la
    règle de non-fuite tenable dans le temps."""
    an, r = _dossier()
    piece = next(p for p in ao_redaction.pieces_redigeables(r)
                 if p["cle"] == "moyens")
    ctx = ao_redaction.contexte(r, an, piece)
    sortis = set(ctx["consultation"])
    assert sortis, "aucun relevé ne sort : le brouillon serait générique"
    assert sortis <= set(ao_redaction.RELEVES_TRANSMIS), (
        "des relevés non déclarés sortent : %s"
        % sorted(sortis - set(ao_redaction.RELEVES_TRANSMIS)))
    # ET LA LISTE N'EST PAS « TOUT » : sinon elle ne déciderait rien.
    tous = {x["cle"] for x in ao_dc.RELEVES}
    assert set(ao_redaction.RELEVES_TRANSMIS) < tous, (
        "la liste couvre tous les relevés : elle n'arbitre plus rien")


# ── 2. LES BARRIÈRES ──────────────────────────────────────────────────────

def test_AUCUNE_declaration_ne_peut_etre_redigee_par_le_modele():
    """LA BARRIÈRE LA PLUS IMPORTANTE, ET ELLE EST STRUCTURELLE. Le DC1, le
    DC2 et la déclaration sur l'honneur portent des affirmations dont la
    fausseté est sanctionnée pénalement. Le module borne son périmètre aux
    voies « rediger » et « completer » ; aucune liste écrite à la main ne peut
    y faire entrer une déclaration par distraction."""
    _an, r = _dossier()
    redigeables = {p["cle"] for p in ao_redaction.pieces_redigeables(r)}
    interdites = {p["cle"] for p in r["pieces"]
                  if any(l.get("source") == "declaration"
                         for l in p.get("rubriques") or [])}
    assert interdites, "le dossier d'essai ne porte plus aucune déclaration"
    assert not (redigeables & interdites), (
        "une pièce à déclaration est rédigeable : %s"
        % sorted(redigeables & interdites))
    for cle in sorted(interdites):
        with pytest.raises(ao_redaction.RedactionError) as e:
            ao_redaction.rediger(cle, r)
        assert e.value.code == "piece_non_redigeable", (cle, e.value.code)


def test_le_brief_INTERDIT_d_inventer_et_de_declarer():
    """LES DEUX CONSIGNES QUI COMPTENT, et dont l'échec ne se voit pas à la
    lecture du brouillon : ce qui est inventé se lit comme ce qui est vrai."""
    _an, r = _dossier()
    piece = next(p for p in ao_redaction.pieces_redigeables(r)
                 if p["cle"] == "references")
    b = ao_redaction.brief(ao_redaction.contexte(r, None, piece))
    for attendu in ("N'INVENTEZ RIEN", "À COMPLÉTER",
                    "NE DÉCLAREZ RIEN", "sur l'honneur", "pénalement"):
        assert attendu in b, "le brief ne dit plus « %s »" % attendu
    # ET LA PIÈCE BLOQUANTE LE DIT.
    assert "BLOQUANTE" in b, "une pièce bloquante ne s'annonce pas comme telle"
    autre = next(p for p in ao_redaction.pieces_redigeables(r)
                 if not p.get("bloquant"))
    assert "BLOQUANTE" not in ao_redaction.brief(
        ao_redaction.contexte(r, None, autre)), (
        "toutes les pièces se disent bloquantes : la mention ne dit plus rien")


def test_sans_cle_le_module_REFUSE_au_lieu_de_rendre_un_document_vide():
    """UN REFUS NOMMÉ VAUT MIEUX QU'UNE PIÈCE VIDE. Sans clé, l'utilisateur
    doit apprendre que la rédaction assistée n'est pas configurée — pas
    recevoir un brouillon blanc qu'il croira normal."""
    _an, r = _dossier()
    garde = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        with pytest.raises(ao_redaction.RedactionError) as e:
            ao_redaction.rediger("moyens", r)
        assert e.value.code == "sans_cle", e.value.code
        assert e.value.status == 503
        assert "ANTHROPIC_API_KEY" in e.value.detail
    finally:
        if garde is not None:
            os.environ["ANTHROPIC_API_KEY"] = garde


# ── 3. LA REQUÊTE ─────────────────────────────────────────────────────────

def test_la_requete_demande_le_RAISONNEMENT_et_met_la_consigne_en_cache():
    """DEUX RÉGLAGES, DEUX RAISONS.

    LE RAISONNEMENT. L'assistant du site tourne raisonnement COUPÉ, pour la
    latence du chat — et le module porte même un rattrapage pour les brouillons
    que le modèle écrit alors dans sa réponse. Rédiger un mémoire technique est
    l'inverse : on veut le raisonnement, et trois secondes de plus ne coûtent
    rien sur un document qu'on relira une demi-heure.

    LE CACHE. Les onze pièces d'un même dossier partagent la consigne, et le
    dossier se relance à chaque correction de la fiche. Sans `cache_control`,
    ce préfixe est refacturé onze fois.

    ON LIT LA REQUÊTE RÉELLEMENT ENVOYÉE, pas la source : un réglage écrit et
    jamais transmis ne règle rien."""
    _an, r = _dossier()
    vu = {}

    class _Flux(object):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get_final_message(self):
            class _U(object):
                input_tokens = 10
                output_tokens = 20
                cache_creation_input_tokens = 0
                cache_read_input_tokens = 0

            class _B(object):
                type = "text"
                text = "## Moyens\n\n[À COMPLÉTER : effectif] à porter."

            class _M(object):
                content = [_B()]
                usage = _U()
                model = ao_redaction.MODELE
                stop_reason = "end_turn"
                stop_details = None
            return _M()

    class _Messages(object):
        def stream(self, **kw):
            vu.update(kw)
            return _Flux()

    class _Client(object):
        messages = _Messages()

    class _Faux(object):
        NotFoundError = AuthenticationError = RateLimitError = type(
            "E", (Exception,), {})
        APIStatusError = APIConnectionError = type("E2", (Exception,), {})

        @staticmethod
        def Anthropic():
            return _Client()

    garde_cle = os.environ.get("ANTHROPIC_API_KEY")
    os.environ["ANTHROPIC_API_KEY"] = "essai"
    garde = ao_redaction._client
    ao_redaction._client = lambda: _Faux
    try:
        out = ao_redaction.rediger("moyens", r)
    finally:
        ao_redaction._client = garde
        if garde_cle is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)

    assert vu["model"] == ao_redaction.MODELE
    assert vu["thinking"] == {"type": "adaptive"}, vu.get("thinking")
    assert vu["system"][0]["cache_control"] == {"type": "ephemeral"}, vu["system"]
    assert vu["timeout"] == ao_redaction.DELAI
    # ET LE RÉSULTAT PORTE DE QUOI JUGER : ce qui reste à compléter se compte.
    assert out["a_completer"] == 1, out
    assert out["markdown"].startswith("## "), out["markdown"][:40]
    assert out["tronque"] is False


def test_le_modele_par_defaut_est_celui_qu_ANTHROPIC_recommande_aujourd_hui():
    """ÉPINGLÉ, ET SÉPARÉ DE CELUI DE L'ASSISTANT. Les deux usages n'ont pas
    les mêmes contraintes — le chat vise la latence, la rédaction la qualité —
    et un seul réglage pour les deux force à choisir lequel on dégrade."""
    import assistant
    assert ao_redaction.MODELE == os.environ.get(
        "AO_REDACTION_MODEL", "claude-opus-5")
    assert "AO_REDACTION_MODEL" in io.open(
        os.path.join(ICI, "ao_redaction.py"), encoding="utf-8").read()
    assert ao_redaction.MODELE != assistant.CLAUDE_MODEL or \
        os.environ.get("AO_REDACTION_MODEL"), (
        "la rédaction et le chat partagent le même réglage")


# ── 4. LE REGISTRE DIT CE QUI SORT ────────────────────────────────────────

def test_le_registre_RGPD_dit_ce_qui_part_chez_Anthropic():
    """UN REGISTRE QUI PROMET CE QUE LE CODE NE TIENT PLUS EST PIRE QU'UN
    REGISTRE ABSENT.

    L'entrée « dossier-marche » affirmait : « Le contenu ne part vers aucun
    modèle de langage ». C'était vrai tant que le remplissage était mécanique.
    Ouvrir la rédaction assistée rend cette phrase FAUSSE — et c'est le genre
    d'écart qu'on ne voit jamais depuis le code.

    LA RÈGLE MESURE LES DEUX SENS : que le registre nomme ce qui sort, et
    qu'il continue d'affirmer ce qui ne sort pas."""
    import rgpd
    e = next(x for x in rgpd.REGISTRE if x["id"] == "dossier-marche")
    t = e["transferts"]
    assert "Anthropic" in t, "le registre ne nomme pas le destinataire"
    assert "États-Unis" in t, "le registre ne dit pas où part le transfert"
    for quoi in ("VALEURS", "Ni le texte des pièces", "citations"):
        assert quoi in t, "le registre ne dit pas « %s »" % quoi
    assert "Le contenu ne part vers aucun modèle de langage" not in t, (
        "le registre promet encore ce que la rédaction assistée ne tient plus")
    # ET CE QUI RESTE VRAI EST TOUJOURS AFFIRMÉ.
    assert "expressions régulières" in t and "jamais par génération" in t, (
        "le registre a perdu ce qui reste vrai de l'extraction")
    # LE DESTINATAIRE EST DÉJÀ AU REGISTRE DES SOUS-TRAITANTS : sans cela, la
    # ligne ci-dessus nommerait un tiers que le registre ignore.
    assert any("Anthropic" in (s.get("nom") or "")
               for s in rgpd.SOUS_TRAITANTS), (
        "Anthropic n'est pas au registre des sous-traitants")
