"""
agent_datacenter.py
Agent specialise Data Centers pour Sentinel.

Objet
-----
Produire des livrables de haut niveau pour les pages "transformation" et
"conseils" (data centers bas carbone et sujets data centers specifiques) a
partir d'un corpus documentaire general, sans fine tuning de modele :

  1. segmentation thematique du corpus et etiquetage des passages ;
  2. recuperation filtree par page, avec seuil de similarite et refus de
     generation lorsque le contexte est insuffisant ;
  3. gabarits de livrables imposant plan, chiffrage et references ;
  4. boucle critique deterministe puis LLM, avec regeneration ciblee ;
  5. journalisation exploitable par le registre de transparence article 50.

Integration
-----------
Le module est agnostique du fournisseur de modele. Deux fonctions sont
injectees a la construction de l'agent :

    embed_fn(list[str]) -> list[list[float]]
    complete_fn(system: str, user: str, temperature: float) -> str

Elles doivent pointer vers le proxy serveur existant de Sentinel. Aucune cle
d'API n'est lue ni stockee ici.

Conventions de code Sentinel respectees : le module "re" est importe sous le
nom "_re" ; aucune reference AIES ; module compilable par py_compile.

Note d'integration (ajouts au module d'origine, chacun signale sur place)
-----------------------------------------------------------------------
Cinq points ont ete completes lors de la mise en service. Ils sont documentes
au fil du code plutot qu'ici, mais le plus important merite d'etre annonce :
`_normalise` unifie desormais les apostrophes. Sans cela, un modele qui ecrit
"donnees d'entree" avec l'apostrophe typographique — ce que fait tout modele
redigeant en francais — voyait sa section declaree MANQUANTE alors qu'elle
etait la. Le controle deterministe declenchait une regeneration inutile, puis
marquait non conforme un livrable correct.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re as _re
import threading
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Sequence

CORPUS_VERSION = "2026.08"

# ---------------------------------------------------------------------------
# 1. Segmentation thematique
# ---------------------------------------------------------------------------

# Chaque theme porte des motifs de reconnaissance. Un passage non reconnu est
# etiquete "non_classe" et reste exclu de toute recuperation : il ne peut donc
# pas contaminer un livrable.
THEMES: dict[str, dict[str, object]] = {
    "efficacite_energetique": {
        "label": "Efficacite energetique et PUE",
        "patterns": [
            r"\bpue\b", r"power usage effectiveness", r"rendement energetique",
            r"charge it", r"\bkwh\b", r"consommation electrique",
        ],
    },
    "eau": {
        "label": "Usage de l'eau et WUE",
        "patterns": [
            r"\bwue\b", r"water usage effectiveness", r"consommation d'eau",
            r"tour aerorefrigerante", r"adiabatique",
        ],
    },
    "refroidissement": {
        "label": "Refroidissement et free cooling",
        "patterns": [
            r"free cooling", r"refroidissement", r"immersion", r"direct[- ]to[- ]chip",
            r"confinement (?:chaud|froid)", r"\bcrac\b", r"\bcrah\b", r"delta t",
        ],
    },
    "chaleur_fatale": {
        "label": "Recuperation de chaleur fatale",
        "patterns": [
            r"chaleur fatale", r"recuperation de chaleur", r"reseau de chaleur",
            r"pompe a chaleur", r"\bere\b", r"energy reuse",
        ],
    },
    "energie_bas_carbone": {
        "label": "Approvisionnement bas carbone",
        "patterns": [
            r"\bppa\b", r"garantie d'origine", r"mix electrique", r"facteur d'emission",
            r"bas carbone", r"photovolta", r"eolien", r"\bcfe\b",
        ],
    },
    "reglementaire_eed": {
        "label": "EED article 12 et rapportage",
        "patterns": [
            r"\beed\b", r"directive 2023/1791", r"article 12", r"reglement delegue",
            r"declaration annuelle", r"registre europeen",
        ],
    },
    "code_of_conduct": {
        "label": "EU Code of Conduct et EN 50600",
        "patterns": [
            r"code of conduct", r"en ?50600", r"iso ?30134", r"best practice",
            r"bonne pratique",
        ],
    },
    "csrd_acv": {
        "label": "CSRD, GHG Protocol et analyse de cycle de vie",
        "patterns": [
            r"\bcsrd\b", r"\besrs\b", r"ghg protocol", r"scope ?[123]",
            r"analyse de cycle de vie", r"\bacv\b", r"empreinte carbone",
            r"carbone incorpore",
        ],
    },
    "raccordement": {
        "label": "Raccordement, puissance et flexibilite reseau",
        "patterns": [
            r"raccordement", r"puissance souscrite", r"effacement", r"flexibilite",
            r"groupe electrogene", r"\bups\b", r"onduleur",
        ],
    },
    "gouvernance_ia": {
        "label": "Charge IA, gouvernance et souverainete",
        "patterns": [
            r"gigafactor", r"charge ia", r"\bgpu\b", r"densite de baie",
            r"souverainete", r"ai act", r"gouvernance",
        ],
    },
}

# Espaces thematiques autorises par page. Une page ne consomme que ses espaces.
PAGES: dict[str, dict[str, object]] = {
    "transformation": {
        "label": "Transformation des data centers",
        "themes": [
            "efficacite_energetique", "refroidissement", "raccordement",
            "code_of_conduct", "gouvernance_ia", "reglementaire_eed",
        ],
    },
    "conseils_bas_carbone": {
        "label": "Conseils data centers bas carbone",
        "themes": [
            "energie_bas_carbone", "chaleur_fatale", "csrd_acv", "eau",
            "efficacite_energetique", "reglementaire_eed",
        ],
    },
    "conseils_specifiques": {
        "label": "Conseils data centers, sujets specifiques",
        "themes": list(THEMES.keys()),
    },
}

_COMPILED = {
    theme: [_re.compile(p, _re.IGNORECASE) for p in cfg["patterns"]]
    for theme, cfg in THEMES.items()
}

# AJOUT — Unification des apostrophes et tirets.
#
# C'est la correction la plus importante du lot, et la moins visible. Les
# gabarits ecrivent "Perimetre et donnees d'entree" avec l'apostrophe droite ;
# un modele redigeant en francais ecrit "données d'entrée" avec l'apostrophe
# typographique. Les deux chaines normalisees ne se ressemblaient pas, donc le
# controle deterministe declarait la section manquante — alors qu'elle etait
# la, correctement redigee. Consequence en chaine : une regeneration inutile
# (donc un appel de modele paye pour rien), puis un livrable correct marque
# non conforme, puis un journal de transparence qui enregistre un defaut qui
# n'existe pas.
_APOSTROPHES = dict.fromkeys(map(ord, "’‘‛ʼ´`"), "'")
_TIRETS = dict.fromkeys(map(ord, "‐‑‒–—−"), "-")


def _normalise(text: str) -> str:
    """Minuscules sans diacritiques, pour une reconnaissance robuste.

    Unifie aussi les apostrophes et les tirets, et ecrase les espaces
    multiples : ce sont les trois variations que produit un modele sans qu'on
    le lui demande, et chacune suffit a faire echouer une comparaison de
    chaines qui devrait reussir.
    """
    text = text.translate(_APOSTROPHES).translate(_TIRETS)
    decomposed = unicodedata.normalize("NFKD", text.lower())
    sans_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _re.sub(r"\s+", " ", sans_accents)


def classify(text: str) -> tuple[str, int]:
    """Retourne le theme dominant et son score de correspondance."""
    probe = _normalise(text)
    best_theme, best_score = "non_classe", 0
    for theme, regexes in _COMPILED.items():
        score = sum(len(rx.findall(probe)) for rx in regexes)
        if score > best_score:
            best_theme, best_score = theme, score
    return best_theme, best_score


def split_document(text: str, max_chars: int = 1200) -> list[str]:
    """Decoupe en passages sur les ruptures de paragraphe, taille bornee."""
    paragraphs = [p.strip() for p in _re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 2 <= max_chars:
            buffer = f"{buffer}\n\n{paragraph}".strip()
        else:
            if buffer:
                chunks.append(buffer)
            buffer = paragraph[:max_chars]
    if buffer:
        chunks.append(buffer)
    return chunks


# ---------------------------------------------------------------------------
# 2. Index et recuperation filtree
# ---------------------------------------------------------------------------

@dataclass
class Passage:
    id: str
    source: str
    theme: str
    theme_score: int
    published_on: str
    text: str
    embedding: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "source": self.source, "theme": self.theme,
            "theme_score": self.theme_score, "published_on": self.published_on,
            "text": self.text, "embedding": self.embedding,
        }

    @staticmethod
    def from_dict(raw: dict) -> "Passage":
        return Passage(
            id=raw["id"], source=raw["source"], theme=raw["theme"],
            theme_score=int(raw.get("theme_score", 0)),
            published_on=raw.get("published_on", ""), text=raw["text"],
            embedding=list(raw.get("embedding", [])),
        )


class EmbeddingIndisponible(RuntimeError):
    """Le service de vectorisation n'a pas repondu, ou a repondu de travers.

    AJOUT. Distincte d'une erreur quelconque : sans elle, un lot de vecteurs
    incomplet passait silencieusement — zip s'arrete au plus court, les
    passages restants gardaient un vecteur vide, et cosine renvoyait 0.0 pour
    eux. Ils etaient donc indexes et INTROUVABLES : le corpus paraissait
    complet et la recuperation ne les proposait jamais.
    """


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class CorpusIndex:
    """Index thematique persistant en JSON. Substituable par pgvector."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path
        self.passages: list[Passage] = []
        # AJOUT — verrou. Le serveur sert plusieurs requetes en parallele :
        # deux imports simultanes se marchaient dessus sur self.passages, et
        # deux ecritures d'index concurrentes produisaient un JSON tronque,
        # c'est-a-dire un corpus perdu.
        self._lock = threading.Lock()
        if path and os.path.exists(path):
            self.load()

    def add_document(
        self,
        text: str,
        source: str,
        published_on: str,
        embed_fn: Callable[[list[str]], list[list[float]]],
        min_theme_score: int = 1,
    ) -> int:
        """Segmente, etiquette, vectorise. Retourne le nombre de passages retenus."""
        retained: list[Passage] = []
        for chunk in split_document(text):
            theme, score = classify(chunk)
            if theme == "non_classe" or score < min_theme_score:
                continue
            retained.append(Passage(
                id=uuid.uuid4().hex[:12], source=source, theme=theme,
                theme_score=score, published_on=published_on, text=chunk,
            ))
        if retained:
            vectors = embed_fn([p.text for p in retained])
            # AJOUT — on refuse un lot incomplet plutot que de l'indexer a
            # moitie. Un passage sans vecteur est un passage invisible, et rien
            # dans l'interface ne le signalerait.
            if not vectors or len(vectors) != len(retained):
                raise EmbeddingIndisponible(
                    f"{len(vectors) if vectors else 0} vecteur(s) recu(s) pour "
                    f"{len(retained)} passage(s) : aucun n'est indexe."
                )
            for passage, vector in zip(retained, vectors):
                if not vector:
                    raise EmbeddingIndisponible(
                        "Vecteur vide renvoye : aucun passage n'est indexe.")
                passage.embedding = list(vector)
            with self._lock:
                self.passages.extend(retained)
        return len(retained)

    def search(
        self,
        query_vector: Sequence[float],
        page: str,
        top_k: int = 8,
        threshold: float = 0.32,
    ) -> list[tuple[Passage, float]]:
        allowed = set(PAGES.get(page, {}).get("themes", []))
        if not allowed:
            raise ValueError(f"Page inconnue : {page}")
        scored = [
            (p, cosine(query_vector, p.embedding))
            for p in self.passages if p.theme in allowed
        ]
        scored = [item for item in scored if item[1] >= threshold]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    def save(self, path: str | None = None) -> None:
        target = path or self.path
        if not target:
            raise ValueError("Aucun chemin d'index defini.")
        payload = {
            "corpus_version": CORPUS_VERSION,
            "passages": [p.to_dict() for p in self.passages],
        }
        # AJOUT — ecriture atomique. Une coupure au milieu d'un json.dump
        # laissait un fichier tronque, que le prochain load() refusait : le
        # corpus entier disparaissait au redemarrage suivant.
        with self._lock:
            provisoire = f"{target}.tmp"
            with open(provisoire, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
            os.replace(provisoire, target)

    def load(self, path: str | None = None) -> None:
        target = path or self.path
        with open(target, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.passages = [Passage.from_dict(r) for r in payload.get("passages", [])]


# ---------------------------------------------------------------------------
# 3. Gabarits de livrables
# ---------------------------------------------------------------------------

DELIVERABLES: dict[str, dict[str, object]] = {
    "diagnostic": {
        "label": "Diagnostic energie et carbone",
        "sections": [
            "Perimetre et donnees d'entree",
            "Situation de reference chiffree",
            "Ecarts au regard des exigences applicables",
            "Risques et points de vigilance",
            "Conclusion et suites recommandees",
        ],
    },
    "feuille_de_route": {
        "label": "Feuille de route de transformation",
        "sections": [
            "Objectif cible et indicateurs",
            "Actions a court terme, moins de douze mois",
            "Actions structurantes, douze a trente-six mois",
            "Conditions de reussite et dependances",
            "Trajectoire de gains attendus",
        ],
    },
    "note_technique": {
        "label": "Note technique specifique",
        "sections": [
            "Enonce du sujet et hypotheses",
            "Etat de l'art applicable",
            "Analyse technique chiffree",
            "Cadre normatif et reglementaire",
            "Recommandation motivee",
        ],
    },
}

SYSTEM_PROMPT = (
    "Vous etes un ingenieur conseil senior specialise dans les data centers, "
    "l'efficacite energetique et la conformite environnementale. Vous redigez "
    "en francais, dans un registre professionnel et sobre. Regles imperatives : "
    "n'utilisez que les extraits fournis ; chaque affirmation factuelle est "
    "suivie de sa reference sous la forme [S1], [S2] ; chaque section comporte "
    "au moins une valeur chiffree issue des extraits ; si un element manque, "
    "vous ecrivez explicitement la mention Donnee non disponible dans le corpus, "
    "sans jamais l'inventer ; aucune reference normative n'est citee si elle "
    "n'apparait pas dans les extraits."
)


def build_context(hits: Sequence[tuple[Passage, float]]) -> tuple[str, list[dict]]:
    """Construit le bloc d'extraits numerotes et la table des sources."""
    blocks, sources = [], []
    for position, (passage, score) in enumerate(hits, start=1):
        marker = f"S{position}"
        # AJOUT — .get plutot qu'indexation directe. Un index construit sous
        # une version anterieure du vocabulaire porte des themes qui n'existent
        # plus ; une KeyError ici ferait echouer la generation entiere, alors
        # que le passage lui-meme reste parfaitement utilisable.
        theme_cfg = THEMES.get(passage.theme) or {}
        theme_label = theme_cfg.get("label") or f"theme retire du referentiel ({passage.theme})"
        blocks.append(
            f"[{marker}] Source : {passage.source} "
            f"(theme : {theme_label}, "
            f"date : {passage.published_on or 'non datee'})\n{passage.text}"
        )
        sources.append({
            "marker": marker, "passage_id": passage.id, "source": passage.source,
            "theme": passage.theme, "published_on": passage.published_on,
            "similarity": round(score, 4),
        })
    # LA CLOTURE. Ce module a son PROPRE entonnoir de contexte, distinct de
    # celui de rag_store. Proteger l'un sans l'autre laisserait une porte
    # ouverte a cote d'une porte fermee — et c'est celle qu'on oublie qu'on
    # emprunte. Les extraits sont des DONNEES, jamais des consignes.
    corps = "\n\n".join(blocks)
    if not corps.strip():
        return "", sources
    try:
        import garde_ia
    except Exception:
        # Meme regle que pour l'analyse antivirale : une porte absente qui
        # laisse passer est pire que pas de porte. Sans le garde, pas de
        # contexte du tout — l'agent refusera faute de corpus, ce qui se voit,
        # au lieu d'obeir a un document, ce qui ne se voit pas.
        return "", sources
    bloc, _ = garde_ia.clore(corps)
    return bloc, sources


# ---------------------------------------------------------------------------
# 4. Controle qualite
# ---------------------------------------------------------------------------

RUBRIC = {
    "exactitude_reglementaire": 0.35,
    "chiffrage": 0.25,
    "tracabilite": 0.25,
    "absence_affirmation_non_sourcee": 0.15,
}

CRITIC_PROMPT = (
    "Vous evaluez un livrable technique au regard des seuls extraits fournis. "
    "Repondez exclusivement par un objet JSON, sans texte ni balise, au format : "
    '{"exactitude_reglementaire": 0-5, "chiffrage": 0-5, "tracabilite": 0-5, '
    '"absence_affirmation_non_sourcee": 0-5, "defauts": ["..."]}. '
    "Sanctionnez toute reference normative absente des extraits, toute valeur "
    "chiffree non tracable et toute section depourvue de reference."
)


@dataclass
class QualityReport:
    deterministic_defects: list[str]
    scores: dict[str, float]
    defects: list[str]
    weighted_score: float
    # AJOUT — un critique injoignable n'est PAS un livrable mauvais.
    # Sans ce drapeau, une panne du service d'evaluation produisait un score de
    # zero, donc "non conforme", donc deux regenerations inutiles, et un
    # journal de transparence affirmant un defaut de qualite qui n'a jamais ete
    # constate. Le doute doit se lire comme un doute.
    critique_indisponible: bool = False

    @property
    def passed(self) -> bool:
        return not self.deterministic_defects and self.weighted_score >= 4.0

    @property
    def concluant(self) -> bool:
        """Vrai si le controle a pu se prononcer, dans un sens ou dans l'autre."""
        return not self.critique_indisponible


# ---------------------------------------------------------------------------
# LES CHIFFRES DOIVENT VENIR DES EXTRAITS — ET C'ETAIT UNE CONSIGNE, PAS UN
# CONTROLE.
#
# Le prompt systeme dit au modele de n'utiliser que les extraits et de ne
# jamais inventer une valeur. Rien ne le verifiait. Un livrable pouvait donc
# citer [S1] correctement — le controle des marqueurs passait — et poser a cote
# un chiffre qui ne figure nulle part dans le corpus. C'est le defaut le plus
# couteux qu'un livrable puisse porter : il a l'apparence exacte du travail
# source, et il tombe a la premiere verification du client.
#
# CE QU'ON CONTROLE, ET POURQUOI PAS TOUT. On ne verifie que les QUANTITES :
# un nombre portant une unite, ou un nombre a decimales. Un identifiant n'est
# pas une quantite — « directive 2023/1791 », « IEC 62443 », « EN 50600-4-2 »
# ne se sourcent pas comme un debit d'eau. Les compter aurait noye le controle
# sous des signalements faux, et un controle qui crie pour rien finit
# desactive : le module le dit deja ailleurs, on applique la meme prudence.
# Les entiers sous 10 sont ecartes pour la meme raison — « 3 suites », « 1
# risque » sont des denombrements de redaction, pas des mesures.
#
# LA DEMANDE DU CLIENT EST UNE SOURCE LEGITIME. Un chiffre qu'il fournit dans
# son brief (« notre site fait 4,2 MW ») doit pouvoir etre repris ; le refuser
# obligerait a le retirer du livrable.

_UNITES = (
    r"%|€|k€|M€|Md€|kW|MW|GW|kWh|MWh|GWh|TWh|Wh|VA|kVA|kVAr|"
    r"m3|m³|m2|m²|L|l|litres?|t|kg|g|tCO2e|kgCO2e|gCO2e|tCO₂e|kgCO₂e|gCO₂e|"
    r"an|ans|annees?|années?|mois|jours?|heures?|h|°C|K|bar|ppm|"
    r"W/m|kW/baie|l/kWh|L/kWh|g/kWh|m3/an|m³/an"
)
# LA GARDE EST EN AMONT, PAS EN AVAL. Refuser un nombre SUIVI d'un point
# ecartait « 0,77. » en fin de phrase — c'est-a-dire la moitie des extraits, et
# le controle signalait alors comme inventees des valeurs bel et bien sourcees.
# La garde amont, elle, reste : elle ecarte « 1791 » de « 2023/1791 », qui est
# un numero de directive et non une mesure.
_NOMBRE = _re.compile(
    r"(?<![\w./-])(\d{1,3}(?:[\s\u00a0\u202f]\d{3})+|\d+(?:[.,]\d+)?)"
    r"(?!\w)"
)
# PAS DE \b APRES L'UNITE : « % », « € », « °C » ne sont pas des caracteres de
# mot, et la frontiere echouait donc toujours apres eux. Un pourcentage invente
# passait le controle — mesure, puis corrige.
_SUIT_UNITE = _re.compile(r"^[\s\u00a0\u202f]{0,3}(?:" + _UNITES + r")(?![\wÀ-ÿ])")


def _quantites(texte: str) -> set:
    """Les nombres qui se comportent comme des MESURES, en valeur flottante."""
    out = set()
    for m in _NOMBRE.finditer(texte or ""):
        brut = m.group(1)
        normalise = (brut.replace("\u202f", "").replace("\u00a0", "")
                     .replace(" ", "").replace(",", "."))
        try:
            valeur = float(normalise)
        except ValueError:
            continue
        decimal = ("," in brut) or ("." in brut)
        unite = bool(_SUIT_UNITE.match(texte[m.end():m.end() + 14]))
        if not (decimal or unite):
            continue
        if abs(valeur) < 10 and float(valeur).is_integer():
            continue
        out.add(round(valeur, 6))
    return out


def _adossee(valeur: float, sourcees: set) -> bool:
    """Une quantite est adossee si elle figure dans les extraits — a l'arrondi
    pres. Le modele qui ecrit « 1,4 » pour un extrait a « 1,42 » n'invente
    rien : il arrondit, et le lui reprocher rendrait le controle inutilisable.
    """
    for s in sourcees:
        if s == valeur:
            return True
        echelle = max(abs(s), abs(valeur), 1e-9)
        if abs(s - valeur) / echelle <= 0.005:      # arrondi a 0,5 %
            return True
        for chiffres in (1, 2, 3):                   # arrondi explicite
            if round(s, chiffres) == round(valeur, chiffres):
                return True
    return False


def chiffres_hors_source(draft: str, context: str, brief: str = "") -> list:
    """Les quantites du livrable qui ne figurent ni dans les extraits ni dans
    la demande du client. Rendues triees, pour un message stable."""
    sourcees = _quantites(context) | _quantites(brief)
    return sorted(v for v in _quantites(draft) if not _adossee(v, sourcees))


def deterministic_check(draft: str, sections: Sequence[str], markers: Sequence[str],
                        context: str = "", brief: str = "") -> list[str]:
    """Verifications sans appel de modele : plan, chiffrage, marqueurs de
    source, et PROVENANCE DES QUANTITES."""
    defects: list[str] = []
    probe = _normalise(draft)
    for section in sections:
        if _normalise(section)[:28] not in probe:
            defects.append(f"Section manquante ou renommee : {section}")
    known = set(markers)
    cited = set(_re.findall(r"\[S\d+\]", draft))
    unknown = sorted(m for m in cited if m.strip("[]") not in known)
    if unknown:
        defects.append(f"References inexistantes citees : {', '.join(unknown)}")
    if not cited:
        defects.append("Aucune reference de source dans le livrable.")
    if not _re.search(r"\d", draft):
        defects.append("Aucune valeur chiffree dans le livrable.")
    # LE CONTROLE N'EST FAIT QUE SI LE CONTEXTE EST FOURNI. Sans lui, toute
    # quantite paraitrait inventee : un appelant qui ne le passe pas obtiendrait
    # un livrable rejete pour une raison fausse.
    if context:
        inventees = chiffres_hors_source(draft, context, brief)
        if inventees:
            defects.append(
                "Quantites absentes des extraits et de la demande : "
                + ", ".join(_fr(v) for v in inventees[:8])
                + (" (et %d autre(s))" % (len(inventees) - 8) if len(inventees) > 8 else "")
            )
    return defects


def _fr(v: float) -> str:
    """Un nombre ecrit comme le livrable l'ecrit, pour que le defaut se
    retrouve a l'oeil dans le texte."""
    if float(v).is_integer():
        return format(int(v), ",d").replace(",", "\u202f")
    return ("%.4f" % v).rstrip("0").rstrip(".").replace(".", ",")


def _parse_scores(raw: str) -> tuple[dict[str, float], list[str], bool]:
    """Retourne (scores, defauts, indisponible).

    Le troisieme element est l'ajout : il distingue "le critique a lu et
    sanctionne" de "le critique n'a rien pu dire". Les deux produisaient
    jusqu'ici le meme zero.
    """
    if not raw or not raw.strip():
        return {key: 0.0 for key in RUBRIC}, ["Evaluation indisponible."], True
    match = _re.search(r"\{.*\}", raw, _re.DOTALL)
    if not match:
        return {key: 0.0 for key in RUBRIC}, ["Evaluation illisible."], True
    try:
        payload = json.loads(match.group(0))
    except ValueError:
        return {key: 0.0 for key in RUBRIC}, ["Evaluation illisible."], True
    scores = {key: float(payload.get(key, 0) or 0) for key in RUBRIC}
    defects = [str(d) for d in payload.get("defauts", [])]
    return scores, defects, False


# ---------------------------------------------------------------------------
# 5. Agent
# ---------------------------------------------------------------------------

class InsufficientContext(RuntimeError):
    """Leve lorsque le corpus ne couvre pas suffisamment la demande."""


class DataCenterAgent:
    def __init__(
        self,
        index: CorpusIndex,
        embed_fn: Callable[[list[str]], list[list[float]]],
        complete_fn: Callable[..., str],
        journal_path: str = "journal_agent_datacenter.jsonl",
        threshold: float = 0.32,
        min_passages: int = 3,
        max_attempts: int = 2,
    ) -> None:
        self.index = index
        self.embed_fn = embed_fn
        self.complete_fn = complete_fn
        self.journal_path = journal_path
        self.threshold = threshold
        self.min_passages = min_passages
        self.max_attempts = max_attempts
        # AJOUT — le journal est ecrit depuis plusieurs requetes simultanees.
        # Une ligne JSONL de plusieurs kilo-octets n'est pas ecrite d'un bloc :
        # deux ajouts concurrents entrelacaient leurs caracteres et rendaient le
        # journal illisible. Or c'est la piece qui fonde la transparence de
        # l'article 50 : un journal corrompu n'est pas un desagrement, c'est une
        # obligation qui tombe.
        self._journal_lock = threading.Lock()

    def generate(self, page: str, deliverable: str, brief: str) -> dict:
        if deliverable not in DELIVERABLES:
            raise ValueError(f"Livrable inconnu : {deliverable}")
        template = DELIVERABLES[deliverable]
        sections: list[str] = list(template["sections"])

        query_vector = self.embed_fn([brief])[0]
        hits = self.index.search(query_vector, page, top_k=8, threshold=self.threshold)
        if len(hits) < self.min_passages:
            raise InsufficientContext(
                f"Corpus insuffisant pour la page {page} : "
                f"{len(hits)} passage(s) au-dessus du seuil {self.threshold}."
            )

        context, sources = build_context(hits)
        markers = [s["marker"] for s in sources]
        plan = "\n".join(f"{i}. {s}" for i, s in enumerate(sections, start=1))

        draft, report, attempts = "", None, 0
        corrections = ""
        while attempts < self.max_attempts:
            attempts += 1
            user_prompt = (
                f"Page cible : {PAGES[page]['label']}\n"
                f"Livrable : {template['label']}\n"
                f"Demande du client :\n{brief}\n\n"
                f"Plan impose, a respecter titre par titre :\n{plan}\n\n"
                f"Extraits autorises :\n{context}\n"
                f"{corrections}"
            )
            draft = self.complete_fn(SYSTEM_PROMPT, user_prompt, 0.2)
            report = self.review(draft, sections, markers, context, brief)
            if report.passed:
                break
            # AJOUT — ne pas regenerer quand le CRITIQUE est en panne et que le
            # controle deterministe, lui, n'a rien trouve. Le brouillon est
            # peut-etre bon ; le refaire ne le rendra pas meilleur, et le second
            # appel echouera pour la meme raison que le premier.
            if report.critique_indisponible and not report.deterministic_defects:
                break
            corrections = (
                "\n\nDefauts releves lors du controle precedent, a corriger "
                "integralement :\n- " + "\n- ".join(
                    report.deterministic_defects + report.defects
                )
            )

        entry = self.journalise(page, deliverable, brief, draft, sources, report, attempts)
        return {
            "livrable": draft,
            "sources": sources,
            "controle": {
                "score": report.weighted_score if report else 0.0,
                "conforme": bool(report and report.passed),
                "concluant": bool(report and report.concluant),
                "defauts": (report.deterministic_defects + report.defects) if report else [],
            },
            "tentatives": attempts,
            "journal_id": entry["id"],
        }

    def review(
        self, draft: str, sections: Sequence[str], markers: Sequence[str], context: str,
        brief: str = ""
    ) -> QualityReport:
        deterministic = deterministic_check(draft, sections, markers, context, brief)
        # AJOUT — une panne du critique ne doit pas faire echouer la generation
        # entiere. Le controle deterministe, lui, a deja rendu son verdict et il
        # est le plus important des deux : c'est le seul qui ne depende de rien.
        try:
            raw = self.complete_fn(
                CRITIC_PROMPT,
                f"Extraits autorises :\n{context}\n\nLivrable a evaluer :\n{draft}",
                0.0,
            )
        except Exception as exc:  # noqa: BLE001
            return QualityReport(deterministic, {k: 0.0 for k in RUBRIC},
                                 [f"Evaluation indisponible : {exc}"], 0.0, True)
        scores, defects, indisponible = _parse_scores(raw)
        weighted = sum(scores[key] * weight for key, weight in RUBRIC.items())
        return QualityReport(deterministic, scores, defects, round(weighted, 2),
                             indisponible)

    def journalise(
        self,
        page: str,
        deliverable: str,
        brief: str,
        draft: str,
        sources: list[dict],
        report: QualityReport | None,
        attempts: int,
    ) -> dict:
        entry = {
            "id": uuid.uuid4().hex,
            "horodatage": datetime.now(timezone.utc).isoformat(),
            "page": page,
            "livrable": deliverable,
            "corpus_version": CORPUS_VERSION,
            "empreinte_demande": hashlib.sha256(brief.encode("utf-8")).hexdigest()[:16],
            "empreinte_livrable": hashlib.sha256(draft.encode("utf-8")).hexdigest()[:16],
            "sources": [
                {"marker": s["marker"], "source": s["source"],
                 "passage_id": s["passage_id"], "similarite": s["similarity"]}
                for s in sources
            ],
            "scores": report.scores if report else {},
            "score_pondere": report.weighted_score if report else 0.0,
            "conforme": bool(report and report.passed),
            "controle_concluant": bool(report and report.concluant),
            "defauts": (report.deterministic_defects + report.defects) if report else [],
            "tentatives": attempts,
        }
        with self._journal_lock:
            with open(self.journal_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry


# ---------------------------------------------------------------------------
# 6. Exposition Flask facultative
# ---------------------------------------------------------------------------

def build_blueprint(agent: DataCenterAgent,
                    url_prefix: str = "/api/datacenter/agent",
                    garde: Callable | None = None):
    """Retourne un blueprint Flask. A enregistrer depuis app.py en une ligne.

    Le prefixe par defaut est /api/datacenter/AGENT et non /api/datacenter :
    ce site expose deja un moteur de calcul deterministe sous /api/datacenter
    (etude, comparaison, export). Deux regles Flask sur la meme URL ne levent
    pas d'erreur — la premiere enregistree gagne, l'autre est silencieusement
    morte. Un conflit d'URL qui ne dit rien est plus couteux qu'une collision
    bruyante : on l'ecarte par construction.

    AJOUT — le parametre `garde`. Le blueprint d'origine etait entierement
    OUVERT : /api/datacenter/generer faisait travailler un modele et livrait une
    etude a qui la demandait. Le module reste agnostique — il ne sait rien du
    systeme de comptes de l'hote — mais il accepte desormais un decorateur, que
    l'appelant fournit. Par defaut il n'y en a pas, ce qui convient a un usage
    hors ligne ; sur Sentinel, app.py passe le verrou des abonnes.
    """
    from flask import Blueprint, jsonify, request

    blueprint = Blueprint("agent_datacenter", __name__, url_prefix=url_prefix)
    protege = garde if callable(garde) else (lambda f: f)

    # AJOUT — `agent` accepte aussi une FONCTION qui renvoie l'agent. Un
    # blueprint s'enregistre a l'import de l'application, alors qu'un agent
    # charge son corpus depuis le disque : exiger l'objet construit imposerait
    # cette lecture a chaque demarrage, y compris quand personne n'ouvrira la
    # page. La resolution a lieu par requete, ce qui coute une indirection.
    def _agent():
        return agent() if callable(agent) and not isinstance(agent, DataCenterAgent) else agent

    @blueprint.route("/generer", methods=["POST"])
    @protege
    def generer():
        payload = request.get_json(silent=True) or {}
        page = str(payload.get("page", "")).strip()
        deliverable = str(payload.get("livrable", "")).strip()
        brief = str(payload.get("demande", "")).strip()
        if page not in PAGES or deliverable not in DELIVERABLES or len(brief) < 20:
            return jsonify({"erreur": "Parametres invalides."}), 400
        try:
            return jsonify(_agent().generate(page, deliverable, brief)), 200
        except InsufficientContext as exc:
            return jsonify({"erreur": str(exc), "code": "corpus_insuffisant"}), 422
        # AJOUT — la vectorisation peut etre indisponible (cle absente, service
        # injoignable). Sans ce cas, la reponse etait un 500 opaque, et
        # l'utilisateur concluait a une panne du site.
        except EmbeddingIndisponible as exc:
            return jsonify({"erreur": str(exc), "code": "vectorisation_indisponible"}), 503

    @blueprint.route("/referentiel", methods=["GET"])
    @protege
    def referentiel():
        return jsonify({
            "corpus_version": CORPUS_VERSION,
            "pages": {k: v["label"] for k, v in PAGES.items()},
            "livrables": {k: v["label"] for k, v in DELIVERABLES.items()},
            "themes": {k: v["label"] for k, v in THEMES.items()},
            "passages_indexes": len(_agent().index.passages),
        }), 200

    return blueprint
