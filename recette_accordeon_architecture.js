/* RECETTE — LA LISTE DÉROULANTE DES QUESTIONS D'ARCHITECTURE
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * LA DEMANDE : « créer une liste déroulante » pour le bloc des questions qui
 * font tomber une architecture d'IA.
 *
 * CE QUI A ÉTÉ ÉCARTÉ, ET POURQUOI. Un menu à choix unique aurait masqué six
 * questions sur sept. Or la LISTE est l'objet : on la parcourt AVANT une revue
 * pour savoir ce qu'on va demander, et on déplie ensuite celle sur laquelle on
 * travaille. Les intitulés restent donc lisibles au repos ; seul ce qui se lit
 * une question à la fois — la mauvaise réponse, puis la pièce — attend le clic.
 *
 * POURQUOI CETTE RECETTE EXISTE, ALORS QUE DES RÈGLES pytest COUVRENT DÉJÀ LA
 * STRUCTURE. Les règles lisent le fichier ; elles savent que le gabarit émet
 * un `<details>` et que la réponse est écrite APRÈS le `</summary>`. Elles ne
 * peuvent pas savoir si le navigateur la masque pour autant — c'est une
 * propriété du rendu, pas du texte. Et le piège est réel : Chromium 141 rend
 * le contenu d'un `<details>` fermé sous `content-visibility`, où `offsetHeight`
 * vaut toujours son plein et où `getClientRects()` rend une boîte. Mesuré
 * ainsi, un volet parfaitement replié se lit comme grand ouvert.
 * `checkVisibility({contentVisibilityAuto:true})` est le seul instrument qui
 * dise la vérité ici, et c'est la raison d'être de ce fichier.
 *
 * CE QUE CES CONTRÔLES GARDENT :
 *
 *   1. AUTANT DE VOLETS QUE DE QUESTIONS AU MOTEUR — aucune perdue en route.
 *   2. AU REPOS, LES SEPT INTITULÉS SE LISENT. C'est la liste de revue ; un
 *      seul intitulé visible ferait un menu, pas une liste.
 *   3. AU REPOS, AUCUNE RÉPONSE NE SE LIT. Sans quoi le dépliement ne déplie
 *      rien et la page a seulement changé de bordures.
 *   4. RIEN N'EST OUVERT AU CHARGEMENT — sinon la première question passe pour
 *      la seule qui compte.
 *   5. LE CLIC OUVRE CELUI-LÀ, et le contenu devient réellement lisible.
 *   6. LES VOLETS SONT INDÉPENDANTS : ouvrir le second ne referme pas le
 *      premier. On compare deux questions en revue.
 *   7. LE CLAVIER FAIT LA MÊME CHOSE, et le focus se voit (WCAG 2.1.1, 2.4.7).
 *   8. L'ÉTAT OUVERT SE DISTINGUE DE L'ÉTAT FERMÉ AUTREMENT QUE PAR LE TEXTE
 *      APPARU — bordure et chevron, pour qui parcourt la liste des yeux.
 *   9. ET RIEN NE DÉBORDE À 390 px.
 *
 * Lancement :
 *     BASE=http://127.0.0.1:5732 node recette_accordeon_architecture.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const BASE = process.env.BASE || 'http://127.0.0.1:5732';

let ko = 0;
const ok = (t, cond, siKo, mesure) => {
  console.log((cond ? '  OK   ' : '  KO   ') + t
              + (mesure ? ' — ' + mesure : '')
              + (!cond && siKo ? ' — ' + siKo : ''));
  if (!cond) ko++;
};

/* L'INSTRUMENT. Passé en texte puis reconstruit dans la page : `checkVisibility`
   tient compte de `content-visibility`, ce que ni `offsetHeight` ni
   `getClientRects()` ne font sur un `<details>` replié. */
const VIS = "e => e && e.checkVisibility({checkVisibilityCSS:true,"
          + "contentVisibilityAuto:true,opacityProperty:true,visibilityProperty:true})";

(async () => {
  const nav = await chromium.launch();
  const page = await nav.newPage({ viewport: { width: 1280, height: 900 } });
  const err = [];
  page.on('pageerror', e => err.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') err.push('console: ' + m.text()); });

  console.log('\nRECETTE — liste déroulante des questions d’architecture\n');

  await page.goto(BASE + '/securite-ia', { waitUntil: 'networkidle' });

  /* COMBIEN LE MOTEUR EN DÉCLARE-T-IL ? On ne compare pas à sept écrit ici :
     le jour où une question s'ajoute au module, ce nombre suivrait tout seul,
     et un contrôle figé se mettrait à refuser un ajout légitime. */
  const attendu = await page.evaluate(async (base) => {
    const r = await fetch(base + '/api/ai-factory/referentiel',
                          { credentials: 'same-origin' });
    const d = await r.json();
    return (d && d.ok) ? d.referentiel.architecture.length : -1;
  }, BASE);

  const repos = await page.evaluate((vis) => {
    const f = new Function('e', 'return (' + vis + ')(e)');
    const ds = [...document.querySelectorAll('#cx-archi details.cx-q')];
    return {
      volets: ds.length,
      ouverts: ds.filter(d => d.open).length,
      intitules: ds.filter(d => f(d.querySelector('.cx-qt'))).length,
      vides: ds.filter(d => !(d.querySelector('.cx-qt') || {}).textContent
                            || !d.querySelector('.cx-qt').textContent.trim()).length,
      reponses: ds.filter(d => f(d.querySelector('dd.cx-mauvaise'))).length,
      pieces: ds.filter(d => f(d.querySelectorAll('dd')[1])).length,
      curseur: ds.length
        ? getComputedStyle(ds[0].querySelector('summary')).cursor : null
    };
  }, VIS);

  ok('autant de volets que de questions au moteur',
     attendu > 0 && repos.volets === attendu,
     'moteur ' + attendu + ', écran ' + repos.volets,
     repos.volets + ' volets');
  ok('les intitulés se lisent tous au repos',
     repos.volets > 0 && repos.intitules === repos.volets,
     repos.intitules + '/' + repos.volets + ' lisibles');
  ok('…et aucun n’est vide', repos.vides === 0, repos.vides + ' intitulé(s) vide(s)');
  ok('aucune mauvaise réponse ne se lit au repos',
     repos.reponses === 0, repos.reponses + ' réponse(s) déjà visibles');
  ok('aucune pièce ne se lit au repos',
     repos.pieces === 0, repos.pieces + ' pièce(s) déjà visibles');
  ok('rien n’est ouvert au chargement', repos.ouverts === 0,
     repos.ouverts + ' volet(s) ouverts');
  ok('l’intitulé s’annonce cliquable', repos.curseur === 'pointer',
     'cursor = ' + repos.curseur);

  /* ── LE CLIC ─────────────────────────────────────────────────────────── */
  const volets = page.locator('#cx-archi details.cx-q');
  await volets.nth(2).locator('summary').click();
  await page.waitForTimeout(600);
  const apres = await page.evaluate((vis) => {
    const f = new Function('e', 'return (' + vis + ')(e)');
    const ds = [...document.querySelectorAll('#cx-archi details.cx-q')];
    const d = ds[2];
    return {
      ouverts: ds.filter(x => x.open).length,
      reponse: f(d.querySelector('dd.cx-mauvaise')),
      piece: f(d.querySelectorAll('dd')[1]),
      texte: (d.querySelector('dd.cx-mauvaise') || {}).textContent || '',
      bordOuvert: getComputedStyle(d).borderTopColor,
      bordFerme: getComputedStyle(ds[0]).borderTopColor,
      chevOuvert: getComputedStyle(d.querySelector('.cx-chev')).transform,
      chevFerme: getComputedStyle(ds[0].querySelector('.cx-chev')).transform
    };
  }, VIS);

  ok('le clic ouvre un volet, et un seul', apres.ouverts === 1,
     apres.ouverts + ' ouvert(s)');
  ok('…la mauvaise réponse devient lisible', apres.reponse === true);
  ok('…la pièce aussi', apres.piece === true);
  ok('…et elle porte du texte', apres.texte.trim().length > 20,
     'longueur ' + apres.texte.trim().length);
  /* SANS CE CONTRÔLE, un volet ouvert et un volet fermé se ressembleraient
     pour qui parcourt la colonne des yeux sans lire. */
  ok('l’état ouvert se distingue par la bordure',
     apres.bordOuvert !== apres.bordFerme,
     'ouvert ' + apres.bordOuvert + ' = fermé ' + apres.bordFerme);
  ok('…et par le chevron', apres.chevOuvert !== apres.chevFerme,
     'ouvert ' + apres.chevOuvert + ' = fermé ' + apres.chevFerme);

  /* ── DEUX À LA FOIS : on compare deux questions en revue ─────────────── */
  await volets.nth(4).locator('summary').click();
  await page.waitForTimeout(400);
  const deux = await page.locator('#cx-archi details.cx-q[open]').count();
  ok('ouvrir un second volet ne referme pas le premier', deux === 2,
     deux + ' ouvert(s) au lieu de 2');

  /* ── LE CLAVIER ──────────────────────────────────────────────────────── */
  await volets.nth(2).locator('summary').click();   // on referme
  await volets.nth(4).locator('summary').click();
  await page.waitForTimeout(300);
  const s0 = volets.nth(0).locator('summary');
  await s0.focus();
  await page.keyboard.press('Shift+Tab');
  await page.keyboard.press('Tab');
  await page.waitForTimeout(150);
  const contour = await s0.evaluate(e => {
    const c = getComputedStyle(e);
    return { w: c.outlineWidth, style: c.outlineStyle,
             actif: document.activeElement === e,
             visible: e.matches(':focus-visible') };
  });
  await page.keyboard.press('Enter');
  await page.waitForTimeout(400);
  const ouvertClavier = await volets.nth(0).evaluate(e => e.open);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(400);
  const refermeClavier = await volets.nth(0).evaluate(e => e.open);

  ok('le clavier ouvre le volet (WCAG 2.1.1)', ouvertClavier === true);
  ok('…et le referme', refermeClavier === false);
  ok('…le focus au clavier atterrit bien sur l’intitulé', contour.actif === true,
     'l’élément actif n’est pas le summary');
  ok('…et il se voit (WCAG 2.4.7)',
     contour.visible && contour.style !== 'none' && parseFloat(contour.w) >= 1,
     'focus-visible=' + contour.visible + ', outline ' + contour.w + ' ' + contour.style);

  /* ── 390 px ──────────────────────────────────────────────────────────── */
  await page.setViewportSize({ width: 390, height: 900 });
  await page.waitForTimeout(300);
  const etroit = await page.evaluate(() => {
    const W = document.documentElement.clientWidth;
    const ds = [...document.querySelectorAll('#cx-archi details.cx-q')];
    return {
      debordPage: document.documentElement.scrollWidth - W,
      debordVolet: ds.filter(d => d.getBoundingClientRect().right > W + 1).length,
      cible: Math.min(...ds.map(d =>
        d.querySelector('summary').getBoundingClientRect().height))
    };
  });
  ok('la page ne défile pas de côté à 390 px', etroit.debordPage === 0,
     etroit.debordPage + ' px');
  ok('…aucun volet ne dépasse', etroit.debordVolet === 0,
     etroit.debordVolet + ' volet(s)');
  ok('…et la cible garde 24 px (WCAG 2.5.8)', etroit.cible >= 24,
     'plus petite ' + Math.round(etroit.cible) + ' px');

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  console.log('\n' + (ko === 0 ? 'tout est vert' : ko + ' contrôle(s) en échec') + '\n');
  await nav.close();
  process.exit(ko === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
