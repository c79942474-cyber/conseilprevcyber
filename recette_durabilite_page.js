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
