# -*- coding: utf-8 -*-
"""RECETTE — le champ survit-il au repeint, dans un VRAI navigateur ?

POURQUOI CE SCRIPT EXISTE, À CÔTÉ DE `tests/test_ao_saisie_confortable.py`.
Les règles de la suite éprouvent les deux gardes contre un DOM réduit : c'est
rapide, hermétique, et cela suffit à faire tomber toute mutation qui les
casse. Mais le focus, le curseur et la sélection sont des comportements de
NAVIGATEUR : un double qui répond « oui » ne prouve pas qu'un vrai Chromium
ferait de même. Ce script lance le vrai, tape de vraies touches, et compare
le comportement AVEC et SANS la garde.

    python3 outils/recette_saisie_clavier.py

Attendu :
    SANS la garde : focus perdu, « VILLE » — les neuf caractères tapés
                    pendant l'aller-retour ont disparu.
    AVEC la garde : focus tenu, « VILLE DE PARIS », curseur à 8.
"""
import io, json, os, sys, subprocess

ICI = os.path.dirname(os.path.abspath(__file__))


def js_source(*noms):
    src = io.open(os.path.join("/home/user/conseilprevcyber",
                               "ingenierie-dc.js"), encoding="utf-8").read()
    out = []
    for nom in noms:
        i = src.index("\n  function %s(" % nom) + 1
        p, k = 1, src.index("{", i) + 1
        while p:
            p += 1 if src[k] == "{" else (-1 if src[k] == "}" else 0)
            k += 1
        out.append(src[i:k])
    return "\n".join(out)


PAGE = """<!doctype html><meta charset="utf-8"><div id="z"></div>
<script>
%s
window.peindre = function (valeur) {
  var z = document.getElementById("z");
  var garde = aoFocusRetenir(z);
  z.innerHTML = '<p>compteurs repeints</p>'
    + '<input data-saisie="dc1.acheteur" value="' + valeur + '">'
    + '<input data-saisie="dc1.objet" value="">';
  aoFocusRendre(z, garde);
};
window.peindreSansGarde = function (valeur) {
  var z = document.getElementById("z");
  z.innerHTML = '<p>compteurs repeints</p>'
    + '<input data-saisie="dc1.acheteur" value="' + valeur + '">'
    + '<input data-saisie="dc1.objet" value="">';
};
</script>""" % js_source("aoFocusRetenir", "aoFocusRendre")

from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    nav = pw.chromium.launch(
        executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
        args=["--no-sandbox"])
    page = nav.new_page()
    page.set_content(PAGE)

    def essai(avec_garde):
        page.evaluate("(v) => window.%s(v)"
                      % ("peindre" if avec_garde else "peindreSansGarde"), "")
        page.focus('[data-saisie="dc1.acheteur"]')
        # L'OPÉRATEUR TAPE — vraies touches, vrai curseur.
        page.keyboard.type("VILLE DE PARIS")
        # Puis il revient corriger au MILIEU du mot, comme on le fait.
        for _ in range(6):
            page.keyboard.press("ArrowLeft")
        # Le serveur répond, avec une valeur PLUS VIEILLE que la frappe.
        page.evaluate("(v) => window.%s(v)"
                      % ("peindre" if avec_garde else "peindreSansGarde"),
                      "VILLE")
        return page.evaluate("""() => {
          var a = document.activeElement;
          var n = document.querySelector('[data-saisie="dc1.acheteur"]');
          return {focus: a === n, valeur: n.value,
                  curseur: (a === n) ? a.selectionStart : null};
        }""")

    sans = essai(False)
    page.set_content(PAGE)
    avec = essai(True)

    print("─" * 66)
    print("SANS la garde :", json.dumps(sans, ensure_ascii=False))
    print("AVEC la garde :", json.dumps(avec, ensure_ascii=False))
    print("─" * 66)
    nav.close()
