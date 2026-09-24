#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le banc de mutations : chaque défaut injecté doit faire tomber UNE règle
NOMMÉE.

POURQUOI IL EST DANS LE DÉPÔT. Les tables `tests/mutations_*.json` y étaient,
le script qui les rejoue n'y était pas : personne d'autre que leur auteur ne
pouvait vérifier qu'une règle tombe bien sur SON défaut — « une règle qui
passe pour une raison sans rapport avec ce qu'elle prétend » est précisément
ce que ce banc débusque.

CE QU'IL FAIT, POUR CHAQUE MUTATION D'UNE TABLE :
  1. remplace, dans `fichier`, le texte `avant` (présent UNE fois) par
     `apres` ;
  2. lance les `cibles` de la table ;
  3. dit « tombe ✓ » si la règle `regle` est parmi celles qui échouent,
     « SURVIT » si aucune n'échoue, « MAL VISÉE » si d'autres échouent mais
     pas elle ;
  4. remet le fichier dans son état, QUOI QU'IL ARRIVE.

CE QUI A ÉTÉ MESURÉ, ET QU'IL REFUSE DÉSORMAIS :
  · un banc interrompu a laissé `dora_supervision.py` muté sur le disque —
    la restauration est maintenant faite aussi sur SIGINT et SIGTERM ;
  · un fichier modifié à la main PENDANT la batterie aurait été écrasé par
    la restauration — celle-ci n'écrit plus que si le fichier est encore
    exactement celui qu'elle a muté, et sinon défait la seule mutation ;
  · une ancre devenue ambiguë (présente deux fois) rendait une mutation
    inexécutable sans que rien ne tombe — la table est vérifiée AVANT de
    jouer, et `tests/test_banc_mutations.py` fait la même vérification à
    chaque passage de la suite.

Usage :
    python outils/muter.py tests/mutations_taux_rail.json [autres tables…]
    python outils/muter.py --toutes

Le code de sortie vaut 0 si toutes les mutations tombent sur leur règle,
1 sinon (survivante, mal visée, table fautive, base rouge).
"""
import io
import json
import os
import re
import signal
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: LA MUTATION EN COURS : (chemin, texte d'origine, texte muté). Lue par la
#: restauration de secours, si le banc est interrompu.
_EN_COURS = [None]


def _lire(chemin):
    with io.open(chemin, encoding="utf-8") as f:
        return f.read()


def _ecrire(chemin, texte):
    with io.open(chemin, "w", encoding="utf-8") as f:
        f.write(texte)


def charger(table):
    return json.loads(_lire(table))


def _nom_de_base(regle):
    """`test_x[param]` → `test_x` : la fonction qui porte la règle."""
    return regle.split("[", 1)[0]


def verifier(table, racine=RACINE):
    """Les fautes d'une table, AVANT de jouer quoi que ce soit.

    Une ancre absente ou double, une règle qui n'existe dans aucune cible :
    chacune rendrait une mutation muette — elle « survivrait », ou serait
    ignorée, sans rien dire de la règle qu'elle devait éprouver."""
    fautes = []
    t = charger(table) if isinstance(table, str) else table
    cibles = t.get("cibles") or []
    if not cibles:
        fautes.append("aucune cible")
    sources = []
    for c in cibles:
        p = os.path.join(racine, c)
        if not os.path.exists(p):
            fautes.append("cible absente : %s" % c)
        else:
            sources.append(_lire(p))
    for i, m in enumerate(t.get("mutations") or [], 1):
        for champ in ("nom", "fichier", "avant", "apres", "regle"):
            if champ not in m:
                fautes.append("M%d : champ « %s » absent" % (i, champ))
        if any(champ not in m for champ in ("fichier", "avant", "apres", "regle")):
            continue
        if m["avant"] == m["apres"]:
            fautes.append("M%d (%s) : « avant » et « après » sont identiques"
                          % (i, m.get("nom")))
        p = os.path.join(racine, m["fichier"])
        if not os.path.exists(p):
            fautes.append("M%d (%s) : fichier absent %s"
                          % (i, m.get("nom"), m["fichier"]))
        else:
            n = _lire(p).count(m["avant"])
            if n != 1:
                fautes.append("M%d (%s) : ancre présente %d fois dans %s"
                              % (i, m.get("nom"), n, m["fichier"]))
        base = _nom_de_base(m["regle"])
        motif = re.compile(r"(?m)^def %s\(" % re.escape(base))
        if not any(motif.search(s) for s in sources):
            fautes.append("M%d (%s) : la règle %s n'est définie dans aucune "
                          "cible" % (i, m.get("nom"), base))
    return fautes


def lancer(cibles, racine=RACINE):
    """Les cibles, et la sortie de pytest."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header",
         "-p", "no:cacheprovider"] + list(cibles),
        cwd=racine, capture_output=True, text=True, timeout=1800,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    return out.stdout + out.stderr


def tombees(sortie):
    """Les règles tombées. Une ERREUR de collecte compte aussi : elle dit
    que le module ne se charge plus, et c'est une chute, pas une survie.

    LES LIGNES DU JOURNAL NE SONT PAS DES CHUTES. Une règle qui tombe affiche
    le journal capturé pendant son exécution, dont les lignes commencent
    aussi par « ERROR » — mais suivi de l'alignement du niveau, puis du nom
    du journal : « ERROR    conseilprev:app.py:76 … ». Mesuré : les cinq
    avertissements du démarrage de l'application étaient comptés comme cinq
    règles tombées de plus. Le résumé, lui, met UNE espace après le mot,
    puis le fichier de règles."""
    noms = set()
    for l in sortie.splitlines():
        for prefixe in ("FAILED ", "ERROR "):
            if not l.startswith(prefixe):
                continue
            reste = l[len(prefixe):]
            if reste[:1] in ("", " "):
                continue
            lieu = reste.split(" - ")[0]
            noms.add(lieu.split("::")[-1].split()[0])
    return sorted(noms)


def restaurer():
    """Remet le fichier muté dans son état d'origine — sans jamais écraser
    ce qu'on y aurait écrit pendant la batterie."""
    en_cours = _EN_COURS[0]
    if not en_cours:
        return
    chemin, origine, mute, avant, apres = en_cours
    _EN_COURS[0] = None
    actuel = _lire(chemin)
    if actuel == mute:
        _ecrire(chemin, origine)
    elif apres and actuel.count(apres) == 1:
        # LE FICHIER A CHANGÉ PENDANT LA BATTERIE : on ne défait que la
        # mutation, et on laisse le reste tel qu'on l'a trouvé.
        _ecrire(chemin, actuel.replace(apres, avant, 1))
        sys.stderr.write("⚠ %s modifié pendant la batterie : seule la "
                         "mutation a été défaite.\n" % chemin)
    elif actuel != origine:
        sys.stderr.write("⚠ %s modifié pendant la batterie et la mutation "
                         "n'y est plus reconnaissable : RIEN n'est réécrit, "
                         "vérifiez le fichier.\n" % chemin)


def _sur_signal(num, _cadre):
    restaurer()
    sys.stderr.write("\nbanc interrompu (signal %d) : fichier restauré.\n" % num)
    sys.exit(130)


def jouer(table, racine=RACINE, lanceur=None, sortie=print):
    """Joue une table. Rend (survivantes, mal_visees, fautes)."""
    lanceur = lanceur or (lambda cibles: lancer(cibles, racine))
    t = charger(table) if isinstance(table, str) else table
    fautes = verifier(t, racine)
    if fautes:
        for f in fautes:
            sortie("TABLE FAUTIVE  " + f)
        return 0, 0, fautes
    base = lanceur(t["cibles"])
    resume = [l for l in base.splitlines() if " passed" in l or " failed" in l]
    sortie("base : %s" % (resume[-1] if resume else "?"))
    if tombees(base) or not resume or " failed" in resume[-1]:
        sortie("BASE NON VERTE — rien n'est joué.")
        return 0, 0, ["base non verte"]
    survit = mal = 0
    for i, m in enumerate(t["mutations"], 1):
        chemin = os.path.join(racine, m["fichier"])
        origine = _lire(chemin)
        mute = origine.replace(m["avant"], m["apres"], 1)
        _EN_COURS[0] = (chemin, origine, mute, m["avant"], m["apres"])
        _ecrire(chemin, mute)
        try:
            chute = tombees(lanceur(t["cibles"]))
        finally:
            restaurer()
        if not chute:
            survit += 1
            sortie("M%-3d SURVIT      %s" % (i, m["nom"]))
        elif m["regle"] in chute:
            sup = len(chute) - 1
            sortie("M%-3d tombe  ✓    %s   → %s%s" % (
                i, m["nom"], m["regle"], "  (+%d)" % sup if sup else ""))
        else:
            mal += 1
            sortie("M%-3d MAL VISÉE   %s\n      attendue : %s\n      tombées  : %s"
                   % (i, m["nom"], m["regle"], chute))
    sortie("%d mutations · %d survivantes · %d mal visées"
           % (len(t["mutations"]), survit, mal))
    return survit, mal, []


def main(argv):
    tables = argv[1:]
    if tables == ["--toutes"]:
        dossier = os.path.join(RACINE, "tests")
        tables = sorted(os.path.join("tests", f) for f in os.listdir(dossier)
                        if f.startswith("mutations_") and f.endswith(".json"))
    if not tables:
        print(__doc__)
        return 2
    signal.signal(signal.SIGINT, _sur_signal)
    signal.signal(signal.SIGTERM, _sur_signal)
    echec = False
    for table in tables:
        print("══ %s" % table)
        s, m, f = jouer(os.path.join(RACINE, table) if not os.path.isabs(table)
                        else table)
        echec = echec or bool(s or m or f)
    return 1 if echec else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
