/* RECETTE — LA NEUVIÈME FICHE DIT CE QU'ELLE EST, ET ELLE TIENT DANS LA PAGE
 * ═══════════════════════════════════════════════════════════════════════════
 * La page s'intitule « Références & missions ». Y poser une fiche qui n'est
 * PAS une mission menée n'est acceptable qu'à une condition : que le lecteur
 * l'apprenne au même endroit qu'il lit le nom du client, et non dans une note
 * de bas de carte qu'il n'atteindra pas.
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
  await pg.waitForTimeout(400);

  titre('1. La fiche existe et s’ajoute aux autres');
  const n = await sur(() => ({
    total: document.querySelectorAll('.case').length,
    e9: !!document.querySelector('.case.e9'),
    titre: (document.querySelector('.case.e9 .case-co')||{}).textContent || ''
  }));
  ok('les huit fiches d’origine sont toujours là, et une neuvième s’ajoute',
     !n.err && n.total === 9 && n.e9, n.err || (n.total + ' fiche(s)'));
  ok('…et elle porte un intitulé de poste haute tension',
     !n.err && /haute tension/i.test(n.titre), n.titre);

  titre('2. LE POINT QUI DÉCIDE — elle dit qu’elle n’est pas une mission menée');
  const badge = await sur(() => {
    const b = document.querySelector('.case.e9 .typ');
    if (!b) return { absent:true };
    const top = b.closest('.case-top');
    const co = top && top.querySelector('.case-co');
    const s = getComputedStyle(b);
    const r = b.getBoundingClientRect(), rc = co ? co.getBoundingClientRect() : null;
    return { texte:b.textContent.trim(), couleur:s.color, taille:parseFloat(s.fontSize),
             visible:r.width > 0 && r.height > 0,
             // MÊME BLOC QUE LE NOM : le badge doit se lire d'un seul regard
             // avec l'intitulé, pas à trente lignes de là.
             memeBloc: !!(top && co), ecartY: rc ? Math.abs(r.top - rc.top) : null };
  });
  ok('un badge marque la fiche', !badge.err && !badge.absent && badge.visible,
     badge.err || badge.texte);
  ok('…il annonce un CAS TYPE, pas une référence',
     !badge.err && /cas type/i.test(badge.texte || ''), badge.texte);
  ok('…et il est DANS LE MÊME BLOC que le nom, à moins de 40 px de sa ligne',
     !badge.err && badge.memeBloc && badge.ecartY !== null && badge.ecartY < 40,
     badge.err || ('écart vertical ' + badge.ecartY + ' px'));

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

  titre('3. Aucun résultat chiffré n’est revendiqué');
  const promesses = await sur(() => {
    const c = document.querySelector('.case.e9');
    const t = c ? c.textContent : '';
    return {
      win: !!(c && c.querySelector('.win')),          // le bandeau vert des gains
      pourcents: (t.match(/[-−+]\s?\d+\s?%/g) || []),  // « ‑30 % d'incidents »
      // L'AVEU EST UNE LIGNE DISCRÈTE, comme sur la fiche « mission en cours »
      // déjà présente : c'est le badge qui alerte, la ligne qui précise.
      cadre: !!(c && c.querySelector('p.muted')),
      dit: c && c.querySelector('p.muted')
             ? c.querySelector('p.muted').textContent.replace(/\s+/g, ' ') : ''
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
    const t = (document.querySelector('.case.e9')||{}).textContent || '';
    const attendus = ['62443‑3‑2','62443‑3‑3','62443‑2‑4','NIS2','BDEW','EnWG','SL‑T'];
    return { manquants: attendus.filter(x => !t.includes(x)),
             etiquettes: document.querySelectorAll('.case.e9 .tags span').length,
             rubriques: document.querySelectorAll('.case.e9 li').length };
  });
  ok('les normes et protocoles annoncés sont tous traités',
     !fond.err && fond.manquants.length === 0,
     fond.err || ('manquants : ' + fond.manquants.join(', ')));
  ok('…la fiche est structurée en points, pas en bloc de texte',
     !fond.err && fond.rubriques >= 2, fond.err || (fond.rubriques + ' point(s)')); 

  titre('5. La mise en page tient — sur grand écran et sur téléphone');
  for (const [nom, w, h] of [['bureau',1400,1000], ['téléphone',390,844]]) {
    await pg.setViewportSize({ width:w, height:h });
    await pg.waitForTimeout(250);
    const geo = await sur(() => {
      const c = document.querySelector('.case.e9');
      const g = document.querySelector('.cases');
      if (!c || !g) return { err:'fiche ou grille absente' };
      const rc = c.getBoundingClientRect(), rg = g.getBoundingClientRect();
      // Aucun enfant ne doit déborder de la carte.
      let deborde = 0;
      c.querySelectorAll('*').forEach(x => {
        const r = x.getBoundingClientRect();
        if (r.width && (r.right > rc.right + 1 || r.left < rc.left - 1)) deborde++;
      });
      return { largeurFiche:Math.round(rc.width), largeurGrille:Math.round(rg.width),
               deborde, pageDeborde: document.documentElement.scrollWidth
                                     > document.documentElement.clientWidth + 1 };
    });
    // ELLE TIENT DANS UNE COLONNE, comme les huit autres : c'était la demande.
    const attendu = w > 820 ? geo.largeurGrille / 2 : geo.largeurGrille;
    ok('[' + nom + '] la fiche a la MÊME largeur que les autres fiches',
       !geo.err && Math.abs(geo.largeurFiche - attendu) <= 12,
       geo.err || (geo.largeurFiche + ' px pour ' + Math.round(attendu) + ' attendus'));
    ok('[' + nom + '] aucun contenu ne déborde, et la page ne défile pas latéralement',
       !geo.err && geo.deborde === 0 && !geo.pageDeborde,
       geo.err || (geo.deborde + ' débordement(s)'));
  }

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0, err.slice(0,2).join(' | '));
  console.log('\n' + (ko === 0 ? 'tout est vert' : ko + ' contrôle(s) en échec') + '\n');
  await nav.close();
  process.exit(ko === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
