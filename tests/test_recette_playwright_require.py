"""Les scripts recette_*.js chargent tous playwright au même endroit.

LE DÉFAUT CORRIGÉ. Ces scripts ne passent pas par `npm install` — ils
tournent en dehors de tout `node_modules` de projet, contre un serveur déjà
lancé (BASE=http://127.0.0.1:PORT node recette_xxx.js). 18 d'entre eux le
savaient et chargeaient playwright par son chemin absolu d'installation
système ; trois — recette_cas_poste_ht.js, recette_menu_icones.js,
recette_perspectives_choix.js — avaient un `require('playwright')` nu, qui ne
se résout que s'il existe un `node_modules/playwright` local. Sur toute
machine qui n'en a pas exactement au bon endroit, le script échoue à la
toute première ligne exécutable, avant même d'ouvrir un navigateur.
"""
import glob
import os
import re

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHEMIN_SYSTEME = "/opt/node22/lib/node_modules/playwright"


def _scripts_recette():
    return sorted(glob.glob(os.path.join(ICI, "recette_*.js")))


def test_tous_les_scripts_recette_chargent_playwright_par_le_meme_chemin():
    fautifs = []
    scripts = _scripts_recette()
    assert len(scripts) >= 10, "les scripts recette_*.js n'ont pas été trouvés"
    for chemin in scripts:
        with open(chemin, encoding="utf-8") as f:
            contenu = f.read()
        for m in re.finditer(r"require\(['\"]([^'\"]*playwright[^'\"]*)['\"]\)", contenu):
            if m.group(1) != CHEMIN_SYSTEME:
                fautifs.append((os.path.basename(chemin), m.group(1)))
    assert fautifs == [], (
        "ces scripts ne chargent pas playwright par le chemin système "
        "utilisé par tous les autres : %r" % (fautifs,))
