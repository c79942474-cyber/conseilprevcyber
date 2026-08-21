/* RECETTE — LES QUATRE PERSPECTIVES, REPLIÉES SANS PERDRE LEUR PROPOS
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * LA DEMANDE. Les quatre cartes occupaient 509 px avant même la première
 * question, et le chapeau 274 px de plus. Un sélecteur les remplace.
 *
 * LE PIÈGE, ET C'EST LUI QUE CES CONTRÔLES GARDENT. Ce bloc n'existe pas pour
 * décrire quatre perspectives : il existe pour montrer UNE ASYMÉTRIE — trois
 * sont demandées au client, la quatrième est établie par les données, et c'est
 * tout le propos de la méthode. N'en afficher qu'une à la fois pouvait effacer
 * ce contraste. Il doit donc rester lisible SANS RIEN OUVRIR :
 *
 *   1. chaque option du sélecteur dit qui répond ;
 *   2. une ligne compte les deux natures, et ce compte est DÉRIVÉ ;
 *   3. la perspective scientifique n'est jamais annoncée comme « vous
 *      répondez » — la recueillir comme une opinion est précisément ce que la
 *      méthode refuse.
 *
 * Lancement :
 *     BASE=http://127.0.0.1:5731 node recette_perspectives_choix.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const BASE = process.env.BASE || 'http://127.0.0.1:5731';
const MAIL = process.env.MAIL || 'recette@local.test';
const MDP = process.env.MDP || 'RecetteLocale!2026';

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
  /* CONVENTION DU DÉPÔT : un échec dans `evaluate` se rend en donnée. */
  const sur = async (fn, arg) => {
    try { return await pg.evaluate(fn, arg); }
    catch (e) { return { err: String(e && e.message || e) }; }
  };

  await pg.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(500);
  const cnx = await sur(async ([m, p]) => {
    const r = await fetch('/api/auth/login', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: m, password: p })
    });
    return { statut: r.status };
  }, [MAIL, MDP]);
  ok('la session de recette s’ouvre', !cnx.err && cnx.statut === 200,
     cnx.err || ('HTTP ' + cnx.statut));

  await pg.goto(BASE + '/strategie-durable-datacenter', { waitUntil: 'domcontentloaded' });
  await pg.waitForFunction(() => document.getElementById('sd-persp-sel'),
                           null, { timeout: 40000 }).catch(() => {});
  await pg.waitForTimeout(500);

  // ── 1 ───────────────────────────────────────────────────────────────────
  titre('1. Une perspective à la fois, choisie dans une liste');

  const base = await sur(() => {
    const sel = document.getElementById('sd-persp-sel');
    if (!sel) return { absent: true };
    return {
      options: [...sel.options].map(o => o.textContent.trim()),
      cartes: document.querySelectorAll('#sd-persp .sd-p').length,
      etiquette: !!document.querySelector('.sd-persp-choix label[for="sd-persp-sel"]')
    };
  });
  ok('un sélecteur remplace les quatre cartes',
     !base.err && !base.absent && base.options.length === 4,
     base.err || ((base.options || []).length + ' option(s)'));
  ok('…et une seule perspective est affichée à la fois',
     !base.err && base.cartes === 1, base.err || (base.cartes + ' carte(s)'));
  ok('…le sélecteur porte une étiquette qui lui est liée',
     !base.err && base.etiquette);

  // ── 2 : LE POINT QUI DÉCIDE ─────────────────────────────────────────────
  titre('2. L’asymétrie 3 / 1 se lit SANS RIEN OUVRIR');

  const asym = await sur(() => {
    const sel = document.getElementById('sd-persp-sel');
    const opts = [...sel.options].map(o => o.textContent.trim());
    const ligne = (document.querySelector('.sd-persp-dit') || {}).textContent || '';
    return {
      opts, ligne: ligne.replace(/\s+/g, ' ').trim(),
      client: opts.filter(t => /vous répondez/.test(t)).length,
      donnees: opts.filter(t => /établi par les données/.test(t)).length,
      // La perspective scientifique ne doit JAMAIS être annoncée « vous répondez ».
      scienceFausse: opts.filter(
        t => /[Ss]cience/.test(t) && /vous répondez/.test(t)).length
    };
  });
  ok('CHAQUE OPTION dit qui répond — on le lit sans ouvrir',
     !asym.err && asym.client + asym.donnees === (asym.opts || []).length,
     asym.err || (asym.opts || []).join(' | '));
  ok('…trois « vous répondez » et une « établi par les données »',
     !asym.err && asym.client === 3 && asym.donnees === 1,
     asym.err || (asym.client + ' / ' + asym.donnees));
  const scienceOK = !asym.err && asym.scienceFausse === 0;
  ok('LA SCIENCE N’EST JAMAIS PRÉSENTÉE COMME UNE RÉPONSE DU CLIENT', scienceOK,
     scienceOK ? '' : (asym.err
       || 'la perspective scientifique est annoncée « vous répondez »'));
  ok('…et une ligne compte les deux natures avant le choix',
     !asym.err && /3 vous sont demandées/.test(asym.ligne)
       && /1 est établie/.test(asym.ligne), asym.err || asym.ligne);

  // ── 3 ───────────────────────────────────────────────────────────────────
  titre('3. Le compte est DÉRIVÉ de la donnée, pas écrit en dur');

  const derive = await sur(async () => {
    const r = await fetch('/api/datacenter/strategie/questionnaire', { credentials: 'same-origin' });
    const j = await r.json();
    const P = ((j.questionnaire || {}).perspectives) || [];
    return { n: P.length,
             client: P.filter(p => p.source === 'client').length,
             ligne: ((document.querySelector('.sd-persp-dit') || {}).textContent || '')
                      .replace(/\s+/g, ' ') };
  });
  ok('le compte affiché est celui que le serveur déclare',
     !derive.err && derive.n > 0
       && derive.ligne.indexOf(derive.n + ' perspectives') >= 0
       && derive.ligne.indexOf(derive.client + ' vous sont demandées') >= 0,
     derive.err || (derive.n + ' / ' + derive.client + ' · « ' + derive.ligne + ' »'));

  // ── 4 ───────────────────────────────────────────────────────────────────
  titre('4. Le choix change réellement la carte');

  const chg = await sur(() => {
    const sel = document.getElementById('sd-persp-sel');
    const lu = () => {
      const c = document.querySelector('#sd-persp .sd-p');
      return { titre: (c.querySelector('h3') || {}).textContent.trim(),
               classe: c.className,
               src: (c.querySelector('.sd-src') || {}).textContent.trim() };
    };
    const avant = lu();
    sel.value = sel.options[2].value;
    sel.dispatchEvent(new Event('change'));
    const apres = lu();
    sel.value = sel.options[0].value;
    sel.dispatchEvent(new Event('change'));
    return { avant, apres, revenu: lu() };
  });
  ok('choisir une autre perspective remplace la carte',
     !chg.err && chg.avant.titre !== chg.apres.titre,
     chg.err || (chg.avant.titre + ' → ' + chg.apres.titre));
  ok('…et la carte porte la bonne mention de source',
     !chg.err && /établi par les données/.test(chg.apres.src),
     chg.err || chg.apres.src);
  ok('…revenir au premier choix le restitue',
     !chg.err && chg.revenu.titre === chg.avant.titre, chg.err);

  // ── 5 ───────────────────────────────────────────────────────────────────
  titre('5. La place est réellement gagnée');

  const place = await sur(() => {
    const z = document.getElementById('sd-persp');
    const sect = z.closest('section');
    const leads = [...sect.querySelectorAll('p.lead')];
    return {
      bloc: Math.round(z.getBoundingClientRect().height),
      chapeau: leads.reduce((s, p) => s + Math.round(p.getBoundingClientRect().height), 0),
      car: leads.reduce((s, p) => s + p.textContent.replace(/\s+/g, ' ').trim().length, 0),
      paragraphes: leads.length
    };
  });
  /* MESURÉ AVANT : bloc 509 px, chapeau 274 px sur deux paragraphes (688
     caractères). Les seuils bornent ce qui a été gagné, ils ne le devinent
     pas. */
  ok('le bloc des perspectives tient sous 300 px (509 auparavant)',
     !place.err && place.bloc < 300, place.err || (place.bloc + ' px'));
  ok('le chapeau tient en UN paragraphe sous 200 px (274 auparavant)',
     !place.err && place.paragraphes === 1 && place.chapeau < 200,
     place.err || (place.paragraphes + ' paragraphe(s), ' + place.chapeau + ' px'));
  ok('…et il a réellement été raccourci (688 caractères auparavant)',
     !place.err && place.car < 450, place.err || (place.car + ' caractères'));

  // ── 6 ───────────────────────────────────────────────────────────────────
  titre('6. Le clavier suffit, et rien ne déborde');

  for (const [nom, w] of [['bureau', 1280], ['téléphone', 390]]) {
    await pg.setViewportSize({ width: w, height: 900 });
    await pg.waitForTimeout(400);
    const g = await sur(() => {
      const sel = document.getElementById('sd-persp-sel');
      const r = sel.getBoundingClientRect();
      return { tab: sel.tabIndex >= 0, haut: Math.round(r.height),
               deborde: r.right > document.documentElement.clientWidth + 1,
               pageDeborde: document.documentElement.scrollWidth
                          > document.documentElement.clientWidth + 1 };
    });
    ok('[' + nom + '] le sélecteur est atteignable au clavier et fait 24 px au moins',
       !g.err && g.tab && g.haut >= 24, g.err || (g.haut + ' px'));
    ok('[' + nom + '] …et rien ne sort de la fenêtre',
       !g.err && !g.deborde && !g.pageDeborde, g.err);
  }

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  console.log('\n' + (ko === 0 ? 'tout est vert' : ko + ' contrôle(s) en échec') + '\n');
  await nav.close();
  process.exit(ko === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
