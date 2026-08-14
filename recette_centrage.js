/* TOUTES LES PAGES SONT-ELLES CENTRÉES — ET AUCUNE NE DÉBORDE-T-ELLE ?
 *
 * LE SYMPTÔME ET LA CAUSE NE SONT PAS AU MÊME ENDROIT. Une page « décalée sur
 * la gauche » n'a presque jamais un défaut de centrage : `.wrap` porte
 * `margin:0 auto` et le fait très bien. Ce qu'on voit est l'effet d'un
 * DÉBORDEMENT HORIZONTAL — un seul élément plus large que la fenêtre suffit à
 * élargir le document, et tout ce qui est centré se retrouve alors centré dans
 * une largeur qui n'est plus celle qu'on regarde. Le lecteur, lui, voit une
 * marge gauche nulle et une bande vide à droite.
 *
 * CE FICHIER MESURE DONC LES DEUX, ET NOMME LE COUPABLE :
 *
 *   1. LE DOCUMENT NE DÉBORDE PAS. `scrollWidth` ne doit pas dépasser
 *      `clientWidth`. Une tolérance d'un pixel absorbe les arrondis de
 *      sous-pixel, rien de plus.
 *   2. LE CONTENU EST CENTRÉ. Pour chaque conteneur `.wrap` visible, la marge
 *      gauche et la marge droite doivent être égales à 2 px près.
 *   3. QUAND ÇA DÉBORDE, ON DIT QUOI. Le contrôle remonte l'élément fautif —
 *      sa balise, sa classe, sa largeur — sinon le rapport oblige à rouvrir la
 *      page à la main pour chercher, et on ne le fait pas.
 *
 * ON MESURE SUR TROIS LARGEURS. Un débordement peut n'exister qu'en dessous
 * d'un point de rupture, ou seulement au-dessus : une seule mesure laisserait
 * passer la moitié des cas.
 *
 *   POUR L'EXÉCUTER :  BASE=http://127.0.0.1:5404 node recette_centrage.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
let ko = 0;
const ok = (n, c, d) => {
  console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : ''));
  if (!c) ko++;
};
const titre = t => console.log('\n══ ' + t + ' ══\n');

/* Les pages du site, y compris celles qui demandent un compte : la recette
   ouvre une session, sinon la moitié du site échapperait à la mesure. */
const PAGES = [
  '/', '/services', '/secteurs', '/etudes-de-cas', '/ressources', '/faq',
  '/about', '/vos-projets', '/contact', '/veille', '/diagnostic', '/nis2',
  '/mentions-legales', '/politique-confidentialite', '/conformite',
  '/operating-model', '/maturite-ot', '/feuille-de-route', '/continuite-ot',
  '/gestion-des-changements', '/architecture-cible', '/formation',
  '/gouvernance-ia', '/referentiel', '/analyse-de-risque', '/methodologie',
  '/exigences-systeme', '/exigences-composants', '/exigences-prestataires',
  '/developpement-securise', '/technologies-securite', '/programme-securite',
  '/gestion-correctifs', '/glossaire-62443', '/metriques-62443',
  '/juridique', '/relecture-contrat', '/datacenter', '/ingenierie-datacenter',
  '/decarbonation-datacenter', '/strategie-durable-datacenter',
  '/audit-conformite', '/tendances', '/connecter', '/guide-integration',
  '/demo', '/assistant',
];

const LARGEURS = [
  { nom: 'grand écran', w: 1520, h: 950 },
  { nom: 'ordinateur portable', w: 1280, h: 900 },
  { nom: 'téléphone', w: 390, h: 844 },
];

/* CE QUI DÉBORDE, ET DE COMBIEN. On parcourt tout le document et on retient
   les éléments dont le bord droit dépasse la largeur utile. On écarte ceux
   qui défilent DANS un conteneur prévu pour cela (`overflow-x:auto`) : un
   tableau large qui défile dans sa boîte est un choix, pas un défaut. */
const MESURE = (marge) => {
  const de = document.documentElement;
  const utile = de.clientWidth;
  const dedans = el => {
    for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {
      const o = getComputedStyle(n).overflowX;
      if (o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip') return true;
    }
    return false;
  };
  const fixe = el => {
    for (let n = el; n && n !== document.body; n = n.parentElement) {
      if (getComputedStyle(n).position === 'fixed') return true;
    }
    return false;
  };
  const coupables = [];
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    if (r.right <= utile + marge && r.left >= -marge) return;
    if (dedans(el)) return;
    /* LE TIROIR DE NAVIGATION N'EST PAS UN COUPABLE. Il est `position:fixed`
       et rangé hors champ par `translateX(-100%)` : c'est sa place au repos,
       et il n'élargit pas le document. Nommé à chaque fois, il accompagnait
       le vrai fautif dans le rapport et lui disputait la lecture — or un
       rapport qu'on apprend à survoler ne sert plus à rien.
       ON REMONTE LA LIGNÉE, ET PAS SEULEMENT L'ÉLÉMENT. Écarter le seul nœud
       `fixed` faisait surgir SON ENFANT à sa place, qui n'est pas fixe et
       hérite pourtant de sa position hors champ : le bruit changeait de nom
       sans disparaître. */
    if (fixe(el)) return;
    coupables.push({
      quoi: el.tagName.toLowerCase()
        + (el.id ? '#' + el.id : '')
        + (el.className && typeof el.className === 'string'
            ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : ''),
      gauche: Math.round(r.left), droite: Math.round(r.right),
      largeur: Math.round(r.width),
    });
  });
  /* Le PREMIER coupable dans l'arbre suffit : ses enfants débordent parce
     qu'il déborde, les lister tous noierait la cause dans ses effets. */
  const racines = coupables.filter((c, i) =>
    !coupables.slice(0, i).some(p => c.gauche >= p.gauche && c.droite <= p.droite));

  const wraps = [...document.querySelectorAll('.wrap')]
    .filter(w => w.getBoundingClientRect().width > 0)
    .map(w => {
      const r = w.getBoundingClientRect();
      return { g: Math.round(r.left), d: Math.round(utile - r.right),
               quoi: w.tagName.toLowerCase()
                 + (w.className ? '.' + String(w.className).trim().split(/\s+/)[0] : '') };
    });
  return {
    utile: utile, defile: de.scrollWidth, corps: document.body.scrollWidth,
    coupables: racines.slice(0, 4),
    /* Le centrage se juge sur l'ÉCART entre les deux marges, jamais sur leur
       valeur : elles changent avec la largeur de fenêtre, leur écart non. */
    decentres: wraps.filter(w => Math.abs(w.g - w.d) > 2).slice(0, 3),
    wraps: wraps.length,
  };
};

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1520, height: 950 } });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
  });
  await ctx.route('**/*', r => (['image', 'font', 'media'].includes(r.request().resourceType())
    ? r.abort() : r.continue()));
  const pg = await ctx.newPage();

  /* SESSION D'ABORD : sans compte, une bonne moitié des pages renverrait vers
     le formulaire de connexion, et la recette mesurerait quarante fois la même
     page en se croyant exhaustive. */
  await pg.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg.evaluate(async ([e, m]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: m }) }),
    [process.env.RECETTE_EMAIL || 'recette@local.test',
     process.env.RECETTE_MDP || 'RecetteLocale!2026']);

  const fautes = [];
  let mesurees = 0, redirigees = [];

  for (const ecran of LARGEURS) {
    titre(ecran.nom + ' — ' + ecran.w + ' px');
    await pg.setViewportSize({ width: ecran.w, height: ecran.h });
    let debordent = [], decentrees = [];

    for (const url of PAGES) {
      let rep;
      try {
        rep = await pg.goto(BASE + url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      } catch (e) { fautes.push(url + ' : ' + String(e).slice(0, 60)); continue; }
      if (!rep || rep.status() >= 400) { fautes.push(url + ' : HTTP ' + (rep && rep.status())); continue; }
      if (/\/connexion/.test(pg.url())) { redirigees.push(url); continue; }
      /* On laisse le rendu se poser : plusieurs blocs se peuplent par fetch, et
         c'est précisément un bloc peuplé après coup qui peut déborder. */
      await pg.waitForTimeout(700);
      const m = await pg.evaluate(MESURE, 1);
      mesurees++;
      if (m.defile > m.utile + 1) {
        debordent.push({ url: url, de: m.defile - m.utile, qui: m.coupables });
      }
      if (m.decentres.length) decentrees.push({ url: url, quoi: m.decentres });
    }

    ok('AUCUNE PAGE NE DÉBORDE HORIZONTALEMENT', debordent.length === 0,
       debordent.length
         ? debordent.length + ' page(s) : ' + debordent.slice(0, 3).map(d =>
             d.url + ' (+' + d.de + ' px' + (d.qui.length
               ? ' — ' + d.qui.map(c => c.quoi + ' ' + c.largeur + 'px').join(', ') : '') + ')')
             .join(' | ')
         : PAGES.length - redirigees.length + ' page(s) mesurée(s)');
    ok('…et le contenu y est centré, marge gauche = marge droite',
       decentrees.length === 0,
       decentrees.length
         ? decentrees.slice(0, 3).map(d => d.url + ' (' + d.quoi.map(w =>
             w.quoi + ' g=' + w.g + ' d=' + w.d).join(', ') + ')').join(' | ')
         : 'toutes');
  }

  titre('Ce que la mesure a pu voir');

  ok('toutes les pages annoncées ont été mesurées', fautes.length === 0,
     fautes.slice(0, 4).join(' | ') || mesurees + ' mesure(s)');
  /* UNE PAGE NON MESURÉE N'EST PAS UNE PAGE SAINE. Sans ce contrôle, une
     redirection généralisée rendrait ce fichier vert en n'ayant rien vu. */
  ok('…et aucune n’a échappé à la mesure faute de session',
     redirigees.length === 0, redirigees.join(' ') || 'aucune');

  await nav.close();
  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  process.exit(ko ? 1 : 0);
})();
