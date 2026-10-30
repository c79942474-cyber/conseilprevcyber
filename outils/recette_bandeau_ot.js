#!/usr/bin/env node
/* RECETTE NAVIGATEUR DU BANDEAU « OFFSHORE SUBSTATIONS — OT SECURITY ».
 *
 *   PORT=5077 python3 app.py &      (le site en local)
 *   node outils/recette_bandeau_ot.js 5077
 *
 * Mesure, dans Chromium : l'affiche est là dès le chargement, au-dessus du
 * titre ; la vidéo arrive ensuite et joue ; la pause l'arrête SANS ouvrir
 * d'onglet ; un clic sur le bandeau ouvre le profil LinkedIn dans un nouvel
 * onglet ; sous mouvement réduit, l'affiche tient seule et la pause reste
 * cachée. LinkedIn n'est pas contacté : la requête est interceptée.
 */
'use strict';
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const PORT = process.argv[2] || process.env.PORT || 5077;
const URL = 'http://localhost:' + PORT + '/';
const PROFIL = 'https://www.linkedin.com/in/cerfchristophe';
let echecs = 0;
function ok(cond, msg) { console.log((cond ? '  ✓ ' : '  ✗ ') + msg); if (!cond) echecs++; }

(async () => {
  const nav = await chromium.launch();
  try {
    const ctx = await nav.newContext({ viewport: { width: 1280, height: 800 }, locale: 'fr-FR' });
    await ctx.route('https://www.linkedin.com/**', (r) => r.fulfill({ status: 200, body: 'profil', contentType: 'text/html' }));
    const p = await ctx.newPage();
    await p.goto(URL, { waitUntil: 'domcontentloaded' });
    const g = await p.evaluate(() => {
      const f = document.getElementById('bandeau-ot').getBoundingClientRect();
      const h = document.querySelector('main h1').getBoundingClientRect();
      return { l: f.width, h: f.height, bas: f.bottom, titre: h.top, video: !!document.querySelector('.bandeau-ot-video') };
    });
    console.log('§1 — au chargement');
    ok(Math.abs(g.l / g.h - 4) < 0.02, 'le bandeau est au format 4:1 (' + g.l + ' × ' + g.h + ')');
    ok(g.bas <= g.titre, 'le bandeau est au-dessus du titre');
    await p.waitForFunction(() => document.getElementById('bandeau-ot').getAttribute('data-etat') === 'vidéo', null, { timeout: 15000 });
    console.log('§2 — la vidéo');
    const t0 = await p.evaluate(() => document.querySelector('.bandeau-ot-video').currentTime);
    await p.waitForTimeout(1200);
    const t1 = await p.evaluate(() => document.querySelector('.bandeau-ot-video').currentTime);
    ok(t1 > t0, 'elle joue (' + t0.toFixed(2) + ' → ' + t1.toFixed(2) + ' s)');
    console.log('§3 — la pause');
    const onglets = ctx.pages().length;
    await p.click('.bandeau-ot-btn');
    await p.waitForTimeout(300);
    ok(await p.evaluate(() => document.querySelector('.bandeau-ot-video').paused), 'la vidéo est en pause');
    ok(await p.getAttribute('.bandeau-ot-btn', 'aria-label') === 'Relancer l’animation', 'le bouton dit « Relancer l’animation »');
    ok(ctx.pages().length === onglets, "la pause n'a ouvert aucun onglet");
    console.log('§4 — le lien');
    const [onglet] = await Promise.all([ctx.waitForEvent('page'), p.click('.bandeau-ot-lien', { position: { x: 500, y: 120 } })]);
    await onglet.waitForLoadState();
    ok(onglet.url() === PROFIL, 'un clic sur le bandeau ouvre ' + onglet.url());
    await ctx.close();

    console.log('§5 — mouvement réduit');
    const ctx2 = await nav.newContext({ viewport: { width: 390, height: 760 }, reducedMotion: 'reduce' });
    const q = await ctx2.newPage();
    await q.goto(URL, { waitUntil: 'load' });
    await q.waitForTimeout(2500);
    const r = await q.evaluate(() => ({ etat: document.getElementById('bandeau-ot').getAttribute('data-etat'),
      video: !!document.querySelector('.bandeau-ot-video'), btn: document.querySelector('.bandeau-ot-btn').hidden }));
    ok(!r.video && /mouvement réduit/.test(r.etat || ''), "l'affiche tient seule (" + r.etat + ')');
    ok(r.btn, 'le bouton de pause reste caché');
    await ctx2.close();
  } finally {
    await nav.close();
  }
  console.log(echecs ? '\n✗ ' + echecs + ' mesure(s) en défaut.' : "\n✓ Bandeau de l'accueil : tout ce qui est mesuré tient.");
  process.exit(echecs ? 1 : 0);
})().catch((e) => { console.error('✗ ' + e.message); process.exit(1); });
