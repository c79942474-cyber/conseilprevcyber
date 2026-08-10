/* La plateforme de décarbonation, vue par un visiteur sans compte.
 *
 * POURQUOI UNE RECETTE NAVIGATEUR EN PLUS DES TESTS PYTHON. Les tests Python
 * prouvent que le module refuse de se charger si la compensation porte un
 * paramètre de calcul, et que l'API sert les rangs dans l'ordre. Ils ne
 * prouvent RIEN sur ce que voit le lecteur. Entre le JSON et l'écran il y a un
 * script de rendu — et c'est exactement là que l'ordre se perd, qu'une
 * étiquette disparaît, qu'un « ce que le levier ne fait pas » passe à la
 * trappe. Le JSON, lui, reste parfait.
 *
 * CE QU'ON PROTÈGE, DANS L'ORDRE D'IMPORTANCE :
 *
 *   1. L'ORDRE DE LA HIÉRARCHIE EST VISIBLE, ET LA COMPENSATION EST LA
 *      DERNIÈRE. C'est le fil de toute la page. Un rendu qui remonterait le
 *      résiduel — par un tri, par un ordre d'objet, par une refonte — ferait
 *      lire la page à l'envers sans lever la moindre erreur.
 *   2. LE LEVIER DE COMPENSATION N'AFFICHE AUCUN PARAMÈTRE, ET DIT POURQUOI.
 *      À l'écran, pas seulement dans le module.
 *   3. CHAQUE LEVIER MONTRE CE QU'IL NE FAIT PAS. Un levier qui n'annonce que
 *      son gain est un argumentaire.
 *   4. LES DEUX ZONES NE SE CONTREDISENT JAMAIS — la frise et le bloc du
 *      dessous. C'est le défaut déjà corrigé sur la page d'ingénierie.
 *   5. LA PAGE S'OUVRE SANS COMPTE, ET N'A RIEN OUVERT D'AUTRE.
 *
 * ON MESURE AU REPOS : on attend que chaque zone soit peuplée avant de lire.
 *
 * POUR L'EXÉCUTER — aucune session nécessaire, et c'est le sujet :
 *     BASE=http://127.0.0.1:5404 node recette_decarbonation.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
let ko = 0;
const ok = (n, c, d) => { console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : '')); if (!c) ko++; };
const titre = (t) => console.log('\n══ ' + t + ' ══\n');

/* MESURER AU REPOS — ET « AU REPOS » NE VEUT PAS DIRE « N'A PAS BOUGÉ ».
 *
 * Le défilement est animé (`behavior: "smooth"`) et met ici environ une
 * seconde à s'arrêter. J'ai écrit trois versions fausses de ce contrôle avant
 * celle-ci, et les trois échecs valent d'être notés :
 *
 *   · un délai fixe lit une position INTERPOLÉE en cours d'animation —
 *     700 ms donnaient -271 px pour une cible qui se pose à +482 ;
 *   · attendre que la valeur cesse de changer conclut AVANT que l'animation
 *     ne démarre : trois lectures identiques à 60 ms tombent toutes dans le
 *     délai de démarrage, et on mesure le point de départ ;
 *   · exiger que la cible ait « bougé » d'abord ne suffit pas non plus :
 *     Playwright fait défiler le BOUTON jusqu'à lui avant de cliquer, si bien
 *     que la position relevée juste avant le clic est déjà périmée — la cible
 *     a bougé, mais à cause du clic, pas de notre défilement.
 *
 * On attend donc l'état ATTENDU, avec une échéance : la cible entre dans la
 * fenêtre et s'y stabilise. C'est exactement la question posée au bouton
 * — « amène-t-il le champ à l'écran ? » — et l'échéance dépassée est un
 * échec, pas un contournement. */
async function attendreAlEcran(pg, sel, ms = 6000) {
  const t0 = Date.now();
  let dernier = null, stable = 0;
  while (Date.now() - t0 < ms) {
    const v = await pg.evaluate((s) => {
      const el = document.querySelector(s);
      if (!el) return null;
      return { top: Math.round(el.getBoundingClientRect().top),
               vue: window.innerHeight };
    }, sel);
    if (v === null) return { top: null, vue: 0 };
    stable = (v.top === dernier) ? stable + 1 : 0;
    dernier = v.top;
    if (stable >= 3 && v.top > 0 && v.top < v.vue) return v;
    await pg.waitForTimeout(60);
  }
  const fin = await pg.evaluate(() => ({ vue: window.innerHeight }));
  return { top: dernier, vue: fin.vue };
}

(async () => {
  const nav = await chromium.launch();
  /* Contexte NEUF et anonyme : réutiliser une session prouverait le contraire
     de ce qu'on veut prouver. */
  const ctx = await nav.newContext({ viewport: { width: 1400, height: 1000 } });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
  });
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e)));

  titre('1. La plateforme s’ouvre sans compte');

  const rep = await pg.goto(BASE + '/decarbonation-datacenter', { waitUntil: 'networkidle' });
  ok('la page répond', rep && rep.status() === 200, rep ? 'HTTP ' + rep.status() : 'pas de réponse');
  if (!rep || rep.status() !== 200) { await nav.close(); process.exit(2); }
  ok('…et ne renvoie pas vers la connexion', !/\/connexion/.test(pg.url()), pg.url());
  const ck = await ctx.cookies();
  ok('…sans le moindre cookie de session', !ck.some(c => c.name === 'cpc_session'),
     ck.map(c => c.name).join(', ') || 'aucun cookie');

  await pg.waitForFunction(() => document.querySelectorAll('#dk-hierarchie .dk-h').length > 0,
                           null, { timeout: 20000 });
  await pg.waitForFunction(() => document.querySelectorAll('#dk-form [data-champ]').length > 0,
                           null, { timeout: 20000 });

  titre('2. LE contrôle : la hiérarchie, dans son ordre, et la compensation en dernier');

  const h = await pg.evaluate(() => {
    const rangs = [...document.querySelectorAll('#dk-hierarchie .dk-h')];
    return {
      n: rangs.length,
      /* L'ordre lu à l'ÉCRAN, pas dans la réponse : c'est le rendu qu'on
         éprouve, et c'est lui qui peut trahir la donnée. */
      noms: rangs.map(r => ((r.querySelector('h3') || {}).textContent || '').trim()),
      ordres: rangs.map(r => ((r.querySelector('.o') || {}).textContent || '').trim()),
      classes: rangs.map(r => [...r.classList].filter(c => /^r\d$/.test(c))[0] || ''),
      leviers: rangs.map(r => r.querySelectorAll('.dk-lv').length),
      /* Le dernier rang : aucun paramètre affiché, et l'explication présente. */
      dernierChamps: rangs.length
        ? rangs[rangs.length - 1].querySelectorAll('.dk-ch').length : -1,
      dernierNch: rangs.length
        ? rangs[rangs.length - 1].querySelectorAll('.dk-nch').length : -1,
      dernierTxt: rangs.length
        ? (rangs[rangs.length - 1].querySelector('.dk-nch') || {}).textContent || '' : '',
      /* Aucun autre rang ne doit être dépourvu de paramètre : sinon
         l'absence cesse de distinguer la compensation. */
      autresSansChamp: rangs.slice(0, -1)
        .filter(r => r.querySelectorAll('.dk-ch').length === 0).length,
    };
  });
  ok('les quatre rangs sont dessinés', h.n === 4, h.n + ' rang(s)');
  ok('…dans l’ordre éviter → réduire → substituer → résiduel',
     h.classes.join(',') === 'r1,r2,r3,r4', h.noms.join(' → '));
  ok('…numérotés à l’écran dans le même ordre',
     h.ordres.join(',') === 'Rang 1,Rang 2,Rang 3,Rang 4', h.ordres.join(' · '));
  ok('LE RÉSIDUEL EST LE DERNIER RANG AFFICHÉ',
     /résiduel/i.test(h.noms[h.noms.length - 1] || ''), h.noms[h.noms.length - 1]);
  ok('…et il n’affiche AUCUN paramètre de calcul', h.dernierChamps === 0,
     h.dernierChamps + ' paramètre(s)');
  ok('…tout en disant pourquoi il n’en a pas', h.dernierNch === 1,
     h.dernierTxt.replace(/\s+/g, ' ').slice(0, 110));
  ok('…alors que les trois autres rangs en portent, eux',
     h.autresSansChamp === 0, h.autresSansChamp + ' rang(s) sans paramètre');
  ok('chaque rang porte au moins un levier',
     h.leviers.every(n => n > 0), h.leviers.join(' / '));

  const lv = await pg.evaluate(() => {
    const t = [...document.querySelectorAll('#dk-hierarchie .dk-lv')];
    return {
      n: t.length,
      sansNon: t.filter(x => !x.querySelector('.non')).length,
      sansPiege: t.filter(x => !x.querySelector('.pi')).length,
    };
  });
  ok('tous les leviers sont rendus', lv.n >= 10, lv.n + ' levier(s)');
  ok('AUCUN levier ne tait ce qu’il ne fait pas', lv.sansNon === 0,
     lv.sansNon + ' levier(s) muet(s)');
  ok('AUCUN levier ne tait son piège', lv.sansPiege === 0,
     lv.sansPiege + ' levier(s) sans piège');

  titre('3. Les textes, et ce qu’ils pèsent');

  const tx = await pg.evaluate(() => {
    const t = [...document.querySelectorAll('#dk-textes .dk-tx')];
    return {
      n: t.length,
      sansPortee: t.filter(x => !x.querySelector('.dk-po')).length,
      portees: [...new Set([...document.querySelectorAll('#dk-textes .dk-po')]
        .map(x => x.textContent.trim()))].sort(),
      avert: (document.querySelector('#dk-avert .dk-av') || {}).textContent || '',
    };
  });
  ok('les textes sont listés', tx.n >= 15, tx.n + ' texte(s)');
  ok('AUCUN texte sans sa portée', tx.sansPortee === 0, tx.sansPortee + ' sans portée');
  ok('…et les quatre portées sont distinguées', tx.portees.length === 4,
     tx.portees.join(' · '));
  ok('la page dit ce qu’elle ne fait pas',
     /aucune conformité|aucune neutralité/i.test(tx.avert),
     tx.avert.replace(/\s+/g, ' ').slice(0, 110));

  titre('4. Les deux zones ne se contredisent jamais');

  const vide = await pg.evaluate(() => ({
    etapes: document.querySelectorAll('#dk-parcours .dk-e').length,
    parcours: ((document.getElementById('dk-parcours') || {}).textContent || '').replace(/\s+/g, ' ').trim(),
    dossier: ((document.getElementById('dk-dossier') || {}).textContent || '').replace(/\s+/g, ' ').trim(),
  }));
  ok('sans puissance, la frise ne montre aucune étape', vide.etapes === 0);
  ok('…et le bloc du dessous n’invite pas à en choisir une',
     !/Choisissez une étape/.test(vide.dossier), vide.dossier.slice(0, 96));
  ok('…il nomme au contraire le champ qui manque',
     /puissance informatique installée/.test(vide.dossier));
  ok('la frise le nomme aussi, plutôt que de rester muette',
     /puissance informatique installée/.test(vide.parcours));

  await pg.fill('#dk-form [data-champ="puissance_it_kw"]', '50000');
  await pg.waitForFunction(() => document.querySelectorAll('#dk-parcours .dk-e').length > 0,
                           null, { timeout: 20000 });
  const plein = await pg.evaluate(() => ({
    etapes: document.querySelectorAll('#dk-parcours .dk-e').length,
    dossier: ((document.getElementById('dk-dossier') || {}).textContent || '').replace(/\s+/g, ' ').trim(),
    stop: ((document.querySelector('#dk-parcours .dk-e.stop') || {}).textContent || ''),
  }));
  ok('la puissance saisie, la frise dessine ses étapes', plein.etapes === 6,
     plein.etapes + ' étape(s)');
  ok('…et le bloc bascule alors sur « choisissez une étape »',
     /Choisissez une étape/.test(plein.dossier), plein.dossier.slice(0, 80));
  ok('…le premier blocage est marqué dans la frise', !!plein.stop.trim(),
     plein.stop.replace(/\s+/g, ' ').slice(0, 60));

  titre('5. Les deux voies, et le dossier d’une étape');

  const voies = await pg.evaluate(() =>
    [...document.querySelectorAll('#dk-voies [data-voie]')].map(b => b.getAttribute('data-voie')));
  ok('les deux voies sont proposées', voies.length === 2, voies.join(' · '));

  await pg.click('#dk-voies [data-voie="trajectoire"]');
  await pg.waitForFunction(() => document.querySelector('#dk-parcours [data-etape="RESID"]'),
                           null, { timeout: 20000 });
  await pg.click('#dk-parcours [data-etape="SUBST"]');
  /* La saisie de la puissance a laissé un rechargement en attente (le
     formulaire est temporisé). Il peut retomber APRÈS le clic et remplacer le
     dossier par son message de chargement. On attend donc que le titre soit
     posé ET qu'il le reste — attendre la seule apparition du texte lisait un
     état transitoire, et la recette mourait sur un élément disparu entre deux
     instructions. */
  await pg.waitForFunction(() => {
    const h = document.querySelector('#dk-dossier h3');
    return h && /SUBST/.test(h.textContent || '');
  }, null, { timeout: 20000 });
  await pg.waitForTimeout(900);
  await pg.waitForFunction(() => {
    const h = document.querySelector('#dk-dossier h3');
    return h && /SUBST/.test(h.textContent || '');
  }, null, { timeout: 20000 });

  const dos = await pg.evaluate(() => ({
    hash: window.location.hash,
    titre: ((document.querySelector('#dk-dossier h3') || {}).textContent || '').trim(),
    verrouille: !!document.querySelector('#dk-dossier .dk-verr'),
    preuve: !!document.querySelector('#dk-dossier .dk-preuve'),
    grandeurs: document.querySelectorAll('#dk-dossier .dk-gr').length,
    aRemplacer: document.querySelectorAll('#dk-dossier .dk-gr.a_remplacer').length,
    bloqNommes: [...document.querySelectorAll('#dk-dossier .dk-gr.a_remplacer .bloq')]
      .filter(x => x.textContent.trim().length > 12).length,
    leviers: document.querySelectorAll('#dk-dossier .dk-lv').length,
    sections: document.querySelectorAll('#dk-dossier .dk-b ul li').length,
    rdv: document.querySelectorAll('#dk-dossier .dk-rdv').length,
    textes: document.querySelectorAll('#dk-dossier .dk-tx').length,
    manques: document.querySelectorAll('#dk-dossier .dk-manque').length,
  }));
  ok('le dossier de l’étape se charge', /SUBST/.test(dos.titre), dos.titre);
  ok('…la page devient adressable', dos.hash === '#voie=trajectoire&etape=SUBST', dos.hash);
  ok('…il dit ce que l’étape verrouille', dos.verrouille);
  ok('…et ce qui la prouve', dos.preuve);
  ok('les grandeurs du moteur y figurent', dos.grandeurs === 6, dos.grandeurs + ' grandeur(s)');
  ok('…celles qui ne sont plus recevables le disent', dos.aRemplacer > 0,
     dos.aRemplacer + ' à remplacer');
  ok('…et NOMMENT ce qui les bloque', dos.bloqNommes === dos.aRemplacer,
     dos.bloqNommes + '/' + dos.aRemplacer);
  ok('les leviers de cette étape sont rappelés', dos.leviers === 4, dos.leviers + ' levier(s)');
  ok('le plan du livrable est donné', dos.sections >= 4, dos.sections + ' section(s)');
  ok('le rendez-vous avec l’autre voie est cité', dos.rdv === 1);
  ok('les textes applicables à l’étape aussi', dos.textes >= 3, dos.textes + ' texte(s)');
  ok('les points ouverts sont listés', dos.manques > 0, dos.manques + ' point(s)');

  titre('6. Le bouton conduit vraiment au champ');

  const cible = await pg.evaluate(() => {
    const b = document.querySelector('#dk-dossier [data-vers-champ]');
    return b ? b.getAttribute('data-vers-champ') : null;
  });
  if (cible) {
    const sel0 = '#dk-form [data-champ="' + cible + '"]';
    await pg.click('#dk-dossier [data-vers-champ="' + cible + '"]');
    /* La DÉSIGNATION est posée de façon synchrone au clic et retirée au bout
       de quelques secondes. On la relève donc tout de suite : la relever après
       le défilement ferait dépendre le contrôle du temps que met l'animation,
       et il tomberait le jour où la page s'allonge. */
    const marque = await pg.evaluate((c) => {
      const el = document.querySelector('#dk-form [data-champ="' + c + '"]');
      const bloc = el && el.closest('[data-champ-bloc]');
      return { focus: !!el && document.activeElement === el,
               designe: !!(bloc && bloc.classList.contains('dk-designe')) };
    }, cible);
    const pos = await attendreAlEcran(pg, sel0);
    ok('le champ est amené à l’écran',
       pos.top !== null && pos.top > 0 && pos.top < pos.vue,
       pos.top === null ? 'champ introuvable'
                        : pos.top + ' dans ' + pos.vue + ' px');
    ok('…il prend le focus, on peut taper aussitôt', marque.focus);
    ok('…et il est DÉSIGNÉ : un défilement seul laisse devant treize champs pareils',
       marque.designe);
    /* La désignation doit s'effacer : une mise en évidence permanente devient
       du décor et cesse de désigner quoi que ce soit. */
    await pg.waitForTimeout(2800);
    const apres = await pg.evaluate((c) => {
      const el = document.querySelector('#dk-form [data-champ="' + c + '"]');
      const bloc = el && el.closest('[data-champ-bloc]');
      return !!(bloc && bloc.classList.contains('dk-designe'));
    }, cible);
    ok('…puis elle s’efface', !apres);
  } else {
    ok('un bouton conduit au champ manquant', false, 'aucun bouton trouvé');
  }

  titre('7. Ce que l’ouverture ne devait PAS ouvrir');

  for (const [chemin, nom] of [
    ['/api/datacenter/ingenierie/dossier', 'le dossier d’ingénierie'],
    ['/api/datacenter/export', 'l’export de note de calcul'],
  ]) {
    const r = await ctx.request.post(BASE + chemin, {
      headers: { 'Origin': BASE, 'Content-Type': 'application/json' }, data: {},
    });
    ok(nom + ' reste fermé', r.status() === 401, 'HTTP ' + r.status());
  }
  const kb = await ctx.request.get(BASE + '/admin/base-connaissance', { maxRedirects: 0 });
  ok('la base documentaire reste réservée', [301, 302, 401, 403].includes(kb.status()),
     'HTTP ' + kb.status());

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.join(' | ').slice(0, 200));

  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  await nav.close();
  process.exit(ko ? 1 : 0);
})();
