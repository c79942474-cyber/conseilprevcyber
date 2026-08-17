/* RECETTE — LA PROGRESSION DES PARCOURS GUIDÉS : VERT VISITÉ, AMBRE À FAIRE
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * CE QUI A CHANGÉ. Rôle et secteur choisis, la fiche listait les étapes sans
 * dire où on en était ; et les points du bandeau peignaient « fait » tout ce
 * qui précédait la POSITION courante — sauter à l'étape 4 peignait en vert
 * deux pages jamais ouvertes. Désormais :
 *
 *   - VERT ENCADRÉ : la page a été ATTEINTE pendant ce parcours — la visite
 *     est constatée au chargement de la page, jamais au clic qui y mène ;
 *   - AMBRE ENCADRÉ, BATTANT à 1,8 s : ce qui reste à faire — et le compte
 *     (« X visitées · Y à faire ») se lit en tête de fiche et dans le bandeau.
 *
 * CE QUE CES CONTRÔLES PROUVENT, dans l'ordre d'importance :
 *
 *   1. LE POINT QUI DÉCIDE — FAIT N'EST PAS DÉPASSÉ. On saute une étape :
 *      elle doit rester ambre pendant que celle qu'on atteint devient verte.
 *      C'est le mensonge exact que la progression par position racontait.
 *   2. LA VISITE EST CONSTATÉE À L'ARRIVÉE : après navigation réelle vers la
 *      page, pas à l'intention de clic.
 *   3. LE BATTEMENT EST SOBRE : 1,8 s — sous le seuil de photosensibilité —
 *      et il DISPARAÎT sous prefers-reduced-motion, remplacé par un cadre
 *      statique, pas par rien.
 *   4. LE VERT DIT CE QU'IL MESURE : « Visitée », avec l'infobulle qui
 *      précise que le module constate la visite, pas le travail accompli.
 *
 * Lancement :
 *     BASE=http://127.0.0.1:5404 node recette_parcours_progression.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
let ko = 0;
const ok = (n, c, d) => { console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : '')); if (!c) ko++; };
const titre = (t) => console.log('\n══ ' + t + ' ══\n');

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1400, height: 950 } });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
  });
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e)));

  /* Le parcours « découverte » traverse des pages réservées : on se connecte
     comme le fait recette_durabilite_page, sinon la moitié du chemin serait
     un formulaire de connexion. */
  await pg.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg.evaluate(async ([e, m]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: m }) }),
    [process.env.RECETTE_EMAIL || 'recette@local.test',
     process.env.RECETTE_MDP || 'RecetteLocale!2026']);

  /* CONVENTION DU DÉPÔT : un échec dans `evaluate` se rend en donnée. */
  const sur = async (fn, arg) => {
    try { return await pg.evaluate(fn, arg); }
    catch (e) { return { err: String(e && e.message || e) }; }
  };
  const attendreParcours = () => pg.waitForFunction(
    () => typeof window.parcoursOuvrir === 'function', null, { timeout: 30000 });

  // ── 1 ─────────────────────────────────────────────────────────────────
  titre('1. Rôle + secteur choisis : tout est « à faire », et le compte le dit');

  await pg.goto(BASE + '/secteurs', { waitUntil: 'domcontentloaded' });
  await attendreParcours();
  await pg.waitForTimeout(400);

  const depart = await sur(async () => {
    sessionStorage.removeItem('cp_parcours');
    window.parcoursOuvrir('decouverte');
    await new Promise(r => setTimeout(r, 300));
    const sec = document.getElementById('pc-select-sec');
    sec.value = 'energie';
    sec.dispatchEvent(new Event('change', { bubbles: true }));
    await new Promise(r => setTimeout(r, 300));
    const f = document.getElementById('pc-fiche');
    const compte = f.querySelector('.pc-compte');
    return {
      etapes: f.querySelectorAll('.pc-etape').length,
      restes: f.querySelectorAll('.pc-etape.pc-e-reste').length,
      faites: f.querySelectorAll('.pc-etape.pc-e-fait').length,
      compte: compte ? compte.textContent.replace(/\s+/g, ' ').trim() : 'absent',
      croise: !!f.querySelector('.pc-prio'),
    };
  });
  ok('la fiche du croisement rôle × secteur est rendue, priorités comprises',
     !depart.err && depart.etapes >= 5 && depart.croise,
     depart.err || (depart.etapes + ' étape(s), priorités calculées : ' + depart.croise));
  ok('AVANT TOUT GESTE, TOUT EST ENCADRÉ « À FAIRE » — rien n’est crédité d’avance',
     !depart.err && depart.restes === depart.etapes && depart.faites === 0,
     depart.err || (depart.restes + ' ambre / ' + depart.faites + ' verte'));
  ok('…et le compte l’écrit en tête de fiche',
     !depart.err && /0 visitée · 5 à faire sur 5 étapes/.test(depart.compte),
     depart.err || depart.compte);

  // ── 2 ─────────────────────────────────────────────────────────────────
  titre('2. « Rester ici » constate la visite : on y est, c’est un fait');

  const ici = await sur(async () => {
    const f = document.getElementById('pc-fiche');
    const lien = [...f.querySelectorAll('[data-pc-go]')]
      .find(a => a.getAttribute('href') === '/secteurs');
    if (!lien) return { err: 'lien « Rester ici » introuvable' };
    lien.click();
    await new Promise(r => setTimeout(r, 300));
    const g = JSON.parse(sessionStorage.getItem('cp_parcours') || 'null');
    return { vus: g ? g.vus : null, sec: g ? g.sec : null };
  });
  ok('la page où l’on se trouve entre dans les visites',
     !ici.err && Array.isArray(ici.vus) && ici.vus.indexOf('/secteurs') >= 0,
     ici.err || JSON.stringify(ici.vus));
  ok('…et le secteur choisi est conservé avec le parcours',
     !ici.err && ici.sec === 'energie', ici.err || ('secteur : ' + ici.sec));

  // ── 3 : LE POINT QUI DÉCIDE ───────────────────────────────────────────
  titre('3. FAIT N’EST PAS DÉPASSÉ : l’étape sautée reste ambre');

  /* On saute directement à l'étape 4 (glossaire), par navigation réelle,
     sans passer par les étapes 2 et 3. La progression par position aurait
     peint les trois premières en vert ; la progression par VISITE ne doit
     créditer que ce qui a été vu. */
  await pg.goto(BASE + '/glossaire-62443', { waitUntil: 'domcontentloaded' });
  await attendreParcours();
  await pg.waitForTimeout(500);

  const saut = await sur(async () => {
    const g = JSON.parse(sessionStorage.getItem('cp_parcours') || 'null');
    window.parcoursOuvrir('decouverte');
    await new Promise(r => setTimeout(r, 400));
    const f = document.getElementById('pc-fiche');
    const etats = [...f.querySelectorAll('.pc-etape')].map(x =>
      x.classList.contains('pc-e-fait') ? 'fait' : 'reste');
    const compte = (f.querySelector('.pc-compte') || {}).textContent || '';
    return { vus: g ? g.vus : null, i: g ? g.i : null, etats,
             compte: compte.replace(/\s+/g, ' ').trim() };
  });
  ok('la navigation réelle vers l’étape 4 est constatée à l’ARRIVÉE',
     !saut.err && saut.vus && saut.vus.indexOf('/glossaire-62443') >= 0
       && saut.i === 3,
     saut.err || ('vus=' + JSON.stringify(saut.vus) + ' · i=' + saut.i));
  ok('LES ÉTAPES SAUTÉES (2 et 3) RESTENT AMBRE — le mensonge par position est mort',
     !saut.err && saut.etats[1] === 'reste' && saut.etats[2] === 'reste',
     saut.err || saut.etats.join(' · '));
  ok('…pendant que la 1 et la 4, réellement vues, sont vertes',
     !saut.err && saut.etats[0] === 'fait' && saut.etats[3] === 'fait',
     saut.err || saut.etats.join(' · '));
  ok('…et le compte suit : 2 visitées · 3 à faire',
     !saut.err && /2 visitées · 3 à faire/.test(saut.compte),
     saut.err || saut.compte);

  // ── 4 ─────────────────────────────────────────────────────────────────
  titre('4. Le bandeau dit la même chose que la fiche');

  const bandeau = await sur(() => {
    const b = document.getElementById('pc-bandeau');
    if (!b || !b.classList.contains('on')) return { err: 'bandeau absent' };
    return {
      faits: b.querySelectorAll('.pc-dot.fait').length,
      restes: b.querySelectorAll('.pc-dot.reste').length,
      ici: b.querySelectorAll('.pc-dot.ici').length,
      texte: (b.querySelector('.pc-b-reste') || {}).textContent || 'absent',
    };
  });
  ok('les points du bandeau comptent les VISITES, pas la position',
     !bandeau.err && bandeau.faits === 1 && bandeau.ici === 1 && bandeau.restes === 3,
     bandeau.err || (bandeau.faits + ' vert(s) + 1 courant · ' + bandeau.restes + ' ambre(s)'));
  ok('…et le bandeau porte le compte de ce qui reste',
     !bandeau.err && /3 à faire/.test(bandeau.texte), bandeau.err || bandeau.texte);

  // ── 5 ─────────────────────────────────────────────────────────────────
  titre('5. Le battement est sobre, et il s’efface pour qui le demande');

  const anim = await sur(() => {
    const e = document.querySelector('.pc-etape.pc-e-reste');
    if (!e) return { err: 'aucune étape à faire à l’écran' };
    const cs = getComputedStyle(e);
    return { nom: cs.animationName, duree: cs.animationDuration,
             bord: cs.borderColor };
  });
  ok('les étapes à faire battent à 1,8 s — sous le seuil de photosensibilité',
     !anim.err && anim.nom === 'pcAFaire' && anim.duree === '1.8s',
     anim.err || (anim.nom + ' · ' + anim.duree));

  const badge = await sur(() => {
    const v = document.querySelector('.pc-e-etat.fait');
    const r = document.querySelector('.pc-e-etat.reste');
    return { vert: v ? v.textContent.trim() : null,
             vertTitre: v ? (v.getAttribute('title') || '') : '',
             ambre: r ? r.textContent.trim() : null };
  });
  ok('le vert DIT ce qu’il mesure : « Visitée », la visite et pas le travail',
     !badge.err && badge.vert === '✓ Visitée'
       && /constate la visite, pas le travail/.test(badge.vertTitre),
     badge.err || (badge.vert + ' — ' + badge.vertTitre.slice(0, 60)));
  ok('…et l’ambre dit « À faire »', !badge.err && badge.ambre === 'À faire');

  /* MOUVEMENT RÉDUIT : un contexte à part — la préférence se déclare à la
     création. Le battement doit disparaître, le cadre ambre RESTER. */
  const ctx2 = await nav.newContext({ reducedMotion: 'reduce',
    viewport: { width: 1400, height: 950 } });
  await ctx2.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
  });
  const pg2 = await ctx2.newPage();
  await pg2.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg2.evaluate(async ([e, m]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: m }) }),
    ['recette@local.test', 'RecetteLocale!2026']);
  await pg2.goto(BASE + '/secteurs', { waitUntil: 'domcontentloaded' });
  await pg2.waitForFunction(() => typeof window.parcoursOuvrir === 'function',
    null, { timeout: 30000 });
  const calme = await pg2.evaluate(async () => {
    window.parcoursOuvrir('decouverte');
    await new Promise(r => setTimeout(r, 400));
    /* PAS l'étape courante : son cadre est teal (« vous y êtes ») et il
       aurait fait passer le contrôle sans rien prouver sur l'ambre. */
    const e = document.querySelector('.pc-etape.pc-e-reste:not(.pc-ici)');
    if (!e) return { err: 'aucune étape à faire hors page courante' };
    const cs = getComputedStyle(e);
    return { animation: cs.animationName, bord: cs.borderColor };
  }).catch(e => ({ err: String(e && e.message || e) }));
  /* L'ambre du site est #F0B429 = rgb(240, 180, 41). */
  ok('SOUS MOUVEMENT RÉDUIT, le battement disparaît — et le cadre reste AMBRE',
     !calme.err && calme.animation === 'none' && calme.bord === 'rgb(240, 180, 41)',
     calme.err || (calme.animation + ' · bord ' + calme.bord));
  await pg2.close();

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  console.log('\n' + (ko === 0 ? 'tout est vert' : ko + ' contrôle(s) en échec') + '\n');
  await nav.close();
  process.exit(ko === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
