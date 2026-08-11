/* La décarbonation, dans la page fusionnée, vue par un visiteur sans compte.
 *
 * LA FUSION. La décarbonation avait sa page ; celle-ci refaisait le même
 * formulaire et lisait le même profil. Elle vit désormais dans /datacenter, et
 * lit le formulaire de la page — saisi une seule fois. La recette éprouve donc
 * la page fusionnée, et vérifie EN PLUS qu'il n'y a bien qu'un formulaire.
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

  const rep = await pg.goto(BASE + '/datacenter', { waitUntil: 'networkidle' });
  ok('la page répond', rep && rep.status() === 200, rep ? 'HTTP ' + rep.status() : 'pas de réponse');
  if (!rep || rep.status() !== 200) { await nav.close(); process.exit(2); }
  ok('…et ne renvoie pas vers la connexion', !/\/connexion/.test(pg.url()), pg.url());
  const ck = await ctx.cookies();
  ok('…sans le moindre cookie de session', !ck.some(c => c.name === 'cpc_session'),
     ck.map(c => c.name).join(', ') || 'aucun cookie');

  await pg.waitForFunction(() => document.querySelectorAll('#dk-hierarchie .dk-h').length > 0,
                           null, { timeout: 20000 });
  await pg.waitForFunction(() => document.querySelectorAll('#dc-form [data-champ]').length > 0,
                           null, { timeout: 20000 });

  titre('2. La fusion : un seul formulaire, un seul profil');

  const fus = await pg.evaluate(() => ({
    formulaires: document.querySelectorAll('[id$="-form"]').length,
    formsIds: [...document.querySelectorAll('[id$="-form"]')].map(x => x.id),
    champs: document.querySelectorAll('#dc-form [data-champ]').length,
    /* Le champ de puissance ne doit exister qu'une fois sur toute la page :
       deux exemplaires, et le visiteur en remplit un pendant que l'autre reste
       vide — les deux moitiés de la page se contredisent alors en silence. */
    puissances: document.querySelectorAll('[data-champ="puissance_it_kw"]').length,
    titre: (document.querySelector('h1') || {}).textContent.trim(),
    sousTitre: ((document.querySelector('.dc-sous') || {}).textContent || '').trim(),
    // Les sections des deux anciennes pages coexistent
    sections: ['dc-sec-vert', 'dc-form', 'dc-sec-res', 'dc-sec-deca',
               'dc-sec-hier', 'dc-sec-art', 'dc-sec-textes']
      .filter(id => !!document.getElementById(id)),
  }));
  ok('un seul formulaire de profil sur la page', fus.puissances === 1,
     fus.puissances + ' champ(s) de puissance · ' + fus.formsIds.join(', '));
  ok('…et il porte bien les treize champs du référentiel', fus.champs === 13,
     fus.champs + ' champ(s)');
  ok('LE TITRE EST CONSERVÉ',
     /Data Center Sustainability & Decarbonisation/.test(fus.titre), fus.titre);
  ok('…et le sous-titre de méthode aussi',
     /Énergie, eau et carbone — calculés ensemble/.test(fus.sousTitre), fus.sousTitre);
  ok('les sections des deux pages coexistent', fus.sections.length === 7,
     fus.sections.join(' · '));

  const red = await ctx.request.get(BASE + '/decarbonation-datacenter',
                                    { maxRedirects: 0 });
  ok('l’ancienne adresse redirige au lieu de disparaître', red.status() === 301,
     'HTTP ' + red.status());
  ok('…vers la section fusionnée',
     (red.headers()['location'] || '').startsWith('/datacenter#'),
     red.headers()['location'] || 'aucun en-tête Location');

  titre('3. LE contrôle : la hiérarchie, dans son ordre, et la compensation en dernier');

    /* ── LES MÊMES EXIGENCES, PARCOURUES PAR LE SÉLECTEUR ─────────────────
     Ces contrôles éprouvaient les quatre rangs dessinés ensemble. Le rang se
     choisit maintenant : ils sont réécrits, pas supprimés. Ce qu'ils
     protégeaient n'a pas changé d'un mot — l'ordre, la numérotation, le fait
     que le résiduel soit le SEUL rang sans paramètre de calcul, et qu'aucun
     levier ne taise ce qu'il ne fait pas. Un contrôle qu'on efface parce que
     l'écran a bougé emporte avec lui la raison pour laquelle il existait. */
  /* LE RANG D'OUVERTURE SE LIT AVANT DE TOUCHER AU SÉLECTEUR. Contrôlé plus
     bas, après la boucle qui parcourt les quatre rangs, il rendait la valeur
     laissée par le dernier tour — et le contrôle disait « ouvre sur le rang 4 »
     alors que la page ouvre bien sur le rang 1. Un état mesuré après l'avoir
     modifié ne dit rien de l'état initial. */
  const rangOuverture = await pg.evaluate(
    () => document.getElementById('dk-rang').value);

  const parRang = [];
  for (const r of [1, 2, 3, 4]) {
    await pg.selectOption('#dk-rang', String(r));
    await pg.waitForFunction(
      (a) => {
        const o = document.querySelector('#dk-hierarchie .dk-h-t .o');
        return o && o.textContent.indexOf('Rang ' + a + ' ') === 0;
      }, String(r), { timeout: 8000 });
    parRang.push(await pg.evaluate(() => {
      const bloc = document.querySelector('#dk-hierarchie .dk-h');
      const lv = [...bloc.querySelectorAll('.dk-lv')];
      return {
        nom: ((bloc.querySelector('h3') || {}).textContent || '').trim(),
        ordre: ((bloc.querySelector('.o') || {}).textContent || '').trim(),
        classe: [...bloc.classList].filter(c => /^r\d$/.test(c))[0] || '',
        leviers: lv.length,
        champs: bloc.querySelectorAll('.dk-ch').length,
        nch: bloc.querySelectorAll('.dk-nch').length,
        txtNch: (bloc.querySelector('.dk-nch') || {}).textContent || '',
        sansNon: lv.filter(x => !x.querySelector('.non')).length,
        sansPiege: lv.filter(x => !x.querySelector('.pi')).length,
      };
    }));
  }

  ok('les quatre rangs sont atteignables', parRang.length === 4);
  ok('…dans l’ordre éviter → réduire → substituer → résiduel',
     parRang.map(x => x.classe).join(',') === 'r1,r2,r3,r4',
     parRang.map(x => x.nom).join(' → '));
  ok('…numérotés à l’écran dans le même ordre',
     parRang.every((x, k) => x.ordre.indexOf('Rang ' + (k + 1) + ' sur 4') === 0),
     parRang.map(x => x.ordre).join(' · '));
  ok('LE RÉSIDUEL EST LE DERNIER RANG DE LA SÉQUENCE',
     /résiduel/i.test(parRang[3].nom), parRang[3].nom);
  ok('…et il n’affiche AUCUN paramètre de calcul', parRang[3].champs === 0,
     parRang[3].champs + ' paramètre(s)');
  ok('…tout en disant pourquoi il n’en a pas', parRang[3].nch === 1,
     parRang[3].txtNch.replace(/\s+/g, ' ').slice(0, 110));
  ok('…alors que les trois autres rangs en portent, eux',
     parRang.slice(0, 3).every(x => x.champs > 0),
     parRang.slice(0, 3).map(x => x.champs).join(' / '));
  ok('chaque rang porte au moins un levier',
     parRang.every(x => x.leviers > 0), parRang.map(x => x.leviers).join(' / '));
  ok('tous les leviers sont rendus, rangs cumulés',
     parRang.reduce((n, x) => n + x.leviers, 0) >= 10,
     parRang.reduce((n, x) => n + x.leviers, 0) + ' levier(s)');
  ok('AUCUN levier ne tait ce qu’il ne fait pas',
     parRang.every(x => x.sansNon === 0),
     parRang.map(x => x.sansNon).join('/') + ' muet(s) par rang');
  ok('AUCUN levier ne tait son piège',
     parRang.every(x => x.sansPiege === 0),
     parRang.map(x => x.sansPiege).join('/') + ' sans piège par rang');

  titre('4. Les textes, et ce qu’ils pèsent');

  /* ── LA PORTÉE SE CHOISIT : LES CONTRÔLES LA PARCOURENT ───────────────
     Ces contrôles éprouvaient les dix-sept textes affichés ensemble. Ils sont
     RÉÉCRITS, pas supprimés : aucun texte sans sa portée, les quatre portées
     distinguées, la page qui dit ce qu'elle ne fait pas.

     ET LE CONTRÔLE NOUVEAU, QUI EST LE SUJET DE LA SECTION. Elle n'aligne pas
     dix-sept références : elle enseigne qu'elles NE PÈSENT PAS PAREIL. Un
     lecteur qui n'ouvrirait que « méthode de place » ignorerait qu'il existe
     cinq textes qui l'obligent — et c'est l'erreur que la section prévient. */
  const ouverture = await pg.evaluate(
    () => document.getElementById('dk-portee').value);
  const opts = await pg.evaluate(
    () => [...document.getElementById('dk-portee').options].map(o => o.value));

  ok('la portée se choisit dans une liste', opts.length === 4, opts.join(' · '));
  ok('LA LISTE S’OUVRE SUR CE QUI OBLIGE', ouverture === 'contraignant',
     'ouverture sur « ' + ouverture + ' »');
  ok('…et l’ordre est celui du POIDS, pas l’alphabet',
     opts.join(',') === 'contraignant,norme,auto_regulation,methode',
     opts.join(' → '));
  ok('…chaque entrée annonce combien de textes elle porte',
     await pg.evaluate(() => [...document.getElementById('dk-portee').options]
       .every(o => /\d+\s+textes?/.test(o.textContent))));

  const parPortee = [];
  for (const p of opts) {
    await pg.selectOption('#dk-portee', p);
    await pg.waitForFunction((a) => {
      const s = document.getElementById('dk-portee');
      return s && s.value === a
        && document.querySelectorAll('#dk-textes .dk-tx').length > 0;
    }, p, { timeout: 8000 });
    parPortee.push(await pg.evaluate((a) => {
      const t = [...document.querySelectorAll('#dk-textes .dk-tx')];
      const def = document.querySelector('.dk-tx-def');
      return {
        cle: a,
        n: t.length,
        sansPortee: t.filter(x => !x.querySelector('.dk-po')).length,
        etiquettes: [...new Set(t.map(
          x => (x.querySelector('.dk-po') || {}).textContent || ''))],
        def: def ? def.textContent : '',
        rappel: (document.querySelector('.dk-tx-ob') || {}).textContent || '',
        /* La définition de la portée, une seule fois : six répétitions la
           font lire zéro fois. */
        repets: (document.getElementById('dk-textes').textContent
                 .match(/Son non-respect est sanctionnable/g) || []).length,
      };
    }, p));
  }

  const total = parPortee.reduce((n, x) => n + x.n, 0);
  ok('tous les textes restent atteignables, portées cumulées', total >= 15,
     total + ' texte(s) : ' + parPortee.map(x => x.n).join(' / '));
  ok('AUCUN texte sans sa portée', parPortee.every(x => x.sansPortee === 0),
     parPortee.reduce((n, x) => n + x.sansPortee, 0) + ' sans portée');
  ok('…et les quatre portées sont distinguées',
     new Set(parPortee.flatMap(x => x.etiquettes)).size === 4,
     [...new Set(parPortee.flatMap(x => x.etiquettes))].join(' · '));
  ok('chaque portée n’affiche QUE ses propres textes',
     parPortee.every(x => x.etiquettes.length === 1),
     parPortee.map(x => x.etiquettes.length).join('/'));
  ok('chaque portée énonce ce qu’elle signifie',
     parPortee.every(x => /Ce que cette portée signifie/.test(x.def)));
  ok('…une seule fois, et non sous chaque texte',
     parPortee[0].repets === 1, parPortee[0].repets + ' répétition(s)');

  const nonObl = parPortee.filter(x => x.cle !== 'contraignant');
  ok('AILLEURS QUE DANS LE CONTRAIGNANT, on rappelle ce qui oblige',
     nonObl.every(x => /n’oblige pas par elle-même/.test(x.rappel)),
     nonObl.filter(x => !x.rappel).map(x => x.cle).join(' · ') || 'toutes le font');
  ok('…en disant COMBIEN de textes obligent',
     nonObl.every(x => /\d+ textes? de ce cadre oblige/.test(x.rappel)),
     nonObl[0].rappel.replace(/\s+/g, ' ').slice(0, 95));
  ok('…et le contraignant ne se rappelle pas à lui-même',
     !parPortee.find(x => x.cle === 'contraignant').rappel);

  await pg.click('.dk-tx-go');
  await pg.waitForFunction(
    () => document.getElementById('dk-portee').value === 'contraignant',
    null, { timeout: 8000 });
  ok('…et le rappel conduit aux textes contraignants d’un clic', true);

  const tx = { avert: await pg.evaluate(
    () => (document.querySelector('#dk-avert .dk-av') || {}).textContent || '') };
  ok('la page dit ce qu’elle ne fait pas',
     /aucune conformité|aucune neutralité/i.test(tx.avert),
     tx.avert.replace(/\s+/g, ' ').slice(0, 110));

  titre('5. Les deux zones ne se contredisent jamais');

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

  await pg.fill('#dc-form [data-champ="puissance_it_kw"]', '50000');
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

  titre('6. Les deux voies, et le dossier d’une étape');

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

  titre('7. Le bouton conduit vraiment au champ');

  const cible = await pg.evaluate(() => {
    const b = document.querySelector('#dk-dossier [data-vers-champ]');
    return b ? b.getAttribute('data-vers-champ') : null;
  });
  if (cible) {
    const sel0 = '#dc-form [data-champ="' + cible + '"]';
    await pg.click('#dk-dossier [data-vers-champ="' + cible + '"]');
    /* La DÉSIGNATION est posée de façon synchrone au clic et retirée au bout
       de quelques secondes. On la relève donc tout de suite : la relever après
       le défilement ferait dépendre le contrôle du temps que met l'animation,
       et il tomberait le jour où la page s'allonge. */
    const marque = await pg.evaluate((c) => {
      const el = document.querySelector('#dc-form [data-champ="' + c + '"]');
      const bloc = el && (el.closest('label.dc-champ') || el.closest('[data-champ-bloc]'));
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
      const el = document.querySelector('#dc-form [data-champ="' + c + '"]');
      const bloc = el && (el.closest('label.dc-champ') || el.closest('[data-champ-bloc]'));
      return !!(bloc && bloc.classList.contains('dk-designe'));
    }, cible);
    ok('…puis elle s’efface', !apres);
  } else {
    ok('un bouton conduit au champ manquant', false, 'aucun bouton trouvé');
  }

  titre('8. Ce que l’ouverture ne devait PAS ouvrir');

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

  /* ══ LA HIÉRARCHIE : UNE LISTE QUI NE DOIT PAS DÉFAIRE L'ORDRE ══════════
     Les quatre rangs se dépliaient d'un coup ; le rang se choisit maintenant.
     Le risque n'est pas d'ergonomie mais de fond : cette section n'enseigne pas
     quatre familles de leviers, elle enseigne un ORDRE. Ouvrir « Compenser »
     sans avoir jamais vu qu'il existe trois rangs au-dessus ferait dire à
     l'interface le contraire de ce que la page démontre.

     CE CONTRÔLE EST ICI ET PAS DANS LES TESTS PYTHON, ET C'EST DÉLIBÉRÉ. Un
     test qui lit le fichier source voit les chaînes ; il ne voit pas qu'elles
     sont devenues inatteignables. J'ai désactivé la branche d'affichage — « if
     (amont.length) » remplacé par « if (false) » — et le test Python est resté
     vert. Seul le vrai document tranche. */
  titre('La hiérarchie : le rang se choisit, l’ordre reste');

  await pg.waitForSelector('#dk-rang', { timeout: 25000 });
  const hier = await pg.evaluate(() => {
    const s = document.getElementById('dk-rang');
    return { n: s.options.length,
             libelles: [...s.options].map(o => o.textContent),
           };
  });
  ok('le rang se choisit dans une liste', hier.n === 4, hier.n + ' option(s)');
  ok('…et la séquence se lit SANS ouvrir la liste',
     hier.libelles.every((t, i) => t.trim().startsWith(String(i + 1) + '.')),
     hier.libelles.join(' / '));
  ok('…qui s’ouvre sur le premier rang', rangOuverture === '1',
     'rang ' + rangOuverture + ' à l’arrivée sur la page');

  const vu = async (r) => {
    await pg.selectOption('#dk-rang', String(r));
    await pg.waitForFunction(
      (attendu) => {
        const o = document.querySelector('#dk-hierarchie .dk-h-t .o');
        return o && o.textContent.indexOf('Rang ' + attendu + ' ') === 0;
      }, String(r), { timeout: 8000 });
    return pg.evaluate(() => ({
      position: document.querySelector('#dk-hierarchie .dk-h-t .o').textContent,
      leviers: document.querySelectorAll('#dk-hierarchie .dk-lv').length,
      amont: [...document.querySelectorAll('.dk-h-go')].map(b => b.textContent),
      texteAmont: (document.querySelector('.dk-h-amont') || {}).textContent || '',
    }));
  };

  const r1 = await vu(1);
  ok('le premier rang n’affiche aucun amont — il n’en a pas',
     r1.amont.length === 0, r1.amont.join(' · '));
  ok('…et il rappelle sa position dans la séquence',
     /Rang 1 sur 4/.test(r1.position), r1.position);

  const r4 = await vu(4);
  ok('le dernier rang NOMME les trois qui doivent être instruits avant',
     r4.amont.length === 3, r4.amont.join(' · ') || 'AUCUN — l’ordre est devenu un menu');
  ok('…et dit ce qu’il en coûte de s’en passer',
     /écarter en vérification/.test(r4.texteAmont), r4.texteAmont.slice(0, 90));

  await pg.click('.dk-h-go');
  await pg.waitForFunction(() => {
    const o = document.querySelector('#dk-hierarchie .dk-h-t .o');
    return o && o.textContent.indexOf('Rang 1 ') === 0;
  }, null, { timeout: 8000 });
  const retour = await pg.evaluate(() => document.getElementById('dk-rang').value);
  ok('…et chacun se rejoint d’un clic', retour === '1', 'rang ' + retour);

  ok('un seul rang est affiché à la fois',
     (await pg.evaluate(() => document.querySelectorAll('#dk-hierarchie .dk-h').length)) === 1);

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.join(' | ').slice(0, 200));

  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  await nav.close();
  process.exit(ko ? 1 : 0);
})();
