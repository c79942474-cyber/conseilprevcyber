/* LA SESSION QUI S'ÉTEINT SUR /ingenierie-datacenter — la page doit LE DIRE.
 *
 * LE DÉFAUT QUE CE CONTRÔLE FIGE. Toutes les commandes de la page passent par
 * des API réservées. Quand la session expirait, chaque zone habillait le 401
 * de son message générique — « le parcours n'a pas pu être établi », « dossier
 * indisponible » — pendant que la frise soutenait qu'il manquait la puissance
 * QUE LE LECTEUR VENAIT DE SAISIR. À partir de la section 4, plus rien ne
 * s'affichait, et rien ne disait ni pourquoi ni quoi faire ; « réessayez dans
 * un instant » était même un conseil faux, se reconnecter étant le seul
 * remède. C'est le signalement d'origine : « à partir de 4, on ne voit plus
 * rien s'afficher ».
 *
 * CE QUI EST ÉPROUVÉ, DANS L'ORDRE :
 *   1. connecté, la page rend TOUT — le contrôle ne vaut que si le cas nominal
 *      tient ;
 *   2. la session meurt (cookie effacé), le lecteur agit : une bannière nomme
 *      la cause, reste collée à l'écran, et offre la reconnexion qui RAMÈNE
 *      ICI ;
 *   3. les zones qui mentaient disent désormais la même chose que la bannière ;
 *   4. le chiffrage MOE, section 6, nomme la session plutôt que
 *      « chiffrage indisponible » ;
 *   5. la reconnexion ramène sur la page, qui refonctionne.
 *
 *   POUR L'EXÉCUTER :  BASE=http://127.0.0.1:5404 node recette_session_ingenierie.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
const COMPTE = { email: 'recette@local.test', password: 'RecetteLocale!2026' };
let ko = 0;
const ok = (n, c, d) => {
  console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : ''));
  if (!c) ko++;
};
const titre = t => console.log('\n══ ' + t + ' ══\n');

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1400, height: 1000 } });
  await ctx.route('**/*', r =>
    (['image', 'font', 'media'].includes(r.request().resourceType())
      ? r.abort() : r.continue()));
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e).slice(0, 200)));

  const connecter = () => pg.evaluate(c =>
    fetch('/api/auth/login', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(c) }).then(r => r.json()), COMPTE);

  await pg.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
  await connecter();
  await pg.goto(BASE + '/ingenierie-datacenter', { waitUntil: 'domcontentloaded' });
  await pg.waitForSelector('#ig-form [data-champ="puissance_it_kw"]', { timeout: 25000 });
  await pg.waitForTimeout(1500);

  titre('1. Connecté, la page rend tout — sans quoi la suite ne prouve rien');

  await pg.evaluate(() => {
    const i = document.querySelector('#ig-form [data-champ="puissance_it_kw"]');
    i.value = '1200';
    i.dispatchEvent(new Event('input', { bubbles: true }));
    i.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await pg.waitForSelector('#ig-parcours [data-phase]', { timeout: 25000 });
  await pg.click('#ig-parcours [data-phase]');
  await pg.waitForFunction(() =>
    ((document.getElementById('ig-dossier') || {}).innerText || '').length > 800,
    null, { timeout: 30000 });
  const avant = await pg.evaluate(() => ({
    dossier: (document.getElementById('ig-dossier').innerText || '').length,
    banniere: !!document.getElementById('ig-session'),
  }));
  ok('l’étude de la phase retenue s’affiche', avant.dossier > 800,
     avant.dossier + ' caractères');
  ok('…et aucune bannière de session ne s’affiche à tort', !avant.banniere);
  /* Le geste d'écoconception de la phase, VISIBLE sur la fiche : servi avec
     le dossier (ISO/TR 14062 art. 8, ISO 14006), il donne à chaque phase le
     management de ses produits de construction — geste, preuve, clause. */
  const eco = await pg.evaluate(() => {
    const t = (document.getElementById('ig-dossier').innerText || '').replace(/\s+/g, ' ');
    return {
      titre: /Écoconception de la phase/i.test(t),
      preuve: /Preuve\s?:/.test(t),
      clause: /ISO\/TR 14062, art\. 8\.3\.\d/.test(t),
    };
  });
  ok('LA FICHE PORTE LE GESTE D’ÉCOCONCEPTION DE LA PHASE — preuve et clause',
     eco.titre && eco.preuve && eco.clause,
     'titre: ' + eco.titre + ', preuve: ' + eco.preuve + ', clause 14062: ' + eco.clause);

  titre('2. LA SESSION MEURT — la page le dit, au lieu de se taire');

  await ctx.clearCookies();
  /* Le lecteur agit : il retouche la puissance. Avant la correction, la frise
     répondait « il manque la puissance » — celle qu'il venait de saisir. */
  await pg.evaluate(() => {
    const i = document.querySelector('#ig-form [data-champ="puissance_it_kw"]');
    i.value = '1300';
    i.dispatchEvent(new Event('input', { bubbles: true }));
    i.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await pg.waitForSelector('#ig-session', { timeout: 20000 });
  const mort = await pg.evaluate(() => {
    const b = document.getElementById('ig-session');
    const z = id => (document.getElementById(id) || {}).innerText || '';
    return {
      role: b.getAttribute('role'),
      colle: getComputedStyle(b).position,
      texte: (b.innerText || '').replace(/\s+/g, ' '),
      lien: (b.querySelector('a[href^="/connexion"]') || {}).getAttribute
        ? b.querySelector('a[href^="/connexion"]').getAttribute('href') : null,
      parcours: z('ig-parcours').replace(/\s+/g, ' '),
      dossier: z('ig-dossier').replace(/\s+/g, ' '),
      etat: z('ig-etat').trim(),
    };
  });
  ok('UNE BANNIÈRE NOMME LA CAUSE', /session n’est plus active/i.test(mort.texte),
     mort.texte.slice(0, 60) + '…');
  ok('…en role="alert", pour être annoncée aux lecteurs d’écran',
     mort.role === 'alert');
  ok('…collée à l’écran pendant qu’on défile', mort.colle === 'sticky');
  ok('…avec la reconnexion QUI RAMÈNE ICI',
     mort.lien === '/connexion?next=/ingenierie-datacenter', mort.lien);

  titre('3. Les zones qui MENTAIENT disent la même chose que la bannière');

  ok('la frise ne réclame plus une puissance déjà saisie',
     !/il manque la puissance/i.test(mort.parcours), mort.parcours.slice(0, 56));
  ok('…elle nomme la session', /session/i.test(mort.parcours));
  ok('le bloc d’étude (section 4) nomme la session aussi',
     /session/i.test(mort.dossier), mort.dossier.slice(0, 56));
  ok('et plus de « réessayez dans un instant » — un conseil faux',
     !/réessayez dans un instant/i.test(mort.etat), mort.etat || '(vide)');

  titre('4. Le chiffrage MOE nomme la session, pas une panne de barème');

  await pg.evaluate(() => {
    const t = document.getElementById('ig-moe-trav');
    if (t) t.value = '600-750';
    document.getElementById('ig-moe-go').click();
  });
  await pg.waitForFunction(() =>
    /session/i.test((document.getElementById('ig-moe-msg') || {}).textContent || ''),
    null, { timeout: 15000 });
  const moe = await pg.evaluate(() => ({
    msg: (document.getElementById('ig-moe-msg').textContent || '').trim(),
    lien: !!document.querySelector('#ig-moe-msg a[href^="/connexion"]'),
  }));
  ok('le message nomme la session', /session n’est plus active/i.test(moe.msg),
     moe.msg.slice(0, 60));
  ok('…et porte le lien de reconnexion', moe.lien);
  ok('…sans accuser le barème', !/chiffrage indisponible/i.test(moe.msg));

  titre('5. La reconnexion ramène sur la page, et elle refonctionne');

  await connecter();
  await pg.goto(BASE + '/ingenierie-datacenter', { waitUntil: 'domcontentloaded' });
  await pg.waitForSelector('#ig-form [data-champ="puissance_it_kw"]', { timeout: 25000 });
  await pg.evaluate(() => {
    const i = document.querySelector('#ig-form [data-champ="puissance_it_kw"]');
    i.value = '1200';
    i.dispatchEvent(new Event('input', { bubbles: true }));
    i.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await pg.waitForSelector('#ig-parcours [data-phase]', { timeout: 25000 });
  const retour = await pg.evaluate(() => ({
    phases: document.querySelectorAll('#ig-parcours [data-phase]').length,
    banniere: !!document.getElementById('ig-session'),
  }));
  ok('la frise revient', retour.phases >= 5, retour.phases + ' phase(s)');
  ok('…sans bannière résiduelle', !retour.banniere);

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  await nav.close();
  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  process.exit(ko ? 1 : 0);
})();
