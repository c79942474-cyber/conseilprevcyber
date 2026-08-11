/* Le questionnaire des quatre perspectives, vu par un visiteur sans compte.
 *
 * POURQUOI UNE RECETTE NAVIGATEUR EN PLUS DES TESTS PYTHON. Les tests Python
 * prouvent que le module ignore une note scientifique glissée par le client, et
 * qu'une absence de réponse ne devient jamais un zéro. Ils ne prouvent RIEN sur
 * le FORMULAIRE : c'est lui qui décide de ce que le client peut saisir, et
 * c'est là que la règle se perd. Un sélecteur « science » ajouté par
 * distraction, un pré-remplissage « secondaire » posé pour faire joli — le
 * module resterait juste, et la page recueillerait autre chose que ce qu'elle
 * annonce.
 *
 * CE QU'ON PROTÈGE, DANS L'ORDRE D'IMPORTANCE :
 *
 *   1. TROIS SÉLECTEURS PAR ENJEU, JAMAIS QUATRE. La science est affichée,
 *      jamais proposée à la saisie.
 *   2. AUCUN PRÉ-REMPLISSAGE. Chaque sélecteur ouvre sur « non instruit », et
 *      chaque contexte sur « non renseigné ». Ce qui n'est pas répondu doit se
 *      voir dans le livrable.
 *   3. LES DIVERGENCES SURVIVENT À L'AFFICHAGE. Un enjeu retenu par la seule
 *      perception et un enjeu retenu par les seules données apparaissent tous
 *      deux, sous leur nom propre.
 *   4. LES ALERTES SONT EN TÊTE. Placées après les conclusions, elles se
 *      lisent après que le lecteur s'est félicité du résultat — c'est-à-dire
 *      jamais.
 *   5. L'EXPORT EST FERMÉ, ET IL LE DIT. Un refus muet enverrait le lecteur
 *      vérifier ses réponses alors qu'il lui manque une session.
 *
 * POUR L'EXÉCUTER — aucune session nécessaire pour le questionnaire, et c'est
 * le sujet :
 *     BASE=http://127.0.0.1:5404 node recette_strategie_dd.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
let ko = 0;
const ok = (n, c, d) => { console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : '')); if (!c) ko++; };
const titre = (t) => console.log('\n══ ' + t + ' ══\n');

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1400, height: 1100 } });
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

  titre('1. Le questionnaire s’ouvre sans compte');

  const rep = await pg.goto(BASE + '/strategie-durable-datacenter', { waitUntil: 'networkidle' });
  ok('la page répond', rep && rep.status() === 200, rep ? 'HTTP ' + rep.status() : 'pas de réponse');
  if (!rep || rep.status() !== 200) { await nav.close(); process.exit(2); }
  ok('…et ne renvoie plus vers la connexion', !/\/connexion/.test(pg.url()), pg.url());
  /* CONTRÔLE INVERSÉ PAR LA POLITIQUE D'ACCÈS. Il exigeait AUCUN cookie — la
     page était ouverte. Elle est maintenant réservée : c'est l'absence de
     session qui trahirait une connexion ratée, et tout ce qui suit ne
     mesurerait alors que le formulaire de connexion. */
  const ck = await ctx.cookies();
  ok('…et la session est bien établie', ck.some(c => c.name === 'cpc_session'),
     ck.map(c => c.name).join(', ') || 'aucun cookie');

  await pg.waitForFunction(() => document.querySelectorAll('#sd-enjeux [data-enjeu]').length > 0,
                           null, { timeout: 20000 });

  titre('2. LE contrôle : trois perspectives se notent, pas quatre');

  const f = await pg.evaluate(() => {
    const blocs = [...document.querySelectorAll('#sd-enjeux [data-enjeu]')];
    const notes = [...document.querySelectorAll('#sd-enjeux [data-note]')];
    return {
      enjeux: blocs.length,
      parEnjeu: [...new Set(blocs.map(b => b.querySelectorAll('[data-note]').length))],
      perspectives: [...new Set(notes.map(s => s.getAttribute('data-note')))].sort(),
      /* Aucun contrôle de saisie ne doit porter la science, sous quelque
         forme que ce soit — sélecteur, champ, curseur. */
      scienceSaisissable: document.querySelectorAll(
        '#sd-enjeux [data-note="science"], #sd-enjeux input[name*="science"]').length,
      /* …mais elle doit être AFFICHÉE : le client note en connaissance de
         cause, sinon la restitution est une surprise. */
      scienceAffichee: blocs.filter(b => /données en disent/i.test(b.textContent)).length,
      pieges: blocs.filter(b => /Le piège/i.test(b.textContent)).length,
      // Les libellés des perspectives, tels que le lecteur les voit
      sources: [...document.querySelectorAll('#sd-persp .sd-src')].map(x => x.textContent.trim()),
    };
  });
  ok('les vingt enjeux du registre sont proposés', f.enjeux === 20, f.enjeux + ' enjeu(x)');
  ok('TROIS sélecteurs par enjeu, et trois exactement',
     f.parEnjeu.length === 1 && f.parEnjeu[0] === 3, f.parEnjeu.join(' / '));
  ok('…et ce sont bien les trois perspectives du client',
     f.perspectives.join(',') === 'parties_prenantes,raison_etre,valeur',
     f.perspectives.join(' · '));
  ok('LA SCIENCE N’EST NULLE PART SAISISSABLE', f.scienceSaisissable === 0,
     f.scienceSaisissable + ' contrôle(s) de saisie');
  ok('…mais elle est affichée pour chaque enjeu', f.scienceAffichee === f.enjeux,
     f.scienceAffichee + '/' + f.enjeux);
  ok('…et chaque enjeu montre son piège', f.pieges === f.enjeux,
     f.pieges + '/' + f.enjeux);
  ok('l’en-tête dit qui répond à quoi',
     f.sources.filter(x => /données/i.test(x)).length === 1
     && f.sources.filter(x => /répondez/i.test(x)).length === 3,
     f.sources.join(' · '));

  titre('3. Aucun pré-remplissage : ce qui n’est pas répondu se voit');

  const vides = await pg.evaluate(() => ({
    notes: [...new Set([...document.querySelectorAll('#sd-enjeux [data-note]')].map(s => s.value))],
    contexte: [...new Set([...document.querySelectorAll('#sd-contexte [data-contexte]')].map(s => s.value))],
    ouvertes: [...new Set([...document.querySelectorAll('#sd-ouvertes [data-ouverte]')].map(t => t.value))],
    premiereOption: [...new Set([...document.querySelectorAll('#sd-enjeux [data-note]')]
      .map(s => s.options[0].textContent.trim()))],
    groupesActifs: document.querySelectorAll('#sd-enjeux [data-groupe][aria-pressed="true"]').length,
  }));
  ok('aucune note pré-remplie', vides.notes.length === 1 && vides.notes[0] === '',
     JSON.stringify(vides.notes));
  ok('aucun contexte pré-rempli', vides.contexte.length === 1 && vides.contexte[0] === '',
     JSON.stringify(vides.contexte));
  ok('aucune réponse ouverte pré-remplie',
     vides.ouvertes.length === 1 && vides.ouvertes[0] === '');
  ok('…et la première option dit « non instruit », pas « secondaire »',
     vides.premiereOption.every(t => /non instruit/i.test(t)),
     vides.premiereOption.join(' / '));
  ok('aucun porteur pré-sélectionné', vides.groupesActifs === 0);

  titre('4. Un questionnaire vide produit un livrable qui le dit');

  await pg.click('#sd-gen');
  await pg.waitForFunction(() => document.querySelectorAll('#sd-resultat .sd-l').length > 0,
                           null, { timeout: 30000 });
  const rien = await pg.evaluate(() => {
    const v = [...document.querySelectorAll('#sd-matrice [data-verdict]')]
      .map(x => x.getAttribute('data-verdict'));
    return {
      verdicts: v,
      nonInstruits: document.querySelectorAll('[data-verdict="non_instruit"] .sd-l').length,
      alertes: [...document.querySelectorAll('#sd-alertes .sd-al')].map(x => x.textContent.trim()),
    };
  });
  ok('tous les enjeux ressortent « non instruits »', rien.nonInstruits === 20,
     rien.nonInstruits + '/20');
  ok('…et aucun n’a basculé en « écarté »',
     rien.verdicts.indexOf('ecarte') === -1, rien.verdicts.join(' · '));
  ok('une alerte HAUTE le signale',
     rien.alertes.some(a => /non instruit/i.test(a)),
     (rien.alertes[0] || '').slice(0, 90));

  titre('5. Un cas réel : les divergences survivent à l’affichage');

  await pg.fill('[data-identite="projet"]', 'DC Nord — 20 MW');
  await pg.selectOption('[data-contexte="voisinage"]', 'tres_eleve');
  /* Le stress hydrique est laissé VIDE à dessein : il relèverait le conflit
     d'usage de l'eau, et supprimerait l'écart perception/données qu'on veut
     précisément démontrer sur cet enjeu-là. Le livrable signalera d'ailleurs
     le contexte manquant — c'est le comportement attendu. */
  await pg.fill('[data-ouverte="raison_etre_texte"]',
                "Héberger les charges d'IA sans déplacer le problème ailleurs.");
  /* Le jeu de notes est choisi pour produire CHACUN des verdicts. Deux pièges
     que j'ai d'abord ignorés, et qui rendaient le scénario contradictoire :
       · le contexte « habitat contigu » relève la science du bruit ET des
         groupes de secours à 3, ce qui supprime exactement l'écart
         perception/données qu'on voulait montrer. Le cas se démontre donc sur
         le conflit d'usage de l'eau, dont le contexte est laissé vide ;
       · un enjeu dont le registre donne la science pour « significatif » ne
         peut PAS être écarté par le client — c'est voulu. Seul un enjeu que
         les données elles-mêmes tiennent pour secondaire peut l'être. */
  const jeu = {
    // opinion très en avance sur les données : le cas de la capsule de café
    conflit_usage_eau: [1, 3, 1],
    // données très en avance sur l'opinion : le cas silencieux
    carbone_incorpore: [1, 0, 1],
    // porté par la seule raison d'être, sans demande ni effet sur les comptes
    fin_de_vie: [3, 1, 0],
    // convergence franche, et hors périmètre : coalition
    raccordement: [3, 3, 3],
    // convergence franche, dans notre périmètre : investissement
    pue: [3, 3, 3],
    // ni les données ni personne ne le portent : écarté explicitement
    emploi_local: [0, 0, 0],
    // données et parties prenantes au maximum, sans adhésion interne
    bruit: [1, 3, 1],
  };
  for (const [cle, v] of Object.entries(jeu)) {
    const p = ['raison_etre', 'parties_prenantes', 'valeur'];
    for (let i = 0; i < 3; i++) {
      await pg.selectOption('[data-enjeu="' + cle + '"] [data-note="' + p[i] + '"]',
                            String(v[i]));
    }
  }
  await pg.click('[data-enjeu="bruit"] [data-groupe="riverains"]');

  await pg.click('#sd-gen');
  await pg.waitForFunction(
    () => document.querySelectorAll('[data-verdict="croisement"] .sd-l').length > 0,
    null, { timeout: 30000 });
  await pg.waitForTimeout(500);

  const r = await pg.evaluate(() => {
    const lignes = {};
    document.querySelectorAll('#sd-matrice [data-verdict]').forEach(g => {
      g.querySelectorAll('[data-ligne]').forEach(l => {
        lignes[l.getAttribute('data-ligne')] = {
          verdict: g.getAttribute('data-verdict'),
          mode: (l.querySelector('.sd-mode') || {}).textContent || null,
          texte: l.textContent.replace(/\s+/g, ' '),
        };
      });
    });
    return {
      lignes,
      tensions: [...document.querySelectorAll('#sd-tensions .sd-t h3')].map(x => x.textContent.trim()),
      lectures: [...document.querySelectorAll('#sd-tensions .sd-t .l')].map(x => x.textContent.trim()),
      programme: document.querySelectorAll('#sd-programme .sd-l').length,
      // Les alertes doivent précéder tensions et matrice dans le document
      ordre: ['sd-alertes', 'sd-tensions', 'sd-matrice'].map(
        id => (document.getElementById(id) || {}).offsetTop || -1),
    };
  });

  ok('l’enjeu retenu par la PERCEPTION est là, sous son nom',
     (r.lignes.conflit_usage_eau || {}).verdict === 'perception',
     (r.lignes.conflit_usage_eau || {}).verdict);
  ok('l’enjeu retenu par les DONNÉES est là, sous son nom',
     (r.lignes.carbone_incorpore || {}).verdict === 'donnees',
     (r.lignes.carbone_incorpore || {}).verdict);
  ok('l’enjeu porté par la seule RAISON D’ÊTRE est là',
     (r.lignes.fin_de_vie || {}).verdict === 'raison_etre',
     (r.lignes.fin_de_vie || {}).verdict);
  ok('la convergence est classée au croisement',
     (r.lignes.pue || {}).verdict === 'croisement');
  ok('…avec le mode d’action « investir »',
     /Investir/i.test((r.lignes.pue || {}).mode || ''), (r.lignes.pue || {}).mode);
  ok('un enjeu qui déborde l’entreprise appelle une COALITION',
     /coalition/i.test((r.lignes.raccordement || {}).mode || ''),
     (r.lignes.raccordement || {}).mode);
  ok('l’enjeu que rien ne porte est ÉCARTÉ explicitement',
     (r.lignes.emploi_local || {}).verdict === 'ecarte',
     (r.lignes.emploi_local || {}).verdict);
  ok('…et un enjeu que le client note à zéro mais que les DONNÉES portent ne '
     + 'peut pas être écarté',
     (r.lignes.bruit || {}).verdict === 'croisement',
     (r.lignes.bruit || {}).verdict);
  ok('le contexte de site est répercuté sur l’enjeu concerné',
     /relevé de/i.test((r.lignes.bruit || {}).texte || ''),
     ((r.lignes.bruit || {}).texte || '').slice(0, 100));

  ok('les deux tensions sont nommées', r.tensions.length === 2, r.tensions.join(' · '));
  ok('…et la lecture cite les enjeux, pas des généralités',
     r.lectures.some(t => /Bruit|Carbone|Emploi|Raccordement/.test(t)),
     (r.lectures[0] || '').slice(0, 90));
  ok('le programme d’étude est produit', r.programme > 0, r.programme + ' ligne(s)');

  ok('LES ALERTES SONT EN TÊTE, avant les tensions et la matrice',
     r.ordre[0] > 0 && r.ordre[0] < r.ordre[1] && r.ordre[1] < r.ordre[2],
     r.ordre.join(' < '));

  titre('6. L’export — refusé à l’inconnu, rendu au client');

  /* CE QUE CETTE SECTION ÉPROUVAIT N'EXISTE PLUS TEL QUEL. Elle cliquait sur
     « exporter » depuis la page ouverte et vérifiait que le refus nommait sa
     cause. La page est maintenant réservée : personne ne peut être dessus sans
     session, et ce scénario n'est plus atteignable par l'interface. Reste ce
     qui compte encore, et qui compte davantage — la route elle-même, éprouvée
     depuis un contexte SANS session, puis rendue au client connecté. */
  const anon = await nav.newContext();
  const api = await anon.request.post(BASE + '/api/datacenter/strategie/export', {
    headers: { 'Origin': BASE, 'Content-Type': 'application/json' },
    data: { format: 'docx' },
  });
  ok('la route d’export refuse l’inconnu', api.status() === 401,
     'HTTP ' + api.status());
  const page_anon = await anon.request.get(BASE + '/strategie-durable-datacenter',
                                           { maxRedirects: 0 });
  ok('…et la page elle-même ne s’atteint plus sans compte',
     [301, 302].includes(page_anon.status()), 'HTTP ' + page_anon.status());
  await anon.close();

  /* L'AUTRE MOITIÉ : au client validé, le document sort. Sans ce contrôle, une
     porte fermée à tout le monde passerait pour une protection réussie. */
  await pg.click('#sd-docx');
  await pg.waitForFunction(
    () => !/^\s*$/.test((document.getElementById('sd-etat') || {}).textContent || ''),
    null, { timeout: 20000 }).catch(() => {});
  const msg = await pg.evaluate(() =>
    (document.getElementById('sd-etat') || {}).textContent || '');
  ok('au client connecté, l’export ne réclame plus de compte',
     !/compte|connect/i.test(msg), msg.slice(0, 110) || '(aucun message)');

  titre('7. Ce qui reste fermé — mesuré SANS session');

  /* CES CONTRÔLES S'EXÉCUTAIENT DANS LE CONTEXTE DE LA PAGE, jadis anonyme.
     Il porte maintenant une session : ils mesuraient donc ce qu'un client
     atteint, et non ce qu'un inconnu se voit refuser — c'est-à-dire l'inverse
     de ce que leur nom annonçait. Un contexte neuf rétablit la question. */
  const anon2 = await nav.newContext();
  for (const [chemin, nom] of [
    ['/api/datacenter/ingenierie/dossier', 'le dossier d’ingénierie'],
    ['/api/datacenter/export', 'l’export de note de calcul'],
  ]) {
    const x = await anon2.request.post(BASE + chemin, {
      headers: { 'Origin': BASE, 'Content-Type': 'application/json' }, data: {},
    });
    ok(nom + ' reste fermé à l’inconnu', x.status() === 401, 'HTTP ' + x.status());
  }
  await anon2.close();

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.join(' | ').slice(0, 200));

  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  await nav.close();
  process.exit(ko ? 1 : 0);
})();
