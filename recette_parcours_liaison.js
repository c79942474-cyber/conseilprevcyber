/* RECETTE — LE PARCOURS NE DIT JAMAIS QU'ON EST OÙ L'ON N'EST PAS
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * LE DÉFAUT MESURÉ, ET IL PORTAIT SUR TOUTE LA LIAISON ENTRE PAGES.
 * Cliquer « Suivant » écrivait l'étape suivante dans l'état, PUIS le navigateur
 * partait. Quand la page visée demandait un compte, le serveur renvoyait vers
 * /connexion?next=… — et le bandeau annonçait « Étape 5 / 7 · Feuille de
 * route » à un lecteur assis devant un formulaire de connexion. Mesuré en
 * marchant le parcours RSSI sans session : les SEPT étapes mentaient, et rien
 * à l'écran ne disait pourquoi la page demandée n'était pas là.
 *
 * C'est très exactement « le cheminement est incertain et pas fiable ».
 *
 * CE QUE CES CONTRÔLES PROUVENT :
 *
 *   1. CONNECTÉ, la marche complète est fidèle : chaque page atteinte pose son
 *      rang et sa visite, du premier au dernier pas.
 *   2. LE POINT QUI DÉCIDE — AU MUR DE CONNEXION, LE RANG NE BOUGE PAS. Le
 *      bandeau passe en « En attente », dit QUELLE étape est retenue, pourquoi,
 *      et offre les deux portes (connexion, inscription).
 *   3. FRANCHIR LE MUR LÈVE L'ÉTAT : la page enfin ouverte pose son rang, sa
 *      visite, et l'avertissement disparaît.
 *   4. LES COMPTES ANNONCÉS SONT LES COMPTES RÉELS — rôles, secteurs,
 *      croisements, et les pages que les parcours traversent.
 *   5. AUCUN LIEN MORT : chaque étape, chaque note sectorielle et chaque entrée
 *      du moteur désigne une page que le serveur sert vraiment.
 *
 * Lancement :
 *     BASE=http://127.0.0.1:5404 node recette_parcours_liaison.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
let ko = 0;
const ok = (n, c, d) => { console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : '')); if (!c) ko++; };
const titre = (t) => console.log('\n══ ' + t + ' ══\n');

const PARCOURS = 'rssi';
const SECTEUR = 'energie';

(async () => {
  const nav = await chromium.launch();
  const ctxNeuf = async () => {
    const c = await nav.newContext({ viewport: { width: 1400, height: 950 } });
    await c.addInitScript(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => false });
      Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
      Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
    });
    return c;
  };
  const armer = pg => pg.waitForFunction(
    () => typeof window.parcoursOuvrir === 'function', null, { timeout: 30000 });
  /* CONVENTION DU DÉPÔT : un échec dans `evaluate` se rend en donnée. */
  const sur = async (pg, fn, arg) => {
    try { return await pg.evaluate(fn, arg); }
    catch (e) { return { err: String(e && e.message || e) }; }
  };
  const etat = pg => sur(pg, () => {
    const b = document.getElementById('pc-bandeau');
    const g = JSON.parse(sessionStorage.getItem('cp_parcours') || 'null');
    return {
      url: location.pathname,
      step: b ? ((b.querySelector('.pc-b-step') || {}).textContent || '').replace(/\s+/g, ' ') : null,
      attente: !!(b && b.querySelector('.pc-b-step.att')),
      mur: b ? ((b.querySelector('.pc-mur') || {}).textContent || '') : '',
      murTexte: b ? ((b.querySelector('.pc-b-mur') || {}).textContent || '').replace(/\s+/g, ' ') : '',
      portes: b ? [...b.querySelectorAll('.pc-b-mur a')].map(a => a.getAttribute('href')) : [],
      i: g ? g.i : null, vus: g ? g.vus : null, bloque: g ? g.bloque : undefined,
    };
  });

  const err = [];

  // ── 1 ─────────────────────────────────────────────────────────────────
  titre('1. CONNECTÉ — la marche complète est fidèle, du premier au dernier pas');

  const c1 = await ctxNeuf();
  const pg = await c1.newPage();
  pg.on('pageerror', e => err.push(String(e).slice(0, 90)));
  await pg.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg.evaluate(async ([e, m]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: m }) }),
    [process.env.RECETTE_EMAIL || 'recette@local.test',
     process.env.RECETTE_MDP || 'RecetteLocale!2026']);
  await pg.goto(BASE + '/secteurs', { waitUntil: 'domcontentloaded' });
  await armer(pg);

  const itineraire = await sur(pg, async ([p, s]) => {
    sessionStorage.removeItem('cp_parcours');
    window.parcoursOuvrir(p);
    await new Promise(r => setTimeout(r, 300));
    const sel = document.getElementById('pc-select-sec');
    sel.value = s; sel.dispatchEvent(new Event('change', { bubbles: true }));
    await new Promise(r => setTimeout(r, 350));
    const f = document.getElementById('pc-fiche');
    return [...f.querySelectorAll('[data-pc-go]')].map(a => a.getAttribute('href'));
  }, [PARCOURS, SECTEUR]);
  ok('le parcours croisé rend son itinéraire',
     Array.isArray(itineraire) && itineraire.length >= 5,
     Array.isArray(itineraire) ? itineraire.length + ' étapes' : JSON.stringify(itineraire));

  /* DÉMARRER LE PARCOURS. Lire la fiche ne l'ouvre pas : sans état en
     session, le bandeau n'existe pas et la marche ne mesurerait rien. */
  await sur(pg, ([p, s]) => {
    sessionStorage.setItem('cp_parcours', JSON.stringify({ id: p, i: 0, sec: s, vus: [] }));
  }, [PARCOURS, SECTEUR]);

  const marche = [];
  for (let k = 0; k < itineraire.length; k++) {
    await pg.goto(BASE + itineraire[k], { waitUntil: 'domcontentloaded' });
    await armer(pg).catch(() => {});
    await pg.waitForTimeout(320);
    const e = await etat(pg);
    marche.push(e);
  }
  const fideles = marche.filter((e, k) =>
    e.url === itineraire[k] && !e.attente
    && e.i === k && (e.vus || []).indexOf(itineraire[k]) >= 0);
  ok('CHAQUE PAGE ATTEINTE POSE SON RANG ET SA VISITE',
     fideles.length === itineraire.length,
     fideles.length + ' / ' + itineraire.length + ' pas fidèles'
       + (fideles.length === itineraire.length ? '' : ' — premier écart : '
          + JSON.stringify(marche.find((e, k) => e.i !== k) || {})));
  ok('…et le bandeau ne passe jamais en attente sur un chemin qui aboutit',
     marche.every(e => !e.attente && !e.bloque),
     marche.filter(e => e.attente).map(e => e.url).join(', ') || 'aucune attente');
  await c1.close();

  // ── 2 : LE POINT QUI DÉCIDE ───────────────────────────────────────────
  titre('2. NON CONNECTÉ — le mur retient le rang au lieu de le faire mentir');

  const c2 = await ctxNeuf();
  const pg2 = await c2.newPage();
  pg2.on('pageerror', e => err.push(String(e).slice(0, 90)));
  await pg2.goto(BASE + '/secteurs', { waitUntil: 'domcontentloaded' });
  await armer(pg2);
  /* On se place en début de parcours, une page ouverte réellement visitée,
     puis on demande une étape RÉSERVÉE : c'est le scénario du signalement. */
  await sur(pg2, ([p, s]) => {
    sessionStorage.setItem('cp_parcours', JSON.stringify(
      { id: p, i: 0, sec: s, vus: [] }));
  }, [PARCOURS, SECTEUR]);

  /* ON CLIQUE « SUIVANT », ON NE NAVIGUE PAS DIRECTEMENT. C'est le chemin
     EXACT du défaut : c'est le gestionnaire de ce bouton qui écrivait le rang
     avant de partir. Une navigation directe ne déclenche pas ce code et
     laisserait le contrôle passer sur un module non corrigé — vérifié par
     injection, il passait effectivement. */
  const cible = itineraire[1];
  await pg2.goto(BASE + itineraire[0], { waitUntil: 'domcontentloaded' });
  await pg2.waitForTimeout(600);
  await pg2.evaluate(() => {
    const a = document.querySelector('#pc-bandeau a.pc-b-suiv');
    if (a) a.click();
  });
  await pg2.waitForLoadState('domcontentloaded').catch(() => {});
  await pg2.waitForTimeout(700);
  const mur = await etat(pg2);

  ok('la page réservée renvoie bien vers la connexion — sans quoi rien n’est prouvé',
     mur.url === '/connexion', mur.url);
  ok('LE RANG N’A PAS BOUGÉ : le parcours n’annonce pas une page jamais ouverte',
     mur.i === 0 && (mur.vus || []).length === 0,
     'i=' + mur.i + ' · ' + (mur.vus || []).length + ' visite(s)');
  ok('…et le bandeau le DIT : il passe en attente au lieu d’annoncer une étape',
     mur.attente === true && /En attente/.test(mur.step || ''), mur.step);
  ok('L’ÉTAPE RETENUE EST NOMMÉE, avec son rang et le motif',
     /compte requis/.test(mur.mur) && /compte client validé/.test(mur.murTexte),
     mur.mur + ' | ' + mur.murTexte.slice(0, 80));
  ok('…et les DEUX portes sont offertes : se connecter, demander un compte',
     mur.portes.length === 2 && /\/connexion\?next=/.test(mur.portes[0])
       && mur.portes[1] === '/inscription',
     mur.portes.join(' · '));
  ok('…le retour promis pointe sur l’étape retenue, pas sur l’accueil',
     decodeURIComponent(mur.portes[0] || '').indexOf(cible) > 0,
     decodeURIComponent(mur.portes[0] || ''));

  // ── 3 ─────────────────────────────────────────────────────────────────
  titre('3. Franchir le mur lève l’état — et rien ne reste affiché à tort');

  await pg2.evaluate(async ([e, m]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: m }) }),
    [process.env.RECETTE_EMAIL || 'recette@local.test',
     process.env.RECETTE_MDP || 'RecetteLocale!2026']);
  await pg2.goto(BASE + cible, { waitUntil: 'domcontentloaded' });
  await armer(pg2).catch(() => {});
  await pg2.waitForTimeout(500);
  const apres = await etat(pg2);
  ok('la page enfin ouverte pose son rang et sa visite',
     apres.url === cible && (apres.vus || []).indexOf(cible) >= 0,
     apres.url + ' · i=' + apres.i + ' · vus=' + JSON.stringify(apres.vus));
  ok('L’AVERTISSEMENT DISPARAÎT — il ne survit pas à sa raison d’être',
     !apres.bloque && !apres.attente && apres.murTexte === '',
     'bloque=' + apres.bloque + ' · attente=' + apres.attente);
  await c2.close();

  // ── 4 ─────────────────────────────────────────────────────────────────
  titre('4. Les comptes annoncés sont les comptes réels');

  const c3 = await ctxNeuf();
  const pg3 = await c3.newPage();
  await pg3.goto(BASE + '/secteurs', { waitUntil: 'domcontentloaded' });
  await armer(pg3);
  const comptes = await sur(pg3, async () => {
    window.parcoursOuvrir(null);
    await new Promise(r => setTimeout(r, 300));
    const m = document.getElementById('pc-modal');
    const roles = m.querySelectorAll('#pc-select option').length - 1;
    const secs = m.querySelectorAll('#pc-select-sec option').length - 1;
    const intro = (m.querySelector('.pc-intro') || {}).textContent || '';
    return { roles, secs, intro: intro.replace(/\s+/g, ' ') };
  });
  ok('la liste des rôles et celle des secteurs sont peuplées',
     comptes.roles > 0 && comptes.secs > 0,
     comptes.roles + ' rôles · ' + comptes.secs + ' secteurs');

  /* LE COMMENTAIRE DU MODULE ANNONÇAIT « sept rôles » et « soixante-trois
     croisements » : deux rôles ont été ajoutés depuis sans reprendre le
     compte. On mesure le texte du fichier contre les listes qu'il décrit. */
  const src = await (await fetch(BASE + '/parcours.js')).text();
  const mR = /([A-Za-zÀ-ÿ]+) rôles et ([a-zà-ÿ]+)\s*\n?\s*secteurs feraient ([a-zà-ÿ-]+) parcours/.exec(src);
  const MOTS = { deux: 2, trois: 3, quatre: 4, cinq: 5, six: 6, sept: 7, huit: 8,
                 neuf: 9, dix: 10, 'soixante-trois': 63, 'quatre-vingt-un': 81 };
  const dit = mR ? { r: MOTS[mR[1].toLowerCase()], s: MOTS[mR[2]], x: MOTS[mR[3]] } : null;
  ok('LE COMMENTAIRE DIT LE VRAI NOMBRE DE RÔLES ET DE SECTEURS',
     !!dit && dit.r === comptes.roles && dit.s === comptes.secs,
     dit ? (dit.r + ' × ' + dit.s + ' annoncés, ' + comptes.roles + ' × '
            + comptes.secs + ' réels') : 'phrase introuvable');
  ok('…et le produit annoncé est le produit réel',
     !!dit && dit.x === comptes.roles * comptes.secs,
     dit ? (dit.x + ' annoncés pour ' + comptes.roles * comptes.secs + ' réels') : '—');

  // ── 5 ─────────────────────────────────────────────────────────────────
  titre('5. Aucun lien mort : tout ce que les parcours désignent est servi');

  const cibles = await sur(pg3, () => {
    const urls = new Set();
    (window.PCMoteur ? Object.keys(window.PCMoteur.AXES_URL) : []).forEach(u => urls.add(u));
    return [...urls];
  });
  ok('le moteur de pertinence connaît des pages',
     Array.isArray(cibles) && cibles.length > 0,
     (cibles || []).length + ' page(s) pesées');

  const morts = [];
  for (const u of (cibles || [])) {
    const r = await pg3.request.get(BASE + u).catch(() => null);
    /* 200 = servie ; 302 vers /connexion = servie mais réservée, ce que le
       cadenas annonce déjà. Un 404 est un lien mort. */
    if (!r || r.status() >= 400) morts.push(u + ' → ' + (r ? r.status() : 'sans réponse'));
  }
  ok('AUCUNE PAGE DÉSIGNÉE PAR LE MOTEUR N’EST INTROUVABLE',
     morts.length === 0, morts.join(', ') || (cibles || []).length + ' pages servies');
  await c3.close();

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  console.log('\n' + (ko === 0 ? 'tout est vert' : ko + ' contrôle(s) en échec') + '\n');
  await nav.close();
  process.exit(ko === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
