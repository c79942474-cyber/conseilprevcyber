# -*- coding: utf-8 -*-
"""CE DÉPÔT ANNONÇAIT ENCORE L'ANNEXE III AU 2 AOÛT 2026.

CE QUI A DÉCLENCHÉ CE FICHIER. `juridique.py` est décrit dans les deux
applications comme « partagé à l'identique ». Il ne l'était plus. Le Digital
Omnibus a reporté l'entrée en application des systèmes à haut risque de
l'annexe III au 2 décembre 2027, et celle de l'art. 6(1) au 2 août 2028 ; la
copie de conseilprevia a suivi, celle-ci non. Elle annonçait donc à des clients
une échéance dépassée de seize mois, et une autre avancée d'un an.

POURQUOI LA DÉRIVE N'A RIEN CASSÉ. Parce qu'aucune règle ne regardait ces dates
ici. Mille sept cent trente-huit contrôles passaient au vert sur un calendrier
faux : une date est une donnée, et une donnée que personne ne vérifie ne se
signale jamais d'elle-même.

CE QUE CES RÈGLES GARDENT. Que le référentiel porte les dates du Digital
Omnibus ; qu'aucun fichier du dépôt ne rattache une date périmée au régime de
l'annexe III ; et que l'art. 50, lui, RESTE au 2 août 2026 — il n'a pas été
reporté, et l'aligner par mégarde sur ses voisins serait l'erreur symétrique.
"""
import io
import os
import re

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import sys  # noqa: E402
sys.path.insert(0, ICI)
import juridique  # noqa: E402

ANNEXE_III = '2 décembre 2027'
ANNEXE_I = '2 août 2028'
ARTICLE_50 = '2 août 2026'

FICHIERS = [f for f in os.listdir(ICI)
            if f.endswith(('.py', '.js', '.html')) and not f.startswith('.')]


def _ia_act():
    t = juridique.texte('ai-act')
    assert t, "le texte « ai-act » a disparu du référentiel"
    return t


# ── LE RÉFÉRENTIEL PORTE LES BONNES DATES ────────────────────────────────

@pytest.mark.parametrize('date,quoi', [
    (ANNEXE_III, "les systèmes à haut risque de l'annexe III"),
    (ANNEXE_I, "les systèmes à haut risque relevant de l'art. 6(1)"),
])
def test_les_jalons_portent_les_dates_du_digital_omnibus(date, quoi):
    jalons = ' | '.join(_ia_act().get('jalons', []))
    assert date in jalons, (
        "le référentiel n'annonce pas %s pour %s — jalons actuels : %s"
        % (date, quoi, jalons))


@pytest.mark.parametrize('perimee', ['2 août 2027', '2 décembre 2026'])
def test_aucun_jalon_ne_porte_plus_une_date_perimee(perimee):
    jalons = ' | '.join(_ia_act().get('jalons', []))
    assert perimee not in jalons, (
        "le référentiel annonce encore « %s » : %s" % (perimee, jalons))


def test_l_article_50_n_a_pas_ete_reporte():
    """L'ERREUR SYMÉTRIQUE, ET ELLE EST FACILE À COMMETTRE. En corrigeant les
    dates voisines, on aligne l'art. 50 sur elles. Or la transparence s'applique
    depuis le 2 août 2026 : la reporter dirait à un client qu'il a encore un an
    devant lui alors qu'il est en retard."""
    jalons = ' | '.join(_ia_act().get('jalons', []))
    assert ARTICLE_50 in jalons, (
        "le 2 août 2026 a disparu des jalons : l'art. 50 a-t-il été reporté "
        "par contagion ? — %s" % jalons)


def test_la_qualification_renvoie_la_bonne_echeance_pour_l_annexe_I():
    """La date n'est pas seulement affichée : elle est écrite dans le motif que
    la qualification rend à un client dont le produit relève de l'art. 6(1)."""
    plat = io.open(os.path.join(ICI, 'juridique.py'), encoding='utf-8').read()
    assert "applicable au %s" % ANNEXE_I in plat, (
        "le motif de qualification n'annonce pas le %s pour l'art. 6(1)" % ANNEXE_I)


# ── AUCUN FICHIER N'ANNONCE UNE DATE PÉRIMÉE POUR L'ANNEXE III ───────────
#
# La logique ci-dessous vient de la règle jumelle écrite dans conseilprevia, et
# elle y a coûté trois versions. On la reprend telle quelle plutôt que de la
# réinventer, parce que chacune de ces trois versions a été fausse d'une manière
# différente :
#
#   — ±90 caractères de part et d'autre : accusait quatre phrases JUSTES, celles
#     qui OPPOSENT les deux régimes (« transparence depuis le 2 août 2026 ; haut
#     risque annexe III au 2 décembre 2027 »). Interdire de nommer les deux
#     calendriers dans une phrase, c'est interdire d'être clair.
#   — qualifiant le plus proche, sans borne : l'entrée VOISINE d'une liste se
#     terminait par « (transparence) » plus près de la date que l'« annexe III »
#     de sa propre phrase. Une fenêtre de caractères ignore les frontières du
#     texte ; une liste de chaînes en a.
#   — retrait des balises `<[^>]*>` sur tous les fichiers : appliqué à un `.js`,
#     il ne retire pas des balises, il dévore tout ce qui sépare un `<` et un `>`
#     de COMPARAISON. La règle travaillait sur un fichier mutilé.

QUALIFIANT = re.compile(r'annexe\s*III|art\.?\s*6\(1\)|Art\.?\s*6\(2\)', re.I)
TRANSPARENCE = re.compile(r'art\.?\s*50|article\s*50|transparence', re.I)
DATE = re.compile(r'2\s*ao[uû]t\s*2026|2\s*ao[uû]t\s*2027|2026-08-02|2027-08-02')


def _qualifiant_le_plus_proche(unite, pos):
    proches = []
    for rx, etiquette in ((QUALIFIANT, 'annexe III'), (TRANSPARENCE, 'transparence')):
        for m in rx.finditer(unite):
            proches.append((min(abs(m.start() - pos), abs(m.end() - pos)), etiquette))
    if not proches:
        return None
    return min(proches)[1]


def test_aucun_fichier_n_annonce_une_date_perimee_pour_l_annexe_III():
    """LA RÈGLE QUI AURAIT ÉVITÉ LA DÉRIVE. Elle regarde le dépôt entier, pas
    seulement le module partagé : une date recopiée dans une page se périme
    exactement de la même façon, et plus discrètement."""
    fautes = []
    for nom in sorted(FICHIERS):
        brut = io.open(os.path.join(ICI, nom), encoding='utf-8', errors='replace').read()
        s = re.sub(r'<[^>]*>', '', brut) if nom.endswith('.html') else brut
        for m in DATE.finditer(s):
            g = max((s.rfind(x, max(0, m.start() - 400), m.start())
                     for x in ('"', '\n', ';')), default=-1)
            pt = s.rfind('. ', max(0, m.start() - 400), m.start())
            g = max(g, pt + 1 if pt >= 0 else -1)
            fin = min((p for p in (s.find(x, m.end(), m.end() + 400)
                                   for x in ('"', '\n', ';', '. ')) if p >= 0),
                      default=len(s))
            unite = s[g + 1:fin]
            if _qualifiant_le_plus_proche(unite, m.start() - (g + 1)) != 'annexe III':
                continue
            plat = re.sub(r'\s+', ' ', unite)
            # Le commentaire qui RACONTE l'ancienne date pour expliquer la
            # correction n'est pas une affirmation de calendrier.
            if 'annonçait encore' in plat:
                continue
            fautes.append('%s : « %s »' % (nom, plat.strip()[:140]))
    assert not fautes, (
        "date périmée rattachée au régime de l'annexe III :\n  - %s"
        % '\n  - '.join(fautes))


# L'ANGLE MORT DE LA RÈGLE PRÉCÉDENTE, ET COMMENT ON LE FERME.
#
# La règle ci-dessus retient le qualifiant le PLUS PROCHE de la date, pour
# autoriser les phrases qui OPPOSENT les deux régimes. Confrontée à la
# régression réelle — « 2 août 2026 — application générale, dont l'art. 50
# (transparence) et les systèmes à haut risque de l'annexe III » — elle se tait :
# « transparence » est plus près de la date que « annexe III ».
#
# Or c'est exactement l'énoncé fautif. La différence entre opposer et confondre
# ne se lit pas dans la distance, elle se lit dans le NOMBRE DE DATES : opposer
# deux régimes demande deux dates, les confondre consiste à n'en donner qu'une.
# C'est une propriété, pas une heuristique.

TOUTE_DATE = re.compile(
    r'2\s*ao[uû]t\s*202[5-9]|2\s*d[ée]cembre\s*202[5-9]'
    r'|202[5-9]-08-02|202[5-9]-12-02')


def _confond(enonce):
    """Vrai si l'énoncé donne UNE SEULE date aux deux régimes."""
    dates = TOUTE_DATE.findall(enonce)
    if not dates:
        return False
    if not (QUALIFIANT.search(enonce) and TRANSPARENCE.search(enonce)):
        return False
    return len(set(re.sub(r'\s+', ' ', d) for d in dates)) < 2


def test_aucun_jalon_ne_donne_une_seule_date_aux_deux_regimes():
    """LA RÈGLE QUI ATTRAPE LA RÉGRESSION RÉELLE, ET ELLE PORTE SUR LA VALEUR.

    La version qui lisait le FICHIER se taisait : dans le source, le jalon
    fautif est écrit en deux chaînes accolées — « … (transparence) » puis « et
    les systèmes à haut risque de l'annexe III » — et découper sur le guillemet
    les sépare. Le lecteur, lui, voit la phrase entière. On contrôle donc ce que
    le module REND, pas la façon dont il est écrit.

    Le défaut gardé : un jalon unique pour la transparence et le haut risque
    annexe III annonce qu'ils s'appliquent le même jour. Seize mois les
    séparent."""
    fautifs = [j for j in _ia_act().get('jalons', []) if _confond(j)]
    assert not fautifs, (
        "jalon(s) donnant une seule date à la transparence et au haut risque de "
        "l'annexe III :\n  - %s" % '\n  - '.join(fautifs))


def test_un_enonce_qui_nomme_les_deux_regimes_porte_deux_dates():
    """La même propriété, cette fois sur les pages : une date recopiée dans un
    gabarit se périme comme les autres, et plus discrètement."""
    fautes = []
    for nom in sorted(FICHIERS):
        brut = io.open(os.path.join(ICI, nom), encoding='utf-8', errors='replace').read()
        s = re.sub(r'<[^>]*>', '', brut) if nom.endswith('.html') else brut
        for unite in re.split(r'[\n;]|\. ', s):
            if len(unite) > 400 or not _confond(unite):
                continue
            plat = re.sub(r'\s+', ' ', unite).strip()
            if 'annonçait encore' in plat:
                continue
            fautes.append('%s : « %s »' % (nom, plat[:160]))
    assert not fautes, (
        "énoncé donnant UNE SEULE date à la transparence et au haut risque de "
        "l'annexe III — seize mois les séparent :\n  - %s" % '\n  - '.join(fautes))
