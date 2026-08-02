# -*- coding: utf-8 -*-
"""Recette du moteur de relecture — contrats témoins, aucun réseau, aucune IA.

Un moteur de détection d'écarts se juge sur deux erreurs, et la deuxième est la
plus grave :

  — le FAUX NÉGATIF : une ligne rouge qui passe. Le contrat est signé, et le
    playbook a servi de caution.
  — le FAUX POSITIF : un contrat correct signalé en écart. Le juriste perd sa
    confiance dans l'outil au troisième cas, et retourne à sa relecture
    manuelle. Le cycle qu'on voulait raccourcir s'allonge.

On teste donc les deux sens, avec trois contrats témoins : un favorable qui doit
passer, un défavorable dont chaque piège doit être vu, un muet qui ne doit rien
inventer.

Lancement :  python3 tests/test_playbook.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import playbook as pb          # noqa: E402
import juridique               # noqa: E402

KO = []


def ok(nom, cond, detail=""):
    print(("  OK   " if cond else "  KO   ") + nom + ((" — " + str(detail)) if detail else ""))
    if not cond:
        KO.append(nom)


def niveau(res, tid):
    for t in res["themes"]:
        if t["id"] == tid:
            return t["niveau"]
    return "?"


def theme(res, tid):
    for t in res["themes"]:
        if t["id"] == tid:
            return t
    return {}


# ═══════════════════════════════════════════════════════════════════════════
# CONTRAT A — rédigé selon les positions standard. Doit passer.
# ═══════════════════════════════════════════════════════════════════════════

FAVORABLE = """
CONTRAT DE SERVICES DE CYBERSÉCURITÉ INDUSTRIELLE

Article 1 - Périmètre de sécurité
Le Prestataire assure les Services sur le périmètre décrit en Annexe 2, laquelle
identifie les systèmes, réseaux, zones et conduits concernés ainsi que les
interfaces avec les systèmes du Client. Toute évolution du périmètre fait l'objet
d'un avenant et d'une réévaluation des risques.

Article 2 - Mesures techniques et organisationnelles
Le Prestataire met en œuvre a minima les mesures décrites en Annexe Sécurité,
dont : cloisonnement réseau, authentification multifacteur pour tout accès
d'administration, chiffrement des données en transit et au repos, journalisation
conservée 12 mois, gestion des correctifs et sauvegardes testées. Ces mesures
constituent un plancher contractuel.

Article 3 - Notification des incidents de sécurité
Le Prestataire informe le Client de tout incident de sécurité affectant les
Services sans délai injustifié et au plus tard dans les 8 heures suivant sa
détection, par le canal d'astreinte défini en Annexe 4, avec les éléments
permettant au Client de satisfaire ses propres obligations de notification.

Article 4 - Coopération en gestion de crise
Le Prestataire participe aux cellules de crise du Client, met à disposition les
ressources techniques nécessaires à l'investigation, préserve les journaux et
éléments de preuve pendant 12 mois et s'abstient de toute action susceptible
d'altérer les traces sans accord écrit du Client.

Article 5 - Droit d'audit et d'inspection
Le Client, ses auditeurs mandatés et les autorités compétentes disposent d'un
droit d'audit et d'inspection sur pièces et sur place, deux fois par an et sans
limitation en cas d'incident, moyennant un préavis de 15 jours ouvrés.

Article 6 - Sous-traitance
Le Prestataire ne recourt à aucun sous-traitant sans autorisation écrite
préalable du Client. Il répercute l'intégralité des obligations de sécurité du
présent Contrat à ses sous-traitants et demeure responsable de leurs
manquements comme des siens.

Article 7 - Localisation des données
Les Données du Client sont hébergées et traitées exclusivement au sein de
l'Union européenne. Aucun transfert vers un pays tiers n'est autorisé.

Article 8 - Accès distant aux installations industrielles
Tout accès distant aux systèmes industriels transite par le dispositif d'accès
du Client, est nominatif, authentifié par double facteur, ouvert à la demande
pour une durée déterminée, journalisé et enregistré.

Article 9 - Correctifs de sécurité
Le Prestataire qualifie les correctifs publiés. Les vulnérabilités de criticité
haute sont corrigées dans un délai de 15 jours après qualification, ou couvertes
par une mesure compensatoire écrite.

Article 10 - Sûreté et sécurité des personnes
En cas de conflit entre une mesure de cybersécurité et la sûreté de
l'installation, l'exploitant tranche. La sûreté des personnes prime.

Article 11 - Usage d'intelligence artificielle
Le Prestataire déclare en Annexe 7 tout système d'IA utilisé dans l'exécution
des Services, sa finalité et son fournisseur. Il s'interdit d'utiliser les
Données du Client pour entraîner ou améliorer un modèle.

Article 12 - Responsabilités au titre de l'AI Act
Les rôles de fournisseur et de déployeur au sens du règlement (UE) 2024/1689
sont répartis en Annexe 7, qui précise la documentation technique et les
journaux dus par chaque partie ainsi que l'évaluation de conformité applicable.

Article 13 - Réversibilité
À l'expiration du Contrat, le Prestataire assure pendant 6 mois une assistance à
la réversibilité comprenant l'export des Données dans un format structuré et
couramment utilisé, documenté en Annexe 8.

Article 14 - Continuité et reprise
Le Prestataire garantit un RTO de 4 heures et un RPO de 1 heure. Un test du plan
de continuité est conduit chaque année et son compte rendu communiqué au Client.

Article 15 - Responsabilité
La responsabilité du Prestataire est plafonnée à 3 fois le montant des sommes
versées au titre des 12 derniers mois. Ce plafond ne s'applique pas en cas de
manquement aux obligations de sécurité et de protection des données.

Article 16 - Assurance
Le Prestataire justifie d'une police d'assurance responsabilité civile
professionnelle couvrant le risque cyber, dont l'attestation est communiquée
annuellement au Client.

Article 17 - Certifications
Le Prestataire maintient sa certification ISO/IEC 27001 pendant toute la durée
du Contrat. Le périmètre de la certification est celui des Services. Toute
suspension est notifiée au Client sous 5 jours et ouvre droit à résiliation.

Article 18 - Personnel
Le personnel du Prestataire est soumis à un engagement de confidentialité
maintenu pendant 5 ans après la fin du Contrat. Les intervenants sur les
systèmes industriels font l'objet d'une habilitation nominative.

Article 19 - Composition logicielle
Le Prestataire fournit la nomenclature logicielle (SBOM) des composants livrés,
mise à jour à chaque version majeure, et signale les composants tiers affectés
par une vulnérabilité publiée.

Article 20 - Propriété et usage des données du Client
Les Données du Client demeurent sa propriété exclusive. Le Prestataire ne les
utilise que pour l'exécution des Services, à l'exclusion de toute finalité
propre.

Article 21 - Niveaux de service de sécurité
Les indicateurs de sécurité figurent en Annexe 5. Les pénalités prévues ne
constituent pas la réparation exclusive du préjudice.

Article 22 - Changement de contrôle
En cas de changement de contrôle du Prestataire, celui-ci en informe le Client
sans délai. Le Client dispose d'une faculté de résiliation pendant 3 mois.
"""


# ═══════════════════════════════════════════════════════════════════════════
# CONTRAT B — chaque piège du playbook, une fois. Rien ne doit passer.
# ═══════════════════════════════════════════════════════════════════════════

DEFAVORABLE = """
CONDITIONS GÉNÉRALES DE SERVICES

Article 1 - Périmètre
Le périmètre des prestations couvertes est défini par la documentation du
prestataire en vigueur, susceptible d'évoluer à tout moment.

Article 2 - Mesures de sécurité
Le Prestataire met en œuvre les mesures de sécurité conformes à l'état de l'art.

Article 3 - Incident de sécurité
Le Prestataire informe le Client de tout incident de sécurité au plus tard dans
les 72 heures suivant la qualification de l'incident par le prestataire.

Article 4 - Coopération
Toute assistance en gestion de crise est facturée au tarif en vigueur.

Article 5 - Audit
Le droit d'audit du Client se limite à la remise du rapport de certification
annuel du Prestataire.

Article 6 - Sous-traitance
Le Prestataire peut librement sous-traiter tout ou partie des prestations.

Article 7 - Hébergement
Les données sont hébergées aux États-Unis. Le prestataire se réserve le droit de
modifier la localisation des traitements.

Article 8 - Accès distant
Le Prestataire dispose d'un accès distant permanent aux systèmes du Client pour
les besoins de la télémaintenance.

Article 9 - Correctifs
Les correctifs de sécurité sont appliqués selon le calendrier que le prestataire
juge approprié.

Article 11 - Intelligence artificielle
Les contenus et données traités peuvent être utilisés pour l'entraînement et
l'amélioration des modèles d'intelligence artificielle du Prestataire.

Article 13 - Réversibilité
La restitution des données intervient sur devis, au tarif en vigueur du
prestataire, dans un format propriétaire.

Article 14 - Continuité
Le Prestataire est exonéré de toute responsabilité au titre de la force majeure,
laquelle inclut expressément toute attaque informatique ou rançongiciel.

Article 15 - Responsabilité
Le Prestataire décline toute responsabilité au titre d'une violation de données
personnelles. Sa responsabilité est en tout état de cause plafonnée à 0.25 fois
les sommes versées sur les douze derniers mois.

Article 19 - Composants
Le Prestataire refuse de communiquer la composition logicielle de ses produits,
couverte par le secret des affaires.

Article 20 - Données
Le Prestataire peut utiliser les données du Client pour ses propres besoins et
l'amélioration de ses produits.

Article 21 - Pénalités
Les pénalités prévues à l'Annexe tarifaire constituent la seule réparation de
tout manquement du Prestataire, y compris en matière de sécurité.

Article 22 - Cession
Le Prestataire peut librement céder le présent contrat à toute entité de son
choix.
"""


# ═══════════════════════════════════════════════════════════════════════════
# CONTRAT C — un contrat de prestation banal, muet sur la sécurité.
# ═══════════════════════════════════════════════════════════════════════════

MUET = """
CONTRAT DE PRESTATION DE SERVICES

Article 1 - Objet
Le Prestataire réalise pour le Client les prestations d'ingénierie décrites en
Annexe 1.

Article 2 - Durée
Le présent contrat est conclu pour une durée de trois ans à compter de sa
signature.

Article 3 - Prix et facturation
Le prix des prestations est fixé à 480 000 euros hors taxes. La facturation
intervient mensuellement, à 30 jours fin de mois.

Article 4 - Propriété intellectuelle
Les livrables réalisés dans le cadre du présent contrat deviennent la propriété
du Client à compter de leur paiement intégral.

Article 5 - Droit applicable
Le présent contrat est soumis au droit français. Tout litige relève de la
compétence exclusive du tribunal de commerce de Paris.
"""


print("═══ 1. Le playbook se tient debout ═══")
s = pb.sante()
ok("le playbook couvre tout le clausier", s["ok"] and not s["sans_regle"], s["detail"])
ok("aucun motif cassé", not s["motifs_casses"], "%d motifs" % s["motifs"])
ok("chaque validateur existe dans le référentiel des instances",
   not s["instances_inconnues"], s["instances_inconnues"] or "11 instances")
th = pb.themes()
ok("chaque thème porte une position standard", all(t["position"] for t in th))
ok("chaque thème porte une ligne rouge", all(t["ligne_rouge"] for t in th),
   "%d thèmes" % len(th))
ok("chaque thème nomme qui valide un écart",
   all(t["valide"].get("ecart") for t in th))

print()
print("═══ 2. Le découpage retrouve les articles ═══")
segs = pb.decouper(FAVORABLE)
ok("les 22 articles sont retrouvés", len(segs) >= 22, "%d segments" % len(segs))
ok("les numéros d'article sont lus", [x["ref"] for x in segs].count("15") == 1,
   "refs : " + ", ".join(x["ref"] for x in segs[:8]))
ok("un texte sans numérotation retombe sur les paragraphes",
   len(pb.decouper("Blabla.\n\n" + "Ceci est un paragraphe de contrat. " * 30
                   + "\n\n" + "Et un second paragraphe tout aussi long. " * 30)) >= 2)

print()
print("═══ 3. Contrat FAVORABLE — il doit passer ═══")
A = pb.analyser(FAVORABLE)
print("        " + A["synthese"])
ok("aucune ligne rouge", A["compte"]["ligne-rouge"] == 0,
   [t["titre"] for t in A["themes"] if t["niveau"] == "ligne-rouge"])
ok("aucun sujet non traité", A["compte"]["absent"] == 0,
   [t["titre"] for t in A["themes"] if t["niveau"] == "absent"])
faux_positifs = [(t["id"], (t["constats"] or [{}])[0].get("pourquoi", "")[:60])
                 for t in A["themes"] if t["niveau"] == "ecart"]
ok("au plus deux écarts sur un contrat aux positions standard",
   len(faux_positifs) <= 2, faux_positifs)
ok("le délai de notification de 8 h est reconnu conforme",
   niveau(A, "notification-incident") == "conforme",
   (theme(A, "notification-incident").get("seuil") or {}).get("trouve"))
ok("le plafond de 3 fois est reconnu conforme",
   niveau(A, "responsabilite") == "conforme",
   (theme(A, "responsabilite").get("seuil") or {}).get("trouve"))
ok("la réversibilité de 6 mois est reconnue conforme",
   niveau(A, "reversibilite") == "conforme",
   (theme(A, "reversibilite").get("seuil") or {}).get("trouve"))
ok("« état de l'art » n'est PAS déclenché quand une annexe existe",
   niveau(A, "mesures-techniques") in ("conforme", "repli"),
   niveau(A, "mesures-techniques"))

print()
print("═══ 4. Contrat DÉFAVORABLE — chaque piège doit être vu ═══")
B = pb.analyser(DEFAVORABLE)
print("        " + B["synthese"])
ATTENDU_ROUGE = [
    ("perimetre-securite", "périmètre défini par la documentation du prestataire"),
    ("mesures-techniques", "« état de l'art » sans annexe"),
    ("notification-incident", "délai courant après qualification par le prestataire"),
    ("audit", "audit limité au rapport de certification"),
    ("sous-traitance", "sous-traitance libre"),
    ("localisation", "localisation modifiable unilatéralement"),
    ("acces-distant", "accès distant permanent"),
    ("ia-fournisseur", "entraînement sur les données du client"),
    ("reversibilite", "restitution sur devis, format propriétaire"),
    ("continuite", "cyberattaque qualifiée de force majeure"),
    ("responsabilite", "responsabilité exclue en cas de violation de données"),
    ("sbom", "refus de communiquer la composition logicielle"),
    ("donnees-usage", "usage des données à des fins propres"),
    ("sla-securite", "pénalités seule réparation"),
    ("changement-controle", "cession libre du contrat"),
]
for tid, quoi in ATTENDU_ROUGE:
    ok("ligne rouge vue : %s" % quoi, niveau(B, tid) == "ligne-rouge",
       "%s → %s" % (tid, niveau(B, tid)))
ok("le délai de 72 h est refusé", (theme(B, "notification-incident").get("seuil") or {}).get("trouve") == 72.0,
   (theme(B, "notification-incident").get("seuil") or {}).get("trouve"))
ok("le plafond de 0,25 fois est refusé",
   (theme(B, "responsabilite").get("seuil") or {}).get("niveau") in ("ligne-rouge", "ecart"),
   (theme(B, "responsabilite").get("seuil") or {}).get("trouve"))
ok("les correctifs « quand le prestataire juge » sont un écart",
   niveau(B, "correctifs-ot") in ("ecart", "ligne-rouge"), niveau(B, "correctifs-ot"))
ok("la coopération facturée est un écart",
   niveau(B, "cooperation-crise") in ("ecart", "ligne-rouge"), niveau(B, "cooperation-crise"))
ok("le contrat est déclaré non signable en l'état",
   "ne peut pas être signée" in B["synthese"], B["synthese"][:70])
ok("chaque constat cite le contrat",
   all(c["citation"].strip() for t in B["themes"] for c in t["constats"]),
   "%d constats" % sum(len(t["constats"]) for t in B["themes"]))

print()
print("═══ 5. Contrat MUET — ne rien inventer ═══")
C = pb.analyser(MUET)
print("        " + C["synthese"])
ok("aucun thème déclaré conforme sur un contrat qui n'en parle pas",
   C["compte"]["conforme"] == 0,
   [t["titre"] for t in C["themes"] if t["niveau"] == "conforme"])
ok("aucune ligne rouge inventée", C["compte"]["ligne-rouge"] == 0,
   [t["titre"] for t in C["themes"] if t["niveau"] == "ligne-rouge"])
ok("la quasi-totalité des thèmes ressort « non traité »",
   C["compte"]["absent"] >= 19, "%d absents sur %d" % (C["compte"]["absent"], len(C["themes"])))
ok("« 30 jours fin de mois » n'est pas lu comme un délai de notification",
   niveau(C, "notification-incident") == "absent",
   (theme(C, "notification-incident").get("seuil") or {}).get("trouve"))
ok("« trois ans » n'est pas lu comme une durée de réversibilité",
   niveau(C, "reversibilite") == "absent",
   (theme(C, "reversibilite").get("seuil") or {}).get("trouve"))

print()
print("═══ 6. Le verdict est reproductible ═══")
B2 = pb.analyser(DEFAVORABLE)
ok("deux passages donnent exactement le même verdict",
   [t["niveau"] for t in B["themes"]] == [t["niveau"] for t in B2["themes"]])
ok("et le même compte", B["compte"] == B2["compte"], B["compte"])

print()
print("═══ 7. Comparaison de deux versions ═══")
cmp1 = pb.comparer(DEFAVORABLE, FAVORABLE)
ok("de la version défavorable à la favorable : que des progrès",
   cmp1["n_progres"] > 10 and cmp1["n_recul"] == 0,
   "%d progrès · %d reculs" % (cmp1["n_progres"], cmp1["n_recul"]))
cmp2 = pb.comparer(FAVORABLE, DEFAVORABLE)
ok("dans l'autre sens : que des reculs",
   cmp2["n_recul"] > 10 and cmp2["n_progres"] == 0,
   "%d reculs · %d progrès" % (cmp2["n_recul"], cmp2["n_progres"]))
ok("les passages en ligne rouge sont signalés dans la synthèse",
   "ligne rouge" in cmp2["synthese"], cmp2["synthese"][:90])
cmp3 = pb.comparer(FAVORABLE, FAVORABLE)
ok("un texte identique ne bouge pas",
   cmp3["n_recul"] == 0 and cmp3["n_progres"] == 0, cmp3["synthese"][:70])

# Le cas réel de la négociation : une seule clause change.
V2 = FAVORABLE.replace("au plus tard dans les 8 heures",
                       "au plus tard dans les 36 heures")
cmp4 = pb.comparer(FAVORABLE, V2)
recul = [m for m in cmp4["mouvements"] if m["sens"] == "recul"]
ok("un seul mot changé dans une version : un seul recul détecté",
   len(recul) == 1 and recul[0]["id"] == "notification-incident",
   [(m["id"], m["avant"], m["apres"]) for m in recul])
ok("le chiffre d'avant et d'après sont donnés",
   recul and recul[0]["seuil_avant"] == 8.0 and recul[0]["seuil_apres"] == 36.0,
   recul and "%s → %s" % (recul[0]["seuil_avant"], recul[0]["seuil_apres"]))

print()
print("═══ 8. Circuit de validation ═══")
ci = pb.circuit(B)
ok("le circuit nomme des instances réelles",
   all(v["instance"] in juridique.INSTANCES for v in ci["validations"]),
   "%d instances · %d points" % (ci["n_instances"], ci["n_points"]))
ok("il regroupe : moins d'instances que de points à valider",
   ci["n_instances"] < ci["n_points"],
   "%d instances pour %d points" % (ci["n_instances"], ci["n_points"]))
ok("les instances bloquantes viennent en tête",
   ci["validations"] and ci["validations"][0]["bloquant"],
   ci["validations"][0]["libelle"] if ci["validations"] else "")
ok("chaque point porte son motif",
   all(p["motif"] for v in ci["validations"] for p in v["points"]))
ok("aucun thème conforme n'entre dans le circuit",
   all(p["niveau"] != "conforme" for v in ci["validations"] for p in v["points"]))
ci_a = pb.circuit(A)
ok("un contrat conforme ne convoque presque personne",
   ci_a["n_points"] <= 2, "%d point(s)" % ci_a["n_points"])

print()
print("═══ 9. Le contexte remis au modèle ═══")
ctx = pb.contexte_chat(B, focus="notification-incident")
ok("le contexte porte les verdicts", "ANALYSE DÉTERMINISTE" in ctx)
ok("le thème visé est développé", "THÈME SUR LEQUEL PORTE LA QUESTION" in ctx
   and "position standard" in ctx)
ok("il nomme l'instance qui valide", "validation requise" in ctx)
ok("il donne le chiffre du contrat et celui de la politique",
   "le contrat dit 72" in ctx and "au plus 8" in ctx,
   [l for l in ctx.split("\n") if "le contrat dit" in l][:1])
ok("il tient dans le budget", len(ctx) <= 14000, "%d caractères" % len(ctx))
ok("le prompt système interdit de rejuger les verdicts",
   "ne réévalues jamais ces niveaux" in pb.SYSTEM_RELECTURE)

print()
print("═══ 10. La note de relecture ═══")
note = pb.note_markdown(B, objet="Contrat cadre XYZ — version 3", circuit_=ci,
                        comparaison=cmp2,
                        echange=[{"role": "user", "content": "Que bloque la signature ?"},
                                 {"role": "assistant", "content": "Quinze lignes rouges."}])
ok("la note porte un titre et l'objet", note.startswith("# Note de relecture")
   and "Contrat cadre XYZ" in note)
ok("elle donne la version du playbook et du référentiel",
   pb.VERSION_PLAYBOOK in note and juridique.VERSION_REFERENTIEL in note)
ok("elle cite le contrat", note.count("\n  > ") >= 8 or note.count("\n> ") >= 8,
   "%d citations" % (note.count("  > ") + note.count("\n> ")))
ok("elle porte le circuit de validation", "## Circuit de validation" in note)
ok("elle porte l'avertissement et la mention IA",
   juridique.AVERTISSEMENT[:40] in note and juridique.MENTION_IA[:40] in note)
ok("elle reprend l'échange avec l'assistant", "Que bloque la signature" in note)
ok("elle a une taille exploitable", 4000 < len(note) < 90000, "%d caractères" % len(note))

print()
print("═══ 11. Options d'analyse ═══")
D = pb.analyser(DEFAVORABLE, domaines_retenus=["Responsabilité"])
ok("filtrer par domaine restreint l'analyse",
   0 < len(D["themes"]) < 5 and all(t["domaine"] == "Responsabilité" for t in D["themes"]),
   "%d thèmes" % len(D["themes"]))
E = pb.analyser(DEFAVORABLE, ids=["audit"])
ok("analyser un seul thème est possible",
   len(E["themes"]) == 1 and E["themes"][0]["id"] == "audit")
F = pb.analyser("")
ok("un texte vide ne casse rien et ne conclut rien",
   F["compte"]["conforme"] == 0 and F["compte"]["ligne-rouge"] == 0,
   F["synthese"][:60])

print()
if KO:
    print("ECHECS : %d" % len(KO))
    for k in KO:
        print("   · " + k)
    sys.exit(1)
print("RECETTE COMPLETE — aucun echec")
