/* LA POLITIQUE D'ACCÈS — ce que seul le vrai navigateur peut prouver.
 *
 * Le matériau est éprouvé par tests/test_acces.py : les portes, les
 * interfaces, le parcours d'inscription. Ce qu'un test qui lit le source NE
 * PEUT PAS voir, et qui est ici :
 *
 *   · que le cadenas APPARAÎT RÉELLEMENT sur les liens réservés — le marquage
 *     est posé par nav.js après le tiroir, et une erreur d'ordre le laisserait
 *     absent des trente entrées du menu, c'est-à-dire de celles que la
 *     politique concerne. Rien de cela ne se voit dans un fichier ;
 *   · qu'un CLIENT CONNECTÉ n'en voit AUCUN : ces pages lui sont ouvertes, et
 *     les lui signaler comme réservées serait faux ;
 *   · que la légende du pied de page paraît quand, et seulement quand, il y a
 *     quelque chose à expliquer ;
 *   · qu'un clic anonyme sur un lien réservé mène au formulaire de connexion,
 *     et qu'il y revient avec le paramètre « next » — sans lui, le visiteur se
 *     connecte et atterrit ailleurs que là où il allait.
 *
 * La leçon est acquise dans ce dépôt : j'ai désactivé une branche d'affichage
 * avec « if (false) » et le test Python est resté vert, parce que les chaînes
 * étaient toujours dans le fichier. Ce qui s'affiche se vérifie dans le
 * document.
 *
 *   POUR L'EXÉCUTER :  BASE=http://127.0.0.1:5404 node recette_acces.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
const EMAIL = process.env.RECETTE_EMAIL || 'recette@local.test';
const MDP = process.env.RECETTE_MDP || 'RecetteLocale!2026';
let ko = 0;
const ok = (n, c, d) => {
  console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : ''));
  if (!c) ko++;
};
const titre = t => console.log('\n══ ' + t + ' ══\n');

/* Les dix pages du menu en accès direct. */
const OUVERTES = ['/', '/services', '/secteurs', '/etudes-de-cas', '/veille',
                  '/ressources', '/faq', '/about', '/vos-projets', '/contact'];
/* Ouvertes hors menu, et légitimement déclarées au plan du site : les pages
   légales. Les avoir oubliées de cette liste faisait échouer un contrôle sur
   trois adresses parfaitement en règle — la liste était fausse, pas le site. */
const OUVERTES_HORS_MENU = ['/mentions-legales', '/politique-confidentialite',
                            '/conformite'];

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1280, height: 900 } });
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e)));

  titre('1. Les dix pages en accès direct s’ouvrent sans compte');

  for (const c of OUVERTES) {
    const r = await pg.goto(BASE + c, { waitUntil: 'domcontentloaded' });
    const arrivee = new URL(pg.url()).pathname;
    ok(c + ' s’ouvre', r.status() < 400 && arrivee === c,
       'HTTP ' + r.status() + ' sur ' + arrivee);
  }

  titre('2. LE POINT QUI DÉCIDE : le cadenas paraît là où il doit');

  await pg.goto(BASE + '/', { waitUntil: 'networkidle' });
  /* ATTENDRE SANS LEVER. J'avais mis un waitForSelector nu : en vidant la
     liste servie par /api/acces, la recette est morte sur une exception de
     Playwright au lieu d'annoncer « aucun cadenas ». Une recette qui plante
     apprend moins qu'une recette qui nomme ce qui manque — et elle laisse
     croire à une panne d'outillage plutôt qu'à un défaut du site. */
  await pg.waitForSelector('.ac-cle', { timeout: 15000 }).catch(() => {});
  const m = await pg.evaluate(() => {
    const liens = [...document.querySelectorAll('a[href^="/"]')];
    const marques = liens.filter(a => a.querySelector('.ac-cle'));
    const dits = liens.filter(a => /accès client/i.test(a.textContent));
    /* Un lien ouvert marqué par erreur est une faute symétrique : il
       découragerait de cliquer sur ce qui est libre. */
    const OUV = ['/', '/services', '/secteurs', '/etudes-de-cas', '/veille',
                 '/ressources', '/faq', '/about', '/vos-projets', '/contact',
                 '/inscription', '/connexion', '/mentions-legales',
                 '/politique-confidentialite', '/conformite'];
    const faussement = marques
      .map(a => a.getAttribute('href').split('#')[0].split('?')[0])
      .filter(h => OUV.indexOf(h) >= 0);
    return { total: liens.length, marques: marques.length, dits: dits.length,
             faussement: [...new Set(faussement)],
             legende: !!document.querySelector('.ac-legende'),
             lgTexte: (document.querySelector('.ac-legende') || {}).textContent || '' };
  });
  ok('des liens réservés portent le cadenas', m.marques >= 15,
     m.marques + ' cadenas sur ' + m.total + ' liens internes');
  ok('…et AUCUNE page ouverte n’en porte', m.faussement.length === 0,
     m.faussement.join(', ') || 'aucune');
  ok('les liens mis en avant le disent en toutes lettres', m.dits >= 5,
     m.dits + ' libellé(s) « accès client »');
  ok('la légende explique le symbole', m.legende && /compte client/.test(m.lgTexte),
     m.lgTexte.slice(0, 70).replace(/\s+/g, ' '));
  ok('…et elle conduit à la création d’un accès',
     /\/inscription/.test(await pg.evaluate(
       () => (document.querySelector('.ac-legende') || {}).innerHTML || '')),
     'lien /inscription dans la légende');

  titre('3. Le TIROIR aussi — ce sont les pages que la politique vise');

  await pg.evaluate(() => {
    const b = document.querySelector('.burger, [aria-controls="drawer"], .nav-burger');
    if (b) b.click();
  });
  await pg.waitForTimeout(500);
  const tir = await pg.evaluate(() => {
    const d = document.querySelector('#drawer, .drawer');
    if (!d) return null;
    const liens = [...d.querySelectorAll('a[href^="/"]')];
    return { n: liens.length,
             marques: liens.filter(a => a.querySelector('.ac-cle')).length };
  });
  ok('le menu latéral existe et porte ses entrées', tir && tir.n >= 30,
     tir ? tir.n + ' entrée(s)' : 'tiroir introuvable');
  ok('…et ses pages réservées portent le cadenas', tir && tir.marques >= 25,
     tir ? tir.marques + ' marquée(s) sur ' + tir.n : '—');

  titre('4. Un clic anonyme mène à la connexion — et revient au bon endroit');

  await pg.goto(BASE + '/datacenter', { waitUntil: 'domcontentloaded' });
  const u = new URL(pg.url());
  ok('une page réservée renvoie au formulaire', u.pathname === '/connexion',
     u.pathname);
  ok('…en gardant la destination', u.searchParams.get('next') === '/datacenter',
     'next=' + u.searchParams.get('next'));

  /* L'interface aussi : c'est elle qui protège vraiment le contenu. */
  const api = await pg.evaluate(async () => {
    const r = await fetch('/api/datacenter/etat-art');
    return { s: r.status, t: (await r.text()).slice(0, 60) };
  });
  ok('L’INTERFACE AUSSI refuse — fermer la page seule ne protégerait rien',
     api.s === 401, 'HTTP ' + api.s);

  titre('5. Le client CONNECTÉ ne voit aucun cadenas, et les pages s’ouvrent');

  const ctx2 = await nav.newContext({ viewport: { width: 1280, height: 900 } });
  const pg2 = await ctx2.newPage();
  pg2.on('pageerror', e => err.push('connecté: ' + e));
  await pg2.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg2.evaluate(async ([e, p]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: p }) }), [EMAIL, MDP]);

  const r2 = await pg2.goto(BASE + '/datacenter', { waitUntil: 'networkidle' });
  ok('la page réservée s’ouvre',
     r2.status() < 400 && new URL(pg2.url()).pathname === '/datacenter',
     'HTTP ' + r2.status() + ' sur ' + new URL(pg2.url()).pathname);

  await pg2.goto(BASE + '/', { waitUntil: 'networkidle' });
  await pg2.waitForTimeout(1200);
  const c2 = await pg2.evaluate(() => ({
    cadenas: document.querySelectorAll('.ac-cle').length,
    legende: !!document.querySelector('.ac-legende'),
  }));
  ok('AUCUN cadenas pour lui : ces pages lui sont ouvertes', c2.cadenas === 0,
     c2.cadenas + ' cadenas');
  ok('…ni la légende qui les explique', !c2.legende, c2.legende ? 'présente' : 'absente');
  await ctx2.close();

  titre('6. Le plan du site ne déclare que ce qu’un moteur peut lire');

  const plan = await pg.evaluate(async () => {
    const t = await (await fetch('/sitemap.xml')).text();
    return [...t.matchAll(/<loc>([^<]+)<\/loc>/g)].map(x => new URL(x[1]).pathname);
  });
  const OUV = new Set([...OUVERTES, ...OUVERTES_HORS_MENU]);
  const intrus = plan.filter(p => !OUV.has(p.replace(/\/$/, '') || '/'));
  ok('le plan n’est pas vide', plan.length > 0, plan.length + ' adresse(s)');
  ok('…et aucune adresse déclarée ne mène à un formulaire de connexion',
     intrus.length === 0, intrus.join(', ') || 'aucune');

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  await nav.close();
  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  process.exit(ko ? 1 : 0);
})();
