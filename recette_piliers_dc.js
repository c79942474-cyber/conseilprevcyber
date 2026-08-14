/* LES TROIS PILIERS CENTRES DE DONNÉES — l'enchaînement tient-il vraiment ?
 *
 * CE QU'ON PROTÈGE :
 *
 *   1. LE BANDEAU EST SUR LES TROIS, ET DIT LE MÊME ORDRE. Trois pages qui
 *      annonceraient trois enchaînements différents seraient pires que trois
 *      pages muettes : on ne saurait plus laquelle croire.
 *
 *   2. CHAQUE PAGE SAIT OÙ ELLE EST. Le pilier courant est désigné, et il
 *      n'est pas un lien vers lui-même — un lien qui ne mène nulle part use la
 *      confiance dans tous les autres.
 *
 *   3. LE TRIANGLE EST FERMÉ. Depuis n'importe lequel, on atteint les deux
 *      autres. C'est le défaut de départ : /ingenierie-datacenter ne renvoyait
 *      pas une seule fois vers la stratégie.
 *
 *   4. LE POINT QUI DÉCIDE — CE QUI SE TRANSMET EST CONSTATÉ, JAMAIS PROMIS.
 *      « Profil repris : 13 valeurs » ne doit s'afficher que s'il y a un
 *      profil. Un bandeau qui annonce un report qui n'a pas eu lieu fait
 *      croire à une continuité qui n'existe pas, et c'est exactement ce qu'on
 *      vient lui demander de garantir.
 *
 *   5. IL N'INVENTE PAS DE PASSAGE. La stratégie pose des questions
 *      qualitatives, la mesure attend des grandeurs : rien ne doit prétendre
 *      traduire l'une en l'autre.
 *
 *   POUR L'EXÉCUTER :  BASE=http://127.0.0.1:5404 node recette_piliers_dc.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
let ko = 0;
const ok = (n, c, d) => {
  console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : ''));
  if (!c) ko++;
};
const titre = t => console.log('\n══ ' + t + ' ══\n');

const PILIERS = ['/strategie-durable-datacenter', '/datacenter',
                 '/ingenierie-datacenter'];

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1400, height: 1000 } });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
  });
  await ctx.route('**/*', r => (['image', 'font', 'media'].includes(r.request().resourceType())
    ? r.abort() : r.continue()));
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e)));

  await pg.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg.evaluate(async ([e, m]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: m }) }),
    [process.env.RECETTE_EMAIL || 'recette@local.test',
     process.env.RECETTE_MDP || 'RecetteLocale!2026']);

  const ouvrir = async (url) => {
    await pg.goto(BASE + url, { waitUntil: 'domcontentloaded' });
    if (/\/connexion/.test(pg.url())) return 'session';
    await pg.waitForTimeout(1100);
    return 'ok';
  };

  const lire = () => pg.evaluate(() => {
    const z = document.getElementById('piliers');
    if (!z || !z.querySelector('.pdc')) return null;
    const cartes = [...z.querySelectorAll('.pdc-c')];
    return {
      n: cartes.length,
      titres: cartes.map(c => (c.querySelector('.t') || {}).textContent || ''),
      liens: cartes.map(c => c.getAttribute('href')),
      courant: cartes.findIndex(c => c.getAttribute('aria-current') === 'page'),
      courantEstUnLien: cartes.some(c =>
        c.getAttribute('aria-current') === 'page' && c.tagName === 'A'),
      etats: cartes.map(c => ((c.querySelector('.e') || {}).className || '')
        .replace('e ', '').trim()),
      fleches: z.querySelectorAll('.pdc-fl').length,
      recu: (z.querySelector('.pdc-p.recu') || {}).textContent || '',
      emporte: (z.querySelector('.pdc-p.emporte') || {}).textContent || '',
      suivant: (z.querySelector('.pdc-b') || {}).getAttribute
        ? z.querySelector('.pdc-b').getAttribute('href') : null,
      libelleSuivant: (z.querySelector('.pdc-b') || {}).textContent || '',
    };
  });

  titre('1. Le bandeau est sur les trois, et dit le même ordre');

  const vus = [];
  for (const url of PILIERS) {
    if (await ouvrir(url) === 'session') {
      ok('LE BANDEAU EST PRÉSENT SUR ' + url, false,
         'session non établie — limiteur de débit probable, relancer sur un processus NEUF');
      continue;
    }
    const v = await lire();
    ok('le bandeau est présent sur ' + url, !!v && v.n === 3,
       v ? v.n + ' pilier(s)' : 'aucun bandeau');
    if (v) vus.push({ url, v });
  }
  if (vus.length === 3) {
    /* L'ORDRE EST LE MÊME PARTOUT. Trois pages qui l'annonceraient
       différemment se contrediraient sans que rien ne le signale. */
    const ref = vus[0].v.titres.join(' | ');
    ok('LES TROIS ANNONCENT LE MÊME ENCHAÎNEMENT',
       vus.every(x => x.v.titres.join(' | ') === ref), ref);
    ok('…et les flèches disent qu’il s’agit d’un ordre, pas d’un menu',
       vus.every(x => x.v.fleches === 2), vus.map(x => x.v.fleches).join('/'));
  }

  titre('2. Chaque page sait où elle est, et le triangle est fermé');

  for (const { url, v } of vus) {
    const rang = PILIERS.indexOf(url);
    ok('le pilier courant est désigné sur ' + url, v.courant === rang,
       'désigné : ' + v.courant + ', attendu : ' + rang);
    /* PAS DE LIEN VERS SOI-MÊME : un lien qui ne mène nulle part use la
       confiance dans tous les autres liens de la page. */
    ok('…et il ne se lie pas à lui-même', !v.courantEstUnLien);
    const ailleurs = v.liens.filter(Boolean);
    ok('…les DEUX autres piliers sont atteignables depuis lui',
       ailleurs.length === 2
         && PILIERS.filter(p => p !== url).every(p => ailleurs.indexOf(p) >= 0),
       ailleurs.join(' '));
  }
  /* LE DÉFAUT DE DÉPART, NOMMÉ : l'ingénierie ne renvoyait nulle part vers la
     stratégie. C'est l'arête qui manquait au triangle. */
  const ing = vus.find(x => x.url === '/ingenierie-datacenter');
  if (ing) {
    ok('L’INGÉNIERIE RENVOIE ENFIN VERS LA STRATÉGIE',
       ing.v.liens.indexOf('/strategie-durable-datacenter') >= 0,
       ing.v.liens.filter(Boolean).join(' '));
  }

  titre('3. LE POINT QUI DÉCIDE : ce qui se transmet est CONSTATÉ');

  /* Sur une session neuve, rien n'a été saisi : le bandeau ne doit annoncer
     AUCUN report. C'est le sens du contrôle — un bandeau qui promet un profil
     inexistant fait croire à une continuité qui n'a pas eu lieu. */
  const neuf = await ctx.newPage();
  await neuf.goto(BASE + '/datacenter', { waitUntil: 'domcontentloaded' });
  await neuf.waitForTimeout(1200);
  const vide = await neuf.evaluate(() => {
    const z = document.getElementById('piliers');
    return z ? {
      recu: !!z.querySelector('.pdc-p.recu'),
      emporte: !!z.querySelector('.pdc-p.emporte'),
      etats: [...z.querySelectorAll('.pdc-c .e')].map(e => e.textContent.trim()),
    } : null;
  });
  ok('AUCUN REPORT N’EST ANNONCÉ quand rien n’a été saisi',
     !!vide && !vide.recu && !vide.emporte,
     vide ? 'reçu=' + vide.recu + ' emporté=' + vide.emporte : 'aucun bandeau');
  ok('…et les piliers non commencés le disent',
     !!vide && vide.etats.filter(t => /rien de saisi/.test(t)).length >= 2,
     vide ? vide.etats.join(' · ') : '');
  await neuf.close();

  /* Maintenant on remplit VRAIMENT le profil sur la mesure, et le report doit
     apparaître sur l'ingénierie — c'est la continuité promise. */
  if (await ouvrir('/datacenter') !== 'session') {
    /* LE PROFIL N'EST RETENU QU'APRÈS UN CALCUL RÉUSSI, et c'est délibéré : un
       profil qui n'a rien produit ici n'a pas à être proposé ailleurs. Ce
       contrôle remplissait le champ et s'arrêtait là ; il accusait donc le
       report de ne pas avoir lieu alors que sa condition n'était pas réunie.
       On fait maintenant ce que fait le lecteur : on renseigne, PUIS on lance. */
    await pg.evaluate(() => {
      const c = document.querySelector('#dc-form [data-champ="puissance_it_kw"]');
      if (!c) return;
      c.value = '2500';
      c.dispatchEvent(new Event('input', { bubbles: true }));
      c.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await pg.waitForTimeout(400);
    /* AVANT LE CALCUL, LE BANDEAU DIT LA CONDITION — il ne se tait pas. Sans
       cela, celui qui a rempli le formulaire lit « rien de saisi » sans aucun
       moyen de savoir ce qui manque. */
    const cond = await pg.evaluate(() => {
      const z = document.getElementById('piliers');
      return (z && z.querySelector('.pdc-p.attente') || {}).textContent || '';
    });
    ok('tant que l’étude n’est pas calculée, le bandeau dit À QUOI tient le report',
       /étude calculée/.test(cond), cond.trim().slice(0, 92));

    await pg.click('#dc-lancer');
    const calcule = await pg.waitForFunction(
      () => !document.getElementById('dc-sec-res').hidden,
      null, { timeout: 60000 }).then(() => true).catch(() => false);
    ok('l’étude se calcule', calcule, calcule ? '' : 'aucun résultat après 60 s');
    await pg.waitForTimeout(600);
    const pose = await pg.evaluate(() => window.ProfilDC && window.ProfilDC.lire()
      ? Object.keys(window.ProfilDC.lire().champs || window.ProfilDC.lire()).length : 0);
    ok('…et c’est LE CALCUL qui enregistre le profil', pose > 0,
       pose + ' valeur(s) en magasin');
    const apres = await pg.evaluate(() => {
      const z = document.getElementById('piliers');
      return (z && z.querySelector('.pdc-p.emporte') || {}).textContent || '';
    });
    ok('…et la mesure annonce alors ce qu’elle EMPORTE au pilier suivant',
       /valeur/.test(apres), apres.trim().slice(0, 88));

    if (await ouvrir('/ingenierie-datacenter') !== 'session') {
      const v = await lire();
      ok('L’INGÉNIERIE CONSTATE CE QU’ELLE A REÇU',
         !!v && /valeur/.test(v.recu), (v && v.recu || '').trim().slice(0, 88));
      ok('…et le pilier de mesure y est marqué comme renseigné',
         !!v && v.etats[1] === 'fait', v ? v.etats.join(' · ') : '');
    }
  }

  titre('4. Il n’invente aucune traduction entre stratégie et mesure');

  if (await ouvrir('/strategie-durable-datacenter') !== 'session') {
    const v = await lire();
    const e = (v && v.emporte) || '';
    /* Tant que rien n'est noté, RIEN n'est annoncé. Et quand quelque chose
       l'est, le texte doit dire que ce sont des JUGEMENTS, pas des grandeurs
       — sans quoi le lecteur attendra un pré-remplissage qui ne viendra pas. */
    ok('rien n’est annoncé tant qu’aucun enjeu n’est noté', e === '', e.slice(0, 60));
    const note = await pg.evaluate(async () => {
      const s = document.querySelector('#sd-enjeux [data-note]');
      if (!s) return null;
      s.value = s.options[1] ? s.options[1].value : '';
      s.dispatchEvent(new Event('change', { bubbles: true }));
      await new Promise(r => setTimeout(r, 500));
      const z = document.getElementById('piliers');
      return {
        emporte: (z && z.querySelector('.pdc-p.emporte') || {}).textContent || '',
        etat: (z && z.querySelector('.pdc-c .e') || {}).textContent || '',
      };
    });
    ok('noter un enjeu fait passer le pilier à « renseigné »',
       !!note && /renseigné/.test(note.etat), note ? note.etat.trim() : 'non testable');
    ok('…et le bandeau annonce alors le passage vers la mesure',
       !!note && /enjeu/.test(note.emporte), (note && note.emporte || '').slice(0, 80));
    /* LA LIGNE À NE PAS FRANCHIR : ne jamais laisser croire que ces jugements
       deviendront des valeurs de calcul sur la page suivante. */
    ok('…EN DISANT QUE CE NE SONT PAS DES GRANDEURS',
       !!note && /pas des grandeurs|ne les reprend pas/.test(note.emporte),
       (note && note.emporte || '').slice(0, 96));
  }

  titre('5. Le geste suivant, et la boucle');

  for (const { url, v } of vus) {
    const rang = PILIERS.indexOf(url);
    const attendu = PILIERS[(rang + 1) % PILIERS.length];
    ok('le bouton de continuation vise le pilier suivant — ' + url,
       v.suivant === attendu, v.suivant + ' (attendu ' + attendu + ')');
  }
  const dernier = vus.find(x => x.url === '/ingenierie-datacenter');
  if (dernier) {
    /* LE CHEMIN NE SE TERMINE PAS : une phase franchie change ce qu'on vise.
       Un parcours qui s'arrête au troisième pilier laisserait croire que la
       stratégie ne se rejoue jamais. */
    ok('…et le dernier pilier RAMÈNE au premier, il ne se termine pas',
       /stratégie/i.test(dernier.v.libelleSuivant),
       dernier.v.libelleSuivant.trim());
  }

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  await nav.close();
  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  process.exit(ko ? 1 : 0);
})();
