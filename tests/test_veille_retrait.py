"""Le retrait des sources sorties de la veille : compter, puis confirmer.

CE QUE CES RÈGLES TIENNENT, ET POURQUOI ELLES EXISTENT. `automation.veille_purger`
et `/api/admin/veille/retirer` étaient écrits, mesurés, journalisés — et
INATTEIGNABLES. Aucune page ne les appelait. Les 257 bulletins CERT-FR restaient
en base non pas faute de moyen, mais faute de bouton : le même défaut que
`/api/admin/veille/refresh` avait eu avant, et pour la même raison — on mesure
la route et on oublie que personne ne peut la déclencher.

CE QUI EST MESURÉ ICI EST LE COMPORTEMENT DE LA PAGE, PAS SA SOURCE. Chercher
« confirmer » dans le fichier dirait seulement que le mot y figure ; il faut
savoir ce qui PART sur le réseau au premier clic, et ce qui n'en part pas. Le
script est donc exécuté sous node contre un faux document et un faux `fetch`
qui ENREGISTRE chaque appel — corps compris.

Le magasin et la liste des clés sont tenus ailleurs (`test_veille_sources.py`) :
la simulation par défaut, la clé héritée `avis` qui pesait 200 bulletins sur
257, et le fait que les clés viennent de `RETIREES` et non de `SOURCES`.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import veille_sources                                               # noqa: E402

PAGE = open(os.path.join(ICI, "admin.html"), encoding="utf-8").read()


def _script():
    """Le script en ligne de la page — celui qui porte les gestes."""
    blocs = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", PAGE, re.S)
    assert len(blocs) == 1, "la page ne porte plus un seul script en ligne"
    return blocs[0]


def _script_nu():
    """Le script SANS SES COMMENTAIRES, pour les règles qui cherchent un mot.

    LA PREMIÈRE VERSION DE LA RÈGLE « aucune clé écrite dans la page » A ÉCHOUÉ
    SUR SON PROPRE COMMENTAIRE : le script explique pourquoi la clé héritée
    `avis` pesait le plus, et le mot y figure donc — sans qu'aucune liste soit
    recopiée. Chercher dans le fichier entier, c'est mesurer la prose.

    LE RETRAIT SE PROUVE : un stripper trop gourmand mangerait du code et la
    règle passerait pour rien. Le témoin ci-dessous exige qu'une chaîne connue
    du script survive au retrait."""
    nu = re.sub(r"/\*.*?\*/", " ", _script(), flags=re.S)
    nu = re.sub(r"(?m)//.*$", " ", nu)
    assert "/api/admin/veille/retirer" in nu, (
        "le retrait des commentaires a mangé du code : la règle qui s'en sert "
        "ne mesurerait plus rien")
    return nu


def _style_de(ident):
    """Le style EN LIGNE que le balisage donne à un élément."""
    m = re.search(r'id="%s"[^>]*\bstyle="([^"]*)"' % re.escape(ident), PAGE)
    return m.group(1) if m else ""


def _display_de(ident):
    m = re.search(r"(?:^|;)\s*display\s*:\s*([^;]+)", _style_de(ident))
    return m.group(1).strip() if m else ""


# ═══════════════════════════════════════════════════════════════════════════
#  LE HARNAIS : un faux document, un faux fetch qui GARDE CE QU'ON LUI DONNE
# ═══════════════════════════════════════════════════════════════════════════
#
# Le script de /admin commence par demander qui est connecté et s'arrête net si
# la réponse n'est pas « admin » : le harnais répond donc à /api/auth/me avant
# tout le reste, sinon aucun des gestes mesurés ici ne serait seulement posé.

_HARNAIS = r"""
const fs = require("fs");
const SCRIPT = fs.readFileSync(process.argv[2], "utf8");
const REP = JSON.parse(process.env.REPONSE || "{}");
const CONFIRME_REND = process.env.CONFIRME !== "false";

const appels = [];            // ce qui est réellement parti sur le réseau
let confirmations = 0;        // combien de fois window.confirm a été montré

function faireElement(id){
  const el = {
    id: id, style: {}, disabled: false, textContent: "", innerHTML: "",
    _ecoutes: {},
    addEventListener: function(t, f){ (this._ecoutes[t] = this._ecoutes[t] || []).push(f); },
    cliquer: function(){ (this._ecoutes.click || []).forEach(function(f){ f({}); }); },
    classList: { add: function(){}, remove: function(){}, contains: function(){ return false; } },
    setAttribute: function(){}, getAttribute: function(){ return null; },
    appendChild: function(){}, focus: function(){}
  };
  return el;
}

const noeuds = {};
["who","logout","diagBtn","diagOut","regPanel","regOut",
 "veilPanel","veilBtn","veilEtat","veilOut",
 "retrPanel","retrBtn","retrGo","retrEtat","retrOut"].forEach(function(id){
  noeuds[id] = faireElement(id);
});
// L'ÉTAT DE DÉPART DU BOUTON ROUGE EST LU SUR LE BALISAGE, jamais posé ici :
// s'il n'était caché que par le script, un chargement lent le montrerait.
noeuds.retrGo.style.display = process.env.RETRGO_DEPART || "";

global.document = {
  getElementById: function(id){ return noeuds[id] || null; },
  createElement: faireElement,
  addEventListener: function(){},
  body: faireElement("body")
};
global.window = { confirm: function(){ confirmations++; return CONFIRME_REND; },
                  location: { href: "" } };
global.location = global.window.location;
global.navigator = { userAgent: "node" };

global.fetch = function(url, opts){
  opts = opts || {};
  appels.push({ url: url, methode: (opts.method || "GET"), corps: opts.body || null });
  let charge = { ok: true };
  if (url === "/api/auth/me") charge = { role: "admin", email: "a@b.invalid", name: "A" };
  else if (url === "/api/admin/veille/retirer") charge = REP;
  else charge = { ok: true };
  return Promise.resolve({
    ok: true, status: 200,
    json: function(){ return Promise.resolve(charge); },
    text: function(){ return Promise.resolve(JSON.stringify(charge)); }
  });
};

eval(SCRIPT);

// Les promesses en attente doivent se résoudre AVANT chaque geste, sinon on
// mesure l'état d'avant la réponse et toute règle passerait pour rien.
const laisserTourner = () => new Promise(function(r){ setTimeout(r, 0); });

(async function(){
  const rapport = { avant: {}, apres_compte: {}, apres_go: {} };
  await laisserTourner(); await laisserTourner();

  rapport.avant = { go_display: noeuds.retrGo.style.display,
                    appels: appels.slice() };

  noeuds.retrBtn.cliquer();
  await laisserTourner(); await laisserTourner(); await laisserTourner();
  rapport.apres_compte = { go_display: noeuds.retrGo.style.display,
                           sortie: noeuds.retrOut.innerHTML,
                           etat: noeuds.retrEtat.textContent,
                           appels: appels.slice() };

  const avant_go = appels.length;
  noeuds.retrGo.cliquer();
  await laisserTourner(); await laisserTourner(); await laisserTourner();
  rapport.apres_go = { go_display: noeuds.retrGo.style.display,
                       sortie: noeuds.retrOut.innerHTML,
                       confirmations: confirmations,
                       partis: appels.slice(avant_go),
                       appels: appels.slice() };

  process.stdout.write(JSON.stringify(rapport));
})();
"""

# Une réponse REPRÉSENTATIVE : trois clés, dont la clé héritée `avis` qui pèse
# le plus, et un résidu non nul sur l'une d'elles pour que le rendu ait quelque
# chose à distinguer.
_REPONSE = {
    "ok": True,
    "retrait": {"cles": ["avis", "certfr_alerte", "certfr_avis"],
                "bulletins": 257, "simule": True},
    "motifs": {"avis": "clé héritée, plus jamais alimentée",
               "certfr_alerte": "flux retiré du catalogue",
               "certfr_avis": "flux retiré du catalogue"},
    "restant": {"avis": 200, "certfr_alerte": 31, "certfr_avis": 26},
    "sources_avant": {"avis": 200}, "sources_apres": {"avis": 200},
}


def _jouer(reponse=None, confirme=True, retrgo_depart=None):
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le script ne peut pas être exécuté")
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "h.js")
        s = os.path.join(d, "s.js")
        with io.open(h, "w", encoding="utf-8") as f:
            f.write(_HARNAIS)
        with io.open(s, "w", encoding="utf-8") as f:
            f.write(_script())
        env = dict(os.environ,
                   REPONSE=json.dumps(reponse if reponse is not None else _REPONSE),
                   CONFIRME="true" if confirme else "false")
        # L'ÉTAT DE DÉPART VIENT DU BALISAGE, pas d'un défaut choisi ici : le
        # harnais doit reproduire la page servie, sinon les règles mesurent une
        # page qui n'existe pas.
        env["RETRGO_DEPART"] = (_display_de("retrGo") if retrgo_depart is None
                                else retrgo_depart)
        p = subprocess.run([node, h, s], capture_output=True, text=True, timeout=90,
                           env=env)
    if p.returncode != 0:
        pytest.fail("le script de /admin ne tourne pas :\n%s" % (p.stderr or "")[-1500:])
    return json.loads(p.stdout)


JOUE = _jouer()


def _vers_retrait(appels):
    return [a for a in appels if a["url"] == "/api/admin/veille/retirer"]


# ═══════════════════════════════════════════════════════════════════════════
#  LE GESTE EST EN DEUX TEMPS, ET LE PREMIER NE SUPPRIME RIEN
# ═══════════════════════════════════════════════════════════════════════════


def test_le_premier_clic_COMPTE_et_n_envoie_aucune_confirmation():
    """LA SIMULATION EST LE DÉFAUT CÔTÉ ROUTE ; encore faut-il que la page ne
    la lève pas. Ce qui est mesuré est le CORPS RÉELLEMENT ENVOYÉ, pas la
    présence du mot dans le fichier : un `confirmer:true` posé par erreur au
    premier clic supprimerait 257 bulletins sans que personne ait décidé."""
    partis = _vers_retrait(JOUE["apres_compte"]["appels"])
    assert len(partis) == 1, "le comptage n'a pas appelé la route une fois et une seule"
    envoi = partis[0]
    assert envoi["methode"] == "POST"
    charge = json.loads(envoi["corps"] or "{}")
    assert charge.get("confirmer") in (None, False), (
        "le premier clic confirme la suppression : %r" % (envoi["corps"],))


def test_avant_tout_clic_RIEN_ne_part_vers_le_retrait():
    """Un appel au chargement supprimerait — ou compterait — sans demande."""
    assert _vers_retrait(JOUE["avant"]["appels"]) == []


def test_le_bouton_rouge_est_CACHE_PAR_LE_BALISAGE_et_pas_par_le_script():
    """SI LE SCRIPT ÉTAIT LE SEUL À LE CACHER, une page servie avant que le
    script tourne — ou avec le script en erreur — offrirait la suppression
    définitive au premier clic venu. La règle joue donc la page avec un bouton
    laissé VISIBLE au départ : si le script suffisait, il le cacherait."""
    bloc = PAGE[PAGE.index('id="retrGo"'):PAGE.index('id="retrGo"') + 260]
    assert "display:none" in bloc, "le bouton rouge n'est pas caché dans le balisage"
    laisse = _jouer(retrgo_depart="")
    assert laisse["avant"]["go_display"] == "", (
        "témoin : le script cache lui-même le bouton, la règle ne mesurerait "
        "plus le balisage")


def test_le_bouton_rouge_ne_PARAIT_qu_une_fois_le_compte_connu_et_non_nul():
    """Proposer « supprimer définitivement » avant de savoir combien ferait
    prendre la décision à l'aveugle."""
    assert JOUE["avant"]["go_display"] == "none"
    assert JOUE["apres_compte"]["go_display"] != "none", JOUE["apres_compte"]


def test_un_compte_a_ZERO_laisse_le_bouton_rouge_cache():
    """RIEN À RETIRER N'EST PAS UNE RAISON D'OFFRIR LE RETRAIT : un bouton
    rouge qui supprimerait zéro bulletin ferait douter du compte qu'on vient
    de lire."""
    vide = dict(_REPONSE, retrait={"cles": [], "bulletins": 0, "simule": True},
                motifs={}, restant={})
    r = _jouer(reponse=vide)
    assert r["apres_compte"]["go_display"] == "none", r["apres_compte"]


def test_le_second_clic_confirme_et_c_est_LUI_qui_supprime():
    partis = _vers_retrait(JOUE["apres_go"]["partis"])
    assert len(partis) == 1, "le bouton rouge n'a pas appelé la route"
    charge = json.loads(partis[0]["corps"] or "{}")
    assert charge.get("confirmer") is True, (
        "le second clic n'emporte pas la confirmation : %r" % (partis[0]["corps"],))


def test_un_refus_dans_la_boite_de_dialogue_N_ENVOIE_RIEN():
    """LE GARDE-FOU DOIT MORDRE. Une boîte de confirmation qu'on peut refuser
    sans que cela change quoi que ce soit ne protège de rien — et c'est un
    défaut qui ne se voit pas : la suppression aurait lieu quand même."""
    r = _jouer(confirme=False)
    assert r["apres_go"]["confirmations"] == 1, "aucune confirmation n'a été demandée"
    assert _vers_retrait(r["apres_go"]["partis"]) == [], (
        "le refus n'a pas retenu la suppression")


def test_apres_la_suppression_le_bouton_rouge_se_retire():
    """Le compte affiché vient d'être consommé ; le laisser rouge inviterait à
    re-supprimer ce qui n'est plus là."""
    assert JOUE["apres_go"]["go_display"] == "none"


# ═══════════════════════════════════════════════════════════════════════════
#  CE QUE LA PAGE MONTRE : CHAQUE CLÉ, SON MOTIF, SON RÉSIDU
# ═══════════════════════════════════════════════════════════════════════════


def test_chaque_cle_est_nommee_avec_son_motif_et_son_residu():
    """UN TOTAL SEUL NE DIT PAS LAQUELLE A ÉTÉ OUBLIÉE. C'est exactement ce qui
    s'est joué ici : la clé héritée `avis` pesait 200 bulletins sur 257, et un
    retrait qui n'aurait connu que les noms actuels en aurait laissé les trois
    quarts — sans erreur, avec un total qui aurait paru plausible."""
    sortie = JOUE["apres_compte"]["sortie"]
    for cle, motif in _REPONSE["motifs"].items():
        assert cle in sortie, "la clé %s n'est pas nommée" % cle
        assert motif[:24] in sortie, "le motif de %s n'est pas rendu" % cle
    for cle, reste in _REPONSE["restant"].items():
        assert re.search(r"reste\s*%d\b" % reste, sortie), (
            "le résidu de %s (%d) n'est pas rendu" % (cle, reste))
    assert "257" in sortie, "le total n'est pas rendu"


def _ligne_du_compte(sortie):
    """La phrase qui PORTE LE NOMBRE, et elle seule.

    LA PREMIÈRE VERSION DE CETTE RÈGLE CHERCHAIT « supprimé » DANS TOUT LE
    RENDU, et elle est tombée sur la phrase qui dit précisément que rien ne
    l'a été (« Rien n'a été supprimé »). Une règle qui échoue sur du code
    correct aurait tout aussi bien pu passer sur du code faux : c'est le verbe
    ACCOLÉ AU NOMBRE qui distingue les deux réponses, pas le vocabulaire de la
    page."""
    fin = sortie.index("</div>")
    return sortie[:fin]


def test_le_compte_DIT_qu_il_n_a_rien_supprime_et_le_retrait_qu_il_l_a_fait():
    """Les deux réponses ont la même forme ; sans un mot qui les sépare, on ne
    saurait pas laquelle on lit — et on croirait avoir supprimé."""
    compte = _ligne_du_compte(JOUE["apres_compte"]["sortie"])
    retire = _ligne_du_compte(JOUE["apres_go"]["sortie"])
    assert "partiraient" in compte and "supprim" not in compte, compte[:250]
    assert "supprimé" in retire and "partiraient" not in retire, retire[:250]
    # Et la page dit, HORS de cette ligne, que le comptage n'a rien touché.
    assert "Rien n" in JOUE["apres_compte"]["sortie"]


def test_les_cles_montrees_sont_CELLES_DU_SERVEUR_et_non_une_liste_de_page():
    """UNE SECONDE LISTE ÉCRITE DANS LA PAGE SERAIT LA COPIE QU'ON OUBLIE DE
    CORRIGER : elle divergerait de `RETIREES` en silence, et la page annoncerait
    un retrait qui ne porte pas sur ce qu'elle nomme."""
    nu = _script_nu()
    for cle in veille_sources.RETIREES:
        assert cle not in nu, (
            "la clé %s est écrite dans le script de /admin ; elle doit venir de "
            "la réponse du serveur" % cle)
    # Et le témoin : jouée avec une clé que la maison ne connaît pas, la page
    # la rend quand même — donc elle lit bien la réponse.
    etrangere = dict(_REPONSE,
                     retrait={"cles": ["flux_inconnu"], "bulletins": 4, "simule": True},
                     motifs={"flux_inconnu": "témoin de lecture"},
                     restant={"flux_inconnu": 4})
    r = _jouer(reponse=etrangere)
    assert "flux_inconnu" in r["apres_compte"]["sortie"]


def test_une_reponse_en_echec_ne_se_lit_pas_comme_un_retrait_reussi():
    """`ok:false` avec un rendu optimiste ferait croire le travail fait."""
    r = _jouer(reponse={"ok": False, "error": "retrait"})
    sortie = r["apres_compte"]["sortie"]
    assert "supprimé" not in sortie and "partiraient" not in sortie, sortie[:200]
    assert r["apres_compte"]["go_display"] == "none", (
        "un échec laisse le bouton rouge accessible")


def test_le_panneau_n_est_pas_masque_par_defaut():
    """LE MÊME DÉFAUT QUE LE BOUTON DE COLLECTE AVAIT EU : un panneau caché
    tant que rien n'est signalé laisse le bouton hors d'atteinte dans le cas
    même où il sert."""
    bloc = PAGE[PAGE.index('id="retrPanel"'):PAGE.index('id="retrPanel"') + 300]
    assert "display:none" not in bloc


def test_la_page_dit_que_le_premier_bouton_ne_supprime_pas():
    """Un bouton nommé « compter » à côté d'un bouton rouge reste ambigu tant
    que la page ne dit pas laquelle des deux actions est sans retour."""
    bloc = PAGE[PAGE.index('id="retrPanel"'):PAGE.index('id="retrPanel"') + 1400]
    texte = re.sub(r"<[^>]+>", " ", bloc)
    assert re.search(r"compte\s+sans\s+rien\s+supprimer", texte, re.I), texte[:400]


def test_une_reponse_SANS_MOTIF_ne_fait_paraitre_aucune_cle():
    """LE VERSANT NÉGATIF DE LA RÈGLE PRÉCÉDENTE, ET IL SE MESURE. La recherche
    textuelle dit qu'aucune clé n'est ÉCRITE dans le script ; celle-ci dit
    qu'aucune n'est RENDUE quand le serveur n'en nomme pas. Une page qui
    garderait sa propre liste — même construite ailleurs qu'en clair — les
    afficherait ici."""
    muette = dict(_REPONSE,
                  retrait={"cles": [], "bulletins": 257, "simule": True},
                  motifs={}, restant={})
    r = _jouer(reponse=muette)
    sortie = r["apres_compte"]["sortie"]
    for cle in veille_sources.RETIREES:
        assert cle not in sortie, (
            "la page nomme %s alors que la réponse ne la donne pas" % cle)
