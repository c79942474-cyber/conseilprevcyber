"""La page de veille : ce qu'elle sert, et ce qu'elle ne détient pas.

LE DÉFAUT DE STRUCTURE QUE CES RÈGLES TIENNENT. La page portait sa propre table
de classement, écrite dans son script. Tant qu'il s'agissait de huit familles de
produits, cela pouvait passer ; avec six axes adossés au vocabulaire de la base
documentaire, une copie côté page serait un second vocabulaire — et un filtre
qui ne désigne plus rien ne lève aucune erreur, il rend simplement zéro
résultat. La page ne doit donc rien détenir : elle affiche ce que l'API classe.
"""
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import automation                                                   # noqa: E402
import veille_facettes as vf                                        # noqa: E402
import veille_sources                                               # noqa: E402

PAGE = open(os.path.join(ICI, "veille.html"), encoding="utf-8").read()


def _script_execute():
    """Le script de la page, COMMENTAIRES RETIRÉS.

    LA PREMIÈRE VERSION DE CES RÈGLES LISAIT LE FICHIER ENTIER, et elles ont
    échoué sur leur propre commentaire — celui qui explique quelle taxonomie a
    été retirée. Une règle qui compte les MOTS du fichier ne dit rien de ce que
    la page FAIT : elle serait restée verte devant une table de classement dont
    on aurait renommé les entrées, et elle tombe devant une phrase d'explication
    qui ne change rien. On ne regarde donc que ce qui s'exécute.

    Le pied de page et la navigation sont également hors champ : « NIS2 »,
    « DORA » ou « Veille » y sont de la prose et des liens, pas un vocabulaire
    de classement.
    """
    debut = PAGE.index("(function(){")
    fin = PAGE.index("})();", debut)
    code = PAGE[debut:fin]
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    return re.sub(r"^\s*//.*$", "", code, flags=re.M)


SCRIPT = _script_execute()


# ── 1. Le titre demandé ────────────────────────────────────────────────────

def test_le_titre_annonce_la_veille_reglementaire():
    attendu = "Veille : actualités réglementaires, nouveaux standards et normes"
    assert attendu in PAGE
    assert "réglementaires" in PAGE and "standards" in PAGE


def test_les_quatre_sujets_sont_annonces_au_lecteur():
    for mot in ("industrielle", "IA", "GRC", "centres de données"):
        assert mot in PAGE, mot


# ── 2. La page ne détient aucun vocabulaire ────────────────────────────────

def test_la_page_ne_recopie_pas_le_vocabulaire_de_la_maison():
    """LA RÈGLE DE STRUCTURE. Si un thème de la base documentaire apparaissait
    en dur dans la page, il y aurait deux exemplaires du vocabulaire — et c'est
    celui qu'on oublie de corriger qui reste, sans que rien ne le dise."""
    # LA BONNE LISTE EST CELLE QUE LE MODULE PEUT ÉMETTRE — pas tout
    # `rag_store.THEMES` : « Veille » y figure et est aussi le sujet de la page,
    # qui a le droit d'écrire son propre nom dans un message d'erreur. Ce qu'on
    # cherche, ce sont les valeurs qui divergeraient si la page tenait sa
    # propre table.
    emises = [n for n, _ in (vf.THEMES + vf.STANDARDS + vf.SECTEURS + vf.ENTREPRISES)]
    recopies = [t for t in emises if t in SCRIPT]
    assert not recopies, "vocabulaire recopié dans le script : %s" % recopies[:5]


def test_la_page_ne_contient_plus_la_taxonomie_des_vulnerabilites():
    """« Microsoft & Windows », « Linux & Unix », « Mobile » : les facettes d'un
    flux de vulnérabilités, sans objet devant un communiqué de la Commission."""
    for ancien in ("Linux & Unix", "Bases de donn\u00e9es", "Microsoft & Windows"):
        assert ancien not in SCRIPT, ancien
    # Et surtout : plus aucune expression régulière de classement. C'est la
    # forme qui compte, pas les noms — renommer les entrées aurait laissé la
    # règle précédente verte.
    assert "THEME_RULES" not in SCRIPT
    assert SCRIPT.count("/scada|") == 0


def test_les_six_axes_sont_proposes_au_lecteur():
    for identifiant in ("vdomaine", "vpays", "vtheme", "vstandard",
                        "vsecteur", "ventreprise", "vreg"):
        assert 'id="%s"' % identifiant in PAGE, identifiant


# ── 3. Ce que l'API sert ───────────────────────────────────────────────────

def test_la_veille_est_publique_et_rend_ses_facettes(anonyme):
    j = anonyme.get("/api/veille").get_json()
    assert j["ok"] is True
    assert "facettes" in j and "libelles_pays" in j["facettes"]
    assert set(j["facettes"]).issuperset(
        {"themes", "standards", "secteurs", "entreprises", "pays", "reglementaire"})


def test_les_elements_servis_sont_deja_classes(anonyme, monkeypatch):
    monkeypatch.setattr(automation, "veille_list", lambda limit=60: [
        {"guid": "g", "source": "cisa_ics", "title": "IEC 62443 advisory for SCADA",
         "link": "https://x", "published": 0, "resume": "Siemens SIMATIC."}])
    j = anonyme.get("/api/veille").get_json()
    it = j["items"][0]
    assert it["facettes"]["pays"] == "US"
    assert "IEC 62443" in it["facettes"]["standards"]
    assert "Siemens" in it["facettes"]["entreprises"]
    assert it["emetteur"] and it["lien_libelle"]


def test_la_mention_de_transparence_suit_la_realite(anonyme, monkeypatch):
    """UNE MENTION QUI DÉCRIT AUTRE CHOSE QUE LA RÉALITÉ VAUT MOINS QUE PAS DE
    MENTION. Par défaut on reprend le chapeau publié par la source : il n'y a
    aucune génération, et l'annoncer serait faux."""
    monkeypatch.setattr(automation, "VEILLE_RESUME", False)
    assert anonyme.get("/api/veille").get_json()["resume_ia"] is False
    monkeypatch.setattr(automation, "VEILLE_RESUME", True)
    assert anonyme.get("/api/veille").get_json()["resume_ia"] is True


def test_la_page_n_affiche_la_mention_que_si_l_api_le_dit():
    """Le pendant côté page : la mention est masquée, et n'apparaît que sur
    `resume_ia`. Une mention affichée en dur redeviendrait fausse."""
    assert 'id="vnote" style="display:none"' in PAGE
    assert "j.resume_ia" in PAGE


def test_le_filtre_par_pays_est_servi_par_l_api(anonyme, monkeypatch):
    monkeypatch.setattr(automation, "veille_list", lambda limit=60: [
        {"guid": "a", "source": "cisa_ics", "title": "US", "link": "", "published": 0, "resume": ""},
        {"guid": "b", "source": "certfr_avis", "title": "FR", "link": "", "published": 0, "resume": ""}])
    j = anonyme.get("/api/veille?pays=FR").get_json()
    assert [i["title"] for i in j["items"]] == ["FR"]


# ── 4. La table de santé ───────────────────────────────────────────────────

def test_la_sante_des_flux_est_reservee_a_l_administrateur(anonyme, connecte):
    assert anonyme.get("/api/admin/veille/sante").status_code in (401, 403, 302)
    assert connecte.get("/api/admin/veille/sante").status_code in (401, 403, 302)


def test_la_sante_nomme_chaque_flux_du_catalogue(admin):
    j = admin.get("/api/admin/veille/sante").get_json()
    assert j["total"] == len(veille_sources.SOURCES)
    cles = {l["cle"] for l in j["sources"]}
    assert cles == {s["cle"] for s in veille_sources.SOURCES}
    for ligne in j["sources"]:
        assert ligne["sante"] in ("ok", "muet", "jamais_joint", "pas_encore_essaye")
