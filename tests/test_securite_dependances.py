# -*- coding: utf-8 -*-
"""Le manifeste ne redescend pas sous un plancher de sécurité connu.

CE QUE CETTE RÈGLE MESURE, ET CE QU'ELLE NE PEUT PAS MESURER. Elle lit
`requirements.txt` et compare chaque paquet à la version où TOUTES ses
advisories connues au 10 septembre 2026 (relevé pip-audit) sont corrigées. Elle
attrape un retour en arrière — la ligne qui revient à `pypdf==5.1.0` — et le
nomme. Elle NE prouve PAS que la version épinglée s'installe et fonctionne :
cela demande un build, hors de portée d'un test unitaire. Les deux barrières
sont distinctes et toutes deux nécessaires.

POURQUOI CES CINQ PAQUETS, ET PAS UNE LISTE FIGÉE AU HASARD. Ce sont ceux que
pip-audit signalait vulnérables sur les versions d'alors, et dont le chemin
d'attaque est réel sur ce service :

  - pypdf        : `rag_store.extract_text` ouvre un PDF fourni (base de
                   connaissance, pièces du dossier de consultation, relecture
                   de contrat) — un PDF piégé atteint le lecteur ;
  - requests     : appels sortants (Brevo, plateformes, sources de veille) ;
  - gunicorn     : le serveur WSGI de production (contrebande de requêtes) ;
  - flask        : repli de clé de signature de session (CVE-2025-47278) ;
  - cryptography : chiffrement au repos du dossier marché (ao_projet).
"""
import io
import os

from packaging.requirements import Requirement
from packaging.version import Version

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paquet -> (version plancher, version vulnérable qui l'a motivé). Le plancher
# est la PLUS PETITE version qui efface toutes les advisories connues du paquet.
PLANCHERS = {
    "flask":        ("3.1.3",  "3.0.0"),
    "gunicorn":     ("22.0.0", "21.2.0"),
    "requests":     ("2.33.0", "2.31.0"),
    "pypdf":        ("6.16.1", "5.1.0"),
    "cryptography": ("50.0.0", "46.0.4"),
}


def _epingles():
    """{nom_normalisé: Version} lus dans requirements.txt (lignes épinglées)."""
    out = {}
    with io.open(os.path.join(ICI, "requirements.txt"), encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.split("#", 1)[0].strip()
            if not ligne:
                continue
            try:
                r = Requirement(ligne)
            except Exception:
                continue
            fige = [s.version for s in r.specifier if s.operator in ("==", "===")]
            if fige:
                out[r.name.lower().replace("_", "-")] = Version(fige[0])
    return out


def test_les_cinq_paquets_sensibles_sont_AU_DESSUS_de_leur_plancher():
    epingles = _epingles()
    for paquet, (plancher, vulnerable) in PLANCHERS.items():
        assert paquet in epingles, (
            "%s n'est plus épinglé dans requirements.txt : la règle ne peut "
            "plus garantir qu'il n'est pas sur une version vulnérable" % paquet)
        pose = epingles[paquet]
        assert pose >= Version(plancher), (
            "%s==%s est SOUS le plancher de sécurité %s (la version %s portait "
            "des advisories connues, dont le chemin d'attaque est réel sur ce "
            "service) : le manifeste est redescendu sur une version vulnérable"
            % (paquet, pose, plancher, vulnerable))
        # ET LE PLANCHER EST STRICTEMENT AU-DESSUS DE LA VERSION VULNÉRABLE :
        # sinon la comparaison ci-dessus ne dirait rien.
        assert Version(plancher) > Version(vulnerable), (paquet, plancher, vulnerable)


def test_le_manifeste_ne_reintroduit_pas_une_version_vulnerable_nommee():
    """La non-régression, dite en clair : aucune des versions exactes qui
    étaient vulnérables ne réapparaît. Un test qui ne comparait que « >= » se
    tairait si le plancher lui-même était un jour abaissé par erreur ; celui-ci
    interdit nommément le retour aux versions connues mauvaises."""
    epingles = _epingles()
    for paquet, (_plancher, vulnerable) in PLANCHERS.items():
        if paquet in epingles:
            assert epingles[paquet] != Version(vulnerable), (
                "%s est revenu exactement à %s, la version vulnérable relevée "
                "au pentest" % (paquet, vulnerable))
