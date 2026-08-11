/* LES MODULES NUMÉROTÉS — ce que seul le vrai document peut prouver.
 *
 * Le matériau est éprouvé par tests/test_modules.py. Ce qu'un test qui lit le
 * source NE PEUT PAS voir, et qui est ici :
 *
 *   · combien de blocs battent À L'ARRIVÉE sur la page. C'est le point qui
 *     décide si le dispositif informe ou s'il fait un sapin de Noël : onze
 *     modules non parcourus qui clignotent ensemble ne signalent plus rien, et
 *     le lecteur apprend en trois secondes à ne plus les voir ;
 *   · combien de fois l'animation se répète RÉELLEMENT, telle que le
 *     navigateur la calcule — « infinite » glissé dans une règle plus
 *     spécifique ne se verrait pas dans le fichier ;
 *   · que la pastille disparaît quand le module SERT, et pas avant.
 *
 * La leçon est acquise ailleurs dans ce dépôt : j'ai désactivé une branche
 * d'affichage avec « if (false) » et le test Python est resté vert, parce que
 * les chaînes étaient toujours dans le fichier. Ce qui s'affiche se vérifie
 * dans le document.
 *
 *   POUR L'EXÉCUTER :  BASE=http://127.0.0.1:5404 node recette_modules.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
const EMAIL = process.env.RECETTE_EMAIL || 'recette@local.test';
const MDP = process.env.RECETTE_MDP || 'RecetteLocale!2026';
let ko = 0;
const ok = (n, c, d) => {
  console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : ''));
  if (!c) ko++;
};
const titre = t => console.log('\n══ ' + t + ' ══\n');

const PAGES = [
  ['/datacenter', 11],
  ['/ingenierie-datacenter', 8],
  ['/strategie-durable-datacenter', 5],
];

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1200, height: 900 } });
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e)));

  await pg.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg.evaluate(async ([e, m]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: m }) }), [EMAIL, MDP]);

  /* Repartir d'une page NEUVE : l'état est gardé dans le navigateur, et une
     recette qui hérite d'une visite précédente ne prouve rien. */
  const neuve = async (url) => {
    await pg.goto(BASE + url, { waitUntil: 'networkidle' });
    await pg.evaluate(() => window.MODULES && window.MODULES.reset());
    await pg.reload({ waitUntil: 'networkidle' });
    await pg.waitForSelector('.mod-bloc', { timeout: 25000 });
  };

  titre('1. Les blocs sont séparés, sur les trois pages');

  for (const [url, attendu] of PAGES) {
    await neuve(url);
    const o = await pg.evaluate(() => {
      const b = [...document.querySelectorAll('.mod-bloc')];
      const bord = b.length
        ? getComputedStyle(b[0]).borderLeftColor + ' / '
          + getComputedStyle(b[0]).borderLeftWidth : '';
      return { n: b.length,
               chips: document.querySelectorAll('.mod-chip').length,
               neufs: document.querySelectorAll('.mod-neuf').length,
               numeros: b.map(x => (x.querySelector('.rc-etape .n') || {}).textContent || '').map(s => s.trim()),
               bord };
    });
    ok(url + ' encadre ses ' + attendu + ' modules', o.n === attendu, o.n + ' bloc(s)');
    ok('…tous portent leur numéro', o.numeros.every(x => x.length > 0),
       o.numeros.join(','));
    /* LES CANAUX, PAS LA CHAÎNE. Un bloc non parcouru renforce son cadre et le
       navigateur rend alors « rgba(34, 211, 238, 0.55) » : une expression qui
       exigeait « rgb( » sans le « a » faisait échouer un contrôle sur une
       couleur parfaitement juste. On lit les nombres. */
    const canaux = (o.bord.match(/\d+/g) || []).slice(0, 3).join(',');
    ok('…et le cadre est bleu, marqué à gauche',
       canaux === '34,211,238' && parseFloat(o.bord.split('/')[1]) >= 3,
       o.bord);
    ok('…chaque module non parcouru porte sa pastille',
       o.chips === attendu && o.neufs === attendu,
       o.chips + ' pastille(s) / ' + o.neufs + ' non parcouru(s)');
  }

  titre('2. LE POINT QUI DÉCIDE : le signal ne part pas sur tout à la fois');

  await neuve('/datacenter');
  const arrivee = await pg.evaluate(
    () => document.querySelectorAll('.mod-bloc.mod-bat').length);
  ok('AUCUN module ne bat au chargement de la page', arrivee === 0,
     arrivee + ' bloc(s) battant — un signal posé sur tout ne signale plus rien');

  /* Le battement se déclenche à l'APPROCHE : on descend, et seuls les blocs
     visibles doivent s'être armés. */
  await pg.evaluate(() => document.querySelectorAll('.mod-bloc')[1].scrollIntoView());
  await pg.waitForTimeout(700);
  const apres = await pg.evaluate(() => ({
    bat: document.querySelectorAll('.mod-bloc.mod-bat').length,
    total: document.querySelectorAll('.mod-bloc').length,
  }));
  ok('…mais il se déclenche à l’approche', apres.bat > 0,
     apres.bat + ' bloc(s) à l’écran');
  ok('…et sur une PART seulement des modules, jamais tous',
     apres.bat < apres.total, apres.bat + ' / ' + apres.total);

  titre('3. Le battement est BORNÉ, tel que le navigateur le calcule');

  const anim = await pg.evaluate(() => {
    const b = document.querySelector('.mod-bloc.mod-bat');
    if (!b) return null;
    const s = getComputedStyle(b);
    return { iter: s.animationIterationCount, nom: s.animationName,
             duree: s.animationDuration };
  });
  ok('l’animation est bien posée', !!anim && anim.nom.indexOf('mod-bat') >= 0,
     anim ? anim.nom : 'aucune');
  ok('ELLE N’EST PAS PERPÉTUELLE', anim && anim.iter !== 'infinite',
     anim ? anim.iter + ' itération(s)' : '—');
  ok('…et elle se compte sur les doigts d’une main',
     anim && Number(anim.iter) >= 1 && Number(anim.iter) <= 5, anim && anim.iter);

  titre('4. Mouvement réduit : aucune animation, l’information demeure');

  const ctx2 = await nav.newContext({ viewport: { width: 1200, height: 900 },
                                      reducedMotion: 'reduce' });
  const pg2 = await ctx2.newPage();
  await pg2.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg2.evaluate(async ([e, m]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: m }) }), [EMAIL, MDP]);
  await pg2.goto(BASE + '/strategie-durable-datacenter', { waitUntil: 'networkidle' });
  await pg2.evaluate(() => window.MODULES && window.MODULES.reset());
  await pg2.reload({ waitUntil: 'networkidle' });
  await pg2.waitForSelector('.mod-bloc', { timeout: 25000 });
  await pg2.evaluate(() => document.querySelectorAll('.mod-bloc')[1].scrollIntoView());
  await pg2.waitForTimeout(700);
  const red = await pg2.evaluate(() => {
    const b = document.querySelector('.mod-bloc.mod-bat') || document.querySelector('.mod-bloc');
    return { anim: getComputedStyle(b).animationName,
             chips: document.querySelectorAll('.mod-chip').length,
             neufs: document.querySelectorAll('.mod-neuf').length };
  });
  ok('aucune animation ne tourne', red.anim === 'none', red.anim);
  ok('…et l’information demeure : pastilles et cadre renforcé',
     red.chips > 0 && red.neufs > 0, red.chips + ' pastille(s)');
  await ctx2.close();

  titre('5. « Sollicité » : par l’usage, et par la lecture');

  await neuve('/strategie-durable-datacenter');
  const avant = await pg.evaluate(() => document.querySelectorAll('.mod-chip').length);
  await pg.evaluate(() => {
    const s = document.querySelectorAll('.mod-bloc')[0];
    const c = s.querySelector('input, select, textarea, button');
    if (c) c.click();
  });
  await pg.waitForTimeout(400);
  const usage = await pg.evaluate(() => ({
    chips: document.querySelectorAll('.mod-chip').length,
    premierNeuf: document.querySelectorAll('.mod-bloc')[0].classList.contains('mod-neuf'),
  }));
  ok('se servir d’une commande éteint LE module concerné',
     !usage.premierNeuf, usage.premierNeuf ? 'toujours signalé' : 'éteint');
  ok('…et lui seul', usage.chips === avant - 1,
     avant + ' → ' + usage.chips + ' pastille(s)');

  /* Le module purement rédactionnel s'éteint à la LECTURE — deux secondes à
     l'écran, pas un défilement qui le traverse. */
  const nAvant = await pg.evaluate(() => window.MODULES.vus().length);
  await pg.evaluate(() => document.querySelectorAll('.mod-bloc')[1].scrollIntoView());
  await pg.waitForTimeout(600);
  const tot = await pg.evaluate(() => window.MODULES.vus().length);
  ok('un passage rapide n’éteint rien', tot === nAvant,
     nAvant + ' → ' + tot + ' après 0,6 s');
  await pg.waitForTimeout(2200);
  const lu = await pg.evaluate(() => window.MODULES.vus().length);
  ok('…mais deux secondes à l’écran valent lecture', lu > nAvant,
     nAvant + ' → ' + lu);

  titre('6. L’état survit à la visite suivante');

  await pg.goto(BASE + '/strategie-durable-datacenter', { waitUntil: 'networkidle' });
  await pg.waitForSelector('.mod-bloc', { timeout: 25000 });
  const retour = await pg.evaluate(() => ({
    chips: document.querySelectorAll('.mod-chip').length,
    blocs: document.querySelectorAll('.mod-bloc').length,
  }));
  ok('les modules déjà parcourus ne se resignalent pas',
     retour.chips < retour.blocs,
     retour.chips + ' pastille(s) sur ' + retour.blocs + ' blocs');

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  await nav.close();
  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  process.exit(ko ? 1 : 0);
})();
