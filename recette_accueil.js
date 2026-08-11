/* L'ACCUEIL — ce que seul le vrai document peut prouver.
 *
 * Le matériau est éprouvé par tests/test_accueil.py. Ce qu'un test qui lit le
 * fichier NE PEUT PAS voir, et qui est ici :
 *
 *   · SUR COMBIEN DE LIGNES le titre retombe, et s'il déborde. Un titre de
 *     soixante-douze signes tient sur une maquette et se casse en six lignes
 *     sur un téléphone — le fichier ne dit rien de cela ;
 *   · si les liens d'ingénierie sont VISIBLES et cliquables, ou masqués par une
 *     règle de mise en page héritée ;
 *   · si la carte d'ingénierie s'affiche bien EN PREMIER à l'écran — la grille
 *     peut réordonner ce que la source ordonne.
 *
 * La leçon est acquise dans ce dépôt : j'ai désactivé une branche d'affichage
 * avec « if (false) » et le test Python est resté vert, parce que les chaînes
 * étaient toujours dans le fichier. Ce qui s'affiche se vérifie dans le
 * document.
 *
 *   POUR L'EXÉCUTER :  BASE=http://127.0.0.1:5404 node recette_accueil.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
let ko = 0;
const ok = (n, c, d) => {
  console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : ''));
  if (!c) ko++;
};
const titre = t => console.log('\n══ ' + t + ' ══\n');

const LARGEURS = [[1440, 900], [1240, 900], [900, 800], [420, 800]];
const PAGES = ['/ingenierie-datacenter', '/datacenter',
               '/strategie-durable-datacenter'];

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e)));

  titre('1. Le titre tient — à toutes les largeurs, sans déborder');

  for (const [w, h] of LARGEURS) {
    await pg.setViewportSize({ width: w, height: h });
    await pg.goto(BASE + '/', { waitUntil: 'networkidle' });
    const o = await pg.evaluate(() => {
      const t = document.querySelector('h1');
      const r = t.getBoundingClientRect();
      const ligne = parseFloat(getComputedStyle(t).lineHeight);
      return { lignes: Math.round(r.height / ligne), large: r.width,
               ecran: document.documentElement.clientWidth,
               deborde: document.documentElement.scrollWidth
                        > document.documentElement.clientWidth + 1,
               texte: t.textContent.replace(/\s+/g, ' ').trim() };
    });
    ok(w + ' px : ' + o.lignes + ' ligne(s)', o.lignes <= (w < 600 ? 7 : 4),
       o.texte.slice(0, 48) + '…');
    ok('…rien ne déborde en largeur', !o.deborde,
       o.large + ' px de titre pour ' + o.ecran + ' px d’écran');
  }

  titre('2. LE POINT QUI DÉCIDE : l’ingénierie se voit, et elle est en tête');

  await pg.setViewportSize({ width: 1440, height: 900 });
  await pg.goto(BASE + '/', { waitUntil: 'networkidle' });

  const carte = await pg.evaluate(() => {
    const c = [...document.querySelectorAll('#offres .card')];
    if (!c.length) return null;
    const p = c[0].getBoundingClientRect();
    return { premier: (c[0].querySelector('h3') || {}).textContent || '',
             total: c.length,
             hauteur: Math.round(p.top + window.scrollY),
             autres: c.slice(1, 3).map(x => Math.round(
               x.getBoundingClientRect().top + window.scrollY)) };
  });
  ok('la première carte des domaines est l’ingénierie',
     carte && /ngénierie de centres de données/.test(carte.premier),
     carte ? carte.premier : 'aucune carte');
  ok('…et elle est bien la plus HAUTE à l’écran, pas seulement dans la source',
     carte && carte.autres.every(y => y >= carte.hauteur),
     carte ? carte.hauteur + ' px vs ' + carte.autres.join(', ') : '—');

  titre('3. Les trois modules sont atteignables depuis l’accueil');

  for (const cible of PAGES) {
    const o = await pg.evaluate((c) => {
      const a = [...document.querySelectorAll('a[href="' + c + '"]')];
      const vus = a.filter(x => {
        const r = x.getBoundingClientRect();
        const s = getComputedStyle(x);
        return r.width > 0 && r.height > 0 && s.visibility !== 'hidden'
          && s.display !== 'none';
      });
      return { n: a.length, vus: vus.length,
               libelle: (vus[0] || a[0] || {}).textContent || '' };
    }, cible);
    ok(cible + ' est proposé et VISIBLE', o.vus > 0,
       o.n + ' lien(s), ' + o.vus + ' visible(s) — « '
       + o.libelle.replace(/\s+/g, ' ').trim() + ' »');
  }

  /* Un lien visible qui répond 404 vaut un lien absent : on CLIQUE, et on
     regarde où l'on atterrit.
     « redirect: manual » était un piège que je me suis tendu : il rend un
     statut 0 opaque, que mon contrôle lisait comme « inférieur à 400 » et
     déclarait vert. Il aurait été vert sur une page inexistante.

     ET C'EST CE CLIC QUI A TROUVÉ LE DÉFAUT : le bouton du bandeau menait à
     /connexion. La règle est donc celle-ci — un lien qui ANNONCE l'accès
     client a le droit d'y mener ; un lien muet, non. */
  /* LIRE L'ÉTIQUETTE SUR LA PAGE D'ACCUEIL, PAS SUR CELLE OÙ L'ON VIENT
     D'ATTERRIR. La lecture était faite avant l'appel, sur « la page courante » —
     qui, dès la deuxième itération, était la destination du clic précédent,
     c'est-à-dire /connexion. Deux liens parfaitement étiquetés étaient donc
     déclarés muets. Elle se fait maintenant DANS la fonction, juste après le
     chargement de l'accueil, quand la page est bien celle qu'on croit. */
  const atterrir = async (cible) => {
    await pg.goto(BASE + '/', { waitUntil: 'networkidle' });
    const annonce = await pg.evaluate((c) => [...document.querySelectorAll(
      'a[href="' + c + '"]')].some(
        a => /accès client/i.test(a.textContent)), cible);
    const [n] = await Promise.all([
      pg.waitForNavigation({ waitUntil: 'domcontentloaded' }),
      pg.click('a[href="' + cible + '"]'),
    ]);
    return { statut: n.status(), chemin: new URL(pg.url()).pathname, annonce,
             titre: (await pg.title()).slice(0, 46) };
  };

  for (const cible of PAGES) {
    const a = await atterrir(cible);
    const annonce = a.annonce;
    const mur = a.chemin === '/connexion';
    ok('cliquer « ' + cible + ' » ne surprend pas le visiteur',
       a.statut < 400 && (a.chemin === cible || (mur && annonce)),
       'HTTP ' + a.statut + ' sur ' + a.chemin + ' — ' + a.titre
       + (mur ? (annonce ? ' (annoncé : accès client)'
                         : ' ⟵ MUR NON ANNONCÉ') : ''));
  }

  titre('3 bis. La page à compte existe VRAIMENT derrière son mur');

  /* Une étiquette « accès client » posée devant une route morte se lirait
     exactement comme une étiquette posée devant une page saine. On se connecte,
     et on reclique. */
  await pg.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg.evaluate(async ([e, m]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: m }) }),
    [process.env.RECETTE_EMAIL || 'recette@local.test',
     process.env.RECETTE_MDP || 'RecetteLocale!2026']);
  for (const cible of PAGES) {
    const a = await atterrir(cible);
    ok('connecté, « ' + cible + ' » ouvre bien sa page',
       a.statut < 400 && a.chemin === cible,
       'HTTP ' + a.statut + ' sur ' + a.chemin + ' — ' + a.titre);
  }
  await pg.goto(BASE + '/', { waitUntil: 'networkidle' });

  titre('4. Le bandeau et le chapeau disent les deux métiers');

  const dit = await pg.evaluate(() => {
    const t = (s) => (document.querySelector(s) || {}).textContent || '';
    return { bandeau: t('.eyebrow').replace(/\s+/g, ' ').trim(),
             chapeau: t('.lead').replace(/\s+/g, ' ').trim() };
  });
  ok('le bandeau nomme l’ingénierie ET la cybersécurité',
     /ngénierie de projets/.test(dit.bandeau)
     && /ybersécurité industrielle/.test(dit.bandeau), dit.bandeau);
  ok('le chapeau ne promet pas ce que la page ne tient pas',
     /maîtrise d.œuvre/i.test(dit.chapeau) && /IEC/.test(dit.chapeau),
     dit.chapeau.slice(0, 90) + '…');

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  await nav.close();
  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  process.exit(ko ? 1 : 0);
})();
