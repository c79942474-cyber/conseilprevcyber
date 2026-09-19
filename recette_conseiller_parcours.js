/* RECETTE — LE CONSEILLER DE PARCOURS, ET LA FICHE QUI S'AGRANDIT
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * LA DEMANDE : agrandir le parcours choisi pour qu'il se lise, revoir la
 * pertinence des itinéraires, éviter les doublons, et aider le visiteur à
 * choisir celui qui le concerne.
 *
 * CE QUE LES RÈGLES PYTHON NE PEUVENT PAS VOIR. Elles lisent le moteur et la
 * source ; elles ne savent pas si la modale s'agrandit VRAIMENT, ni si les
 * questions se répondent, ni si le verdict remplit la liste déroulante. Ces
 * trois choses n'existent que dans un navigateur, et c'est ici qu'on les
 * mesure.
 *
 * UN PIÈGE, TENU EN MÉMOIRE : sous `content-visibility`, le contenu replié
 * d'un <details> a une boîte — offsetHeight ment. Seul `checkVisibility` avec
 * ses quatre drapeaux dit la vérité, et c'est lui qu'on emploie partout ici.
 *
 * LES CONTRÔLES :
 *   1-3.   La porte existe, elle est repliée, et ce qu'elle cache est bien caché.
 *   4-6.   Elle s'ouvre, les trois questions apparaissent, et chacune démarre
 *          sur sa réponse neutre — on ne force personne à trancher pour voir.
 *   7-9.   Trois réponses donnent un itinéraire NOMMÉ, un second, et une liste
 *          d'écartés PORTANT LEUR MOTIF.
 *   10-11. Le verdict se recalcule quand on change une réponse, et il change
 *          de gagnant quand le levier change — c'est la preuve que la
 *          troisième question sert à quelque chose.
 *   12-13. « Suivre ce parcours » remplit la liste déroulante et ouvre la
 *          fiche : le visiteur voit ce qui a été choisi POUR lui, et peut en
 *          changer.
 *   14-16. La carte s'agrandit à la lecture, revient à sa taille au choix, et
 *          le texte grossit avec elle.
 *   17.    La conclusion de l'itinéraire NOMME ce qu'on emporte de lui.
 *   18-19. Rien ne déborde, ni à 1400 px ni à 390 px.
 *   20.    Aucune erreur JavaScript de bout en bout.
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:8941';

let ok = 0, ko = 0;
function dit(bon, quoi, detail) {
  if (bon) { ok++; console.log('OK   ' + quoi + (detail ? '  — ' + detail : '')); }
  else { ko++; console.log('KO   ' + quoi + (detail ? '  — ' + detail : '')); }
}

const VISIBLE = `el => el && el.checkVisibility({checkVisibilityCSS:true,
  contentVisibilityAuto:true, opacityProperty:true, visibilityProperty:true})`;

(async () => {
  const b = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const pg = await b.newPage({ viewport: { width: 1400, height: 1000 } });
  const errs = [];
  pg.on('pageerror', e => errs.push(String(e)));

  await pg.goto(BASE + '/secteurs', { waitUntil: 'networkidle' });
  await pg.evaluate(() => document.getElementById('pc-open-drawer').click());
  await pg.waitForSelector('.pc-modal.on');

  /* 1-3 — la porte, repliée */
  const d0 = await pg.evaluate(`(() => {
    const v = ${VISIBLE};
    const d = document.querySelector('.pc-conseil');
    const q = document.querySelector('.pc-cq');
    const c = document.querySelector('.pc-card');
    return { porte: !!d, ouverte: d && d.hasAttribute('open'),
             questionsVues: v(q), largeur: Math.round(c.getBoundingClientRect().width),
             lecture: c.classList.contains('pc-lecture'),
             menus: document.querySelectorAll('.pc-selects select').length };
  })()`);
  dit(d0.porte, '1. la porte du conseiller existe');
  dit(!d0.ouverte, '2. elle est repliée au départ');
  dit(d0.questionsVues === false, '3. ce qu’elle cache est réellement caché',
      'checkVisibility=' + d0.questionsVues);

  /* 4-6 — elle s'ouvre, trois questions, neutres cochées */
  await pg.evaluate(() => document.querySelector('.pc-conseil > summary').click());
  await pg.waitForTimeout(250);
  const d1 = await pg.evaluate(`(() => {
    const v = ${VISIBLE};
    const q = document.querySelector('.pc-cq');
    const fs = [...document.querySelectorAll('.pc-cq fieldset')];
    return { vues: v(q), n: fs.length,
             legendes: fs.map(f => f.querySelector('legend').textContent.trim()),
             cochees: [...document.querySelectorAll('.pc-cq input:checked')].map(i => i.value),
             verdict: document.querySelector('#pc-verdict').textContent.trim().length };
  })()`);
  dit(d1.vues === true, '4. la porte s’ouvre et montre ses questions');
  dit(d1.n === 3, '5. trois questions', d1.legendes.join(' | '));
  dit(d1.cochees.length === 3 && d1.cochees.every(v => v === ''),
      '6. chacune démarre sur sa réponse neutre', JSON.stringify(d1.cochees));

  /* 7-9 — trois réponses : un retenu nommé, un second, des écartés motivés */
  async function repondre(o, dcl, lev) {
    await pg.evaluate(([a, b2, c]) => {
      const coche = (n, v) => { const r = document.querySelector(
        'input[name="pc-q-' + n + '"][value="' + v + '"]');
        r.checked = true; r.dispatchEvent(new Event('change', { bubbles: true })); };
      coche('objet', a); coche('declencheur', b2); coche('levier', c);
    }, [o, dcl, lev]);
    await pg.waitForTimeout(200);
    return pg.evaluate(() => {
      const z = document.querySelector('#pc-verdict');
      const prem = z.querySelector('.pc-v-card:not(.pc-v-second)');
      return { motif: z.querySelector('.pc-v-motif').textContent.trim(),
               retenu: prem && prem.querySelector('.pc-v-role span').textContent.trim(),
               pts: prem && prem.querySelector('.pc-v-pts').textContent.trim(),
               entree: prem && (prem.querySelector('.pc-v-entree') || {}).textContent,
               second: (z.querySelector('.pc-v-second .pc-v-role span') || {}).textContent,
               apport: (z.querySelector('.pc-v-apport') || {}).textContent,
               nEcartes: z.querySelectorAll('.pc-v-ec li').length,
               motifs: [...z.querySelectorAll('.pc-v-ec li')].map(l => l.textContent) };
    });
  }
  const v1 = await repondre('datacenter', 'projet', 'budget');
  dit(/coût|Économie/i.test(v1.retenu || ''), '7. l’itinéraire retenu est nommé', v1.retenu);
  dit(!!v1.entree && v1.entree.length > 30,
      '8. il dit de quelle situation il part', (v1.entree || '').slice(0, 70) + '…');
  dit(v1.nEcartes >= 8 && v1.motifs.every(m => /vous avez répondu/.test(m)),
      '9. chaque écarté porte un motif qui cite la réponse du visiteur',
      v1.nEcartes + ' écartés');

  /* 10-11 — le verdict suit les réponses, et le levier départage */
  const v2 = await repondre('datacenter', 'projet', 'technique');
  dit(v2.retenu !== v1.retenu,
      '10. changer une seule réponse change le conseil',
      v1.retenu + '  →  ' + v2.retenu);
  dit(/charge|systèmes d’information/i.test(v2.retenu || ''),
      '11. c’est bien le levier qui a départagé', v2.retenu);
  dit(!!v2.second && !!v2.apport,
      '11b. le second dit ce qu’il apporte', (v2.apport || '').slice(0, 80));

  /* 12-13 — le verdict remplit le menu, et ouvre la fiche */
  await pg.evaluate(() =>
    document.querySelector('.pc-v-card:not(.pc-v-second) .pc-v-go').click());
  await pg.waitForTimeout(600);
  const ap = await pg.evaluate(`(() => {
    const v = ${VISIBLE};
    const c = document.querySelector('.pc-card');
    return { role: document.querySelector('#pc-select').value,
             menuVu: v(document.querySelector('#pc-select')),
             etapes: document.querySelectorAll('#pc-fiche .pc-etape').length,
             lecture: c.classList.contains('pc-lecture'),
             largeur: Math.round(c.getBoundingClientRect().width),
             label: (document.querySelector('#pc-fiche .pc-e-label') || {}).textContent,
             taille: document.querySelector('#pc-fiche .pc-e-d')
               ? parseFloat(getComputedStyle(document.querySelector('#pc-fiche .pc-e-d')).fontSize) : 0,
             derniere: [...document.querySelectorAll('#pc-fiche .pc-e-d')].slice(-1)[0].textContent };
  })()`);
  dit(!!ap.role && ap.menuVu === true,
      '12. le verdict REMPLIT la liste déroulante au lieu de la remplacer',
      'rôle sélectionné = ' + ap.role);
  dit(ap.etapes >= 4, '13. la fiche de l’itinéraire s’ouvre', ap.etapes + ' étapes');

  /* 14-16 — la lecture agrandit, le choix rétrécit, le texte suit */
  dit(ap.lecture && ap.largeur > d0.largeur + 100,
      '14. la carte s’agrandit à la lecture', d0.largeur + ' px  →  ' + ap.largeur + ' px');
  await pg.evaluate(() => { const s = document.querySelector('#pc-select');
    s.value = ''; s.dispatchEvent(new Event('change', { bubbles: true })); });
  await pg.waitForTimeout(500);
  const retour = await pg.evaluate(() => { const c = document.querySelector('.pc-card');
    return { lecture: c.classList.contains('pc-lecture'),
             largeur: Math.round(c.getBoundingClientRect().width) }; });
  dit(!retour.lecture && retour.largeur === d0.largeur,
      '15. revenir au choix la ramène à sa taille', retour.largeur + ' px');
  dit(ap.taille >= 14, '16. le texte des étapes grossit avec elle', ap.taille + ' px');

  /* 17 — la conclusion nomme ce qu'on emporte */
  dit(/^Ce que vous y gagnez\s*:\s*Vous arrivez avec /.test((ap.derniere || '').trim()),
      '17. la conclusion nomme ce que CET itinéraire produit',
      (ap.derniere || '').trim().slice(0, 95) + '…');

  /* 18-19 — rien ne déborde */
  await pg.evaluate(() => { const s = document.querySelector('#pc-select');
    s.value = 'rssi'; s.dispatchEvent(new Event('change', { bubbles: true })); });
  await pg.waitForTimeout(500);
  const deb = await pg.evaluate(() => Math.max(0,
    document.documentElement.scrollWidth - document.documentElement.clientWidth));
  dit(deb === 0, '18. rien ne déborde à 1400 px', deb + ' px');
  await pg.setViewportSize({ width: 390, height: 844 });
  await pg.waitForTimeout(500);
  const deb2 = await pg.evaluate(() => Math.max(0,
    document.documentElement.scrollWidth - document.documentElement.clientWidth));
  dit(deb2 === 0, '19. rien ne déborde à 390 px', deb2 + ' px');

  /* 20 — aucune erreur */
  dit(errs.length === 0, '20. aucune erreur JavaScript', errs.join(' | ') || 'aucune');

  await b.close();
  console.log('\n' + ok + ' contrôles passés, ' + ko + ' en échec');
  process.exit(ko ? 1 : 0);
})().catch(e => { console.error('KO   la recette a rompu : ' + e); process.exit(1); });
