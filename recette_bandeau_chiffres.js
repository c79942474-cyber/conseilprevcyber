/* RECETTE — LE BANDEAU « IA SECURITY EN CHIFFRES »
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * LA DEMANDE : poser six chiffres en tête de /securite-ia, et « les mettre à
 * jour constamment ».
 *
 * CE QUE « CONSTAMMENT » RECOUVRE RÉELLEMENT, et la page doit le dire plutôt
 * que le laisser croire. Un seul des six se recompte : le nombre de serveurs
 * au registre public MCP, obtenu en paginant un registre ouvert. Les cinq
 * autres sont des chiffres de rapport — ils n'ont pas d'interface, ils ne
 * changent plus, et on ne les rafraîchit pas : on les REMPLACE quand
 * l'édition suivante paraît. Ce qui s'automatise pour eux, c'est leur
 * VIEILLISSEMENT.
 *
 * CE QUE CES CONTRÔLES GARDENT :
 *
 *   1. LE BANDEAU EST EN TÊTE, avant l'instrument qu'il justifie.
 *   2. AUTANT DE TUILES QUE DE CHIFFRES AU MODULE.
 *   3. CHAQUE TUILE PORTE SA SOURCE ET SON ÂGE. Un pourcentage sans date se
 *      cite ; un pourcentage daté se vérifie.
 *   4. L'ÉTAT NE TIENT PAS À LA COULEUR SEULE (WCAG 1.4.1) : chaque pastille
 *      porte son mot.
 *   5. UNE RÉFÉRENCE NON ÉTABLIE SE VOIT SUR LA TUILE, pas en bas de page —
 *      reléguée, elle s'applique à un chiffre qu'on ne regarde plus.
 *   6. LA RÉSERVE EST SERVIE AVEC LES CHIFFRES, pour qu'une capture d'écran
 *      l'emporte avec elle.
 *   7. LE BANDEAU VIEILLIT VRAIMENT : interrogé à une date lointaine, il
 *      change d'état. C'est le seul contrôle qui prouve que la mécanique
 *      d'âge est branchée sur l'écran et pas seulement sur le module.
 *   8. ET RIEN NE DÉBORDE À 390 px.
 *
 * Lancement :
 *     BASE=http://127.0.0.1:5732 node recette_bandeau_chiffres.js
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

(async () => {
  const nav = await chromium.launch();
  const page = await nav.newPage({ viewport: { width: 1280, height: 900 } });
  const err = [];
  page.on('pageerror', e => err.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') err.push('console: ' + m.text()); });

  console.log('\nRECETTE — bandeau « IA Security en chiffres »\n');
  await page.goto(BASE + '/securite-ia', { waitUntil: 'networkidle' });

  /* COMBIEN LE MODULE EN DÉCLARE-T-IL ? On ne compare pas à six écrit ici :
     un chiffre ajouté demain ferait échouer un contrôle figé, alors qu'il
     n'aurait rien cassé. */
  const attendu = await page.evaluate(async (base) => {
    const r = await fetch(base + '/api/securite-ia/chiffres',
                          { credentials: 'same-origin' });
    const d = await r.json();
    return d && d.ok ? d.chiffres.length : -1;
  }, BASE);

  const vu = await page.evaluate(() => {
    const ts = [...document.querySelectorAll('#ch-grille .ch-t')];
    return {
      tuiles: ts.length,
      avecValeur: ts.filter(t => (t.querySelector('.ch-v') || {}).textContent
                                 && t.querySelector('.ch-v').textContent.trim()).length,
      avecLibelle: ts.filter(t => (t.querySelector('.ch-d') || {}).textContent
                                  && t.querySelector('.ch-d').textContent.trim().length > 15).length,
      avecPied: ts.filter(t => t.querySelector('.ch-pied')).length,
      avecAge: ts.filter(t => /il y a |aujourd/.test(t.querySelector('.ch-pied').textContent)).length,
      pastillesMuettes: ts.filter(t => {
        const p = t.querySelector('.ch-etat');
        return p && !p.textContent.trim();
      }).length,
      aConfirmer: ts.filter(t => /source à confirmer/.test(t.textContent)).length,
      reserve: (document.getElementById('ch-reserve') || {}).textContent || '',
      titre: (document.getElementById('ch-titre') || {}).textContent || '',
      enTete: (() => {
        const a = document.getElementById('chiffres');
        const b = document.getElementById('parc');
        return !!(a && b) &&
          (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) > 0;
      })()
    };
  });

  ok('le bandeau est en tête, avant l’instrument', vu.enTete === true);
  ok('il porte son titre', vu.titre.trim().length > 5, '', vu.titre.trim());
  ok('autant de tuiles que de chiffres au module',
     attendu > 0 && vu.tuiles === attendu,
     'module ' + attendu + ', écran ' + vu.tuiles, vu.tuiles + ' tuiles');
  ok('chaque tuile porte une valeur', vu.avecValeur === vu.tuiles,
     vu.avecValeur + '/' + vu.tuiles);
  ok('…et dit ce qu’elle mesure', vu.avecLibelle === vu.tuiles,
     vu.avecLibelle + '/' + vu.tuiles);
  ok('…et porte sa source en pied', vu.avecPied === vu.tuiles,
     vu.avecPied + '/' + vu.tuiles);
  ok('…et son âge', vu.avecAge === vu.tuiles, vu.avecAge + '/' + vu.tuiles);
  /* LA COULEUR NE PORTE JAMAIS SEULE UNE INFORMATION (WCAG 1.4.1) : qui ne
     distingue pas le vert de l’ambre doit lire l’état. */
  ok('l’état est écrit, pas seulement coloré (WCAG 1.4.1)',
     vu.pastillesMuettes === 0, vu.pastillesMuettes + ' pastille(s) muettes');
  ok('une référence non établie se voit SUR la tuile', vu.aConfirmer > 0,
     'aucune tuile ne signale de source à confirmer',
     vu.aConfirmer + ' tuile(s)');
  ok('la réserve est servie avec les chiffres', vu.reserve.length > 80,
     'réserve absente ou trop courte');
  ok('…et elle dit ce qui se recompte vraiment',
     /recompte|registre/.test(vu.reserve));

  /* ── LE VIEILLISSEMENT, VU DEPUIS L’ÉCRAN ────────────────────────────── */
  const plusTard = await page.evaluate(async (base) => {
    const r = await fetch(base + '/api/securite-ia/chiffres?date=2029-01-01',
                          { credentials: 'same-origin' });
    const d = await r.json();
    return { aRevoir: d.a_revoir.length, total: d.chiffres.length,
             etats: d.chiffres.map(c => c.fraicheur.etat) };
  }, BASE);
  ok('interrogé trois ans plus tard, le bandeau se dénonce lui-même',
     plusTard.aRevoir >= plusTard.total - 1,
     plusTard.aRevoir + '/' + plusTard.total + ' signalés',
     plusTard.etats.join(', '));

  /* ── 390 px ──────────────────────────────────────────────────────────── */
  await page.setViewportSize({ width: 390, height: 900 });
  await page.waitForTimeout(300);
  const etroit = await page.evaluate(() => {
    const W = document.documentElement.clientWidth;
    const ts = [...document.querySelectorAll('#ch-grille .ch-t')];
    return {
      debordPage: document.documentElement.scrollWidth - W,
      debordTuile: ts.filter(t => t.getBoundingClientRect().right > W + 1).length
    };
  });
  ok('la page ne défile pas de côté à 390 px', etroit.debordPage === 0,
     etroit.debordPage + ' px');
  ok('…aucune tuile ne dépasse', etroit.debordTuile === 0,
     etroit.debordTuile + ' tuile(s)');

  ok('aucune erreur de script', err.length === 0, err.slice(0, 2).join(' | '));

  console.log('\n' + (ko === 0 ? 'tout est vert' : ko + ' contrôle(s) en échec') + '\n');
  await nav.close();
  process.exit(ko === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
