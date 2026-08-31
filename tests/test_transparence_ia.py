# -*- coding: utf-8 -*-
"""Article 50 de l'IA Act : trois obligations, et une seule pèse sur le marquage.

    marquage technique du fournisseur
  ≠ obligation légale de transparence du déployeur
  ≠ obligations contractuelles

CE QUE CES RÈGLES PROTÈGENT. Le site confondait les trois, et la confusion se
voyait dans les deux sens.

  1. Le marquage « AI-generated » était apposé sur TOUT export. Sur les treize
     points d'export, la moitié ne passe aucun modèle : une checklist IEC 62443
     remplie à la main par le client sortait avec, dans les propriétés du
     fichier, la mention « contenu généré par IA » et l'auteur « CONSEILPREV —
     assistance par intelligence artificielle ». L'article 50.2 demande au
     FOURNISSEUR de marquer ce que SON système génère ; l'apposer ailleurs
     n'est pas une prudence, c'est une déclaration fausse — et une marque
     posée partout ne signale plus rien.

  2. La mention VISIBLE se réclamait de l'article 50. Elle disait, sous chaque
     analyse juridique, « information donnée au titre de l'article 50 », et
     dans les propriétés de chaque document « signalé comme tel au titre du
     règlement ». Le déployeur n'a pourtant aucune obligation générale
     d'indiquer qu'un contenu a été produit avec une IA : ses obligations
     d'information visent des cas nommés (§1 interaction, §3 émotions et
     biométrie, §4 hypertrucages et textes publiés d'intérêt public), dont
     aucun ne couvre un livrable remis à un client. Ce qui peut l'imposer est
     ailleurs — le contrat, la politique fournisseurs du client, la
     confidentialité.

CE QU'ELLES NE FONT PAS. Elles ne disent pas le droit : elles vérifient que le
dépôt ne se réclame pas d'une obligation qu'il n'a pas, et que ce qu'il marque
correspond à ce qu'il a produit.
"""
import ast
import io
import os
import re
import sys
import zipfile

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import conformite_mesures  # noqa: E402
import juridique  # noqa: E402
import livrables_export as LE  # noqa: E402
import rgpd  # noqa: E402

MD = "# Piece de controle\n\nUn paragraphe, jamais distribue.\n"


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def _docx(meta):
    """Le document RÉELLEMENT construit, ouvert et lu — jamais supposé."""
    blob = LE.build_docx(MD, meta)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return (z.read("docProps/core.xml").decode("utf-8", "replace"),
                z.read("word/document.xml").decode("utf-8", "replace"))


# ── 1. Le marquage machine suit ce qui a réellement écrit ──────────────────

def test_un_document_calcule_ne_porte_pas_le_marquage_de_contenu_genere():
    """LE DÉFAUT D'ORIGINE. Une checklist calculée sortait « AI-generated »."""
    core, _ = _docx({"label": "Checklist", "ia": False,
                     "referentiel": "Parcours IEC 62443 v0"})
    assert LE.MARQUE_IA not in core
    assert "intelligence artificielle" not in core
    # Et ce qu'il porte À LA PLACE dit sa vraie nature : l'absence de marque
    # ne suffit pas, un document sans aucune propriété serait « conforme »
    # à la règle précédente et ne dirait rien.
    assert "deterministe" in core
    assert "Parcours IEC 62443 v0" in core


def test_un_document_redige_par_un_modele_porte_le_marquage():
    core, _ = _docx({"label": "Note", "ia": True, "model": "modele-x"})
    assert LE.MARQUE_IA in core
    # LE MODÈLE ET LE PRODUCTEUR AUSSI, et pas seulement la catégorie : le
    # dépôt PROMET « outil producteur, modèle utilisé » dans les propriétés
    # (rgpd.ART50, politique de confidentialité). Une promesse qu'on ne relit
    # pas dans le fichier lui-même est une promesse.
    assert "modele-x" in core
    assert "CONSEILPREV" in core
    assert "fournisseur du systeme" in core


def test_une_propriete_trop_longue_n_emporte_pas_les_autres(monkeypatch):
    """LE PIÈGE, ÉPROUVÉ. Les sept propriétés étaient posées dans un seul
    `try` : la première qui refusait emportait toutes les suivantes, en
    silence. Une note de 369 caractères — la limite du format est 255 — a
    ainsi fait disparaître d'un coup la note ET l'auteur, sans qu'aucune
    erreur ne remonte et sans qu'aucune règle ne tombe."""
    vrai = LE._marque_ia
    monkeypatch.setattr(LE, "_marque_ia",
                        lambda meta: dict(vrai(meta), note="N" * 400))
    core, _ = _docx({"label": "Note", "ia": True, "model": "modele-x"})
    assert "modele-x" in core, "une note trop longue a emporté l'auteur"
    assert LE.MARQUE_IA in core


def test_le_marquage_manquant_vaut_marquage():
    """LE SENS DU DOUTE. `ia` absent marque : un marquage en trop se corrige,
    un marquage perdu est une obligation du fournisseur que personne ne voit
    partir."""
    core, _ = _docx({"label": "Sans drapeau"})
    assert LE.MARQUE_IA in core


def test_le_marquage_ne_se_reclame_plus_d_une_obligation_du_deployeur():
    """La note des propriétés disait « signalé comme tel au titre du
    règlement » : elle attribuait au déployeur une obligation que l'art. 50
    met sur le fournisseur."""
    note = LE._marque_ia({"ia": True, "model": "m"})["note"].lower()
    assert "fournisseur" in note
    assert "machine" in note
    assert "signale comme tel au titre" not in note


# ── 2. La mention visible dit ce qui a écrit, et le statut ne dépend pas ───

def test_la_mention_visible_suit_ce_qui_a_ecrit():
    _, corps_ia = _docx({"label": "Note", "ia": True, "model": "m"})
    _, corps_calc = _docx({"label": "Checklist", "ia": False})
    dit_ia = "modèle de langage" in corps_ia and "aide d" in corps_ia
    dit_calc = "calcul déterministe" in corps_calc
    assert dit_ia and dit_calc
    # Et surtout : chacun ne dit QUE le sien.
    assert "aucun modèle de langage n" not in corps_ia
    assert "avec l’aide d’un modèle" not in corps_calc


def test_le_statut_de_brouillon_ne_depend_pas_de_l_ia():
    """Le statut n'a rien à voir avec l'article 50 : un calcul non visé est un
    brouillon comme un texte non visé."""
    for meta in ({"label": "A", "ia": True}, {"label": "B", "ia": False}):
        _, corps = _docx(meta)
        assert "Brouillon" in corps


def test_un_document_vise_ne_se_termine_plus_sur_brouillon():
    """Le pied de page suivait déjà le statut réel ; la note finale, non — un
    document visé se contredisait page de garde contre dernière ligne."""
    assert "Brouillon" not in LE._mention_finale({"statut": "Visé", "ia": True})
    assert "Brouillon" in LE._mention_finale({"ia": True})


# ── 3. Chaque point d'export déclare ce qui a écrit ────────────────────────

def _points_d_export(source):
    """Chaque appel à build_docx/build_pdf, avec les clés du dict `meta` que la
    même fonction lui assigne. Lu par l'ARBRE et non par le texte : un
    commentaire qui contiendrait « ia » ne satisferait pas la règle."""
    arbre = ast.parse(source)
    out = []
    for fn in ast.walk(arbre):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        noms = set()
        for n in ast.walk(fn):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("build_docx", "build_pdf")
                    and len(n.args) >= 2 and isinstance(n.args[1], ast.Name)):
                noms.add(n.args[1].id)
        if not noms:
            continue
        cles = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id in noms:
                        cles |= {k.value for k in n.value.keys
                                 if isinstance(k, ast.Constant)}
        out.append((fn.name, cles))
    return out


def test_chaque_point_d_export_declare_ce_qui_a_ecrit_le_document():
    """LA RÈGLE QUI TIENT DEMAIN. Une quatorzième route d'export qui oublie le
    drapeau la fait tomber ici, et non chez un client qui reçoit une checklist
    marquée « générée par IA »."""
    points = _points_d_export(_src("app.py"))
    assert len(points) >= 13, "les points d'export ont disparu de l'analyse"
    muets = sorted(nom for nom, cles in points if "ia" not in cles)
    assert not muets, "points d'export sans drapeau « ia » : " + ", ".join(muets)


def test_le_predicat_de_redaction_est_celui_du_cartouche():
    """UNE SEULE DÉCISION. Le marquage et la ligne « Établi par » doivent dire
    la même chose : deux exemplaires divergeraient, et c'est celui qu'on
    oublie de corriger qui resterait."""
    import app
    assert app._redige_par_modele("trame-moteur_seul") is False
    assert app._redige_par_modele("modele-x") is True
    # Un code vide ne PROUVE rien : il marque.
    assert app._redige_par_modele("") is True
    assert "Moteur" in app._auteur_document("trame-moteur_seul")
    assert "assistée" in app._auteur_document("modele-x")


# ── 4. Le référentiel nomme les trois obligations ─────────────────────────

def test_les_trois_obligations_sont_nommees_et_distinguees():
    roles = rgpd.TRANSPARENCE_IA
    assert len(roles) == 3
    for r in roles:
        for champ in ("role", "qui", "ref", "dit", "ne_dit_pas", "chez_nous"):
            assert (r.get(champ) or "").strip(), "%s sans %s" % (r.get("role"), champ)
    textes = " ".join(r["role"].lower() for r in roles)
    assert "fournisseur" in textes
    assert "déployeur" in textes
    assert "contractuel" in textes


def test_le_role_du_deployeur_refuse_l_obligation_generale():
    """LE CŒUR DE LA DISTINCTION. Si cette entrée cesse de dire qu'aucune
    obligation générale n'existe, le site recommence à en inventer une."""
    dep = [r for r in rgpd.TRANSPARENCE_IA
           if "déployeur" in r["role"].lower()][0]
    nd = dep["ne_dit_pas"].lower()
    assert "aucune obligation générale" in nd
    # Et il ne se contente pas de nier : il nomme les cas où le déployeur DOIT
    # informer, sans quoi la négation se lirait comme « jamais rien ».
    for par in ("§1", "§3", "§4"):
        assert par in dep["ref"] or par in dep["dit"]


def test_le_role_du_fournisseur_est_celui_du_marquage_machine():
    fou = [r for r in rgpd.TRANSPARENCE_IA
           if "fournisseur" in r["role"].lower()][0]
    assert "50 §2" in fou["ref"] or "50.2" in fou["ref"]
    assert "machine" in fou["dit"].lower()
    assert "aucune phrase" in fou["ne_dit_pas"].lower()


def test_la_troisieme_obligation_est_hors_ia_act():
    ctr = [r for r in rgpd.TRANSPARENCE_IA
           if "contractuel" in r["role"].lower()][0]
    assert "hors ia act" in ctr["ref"].lower()
    assert "contrat par contrat" in ctr["ne_dit_pas"].lower()


# ── 5. Les mesures déclarées ne se réclament plus du mauvais article ──────

def test_aucune_mesure_visible_ne_se_fonde_sur_l_article_50_2():
    """SUR TOUT LE REGISTRE, DANS LES DEUX SENS. L'art. 50.2 vise le marquage
    lisible par une MACHINE ; une mention lisible par un humain qui s'en
    réclame attribue au déployeur une obligation qu'il n'a pas."""
    visibles = [a for a in rgpd.ART50
                if re.search(r"visible|lisible par un humain", a["mesure"], re.I)]
    assert visibles, "plus aucune mesure de mention visible dans le registre"
    for a in visibles:
        assert "50.2" not in a["ref"], a["mesure"] + " se réclame de l'art. 50.2"
        assert "engagement" in a["ref"].lower()

    machines = [a for a in rgpd.ART50
                if re.search(r"lisible par une machine", a["mesure"], re.I)]
    assert machines, "plus aucune mesure de marquage machine dans le registre"
    for a in machines:
        assert "50.2" in a["ref"]
        assert "fournisseur" in a["detail"].lower()


def test_la_mention_des_analyses_juridiques_ne_se_reclame_plus_de_l_article_50():
    """Elle s'affiche sous chaque analyse et s'imprime dans chaque note de
    relecture : c'était le point de contact le plus fréquent avec la
    confusion."""
    m = juridique.MENTION_IA.lower()
    assert "au titre de l" not in m
    assert "fournisseur" in m and "machine" in m
    assert "déployeur" in m


# ── 6. Le contrôle mesuré voit les deux dérives ───────────────────────────

def test_le_controle_de_marquage_voit_une_marque_posee_partout(monkeypatch):
    """SANS TÉMOIN NÉGATIF, LE CONTRÔLE VALIDAIT LE DÉFAUT. Il ne vérifiait
    que la présence de la marque sur un document déclaré rédigé par un
    modèle : un marquage inconditionnel passait au vert."""
    vrai = LE._marque_ia
    monkeypatch.setattr(LE, "_marque_ia",
                        lambda meta: vrai(dict(meta or {}, ia=True)))
    c = conformite_mesures._m_marquage_exports()
    assert c["statut"] == "non-conforme"
    assert "calcul" in c["constat"]


def test_le_controle_de_marquage_voit_une_marque_disparue(monkeypatch):
    vrai = LE._marque_ia
    monkeypatch.setattr(LE, "_marque_ia",
                        lambda meta: vrai(dict(meta or {}, ia=False)))
    c = conformite_mesures._m_marquage_exports()
    assert c["statut"] == "non-conforme"
    assert "fournisseur" in c["constat"]


def test_le_controle_de_marquage_est_vert_quand_les_deux_temoins_disent_vrai():
    c = conformite_mesures._m_marquage_exports()
    assert c["mode"] == "mesure" and c["statut"] == "conforme"


# ── 7. Les pages servent la distinction, elles ne la recopient pas ────────

def test_le_dossier_public_sert_les_trois_obligations():
    etat = rgpd.etat()
    assert len(etat.get("transparence_ia") or []) == 3


def test_la_page_publique_lit_le_referentiel_et_ne_le_recopie_pas():
    """La page doit AFFICHER les trois rôles depuis /api/conformite. Une
    seconde copie du texte dans le HTML dériverait du référentiel, et c'est
    l'exemplaire qu'on oublie de corriger qui resterait."""
    page = _src("conformite.html")
    assert "transparence_ia" in page
    assert "cfRoles" in page
    # Le texte des rôles n'est PAS écrit en dur dans la page.
    for r in rgpd.TRANSPARENCE_IA:
        assert r["dit"][:60] not in page


def test_la_console_de_generation_rappelle_ce_qui_est_du_au_client():
    """C'est là que le consultant décide de ce qu'il écrit au client : la
    distinction n'a de valeur qu'au moment de la décision."""
    page = _src("admin-livrables.html")
    assert "impose pas" in page
    assert "article 50" in page.lower()
    assert "contrat" in page.lower()
