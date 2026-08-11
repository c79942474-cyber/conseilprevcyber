# DICT — Disponibilité, Intégrité, Confidentialité, Traçabilité — et RGPD :
# chaque mesure DÉCLARÉE doit exister dans le code, et chaque manque trouvé à
# l'audit de ce jour est figé ici pour ne pas revenir.
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import clients_store  # noqa: E402


def _src(nom):
    return open(os.path.join(ICI, nom), encoding="utf-8").read()


# ── Intégrité : les pièces clients ─────────────────────────────────────────

def test_un_executable_deguise_en_pdf_est_refuse():
    try:
        clients_store._controler_piece("contrat.pdf", "pdf", b"MZ" + b"x" * 200)
        raise AssertionError("un exécutable Windows est passé")
    except clients_store.ClientsError as e:
        assert "refusee" in e.code and e.status == 422


def test_un_executable_deguise_en_eml_est_refuse():
    try:
        clients_store._controler_piece("mail.eml", "eml", b"\x7fELF" + b"x" * 100)
        raise AssertionError("un exécutable Linux est passé")
    except clients_store.ClientsError as e:
        assert e.code == "piece_refusee_executable"


def test_le_doc_ancien_format_reste_admis_et_c_est_dit():
    # Le .doc EST un conteneur OLE : refusé partout ailleurs, admis ici
    # explicitement — le retirer priverait les clients de leurs contrats.
    clients_store._controler_piece("contrat.doc", "doc",
                                   b"\xd0\xcf\x11\xe0" + b"x" * 100)
    s = _src("clients_store.py")
    assert "admise ici et seulement ici" in s


def test_un_pdf_propre_est_admis():
    clients_store._controler_piece("note.pdf", "pdf", b"%PDF-1.4 contenu propre")


def test_le_depot_memoire_passe_par_le_controle():
    st = clients_store.MemoryClientsStore()
    cid = st.create({"entreprise": "Essai SA", "email": "a@b.fr"},
                    actor="test")["id"]
    up = st.doc_upload_create(cid, "piege.pdf", 0)
    st.doc_upload_chunk(up, 0, b"MZ" + b"x" * 100)
    try:
        st.doc_upload_finish(cid, up, "contrat", actor="test", filename="piege.pdf")
        raise AssertionError("le dépôt aurait dû être refusé")
    except clients_store.ClientsError as e:
        assert "refusee" in e.code
    # …et le refus est au journal du client.
    assert any(ev["action"] == "piece_refus" for ev in st.events(limit=10))


def test_une_piece_alteree_ne_se_sert_pas():
    st = clients_store.MemoryClientsStore()
    cid = st.create({"entreprise": "Essai SA", "email": "a@b.fr"},
                    actor="test")["id"]
    up = st.doc_upload_create(cid, "preuve.pdf", 0)
    st.doc_upload_chunk(up, 0, b"%PDF-1.4 preuve de consentement")
    meta = st.doc_upload_finish(cid, up, "consentement", actor="test",
                                filename="preuve.pdf")
    # Altération en base, empreinte inchangée : la remise doit refuser.
    st._docs[cid][meta["id"]]["data"] = b"%PDF-1.4 preuve FALSIFIEE ici"
    try:
        st.doc_get(cid, meta["id"], actor="test")
        raise AssertionError("une pièce altérée a été servie comme authentique")
    except clients_store.ClientsError as e:
        assert e.code == "integrite_alteree"
    v = st.docs_verify(actor="test")
    assert len(v["ecarts"]) == 1 and v["ecarts"][0]["id"] == meta["id"]


# ── Traçabilité : les gestes qui n'en avaient pas ──────────────────────────

def test_les_gestes_sensibles_sont_journalises():
    app_src = _src("app.py")
    auth_src = _src("auth.py")
    attendus_app = ["document.chargement", "livrable.generation",
                    "livrable.suppression", "clients.consultation",
                    "clients.verification"]
    for a in attendus_app:
        assert '"%s"' % a in app_src, "action absente du journal : %s" % a
    attendus_auth = ["motdepasse.reinitialise", "motdepasse.demande",
                     "admin_gate.ok", "admin_gate.echec", "compte.export"]
    for a in attendus_auth:
        assert '"%s"' % a in auth_src, "action absente du journal : %s" % a


# ── Confidentialité : la minimisation avant le fournisseur de modèle ───────

def test_le_message_de_contact_est_minimise_avant_le_modele():
    s = _src("app.py")
    i = s.index("def _classify_contact")
    bloc = s[i:i + 1600]
    assert "minimisation.masquer" in bloc, (
        "le message brut du formulaire partait chez le fournisseur de modèle")


def test_le_registre_declare_le_fournisseur_de_modele():
    assert "fournisseur du modèle" in _src("rgpd.py")


# ── RGPD : les droits outillés, la conservation exécutée ───────────────────

def test_l_export_de_compte_existe_et_est_ferme():
    s = _src("auth.py")
    i = s.index('"/api/auth/export"')
    bloc = s[i:i + 400]
    assert "@login_required" in bloc, "l'export doit être réservé au titulaire"


def test_la_revue_des_comptes_inactifs_est_executee():
    s = _src("automation.py")
    assert "last_login" in s and "24 mois" in s, (
        "la revue déclarée au registre doit être exécutée par un travail")
