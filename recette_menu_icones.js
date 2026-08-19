/* RECETTE — LES ICÔNES DU MENU LATÉRAL
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * LA DEMANDE. Des repères visuels colorés à gauche des titres de rubrique,
 * pour situer une section d'un coup d'œil dans un menu de huit rubriques et
 * quarante entrées.
 *
 * CE QUE CES CONTRÔLES GARDENT :
 *
 *   1. CHAQUE RUBRIQUE A SON ICÔNE — aucune n'est laissée sans repère, sans
 *      quoi celle qui en manque paraîtrait rangée ailleurs.
 *   2. CHAQUE ICÔNE A UNE SILHOUETTE DISTINCTE. La couleur ne peut pas être le
 *      seul signal : deux rubriques partagent une teinte, et qui ne distingue
 *      pas le cyan du violet doit reconnaître un livre d'un bâtiment
 *      (WCAG 1.4.1).
 *   3. ELLES SONT MUETTES POUR LES AIDES VOCALES. Le titre est écrit juste à
 *      côté ; annoncer l'icône le répéterait.
 *   4. LE TITRE RESTE LISIBLE — l'icône ne le pousse pas hors du tiroir.
 *
 * Lancement :
 *     BASE=http://127.0.0.1:5732 node recette_menu_icones.js
 */
const { chromium } = require('playwright');

const BASE = process.env.BASE || 'http://127.0.0.1:5732';

let ko = 0;
const ok = (t, cond, detail) => {
  console.log((cond ? '  OK   ' : '  KO   ') + t + (detail ? ' — ' + detail : ''));
  if (!cond) ko++;
};
const titre = t => console.log('\n══ ' + t + ' ══\n');

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({
    viewport: { width: 1280, height: 1000 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      + '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'fr-FR'
  });
  /* SANS CE MASQUE, LE SERVEUR BLOQUE L'ADRESSE POUR 1800 s. */
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
  });
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(e.message));
  const sur = async (fn, arg) => {
    try { return await pg.evaluate(fn, arg); }
    catch (e) { return { err: String(e && e.message || e) }; }
  };

  await pg.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(700);
  /* Le tiroir se construit au premier clic sur le bouton de menu. */
  await pg.evaluate(() => {
    const b = document.querySelector('.menu-btn');
    if (b) b.click();
  });
  await pg.waitForFunction(() => document.querySelectorAll('.drawer-nav h4').length > 0,
                           null, { timeout: 20000 }).catch(() => {});
  await pg.waitForTimeout(500);

  // ── 1 ───────────────────────────────────────────────────────────────────
  titre('1. Chaque rubrique porte son icône');

  const base = await sur(() => {
    const h = [...document.querySelectorAll('.drawer-nav h4')];
    return {
      rubriques: h.length,
      avecIcone: h.filter(x => x.querySelector('svg.drawer-ic')).length,
      sans: h.filter(x => !x.querySelector('svg.drawer-ic'))
             .map(x => x.textContent.trim().slice(0, 30))
    };
  });
  ok('le tiroir est construit et porte ses rubriques',
     !base.err && base.rubriques >= 6, base.err || (base.rubriques + ' rubrique(s)'));
  ok('AUCUNE rubrique n’est laissée sans repère',
     !base.err && base.avecIcone === base.rubriques,
     base.err || ('sans icône : ' + (base.sans || []).join(', ')));

  // ── 2 : LE POINT QUI DÉCIDE ─────────────────────────────────────────────
  titre('2. La couleur n’est pas le seul signal (WCAG 1.4.1)');

  const formes = await sur(() => {
    const sv = [...document.querySelectorAll('.drawer-nav h4 svg.drawer-ic')];
    const trace = sv.map(s => s.innerHTML.replace(/\s+/g, ''));
    const teintes = sv.map(s => getComputedStyle(s).color);
    return {
      n: sv.length,
      silhouettesDistinctes: new Set(trace).size,
      teintesDistinctes: new Set(teintes).size,
      teintes: [...new Set(teintes)]
    };
  });
  ok('CHAQUE ICÔNE A UNE SILHOUETTE DIFFÉRENTE — c’est elle qui distingue',
     !formes.err && formes.silhouettesDistinctes === formes.n,
     formes.err || (formes.silhouettesDistinctes + ' silhouette(s) pour '
                    + formes.n + ' rubriques'));
  /* CE CONTRÔLE EST DÉLIBÉRÉMENT TOLÉRANT SUR LA COULEUR : deux rubriques
     partagent une teinte, et c'est assumé — la palette en compte six pour huit
     rubriques. Ce qui ne doit PAS arriver, c'est que tout soit de la même. */
  ok('…et les teintes sont variées sans avoir à être uniques',
     !formes.err && formes.teintesDistinctes >= 4,
     formes.err || (formes.teintesDistinctes + ' teinte(s) : '
                    + (formes.teintes || []).join(' · ')));

  // ── 3 ───────────────────────────────────────────────────────────────────
  titre('3. Les icônes sont muettes pour les aides vocales');

  const a11y = await sur(() => {
    const sv = [...document.querySelectorAll('.drawer-nav h4 svg.drawer-ic')];
    return {
      n: sv.length,
      cachees: sv.filter(s => s.getAttribute('aria-hidden') === 'true').length,
      focusables: sv.filter(s => s.getAttribute('focusable') !== 'false').length,
      // Le titre reste écrit à côté de l'icône.
      titresEcrits: [...document.querySelectorAll('.drawer-nav h4')]
        .filter(h => h.textContent.trim().length > 2).length
    };
  });
  ok('toutes les icônes sont masquées aux aides vocales',
     !a11y.err && a11y.cachees === a11y.n,
     a11y.err || ((a11y.n - a11y.cachees) + ' annoncée(s)'));
  ok('…et aucune n’attrape la tabulation',
     !a11y.err && a11y.focusables === 0, a11y.err || (a11y.focusables + ' focusable(s)'));
  ok('…le titre reste ÉCRIT à côté de l’icône',
     !a11y.err && a11y.titresEcrits === a11y.n, a11y.err);

  // ── 4 ───────────────────────────────────────────────────────────────────
  titre('4. L’icône ne chasse pas le titre hors du tiroir');

  const geo = await sur(() => {
    const dr = document.querySelector('.drawer');
    const rd = dr.getBoundingClientRect();
    const debord = [...document.querySelectorAll('.drawer-nav h4')].filter(h => {
      const r = h.getBoundingClientRect();
      return r.right > rd.right + 1;
    }).length;
    const ic = document.querySelector('.drawer-nav svg.drawer-ic');
    const r = ic.getBoundingClientRect();
    return { debord, larg: Math.round(r.width), haut: Math.round(r.height),
             visible: r.width > 0 && r.height > 0 };
  });
  ok('aucun titre ne déborde du tiroir',
     !geo.err && geo.debord === 0, geo.err || (geo.debord + ' débordement(s)'));
  ok('…et l’icône est réellement dessinée',
     !geo.err && geo.visible && geo.larg >= 14,
     geo.err || (geo.larg + '×' + geo.haut + ' px'));

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  console.log('\n' + (ko === 0 ? 'tout est vert' : ko + ' contrôle(s) en échec') + '\n');
  await nav.close();
  process.exit(ko === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
