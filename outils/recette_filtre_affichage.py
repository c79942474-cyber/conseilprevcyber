# -*- coding: utf-8 -*-
"""RECETTE — LES DEUX FILTRES D'AFFICHAGE, DANS UN VRAI NAVIGATEUR.

POURQUOI CE SCRIPT EXISTE, À CÔTÉ DES RÈGLES. `tests/test_ao_filtre_affichage.py`
exécute les mêmes fonctions sur un DOM RÉDUIT : un double qui ne connaît que
`hidden`, `dataset`, `classList.contains` et `closest`. Il ne sait rien de la
mise en page, de la cascade CSS, du clavier ni du défilement — et c'est
volontaire : les règles doivent rester rapides et hermétiques, et la maison
tient les scripts de navigateur hors de `tests/`.

CE QUE LUI SEUL MESURE : que Chromium applique bien `hidden`, que `closest`
trouve le bon bloc dans le vrai arbre rendu par `innerHTML`, que la déroulante
émet un `change` que le brancheur entend, et qu'aucune erreur JavaScript ne
part en silence.

CE QU'IL NE FAIT PAS : il n'ouvre aucune socket et ne touche à aucune donnée.
Il rend la colonne depuis une analyse calculée ici même, dans un fichier
temporaire qu'il efface.

    python3 outils/recette_filtre_affichage.py
"""
import io
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

from playwright.sync_api import sync_playwright                  # noqa: E402

import ao_dc                                                     # noqa: E402

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
ECHECS = []


def verifier(condition, dit):
    print(("   OK   " if condition else "   RATÉ ") + dit)
    if not condition:
        ECHECS.append(dit)


def _corps(src, nom):
    i = src.index("function " + nom + "(")
    j, n = src.index("{", i), 0
    for k in range(j, len(src)):
        if src[k] == "{":
            n += 1
        elif src[k] == "}":
            n -= 1
            if n == 0:
                return src[i:k + 1]
    raise AssertionError(nom)


def _navigateur(pw):
    return pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])


# ── 1. LE FILTRE DES PIÈCES À PRODUIRE ──────────────────────────────────────

RC_PIECES = (
    u"REGLEMENT DE LA CONSULTATION\n"
    u"Article 4 — Pieces a produire par le candidat\n"
    u"Lettre de candidature DC1, declaration du candidat DC2, attestation "
    u"d'assurance responsabilite civile professionnelle, liste des references "
    u"de moins de cinq ans, curriculum vitae des intervenants, composition de "
    u"l'equipe, note de repartition des competences, extrait Kbis, "
    u"attestation de vigilance, bilans et comptes de resultat, memoire "
    u"technique, acte d'engagement, DPGF.\n"
    u"Date et heure limites de remise des offres : 25/10/2026 a 12h00.\n")

PAGE_LISTE = u"""<!doctype html><meta charset="utf-8"><body>
<div id="ig-ao-retenus"></div>
<script>
var AO_SELECTION = null, AO_SEL_AJOUTS = {}, AO_SEL_ECARTEES = {}, AO_VUE = {};
function $(s, r) { return (r || document).querySelector(s); }
function esc(x) { return String(x == null ? "" : x)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
  .replace(/"/g,"&quot;").replace(/'/g,"&#39;"); }
function info() { return ""; }
function aoSelectionEnvoyer() {}
%s
window.__rendre = function (sel) { aoSelectionRendre(sel); };
window.__compter = function (groupe) {
  var bloc = document.querySelector('[data-vue-liste="' + groupe + '"]');
  bloc = bloc && bloc.closest(".ig-ao-sg");
  if (!bloc) return null;
  var tous = bloc.querySelectorAll('li[data-vue-piece]:not(.ig-ao-sc)');
  var cit = bloc.querySelectorAll('li.ig-ao-sc[data-vue-piece]');
  return {total: tous.length,
          visibles: [].filter.call(tous, function (n) { return !n.hidden; }).length,
          citations_visibles: [].filter.call(cit, function (n) {
            return !n.hidden; }).length,
          dit: (bloc.querySelector('[data-vue-masque]') || {}).textContent || "",
          choisir: bloc.querySelectorAll('[data-sel-liste] option').length,
          options: [].map.call(bloc.querySelectorAll('[data-vue-liste] option'),
                               function (o) { return o.value; })};
};
window.__filtrer = function (groupe, cat) {
  var s = document.querySelector('[data-vue-liste="' + groupe + '"]');
  s.value = cat; s.dispatchEvent(new Event("change"));
};
</script></body>"""


def recette_liste(pw, src):
    sel = ao_dc.selection(ao_dc.analyser(
        [{"nom": "RC.pdf", "texte": RC_PIECES, "extension": ".pdf"}]))
    prelude = "\n".join(_corps(src, f) for f in (
        "aoSelectionRendre", "aoVueOptions", "aoVueAppliquer", "aoVueBrancher",
        "aoSelectionBrancher", "aoSelectionRecalculer"))
    tmp = os.path.join(ICI, "_recette_filtre_liste.html")
    io.open(tmp, "w", encoding="utf-8").write(PAGE_LISTE % prelude)
    try:
        b = _navigateur(pw)
        pg = b.new_page()
        erreurs = []
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto("file://" + tmp)
        pg.evaluate("s => window.__rendre(s)", sel)
        print("\n== LES DOCUMENTS À PRODUIRE ==")
        for g in ("candidature", "offre", "__non"):
            avant = pg.evaluate("g => window.__compter(g)", g)
            if avant is None:
                verifier(False, "le groupe « %s » n'est pas rendu" % g)
                continue
            print("  %s : %d pièce(s), %d option(s) d'affichage"
                  % (g, avant["total"], len(avant["options"])))
            verifier(avant["visibles"] == avant["total"],
                     "%s — sans filtre, tout est visible" % g)
            verifier(avant["dit"] == "",
                     "%s — sans filtre, rien n'est annoncé masqué" % g)
            for cat in [c for c in avant["options"] if c]:
                pg.evaluate("a => window.__filtrer(a[0], a[1])", [g, cat])
                x = pg.evaluate("y => window.__compter(y)", g)
                verifier(x["visibles"] < x["total"] and x["visibles"] > 0,
                         "%s/%s — %d pièce(s) sur %d affichée(s)"
                         % (g, cat, x["visibles"], x["total"]))
                verifier(x["citations_visibles"] == x["visibles"],
                         "%s/%s — chaque citation suit sa pièce" % (g, cat))
                verifier("masquée(s)" in x["dit"],
                         "%s/%s — le filtre dit ce qu'il cache" % (g, cat))
                verifier(x["choisir"] == avant["choisir"],
                         "%s/%s — la déroulante qui CHOISIT est intacte"
                         % (g, cat))
            pg.evaluate("a => window.__filtrer(a[0], a[1])", [g, ""])
            fin = pg.evaluate("y => window.__compter(y)", g)
            verifier(fin["visibles"] == fin["total"] and fin["dit"] == "",
                     "%s — le retour à « toutes » remontre tout" % g)
        pg.evaluate("a => window.__filtrer(a[0], a[1])",
                    ["candidature", "redigeable"])
        av = pg.evaluate("g => window.__compter(g)", "candidature")
        pg.evaluate("s => window.__rendre(s)", sel)
        ap = pg.evaluate("g => window.__compter(g)", "candidature")
        verifier(ap["visibles"] == av["visibles"] and ap["dit"] == av["dit"],
                 "le filtre survit au redessin de la colonne")
        verifier(not erreurs, "aucune erreur JavaScript : %r" % (erreurs or ""))
        b.close()
    finally:
        os.remove(tmp)


# ── 2. LE FILTRE DU RELEVÉ ──────────────────────────────────────────────────

DOCS = [
    {"nom": "RC-2026.pdf", "extension": ".pdf", "texte":
     u"REGLEMENT DE LA CONSULTATION\nDate et heure limites de remise des "
     u"offres : 25/10/2026 a 12h00.\nCriteres de jugement : prix 40 %.\n"},
    {"nom": "CCAP-2026.pdf", "extension": ".pdf", "texte":
     u"CAHIER DES CLAUSES ADMINISTRATIVES PARTICULIERES\n"
     u"Penalites de retard : 1/1000 du montant par jour.\n"},
    {"nom": "CCTP-2026.pdf", "extension": ".pdf", "texte":
     u"CAHIER DES CLAUSES TECHNIQUES PARTICULIERES\nLe titulaire realise.\n"},
    {"nom": "plan-masse-xyz.dwg", "extension": ".dwg", "texte": u""},
    {"nom": "attestation-assurance-rc-pro.pdf", "extension": ".pdf",
     "texte": u"Attestation d'assurance responsabilite civile.\n"},
]

PAGE_DOC = u"""<!doctype html><meta charset="utf-8"><body>
<div id="ig-ao-out"></div>
<script>
var AO_VUE_DOC = "";
function $(s, r) { return (r || document).querySelector(s); }
function esc(x) { return String(x == null ? "" : x)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
  .replace(/"/g,"&quot;").replace(/'/g,"&#39;"); }
function info() { return ""; }
function aoTexteBrancherListe() {}
function aoTexteFermer() {}
function aoIgnores() {}
%s
window.__rendre = function (a) { aoRendre(a); };
window.__etat = function () {
  var z = document.getElementById("ig-ao-out");
  var tous = z.querySelectorAll("[data-vue-doc-item]");
  return {sections: tous.length,
    visibles: [].filter.call(tous, function (d) { return !d.hidden; }).length,
    alertes: z.querySelectorAll(".ig-ao-al .ig-ao-a").length,
    alertes_visibles: [].filter.call(z.querySelectorAll(".ig-ao-al"),
      function (d) { return !d.hidden; }).length,
    dit: (z.querySelector("[data-vue-doc-masque]") || {}).textContent || "",
    options: [].map.call(z.querySelectorAll("[data-vue-doc] option"),
                         function (o) { return o.value; })};
};
window.__filtrer = function (v) {
  var s = document.querySelector("[data-vue-doc]");
  s.value = v; s.dispatchEvent(new Event("change"));
};
</script></body>"""


def recette_releve(pw, src):
    a = ao_dc.analyser(DOCS)
    prelude = "\n".join(_corps(src, f) for f in (
        "aoRendre", "aoVueDoc", "aoVueDocAppliquer", "aoVueDocBrancher",
        "aoTexteBouton"))
    tmp = os.path.join(ICI, "_recette_filtre_doc.html")
    io.open(tmp, "w", encoding="utf-8").write(PAGE_DOC % prelude)
    try:
        b = _navigateur(pw)
        pg = b.new_page()
        erreurs = []
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto("file://" + tmp)
        pg.evaluate("x => window.__rendre(x)", a)
        e0 = pg.evaluate("() => window.__etat()")
        print("\n== LE RELEVÉ DES DOCUMENTS DÉPOSÉS ==")
        print("  %d section(s), %d alerte(s), %d option(s)"
              % (e0["sections"], e0["alertes"], len(e0["options"])))
        verifier(e0["alertes"] > 0,
                 "le dossier d'essai porte bien des alertes à protéger")
        verifier(e0["visibles"] == e0["sections"],
                 "sans filtre, tout le relevé est visible")
        for v in [o for o in e0["options"] if o]:
            pg.evaluate("x => window.__filtrer(x)", v)
            x = pg.evaluate("() => window.__etat()")
            verifier(x["visibles"] == 1,
                     "« %s » — une seule section affichée" % v)
            verifier(x["alertes_visibles"] == e0["alertes_visibles"],
                     "« %s » — LES ALERTES RESTENT AFFICHÉES" % v)
            verifier("masquée(s)" in x["dit"],
                     "« %s » — le filtre dit ce qu'il cache" % v)
        pg.evaluate("x => window.__filtrer(x)", "")
        f = pg.evaluate("() => window.__etat()")
        verifier(f["visibles"] == f["sections"] and f["dit"] == "",
                 "le retour à « tout le relevé » remontre tout")
        verifier(not erreurs, "aucune erreur JavaScript : %r" % (erreurs or ""))
        b.close()
    finally:
        os.remove(tmp)


def main():
    src = io.open(os.path.join(ICI, "ingenierie-dc.js"),
                  encoding="utf-8").read()
    with sync_playwright() as pw:
        recette_liste(pw, src)
        recette_releve(pw, src)
    print("\n" + "=" * 62)
    if ECHECS:
        print("%d CONTRÔLE(S) EN ÉCHEC :" % len(ECHECS))
        for e in ECHECS:
            print("  · " + e)
        return 1
    print("Tous les contrôles passent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
