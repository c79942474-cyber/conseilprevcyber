#!/usr/bin/env node
/* RECETTE NAVIGATEUR DE L'ACCOMPAGNEMENT DE /securite-ia.
 *
 *   PORT=5077 python3 app.py &
 *   node outils/recette_securite_ia_accompagnement.js 5077 [capture.png]
 *
 * Mesure dans Chromium : la barre de progression part de zéro et avance sur
 * CONSTAT (cadrage rempli, système déclaré, maillon coté, calcul rendu) ;
 * chaque phase reçoit son encadré avec ses sources ; les info-bulles portent
 * une définition ; les listes du cadrage sont remplies ; l'aide à la décision
 * rend un niveau et une décision une fois la gravité donnée, et « gravité à
 * renseigner » sans elle.
 */
'use strict';
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const PORT = process.argv[2] || process.env.PORT || 5077;
const CAPTURE = process.argv[3] || '';
let echecs = 0;
function ok(c, m) { console.log((c ? '  ✓ ' : '  ✗ ') + m); if (!c) echecs++; }

(async () => {
  const nav = await chromium.launch();
  try {
    const p = await nav.newPage({ viewport: { width: 1280, height: 900 }, locale: 'fr-FR' });
    const err = [];
    p.on('pageerror', (e) => err.push(String(e)));
    await p.goto('http://localhost:' + PORT + '/securite-ia', { waitUntil: 'networkidle' });
    const ACC = (await (await p.request.get('http://localhost:' + PORT + '/api/securite-ia/accompagnement')).json()).accompagnement;
    await p.waitForFunction(() => document.querySelectorAll('#sia-etapes li').length > 0, null, { timeout: 15000 });
    const r0 = await p.evaluate(() => ({
      etapes: document.querySelectorAll('#sia-etapes li').length,
      n: document.getElementById('sia-prog-n').textContent,
      encadres: [...document.querySelectorAll('.sia-acc')].map((d) => d.getAttribute('data-phase')),
      sources: [...document.querySelectorAll('.sia-acc')].map((d) => d.querySelectorAll('.sia-src li').length),
      gravites: document.querySelectorAll('#sia-gravite option').length,
      secteurs: document.querySelectorAll('#sia-secteur option').length,
      nis2: document.querySelectorAll('#sia-nis2 option').length,
      bulles: [...document.querySelectorAll('.tipi[data-terme]')].filter((b) => b.getAttribute('data-tip')).length,
      bullesVides: [...document.querySelectorAll('.tipi[data-terme]')].filter((b) => !b.getAttribute('data-tip')).length,
    }));
    console.log('§1 — au chargement');
    ok(r0.etapes === ACC.phases.length, 'une étape par phase (' + r0.etapes + ')');
    ok(/^0 \/ /.test(r0.n), 'la barre part de zéro : « ' + r0.n + ' »');
    ok(r0.encadres.join() === ACC.phases.map((x) => x.cle).join(), 'chaque phase a son encadré, dans l\'ordre');
    ok(r0.sources.every((n, i) => n === ACC.phases[i].sources.length && n > 0), 'chaque encadré cite ses sources (' + r0.sources.join(',') + ')');
    ok(r0.gravites === ACC.gravites.length + 1 && r0.secteurs === ACC.secteurs.length + 1 && r0.nis2 === ACC.statuts_nis2.length + 1, 'les listes du cadrage sont remplies');
    ok(r0.bulles >= 3 && r0.bullesVides === 0, r0.bulles + ' info-bulle(s) avec définition, aucune vide');

    console.log('§2 — un système coté sans gravité');
    await p.fill('#si-nom', 'Agent de supervision');
    await p.click('#si-add');
    await p.selectOption('#si-a-action', '4');
    await p.selectOption('#si-t-action', '1');
    await p.waitForFunction(() => document.querySelector('#sia-decision .sia-dec-l'), null, { timeout: 10000 });
    const r1 = await p.evaluate(() => ({
      n: document.getElementById('sia-prog-n').textContent,
      faits: [...document.querySelectorAll('#sia-etapes a.fait')].map((a) => a.getAttribute('href')),
      dec: document.querySelector('#sia-decision .sia-dec-l li').textContent,
      bulles: [...document.querySelectorAll('#si-maillons .tipi')].every((b) => b.getAttribute('data-tip')),
    }));
    ok(r1.faits.join() === '#parc,#chaine', 'parc et chaîne faits, rien d\'autre : ' + r1.faits.join());
    ok(/Gravité à renseigner/.test(r1.dec), 'sans gravité, le maillon dit « Gravité à renseigner »');
    ok(r1.bulles, 'les info-bulles peintes par la chaîne ont leur définition');

    console.log('§3 — le cadrage rempli');
    await p.selectOption('#sia-secteur', 'energie');
    await p.selectOption('#sia-nis2', 'essentielle');
    await p.fill('#sia-valeur', 'Continuité de la fourniture');
    await p.selectOption('#sia-gravite', '3');
    await p.waitForFunction(() => /Inacceptable/.test((document.querySelector('#sia-decision') || {}).textContent || ''), null, { timeout: 10000 });
    const r2 = await p.evaluate(() => ({
      n: document.getElementById('sia-prog-n').textContent,
      faits: [...document.querySelectorAll('#sia-etapes a.fait')].map((a) => a.getAttribute('href')),
      tete: document.querySelector('#sia-decision .sia-dec-tete').textContent,
      li: document.querySelector('#sia-decision .sia-dec-l li').textContent,
      dit: document.getElementById('sia-gravite-dit').textContent,
      suggestions: document.querySelectorAll('#sia-valeurs option').length,
    }));
    ok(r2.faits.join() === '#cadrage,#parc,#chaine,#ebios', 'cadrage, parc, chaîne et lecture du risque faits : ' + r2.faits.join());
    ok(/Ne pas étendre/.test(r2.tete) && /Entité essentielle/.test(r2.tete) && /validée par la direction/.test(r2.tete),
       'décision d\'ensemble, mention NIS 2 et réserve de validation');
    ok(/Ramener l'autonomie/.test(r2.li) && /Faire passer la maîtrise/.test(r2.li), 'les deux leviers pour refermer le maillon');
    ok(r2.dit.length > 10 && r2.suggestions > 0, 'la gravité choisie est expliquée, le secteur propose des valeurs métier');
    ok(/^4 \/ 8/.test(r2.n), 'la barre dit « ' + r2.n + ' »');
    if (CAPTURE) {
      await p.evaluate(() => window.scrollTo(0, 0));
      await p.screenshot({ path: CAPTURE.replace(/\.png$/, '-haut.png') });
      await p.locator('#cadrage').screenshot({ path: CAPTURE.replace(/\.png$/, '-cadrage.png') });
      await p.locator('#sia-decision').screenshot({ path: CAPTURE.replace(/\.png$/, '-decision.png') });
    }
    ok(!err.length, 'aucune erreur JavaScript' + (err.length ? ' : ' + err[0] : ''));
  } finally {
    await nav.close();
  }
  console.log(echecs ? '\n✗ ' + echecs + ' mesure(s) en défaut.' : '\n✓ Accompagnement de /securite-ia : tout ce qui est mesuré tient.');
  process.exit(echecs ? 1 : 0);
})().catch((e) => { console.error('✗ ' + e.message); process.exit(1); });
