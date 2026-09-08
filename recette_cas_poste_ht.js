/* RECETTE — LA NEUVIÈME FICHE DIT CE QU'ELLE EST, ET ELLE TIENT DANS LA PAGE
 * ═══════════════════════════════════════════════════════════════════════════
 * La page s'intitule « Références & missions ». Y poser une fiche qui n'est
 * PAS une mission menée n'est acceptable qu'à une condition : que le lecteur
 * l'apprenne au même endroit qu'il lit le nom du client, et non dans une note
 * de bas de carte qu'il n'atteindra pas.
 *
 * POURQUOI CETTE RECETTE A ÉTÉ REPRISE. Les fiches sont devenues des cartes
 * qui pivotent, et les contrôles d'origine visaient l'ancienne structure :
 * ils comptaient « .case » (qui inclut désormais les copies de dérive),
 * cherchaient « p.muted » et « li » (devenus des <span>, un <button> ne
 * pouvant pas contenir de <div>), et mesuraient une demi-largeur de grille
 * (il n'y a plus de grille). Laissés tels quels, ils seraient tombés — ou,
 * pire, auraient pu passer — pour une raison sans rapport avec ce qu'ils
 * gardent. Les propriétés protégées n'ont pas bougé d'un pouce ; seule la
 * façon de les mesurer a suivi la page.
 *
 * ET DEUX PROPRIÉTÉS S'AJOUTENT, que la nouvelle structure rend décisives :
 * la fiche ne dérive PAS parmi les missions, et son verso s'ouvre vraiment
 * quand on la retourne — un pivot qui ne montre rien serait une page muette.
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5591';
let ko = 0;
const ok = (t, c, d) => { console.log((c ? '  OK   ' : '  KO   ') + t + (d ? ' — ' + d : '')); if (!c) ko++; };
const titre = t => console.log('\n══ ' + t + ' ══\n');

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport:{width:1400,height:1000},
    userAgent:'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale:'fr-FR' });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
    Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3]});
    Object.defineProperty(navigator,'languages',{get:()=>['fr-FR','fr']});
  });
  const pg = await ctx.newPage();
  const err = []; pg.on('pageerror', e => err.push(e.message));
  const sur = async (fn,a) => { try { return await pg.evaluate(fn,a); }
                                catch(e){ return { err:String(e&&e.message||e) }; } };
  await pg.goto(BASE + '/etudes-de-cas', { waitUntil:'domcontentloaded' });
  await pg.waitForTimeout(600);

  titre('1. La fiche existe et s’ajoute aux autres');
  const n = await sur(() => ({
    // LES COPIES DE DÉRIVE NE SONT PAS DES FICHES : le rail est doublé pour
    // boucler sans saut, et les compter donnerait dix-sept études de cas.
    total: document.querySelectorAll('button.case:not([data-copie])').length,
    copies: document.querySelectorAll('button.case[data-copie]').length,
    e9: !!document.querySelector('.case.e9:not([data-copie])'),
    titre: (document.querySelector('.case.e9 .case-co')||{}).textContent || ''
  }));
  ok('les huit fiches d’origine sont toujours là, et une neuvième s’ajoute',
     !n.err && n.total === 9 && n.e9, n.err || (n.total + ' fiche(s), ' + n.copies + ' copie(s)'));
  ok('…et elle porte un intitulé de poste haute tension',
     !n.err && /haute tension/i.test(n.titre), n.titre);

  titre('2. LE POINT QUI DÉCIDE — elle dit qu’elle n’est pas une mission menée');
  const badge = await sur(() => {
    const b = document.querySelector('.case.e9:not([data-copie]) .typ');
    if (!b) return { absent:true };
    const top = b.closest('.case-top');
    const co = top && top.querySelector('.case-co');
    const s = getComputedStyle(b);
    const r = b.getBoundingClientRect(), rc = co ? co.getBoundingClientRect() : null;
    return { texte:b.textContent.trim(), couleur:s.color, taille:parseFloat(s.fontSize),
             visible:r.width > 0 && r.height > 0,
             // MÊME BLOC QUE LE NOM : le badge doit se lire d'un seul regard
             // avec l'intitulé, pas à trente lignes de là. Et il est sur le
             // RECTO : on n'a pas à retourner la carte pour l'apprendre.
             surLeRecto: !!b.closest('.case-recto'),
             memeBloc: !!(top && co), ecartY: rc ? Math.abs(r.top - rc.top) : null };
  });
  ok('un badge marque la fiche', !badge.err && !badge.absent && badge.visible,
     badge.err || badge.texte);
  ok('…il annonce un CAS TYPE, pas une référence',
     !badge.err && /cas type/i.test(badge.texte || ''), badge.texte);
  ok('…et il est DANS LE MÊME BLOC que le nom, à moins de 40 px de sa ligne',
     !badge.err && badge.memeBloc && badge.ecartY !== null && badge.ecartY < 40,
     badge.err || ('écart vertical ' + badge.ecartY + ' px'));
  ok('…sur la FACE VISIBLE : rien à retourner pour l’apprendre',
     !badge.err && badge.surLeRecto === true);

  titre('2 bis. La page annonce EN TÊTE qu’elle porte deux natures de fiches');
  const tete = await sur(() => {
    const h = document.querySelector('.page-head');
    const t = h ? h.textContent.replace(/\s+/g, ' ') : '';
    return { t, badgeDansTete: !!(h && h.querySelector('.typ')) };
  });
  ok('le chapeau distingue les missions conduites des cas types',
     !tete.err && /cas type/i.test(tete.t) && /démarche/i.test(tete.t),
     tete.err || tete.t.slice(-130));
  ok('…et il MONTRE le badge, au lieu de seulement le nommer',
     !tete.err && tete.badgeDansTete);

  titre('2 ter. Elle NE DÉRIVE PAS parmi les missions');
  const place = await sur(() => {
    const c = document.querySelector('.case.e9:not([data-copie])');
    const cadres = document.getElementById('cadres');
    const kal = document.getElementById('kal');
    return { dansCadres: !!(c && cadres && cadres.contains(c)),
             dansRails: !!(c && kal && kal.contains(c)),
             // Le titre de la bande doit dire ce qu'elle contient.
             intitule: cadres ? (cadres.querySelector('h2')||{}).textContent || '' : '',
             annonce: cadres ? /aucune mission conduite/i.test(cadres.textContent) : false };
  });
  ok('la fiche est dans la bande des cadres d’intervention, pas dans un rail de missions',
     !place.err && place.dansCadres && !place.dansRails,
     place.err || ('cadres=' + place.dansCadres + ' rails=' + place.dansRails));
  ok('…et la bande dit en toutes lettres qu’aucune mission n’y est relatée',
     !place.err && place.annonce, place.err || place.intitule);

  titre('3. Aucun résultat chiffré n’est revendiqué');
  const promesses = await sur(() => {
    const c = document.querySelector('.case.e9:not([data-copie])');
    const t = c ? c.textContent : '';
    const note = c ? c.querySelector('.v-note') : null;
    return {
      win: !!(c && c.querySelector('.win')),          // le bandeau vert des gains
      pourcents: (t.match(/[-−+]\s?\d+\s?%/g) || []),  // « ‑30 % d'incidents »
      // L'AVEU EST UNE LIGNE DISCRÈTE, comme sur la fiche « mission en cours »
      // déjà présente : c'est le badge qui alerte, la ligne qui précise.
      cadre: !!note,
      dit: note ? note.textContent.replace(/\s+/g, ' ') : ''
    };
  });
  ok('AUCUN bandeau de gains : il n’y a pas de résultat à annoncer',
     !promesses.err && !promesses.win);
  ok('…et aucun pourcentage de performance n’est avancé',
     !promesses.err && promesses.pourcents.length === 0,
     promesses.err || promesses.pourcents.join(' '));
  ok('…la fiche écrit noir sur blanc ce qu’elle n’est pas',
     !promesses.err && promesses.cadre
       && /n'est pas|n’est pas/.test(promesses.dit)
       && /aucun client/i.test(promesses.dit),
     promesses.err || ('ligne « ' + (promesses.dit || '(absente)').slice(0, 70) + ' »'));

  titre('4. La substance technique est là');
  const fond = await sur(() => {
    const c = document.querySelector('.case.e9:not([data-copie])');
    const t = c ? c.textContent : '';
    const attendus = ['62443‑3‑2','62443‑3‑3','62443‑2‑4','NIS2','BDEW','EnWG','SL‑T'];
    return { manquants: attendus.filter(x => !t.includes(x)),
             etiquettes: c ? c.querySelectorAll('.tags span').length : 0,
             rubriques: c ? c.querySelectorAll('.pt').length : 0 };
  });
  ok('les normes et protocoles annoncés sont tous traités',
     !fond.err && fond.manquants.length === 0,
     fond.err || ('manquants : ' + fond.manquants.join(', ')));
  ok('…la fiche est structurée en points, pas en bloc de texte',
     !fond.err && fond.rubriques >= 2, fond.err || (fond.rubriques + ' point(s)'));
  ok('…et elle porte ses mots-clés sur la face visible',
     !fond.err && fond.etiquettes >= 3, fond.err || (fond.etiquettes + ' étiquette(s)'));

  titre('5. Le pivot montre VRAIMENT le verso');
  await pg.click('.case.e9:not([data-copie])');
  await pg.waitForTimeout(900);
  const pivot = await sur(() => {
    const c = document.querySelector('.case.e9:not([data-copie])');
    const r = c.getBoundingClientRect();
    // LA FACE CACHÉE N'EST PAS SEULEMENT INVISIBLE : elle ne reçoit pas le
    // pointeur. Ce que `elementFromPoint` renvoie au centre de la carte dit
    // donc laquelle des deux faces est réellement tournée vers le lecteur.
    const au = document.elementFromPoint(r.left + r.width/2, r.top + r.height/2);
    return { presse: c.getAttribute('aria-pressed'),
             face: au && au.closest ? (au.closest('.case-verso') ? 'verso'
                                     : au.closest('.case-recto') ? 'recto' : 'autre') : 'aucune',
             lisible: (c.querySelector('.v-texte')||{}).clientHeight || 0 };
  });
  ok('le clic met la carte à l’état pressé', !pivot.err && pivot.presse === 'true', pivot.presse);
  ok('…et c’est bien le VERSO qui fait face au lecteur',
     !pivot.err && pivot.face === 'verso', pivot.err || ('face : ' + pivot.face));
  ok('…avec une boîte de lecture qui a de la hauteur',
     !pivot.err && pivot.lisible >= 120, pivot.err || (pivot.lisible + ' px'));
  await pg.keyboard.press('Escape');
  await pg.waitForTimeout(800);
  const ferme = await sur(() => (document.querySelector('.case.e9:not([data-copie])')||{})
                                  .getAttribute('aria-pressed'));
  ok('…et Échap la referme', ferme === 'false', String(ferme));

  titre('6. La mise en page tient — sur grand écran et sur téléphone');
  // ON MESURE AU REPOS. Le pointeur était resté sur la carte après le clic du
  // paragraphe 5 : la mesure prenait alors l'état survolé, et la carte
  // paraissait plus large que les huit autres pour une raison qui n'avait
  // rien à voir avec la mise en page.
  await pg.mouse.move(5, 5);
  for (const [nom, w, h] of [['bureau',1400,1000], ['téléphone',390,844]]) {
    await pg.setViewportSize({ width:w, height:h });
    await pg.mouse.move(5, 5);
    await pg.waitForTimeout(400);
    const geo = await sur(() => {
      const c = document.querySelector('.case.e9:not([data-copie])');
      if (!c) return { err:'fiche absente' };
      const rc = c.getBoundingClientRect();
      const autres = [].slice.call(document.querySelectorAll('button.case:not([data-copie])'))
                       .filter(x => x !== c)
                       .map(x => Math.round(x.getBoundingClientRect().width));
      // Aucun enfant ne doit déborder de la carte.
      let deborde = 0;
      c.querySelectorAll('*').forEach(x => {
        const r = x.getBoundingClientRect();
        if (r.width && (r.right > rc.right + 1 || r.left < rc.left - 1)) deborde++;
      });
      return { largeurFiche:Math.round(rc.width), autres,
               deborde, pageDeborde: document.documentElement.scrollWidth
                                     > document.documentElement.clientWidth + 1 };
    });
    // ELLE A LA MÊME TAILLE QUE LES HUIT AUTRES : c'était la demande, et ce
    // qui a changé c'est la façon de le mesurer, pas la propriété.
    const ecart = geo.autres ? Math.max.apply(null,
      geo.autres.map(x => Math.abs(x - geo.largeurFiche))) : -1;
    ok('[' + nom + '] la fiche a la MÊME largeur que les autres fiches',
       !geo.err && ecart >= 0 && ecart <= 2,
       geo.err || (geo.largeurFiche + ' px, écart max ' + ecart + ' px'));
    ok('[' + nom + '] aucun contenu ne déborde, et la page ne défile pas latéralement',
       !geo.err && geo.deborde === 0 && !geo.pageDeborde,
       geo.err || (geo.deborde + ' débordement(s)'));
  }

  titre('7. AUCUNE CARTE N’EST INVISIBLE — l’apparition au défilement ne piège personne');
  await pg.setViewportSize({ width:1400, height:1000 });
  await pg.evaluate(() => { var k = document.getElementById('kal'); if (k) k.scrollIntoView(); });
  await pg.waitForTimeout(1500);
  const vues = await sur(() => {
    const t = [].slice.call(document.querySelectorAll('button.case'));
    const pales = t.filter(c => parseFloat(getComputedStyle(c).opacity) < 0.99
                                && !!c.closest('.kal'));
    return { total: t.length, pales: pales.length,
             noms: pales.map(c => (c.querySelector('.case-co')||{}).textContent.slice(0,20)) };
  });
  // LE PIÈGE, NOMMÉ : « .rv » met la carte à opacity 0 et attend qu'un
  // observateur la voie entrer. Une carte rognée horizontalement par son rail
  // n'entre jamais tant qu'elle n'a pas dérivé — quatre sur dix-sept restaient
  // invisibles après quatorze secondes.
  ok('toutes les cartes des rails sont visibles, sans attendre la dérive',
     !vues.err && vues.pales === 0,
     vues.err || (vues.pales + ' pâle(s) sur ' + vues.total + ' : ' + vues.noms.join(', ')));

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0, err.slice(0,2).join(' | '));
  console.log('\n' + (ko === 0 ? 'tout est vert' : ko + ' contrôle(s) en échec') + '\n');
  await nav.close();
  process.exit(ko === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
