/* La frise des phases, et la consigne qui la commente.
 *
 * LE DÉFAUT CORRIGÉ. Le bloc du dossier affichait « Choisissez une phase dans
 * la frise ci-dessus » — y compris quand la frise n'était pas dessinée. Or elle
 * ne l'est PAS tant que la puissance informatique n'est pas saisie, et c'est le
 * seul des treize champs à n'avoir aucune valeur par défaut. Tout visiteur
 * ouvrait donc la page sur une consigne désignant un objet absent, et chaque
 * clic sur un onglet de filière la réaffirmait.
 *
 * CE QU'ON PROTÈGE ICI, ET C'EST UN INVARIANT, PAS UN CAS :
 *
 *   Les deux zones ne doivent JAMAIS se contredire. Si la frise ne montre
 *   aucune phase, le bloc du dessous ne doit pas inviter à en choisir une —
 *   dans AUCUN état de la page. On balaie donc les six états atteignables, y
 *   compris ceux qu'on n'atteint qu'en effaçant un champ déjà saisi.
 *
 * ET CE QU'ON N'A PAS FAIT. Aucune puissance par défaut n'a été posée : une
 * valeur inventée ferait sortir un dossier d'ingénierie complet et chiffré pour
 * un projet qui n'est pas celui du lecteur, sans que rien ne le lui dise. Le
 * contrôle vérifie que le champ reste VIDE à l'ouverture.
 *
 * POUR L'EXÉCUTER, il faut une instance locale servant /ingenierie-datacenter
 * à un utilisateur connecté :
 *     BASE=http://127.0.0.1:5403 node recette_frise_phases.js
 *
 * La page étant réservée, la recette sait ouvrir la session elle-même quand on
 * lui donne un compte — sinon elle réutilise celle du navigateur. On la voulait
 * exécutable d'une seule commande : une recette qu'il faut préparer à la main
 * n'est jamais relancée, et c'est celle-là qui manque le jour de la régression.
 *     RECETTE_EMAIL=… RECETTE_MDP=… BASE=… node recette_frise_phases.js
 * Le serveur local doit alors tourner avec COOKIE_NON_SECURISE=1, sans quoi le
 * cookie de session — Secure par défaut, et c'est très bien ainsi — ne survit
 * pas à une origine en http.
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5403';
let ko = 0;
const ok = (n, c, d) => { console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : '')); if (!c) ko++; };

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1400, height: 950 } });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
  });
  /* Ouverture de session, si on nous a donné un compte. On passe par l'API et
     non par le formulaire : ce n'est pas ce qu'on teste ici, et le faire à
     l'écran ajouterait une cause de panne étrangère au sujet. */
  if (process.env.RECETTE_EMAIL && process.env.RECETTE_MDP) {
    const r = await ctx.request.post(BASE + '/api/auth/login', {
      headers: { 'Origin': BASE, 'Content-Type': 'application/json' },
      data: { email: process.env.RECETTE_EMAIL, password: process.env.RECETTE_MDP },
    });
    if (r.status() !== 200) {
      console.log('\n  Connexion refusée (HTTP ' + r.status() + ') : '
        + (await r.text()).slice(0, 200) + '\n');
      await nav.close(); process.exit(2);
    }
  }

  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e)));
  const rep = await pg.goto(BASE + '/ingenierie-datacenter', { waitUntil: 'networkidle' });
  /* Une redirection vers la connexion renvoie 200 : sans ce contrôle, la
     recette partirait chercher une frise sur la page de login et échouerait
     trente secondes plus tard sur un délai, en accusant le mauvais coupable. */
  if (rep && /\/connexion/.test(pg.url())) {
    console.log('\n  Session absente : la page a renvoyé vers ' + pg.url()
      + '. Donnez RECETTE_EMAIL / RECETTE_MDP, ou ouvrez la session à la main.\n');
    await nav.close(); process.exit(2);
  }
  if (!rep || rep.status() !== 200) {
    console.log('\n  Page injoignable (' + (rep ? rep.status() : 'pas de réponse')
      + '). Démarrez une instance locale connectée, puis relancez.\n');
    await nav.close(); process.exit(2);
  }
  await pg.waitForFunction(() => document.querySelector('#ig-filieres [data-fil]'),
                           null, { timeout: 30000 });
  await pg.waitForTimeout(1200);

  /* L'état des DEUX zones, relevé ensemble : c'est leur accord qu'on teste,
     et le lire en deux fois laisserait passer un instant de désaccord. */
  const etat = () => pg.evaluate(() => {
    const p = document.getElementById('ig-parcours');
    const d = document.getElementById('ig-dossier');
    const c = document.querySelector('#ig-form [data-champ="puissance_it_kw"]');
    const t = (e) => (e ? (e.textContent || '').replace(/\s+/g, ' ').trim() : '');
    return {
      puissance: c ? c.value : null,
      phases: p ? p.querySelectorAll('[data-phase]').length : -1,
      frise: t(p), dossier: t(d),
      bouton: !!(p && p.querySelector('[data-vers-champ]')),
      /* La filière courante se lit sur l'ONGLET ACTIF, pas sur la variable du
         script : celui-ci vit dans une fonction fermée, invisible d'ici. Et
         c'est de toute façon l'onglet que le lecteur voit — c'est donc lui qui
         fait foi. */
      filiere: (document.querySelector('#ig-filieres [data-fil].on') || {})
        .getAttribute ? document.querySelector('#ig-filieres [data-fil].on')
          .getAttribute('data-fil') : null,
    };
  });

  /* L'INVARIANT, en une phrase : pas de frise ⇒ pas d'invitation à y choisir. */
  const accord = (e) => !(e.phases <= 0 && /Choisissez une phase dans la frise/.test(e.dossier));

  console.log('\n══ 1. L’ouverture : ce que voit tout premier visiteur ══\n');

  let e = await etat();
  ok('la puissance n’est PAS pré-remplie — on n’invente pas le projet du lecteur',
     e.puissance === '', JSON.stringify(e.puissance));
  ok('la frise ne montre donc aucune phase', e.phases === 0, e.phases);
  // LE contrôle central.
  ok('…et le bloc du dessous n’invite pas à y choisir une phase', accord(e), e.dossier);
  ok('il nomme le champ qui manque', /puissance informatique/i.test(e.dossier), e.dossier.slice(0, 80));
  ok('la frise le nomme aussi, plutôt que de rester muette',
     /puissance informatique/i.test(e.frise), e.frise.slice(0, 80));
  ok('…et dit que c’est le SEUL champ nécessaire',
     /seul champ/i.test(e.frise) || /seul champ/i.test(e.dossier));
  ok('un bouton conduit au champ', e.bouton);

  console.log('\n══ 2. Les six états atteignables, et l’accord des deux zones ══\n');

  const releve = async (etiq) => {
    const s = await etat();
    ok(etiq, accord(s),
       'frise=' + s.phases + ' phases · dossier « ' + s.dossier.slice(0, 58) + ' »');
    return s;
  };

  await pg.click('#ig-filieres [data-fil="indus"]');
  await pg.waitForTimeout(700);
  const indusVide = await releve('filière « ingénierie » sans puissance');
  ok('…la filière a bien changé', indusVide.filiere === 'indus', indusVide.filiere);
  await pg.click('#ig-filieres [data-fil="moe"]');
  await pg.waitForTimeout(700);
  await releve('filière « maîtrise d’œuvre » sans puissance');

  const champ = await pg.$('#ig-form [data-champ="puissance_it_kw"]');
  await champ.fill('5000');
  await pg.waitForTimeout(2000);
  const avecMoe = await releve('puissance saisie, filière MOE');
  ok('…la frise dessine alors ses phases', avecMoe.phases > 0, avecMoe.phases);
  // Le piège qui restait après la première correction : la frise apparaissait,
  // et le bloc du dessous continuait d'annoncer qu'elle apparaîtrait.
  ok('…et le bloc bascule sur « choisissez une phase »',
     /Choisissez une phase/.test(avecMoe.dossier), avecMoe.dossier.slice(0, 60));

  await pg.click('#ig-filieres [data-fil="indus"]');
  await pg.waitForTimeout(1200);
  const avecIndus = await releve('puissance saisie, filière ingénierie');
  ok('…cette filière a son propre nombre de phases',
     avecIndus.phases > 0 && avecIndus.phases !== avecMoe.phases,
     avecMoe.phases + ' en MOE contre ' + avecIndus.phases + ' en ingénierie');

  // L'état qu'on n'atteint qu'en revenant en arrière — celui qu'on oublie.
  await champ.fill('');
  await pg.waitForTimeout(2000);
  const efface = await releve('puissance EFFACÉE après avoir vu la frise');
  ok('…la frise redevient vide', efface.phases === 0, efface.phases);
  ok('…et le bouton d’aide au champ revient avec elle', efface.bouton);

  console.log('\n══ 3. Le bouton conduit vraiment au champ ══\n');

  await pg.click('#ig-parcours [data-vers-champ]');
  /* MESURE AU REPOS : le défilement est doux, et une mesure prise pendant
     l'animation rapporte une position intermédiaire — on a vu le contrôle
     échouer sur un champ qui arrivait à l'écran une demi-seconde plus tard. */
  await pg.waitForTimeout(1600);
  const vise = await pg.evaluate(() => {
    const e = document.querySelector('#ig-form [data-champ="puissance_it_kw"]');
    const l = e.closest('.dc-champ'); const b = l.getBoundingClientRect();
    return { focus: document.activeElement === e,
             designe: l.classList.contains('ig-designe'),
             visible: b.top >= 0 && b.bottom <= window.innerHeight,
             haut: Math.round(b.top), bas: Math.round(b.bottom), vp: window.innerHeight };
  });
  ok('le champ est amené à l’écran', vise.visible,
     vise.haut + '→' + vise.bas + ' dans ' + vise.vp + ' px');
  ok('…il prend le focus, on peut taper aussitôt', vise.focus);
  ok('…et il est DÉSIGNÉ : un défilement seul laisse devant treize champs pareils',
     vise.designe);
  await pg.waitForTimeout(2600);
  ok('la désignation s’efface — une mise en évidence permanente devient du décor',
     await pg.evaluate(() => !document.querySelector('#ig-form [data-champ="puissance_it_kw"]')
       .closest('.dc-champ').classList.contains('ig-designe')));

  console.log('\n══ 4. Ce que la correction ne devait PAS casser ══\n');

  await champ.fill('5000');
  await pg.waitForTimeout(2000);
  const codes = await pg.evaluate(() =>
    [...document.querySelectorAll('#ig-parcours [data-phase]')].map(b => b.getAttribute('data-phase')));
  ok('les phases sont toujours cliquables', codes.length > 0, codes.join(','));
  await pg.click('#ig-parcours [data-phase="' + codes[1] + '"]');
  await pg.waitForTimeout(2500);
  const apres = await pg.evaluate(() => {
    const on = document.querySelector('#ig-parcours [data-phase].on');
    return {
      dossier: (document.getElementById('ig-dossier').textContent || '')
        .replace(/\s+/g, ' ').trim().slice(0, 90),
      // La phase retenue se lit sur le bouton marqué, pas sur la variable du
      // script — elle est enfermée dans une IIFE et n'existe pas ici.
      phase: on ? on.getAttribute('data-phase') : null,
      selection: on ? on.getAttribute('aria-selected') : null,
      hash: location.hash,
      actif: document.querySelectorAll('#ig-parcours [data-phase].on').length,
    };
  });
  ok('choisir une phase la retient', apres.phase === codes[1], apres.phase);
  ok('…et l’annonce aux lecteurs d’écran', apres.selection === 'true', apres.selection);
  ok('…charge son dossier, et n’y laisse plus la consigne d’attente',
     !/Choisissez une phase/.test(apres.dossier) && apres.dossier.length > 20,
     apres.dossier.slice(0, 70));
  ok('…marque la phase dans la frise', apres.actif === 1, apres.actif);
  ok('…et rend la page adressable', /phase=/.test(apres.hash), apres.hash);
  ok('aucune erreur de script sur toute la manœuvre', err.length === 0, err.slice(0, 2).join(' | '));

  await nav.close();
  console.log(ko ? '\n' + ko + ' contrôle(s) en échec\n' : '\ntout est vert\n');
  process.exit(ko ? 1 : 0);
})();
