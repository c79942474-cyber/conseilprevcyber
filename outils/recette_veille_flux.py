#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Éprouve les trente-six adresses du catalogue de veille, une par une.

POURQUOI CE SCRIPT EXISTE. La page de veille n'affichait rien, et le code
n'était pas en cause : la collecte tournait, elle allait au bout de son budget,
et elle ne rapportait rien. Le catalogue avait été ÉCRIT HORS LIGNE — il le
déclarait lui-même, deux flux éprouvés sur trente-six — et personne n'avait
jamais eu le moyen de savoir, adresse par adresse, laquelle répond.

Les journaux de production donnaient seize échecs HTTP. Les vingt autres
répondaient 200 sans rien rendre, ce qui, jusqu'à cette version, était compté
comme un flux en bonne santé n'ayant rien publié. Ce script est le seul endroit
du dépôt qui OUVRE UNE SOCKET vers ces adresses : le reste du code ne le fait
qu'en production, et les règles ne le font jamais.

CE QU'IL FAIT, ET QUI EST PLUS QU'UN CONSTAT. Pour chaque adresse fautive il
ESSAIE les variantes mécaniques usuelles — /feed, /feed/, /rss, /rss.xml,
/atom.xml, /index.xml — sur le même hôte. Il ne PROPOSE que ce qu'il a
réellement obtenu : une adresse qui répond, qui est un flux, et qui rend au
moins un élément. Une variante qui n'a pas été essayée avec succès n'est pas
imprimée. Proposer une adresse plausible mais fausse ferait perdre plus de
temps que n'en fait gagner le script.

CE QU'IL NE FAIT PAS. Il ne modifie PAS le catalogue. La correction est une
décision : une adresse de repli peut servir un flux plus étroit, ou une autre
langue, ou un site miroir. Le script imprime la ligne Python à coller, et
s'arrête là.

Usage :  python3 outils/recette_veille_flux.py            (tout le catalogue)
         python3 outils/recette_veille_flux.py cisa_ics anssi   (quelques clés)
         python3 outils/recette_veille_flux.py --sans-variantes

Code de sortie : 0 si toutes les adresses essayées servent un flux, 1 sinon.
"""
import os
import sys
import time

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)
os.environ.setdefault("AUTOMATION_DISABLED", "1")

import requests                                                  # noqa: E402

import automation                                                # noqa: E402
import veille_sources                                            # noqa: E402

# Les suffixes que sert, en pratique, un site qui publie un flux. Ils ne sont
# pas devinés au hasard : ce sont ceux des moteurs de publication courants.
VARIANTES = ("/feed", "/feed/", "/rss", "/rss.xml", "/atom.xml", "/index.xml",
             "/feed.xml", "/en/rss.xml", "/news/rss.xml")

VERT, ROUGE, JAUNE, GRIS, RAZ = "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[0m"
if not sys.stdout.isatty():
    VERT = ROUGE = JAUNE = GRIS = RAZ = ""


def essayer(url, timeout=15):
    """(verdict, detail, elements, url_finale) — un seul aller-retour réseau.

    Le verdict distingue les trois états qui appellent trois gestes différents :
    « ok » n'appelle rien, « pas_un_flux » appelle une correction d'adresse,
    « http » appelle soit une correction, soit une négociation avec l'éditeur.
    """
    try:
        r = requests.get(url, timeout=timeout, headers=automation._ENTETES_FLUX)
    except Exception as exc:
        return "reseau", type(exc).__name__ + " : " + str(exc)[:90], 0, url
    finale = r.url
    if r.status_code >= 400:
        return "http", "%d %s" % (r.status_code, r.reason), 0, finale
    pourquoi = automation._pourquoi_pas_un_flux(r.text)
    if pourquoi:
        return "pas_un_flux", pourquoi, 0, finale
    n = len(automation._parse_feed("recette", r.text))
    return "ok", "%d élément(s)" % n, n, finale


def variantes_de(url):
    """Les adresses mécaniquement voisines, sans doublon et sans l'originale."""
    from urllib.parse import urlsplit, urlunsplit
    p = urlsplit(url)
    base = urlunsplit((p.scheme, p.netloc, "", "", ""))
    # Le chemin amputé de son dernier segment : /a/b/rss.xml -> /a/b
    tronc = p.path.rstrip("/")
    tronc = tronc[:tronc.rfind("/")] if "/" in tronc.lstrip("/") else ""
    out = []
    for socle in (tronc, ""):
        for v in VARIANTES:
            cand = base + socle + v
            if cand != url and cand not in out:
                out.append(cand)
    return out


def main(argv):
    sans_variantes = "--sans-variantes" in argv
    cles = [a for a in argv[1:] if not a.startswith("-")]
    sources = [s for s in veille_sources.SOURCES
               if not cles or s["cle"] in cles]
    if cles and len(sources) != len(cles):
        connues = {s["cle"] for s in veille_sources.SOURCES}
        print(ROUGE + "clé(s) inconnue(s) : %s"
              % ", ".join(sorted(set(cles) - connues)) + RAZ)
        return 2

    print("RECETTE DES FLUX DE VEILLE — %d adresse(s)" % len(sources))
    print("En-tête employé : %s" % automation._ENTETES_FLUX["User-Agent"])
    print("Ce script ouvre de VRAIES connexions. Il ne modifie rien.\n")

    ok, fautifs = [], []
    for s in sources:
        verdict, detail, n, finale = essayer(s["url"])
        marque = {"ok": VERT + "  OK  " + RAZ,
                  "pas_un_flux": JAUNE + " PAS-FLUX " + RAZ,
                  "http": ROUGE + " HTTP " + RAZ,
                  "reseau": ROUGE + " RÉSEAU " + RAZ}[verdict]
        print("%s %-18s %s" % (marque, s["cle"], detail))
        if finale != s["url"]:
            print("        %sredirigé vers %s%s" % (GRIS, finale, RAZ))
        if verdict == "ok" and n:
            ok.append(s["cle"])
        else:
            fautifs.append((s, verdict, detail))
        time.sleep(0.2)                       # on ne martèle pas les éditeurs

    print("\n%d adresse(s) servent un flux non vide, %d à reprendre."
          % (len(ok), len(fautifs)))

    if fautifs and not sans_variantes:
        print("\nRECHERCHE DE VARIANTES — seules celles RÉELLEMENT obtenues "
              "sont imprimées.\n")
        trouve = {}
        for s, _v, _d in fautifs:
            for cand in variantes_de(s["url"]):
                verdict, detail, n, finale = essayer(cand, timeout=10)
                if verdict == "ok" and n:
                    trouve[s["cle"]] = (finale, n)
                    print("%s %-18s %s  (%d éléments)"
                          % (VERT + " TROUVÉ " + RAZ, s["cle"], finale, n))
                    break
                time.sleep(0.15)
            else:
                print("%s %-18s aucune variante mécanique ne répond — "
                      "adresse à retrouver à la main"
                      % (GRIS + " ——     " + RAZ, s["cle"]))
        if trouve:
            print("\nÀ COLLER DANS veille_sources.py (vérifiez le contenu avant) :")
            for cle, (url, n) in sorted(trouve.items()):
                print('    %-18s -> "%s"   # %d éléments au %s'
                      % (cle, url, n, time.strftime("%Y-%m-%d")))

    if fautifs:
        print("\n" + ROUGE + "Le catalogue n'est pas sain : %d adresse(s) sur %d."
              % (len(fautifs), len(sources)) + RAZ)
        return 1
    print("\n" + VERT + "Toutes les adresses essayées servent un flux." + RAZ)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
