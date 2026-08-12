/* LE CADENAS DES PARCOURS GUIDÉS, VU DEPUIS LE NAVIGATEUR.
 *
 * CE QUE LES TESTS PYTHON NE PEUVENT PAS DIRE. Ils comparent la liste écrite
 * dans parcours.js à la politique d'acces.py, et c'est déjà l'essentiel : le
 * défaut livré — neuf pages fermées annoncées libres — s'y voit. Mais ils ne
 * voient ni la modale, ni le bandeau, ni ce que le serveur répond vraiment.
 *
 * DEUX CHOSES NE SE PROUVENT QU'ICI :
 *   1. le cadenas s'affiche pour de bon sur les étapes fermées — une liste
 *      juste et un rendu qui l'ignore donneraient exactement le défaut d'hier ;
 *   2. UN CLIENT CONNECTÉ N'EN VOIT AUCUN. Rien dans le fichier ne le prouve :
 *      la liste écrite en dur les afficherait tous. Seul le rafraîchissement
 *      auprès du serveur les fait disparaître, et il ne se voit qu'à l'exécution.
 *
 * CE QUE CETTE RECETTE NE PEUT PAS VOIR, ET IL FAUT LE DIRE. Depuis que la
 * liste est rafraîchie auprès du serveur avant le premier affichage, une
 * dérive de la liste ÉCRITE dans parcours.js n'apparaît plus ici : on l'a
 * vérifié en la cassant, la recette est restée verte. Ce n'est pas un trou de
 * couverture, c'est un partage : la liste écrite sert au tout premier rendu —
 * le temps que le réseau réponde, et s'il ne répond pas — et c'est
 * tests/test_parcours_a_jour.py qui la compare à acces.py. Ici on éprouve le
 * RENDU ; là-bas, la liste. Chacun tombe sur son propre défaut, et on l'a
 * montré des deux côtés en les injectant.
 *
 *   POUR L'EXÉCUTER :
 *     BASE=http://127.0.0.1:5404 node recette_parcours.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
const MAIL = process.env.MAIL || 'recette@local.test';
const MDP = process.env.MDP || 'RecetteLocale!2026';
let ko = 0;
const ok = (n, c, d) => {
  console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : ''));
  if (!c) ko++;
};
const titre = t => console.log('\n══ ' + t + ' ══\n');

/* Ouvre la modale et rend l'état de chaque étape du parcours demandé. */
async function fiche(pg, role) {
  await pg.evaluate(() => window.parcoursOuvrir());
  await pg.waitForSelector('#pc-select', { timeout: 15000 });
  await pg.selectOption('#pc-select', role);
  await pg.waitForSelector('#pc-fiche .pc-etape', { timeout: 15000 });
  return pg.evaluate(() => [...document.querySelectorAll('#pc-fiche .pc-etape')]
    .map(e => ({
      url: e.querySelector('.pc-go').getAttribute('href'),
      cadenas: !!e.querySelector('.pc-cle'),
    })));
}

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1400, height: 1000 } });
  await ctx.route('**/*', r => (['image', 'font', 'media'].includes(r.request().resourceType())
    ? r.abort() : r.continue()));
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e)));

  titre('1. Le visiteur sans compte — le RENDU suit ce que le serveur dit');

  /* /secteurs est en accès direct : c'est là qu'un visiteur non connecté peut
     réellement ouvrir un parcours. Le prendre sur une page fermée testerait le
     formulaire de connexion, pas la modale. */
  await pg.goto(BASE + '/secteurs', { waitUntil: 'domcontentloaded' });
  await pg.waitForFunction(() => typeof window.parcoursOuvrir === 'function',
    null, { timeout: 20000 });

  /* La vérité de référence vient du serveur, pas d'une liste recopiée ici :
     une recette qui porterait sa propre copie de la politique reproduirait
     exactement la faute qu'elle traque. */
  const politique = await pg.evaluate(() =>
    fetch('/api/acces').then(r => r.json()).then(j => j.client));
  ok('le serveur sait quelles pages sont fermées',
     Array.isArray(politique) && politique.length > 10, politique.length + ' pages');

  let faux = [];
  for (const role of ['rssi', 'ot', 'projet', 'achats', 'direction',
                      'conformite', 'dc-projet', 'dc-durabilite', 'decouverte']) {
    const et = await fiche(pg, role);
    et.forEach(e => {
      const doit = politique.indexOf(e.url) >= 0;
      if (e.cadenas !== doit) {
        faux.push(role + ' · ' + e.url + (doit ? ' : fermée, AUCUN cadenas'
                                               : ' : ouverte, cadenas de trop'));
      }
    });
  }
  ok('CHAQUE ÉTAPE FERMÉE PORTE SON CADENAS, et aucune ouverte n’en porte',
     faux.length === 0, faux.slice(0, 4).join(' | '));

  const intro = await pg.evaluate(() =>
    (document.querySelector('.pc-intro') || {}).innerText || '');
  ok('…et la modale dit comment obtenir un compte',
     /créer un/i.test(intro) && intro.indexOf('validé') > 0);

  titre('2. « Première visite » montre quelque chose AVANT le mur');

  const dec = await fiche(pg, 'decouverte');
  ok('les deux premières étapes sont ouvertes',
     !dec[0].cadenas && !dec[1].cadenas,
     dec.map(e => (e.cadenas ? '🔒' : '·') + e.url).join(' '));

  titre('3. LE POINT QUI DÉCIDE : un client connecté ne voit aucun cadenas');

  /* Rien dans le fichier ne le prouve : la liste écrite en dur les afficherait
     tous. C'est le rafraîchissement auprès du serveur qui les retire — et il
     ne se constate qu'ici.

     CONTEXTE SÉPARÉ, et ce n'est pas de la propreté gratuite : les onglets d'un
     même contexte PARTAGENT les cookies. Ouvrir la session ici connectait aussi
     le « visiteur sans compte » des sections précédentes, et le contrôle du
     bandeau tombait plus bas — sur un défaut que le site n'avait pas. Une
     recette qui se contamine elle-même accuse à tort, ce qui est pire que de
     ne rien voir. */
  const ctx2 = await nav.newContext({ viewport: { width: 1400, height: 1000 } });
  await ctx2.route('**/*', r => (['image', 'font', 'media'].includes(r.request().resourceType())
    ? r.abort() : r.continue()));
  const pg2 = await ctx2.newPage();
  pg2.on('pageerror', e => err.push('[connecté] ' + String(e)));
  await pg2.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  const connecte = await pg2.evaluate(async (c) => {
    const r = await fetch('/api/auth/login', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: c.m, password: c.p }) });
    return r.ok;
  }, { m: MAIL, p: MDP });
  ok('le compte de recette ouvre bien une session', connecte);

  /* Sur une page RÉSERVÉE, cette fois : c'est là que vit un client. */
  await pg2.goto(BASE + '/referentiel', { waitUntil: 'domcontentloaded' });
  await pg2.waitForFunction(() => typeof window.parcoursOuvrir === 'function',
    null, { timeout: 20000 });
  /* Le retrait des cadenas suit une réponse réseau : on attend l'effet, sans
     lever si elle n'arrive pas — un échec doit être NOMMÉ, pas confondu avec
     une panne de l'outil. */
  await pg2.evaluate(() => window.parcoursOuvrir());
  await pg2.selectOption('#pc-select', 'ot');
  const nu = await pg2.waitForFunction(
    () => document.querySelectorAll('#pc-fiche .pc-etape').length > 0
       && document.querySelectorAll('#pc-fiche .pc-cle').length === 0,
    null, { timeout: 15000 }).then(() => true).catch(() => false);
  const restants = await pg2.evaluate(() =>
    [...document.querySelectorAll('#pc-fiche .pc-etape')]
      .filter(e => e.querySelector('.pc-cle'))
      .map(e => e.querySelector('.pc-go').getAttribute('href')));
  /* Le détail n'est affiché qu'en cas d'échec : le calculer dans tous les cas
     collait « la synchronisation n’a jamais abouti » à côté d'un OK. */
  ok('AUCUN CADENAS pour qui a un compte : rien ne lui est fermé', nu,
     nu ? '' : (restants.length ? 'restent : ' + restants.join(', ')
                                : 'la synchronisation n’a jamais abouti'));

  titre('4. Le bandeau de continuité annonce le mur du « Suivant »');

  await pg.evaluate(() => window.parcoursOuvrir());
  await pg.selectOption('#pc-select', 'decouverte');
  await pg.waitForSelector('#pc-fiche .pc-etape', { timeout: 15000 });
  await pg.evaluate(() => {
    /* On se pose à l'étape 2 : la suivante est fermée. */
    sessionStorage.setItem('cp_parcours', JSON.stringify({ id: 'decouverte', i: 1 }));
  });
  await pg.goto(BASE + '/etudes-de-cas', { waitUntil: 'domcontentloaded' });
  await pg.waitForSelector('#pc-bandeau.on', { timeout: 15000 });
  const b = await pg.evaluate(() => {
    const s = document.querySelector('#pc-bandeau .pc-b-suiv');
    return { texte: s ? s.textContent.trim() : '', href: s ? s.getAttribute('href') : '' };
  });
  ok('le « Suivant » vers une page fermée porte le cadenas',
     b.href === '/referentiel' && b.texte.indexOf('🔒') >= 0, b.texte);

  ok('aucune erreur de script', err.length === 0, err.slice(0, 2).join(' | '));

  await nav.close();
  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  process.exit(ko ? 1 : 0);
})();
