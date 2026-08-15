"""GEO — ce que les moteurs génératifs lisent de ce site, tenu exact.

Les moteurs de réponse (ChatGPT, Gemini, Perplexity, Claude) ne citent que ce
qu'ils peuvent LIRE : les pages publiques. Ce module tient la partie la plus
fragile de ce contrat — le JSON-LD FAQPage — en le DÉRIVANT du HTML servi,
jamais en le réécrivant à la main. Un balisage qui dit autre chose que la
page est pire que pas de balisage : c'est la définition du contenu trompeur
chez tous les opérateurs de recherche.

Le même extracteur sert à générer le bloc ET à le contrôler en test : une
seule implémentation, donc aucun écart possible entre les deux.

Régénérer le bloc après modification de la FAQ :
    python3 -c "import geo; print(geo.bloc_script(open('faq.html').read()))"
"""

import html as _html
import json
import re

_DETAILS = re.compile(r'<details class="faq">(.*?)</details>', re.S)
_QUESTION = re.compile(r'<summary><span class="qn">\d+</span><span>(.*?)</span>', re.S)
_REPONSE = re.compile(r'<div class="ans">(.*?)</div>', re.S)
_BALISES = re.compile(r"<[^>]+>")
_BLOC = re.compile(
    r'<script type="application/ld\+json" data-geo="faq">(.*?)</script>', re.S)


def _texte(fragment):
    """Le texte nu d'un fragment HTML : balises retirées, entités résolues,
    blancs repliés — la forme sous laquelle un moteur compare."""
    t = _BALISES.sub(" ", fragment or "")
    t = _html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def extraire_faq(page_html):
    """Les paires question/réponse RÉELLEMENT présentes dans la page."""
    paires = []
    for bloc in _DETAILS.findall(page_html or ""):
        q = _QUESTION.search(bloc)
        r = _REPONSE.search(bloc)
        if q and r:
            paires.append((_texte(q.group(1)), _texte(r.group(1))))
    return paires


def jsonld_faq(page_html):
    """Le FAQPage schema.org dérivé de la page. Vide s'il n'y a pas de FAQ —
    on ne balise pas ce qui n'existe pas."""
    paires = extraire_faq(page_html)
    if not paires:
        return None
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": "fr",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": r}}
            for q, r in paires
        ],
    }


def bloc_script(page_html):
    """Le <script> prêt à poser avant </head>. `data-geo="faq"` le rend
    retrouvable par le contrôle — et par la personne qui régénère."""
    d = jsonld_faq(page_html)
    if d is None:
        return ""
    return ('<script type="application/ld+json" data-geo="faq">'
            + json.dumps(d, ensure_ascii=False) + "</script>")


def bloc_en_place(page_html):
    """Le JSON-LD FAQ déjà présent dans la page, décodé — None s'il manque."""
    m = _BLOC.search(page_html or "")
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None
