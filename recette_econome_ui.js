const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE, SC = process.env.SC;
let ko = 0;
const ok = (t, c, d) => { console.log((c ? '  OK   ' : '  KO   ') + t + (!c && d ? ' — ' + d : '')); if (!c) ko++; };

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1400, height: 1100 }, deviceScaleFactor: 2 });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
  });
  const pg = await ctx.newPage();
  const err = []; pg.on('pageerror', e => err.push(String(e).slice(0, 160)));
  await pg.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(600);
  await pg.fill('#email', 'recette@local.test');
  await pg.fill('#password', 'RecetteLocale!2026');
  await pg.click('form button[type=submit], form .btn');
  await pg.waitForTimeout(2500);
  await pg.goto(BASE + '/ingenierie-datacenter', { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(3200);

  // ── 1. La provenance est proposée sur chaque prix ──────────────────────
  const prov = await pg.evaluate(() => {
    const p = [...document.querySelectorAll('#ig-eco-saisie input[data-p]')];
    const v = [...document.querySelectorAll('#ig-eco-saisie select[data-v]')];
    const opts = v[0] ? [...v[0].options].map(o => o.textContent) : [];
    return { prix: p.length, selects: v.length, options: opts,
             apparies: p.every(x => document.getElementById('ecov-' + x.getAttribute('data-p'))) };
  });
  ok('chaque prix porte un sélecteur de provenance',
     prov.prix > 0 && prov.selects === prov.prix && prov.apparies,
     prov.prix + ' prix / ' + prov.selects + ' sélecteurs');
  ok('…et la liste propose les cinq provenances, du plus opposable au moins',
     prov.options.length === 6, JSON.stringify(prov.options));

  // ── 2. La puissance est reprise de l'étape 2, en temps réel ────────────
  const haut = await pg.$('[data-champ="puissance_it_kw"]');
  ok('l’étape 2 porte bien le champ de puissance', !!haut);
  if (haut) {
    await haut.fill('1750');
    await pg.waitForTimeout(600);
    const repris = await pg.evaluate(() => {
      const c = document.getElementById('ecoq-puissance_it_kw');
      const n = document.getElementById('ig-eco-repris');
      return { valeur: c ? c.value : null, repris: c ? c.dataset.repris : null,
               note: n && n.style.display !== 'none' ? n.textContent : '' };
    });
    ok('LE POINT QUI DÉCIDE — la puissance saisie plus haut arrive ici sans recharger',
       repris.valeur === '1750', 'lu : ' + repris.valeur);
    ok('…et le champ DIT d’où vient sa valeur',
       /reprise de l’étape 2/.test(repris.note), repris.note.slice(0, 70));

    // Une saisie manuelle ici reprend la main : le profil ne doit plus écraser.
    await pg.fill('#ecoq-puissance_it_kw', '900');
    await pg.waitForTimeout(300);
    await haut.fill('2400');
    await pg.waitForTimeout(600);
    const apres = await pg.evaluate(() =>
      document.getElementById('ecoq-puissance_it_kw').value);
    ok('LE POINT QUI DÉCIDE — une correction locale n’est PAS écrasée par l’étape 2',
       apres === '900', 'valeur après modification amont : ' + apres);
  }

  // ── 3. Le tableau porte la provenance, et compte celles qui manquent ───
  await pg.fill('#ecop-froid', '900');
  await pg.selectOption('#ecov-froid', 'devis');
  await pg.fill('#ecop-distribution_secours', '1400');   // volontairement sans source
  await pg.click('#ig-eco-go');
  await pg.waitForTimeout(1800);
  const res = await pg.evaluate(() => {
    const o = document.getElementById('ig-eco-out');
    return { avecSource: o.querySelectorAll('.ig-eco-src:not(.ig-eco-nosrc)').length,
             sansSource: o.querySelectorAll('.ig-eco-nosrc').length,
             compte: /prix saisi\(s\) sans/.test(o.innerText),
             texte: o.innerText.slice(0, 120).replace(/\n+/g, ' | ') };
  });
  ok('le tableau étiquette le prix qui porte sa source',
     res.avecSource === 1, 'trouvés : ' + res.avecSource);
  ok('…et signale celui qui n’en porte pas',
     res.sansSource === 1, 'trouvés : ' + res.sansSource);
  ok('…et le compte est publié sous le tableau', res.compte === true, res.texte);

  // ── 4. Aucun prix n'est proposé tant qu'aucune opération n'est livrée ──
  const sug = await pg.evaluate(() => ({
    listes: document.querySelectorAll('#ig-eco-saisie datalist').length,
    notes: document.querySelectorAll('#ig-eco-saisie .ig-sug').length
  }));
  ok('LE POINT QUI DÉCIDE — aucun prix n’est suggéré, faute d’opération livrée',
     sug.listes === 0 && sug.notes === 0,
     sug.listes + ' liste(s), ' + sug.notes + ' note(s) — le module en propose sans base');

  ok('aucune erreur de script', err.length === 0, err.slice(0, 2).join(' | '));

  const sec = await pg.$('#ig-eco');
  await sec.scrollIntoViewIfNeeded(); await pg.waitForTimeout(400);
  await sec.screenshot({ path: SC + '/eco_section2.png' });
  await nav.close();
  console.log('\n' + (ko === 0 ? 'tout est vert' : ko + ' contrôle(s) en échec') + '\n');
  process.exit(ko === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
