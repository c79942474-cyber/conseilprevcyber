/* La page de connexion — ce qu'elle doit répondre, et à quoi.
 *
 * LE CONTEXTE. Le parcours serveur est sain : quatre issues, chacune avec son
 * message — identifiants refusés, email non confirmé, compte non validé,
 * base de comptes injoignable. Ce qui manquait était du côté de la PAGE.
 *
 * DEUX DÉFAUTS CORRIGÉS, ET ILS PRODUISENT LE MÊME SYMPTÔME — « la connexion ne
 * marche pas » — pour deux raisons différentes :
 *
 *   1. LE DOUBLE ESSAI INVOLONTAIRE. Le bouton restait actif pendant la
 *      requête. Sur un serveur lent à se réveiller, un second clic partait, et
 *      CHAQUE tentative compte au compteur anti-bruteforce. On se retrouvait
 *      bloqué pour « trop de tentatives » en croyant n'avoir essayé qu'une
 *      fois. Le remède n'est pas de desserrer la protection — elle est juste —
 *      mais d'empêcher le second départ.
 *
 *   2. « ERREUR RÉSEAU » POUR UNE ERREUR DE SERVEUR. `r.json()` lève sur une
 *      page d'erreur HTML — celle que renvoie l'hébergeur quand l'application
 *      redémarre. L'exception tombait dans le `catch` réseau : le visiteur
 *      lisait « erreur réseau » alors que sa connexion allait très bien, et
 *      cherchait le problème du mauvais côté. On distingue les deux, et on
 *      donne le code HTTP : il se cherche et se comprend.
 *
 * POUR L'EXÉCUTER : une instance locale sur le port 5404.
 *     BASE=http://127.0.0.1:5404 node recette_connexion.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
let ko = 0;
const ok = (n, c, d) => { console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : '')); if (!c) ko++; };

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 602, height: 480 } });
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e)));

  const etat = () => pg.evaluate(() => {
    const m = document.getElementById('msg');
    const b = document.querySelector('#f button[type=submit]');
    const mb = m.getBoundingClientRect();
    return { texte: (m.textContent || '').trim(), classe: m.className,
             boutonActif: !b.disabled, libelle: b.textContent.trim(),
             msgVisible: mb.top >= 0 && mb.height > 0 };
  });

  console.log('\n══ 1. Un refus d’identifiants se dit, et rend la main ══\n');

  await pg.goto(BASE + '/connexion', { waitUntil: 'networkidle' });
  await pg.fill('#email', 'inconnu@example.com');
  await pg.fill('#password', 'mauvais');
  await pg.click('#f button[type=submit]');
  await pg.waitForTimeout(1500);
  let e = await etat();
  ok('le refus est affiché', /Identifiants incorrects/.test(e.texte), e.texte);
  ok('…dans le ton d’erreur', /err/.test(e.classe), e.classe);
  ok('…et le message est visible sans défiler', e.msgVisible);
  // LE contrôle : on doit pouvoir réessayer.
  ok('le bouton redevient actif', e.boutonActif);
  ok('…et retrouve son libellé', e.libelle === 'Se connecter', e.libelle);

  console.log('\n══ 2. Un seul essai part, même si l’on clique deux fois ══\n');

  await pg.goto(BASE + '/connexion', { waitUntil: 'networkidle' });
  let envois = 0;
  await pg.route('**/api/auth/login', async (route) => {
    envois++;
    // On fait traîner : c'est la fenêtre pendant laquelle le second clic partait.
    await new Promise(r => setTimeout(r, 1200));
    route.fulfill({ status: 401, contentType: 'application/json',
                    body: JSON.stringify({ error: 'Identifiants incorrects.' }) });
  });
  await pg.fill('#email', 'inconnu@example.com');
  await pg.fill('#password', 'mauvais');
  await pg.click('#f button[type=submit]');
  await pg.waitForTimeout(150);
  const pendant = await etat();
  ok('pendant la requête, le bouton est désactivé', !pendant.boutonActif);
  ok('…et il le dit', /Connexion/.test(pendant.libelle), pendant.libelle);
  // Trois clics de plus, dans la fenêtre d'attente.
  for (let i = 0; i < 3; i++) {
    await pg.click('#f button[type=submit]', { force: true }).catch(() => {});
  }
  await pg.waitForTimeout(2000);
  ok('une seule tentative est partie malgré quatre clics', envois === 1,
     envois + ' requête(s)');
  ok('…et la main est rendue à la fin', (await etat()).boutonActif);

  console.log('\n══ 3. Une erreur de SERVEUR n’est pas une erreur de réseau ══\n');

  await pg.unroute('**/api/auth/login');
  await pg.route('**/api/auth/login', route =>
    route.fulfill({ status: 502, contentType: 'text/html',
                    body: '<html><body><h1>502 Bad Gateway</h1></body></html>' }));
  await pg.goto(BASE + '/connexion', { waitUntil: 'networkidle' });
  await pg.fill('#email', 'inconnu@example.com');
  await pg.fill('#password', 'mauvais');
  await pg.click('#f button[type=submit]');
  await pg.waitForTimeout(1500);
  e = await etat();
  ok('la page ne parle PAS de réseau', !/réseau/i.test(e.texte), e.texte.slice(0, 70));
  ok('…elle nomme le code HTTP', /502/.test(e.texte), e.texte.slice(0, 90));
  ok('…et dit que ce n’est pas un refus d’identifiants',
     /identifiants/i.test(e.texte), e.texte.slice(0, 110));
  ok('…tout en rendant la main', e.boutonActif);

  console.log('\n══ 4. Un serveur muet, lui, EST un problème de réseau ══\n');

  await pg.unroute('**/api/auth/login');
  await pg.route('**/api/auth/login', route => route.abort('failed'));
  await pg.goto(BASE + '/connexion', { waitUntil: 'networkidle' });
  await pg.fill('#email', 'inconnu@example.com');
  await pg.fill('#password', 'mauvais');
  await pg.click('#f button[type=submit]');
  await pg.waitForTimeout(1500);
  e = await etat();
  ok('la page dit que le serveur n’a pas répondu',
     /n’a pas répondu|n'a pas répondu/.test(e.texte), e.texte.slice(0, 70));
  ok('…et ne cite aucun code, puisqu’il n’y en a pas', !/HTTP/.test(e.texte));
  ok('…tout en rendant la main', e.boutonActif);

  console.log('\n══ 5. Ce que la correction ne devait PAS casser ══\n');

  await pg.unroute('**/api/auth/login');
  await pg.route('**/api/auth/login', route =>
    route.fulfill({ status: 200, contentType: 'application/json',
                    body: JSON.stringify({ ok: true, name: 'Essai' }) }));
  await pg.goto(BASE + '/connexion?next=/demo', { waitUntil: 'networkidle' });
  await pg.fill('#email', 'ok@example.com');
  await pg.fill('#password', 'bon');
  await pg.click('#f button[type=submit]');
  await pg.waitForTimeout(2000);
  ok('une connexion réussie conduit bien à la destination',
     /\/demo/.test(pg.url()), pg.url());

  await pg.unroute('**/api/auth/login');
  await pg.goto(BASE + '/connexion?deconnecte=1', { waitUntil: 'networkidle' });
  ok('le message de déconnexion s’affiche toujours',
     /déconnecté/.test((await etat()).texte));
  await pg.goto(BASE + '/connexion?verifie=1', { waitUntil: 'networkidle' });
  ok('…et celui de confirmation d’email aussi',
     /confirmé/.test((await etat()).texte));
  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  await nav.close();
  console.log(ko ? '\n' + ko + ' contrôle(s) en échec\n' : '\ntout est vert\n');
  process.exit(ko ? 1 : 0);
})();
