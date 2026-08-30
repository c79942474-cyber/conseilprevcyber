# -*- coding: utf-8 -*-
"""La politique de sécurité du contenu, calculée sur ce qui est réellement servi.

CE QUE CE MODULE PERMET DE RETIRER. `script-src 'unsafe-inline'` signifiait
que tout défaut d'échappement resté quelque part était directement
EXPLOITABLE : l'échappement était la seule défense, et il suffisait d'un oubli.
Sans `'unsafe-inline'`, un même oubli devient inerte — le navigateur refuse
d'exécuter ce qui n'est pas annoncé.

POURQUOI DES EMPREINTES ET NON DES JETONS (« nonces »). Un jeton change à
chaque réponse : il oblige à réécrire le corps de la page à chaque requête, ce
qui détruit d'un coup le cache mémoire et l'ETag fort dont ce site dépend. Les
scripts en ligne d'ici sont STATIQUES — la seule injection serveur dans du HTML
écrit dans la valeur d'un champ et dans un message d'erreur, jamais dans un
script. Leurs empreintes se calculent donc une fois, sur les octets mêmes que
le navigateur recevra, et le cache reste intact.

LE CACHE EST INDEXÉ SUR LE CONTENU, PAS SUR L'HORODATAGE. Une clé
`(date de modification, taille)` ne voit pas deux écritures dans la même
seconde à taille égale. Sur un fichier compilé, ce piège coûte un essai
faussement vert ; ICI il coûterait une PAGE MORTE EN PRODUCTION — empreinte
périmée, script refusé, aucune erreur serveur, rien dans les journaux. On prend
donc l'empreinte des octets qu'on nous donne : elle ne peut pas être en retard
sur eux.

CE QUE CE MODULE NE PEUT PAS RATTRAPER. Un attribut de gestionnaire — `onclick`,
`onsubmit`, `ontoggle` — n'est couvert par AUCUNE empreinte : la spécification
ne le permet pas. Ils sont bloqués net. Il fallait donc les retirer avant, et
une règle vérifie qu'il n'en revient pas.
"""
import base64
import hashlib
import re

VERSION = "2026-08-a"

# Les directives communes. `style-src` garde l'exécution en ligne : un style ne
# s'exécute pas, et mille trente-quatre attributs `style=` pour un risque
# marginal serait un mauvais échange. `script-src`, lui, n'admet plus rien
# d'autre que l'origine et ce qui est nommément empreint.
_BASE = ("default-src 'self'; base-uri 'self'; form-action 'self'; "
         "frame-ancestors 'none'; object-src 'none'; "
         "img-src 'self' data:; font-src 'self' data:; "
         "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
         "script-src 'self'%s")

# `<script>` SANS attribut `src` : un script chargé depuis l'origine est déjà
# couvert par `'self'`, et lui calculer une empreinte n'aurait aucun sens.
_EN_LIGNE = re.compile(rb"<script(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>",
                       re.S | re.I)

_cache = {}
_MAX = 64


def scripts_en_ligne(octets):
    """Le contenu exact de chaque script en ligne, dans l'ordre du document."""
    return [m.group(1) for m in _EN_LIGNE.finditer(octets or b"")]


def empreinte(contenu):
    """L'empreinte au format que la CSP attend, sur les octets EXACTS.

    Aucun ajustement du contenu — ni espaces retirés, ni fin de ligne
    normalisée : le navigateur empreinte ce qu'il lit entre les balises, à
    l'octet près. Toute retouche ici produirait une empreinte qui ne
    correspond à rien, et un script refusé sans que rien ne le dise.
    """
    return "'sha256-%s'" % base64.b64encode(
        hashlib.sha256(contenu).digest()).decode("ascii")


def pour(octets):
    """La politique adaptée à CES octets — ceux que le navigateur recevra.

    L'appelant passe le corps réellement servi, transformations comprises :
    calculer sur le fichier d'origine donnerait des empreintes justes pour un
    document que personne ne reçoit.
    """
    cle = hashlib.sha256(octets or b"").digest()
    trouve = _cache.get(cle)
    if trouve is not None:
        return trouve
    empreintes = "".join(" " + empreinte(c) for c in scripts_en_ligne(octets))
    politique = _BASE % empreintes
    if len(_cache) >= _MAX:
        _cache.clear()          # borne simple : le fonds de pages est petit
    _cache[cle] = politique
    return politique


def sans_script_en_ligne():
    """La politique d'une réponse qui ne porte aucun script en ligne — une API,
    une redirection, un fichier. Elle n'a besoin d'aucune empreinte."""
    return _BASE % ""


def glossaire():
    return {
        "empreinte": "la somme SHA-256 du contenu d'un script en ligne, que le "
                     "navigateur recalcule et compare avant d'exécuter",
        "pourquoi pas un jeton": "un jeton change à chaque réponse et oblige à "
                                 "réécrire la page : le cache et l'ETag "
                                 "tombent avec lui",
        "attribut de gestionnaire": "`onclick` et consorts ne peuvent être "
                                    "couverts par aucune empreinte : ils sont "
                                    "bloqués, il faut les avoir retirés",
    }


def referentiel():
    return {"version": VERSION, "base": _BASE % ""}
