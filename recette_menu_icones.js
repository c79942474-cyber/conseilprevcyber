/* RECETTE — LES ICÔNES DU MENU LATÉRAL
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * LA DEMANDE, EN DEUX TEMPS. D'abord des repères colorés à gauche des titres de
 * rubrique, pour situer une section d'un coup d'œil dans un menu de huit
 * rubriques et quarante-trois entrées. Puis « de petites icônes à gauche pour
 * le reste des onglets du même menu ».
 *
 * CE QUE CES CONTRÔLES GARDENT :
 *
 *   1. CHAQUE RUBRIQUE A SON ICÔNE — aucune n'est laissée sans repère, sans
 *      quoi celle qui en manque paraîtrait rangée ailleurs.
 *   2. CHAQUE ICÔNE DE RUBRIQUE A UNE SILHOUETTE DISTINCTE. La couleur ne peut
 *      pas être le seul signal : deux rubriques partagent une teinte, et qui ne
 *      distingue pas le cyan du violet doit reconnaître un livre d'un bâtiment
 *      (WCAG 1.4.1).
 *   3. ELLES SONT MUETTES POUR LES AIDES VOCALES. Le titre est écrit juste à
 *      côté ; annoncer l'icône le répéterait.
 *   4. LE TITRE RESTE LISIBLE — l'icône ne le pousse pas hors du tiroir.
 *   5. CHAQUE ONGLET AUSSI PORTE LA SIENNE, et deux onglets d'UNE MÊME rubrique
 *      ne partagent jamais un dessin. Entre rubriques, c'est permis : on ne les
 *      lit pas d'un même regard, et l'intitulé est écrit à côté.
 *   6. LA HIÉRARCHIE TIENT. L'onglet reste plus discret que la rubrique qui le
 *      coiffe — deux niveaux également voyants n'en structurent plus aucun.
 *   7. ET RIEN NE CASSE À 390 px : pas de débordement, l'intitulé ne repasse
 *      pas sous son icône, la cible garde ses 24 px (WCAG 2.5.8).
 *
 * Lancement :
 *     BASE=http://127.0.0.1:5732 node recette_menu_icones.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const BASE = process.env.BASE || 'http://127.0.0.1:5732';

let ko = 0;
/* DEUX COLONNES DISTINCTES, ET C'EST VOULU. `mesure` est ce qu'on a relevé et
   s'affiche toujours ; `siKo` est le motif de l'échec et NE S'AFFICHE QUE
   QUAND IL Y EN A UN. Confondre les deux faisait lire « OK — sans icône : » sur
   une ligne verte : un message d'échec qui paraît alors que rien n'a échoué
   apprend à ne plus le croire. */
const ok = (t, cond, siKo, mesure) => {
  console.log((cond ? '  OK   ' : '  KO   ') + t
              + (mesure ? ' — ' + mesure : '')
              + (!cond && siKo ? ' — ' + siKo : ''));
  if (!cond) ko++;
};
const titre = t => console.log('\n══ ' + t + ' ══\n');

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({
    viewport: { width: 1280, height: 1000 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      + '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'fr-FR'
  });
  /* SANS CE MASQUE, LE SERVEUR BLOQUE L'ADRESSE POUR 1800 s. */
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
  });
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(e.message));
  const sur = async (fn, arg) => {
    try { return await pg.evaluate(fn, arg); }
    catch (e) { return { err: String(e && e.message || e) }; }
  };

  await pg.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(700);
  /* Le tiroir se construit au premier clic sur le bouton de menu. */
  await pg.evaluate(() => {
    const b = document.querySelector('.menu-btn');
    if (b) b.click();
  });
  await pg.waitForFunction(() => document.querySelectorAll('.drawer-nav h4').length > 0,
                           null, { timeout: 20000 }).catch(() => {});
  await pg.waitForTimeout(500);

  // ── 1 ───────────────────────────────────────────────────────────────────
  titre('1. Chaque rubrique porte son icône');

  const base = await sur(() => {
    const h = [...document.querySelectorAll('.drawer-nav h4')];
    return {
      rubriques: h.length,
      avecIcone: h.filter(x => x.querySelector('svg.drawer-ic')).length,
      sans: h.filter(x => !x.querySelector('svg.drawer-ic'))
             .map(x => x.textContent.trim().slice(0, 30))
    };
  });
  ok('le tiroir est construit et porte ses rubriques',
     !base.err && base.rubriques >= 6, base.err,
     base.err ? '' : base.rubriques + ' rubrique(s)');
  ok('AUCUNE rubrique n’est laissée sans repère',
     !base.err && base.avecIcone === base.rubriques,
     base.err || ('sans icône : ' + (base.sans || []).join(', ')));

  // ── 2 : LE POINT QUI DÉCIDE ─────────────────────────────────────────────
  titre('2. La couleur n’est pas le seul signal (WCAG 1.4.1)');

  const formes = await sur(() => {
    const sv = [...document.querySelectorAll('.drawer-nav h4 svg.drawer-ic')];
    const trace = sv.map(s => s.innerHTML.replace(/\s+/g, ''));
    const teintes = sv.map(s => getComputedStyle(s).color);
    return {
      n: sv.length,
      silhouettesDistinctes: new Set(trace).size,
      teintesDistinctes: new Set(teintes).size,
      teintes: [...new Set(teintes)]
    };
  });
  ok('CHAQUE ICÔNE A UNE SILHOUETTE DIFFÉRENTE — c’est elle qui distingue',
     !formes.err && formes.silhouettesDistinctes === formes.n, formes.err,
     formes.err ? '' : formes.silhouettesDistinctes + ' silhouette(s) pour '
                       + formes.n + ' rubriques');
  /* CE CONTRÔLE EST DÉLIBÉRÉMENT TOLÉRANT SUR LA COULEUR : deux rubriques
     partagent une teinte, et c'est assumé — la palette en compte six pour huit
     rubriques. Ce qui ne doit PAS arriver, c'est que tout soit de la même. */
  ok('…et les teintes sont variées sans avoir à être uniques',
     !formes.err && formes.teintesDistinctes >= 4, formes.err,
     formes.err ? '' : formes.teintesDistinctes + ' teinte(s) : '
                       + (formes.teintes || []).join(' · '));

  // ── 3 ───────────────────────────────────────────────────────────────────
  titre('3. Les icônes sont muettes pour les aides vocales');

  const a11y = await sur(() => {
    const sv = [...document.querySelectorAll('.drawer-nav h4 svg.drawer-ic')];
    return {
      n: sv.length,
      cachees: sv.filter(s => s.getAttribute('aria-hidden') === 'true').length,
      focusables: sv.filter(s => s.getAttribute('focusable') !== 'false').length,
      // Le titre reste écrit à côté de l'icône.
      titresEcrits: [...document.querySelectorAll('.drawer-nav h4')]
        .filter(h => h.textContent.trim().length > 2).length
    };
  });
  ok('toutes les icônes sont masquées aux aides vocales',
     !a11y.err && a11y.cachees === a11y.n,
     a11y.err || ((a11y.n - a11y.cachees) + ' annoncée(s)'));
  ok('…et aucune n’attrape la tabulation',
     !a11y.err && a11y.focusables === 0, a11y.err || (a11y.focusables + ' focusable(s)'));
  ok('…le titre reste ÉCRIT à côté de l’icône',
     !a11y.err && a11y.titresEcrits === a11y.n, a11y.err);

  // ── 4 ───────────────────────────────────────────────────────────────────
  titre('4. L’icône ne chasse pas le titre hors du tiroir');

  const geo = await sur(() => {
    const dr = document.querySelector('.drawer');
    const rd = dr.getBoundingClientRect();
    const debord = [...document.querySelectorAll('.drawer-nav h4')].filter(h => {
      const r = h.getBoundingClientRect();
      return r.right > rd.right + 1;
    }).length;
    const ic = document.querySelector('.drawer-nav svg.drawer-ic');
    const r = ic.getBoundingClientRect();
    return { debord, larg: Math.round(r.width), haut: Math.round(r.height),
             visible: r.width > 0 && r.height > 0 };
  });
  ok('aucun titre ne déborde du tiroir',
     !geo.err && geo.debord === 0, geo.err || (geo.debord + ' débordement(s)'));
  ok('…et l’icône est réellement dessinée',
     !geo.err && geo.visible && geo.larg >= 14, geo.err,
     geo.err ? '' : geo.larg + '×' + geo.haut + ' px');

  // ── 5 ───────────────────────────────────────────────────────────────────
  titre('5. Chaque onglet porte aussi son icône');

  const ent = await sur(() => {
    const sec = [...document.querySelectorAll('.drawer-nav section')];
    let liens = 0, avec = 0;
    const sans = [], collisions = [], echos = [];
    sec.forEach(s => {
      const h = s.querySelector('h4');
      const t = (h ? h.textContent : '?').trim();
      const hs = h && h.querySelector('svg.drawer-ic');
      const dessinChapeau = hs ? hs.innerHTML.replace(/\s+/g, '') : null;
      const vus = {};
      [...s.querySelectorAll('a')].forEach(a => {
        liens++;
        const sv = a.querySelector('svg.drawer-ic-p');
        if (!sv) { sans.push(t + ' → ' + a.textContent.trim()); return; }
        avec++;
        /* LA SILHOUETTE, PAS LA COULEUR. Deux rubriques peuvent réemployer un
           même dessin sans confusion — on ne les lit pas d'un même regard.
           Deux entrées d'UNE MÊME rubrique, si. */
        const d = sv.innerHTML.replace(/\s+/g, '');
        if (vus[d]) collisions.push(t + ' : « ' + a.textContent.trim()
                                    + ' » et « ' + vus[d] + ' »');
        vus[d] = a.textContent.trim();
        /* …ET PAS NON PLUS CELUI DE SON PROPRE CHAPEAU. Une entrée qui reprend
           le dessin de sa rubrique se lit comme le titre : la colonne perd le
           repère qui la structurait. */
        if (dessinChapeau && d === dessinChapeau)
          echos.push(t + ' → ' + a.textContent.trim());
      });
    });
    return { liens, avec, sans, collisions, echos, sections: sec.length };
  });
  ok('le tiroir porte ses onglets',
     !ent.err && ent.liens >= 40, ent.err,
     ent.err ? '' : ent.liens + ' onglet(s)');
  ok('AUCUN onglet n’est laissé sans repère',
     !ent.err && ent.liens > 0 && ent.avec === ent.liens,
     ent.err || ('sans icône : ' + (ent.sans || []).slice(0, 4).join(' | ')));
  ok('LE POINT QUI DÉCIDE — deux onglets d’UNE MÊME rubrique ne partagent '
     + 'jamais une silhouette',
     !ent.err && (ent.collisions || []).length === 0,
     ent.err || (ent.collisions || []).slice(0, 4).join(' | '));
  ok('…et aucun onglet ne recopie le dessin de son propre chapeau',
     !ent.err && (ent.echos || []).length === 0,
     ent.err || (ent.echos || []).slice(0, 4).join(' | '));

  const hier = await sur(() => {
    const p = [...document.querySelectorAll('.drawer-nav a svg.drawer-ic-p')];
    const h = [...document.querySelectorAll('.drawer-nav h4 svg.drawer-ic')];
    const larg = x => Math.round(x.getBoundingClientRect().width);
    return {
      n: p.length,
      dessinees: p.filter(x => larg(x) > 0).length,
      pMax: Math.max(...p.map(larg)),
      hMin: Math.min(...h.map(larg)),
      cachees: p.filter(x => x.getAttribute('aria-hidden') === 'true').length,
      focusables: p.filter(x => x.getAttribute('focusable') !== 'false').length,
      /* LE NOM ACCESSIBLE RESTE L'INTITULÉ ÉCRIT (WCAG 2.5.3) : l'icône étant
         muette, le lien ne s'annonce que par son texte. */
      nomsVides: [...document.querySelectorAll('.drawer-nav a')]
        .filter(a => a.textContent.trim().length < 2).length
    };
  });
  ok('…et elles sont réellement dessinées',
     !hier.err && hier.n > 0 && hier.dessinees === hier.n,
     hier.err || ((hier.n - hier.dessinees) + ' invisible(s)'));
  /* DEUX NIVEAUX QUI CRIENT ENSEMBLE N'EN FONT PLUS AUCUN. L'onglet reste en
     retrait de la rubrique qui le coiffe : c'est ce qui laisse le titre de
     section structurer la colonne. */
  ok('l’onglet reste PLUS DISCRET que la rubrique qui le coiffe',
     !hier.err && hier.pMax < hier.hMin, hier.err,
     hier.err ? '' : 'onglet ' + hier.pMax + ' px, rubrique ' + hier.hMin + ' px');
  ok('elles sont muettes pour les aides vocales',
     !hier.err && hier.cachees === hier.n,
     hier.err || ((hier.n - hier.cachees) + ' annoncée(s)'));
  ok('…aucune n’attrape la tabulation',
     !hier.err && hier.focusables === 0, hier.err || (hier.focusables + ' focusable(s)'));
  ok('…et l’intitulé écrit reste le nom du lien',
     !hier.err && hier.nomsVides === 0, hier.err || (hier.nomsVides + ' lien(s) muet(s)'));

  // ── 6 ───────────────────────────────────────────────────────────────────
  titre('6. Sur un téléphone — l’icône ne chasse pas l’intitulé');

  await pg.setViewportSize({ width: 390, height: 780 });
  await pg.waitForTimeout(400);

  const etroit = await sur(() => {
    const dr = document.querySelector('.drawer');
    const rd = dr.getBoundingClientRect();
    let debord = 0, trop = 0, recouvre = 0;
    const exemples = [];
    let plieuses = 0, decale = 0, pire = 0;
    const glissees = [];
    [...document.querySelectorAll('.drawer-nav a')].forEach(a => {
      const r = a.getBoundingClientRect();
      if (r.right > rd.right + 1) { debord++; exemples.push(a.textContent.trim()); }
      /* WCAG 2.5.8 : une cible d'au moins 24 px. */
      if (r.height < 24) trop++;
      const sp = a.querySelector('span'), sv = a.querySelector('svg.drawer-ic-p');
      if (sp && sv) {
        const rs = sp.getBoundingClientRect(), ri = sv.getBoundingClientRect();
        /* L'INTITULÉ COMMENCE APRÈS L'ICÔNE. S'il repassait dessous, la
           deuxième ligne s'alignerait sous le dessin et non sur elle-même. */
        if (rs.left < ri.right - 0.5) { recouvre++; exemples.push(a.textContent.trim()); }
        /* L'ICÔNE SE CENTRE SUR LA PREMIÈRE LIGNE, et c'est sur les intitulés
           REPLIÉS que ça se voit : centrée sur le bloc, elle tomberait entre
           les deux lignes.
           LA TOLÉRANCE A DÛ ÊTRE RESSERRÉE. Fixée d'abord à un demi-interligne,
           elle valait EXACTEMENT l'erreur que produit `align-items:center` sur
           deux lignes (11,2 px) : le contrôle passait avec ET sans le correctif,
           donc ne gardait rien. Quatre pixels — moins d'un tiers de l'icône —
           est la limite au-delà de laquelle le décalage se voit. */
        const li = parseFloat(getComputedStyle(sp).lineHeight) || 22.4;
        if (rs.height > li * 1.5) {
          plieuses++;
          const ecart = Math.abs((ri.top + ri.height / 2) - (rs.top + li / 2));
          if (ecart > pire) pire = ecart;
          if (ecart > 4) {
            decale++;
            glissees.push(a.textContent.trim() + ' (' + ecart.toFixed(1) + ' px)');
          }
        }
      }
    });
    return { debord, trop, recouvre, plieuses, decale, glissees,
             pire: Math.round(pire * 10) / 10,
             exemples: exemples.slice(0, 3), larg: Math.round(rd.width) };
  });
  ok('aucun onglet ne déborde du tiroir à 390 px',
     !etroit.err && etroit.debord === 0,
     etroit.err || (etroit.debord + ' débordement(s) : ' + (etroit.exemples || []).join(', ')));
  ok('…l’intitulé ne passe pas sous son icône',
     !etroit.err && etroit.recouvre === 0,
     etroit.err || (etroit.recouvre + ' recouvrement(s)'));
  ok('…et la cible reste d’au moins 24 px (WCAG 2.5.8)',
     !etroit.err && etroit.trop === 0, etroit.err || (etroit.trop + ' cible(s) trop basse(s)'));
  /* CE CONTRÔLE NE VAUT QUE S'IL A DE QUOI MESURER. Sans un seul intitulé
     replié il passerait à vide, et on croirait l'alignement vérifié. */
  ok('des intitulés se replient bel et bien à cette largeur',
     !etroit.err && etroit.plieuses > 0, etroit.err,
     etroit.err ? '' : etroit.plieuses + ' intitulé(s) sur deux lignes');
  ok('…et l’icône y désigne LA PREMIÈRE LIGNE, pas le vide entre les deux',
     !etroit.err && etroit.decale === 0,
     etroit.err || (etroit.glissees || []).slice(0, 3).join(' | '),
     etroit.err ? '' : 'pire écart ' + etroit.pire + ' px, limite 4');

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  console.log('\n' + (ko === 0 ? 'tout est vert' : ko + ' contrôle(s) en échec') + '\n');
  await nav.close();
  process.exit(ko === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
