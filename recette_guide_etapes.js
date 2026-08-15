/* LE PARCOURS GUIDÉ DES ÉTAPES NUMÉROTÉES — ce qu'il promet, il le tient.
 *
 * CE QU'ON PROTÈGE, ET POURQUOI CHAQUE POINT MÉRITE UN CONTRÔLE :
 *
 *   1. LE PARCOURS EXISTE LÀ OÙ IL Y A QUELQUE CHOSE À REMPLIR, et nulle part
 *      ailleurs. Une page de lecture qui affiche « Vous ne savez pas par où
 *      commencer ? » ajoute une commande sans rien apprendre.
 *
 *   2. LES ÉTAPES ANNONCÉES SONT CELLES QUE LA PAGE MONTRE. C'est LE point.
 *      Un parcours qui annonce huit étapes quand la page en affiche dix fait
 *      chercher ce qui n'existe pas — et c'est le défaut qu'une liste écrite à
 *      la main finit toujours par produire. On compare donc ce que le parcours
 *      déclare aux sections NUMÉROTÉES réellement présentes, et on vérifie que
 *      le cadrage non numéroté (« ◆ ») n'y entre pas.
 *
 *   3. CE QU'IL DIT À REMPLIR EXISTE VRAIMENT. « Trois listes déroulantes »
 *      doit correspondre à trois `select` dans la section visée, sans quoi le
 *      lecteur cherche une commande absente et conclut que la page est cassée.
 *
 *   4. L'AVANCEMENT EST CONSTATÉ, PAS DÉCLARÉ. Cliquer « suivante » ne doit
 *      rien marquer comme fait ; remplir un champ, oui. C'est la seule façon
 *      qu'un parcours dise quelque chose de vrai sur l'avancement — et c'est
 *      justement l'avancement qu'on vient lui demander.
 *
 *   5. IL NE CASSE RIEN. Il ne masque aucune section, ne déplace aucun bloc,
 *      et la page reste entière quand on le ferme.
 *
 *   6. IL EST UTILISABLE AU CLAVIER ET LISIBLE. Les commandes sont des
 *      boutons, l'étape ouverte est désignée autrement que par la couleur, et
 *      tout ce qu'il écrit passe le seuil AA.
 *
 *   POUR L'EXÉCUTER :  BASE=http://127.0.0.1:5404 node recette_guide_etapes.js
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const BASE = process.env.BASE || 'http://127.0.0.1:5404';
let ko = 0;
const ok = (n, c, d) => {
  console.log('  ' + (c ? 'OK ' : 'KO ') + '  ' + n + (d ? ' — ' + d : ''));
  if (!c) ko++;
};
const titre = t => console.log('\n══ ' + t + ' ══\n');

/* Les pages qui font remplir quelque chose, et donc doivent porter le
   parcours. Écrite ici, cette liste ne peut pas deviner une page ajoutée
   demain — mais elle empêche qu'une des quatre le perde en silence, ce qui est
   le risque réel. La complétude est éprouvée par la section 1 : toute page
   comptant deux sections numérotées ET des commandes doit l'avoir. */
const ATTENDUES = ['/datacenter', '/strategie-durable-datacenter',
                   '/relecture-contrat'];
/* Des pages de LECTURE : elles ne doivent PAS porter le parcours. */
const SANS = ['/about', '/faq', '/methodologie'];

(async () => {
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1400, height: 1000 } });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
  });
  await ctx.route('**/*', r => (['image', 'font', 'media'].includes(r.request().resourceType())
    ? r.abort() : r.continue()));
  const pg = await ctx.newPage();
  const err = [];
  pg.on('pageerror', e => err.push(String(e)));

  await pg.goto(BASE + '/connexion', { waitUntil: 'domcontentloaded' });
  await pg.evaluate(async ([e, m]) => fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: e, password: m }) }),
    [process.env.RECETTE_EMAIL || 'recette@local.test',
     process.env.RECETTE_MDP || 'RecetteLocale!2026']);

  /* NE PAS MOURIR SUR UNE ATTENTE : sans session la page renvoie vers la
     connexion, et un « Timeout » se lirait comme une panne d'outil là où la
     cause est une session absente — le limiteur de débit, le plus souvent. */
  const ouvrir = async (url) => {
    await pg.goto(BASE + url, { waitUntil: 'domcontentloaded' });
    if (/\/connexion/.test(pg.url())) return 'session';
    await pg.waitForTimeout(1100);
    return 'ok';
  };

  titre('1. Le parcours est là où il y a à remplir — et pas ailleurs');

  for (const url of ATTENDUES) {
    const e = await ouvrir(url);
    if (e === 'session') {
      ok('LE PARCOURS EST PRÉSENT SUR ' + url, false,
         'session non établie — limiteur de débit probable, relancer sur un processus NEUF');
      continue;
    }
    const v = await pg.evaluate(() => ({
      amorce: !!document.querySelector('#gd .gd-lanceur'),
      bouton: (document.querySelector('#gd-ouvrir') || {}).textContent || '',
      accroche: (document.querySelector('#gd .gd-lanceur-t b') || {}).textContent || '',
      annonce: (document.querySelector('#gd .gd-lanceur-t span') || {}).textContent || '',
    }));
    ok('le parcours est proposé sur ' + url, v.amorce);
    ok('…avec la même accroche que celui de l’ingénierie',
       /par où commencer/i.test(v.accroche), v.accroche.trim().slice(0, 46));
    /* L'ANNONCE EST CHIFFRÉE SUR LA PAGE. « Quelques étapes » ne prévient de
       rien : le lecteur doit savoir dans quoi il entre avant d'y entrer. */
    ok('…et l’annonce CHIFFRE ce qui attend le lecteur',
       /\d+\s+étape/.test(v.annonce), v.annonce.trim().slice(0, 72));
  }

  /* ON VÉRIFIE L'ABSENCE DU POINT D'ANCRAGE, ET NON L'ABSENCE DE L'AMORCE.
     Écrit sur l'amorce, ce contrôle ne pouvait pas tomber : le module refuse
     déjà de se dessiner sous deux étapes numérotées, et une page de lecture
     n'en a aucune — il restait donc vert même en câblant le parcours sur la
     page, ce que j'ai vérifié en le câblant vraiment. Il ne prouvait rien.
     Sur le point d'ancrage, il attrape ce qui arrive pour de bon : un en-tête
     recopié d'une page à l'autre, script et `<div id="gd">` compris. */
  for (const url of SANS) {
    const e = await ouvrir(url);
    if (e === 'session') continue;
    const v = await pg.evaluate(() => ({
      ancrage: !!document.querySelector('#gd'),
      script: !![...document.querySelectorAll('script[src]')]
        .find(s => /guide-etapes\.js/.test(s.getAttribute('src'))),
    }));
    ok('une page de lecture n’est pas câblée au parcours — ' + url,
       !v.ancrage && !v.script,
       (v.ancrage ? '#gd présent ' : '') + (v.script ? 'script chargé' : ''));
  }

  titre('2. LE POINT QUI DÉCIDE : les étapes annoncées sont celles de la page');

  for (const url of ATTENDUES) {
    if (await ouvrir(url) === 'session') continue;
    const c = await pg.evaluate(() => {
      /* Ce que la PAGE montre : sections numérotées, visibles ou non — une
         section masquée au départ (les résultats) reste une étape du chemin. */
      const vues = [...document.querySelectorAll('section .rc-etape')]
        .filter(t => t.querySelector('.n') && /^\d+$/.test(t.querySelector('.n').textContent.trim()))
        .map(t => t.querySelector('h2, h3') ? t.querySelector('h2, h3').textContent.trim() : '');
      const cadrages = [...document.querySelectorAll('section .rc-etape .n')]
        .filter(n => !/^\d+$/.test(n.textContent.trim())).length;
      const g = window.GUIDE_ETAPES;
      return { vues: vues, cadrages: cadrages,
               declarees: g ? g.etapes().map(e => e.titre) : null };
    });
    ok('les étapes déclarées sont EXACTEMENT celles affichées — ' + url,
       !!c.declarees && c.declarees.length === c.vues.length
         && c.declarees.every((t, i) => t === c.vues[i]),
       (c.declarees ? c.declarees.length : '—') + ' déclarée(s) / '
         + c.vues.length + ' affichée(s)');
    /* LE CADRAGE N'EST PAS UNE ÉTAPE. Sur /datacenter, « ◆ Le cadre » précède
       les dix étapes : le compter ferait « l'étape ◆ sur 11 ». */
    if (c.cadrages) {
      ok('…et le cadrage non numéroté n’est pas compté comme une étape — ' + url,
         c.declarees.length === c.vues.length,
         c.cadrages + ' section(s) de cadrage écartée(s)');
    }
  }

  titre('3. Ce qu’il dit à remplir existe vraiment dans la section visée');

  if (await ouvrir('/datacenter') !== 'session') {
    await pg.click('#gd-ouvrir');
    await pg.waitForTimeout(500);
    const v = await pg.evaluate(() => {
      const g = window.GUIDE_ETAPES;
      const i = g.courant();
      const e = g.etapes()[i];
      const r = g.aRemplir(i);
      const sec = document.getElementById(e.ancre);
      return {
        titre: e.titre,
        dit: (document.querySelector('.gd-quoi') || {}).textContent || '',
        listes: r.listes.length, champs: r.champs.length,
        vraiesListes: sec ? sec.querySelectorAll('select').length : -1,
        pourquoi: (document.querySelector('.gd-pq') || {}).textContent || '',
        numero: (document.querySelector('.gd-n') || {}).textContent || '',
      };
    });
    ok('le panneau s’ouvre sur une étape nommée', !!v.titre, v.titre);
    ok('…et annonce son rang, comme « étape 1 sur 10 »',
       /étape\s+\d+\s+sur\s+\d+/i.test(v.numero), v.numero.trim());
    ok('CE QU’IL DIT À REMPLIR CORRESPOND AUX COMMANDES PRÉSENTES',
       v.listes <= v.vraiesListes,
       v.listes + ' liste(s) annoncée(s) / ' + v.vraiesListes + ' dans la section');
    ok('…la phrase le dit en clair au lecteur',
       /liste|champ|case|se lit/i.test(v.dit), v.dit.trim().slice(0, 84));
    /* LE POURQUOI EST LE SEUL TEXTE ÉCRIT À LA MAIN, et le seul qui explique.
       Sans lui le parcours n'est qu'un compteur de champs. */
    ok('…et l’étape dit POURQUOI elle demande cela', v.pourquoi.length > 60,
       v.pourquoi.trim().slice(0, 84));
  }

  titre('4. L’avancement est CONSTATÉ, jamais déclaré');

  if (await ouvrir('/datacenter') !== 'session') {
    await pg.click('#gd-ouvrir');
    await pg.waitForTimeout(400);
    /* On avance dans le parcours SANS rien remplir : rien ne doit passer à
       « fait ». Un parcours qui se félicite d'un clic ment sur l'avancement. */
    const avant = await pg.evaluate(() =>
      window.GUIDE_ETAPES.etapes().map((_, i) => window.GUIDE_ETAPES.etat(i))
        .filter(s => s === 'fait').length);
    await pg.click('[data-gd-suiv]');
    await pg.waitForTimeout(300);
    await pg.click('[data-gd-suiv]');
    await pg.waitForTimeout(300);
    const apres = await pg.evaluate(() => ({
      faits: window.GUIDE_ETAPES.etapes().map((_, i) => window.GUIDE_ETAPES.etat(i))
        .filter(s => s === 'fait').length,
      courant: window.GUIDE_ETAPES.courant(),
    }));
    ok('avancer de deux étapes DÉPLACE le parcours', apres.courant === 2,
       'étape ' + apres.courant);
    ok('…et NE MARQUE RIEN comme fait', apres.faits === avant,
       avant + ' → ' + apres.faits + ' étape(s) faite(s)');

    /* ON ÉPROUVE LES DEUX SENS, ET C'EST INDISPENSABLE. Écrit en un seul sens,
       ce contrôle prenait la première étape à champs — celle du profil, qui
       arrive DÉJÀ remplie de ses valeurs par défaut — et lisait « fait →
       fait ». Il aurait été vert sur un module qui répond « fait » à tout.
       On vide donc d'abord, on constate le passage à « à faire », puis on
       remplit et on constate le retour à « fait ». */
    const bascule = await pg.evaluate(async () => {
      const g = window.GUIDE_ETAPES;
      const i = g.etapes().findIndex((_, k) => {
        const r = g.aRemplir(k);
        return r && r.champs.length > 0 && !r.oblig.length;
      });
      if (i < 0) return null;
      const r = g.aRemplir(i);
      const pose = (v) => { r.champs.forEach(c => {
        c.value = v; c.dispatchEvent(new Event('change', { bubbles: true })); }); };
      const cases = g.aRemplir(i).cases || [];
      cases.forEach(c => { c.checked = false; c.dispatchEvent(new Event('change', { bubbles: true })); });
      pose('');
      await new Promise(x => setTimeout(x, 320));
      const vide = g.etat(i);
      pose('10');
      await new Promise(x => setTimeout(x, 320));
      return { i: i, vide: vide, plein: g.etat(i), n: r.champs.length };
    });
    ok('VIDER UNE ÉTAPE LA REMET « À FAIRE »',
       !!bascule && bascule.vide === 'a-faire',
       bascule ? 'état à vide : ' + bascule.vide : 'aucune étape à champs trouvée');
    ok('…et LA REMPLIR LA FAIT BASCULER À « FAIT »',
       !!bascule && bascule.plein === 'fait',
       bascule ? bascule.vide + ' → ' + bascule.plein + ' (' + bascule.n + ' champ(s))'
               : 'aucune étape à champs trouvée');
  }

  titre('5. Il ne casse rien : la page reste entière');

  if (await ouvrir('/datacenter') !== 'session') {
    const av = await pg.evaluate(() => ({
      sections: document.querySelectorAll('main section').length,
      visibles: [...document.querySelectorAll('main section')].filter(s => !s.hidden).length,
      hauteur: document.documentElement.scrollHeight,
    }));
    await pg.click('#gd-ouvrir');
    await pg.waitForTimeout(600);
    const ap = await pg.evaluate(() => ({
      sections: document.querySelectorAll('main section').length,
      visibles: [...document.querySelectorAll('main section')].filter(s => !s.hidden).length,
      vises: document.querySelectorAll('.gd-vise').length,
    }));
    ok('AUCUNE SECTION N’EST MASQUÉE par l’ouverture du parcours',
       ap.visibles === av.visibles, av.visibles + ' → ' + ap.visibles);
    ok('aucune section n’est retirée du document',
       ap.sections === av.sections, av.sections + ' → ' + ap.sections);
    /* UNE SEULE section en relief : deux ne désignent plus rien. */
    ok('…et une SEULE section est mise en relief', ap.vises === 1,
       ap.vises + ' section(s) en relief');
    await pg.click('[data-gd-fermer]');
    await pg.waitForTimeout(300);
    const ferme = await pg.evaluate(() => ({
      panneau: !!document.querySelector('#gd-panneau'),
      vises: document.querySelectorAll('.gd-vise').length,
      amorce: !!document.querySelector('#gd .gd-lanceur'),
      visibles: [...document.querySelectorAll('main section')].filter(s => !s.hidden).length,
    }));
    ok('fermer le parcours le referme VRAIMENT', !ferme.panneau && ferme.vises === 0);
    ok('…l’amorce reste, pour pouvoir le rouvrir', ferme.amorce);
    ok('…et la page est intacte', ferme.visibles === av.visibles);
  }

  titre('6. Clavier, désignation et lisibilité');

  if (await ouvrir('/datacenter') !== 'session') {
    await pg.click('#gd-ouvrir');
    await pg.waitForTimeout(500);
    const a11y = await pg.evaluate(() => {
      const boutons = [...document.querySelectorAll('#gd button')];
      const p = document.querySelector('.gd-p');
      return {
        n: boutons.length,
        tousBoutons: boutons.every(b => b.tagName === 'BUTTON' && b.type === 'button'),
        expanded: (document.querySelector('#gd-ouvrir') || {}).getAttribute
          ? document.querySelector('#gd-ouvrir').getAttribute('aria-expanded') : null,
        jauge: !!(p && p.querySelector('.gd-jauge[aria-label]')),
        /* La désignation ne doit pas reposer sur la SEULE couleur (WCAG
           1.4.1) : l'étape ouverte du sommaire porte aussi `aria-current`. */
        courantMarque: !!document.querySelector('.gd-saut[aria-current="true"]'),
      };
    });
    ok('les commandes sont de vrais boutons', a11y.tousBoutons, a11y.n + ' bouton(s)');
    ok('…le lanceur annonce son état au lecteur d’écran',
       a11y.expanded === 'true', 'aria-expanded=' + a11y.expanded);
    ok('…la jauge porte un libellé, sinon elle ne dit rien à qui ne la voit pas',
       a11y.jauge);
    ok('…et l’étape ouverte est désignée autrement que par la couleur',
       a11y.courantMarque);

    const ctr = await pg.evaluate(() => {
      const lum = c => { const s = c.map(v => { v /= 255;
        return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); });
        return .2126 * s[0] + .7152 * s[1] + .0722 * s[2]; };
      const nb = t => { const m = String(t).match(/[\d.]+/g); return m ? m.map(Number) : [0, 0, 0, 0]; };
      /* `getComputedStyle` rend rgba(0,0,0,0) pour un fond hérité : on remonte
         jusqu'au premier fond OPAQUE en composant les opacités, sinon le
         rapport se calcule sur du blanc — faux et rassurant sur page sombre. */
      function fond(el) {
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
      const cibles = { 'l’annonce': '.gd-lanceur-t span', 'le rang': '.gd-n',
                       'le pourquoi': '.gd-pq', 'ce qu’il y a à remplir': '.gd-quoi',
                       'l’état': '.gd-etat', 'le sommaire': '.gd-toutes summary' };
      const out = [];
      for (const k in cibles) {
        const e = document.querySelector('#gd ' + cibles[k]);
        if (!e) { out.push({ nom: k, absent: true }); continue; }
        const s = getComputedStyle(e);
        const px = parseFloat(s.fontSize);
        const gras = parseInt(s.fontWeight, 10) >= 700;
        const l1 = lum(nb(s.color).slice(0, 3)), l2 = lum(fond(e));
        out.push({ nom: k, px: px,
          r: Math.round(((Math.max(l1, l2) + .05) / (Math.min(l1, l2) + .05)) * 100) / 100,
          seuil: (px >= 24 || (px >= 18.66 && gras)) ? 3 : 4.5 });
      }
      return out;
    });
    const sous = ctr.filter(x => x.absent || x.r < x.seuil);
    ok('TOUT CE QUE LE PARCOURS ÉCRIT PASSE LE SEUIL AA', sous.length === 0,
       sous.length
         ? sous.map(x => x.absent ? x.nom + ' ABSENT'
             : x.nom + ' ' + x.r + ':1 < ' + x.seuil + ' (' + x.px + 'px)').join(' · ')
         : ctr.map(x => x.r + ':1').join(' · '));
  }

  titre('LA FLÈCHE : elle désigne le prochain champ, et elle se déplace');

  /* CE QU'ELLE RÉPARE. Le panneau disait « à remplir : trois listes, deux
     champs » sans montrer LESQUELS — sur une étape qui en porte huit, dont
     six arrivent pré-remplies, le lecteur les cherche un par un. On éprouve
     donc trois choses : elle DÉSIGNE un champ réel, elle le NOMME aussi en
     toutes lettres (lecteur d'écran, champ hors écran), et elle SE DÉPLACE
     quand ce champ est renseigné — sinon elle enverrait deux fois au même
     endroit. */
  const ouvrirParcours = async () => {
    const dejaOuvert = await pg.evaluate(() =>
      window.GUIDE_ETAPES && window.GUIDE_ETAPES.ouvert());
    if (!dejaOuvert) {
      await pg.click('#gd-ouvrir');
      await pg.waitForFunction(() =>
        window.GUIDE_ETAPES && window.GUIDE_ETAPES.ouvert(), null, { timeout: 8000 });
    }
  };
  /* On se place sur une étape qui a VRAIMENT des champs à remplir : sur une
     étape de lecture, l'absence de flèche est le bon comportement, et le
     contrôle ne prouverait rien. */
  const idx = await pg.evaluate(() => {
    const G = window.GUIDE_ETAPES;
    for (let i = 0; i < G.etapes().length; i++) {
      const r = G.aRemplir(i);
      if (r && (r.listes.length + r.champs.length) > 0 && G.etat(i) !== 'a-venir') return i;
    }
    return -1;
  });
  ok('une étape à remplir existe pour éprouver la flèche', idx >= 0,
     idx >= 0 ? 'étape ' + (idx + 1) : 'aucune — le contrôle ne prouverait rien');

  let fl1 = null, pr1 = null;
  if (idx >= 0) {
    await ouvrirParcours();
    await pg.evaluate((i) => {
      const G = window.GUIDE_ETAPES;
      // On se rend à l'étape par les commandes du panneau, comme un lecteur.
      const b = document.querySelector('[data-gd-i="' + i + '"]');
      if (b) b.click();
    }, idx);
    await pg.waitForTimeout(500);
    pr1 = await pg.evaluate(() => window.GUIDE_ETAPES.prochain());
    fl1 = await pg.evaluate(() => window.GUIDE_ETAPES.fleche());
    ok('la flèche est POSÉE et visible à l’écran',
       !!(fl1 && fl1.visible), fl1 ? fl1.signe + ' en ' + fl1.x + ',' + fl1.y : 'absente');
    ok('…elle désigne un champ RÉEL de la page, nommé',
       !!(pr1 && pr1.nom && pr1.balise),
       pr1 ? pr1.balise + ' « ' + pr1.nom + ' » (' + pr1.quoi + ')' : 'rien de désigné');
    /* Le panneau dit la MÊME chose : les deux lisent la même fonction. */
    const dit = await pg.evaluate(() => {
      const e = document.querySelector('.gd-vers');
      return e ? e.textContent.replace(/\s+/g, ' ').trim() : '';
    });
    ok('…et le panneau le NOMME aussi, en toutes lettres',
       !!dit && (!pr1 || !pr1.nom || dit.indexOf(pr1.nom.slice(0, 18)) >= 0),
       dit.slice(0, 110) || 'aucune ligne « la flèche désigne »');
  }

  /* ELLE SE DÉPLACE — le cœur de la demande : « au fur et à mesure ». */
  if (idx >= 0 && pr1) {
    const bouge = await pg.evaluate((i) => {
      const G = window.GUIDE_ETAPES;
      const r = G.aRemplir(i);
      const tout = r.oblig.concat(r.listes, r.champs);
      const el = tout.find(e => !e.disabled && e.offsetParent !== null);
      if (!el) return null;
      const avant = (window.GUIDE_ETAPES.prochain() || {}).nom;
      // On remplit comme un lecteur : une valeur DIFFÉRENTE de celle vue en
      // arrivant, sinon le module ne la compte pas — et il a raison.
      if (el.tagName === 'SELECT') {
        const opts = [...el.options].filter(o => o.value && o.value !== el.value);
        if (!opts.length) return null;
        el.value = opts[0].value;
      } else {
        el.value = String((parseFloat(el.value) || 0) + 1234);
      }
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return { avant: avant };
    }, idx);
    await pg.waitForTimeout(400);
    const pr2 = await pg.evaluate(() => window.GUIDE_ETAPES.prochain());
    const fl2 = await pg.evaluate(() => window.GUIDE_ETAPES.fleche());
    ok('un champ rempli DÉPLACE la flèche — elle ne renvoie pas au même endroit',
       !!bouge && (!pr2 || pr2.nom !== bouge.avant),
       bouge ? '« ' + String(bouge.avant).slice(0, 34) + ' » → « '
               + String(pr2 ? pr2.nom : 'plus rien').slice(0, 34) + ' »'
             : 'aucun champ remplissable');
    ok('…et elle reste posée sur la page (ou disparaît si tout est fait)',
       (fl2 && fl2.visible) || pr2 === null,
       fl2 ? 'toujours là : ' + fl2.signe : 'retirée — étape complète');
  }

  /* AU FUR ET À MESURE, AU SENS STRICT : pendant la FRAPPE, sans quitter le
     champ. C'est la promesse propre à la flèche — le panneau, lui, ne se
     redessine qu'au `change`, et volontairement : le redessiner à chaque
     lettre volerait le curseur. Un contrôle qui émettrait `change` ne
     prouverait donc rien de la flèche ; celui-ci n'émet QUE `input`. */
  if (idx >= 0) {
    const frappe = await pg.evaluate((i) => {
      const G = window.GUIDE_ETAPES;
      const vise = G.prochain();
      if (!vise) return null;
      /* ON REMPLIT LE CHAMP QUE LA FLÈCHE DÉSIGNE — pas un autre. Remplir un
         champ quelconque de l'étape laisserait la cible inchangée, et le
         contrôle passerait même si la flèche ne suivait rien : c'est
         exactement ce qui s'est produit à la première écriture de ce test. */
      const r = G.aRemplir(i);
      const tout = r.oblig.concat(r.listes, r.champs, r.cases);
      const el = tout.find(e => {
        const nom = (e.getAttribute('data-champ') || e.id || '');
        return nom && nom === vise.champ;
      });
      if (!el) return null;
      const avant = vise.nom || '';
      /* `preventScroll` ISOLE CE QU'ON MESURE. Un `focus()` ordinaire fait
         défiler la page jusqu'au champ, le défilement repositionne la flèche,
         et le contrôle passerait alors même que l'écoute de la saisie serait
         débranchée — vérifié : c'est ce qui s'est produit. Ici, seule la
         saisie peut déplacer le repère. */
      el.focus({ preventScroll: true });
      const flAvant = G.fleche();
      // Le lecteur saisit : `input` SEUL, aucun `change` — il n'a pas quitté
      // le champ. C'est là que le panneau, lui, ne bouge pas encore.
      if (el.tagName === 'SELECT') {
        const opts = [...el.options].filter(o => o.value && o.value !== el.value);
        if (!opts.length) return null;
        el.value = opts[0].value;
      } else if (el.type === 'checkbox' || el.type === 'radio') {
        el.checked = !el.checked;
      } else {
        el.value = String((parseFloat(el.value) || 0) + 4321);
      }
      el.dispatchEvent(new Event('input', { bubbles: true }));
      return { avant: avant, flAvant: flAvant, balise: el.tagName,
               focusTenu: document.activeElement === el };
    }, idx);
    if (frappe) {
      await pg.waitForTimeout(350);
      const apres = await pg.evaluate(() => ({
        pr: window.GUIDE_ETAPES.prochain(),
        fl: window.GUIDE_ETAPES.fleche(),
        focus: (document.activeElement || {}).tagName,
      }));
      const nomApres = apres.pr ? apres.pr.nom : null;
      /* ON MESURE LA FLÈCHE, PAS LA CIBLE RECALCULÉE. `prochain()` interroge
         le DOM à l'instant de l'appel : il change de réponse même si la
         flèche, elle, est restée sur place — c'est ce qui a laissé ce
         contrôle passer alors que l'écoute de la saisie était débranchée. Ce
         qu'on éprouve ici, c'est le DÉPLACEMENT du repère à l'écran : soit il
         a bougé, soit il a disparu parce qu'il n'y a plus rien à désigner. */
      const posBougee = !!(frappe.flAvant && apres.fl
        && (apres.fl.x !== frappe.flAvant.x || apres.fl.y !== frappe.flAvant.y));
      const disparue = !!frappe.flAvant && !apres.fl && nomApres === null;
      ok('LA FLÈCHE SUIT LA FRAPPE — sans attendre qu’on quitte le champ',
         posBougee || disparue,
         '« ' + String(frappe.avant).slice(0, 26) + ' » → « '
         + String(nomApres || 'plus rien').slice(0, 26) + ' » · repère '
         + (frappe.flAvant ? frappe.flAvant.x + ',' + frappe.flAvant.y : '?')
         + ' → ' + (apres.fl ? apres.fl.x + ',' + apres.fl.y : 'retiré'));
      ok('…et la saisie n’est pas interrompue : le champ garde le curseur',
         frappe.focusTenu && apres.focus === frappe.balise,
         'focus sur ' + apres.focus + ' (saisi dans ' + frappe.balise + ')');
    } else {
      ok('LA FLÈCHE SUIT LA FRAPPE — sans attendre qu’on quitte le champ',
         false, 'le champ visé n’a pas pu être retrouvé ni rempli');
    }
  }

  ok('aucune erreur de script sur toute la manœuvre', err.length === 0,
     err.slice(0, 2).join(' | '));

  await nav.close();
  console.log('\n' + (ko ? ko + ' contrôle(s) en échec' : 'tout est vert') + '\n');
  process.exit(ko ? 1 : 0);
})();
