# -*- coding: utf-8 -*-
"""RECETTE — « Charger la fiche du cabinet », dans un vrai navigateur.

CE QU'AUCUNE RÈGLE DE LA SUITE NE PEUT ÉPROUVER. `tests/test_ao_fiche_cabinet.py`
lit le source : il vérifie que la route existe, qu'elle est fermée à
l'administration, que l'ordre « la saisie l'emporte » est écrit. Il ne voit
pas les CHAMPS se remplir, et ne peut pas constater qu'une valeur déjà tapée
survit au clic — c'est du DOM, et le DOM n'existe qu'en navigateur.

CE QUE CETTE RECETTE MESURE, dans cet ordre :
  1. la fiche se dessine et ses champs sont vides au départ ;
  2. une valeur tapée à la main y reste après le clic ;
  3. les autres champs reçoivent bien les valeurs du dossier d'entreprise ;
  4. le message annonce des comptes qui CORRESPONDENT à ce que le DOM porte —
     c'est le point le plus fragile : le défaut corrigé en amont était
     précisément un message juste au-dessus de champs restés vides.

ELLE N'ÉCRIT RIEN. Lecture seule côté serveur ; le seul effet de bord est le
stockage local du navigateur, jeté avec le profil.
"""
import http.cookies
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

PORT = int(os.environ.get("RECETTE_PORT", "5099"))
BASE = "http://127.0.0.1:%d" % PORT
ADMIN = "recette@local.test"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
SAISIE = "ENTREPRISE CLIENTE — SAISIE MANUELLE"


def assurer_admin():
    import auth
    u = auth.store.get(ADMIN)
    if u:
        auth.store.update(ADMIN, role="admin", approved=True,
                          email_verified=True)
        return
    auth.store.create({"email": ADMIN, "name": "Recette", "org": "Essai",
                       "password_hash": "x", "email_verified": True,
                       "approved": True, "role": "admin", "verify_token": None,
                       "verify_expire": None, "approve_token": None,
                       "reset_token": None, "reset_expire": None,
                       "created_at": 0, "last_login": None})


def cookie_de_session():
    """Le même cookie que produirait une connexion — signé par l'application.

    On ne fabrique PAS un droit : on reproduit la séance d'un compte qui
    existe et que `assurer_admin` vient de porter au rôle administrateur.
    """
    import app as A
    from flask.sessions import SecureCookieSessionInterface
    s = SecureCookieSessionInterface().get_signing_serializer(A.app)
    return A.app.config.get("SESSION_COOKIE_NAME", "session"), \
        s.dumps({"user_email": ADMIN})


def attendre(url, essais=60):
    for _ in range(essais):
        try:
            urllib.request.urlopen(url, timeout=1).read()
            return True
        except Exception:
            time.sleep(.5)
    return False


SONDE = """() => {
  const champs = {};
  document.querySelectorAll('#ig-ao-fiche [data-fiche]').forEach(i => {
    champs[i.dataset.fiche] = i.value;
  });
  const m = document.getElementById('ig-ao-cab-msg');
  return { champs, message: m ? m.textContent.trim() : null,
           bouton: !!document.getElementById('ig-ao-cab-go') };
}"""


def main():
    # SANS CLÉ FIXE, LA RECETTE NE PEUT PAS SE CONNECTER — et le diagnostic
    # est muet : `auth.init_app` tire une clé AU HASARD quand
    # FLASK_SECRET_KEY est absent, si bien que le cookie signé ici n'est pas
    # celui qu'attend le serveur lancé à côté. Le navigateur repartait sur
    # /connexion, et la recette expirait en cherchant des champs qui
    # n'existaient pas. La clé est posée AVANT tout import de `auth`.
    os.environ.setdefault("FLASK_SECRET_KEY", "recette-locale-non-secrete")
    assurer_admin()
    nom_cookie, valeur = cookie_de_session()
    serveur = subprocess.Popen(
        [sys.executable, "-c",
         "import app; app.app.run(host='127.0.0.1', port=%d, threaded=True)" % PORT],
        cwd=ICI, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    try:
        if not attendre(BASE + "/"):
            print("REFUS : le service local n'a pas démarré."); return 1
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            n = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
            ctx = n.new_context(viewport={"width": 1400, "height": 1000})
            ctx.add_cookies([{"name": nom_cookie, "value": valeur,
                              "domain": "127.0.0.1", "path": "/"}])
            pg = ctx.new_page()
            erreurs = []
            pg.on("pageerror", lambda e: erreurs.append(str(e)))
            pg.goto(BASE + "/ingenierie-datacenter", wait_until="domcontentloaded")
            pg.wait_for_selector("#ig-ao-fiche [data-fiche]", timeout=45000)
            pg.wait_for_timeout(400)

            avant = pg.evaluate(SONDE)
            vides = [k for k, v in avant["champs"].items() if not v.strip()]
            print("champs de la fiche : %d · vides au départ : %d"
                  % (len(avant["champs"]), len(vides)))

            # 2. Une valeur tapée à la main, dans un champ que le dossier fournit.
            pg.fill('#ig-ao-fiche [data-fiche="raison_sociale"]', SAISIE)
            pg.dispatch_event('#ig-ao-fiche [data-fiche="raison_sociale"]', "input")
            pg.wait_for_timeout(200)

            pg.click("#ig-ao-cab-go")
            pg.wait_for_function(
                "() => { const m = document.getElementById('ig-ao-cab-msg');"
                " return m && /valeur\\(s\\) écrite\\(s\\)|n'a pas pu/.test(m.textContent); }",
                timeout=30000)
            pg.wait_for_timeout(400)
            apres = pg.evaluate(SONDE)
            n.close()
    finally:
        serveur.terminate()
        serveur.wait(timeout=10)

    return verdict(avant, apres, erreurs)


def verdict(avant, apres, erreurs):
    import dossier_entreprise as D
    etat = D.fiche_candidat()
    dossier = etat["fiche"]
    ec = []

    print("\n— message rendu —\n  " + (apres["message"] or "(aucun)"))

    # 2. la saisie survit
    garde = apres["champs"].get("raison_sociale")
    print("\nraison_sociale après le clic : %r" % garde)
    if garde != SAISIE:
        ec.append("la saisie manuelle a été écrasée : %r" % garde)

    # 3. les autres champs reçoivent le dossier
    ecrits, manquants = [], []
    for cle, val in dossier.items():
        if cle == "raison_sociale":
            continue
        if apres["champs"].get(cle, "") == val:
            ecrits.append(cle)
        else:
            manquants.append((cle, apres["champs"].get(cle, "")))
    print("champs du dossier réellement écrits : %d / %d"
          % (len(ecrits), len(dossier) - 1))
    for cle, vu in manquants:
        ec.append("%s attendu %r, vu %r" % (cle, dossier[cle], vu))

    # 4. le message correspond au DOM
    import re
    m = re.match(r"(\d+) valeur\(s\) écrite\(s\), (\d+) saisie\(s\) conservée\(s\)",
                 apres["message"] or "")
    if not m:
        ec.append("le message n'annonce pas le couple écrites/conservées")
    else:
        dit_ecrites, dit_gardees = int(m.group(1)), int(m.group(2))
        print("le message annonce %d écrites / %d conservées"
              % (dit_ecrites, dit_gardees))
        if dit_ecrites != len(ecrits):
            ec.append("le message annonce %d écrites, le DOM en porte %d"
                      % (dit_ecrites, len(ecrits)))
        if dit_gardees != 1:
            ec.append("le message annonce %d conservées, il y en a 1"
                      % dit_gardees)

    if erreurs:
        ec.append("erreurs JS : %s" % erreurs)

    print()
    if ec:
        print("ÉCARTS :")
        for e in ec:
            print("  ·", e)
        return 1
    print("AUCUN ÉCART — le bouton écrit le dossier et respecte la saisie.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
