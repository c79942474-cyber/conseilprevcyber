/* LE DIAGNOSTIC EXPRESS — ce que seul le vrai parcours peut prouver.
 *
 * Le matériau est éprouvé par tests/test_diagnostic.py. Ce qu'un test qui lit
 * le source NE PEUT PAS voir, et qui est ici :
 *
 *   · que le bloc « centre de données » NE PARAÎT PAS quand rien ne le
 *     justifie. C'est ce qui en fait un bloc décisionnel plutôt qu'un pavé
 *     publicitaire : l'afficher à un agroalimentaire qui cherche de la
 *     segmentation en ferait du remplissage, et le remplissage apprend au
 *     lecteur à ne plus lire ;
 *   · qu'il paraît par SES DEUX CHEMINS — le secteur, et la priorité — parce
 *     qu'ils désignent deux personnes différentes : l'exploitant, et
 *     l'industriel qui construit sa propre salle sans être « du secteur » ;
 *   · que le premier module CHANGE réellement avec la situation, et que les
 *     deux autres restent présents, déclassés et non retirés ;
 *   · que le bloc Conseil & transformation rend des leviers DIFFÉRENTS pour
 *     des réponses différentes — une table qui rendrait toujours la même liste
 *     passerait tous les contrôles de fichier ;
 *   · que le seuil européen n'est pas imprimé deux fois au même écran.
 *
 * La leçon est acquise dans ce dépôt : j'ai désactivé une branche d'affichage
 * avec « if (false) » et le test Python est resté vert, parce que les chaînes
 * étaient toujours dans le fichier. Ce qui s'affiche se vérifie dans le
 * document.
 *
 *   POUR L'EXÉCUTER :  BASE=http://127.0.0.1:5404 node recette_diagnostic.js
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

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1280, height: 1000 } });
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e)));

  await pg.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg.evaluate(async ([e, m]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: m }) }), [EMAIL, MDP]);

  /* Dérouler les quatre questions et lire le résultat rendu. */
  const parcours = async (secteur, taille, situation, priorite) => {
    await pg.goto(BASE + '/diagnostic', { waitUntil: 'networkidle' });
    for (const [nom, val] of [['secteur', secteur], ['taille', taille],
                              ['situation', situation], ['priorite', priorite]]) {
      await pg.check('input[name="' + nom + '"][value="' + val + '"]');
      await pg.click('#nextBtn');
    }
    await pg.waitForSelector('#res.on', { timeout: 15000 });
    return pg.evaluate(() => {
      const txt = s => ((document.querySelector(s) || {}).textContent || '')
        .replace(/\s+/g, ' ').trim();
      const liens = s => [...document.querySelectorAll(s + ' a')]
        .map(a => a.getAttribute('href'));
      const dc = document.getElementById('resDcCard');
      return {
        dcVisible: !!dc && !dc.hidden && dc.offsetParent !== null,
        dcTxt: txt('#resDcTxt'),
        dcLiens: liens('#resDc'),
        dcSeuil: txt('#resDcCadre'),
        cadre: txt('#resCadreTxt'),
        badges: [...document.querySelectorAll('#resCadres .badge-cadre')]
          .map(b => b.textContent),
        ctTxt: txt('#resConseilTxt'),
        ctLiens: liens('#resConseil'),
        ctTexte: txt('#resConseil'),
        lectures: liens('#resReads'),
        demarche: liens('#resService'),
      };
    });
  };

  titre('1. LE POINT QUI DÉCIDE : le bloc ne paraît pas quand rien ne le justifie');

  const agro = await parcours('agro', 'moyenne', 'partiel', 'architecture');
  ok('un agroalimentaire ne voit AUCUN bloc centre de données',
     !agro.dcVisible, agro.dcVisible ? 'affiché — c’est du remplissage' : 'masqué');
  ok('…mais il voit bien les leviers de Conseil & transformation',
     agro.ctLiens.length === 3, agro.ctLiens.join(', '));

  titre('2. Et il paraît par SES DEUX CHEMINS');

  const expl = await parcours('datacenter', 'grande', 'encours', 'conformite');
  ok('par le SECTEUR — un exploitant de centre de données', expl.dcVisible,
     expl.dcLiens.join(', '));
  const indus = await parcours('manufacturing', 'moyenne', 'debut', 'datacenter');
  ok('par la PRIORITÉ — un industriel qui construit sa salle', indus.dcVisible,
     indus.dcLiens.join(', '));

  titre('3. Le premier module CHANGE avec la situation, les autres restent');

  const debut = await parcours('datacenter', 'moyenne', 'debut', 'conformite');
  const mature = await parcours('datacenter', 'moyenne', 'mature', 'conformite');
  ok('qui part d’une page blanche commence par la stratégie',
     debut.dcLiens[0] === '/strategie-durable-datacenter', debut.dcLiens[0]);
  ok('qui exploite déjà un site commence par la maîtrise d’œuvre',
     mature.dcLiens[0] === '/ingenierie-datacenter', mature.dcLiens[0]);
  ok('…et les trois modules restent proposés dans les deux cas',
     debut.dcLiens.length === 3 && mature.dcLiens.length === 3,
     debut.dcLiens.length + ' / ' + mature.dcLiens.length);
  ok('…c’est bien un DÉCLASSEMENT, pas un retrait',
     new Set(debut.dcLiens).size === 3 &&
     debut.dcLiens.slice().sort().join() === mature.dcLiens.slice().sort().join(),
     mature.dcLiens.join(', '));
  ok('la phrase d’entrée n’est pas la même non plus',
     debut.dcTxt !== mature.dcTxt && debut.dcTxt.length > 40,
     debut.dcTxt.slice(0, 64) + '…');

  titre('4. Le cadre du centre de données nomme les DEUX obligations');

  ok('NIS2 — infrastructure numérique, régime le plus exigeant',
     /infrastructure numérique/i.test(expl.cadre) &&
     expl.badges.some(b => /NIS2/.test(b)), expl.badges.join(' | '));
  ok('…ET la déclaration annuelle de la directive efficacité énergétique',
     /efficacité énergétique/i.test(expl.cadre) && /500 kW/.test(expl.cadre),
     expl.badges.join(' | '));
  ok('LE SEUIL N’EST PAS IMPRIMÉ DEUX FOIS au même écran',
     !expl.dcSeuil, expl.dcSeuil ? 'répété dans le bloc projet' : 'dit une seule fois');
  ok('…mais l’industriel, lui, le lit — son cadre ne le disait pas',
     /500 kW/.test(indus.dcSeuil), indus.dcSeuil.slice(0, 70) + '…');

  titre('4 bis. La démarche recommandée reste SENSÉE pour une construction');

  /* CE DÉFAUT NE S'EST VU QUE SUR UNE CAPTURE D'ÉCRAN. La règle « qui n'a rien
     de structuré commence par inventorier » est une règle de cybersécurité ;
     appliquée à une construction, elle recommandait d'inventorier les actifs
     OT d'un site qui n'existe pas encore. Aucune table ne pouvait le montrer :
     les deux morceaux étaient justes, c'est leur rencontre qui ne l'était pas. */
  ok('un projet neuf ne commence pas par un inventaire OT',
     indus.demarche[0] !== '/services',
     indus.demarche.join(', '));
  ok('…il commence par l’ingénierie de centre de données',
     indus.demarche[0] === '/ingenierie-datacenter', indus.demarche[0]);
  const cyberNeuf = await parcours('agro', 'moyenne', 'debut', 'visibilite');
  ok('…mais la règle tient toujours pour un parcours cyber',
     cyberNeuf.demarche.length === 2, cyberNeuf.demarche.join(', '));

  titre('5. Conseil & transformation : des leviers qui CHANGENT');

  const gouv = await parcours('manufacturing', 'grande', 'encours', 'gouvernance');
  const conf = await parcours('manufacturing', 'grande', 'encours', 'conformite');
  ok('deux priorités donnent deux jeux de leviers',
     gouv.ctLiens.join() !== conf.ctLiens.join(),
     gouv.ctLiens.join(', ') + '  ≠  ' + conf.ctLiens.join(', '));
  const encours = await parcours('manufacturing', 'grande', 'encours', 'gouvernance');
  const debutG = await parcours('manufacturing', 'grande', 'debut', 'gouvernance');
  ok('…et la situation réordonne SANS vider la liste',
     debutG.ctLiens[0] !== encours.ctLiens[0] && debutG.ctLiens.length === 3,
     debutG.ctLiens.join(', ') + '  vs  ' + encours.ctLiens.join(', '));
  ok('chaque levier porte le motif de son rang',
     (gouv.ctTexte.match(/ — /g) || []).length >= 3,
     gouv.ctTexte.slice(0, 90) + '…');
  ok('la phrase d’en-tête explique le classement',
     gouv.ctTxt.length > 40, gouv.ctTxt.slice(0, 70) + '…');

  titre('6. Les neuf pages de Conseil & transformation sont ATTEIGNABLES');

  /* Le test de fichier voit les adresses dans la table ; lui seul ne dit pas
     qu'une réponse réelle y conduit. On balaie les combinaisons. */
  const vus = new Set();
  for (const p of ['conformite', 'visibilite', 'architecture', 'gouvernance',
                   'ia', 'datacenter']) {
    for (const si of ['debut', 'partiel', 'encours', 'mature']) {
      const r = await parcours('manufacturing', 'moyenne', si, p);
      r.ctLiens.forEach(x => vus.add(x));
    }
  }
  const NEUF = ['/operating-model', '/maturite-ot', '/feuille-de-route',
                '/continuite-ot', '/gestion-des-changements',
                '/architecture-cible', '/formation', '/gouvernance-ia',
                '/relecture-contrat'];
  const jamais = NEUF.filter(x => !vus.has(x));
  ok('les neuf sont proposées par au moins une combinaison de réponses',
     jamais.length === 0, jamais.join(', ') || (vus.size + ' pages atteintes'));

  titre('7. Les liens mènent à de vraies pages');

  const cibles = [...new Set([...expl.dcLiens, ...gouv.ctLiens])];
  for (const c of cibles) {
    const r = await pg.evaluate(async (u) => (await fetch(u)).status, c);
    ok(c + ' répond', r < 400, 'HTTP ' + r);
  }

  ok('aucune erreur de script sur tout le parcours', err.length === 0,
     err.slice(0, 2).join(' | '));

  await nav.close();
  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  process.exit(ko ? 1 : 0);
})();
