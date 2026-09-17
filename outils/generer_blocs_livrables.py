#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Écrit, dans chaque page « Conseil & transformation », le bloc des livrables
de cette page — un par un, chacun avec son propre lien vers l'espace
administrateur.

POURQUOI CE SCRIPT PLUTÔT QUE DU HTML ÉCRIT À LA MAIN
Le bloc était écrit à la main, en prose, page par page. Résultat : une page
annonçait six livrables et n'en rendait qu'un seul atteignable — les cinq
autres existaient dans le catalogue sans qu'aucun lien n'y mène. Le catalogue
est désormais la seule source : ce script régénère les blocs, et
`tests/test_blocs_livrables.py` échoue si une page s'en écarte.

POURQUOI DU HTML STATIQUE PLUTÔT QU'UN RENDU JAVASCRIPT
Ces pages sont publiques et référencées. Un bloc rendu en JavaScript serait
invisible des moteurs et des lecteurs sans script. Le HTML est donc écrit dans
le fichier ; c'est le test qui empêche la dérive, pas le navigateur.

Usage :  python3 outils/generer_blocs_livrables.py [--verifier]
         --verifier n'écrit rien et rend un code de sortie non nul en cas
         d'écart : c'est ce mode qu'utilise le test.
"""
import io
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import livrables  # noqa: E402

DEBUT = "<!-- LIVRABLES:DEBUT (genere par outils/generer_blocs_livrables.py) -->"
FIN = "<!-- LIVRABLES:FIN -->"

# ── LES PAGES QUI TIENNENT LEUR BLOC À LA MAIN ─────────────────────────────
# UNE EXCEPTION SE DÉCLARE, AVEC SON MOTIF. Sans cette table, le générateur
# voyait `/maturite-ot` comme un bloc MANQUANT et, en écriture, en aurait
# inséré un SECOND sous celui que la page tient déjà. En vérification, il
# rendait un écart perpétuel — et un contrôle qui crie toujours ne se lit
# plus : sept pages sont restées non régénérées derrière ce bruit, et deux
# livrables catalogués n'étaient atteignables depuis aucune page.
#
# CE N'EST PAS UN PASSE-DROIT. La page dispensée doit exposer TOUT son
# groupe — c'est ce que le bloc généré garantissait, et l'exception doit
# garantir autant. `verifier_page_a_la_main` le demande à la page elle-même,
# par son module, et rend l'écart s'il y en a un.
A_LA_MAIN = {
    "/maturite-ot":
        "La page sert ses livrables DEPUIS LES RÉPONSES du visiteur : trois "
        "se calculent sur place, les autres disent pourquoi ils ne se "
        "calculent pas. Un bloc généré poserait à la place autant de renvois "
        "identiques vers l'espace administrateur.",
}


def verifier_page_a_la_main(url):
    """La page dispensée expose-t-elle encore tout son groupe ?

    Rend la liste des livrables catalogués pour cette page que la page ne
    sert pas. Le module de la page est la source : on lui DEMANDE ce qu'il
    sert, au lieu de chercher des identifiants dans son HTML — un gabarit qui
    rend sa liste en JavaScript ne dirait rien à une lecture de texte."""
    if url == "/maturite-ot":
        import maturite_ot
        servis = {l["id"] for l in maturite_ot.livrables()["livrables"]}
    else:
        return ["page dispensée sans contrôle écrit : %s" % url]
    attendus = {t["id"] for t in livrables.livrables_de_page(url)}
    return sorted(attendus - servis)

# La phrase que le client lit. Elle affirme trois choses — rédaction par l'IA,
# ancrage sur la base de connaissance, export Word/PDF — et le balayage de
# tests/test_blocs_livrables.py vérifie que les trois sont vraies pour CHAQUE
# livrable listé. Une promesse imprimée sans être vérifiée est un mensonge qui
# attend son tour.
PROMESSE = (
    "Chaque livrable ci-dessous est <strong>rédigeable par l'IA</strong> "
    "(Mistral&nbsp;/&nbsp;Claude) <strong>à partir de la base de connaissance</strong> "
    "du cabinet, et <strong>exportable en Word ou PDF</strong>. Ce que l'IA produit est un "
    "<strong>brouillon structuré</strong>&nbsp;: il est relu, corrigé et validé par un "
    "consultant avant d'être remis."
)


def echapper(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def bloc_html(page):
    """Le bloc d'une page, reconstruit depuis le catalogue."""
    items = livrables.livrables_de_page(page["url"])
    lignes = []
    for t in items:
        # ── LA TUILE EST ELLE-MÊME LE LIEN ─────────────────────────────
        # Elle ne l'était pas : l'appel « Générer… » tenait la dernière
        # ligne, et les deux tiers supérieurs de la tuile — l'intitulé, la
        # description — ne répondaient pas, alors que `.liv-i:hover` les
        # éclaire déjà comme si l'on pouvait cliquer. La tuile promettait
        # sans tenir.
        #
        # L'APPEL RESTE ÉCRIT, EN <span> ET NON EN <a>. Un lien dans un lien
        # est interdit par le HTML : le navigateur referme silencieusement
        # l'extérieur, et la tuile redeviendrait morte partout sauf sur ces
        # quelques mots. La classe `bloc` porte la règle partagée.
        #
        # LE <li> RESTE, ET NE PORTE PLUS RIEN. C'est lui l'élément de la
        # grille ; l'ancre le remplit. Retirer la liste ferait perdre au
        # lecteur d'écran le décompte des livrables.
        lignes.append(
            '          <li><a class="bloc liv-i" href="/admin/livrables?type='
            + t["id"] + '" rel="nofollow">\n'
            '            <div class="liv-t">' + echapper(t["label"]) + '</div>\n'
            '            <div class="liv-d">' + echapper(t["desc"]) + '</div>\n'
            '            <span class="liv-g">'
            'Générer dans l\'espace administrateur →</span>\n'
            '          </a></li>'
        )
    return (
        DEBUT + "\n"
        '    <section class="section" id="livrables" style="padding-top:8px">\n'
        '      <div class="prose" style="max-width:none">\n'
        '        <h2>📦 Livrables — ' + echapper(page["titre"]) + "</h2>\n"
        '        <p class="liv-promesse">' + PROMESSE + "</p>\n"
        '        <ul class="liv-list">\n'
        + "\n".join(lignes) + "\n"
        '        </ul>\n'
        '        <p class="muted" style="font-size:12.5px;margin-top:14px">'
        "L'accès à la génération est réservé à l'administrateur du cabinet. "
        '<a href="/services">Voir l\'ensemble des prestations →</a></p>\n'
        '      </div>\n'
        '    </section>\n'
        "    " + FIN
    )


def ancre_insertion(html):
    """Où poser le bloc quand la page n'en a pas encore : juste avant la
    dernière section (le bandeau d'appel à l'action de bas de page), pour que
    les livrables précèdent l'invitation à nous contacter."""
    i = html.rfind('<div class="divider"></div>')
    return i if i >= 0 else -1


def traiter(page, verifier):
    chemin = os.path.join(RACINE, page["url"].lstrip("/") + ".html")
    if not os.path.isfile(chemin):
        return "ABSENTE", chemin
    if page["url"] in A_LA_MAIN:
        oublies = verifier_page_a_la_main(page["url"])
        return ("À LA MAIN" if not oublies
                else "TROU À LA MAIN : %s" % ", ".join(oublies)), chemin
    html = io.open(chemin, encoding="utf-8").read()
    attendu = bloc_html(page)

    if DEBUT in html:
        motif = re.compile(re.escape(DEBUT) + r".*?" + re.escape(FIN), re.S)
        actuel = motif.search(html)
        if actuel and actuel.group(0) == attendu:
            return "À JOUR", chemin
        if verifier:
            return "ÉCART", chemin
        html = motif.sub(lambda _: attendu, html, count=1)
    else:
        if verifier:
            return "MANQUANT", chemin
        i = ancre_insertion(html)
        if i < 0:
            return "PAS D'ANCRE", chemin
        html = html[:i] + attendu + "\n\n      " + html[i:]

    io.open(chemin, "w", encoding="utf-8").write(html)
    return "ÉCRIT", chemin


def main():
    verifier = "--verifier" in sys.argv
    sante = livrables.sante_pages()
    if not sante["ok"]:
        for p in sante["problemes"]:
            print("  PROBLÈME CATALOGUE :", p)
        return 1

    ecarts = 0
    for page in livrables.PAGES_CONSEIL:
        etat, chemin = traiter(page, verifier)
        n = len(livrables.livrables_de_page(page["url"]))
        print("  %-12s %-30s %d livrable(s)" % (etat, page["url"], n))
        if etat in ("ÉCART", "MANQUANT", "ABSENTE", "PAS D'ANCRE") \
                or etat.startswith("TROU À LA MAIN"):
            ecarts += 1

    print("\n%d page(s) · %d livrable(s) conseil · %s"
          % (sante["pages"], sante["livrables_conseil"],
             ("%d écart(s)" % ecarts) if ecarts else "aucun écart"))
    return 1 if ecarts else 0


if __name__ == "__main__":
    sys.exit(main())
