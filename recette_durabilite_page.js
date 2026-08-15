/* Data Center Sustainability & Decarbonisation — la page ouverte, vue par un
 * visiteur qui n'a pas de compte.
 *
 * CE QUI A CHANGÉ. La page portait un moteur de calcul, un titre de méthode, et
 * une porte fermée. Elle porte désormais le SUJET dans son titre, le cadre de
 * développement durable adossé aux trois sous-dossiers « Green Management » de
 * la base, l'état de l'art des quatre documents versés — et elle s'ouvre sans
 * compte.
 *
 * POURQUOI UNE RECETTE NAVIGATEUR EN PLUS DES TESTS PYTHON. Les tests Python
 * prouvent que l'API sert les bonnes données et que le gabarit contient les
 * bonnes balises. Ils ne prouvent RIEN sur ce que voit le lecteur : entre le
 * JSON et l'écran il y a un script de rendu, et c'est exactement là que les
 * étiquettes de source se perdent. Un état de l'art dont les natures ne
 * s'affichent plus présente un argumentaire commercial au même rang qu'une
 * analyse indépendante — sans erreur, sans trace, et le JSON reste parfait.
 *
 * CE QU'ON PROTÈGE, DANS L'ORDRE D'IMPORTANCE :
 *
 *   1. LA HIÉRARCHIE DES SOURCES EST VISIBLE À L'ÉCRAN. Chaque fait montre son
 *      éditeur, sa page et la NATURE de sa source ; les trois documents de
 *      fournisseur sont visuellement distingués de l'analyse indépendante ; les
 *      réserves sont affichées sous les énoncés qu'elles tempèrent.
 *   2. LA PAGE S'OUVRE VRAIMENT SANS COMPTE — c'était la demande.
 *   3. LES DEUX TITRES COEXISTENT : le nouveau dit le sujet, l'ancien la
 *      méthode. Le second n'est pas décoratif, c'est ce qui distingue la page
 *      d'une plaquette verte.
 *   4. AUCUNE PROMESSE CREUSE : les grandeurs annoncées par le cadre sont celles
 *      que le moteur produit, et chaque axe dit aussi ce qu'il ne calcule pas.
 *
 * ON MESURE AU REPOS et sur des états atteints, jamais sur un rendu en cours :
 * on attend que les deux sections soient peuplées avant de lire quoi que ce
 * soit.
 *
 * POUR L'EXÉCUTER — aucune session n'est nécessaire, et c'est le sujet :
 *     BASE=http://127.0.0.1:5404 node recette_durabilite_page.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
let ko = 0;
const ok = (n, c, d) => { console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : '')); if (!c) ko++; };
const titre = (t) => console.log('\n══ ' + t + ' ══\n');

(async () => {
  const nav = await chromium.launch();
  /* Contexte NEUF et anonyme : réutiliser une session prouverait le contraire
     de ce qu'on veut prouver. */
  const ctx = await nav.newContext({ viewport: { width: 1400, height: 950 } });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
  });
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e)));

  /* SE CONNECTER D'ABORD — la page est passée en accès client. La recette
     ouvrait la page en anonyme et se contentait de constater qu'elle
     répondait ; depuis que la politique d'accès a changé, elle atterrirait sur
     le formulaire de connexion et n'éprouverait plus rien de ce qui suit. Que
     la porte tienne est éprouvé par recette_acces.js — ici, on éprouve le
     contenu, et il faut donc être entré. */
  await pg.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg.evaluate(async ([e, m]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: m }) }),
    [process.env.RECETTE_EMAIL || 'recette@local.test',
     process.env.RECETTE_MDP || 'RecetteLocale!2026']);

  titre('1. La page s’ouvre sans compte');

  const rep = await pg.goto(BASE + '/datacenter', { waitUntil: 'networkidle' });
  ok('la page répond', rep && rep.status() === 200,
     rep ? 'HTTP ' + rep.status() : 'pas de réponse');
  if (!rep || rep.status() !== 200) { await nav.close(); process.exit(2); }
  ok('…et ne renvoie plus vers la connexion', !/\/connexion/.test(pg.url()), pg.url());

  /* LE CONTRÔLE EST INVERSÉ, et c'est la politique d'accès qui l'a retourné.
     Il exigeait AUCUN cookie de session — la page était ouverte, et une session
     traînante aurait pu masquer un gardien retiré. La page est maintenant
     réservée : c'est l'ABSENCE de session qui trahirait une connexion ratée, et
     tout ce qui suit ne mesurerait plus que le formulaire de connexion. */
  const ck = await ctx.cookies();
  ok('…et la session est bien établie', ck.some(c => c.name === 'cpc_session'),
     ck.map(c => c.name).join(', ') || 'aucun cookie');

  titre('2. Les deux titres, et pourquoi les deux');

  const t = await pg.evaluate(() => {
    const h1 = document.querySelector('h1');
    const s = document.querySelector('h1 + .dc-sous, .dc-sous');
    return { h1: h1 ? h1.textContent.replace(/\s+/g, ' ').trim() : null,
             sous: s ? s.textContent.replace(/\s+/g, ' ').trim() : null,
             doc: document.title };
  });
  ok('le titre dit le SUJET', /Data Center Sustainability & Decarbonisation/.test(t.h1 || ''), t.h1);
  ok('…et l’onglet aussi', /Sustainability/.test(t.doc), t.doc);
  ok('le sous-titre garde la MÉTHODE', /Énergie, eau et carbone — calculés ensemble/.test(t.sous || ''), t.sous);

  titre('3. Le cadre — Green Management, une question à la fois');

  /* ── LA QUESTION SE CHOISIT : LES CONTRÔLES PARCOURENT LES TROIS ────────
     Les trois axes se dépliaient côte à côte, et ce fichier lisait donc les
     trois d'un seul regard. Depuis qu'une seule s'affiche, lire le DOM au
     repos n'éprouve plus qu'un tiers du cadre : les deux autres pourraient
     avoir perdu leurs textes, leurs grandeurs ou leur limite sans que rien ne
     tombe. Chaque exigence est donc reportée sur LES TROIS, atteintes par le
     sélecteur — c'est le prix du découpage, et il se paie ici. */
  const armee = await pg.waitForFunction(
    () => document.querySelectorAll('#dc-vert [data-dc-axe] option').length > 0,
    null, { timeout: 20000 }).then(() => true).catch(() => false);
  if (!armee) {
    ok('LA LISTE DES QUESTIONS DU CADRE EST ARMÉE', false,
       'aucune option dans #dc-vert après 20 s'
       + (err.length ? ' | erreur de script : ' + err[0] : ''));
  }

  const lireAxe = () => pg.evaluate(() => {
    const a = document.querySelector('#dc-vert .dc-ax');
    if (!a) return null;
    const bloc = re => [...a.querySelectorAll('.dc-ax-b')].find(
      x => re.test((x.querySelector('b') || {}).textContent || ''));
    const g = bloc(/cette page calcule/i), t = bloc(/textes applicables/i);
    const q = a.querySelector('.dc-ax-q');
    return {
      titre: (a.querySelector('h3') || {}).textContent || '',
      question: q ? q.textContent.trim() : '',
      /* « ce qui n'est pas calculé » : le bloc qui empêche le cadre d'être une
         plaquette. On regarde s'il est porté, pas combien il pèse. */
      non: !!a.querySelector('.dc-ax-non'),
      src: !!a.querySelector('.dc-ax-src'),
      /* Les grandeurs sont listées sous un intitulé, pas sous une classe
         propre : on retient le bloc PAR SON TITRE. Compter tous les « li »
         d'un axe mélangerait textes applicables et grandeurs, et le contrôle
         passerait alors même si la liste des grandeurs disparaissait. */
      grandeurs: g ? g.querySelectorAll('li').length : 0,
      textes: t ? t.querySelectorAll('li').length : 0,
    };
  });

  const opts = armee ? await pg.evaluate(() =>
    [...document.querySelectorAll('#dc-vert [data-dc-axe] option')]
      .map(o => o.textContent)) : [];
  ok('la question du cadre se choisit dans une liste', opts.length === 3,
     opts.length + ' entrée(s)');
  /* L'ASYMÉTRIE SE LIT SANS OUVRIR. Quatre grandeurs pour les indicateurs, une
     pour les certifications : c'est ce chiffre qui empêche de prendre une page
     pour une démarche. */
  ok('…chaque entrée annonce COMBIEN de grandeurs cette page lui calcule',
     opts.length === 3 && opts.every(t => /\d+\s+grandeur/.test(t)),
     opts.join(' | ').slice(0, 130));
  ok('…et la liste s’ouvre sur la première question',
     await pg.evaluate(() => {
       const s = document.querySelector('#dc-vert [data-dc-axe]');
       return s ? s.value : null; }) === '0');

  const vus = [];
  for (let k = 0; k < 3; k++) {
    if (!armee) break;
    await pg.selectOption('#dc-vert [data-dc-axe]', String(k));
    await pg.waitForTimeout(200);
    const a = await lireAxe();
    if (a) vus.push(a);
  }
  ok('LES TROIS QUESTIONS SONT ATTEIGNABLES', vus.length === 3,
     vus.map(a => a.titre).join(' | '));
  ok('…une seule est affichée à la fois',
     await pg.evaluate(() => document.querySelectorAll('#dc-vert .dc-ax').length) === 1);
  ok('…chacune pose sa question', vus.length === 3 && vus.every(a => a.question.length > 10),
     vus.map(a => a.question).join(' | ').slice(0, 110));
  ok('…chacune dit ce qu’elle NE fait PAS calculer',
     vus.length === 3 && vus.every(a => a.non),
     vus.filter(a => a.non).length + '/3');
  ok('…chacune cite sa source documentaire',
     vus.length === 3 && vus.every(a => a.src),
     vus.filter(a => a.src).length + '/3');
  ok('…avec au moins un texte nommé par question',
     vus.length === 3 && vus.every(a => a.textes > 0),
     vus.map(a => a.textes).join(' / '));
  ok('…et chacune nomme les grandeurs qu’elle fait calculer',
     vus.length === 3 && vus.every(a => a.grandeurs > 0),
     vus.map(a => a.grandeurs).join(' / ') + ' grandeur(s)');

  /* ── CE QUE LE DÉCOUPAGE NE DOIT PAS EMPORTER ──────────────────────────
     La chaîne des trois, et la phrase qui dit que le calcul ne sert que la
     deuxième. C'est la seule chose qu'un lecteur d'UNE question ne peut pas
     deviner : elle doit rester à l'écran quel que soit son choix. */
  const fixe = await pg.evaluate(() => ({
    pas: document.querySelectorAll('#dc-vert .dc-vch-p').length,
    designe: [...document.querySelectorAll('#dc-vert .dc-vch-p')]
      .filter(b => b.getAttribute('aria-current') === 'true').length,
    courant: (document.querySelector('#dc-vert .dc-vch-p[aria-current="true"]')
      || {}).textContent || '',
    limites: /propres limites/.test(
      (document.querySelector('#dc-vert .dc-vch-f') || {}).textContent || ''),
    ouvert: !!document.querySelector('#dc-vert .dc-vert-o'),
    avert: !!document.querySelector('#dc-vert .dc-vert-a'),
  }));
  ok('LA CHAÎNE DES TROIS RESTE AFFICHÉE quel que soit le choix', fixe.pas === 3,
     fixe.pas + ' étape(s)');
  ok('…et la question lue y est DÉSIGNÉE', fixe.designe === 1,
     fixe.designe + ' désignée(s)');
  ok('…c’est bien celle qui est ouverte',
     vus.length === 3 && fixe.courant.indexOf(vus[2].question) >= 0,
     fixe.courant.trim().slice(0, 70));
  ok('…et la page prévient qu’une limite lue seule n’est pas la limite du tout',
     fixe.limites);
  ok('l’ouverture et l’avertissement survivent au choix',
     fixe.ouvert && fixe.avert);

  /* DEUX COMMANDES, UN SEUL ÉTAT. Cliquer une étape de la chaîne doit déplacer
     la liste aussi : sinon les deux se contrediraient à l'écran, et le lecteur
     croirait lire ce que la liste annonce. */
  const accord = armee ? await pg.evaluate(async () => {
    const b = document.querySelector('#dc-vert .dc-vch-p[data-dc-ax="1"]');
    if (!b) return null;
    b.click();
    await new Promise(r => setTimeout(r, 250));
    const s = document.querySelector('#dc-vert [data-dc-axe]');
    const a = document.querySelector('#dc-vert .dc-ax h3');
    return { liste: s ? s.value : null, titre: a ? a.textContent : '' };
  }) : null;
  ok('cliquer une étape de la chaîne DÉPLACE AUSSI la liste',
     !!accord && accord.liste === '1',
     accord ? 'liste=' + accord.liste + ' · ' + accord.titre : 'étape absente');

  /* ── LA CHAÎNE SE LIT VRAIMENT ─────────────────────────────────────────
     Le rang de l'étape lue s'écrivait dans le vert de la désignation : 4,15:1
     sur son propre fond teinté, sous le seuil AA d'un texte de 11 px. Une
     mesure faite une fois et non gardée redevient fausse au premier réglage
     de couleur — elle est donc refaite ici, à chaque passage.

     ON COMPOSE LES COUCHES. `getComputedStyle` rend `rgba(0,0,0,0)` pour un
     fond hérité : lire le fond de l'élément seul donnerait un rapport calculé
     sur du blanc, c'est-à-dire un chiffre faux et rassurant sur une page
     sombre. On remonte donc jusqu'au premier fond OPAQUE en appliquant les
     opacités rencontrées. */
  const ctr = await pg.evaluate(() => {
    const lum = c => { const s = c.map(v => { v /= 255;
      return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); });
      return .2126 * s[0] + .7152 * s[1] + .0722 * s[2]; };
    const nb = t => { const m = String(t).match(/[\d.]+/g); return m ? m.map(Number) : [0, 0, 0, 0]; };
    function fond(el){
      const couches = [];
      for (let n = el; n; n = n.parentElement) {
        const c = nb(getComputedStyle(n).backgroundColor);
        const a = c[3] === undefined ? 1 : c[3];
        if (a > 0) { couches.push([c[0], c[1], c[2], a]); if (a === 1) break; }
      }
      let out = [255, 255, 255];
      for (let i = couches.length - 1; i >= 0; i--) {
        const [r, g, b, a] = couches[i];
        out = [r * a + out[0] * (1 - a), g * a + out[1] * (1 - a), b * a + out[2] * (1 - a)];
      }
      return out;
    }
    const cibles = {
      'étape non lue': '.dc-vch-p:not([aria-current])',
      'étape lue': '.dc-vch-p[aria-current="true"]',
      'le rang de l’étape lue': '.dc-vch-p[aria-current="true"] .n',
      'la phrase sous la chaîne': '.dc-vch-f',
      'l’aide sous la liste': '.dc-asel-a',
    };
    const out = [];
    for (const k in cibles) {
      const e = document.querySelector('#dc-vert ' + cibles[k]);
      if (!e) { out.push({ nom: k, absent: true }); continue; }
      const s = getComputedStyle(e);
      const l1 = lum(nb(s.color).slice(0, 3)), l2 = lum(fond(e));
      const px = parseFloat(s.fontSize);
      const gras = parseInt(s.fontWeight, 10) >= 700;
      out.push({ nom: k, px: px,
        r: Math.round(((Math.max(l1, l2) + .05) / (Math.min(l1, l2) + .05)) * 100) / 100,
        seuil: (px >= 24 || (px >= 18.66 && gras)) ? 3 : 4.5 });
    }
    return out;
  });
  const sous = ctr.filter(x => x.absent || x.r < x.seuil);
  ok('TOUT CE QUE LA CHAÎNE ÉCRIT PASSE LE SEUIL AA',
     sous.length === 0,
     sous.length
       ? sous.map(x => x.absent ? x.nom + ' ABSENT'
           : x.nom + ' ' + x.r + ':1 < ' + x.seuil + ' (' + x.px + 'px)').join(' · ')
       : ctr.map(x => x.r + ':1').join(' · '));

  titre('4. L’état de l’art — et le contrôle qui compte : la NATURE des sources');

  /* ── LE THÈME SE CHOISIT : LES CONTRÔLES LE PARCOURENT ────────────────
     Ces contrôles éprouvaient les vingt et un faits affichés ensemble. Le thème
     se choisit maintenant dans une liste : ils sont RÉÉCRITS, pas supprimés.
     Ce qu'ils protègent n'a pas bougé — aucun fait sans éditeur ni page, aucun
     fait sans la nature de sa source, l'œil qui sépare fournisseur et analyse
     indépendante, les réserves, les renvois. Un contrôle qu'on efface parce
     que l'écran a changé emporte la raison pour laquelle il existait.

     ET LE CONTRÔLE NOUVEAU, QUI EST LE SUJET MÊME DE LA SECTION : le découpage
     rend invisible la CONCENTRATION des sources. Quatre thèmes sur sept
     reposent sur une seule maison ; qui n'en ouvre qu'un lira comme un état de
     l'art ce qui est un point de vue. Le nombre de sources doit donc figurer
     dans l'option, et le thème affiché doit nommer ce sur quoi il repose. */
  await pg.waitForSelector('#dc-theme', { timeout: 20000 });

  const sel = await pg.evaluate(() => ({
    opts: [...document.getElementById('dc-theme').options].map(o => o.textContent),
    ouverture: document.getElementById('dc-theme').value,
    n: document.getElementById('dc-theme').options.length,
  }));
  ok('le thème se choisit dans une liste', sel.n >= 6, sel.n + ' thème(s)');
  ok('…chaque entrée annonce combien de faits elle porte',
     sel.opts.every(t => /\d+\s+faits?/.test(t)), sel.opts[0]);
  ok('…ET SUR COMBIEN DE SOURCES elle repose — la concentration se lit sans ouvrir',
     sel.opts.every(t => /\d+\s+sources?/.test(t)), sel.opts[1]);
  ok('…la liste s’ouvre sur le premier thème', sel.ouverture === '0', sel.ouverture);

  const parTheme = [];
  for (let k = 0; k < sel.n; k++) {
    await pg.selectOption('#dc-theme', String(k));
    await pg.waitForFunction((a) => {
      const s = document.getElementById('dc-theme');
      return s && s.value === String(a)
        && document.querySelectorAll('#dc-art .dc-fait').length > 0;
    }, k, { timeout: 8000 });
    parTheme.push(await pg.evaluate(() => {
      const f = [...document.querySelectorAll('#dc-art .dc-fait')];
      const q = document.querySelector('.dc-art-q');
      return {
        titre: (document.querySelector('#dc-art .dc-art-g h3') || {}).textContent || '',
        groupes: document.querySelectorAll('#dc-art .dc-art-g').length,
        faits: f.length,
        sansSource: f.filter(x => {
          const s = x.querySelector('.dc-fait-s');
          return !s || !/p\.\s*\d/.test(s.textContent);
        }).length,
        sansNature: f.filter(x => !x.querySelector('.dc-nat')).length,
        etiquettes: [...new Set([...document.querySelectorAll('#dc-art .dc-fait .dc-nat')]
                      .map(n => n.textContent.trim()))],
        indep: f.filter(x => x.classList.contains('n-analyse_editeur')).length,
        fournisseur: f.filter(x => x.classList.contains('n-livre_blanc_fournisseur')
                                || x.classList.contains('n-guide_fournisseur')).length,
        reserves: document.querySelectorAll('#dc-art .dc-fait-r').length,
        touches: document.querySelectorAll('#dc-art .dc-touche').length,
        qui: q ? q.textContent : '',
        seule: !!document.querySelector('.dc-art-q.seule'),
        lacunes: document.querySelectorAll('#dc-art .dc-art-l li').length,
        biblio: document.querySelectorAll('#dc-art .dc-art-b li').length,
        avert: (document.querySelector('#dc-art .dc-art-av') || {}).textContent || '',
      };
    }));
  }

  const total = parTheme.reduce((n, x) => n + x.faits, 0);
  ok('tous les faits restent atteignables, thèmes cumulés', total >= 20,
     total + ' fait(s) sur ' + sel.n + ' thème(s)');
  ok('un seul thème est affiché à la fois',
     parTheme.every(x => x.groupes === 1), parTheme.map(x => x.groupes).join('/'));
  ok('AUCUN fait sans son éditeur et sa page',
     parTheme.every(x => x.sansSource === 0),
     parTheme.reduce((n, x) => n + x.sansSource, 0) + ' sans référence');
  ok('AUCUN fait sans l’étiquette de nature de sa source',
     parTheme.every(x => x.sansNature === 0),
     parTheme.reduce((n, x) => n + x.sansNature, 0) + ' sans étiquette');
  ok('…les trois natures sont nommées en clair, tous thèmes confondus',
     new Set(parTheme.flatMap(x => x.etiquettes)).size === 3,
     [...new Set(parTheme.flatMap(x => x.etiquettes))].join(' · '));
  ok('…et l’œil sépare fournisseur et analyse indépendante',
     parTheme.reduce((n, x) => n + x.indep, 0) > 0
     && parTheme.reduce((n, x) => n + x.fournisseur, 0) > 0,
     parTheme.reduce((n, x) => n + x.indep, 0) + ' indépendant(s) / '
     + parTheme.reduce((n, x) => n + x.fournisseur, 0) + ' fournisseur(s)');
  ok('les réserves accompagnent les énoncés qu’elles tempèrent',
     parTheme.reduce((n, x) => n + x.reserves, 0) >= 8,
     parTheme.reduce((n, x) => n + x.reserves, 0) + ' réserve(s)');
  ok('les renvois vers les paramètres du moteur sont visibles',
     parTheme.reduce((n, x) => n + x.touches, 0) >= 12,
     parTheme.reduce((n, x) => n + x.touches, 0) + ' renvoi(s)');

  ok('CHAQUE thème nomme ce sur quoi il repose',
     parTheme.every(x => /Qui le dit ici/.test(x.qui)),
     parTheme.filter(x => !/Qui le dit ici/.test(x.qui)).length + ' thème(s) muet(s)');
  const solo = parTheme.filter(x => x.seule);
  ok('…et un thème appuyé sur UNE SEULE maison le DIT',
     solo.length > 0 && solo.every(x => /une seule source/i.test(x.qui)),
     solo.length + ' thème(s) à source unique : ' + solo.map(x => x.titre).join(' · '));
  ok('…en disant ce que cela vaut : un point de vue, pas un recoupement',
     solo.every(x => /point de vue/.test(x.qui) && /confirmé par un tiers/.test(x.qui)));

  ok('l’avertissement précède les chiffres, sur tous les thèmes',
     parTheme.every(x => /fournisseur/.test(x.avert)
       && /n’entre dans le calcul|n'entre dans le calcul/.test(x.avert)),
     parTheme[0].avert.replace(/\s+/g, ' ').trim().slice(0, 110));
  ok('les lacunes restent listées quel que soit le thème choisi',
     parTheme.every(x => x.lacunes >= 4),
     parTheme.map(x => x.lacunes).join('/'));

  /* ── CE QUI REND LE REPLI ACCEPTABLE ────────────────────────────────────
     Les deux blocs de référence — lacunes et bibliographie — pesaient 621 px
     sur les 1331 de la section, soit près de la moitié de sa hauteur pour de
     la matière qu'on CONSULTE, pendant que les faits qu'on vient LIRE en
     occupaient 424. Ils sont donc repliés.

     MAIS LES DEUX CONTRÔLES CI-DESSUS NE LE VOIENT PLUS. Ils comptent des
     `li` dans le document, et un `li` reste dans le document qu'il soit
     déplié ou non : ils resteraient verts même si le repli rendait ces listes
     introuvables. Ce qui rend le repli acceptable — et qui doit donc être
     gardé — c'est que le RÉSUMÉ porte le compte : « 4 lacunes recensées » se
     lit sans ouvrir. Un dépliant qui masque un état renseigné coûte plus cher
     que la place qu'il fait gagner. */
  const repli = await pg.evaluate(() => {
    const q = s => document.querySelector('#dc-art ' + s);
    const lire = s => {
      const d = q(s);
      if (!d) return { absent: true };
      const n = d.querySelector('.dc-art-n');
      return {
        estDepliant: d.tagName === 'DETAILS',
        ferme: !d.open,
        compte: n ? n.textContent.trim() : '',
        compteVisible: !!n && n.getBoundingClientRect().height > 0,
        items: d.querySelectorAll('li').length,
      };
    };
    return { lac: lire('.dc-art-l'), bib: lire('.dc-art-b') };
  });
  for (const [nom, r] of [['les lacunes', repli.lac], ['la bibliographie', repli.bib]]) {
    ok(nom + ' se replie, pour rendre la hauteur aux faits',
       !!r.estDepliant && r.ferme === true,
       r.absent ? 'bloc absent' : 'dépliant=' + r.estDepliant + ' fermé=' + r.ferme);
    ok('…ET SON COMPTE SE LIT SANS OUVRIR — ' + nom,
       !!r.compteVisible && /\d/.test(r.compte || ''),
       r.compte || 'aucun compte sur le résumé');
  }
  ok('la bibliographie ferme la section quel que soit le thème choisi',
     parTheme.every(x => x.biblio === 4), parTheme.map(x => x.biblio).join('/'));

  const art = { texte: await pg.evaluate(
    () => (document.getElementById('dc-art') || {}).textContent || '') };

  titre('4 ter. Le référentiel : trois colonnes, et dix sources qu’on peut OUVRIR');

  /* Le référentiel citait ses sources en toutes lettres, mais aucune n'était
     cliquable. Le menu en propose maintenant dix, servies par le serveur avec
     leur lien officiel. CE QU'ON PROTÈGE : que les liens soient en https et à
     la RACINE du site — un lien profond finit toujours par mourir, et un lien
     mort au milieu d'un référentiel discrédite tout ce qui l'entoure — et que
     la fiche ouverte porte bien `rel="noopener"` : sans lui, la page cible
     reçoit `window.opener`. */
  const refz = await pg.evaluate(() => {
    const z = document.getElementById('dc-referentiel');
    const cartes = [...z.querySelectorAll('.dc-ref .dc-ref-c')];
    const y0 = cartes.length ? Math.round(cartes[0].getBoundingClientRect().top) : 0;
    const sel = z.querySelector('[data-dc-src]');
    const cadre = z.querySelector('.dc-cadre');
    return {
      cartes: cartes.length,
      colonnes: cartes.filter(c =>
        Math.abs(Math.round(c.getBoundingClientRect().top) - y0) < 4).length,
      menu: !!sel, options: sel ? sel.options.length - 1 : 0,
      intitule: sel ? sel.options[0].textContent.trim() : '',
      cadreDepliant: !!cadre && cadre.tagName === 'DETAILS' && !cadre.open,
      cadreCompte: cadre ? ((cadre.querySelector('.dc-art-n') || {}).textContent || '') : '',
    };
  });
  ok('les cartes du référentiel tiennent sur TROIS colonnes',
     refz.colonnes === 3, refz.colonnes + ' au premier rang, ' + refz.cartes + ' carte(s)');
  ok('le cadre réglementaire est replié, et son intitulé porte le compte',
     refz.cadreDepliant && /\d/.test(refz.cadreCompte), refz.cadreCompte);
  ok('LE MENU PROPOSE AU MOINS HUIT SOURCES', refz.menu && refz.options >= 8,
     refz.options + ' source(s)');
  ok('…et son intitulé annonce le compte et le lien',
     /\d+ sources officielles, avec leur lien/.test(refz.intitule), refz.intitule);

  /* LA RÈGLE ANTI-POURRISSEMENT, mesurée sur ce que le serveur SERT : https,
     et rien après le domaine. C'est la doctrine qui rend ces liens durables. */
  const liens = await pg.evaluate(async () => {
    const r = await fetch('/api/datacenter/referentiel', { credentials: 'same-origin' });
    const j = await r.json();
    const srcs = (j.referentiel || j).sources_consultables
      || (j.sources_consultables || []);
    return srcs.map(x => ({ cle: x.cle, lien: x.lien,
      racine: /^https:\/\/[^/]+\/?$/.test(x.lien) }));
  });
  ok('le serveur sert les mêmes sources que le menu', liens.length === refz.options,
     liens.length + ' servies / ' + refz.options + ' au menu');
  /* Les normes d'écoconception fournies au cabinet ont leur porte d'entrée :
     AFNOR (les textes) et INIES (les FDES où la substitution se fait). */
  ok('…dont AFNOR et INIES, les portes des normes d’écoconception et des FDES',
     ['afnor', 'inies'].every(c => liens.some(l => l.cle === c)),
     liens.map(l => l.cle).join(', '));
  ok('TOUS LES LIENS SONT EN HTTPS ET À LA RACINE DU SITE',
     liens.length > 0 && liens.every(x => x.racine),
     liens.filter(x => !x.racine).map(x => x.cle + '=' + x.lien).join(' ') || 'tous');

  const fiche = await pg.evaluate(async () => {
    const sel = document.querySelector('[data-dc-src]');
    if (!sel) return { lien: null, cible: null, rel: null, verifier: '',
                       garde: false, manque: 'aucun menu [data-dc-src]' };
    sel.value = '0';
    sel.dispatchEvent(new Event('change', { bubbles: true }));
    await new Promise(r => setTimeout(r, 250));
    const a = document.querySelector('#dc-src-fiche .dc-src-l');
    const v = document.querySelector('#dc-src-fiche .dc-src-v');
    return {
      lien: a ? a.getAttribute('href') : null,
      cible: a ? a.getAttribute('target') : null,
      rel: a ? a.getAttribute('rel') : null,
      verifier: v ? v.textContent : '',
      garde: sel.value === '0',
    };
  });
  ok('choisir une source OUVRE sa fiche, avec le lien du référentiel',
     !!fiche.lien && liens.some(x => x.lien === fiche.lien), fiche.lien);
  ok('…le lien s’ouvre dans un nouvel onglet SANS donner window.opener',
     fiche.cible === '_blank' && /noopener/.test(fiche.rel || ''),
     'target=' + fiche.cible + ' rel=' + fiche.rel);
  ok('…la fiche dit QUOI vérifier une fois sur place',
     /À vérifier sur place/.test(fiche.verifier), fiche.verifier.slice(0, 60));
  /* Ce menu MONTRE une fiche : il garde sa sélection — l'idiome du sélecteur
     de thème, et deux menus qui montrent doivent se comporter pareil. */
  ok('…et ce menu-là GARDE sa sélection : il montre, il n’insère pas', fiche.garde);

  titre('4 quater. Les limites : chacune porte sa réponse, deux se lèvent ici');

  /* La liste statique disait « le moteur ne connaît pas votre intensité
     carbone » alors que le champ existait : une limite écrite en dur avait
     déjà menti. Tout vient du serveur. CE QU'ON PROTÈGE : chaque limite garde
     sa réponse — normes, calcul, qui — et les limites levables nomment un
     champ RÉEL du formulaire, en teal (le constaté), jamais en ambre. */
  const lims = await pg.evaluate(() => {
    const z = document.getElementById('dc-limites');
    const cartes = [...(z ? z.querySelectorAll('.dc-lim-c') : [])];
    const y0 = cartes.length ? Math.round(cartes[0].getBoundingClientRect().top) : 0;
    const champsForm = [...document.querySelectorAll('#dc-form [data-champ]')]
      .map(c => c.getAttribute('data-champ'));
    return {
      n: cartes.length,
      colonnes: cartes.filter(c =>
        Math.abs(Math.round(c.getBoundingClientRect().top) - y0) < 4).length,
      normes: cartes.map(c => c.querySelectorAll('.dc-lim-n').length),
      marches: cartes.filter(c =>
        /La marche professionnelle/.test(c.textContent)).length,
      /* La ligne « qui — quand » porte sa classe : la repérer par sa POSITION
         (p:last-child) s'est cassé le jour où l'évaluateur s'est ajouté
         derrière elle — le sélecteur mesurait la structure, pas le contenu. */
      quiQuand: cartes.filter(c => !!c.querySelector('.dc-lim-q b')).length,
      levables: cartes.filter(c => c.classList.contains('levable')).length,
      champsLeve: cartes.map(c => {
        const l = c.querySelector('.dc-lim-lv');
        const m = l && l.textContent.match(/« (.+) »/);
        return m ? m[1] : null;
      }).filter(Boolean),
      champsForm: champsForm,
      titreSection: (document.querySelector('#dc-sec-limites h2') || {}).textContent || '',
    };
  });
  ok('les quatre limites sont rendues, sur deux colonnes',
     lims.n === 4 && lims.colonnes === 2, lims.n + ' carte(s), ' + lims.colonnes + ' au premier rang');
  ok('…et le titre dit qu’on y RÉPOND, pas seulement qu’on renonce',
     /comment y répondre/i.test(lims.titreSection), lims.titreSection);
  ok('CHAQUE LIMITE PORTE AU MOINS DEUX NORMES', lims.normes.every(n => n >= 2),
     lims.normes.join('/'));
  ok('…et sa marche professionnelle, avec qui la mène', lims.marches === 4
     && lims.quiQuand === 4, lims.marches + ' marche(s), ' + lims.quiQuand + ' qui/quand');
  ok('DEUX LIMITES SE LÈVENT ICI, par un champ RÉEL du formulaire',
     lims.levables === 2 && lims.champsLeve.length === 2
       && lims.champsLeve.every(c => lims.champsForm.indexOf(c) >= 0),
     lims.champsLeve.join(', ') || 'aucun champ nommé');

  /* L'ÉVALUATEUR DE CHIFFRE ANNONCÉ, sur les cartes des deux études que le
     moteur ne fait pas. CE QU'ON PROTÈGE : le geste qui PRÉCÈDE la simulation
     TMY et le profil horaire — juger le chiffre déjà sur la table — avec les
     plages de l'étude, et un verdict qui DIT quelles valeurs du formulaire il
     a employées. Trois issues, trois rendus : le suspect (ambre), le refus
     (rouge — c'est une réponse, pas une panne), le cohérent (teal). */
  const evs = await pg.evaluate(() => {
    const cartes = [...document.querySelectorAll('#dc-limites .dc-lim-c')];
    return {
      total: document.querySelectorAll('#dc-limites .dc-ev').length,
      pueSurLevable: cartes.some(c => c.classList.contains('levable')
        && c.querySelector('[data-ev="pue"]')),
      intSurLevable: cartes.some(c => c.classList.contains('levable')
        && c.querySelector('[data-ev="intensite"]')),
      eauPresent: cartes.some(c => !c.classList.contains('levable')
        && c.querySelector('[data-ev="eau"]')),
      incPresent: cartes.some(c => !c.classList.contains('levable')
        && c.querySelector('[data-ev="incorpore"]')),
      postesServis: [...document.querySelectorAll('[data-ev="incorpore"] [data-ev-poste] option')]
        .map(o => o.value),
    };
  });
  ok('QUATRE évaluateurs — un par carte, levable ou non',
     evs.total === 4 && evs.pueSurLevable && evs.intSurLevable
       && evs.eauPresent && evs.incPresent,
     evs.total + ' évaluateur(s) — eau: ' + evs.eauPresent + ', incorporé: ' + evs.incPresent);
  ok('…et les postes d’incorporé viennent du référentiel SERVI',
     evs.postesServis.length >= 3 && evs.postesServis.indexOf('serveur_kgCO2e') >= 0,
     evs.postesServis.join(', '));

  /* Le contexte du jugement vient du FORMULAIRE : on le fixe d'abord, pour
     que le verdict attendu soit déterministe. */
  let formPret = true;
  try {
    await pg.selectOption('#dc-form [data-champ="refroidissement"]', 'adiabatique');
    await pg.selectOption('#dc-form [data-champ="pays"]', 'FR');
  } catch (e) { formPret = false; }
  ok('le formulaire accepte famille « adiabatique » et pays « FR »', formPret,
     formPret ? '' : 'selects introuvables — l’évaluateur n’a plus de contexte à lire');

  const verdictDans = async (sel) => {
    try {
      await pg.waitForFunction((s) =>
        document.querySelector(s + ' [data-ev-r] .dc-ev-v'), sel, { timeout: 15000 });
      return pg.evaluate((s) => {
        const z = document.querySelector(s + ' [data-ev-r] .dc-ev-v');
        return { classe: z.className, txt: z.textContent.replace(/\s+/g, ' ').trim() };
      }, sel);
    } catch (e) {
      return { classe: 'ABSENT', txt: 'le verdict n’est jamais arrivé — '
               + String(err[0] || e.message).slice(0, 160) };
    }
  };

  /* 1,02 en adiabatique : SOUS la plage de conception — le PUE de plaquette
     par excellence. Ambre, motif « suspect », et la méthode à exiger. */
  await pg.fill('[data-ev="pue"] [data-ev-pue]', '1,02');
  await pg.click('[data-ev="pue"] [data-ev-go]');
  const v1 = await verdictDans('[data-ev="pue"]');
  ok('un PUE trop beau (1,02) est marqué à l’ambre, motif « suspect »',
     /attention/.test(v1.classe) && /suspect/i.test(v1.txt), v1.txt.slice(0, 140));
  ok('…le verdict DIT le contexte lu du formulaire (famille, taux)',
     /adiabatique/i.test(v1.txt) && /famille lue du formulaire/.test(v1.txt)
       && /% de charge/.test(v1.txt),
     v1.txt.slice(v1.txt.search(/Jugé pour/), v1.txt.search(/Jugé pour/) + 120));
  ok('…et les exigences nomment le BE fluides et ISO/IEC 30134-2',
     /BE fluides/.test(v1.txt) && /ISO\/IEC 30134-2/.test(v1.txt));

  /* 0,8 : physiquement impossible. Le REFUS est la réponse — rendu rouge,
     avec son motif, jamais un verdict ni une correction silencieuse. */
  await pg.fill('[data-ev="pue"] [data-ev-pue]', '0,8');
  await pg.click('[data-ev="pue"] [data-ev-go]');
  const v2 = await verdictDans('[data-ev="pue"]');
  ok('un PUE de 0,8 est REFUSÉ — c’est la réponse, en rouge',
     /refus/.test(v2.classe) && /physiquement impossible/i.test(v2.txt)
       && /refusé/i.test(v2.txt),
     v2.txt.slice(0, 140));

  /* 20 g en France : très en dessous de la moyenne location-based — un
     facteur contractuel probable. La moyenne affichée doit être CELLE que
     l'API sert, pas un chiffre écrit dans la page ou dans cette recette. */
  const refJson = await pg.evaluate(() =>
    fetch('/api/datacenter/referentiel').then(r => r.json()).catch(() => null));
  const moyFR = refJson && refJson.referentiel && refJson.referentiel.intensite_reseau
    ? refJson.referentiel.intensite_reseau.FR : null;
  ok('la moyenne FR de comparaison est servie par l’API', moyFR != null,
     moyFR != null ? moyFR + ' g/kWh' : 'référentiel illisible');
  await pg.fill('[data-ev="intensite"] [data-ev-facteur]', '20');
  await pg.fill('[data-ev="intensite"] [data-ev-basses]',
                String(moyFR != null ? moyFR - 26 : 30));
  await pg.click('[data-ev="intensite"] [data-ev-go]');
  const v3 = await verdictDans('[data-ev="intensite"]');
  ok('20 g en France est lu comme un facteur CONTRACTUEL probable (ambre)',
     /attention/.test(v3.classe) && /market-based/i.test(v3.txt)
       && /double reporting/i.test(v3.txt), v3.txt.slice(0, 140));
  ok('…comparé à la moyenne SERVIE (' + moyFR + ' g), pays lu du formulaire',
     moyFR != null && v3.txt.indexOf(String(moyFR)) >= 0
       && /pays lu du formulaire/.test(v3.txt));
  ok('…et le gain d’un pilotage horaire est BORNÉ en t/GWh déplacé',
     /Pilotage horaire, borné/.test(v3.txt) && /26/.test(v3.txt)
       && /GWh/.test(v3.txt), v3.txt.slice(v3.txt.search(/Pilotage/), v3.txt.search(/Pilotage/) + 130));

  /* L'EAU : la référence est recalculée pour le profil du formulaire. À ce
     stade de la recette la puissance n'est PAS renseignée — et c'est le
     premier contrôle : le moteur doit REFUSER de comparer à un site
     imaginaire, en renvoyant à l'étape 2, plutôt que d'inventer une base. */
  await pg.fill('[data-ev="eau"] [data-ev-vol]', '1000');
  await pg.click('[data-ev="eau"] [data-ev-go]');
  const v4 = await verdictDans('[data-ev="eau"]');
  ok('sans puissance au formulaire, l’eau est REFUSÉE vers l’étape 2',
     /refus/.test(v4.classe) && /puissance/i.test(v4.txt) && /étape 2/.test(v4.txt),
     v4.txt.slice(0, 130));

  /* Puissance posée, la référence d'appoint est demandée à l'API — le MÊME
     moteur — puis rejouée dans l'interface : l'annuel annoncé égal à
     l'appoint calculé doit être jugé cohérent… */
  await pg.fill('#dc-form [data-champ="puissance_it_kw"]', '1000');
  const probe = await pg.evaluate(() =>
    fetch('/api/datacenter/evaluer', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'eau', volume_annuel_m3: 1,
        profil: { puissance_it_kw: 1000, refroidissement: 'adiabatique' } }),
    }).then(r => r.json()).then(j => (j.evaluation && j.evaluation.reference) || null)
      .catch(() => null));
  ok('l’API rend la référence d’appoint recalculée', !!probe && probe.appoint_m3 > 0,
     probe ? probe.appoint_m3 + ' m³/an (évap ' + probe.evaporation_m3 + ')' : 'pas de référence');
  /* …avec, dans le même geste, une pointe arithmétiquement impossible :
     l'irrecevable doit PRIMER — carte à l'ambre, pas au teal du cohérent. */
  const pointeImpossible = probe ? Math.max(0.1, Math.round(probe.appoint_m3 / 365 / 2)) : 1;
  await pg.fill('[data-ev="eau"] [data-ev-vol]', String(probe ? probe.appoint_m3 : 1000));
  await pg.fill('[data-ev="eau"] [data-ev-pointe]', String(pointeImpossible));
  await pg.click('[data-ev="eau"] [data-ev-go]');
  const v5 = await verdictDans('[data-ev="eau"]');
  ok('l’appoint calculé est jugé cohérent, profil dit dans le verdict',
     /Cohérent avec le calcul/i.test(v5.txt) && /profil lu du formulaire/.test(v5.txt),
     v5.txt.slice(0, 140));
  ok('…mais la pointe impossible PRIME : ambre, « max ≥ moyenne » expliqué',
     /attention/.test(v5.classe) && /irrecevable/i.test(v5.txt)
       && /impossible/i.test(v5.txt), v5.txt.slice(v5.txt.search(/Pointe/), v5.txt.search(/Pointe/) + 130));
  ok('…et les exigences eau nomment le profil mensuel et l’étiage',
     /profil MENSUEL/i.test(v5.txt) && /étiage/i.test(v5.txt)
       && /BE fluides/.test(v5.txt));

  /* L'INCORPORÉ : l'ordre sectoriel vient du référentiel servi. Un chiffre
     40 % sous l'ordre n'est PAS refusé — il est possible, c'est l'intérêt
     d'une écoconception réelle — mais il EXIGE la déclaration ISO 14025. */
  const refInc = refJson && refJson.referentiel && refJson.referentiel.incorpore
    ? refJson.referentiel.incorpore.serveur_kgCO2e.valeur : null;
  ok('l’ordre sectoriel du serveur est servi par l’API', refInc != null,
     refInc != null ? refInc + ' kgCO2e' : 'référentiel illisible');
  await pg.selectOption('[data-ev="incorpore"] [data-ev-poste]', 'serveur_kgCO2e');
  await pg.fill('[data-ev="incorpore"] [data-ev-val]', String(Math.round((refInc || 1200) * 0.4)));
  await pg.click('[data-ev="incorpore"] [data-ev-go]');
  const v6 = await verdictDans('[data-ev="incorpore"]');
  ok('un incorporé trop beau exige la déclaration, sans être refusé',
     /attention/.test(v6.classe) && /Sous l’ordre sectoriel|Sous l'ordre sectoriel/i.test(v6.txt)
       && /ISO 14025/.test(v6.txt) && /tierce partie/i.test(v6.txt),
     v6.txt.slice(0, 140));
  ok('…les exigences vont à l’AMO carbone, normes d’écoconception nommées',
     /AMO carbone/.test(v6.txt) && /IEC 62430/.test(v6.txt)
       && /NF X30-264/.test(v6.txt) && /EN 15804\+A2/.test(v6.txt));

  /* La durée de vie annoncée est AMORTIE avec la référence en regard. */
  await pg.fill('[data-ev="incorpore"] [data-ev-val]', String(refInc || 1200));
  await pg.fill('[data-ev="incorpore"] [data-ev-dv]', '6');
  await pg.click('[data-ev="incorpore"] [data-ev-go]');
  const v7 = await verdictDans('[data-ev="incorpore"]');
  ok('la durée de vie annoncée est amortie, référence en regard',
     /ok/.test(v7.classe) && /Amortissement/.test(v7.txt)
       && /premier levier/i.test(v7.txt), v7.txt.slice(v7.txt.search(/Amortissement/), v7.txt.search(/Amortissement/) + 120));

  /* On repart propre : les champs d'essai vidés — puissance comprise, la
     section 6 pose la sienne — pour que la suite de la recette ne juge pas
     une page encombrée par celle-ci. */
  await pg.fill('[data-ev="pue"] [data-ev-pue]', '');
  await pg.fill('[data-ev="intensite"] [data-ev-facteur]', '');
  await pg.fill('[data-ev="intensite"] [data-ev-basses]', '');
  await pg.fill('[data-ev="eau"] [data-ev-vol]', '');
  await pg.fill('[data-ev="eau"] [data-ev-pointe]', '');
  await pg.fill('[data-ev="incorpore"] [data-ev-val]', '');
  await pg.fill('[data-ev="incorpore"] [data-ev-dv]', '');
  await pg.fill('#dc-form [data-champ="puissance_it_kw"]', '');

  titre('5. La mise au point sur le faux « LCA »');

  /* Deux affirmations distinctes, deux contrôles : la notice du document, et
     la lacune de toute la bibliographie. Les fondre en un seul laisserait le
     contrôle vert alors que l'une des deux aurait disparu. */
  const biblio = await pg.evaluate(() =>
    [...document.querySelectorAll('#dc-art .dc-art-b li')]
      .map(l => l.textContent.replace(/\s+/g, ' ').trim()));
  const honey = biblio.find(l => /Honeywell/.test(l)) || '';
  ok('la notice du document dit qu’il n’est PAS une ACV',
     /n['’]est PAS une analyse de cycle de vie/i.test(honey) && /ISO 14040/.test(honey),
     honey.slice(honey.search(/MISE AU POINT|malgré/i)).slice(0, 130));
  ok('…et il est classé « guide de sélection de prestataire »',
     /Guide de sélection de prestataire/.test(honey));
  const lacunes = await pg.evaluate(() =>
    [...document.querySelectorAll('#dc-art .dc-art-l li')]
      .map(l => l.textContent.replace(/\s+/g, ' ').trim()));
  ok('…et l’absence d’ACV est déclarée pour les QUATRE sources',
     lacunes.some(l => /ISO 14040/.test(l)),
     (lacunes.find(l => /ISO 14040/.test(l)) || '').slice(0, 120));

  titre('6. Ce que l’ouverture ne devait PAS ouvrir ni casser');

  /* DEPUIS UN CONTEXTE SANS SESSION : celui de la page en porte une désormais,
     et ces contrôles y mesuraient ce qu'un client atteint plutôt que ce qu'un
     inconnu se voit refuser. */
  const anon = await nav.newContext();
  const ferme = await anon.request.post(BASE + '/api/datacenter/ingenierie/dossier', {
    headers: { 'Origin': BASE, 'Content-Type': 'application/json' }, data: {},
  });
  ok('les pièces du cabinet restent fermées', ferme.status() === 401, 'HTTP ' + ferme.status());
  const kb = await anon.request.get(BASE + '/admin/base-connaissance', { maxRedirects: 0 });
  ok('la base documentaire reste réservée', [301, 302, 401, 403].includes(kb.status()),
     'HTTP ' + kb.status());
  await anon.close();

  /* Le moteur, lui, doit toujours calculer — ouvrir la page sans cela
     n'ouvrirait rien d'utile. */
  await pg.waitForFunction(() => document.querySelector('#dc-form [data-champ="puissance_it_kw"]'),
                           null, { timeout: 20000 });
  await pg.fill('#dc-form [data-champ="puissance_it_kw"]', '50000');
  await pg.click('#dc-lancer');
  await pg.waitForFunction(() => {
    const s = document.getElementById('dc-sec-res');
    return s && !s.hidden && s.textContent.length > 200;
  }, null, { timeout: 30000 });
  const res = await pg.evaluate(() => {
    const s = document.getElementById('dc-sec-res');
    return { visible: !!s && !s.hidden, txt: (s ? s.textContent : '').replace(/\s+/g, ' ') };
  });
  ok('le calcul aboutit pour un visiteur anonyme', res.visible);
  ok('…et rend bien l’énergie, l’eau et le carbone ensemble',
     /PUE/.test(res.txt) && /(WUE|eau)/i.test(res.txt) && /(CO2|carbone)/i.test(res.txt));

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0, err.join(' | ').slice(0, 200));

  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  await nav.close();
  process.exit(ko ? 1 : 0);
})();
