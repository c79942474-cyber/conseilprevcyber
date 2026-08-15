"""GEO — être lisible par les moteurs génératifs sans jamais leur mentir.

Trois contrats, chacun avec le mensonge qu'il empêche :

  1. robots.txt ADMET nommément les robots d'IA (ChatGPT, Claude, Perplexity,
     Gemini, Common Crawl) sur le périmètre public — et leur ferme les mêmes
     zones privées qu'aux autres. Le mensonge empêché : une politique « on
     veut être cité » avec un robots qui bloque les citeurs (c'était l'état
     du site frère).

  2. /llms.txt ne référence QUE des adresses qu'un visiteur SANS COMPTE peut
     lire. Le mensonge empêché : promettre à un assistant une page qui lui
     répondra par une redirection de connexion — il citerait un titre sur une
     porte close.

  3. Le JSON-LD FAQPage est DÉRIVÉ de la page et lui reste ÉGAL. Le mensonge
     empêché : un balisage qui répond autre chose que ce que le lecteur voit —
     la définition du contenu trompeur chez tous les opérateurs de recherche.
"""
import json
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import app as A    # noqa: E402
import geo         # noqa: E402


def _client():
    return A.app.test_client()


def test_robots_admet_chaque_robot_ia_sur_les_memes_regles():
    r = _client().get("/robots.txt")
    assert r.status_code == 200
    corps = r.get_data(as_text=True)
    for bot in ("GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot",
                "Claude-User", "Claude-SearchBot", "anthropic-ai",
                "PerplexityBot", "Perplexity-User", "Google-Extended", "CCBot"):
        bloc = re.search(r"User-agent: %s\n(.*?)(?:\n\n|\Z)" % re.escape(bot),
                         corps, re.S)
        assert bloc, "groupe absent : " + bot
        # Admis sur le public, ET fermé sur le privé : un groupe nommé qui ne
        # répète pas les Disallow ouvrirait /admin/ à ce seul robot.
        assert "Allow: /" in bloc.group(1), bot
        assert "Disallow: /admin/" in bloc.group(1), bot
        assert "Disallow: /api/" in bloc.group(1), bot
    assert "Sitemap:" in corps and "/llms.txt" in corps


def test_llms_txt_ne_reference_que_des_pages_lisibles_sans_compte():
    c = _client()
    r = c.get("/llms.txt")
    assert r.status_code == 200
    assert r.mimetype == "text/plain"
    corps = r.get_data(as_text=True)
    assert corps.startswith("# ")           # convention llmstxt.org
    base = A._base_url()
    chemins = sorted({m.rstrip("/") or "/" for m in
                      re.findall(r"\]\(%s(/[^)]*)\)" % re.escape(base), corps)})
    assert chemins, "aucune adresse interne : le fichier ne guide vers rien"
    gated = A._auth_gated_paths()
    for ch in chemins:
        assert ch not in gated, "adresse réservée promise aux assistants : " + ch
        rep = c.get(ch)
        assert rep.status_code == 200, "%s répond %s à un anonyme" % (ch, rep.status_code)
    # Et il dit la vérité sur ce qu'il ne montre pas : les studios sont
    # décrits comme réservés, pas cachés ni promis.
    assert "réservés aux" in corps and "compte" in corps


def test_le_jsonld_faq_est_egal_a_la_page():
    r = _client().get("/faq")
    page = r.get_data(as_text=True)
    en_place = geo.bloc_en_place(page)
    assert en_place, "aucun bloc FAQPage servi sur /faq"
    derive = geo.jsonld_faq(page)
    assert en_place == derive, (
        "le JSON-LD ne correspond plus à la page — régénérer : "
        "python3 -c \"import geo; print(geo.bloc_script(open('faq.html').read()))\"")
    n = len(derive["mainEntity"])
    assert n >= 16, "la FAQ balisée a maigri : %d entrées" % n
    # Les deux entrées GEO : ce que les studios calculent, pour qui.
    questions = " ".join(q["name"] for q in derive["mainEntity"])
    assert "studios data centre" in questions
    assert "À qui s'adressent" in questions


def test_le_garde_TOMBE_si_le_bloc_diverge_de_la_page():
    """La règle n'existe que si sa violation est détectée : on mutile le bloc
    d'une page COPIE et l'égalité doit casser."""
    page = _client().get("/faq").get_data(as_text=True)
    mutee = page.replace("cybersécurité OT/IACS", "cybersécurité QUANTIQUE", 1)
    assert geo.bloc_en_place(mutee) != geo.jsonld_faq(mutee)


def test_la_vitrine_porte_l_entite_reliee():
    """L'accueil relie les deux sites (sameAs) et déclare l'expertise data
    centre : c'est le graphe d'entités que les moteurs génératifs recoupent."""
    page = _client().get("/").get_data(as_text=True)
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    assert m, "pas de JSON-LD sur l'accueil"
    d = json.loads(m.group(1))
    assert "https://conseilprev.onrender.com" in d.get("sameAs", [])
    assert any("centres de données" in k for k in d.get("knowsAbout", []))
