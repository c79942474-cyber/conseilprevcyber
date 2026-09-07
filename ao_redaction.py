# -*- coding: utf-8 -*-
"""Les onze pièces que le cadre laissait vides, mises en brouillon par Claude.

CE QUI ÉTAIT EN CAUSE. Sur les vingt-trois pièces des deux dossiers, sept se
remplissent mécaniquement — la fiche du candidat et les relevés du règlement y
suffisent — et cinq s'obtiennent d'un tiers. Les onze autres SE RÉDIGENT :
mémoire technique, références, DPGF, et huit notes d'accompagnement. Le module
n'en produisait qu'un PLAN — ce que la pièce doit démontrer. C'est utile, et
c'est loin d'une réponse.

CE QUI SORT D'ICI, ET RIEN D'AUTRE. Décision prise, écrite ici parce que c'est
le seul endroit où elle s'applique :

  · les RELEVÉS, c'est-à-dire les VALEURS que l'analyse a extraites — objet,
    procédure, critères, performances exigées, pénalités, délais ;
  · le dossier d'entreprise CONSEILPREV ;
  · le plan de la pièce, tel que le référentiel le porte.

NE SORTENT PAS : le texte des pièces du client, ni même les CITATIONS. Une
citation est un extrait de quatre cents caractères du document de l'acheteur ;
la retenir dans ce qui part serait envoyer le dossier par petits bouts. Le
relevé garde sa citation pour l'écran, pas pour le modèle.

CE QUE CE MODULE N'ÉCRIRA JAMAIS. Aucune déclaration. Le DC1, le DC2 et la
déclaration sur l'honneur portent des affirmations dont la fausseté est
sanctionnée pénalement ; elles n'ont pas de voie « rédiger » et n'entrent pas
ici. La barrière est structurelle — `PIECES` est bornée aux voies `rediger` et
`completer` — et une règle la mesure plutôt que de la supposer.

ET CE QU'IL NE SAIT PAS. Un brouillon n'est pas une référence : le modèle ne
connaît ni nos affaires passées, ni nos effectifs réels, ni nos prix. Tout ce
qu'il ne tient pas du contexte doit ressortir en clair comme À COMPLÉTER,
jamais être inventé pour faire propre. C'est la consigne la plus importante du
brief, et la seule dont l'échec ne se voit pas à la lecture.
"""
import logging
import os

_log = logging.getLogger("ao_redaction")

VERSION = "2026-09-a"

# LE MODÈLE, À PART DE CELUI DE L'ASSISTANT. Le chat vise la latence et tourne
# raisonnement coupé ; rédiger un mémoire technique est l'inverse — on veut le
# raisonnement, et quelques secondes de plus ne coûtent rien sur un document
# qu'on relira une demi-heure.
MODELE = os.environ.get("AO_REDACTION_MODEL", "claude-opus-5")

# Un brouillon de mémoire technique est long. Le SDK impose le flux au-delà de
# ce qu'un appel direct tient sans expirer : on diffuse et l'on recompose.
JETONS_MAX = 16000
DELAI = 300

# ── CE QUI PART, NOMMÉ UNE FOIS ───────────────────────────────────────────
# La liste est EXPLICITE et non « tous les relevés » : un relevé ajouté demain
# ne doit pas sortir sans que quelqu'un l'ait décidé. C'est la propriété qui
# rend la règle de non-fuite tenable dans le temps.
RELEVES_TRANSMIS = (
    "objet", "procedure", "lots", "reference", "criteres", "performances",
    "penalites", "delai", "date_limite", "visite", "variantes", "groupement",
    "assurances", "derogations", "priorite_pieces",
)

# L'acheteur est NOMMÉ, et c'est délibéré : une note de moyens qui ne sait pas
# à qui elle s'adresse est une note générique. Il figure déjà sur le papier à
# en-tête du cabinet, qui coiffe ces mêmes pièces.
RELEVES_TRANSMIS = RELEVES_TRANSMIS + ("acheteur",)

_A_COMPLETER = "[À COMPLÉTER"


class RedactionError(Exception):
    def __init__(self, code, status=502, detail=""):
        Exception.__init__(self, code)
        self.code = code
        self.status = status
        self.detail = detail


def pieces_redigeables(remplissage):
    """Les pièces que ce module accepte de mettre en brouillon.

    BORNÉE AUX VOIES « rediger » ET « completer », et c'est la barrière : une
    déclaration sur l'honneur a la voie « remplir », un extrait Kbis la voie
    « obtenir ». Ni l'une ni l'autre n'entre ici, et aucune liste de clés
    écrite à la main ne peut les y faire entrer par distraction.
    """
    return [p for p in (remplissage or {}).get("pieces", [])
            if p.get("voie") in ("rediger", "completer")]


def contexte(remplissage, analyse, piece):
    """CE QUI PART CHEZ ANTHROPIC, construit ici et nulle part ailleurs.

    Fonction PURE : elle n'appelle rien, ne lit aucun environnement, et rend un
    dictionnaire. C'est ce qui permet de MESURER ce qui sort — une règle
    l'exécute sur un vrai dossier et vérifie que le texte du client n'y est pas.
    """
    import ao_dc

    idx = ao_dc._index_releves(analyse) if analyse else {}
    par_cle = {r["cle"]: r for r in ao_dc.RELEVES}
    consultation = {}
    for cle in RELEVES_TRANSMIS:
        props = idx.get(cle) or []
        # LA VALEUR SEULE, JAMAIS LA CITATION. La citation est un extrait du
        # document de l'acheteur ; la joindre reviendrait à envoyer le dossier
        # par petits bouts. Elle reste à l'écran, où elle sert à vérifier.
        v = (props[0].get("valeur") if props else None) or ""
        if str(v).strip():
            consultation[cle] = {
                "libelle": (par_cle.get(cle) or {}).get("libelle") or cle,
                "valeur": str(v).strip(),
            }

    # LE DOSSIER D'ENTREPRISE, ET CE QU'IL NE PORTE PAS. Nommer les manques
    # dans le contexte vaut mieux que de les taire : le modèle sait alors quoi
    # marquer À COMPLÉTER plutôt que de le deviner.
    fiche, manques = {}, []
    try:
        import dossier_entreprise
        d = dossier_entreprise.fiche_candidat()
        fiche = {k: v for k, v in (d.get("fiche") or {}).items()
                 if str(v).strip()}
        manques = [m["cle"] for m in (d.get("manques") or [])]
    except Exception:
        _log.exception("dossier d'entreprise indisponible pour la rédaction")

    return {
        "piece": {
            "cle": piece["cle"],
            "nom": piece["nom"],
            "ce_qu_elle_doit_contenir": list(piece.get("contient") or []),
            "produite_par": piece.get("produit_par") or "",
            "piege": piece.get("piege") or "",
            "bloquante": bool(piece.get("bloquant")),
        },
        "consultation": consultation,
        "cabinet": fiche,
        "cabinet_ne_porte_pas": manques,
    }


def brief(ctx):
    """La consigne. Séparée de l'appel pour être lue, éprouvée et discutée."""
    L = [
        "Vous rédigez le BROUILLON d'une pièce de candidature à un marché "
        "public français, pour le compte du cabinet dont la fiche est donnée "
        "ci-dessous. Le brouillon sera relu, corrigé et signé par un humain.",
        "",
        "TROIS RÈGLES, DANS CET ORDRE.",
        "",
        "1. N'INVENTEZ RIEN. Aucune référence de chantier, aucun effectif, "
        "aucun chiffre d'affaires, aucun nom de personne, aucune "
        "certification, aucune date, aucun prix qui ne figure pas dans le "
        "contexte. Ce qui manque s'écrit littéralement "
        "« %s : … ] » avec, entre les crochets, ce qu'il faut aller "
        "chercher et où. Une pièce marquée à dix endroits est utile ; une "
        "pièce plausible et fausse fait perdre le marché." % _A_COMPLETER,
        "",
        "2. NE DÉCLAREZ RIEN, N'ATTESTEZ RIEN, NE SIGNEZ RIEN. N'écrivez "
        "jamais « je certifie », « j'atteste », « le candidat déclare sur "
        "l'honneur », ni aucune formule équivalente. Ces affirmations "
        "engagent pénalement celui qui les signe : elles se prennent à la "
        "main, ailleurs, par une personne habilitée.",
        "",
        "3. RÉPONDEZ À CETTE CONSULTATION-CI. Le contexte porte l'objet, la "
        "procédure, les critères de jugement et les exigences relevés au "
        "dossier de l'acheteur. Une note qui pourrait servir à n'importe "
        "quelle consultation ne vaut rien : accrochez chaque paragraphe à "
        "un élément du contexte.",
        "",
        "FORME. Markdown. Pas de titre de niveau 1 — il est déjà posé par le "
        "papier à en-tête. Commencez au niveau 2. Pas de préambule, pas de "
        "commentaire sur votre travail : le document, et rien d'autre.",
    ]
    if ctx["piece"]["bloquante"]:
        L += ["", "CETTE PIÈCE EST BLOQUANTE : son absence rend la "
                  "candidature irrecevable."]
    return "\n".join(L)


def _demande(ctx):
    """Le message utilisateur : le contexte, en clair, sans mise en scène."""
    import json
    return ("Contexte de la consultation et du cabinet :\n\n```json\n"
            + json.dumps(ctx, ensure_ascii=False, indent=1)
            + "\n```\n\nRédigez le brouillon de « %s »." % ctx["piece"]["nom"])


def _client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RedactionError("sans_cle", 503,
                             "ANTHROPIC_API_KEY n'est pas posée : la "
                             "rédaction assistée est indisponible.")
    try:
        import anthropic
    except ImportError:
        raise RedactionError("sans_sdk", 503, "Le paquet anthropic manque.")
    return anthropic


def rediger(cle, remplissage, analyse=None):
    """Le brouillon d'UNE pièce. Rend le Markdown et ce qu'il a coûté.

    UNE PIÈCE PAR APPEL, comme `/marche/piece` : c'est ce qui permet de les
    lancer ensemble et de voir laquelle a résisté. Un appel unique rendrait
    onze brouillons d'un bloc, à la fin, sans savoir lequel a échoué.
    """
    piece = next((p for p in pieces_redigeables(remplissage)
                  if p["cle"] == cle), None)
    if piece is None:
        raise RedactionError("piece_non_redigeable", 400,
                             "Cette pièce ne se rédige pas : elle se remplit, "
                             "s'obtient d'un tiers, ou n'existe pas.")
    anthropic = _client()
    ctx = contexte(remplissage, analyse, piece)
    consigne = brief(ctx)
    client = anthropic.Anthropic()
    try:
        # LE FLUX, PAS L'APPEL DIRECT. Un mémoire technique atteint plusieurs
        # milliers de jetons ; le SDK impose la diffusion au-delà d'un seuil
        # pour ne pas heurter le délai HTTP.
        #
        # LA CONSIGNE EST MISE EN CACHE, et ce n'est pas une micro-économie :
        # les onze pièces d'un même dossier partagent ce préfixe, et le
        # dossier se relance à chaque correction de la fiche.
        with client.messages.stream(
                model=MODELE,
                max_tokens=JETONS_MAX,
                timeout=DELAI,
                system=[{"type": "text", "text": consigne,
                         "cache_control": {"type": "ephemeral"}}],
                thinking={"type": "adaptive"},
                messages=[{"role": "user", "content": _demande(ctx)}]) as flux:
            reponse = flux.get_final_message()
    except anthropic.NotFoundError:
        raise RedactionError("modele_inconnu", 502,
                             "Le modèle « %s » n'existe pas ou n'est pas "
                             "ouvert à cette clé." % MODELE)
    except anthropic.AuthenticationError:
        raise RedactionError("cle_refusee", 502, "La clé a été refusée.")
    except anthropic.RateLimitError:
        raise RedactionError("cadence", 429,
                             "Le fournisseur limite la cadence : reprenez "
                             "dans quelques instants.")
    except anthropic.APIStatusError as exc:
        raise RedactionError("api", 502 if getattr(exc, "status_code", 0) >= 500
                             else 400, str(getattr(exc, "message", "") or "")[:300])
    except anthropic.APIConnectionError:
        raise RedactionError("reseau", 502, "Le fournisseur est injoignable.")

    # UN REFUS N'EST PAS UN DOCUMENT VIDE, et il doit se lire comme un refus.
    if getattr(reponse, "stop_reason", "") == "refusal":
        d = getattr(reponse, "stop_details", None)
        raise RedactionError("refus", 502,
                             "Le modèle a décliné (%s)."
                             % (getattr(d, "category", None) or "sans motif"))
    texte = "".join(b.text for b in reponse.content if b.type == "text").strip()
    if not texte:
        raise RedactionError("vide", 502, "Le modèle n'a rien rendu.")
    u = reponse.usage
    return {
        "cle": cle,
        "nom": piece["nom"],
        "markdown": texte,
        "modele": getattr(reponse, "model", MODELE),
        "tronque": getattr(reponse, "stop_reason", "") == "max_tokens",
        "a_completer": texte.count(_A_COMPLETER),
        "jetons": {"entree": u.input_tokens, "sortie": u.output_tokens,
                   "cache_ecrit": getattr(u, "cache_creation_input_tokens", 0),
                   "cache_lu": getattr(u, "cache_read_input_tokens", 0)},
    }
