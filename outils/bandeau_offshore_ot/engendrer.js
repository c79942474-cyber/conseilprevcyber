#!/usr/bin/env node
/* ENGENDRE LE BANDEAU DE L'ACCUEIL À PARTIR DE bandeau.html.
 *
 *   node outils/bandeau_offshore_ot/engendrer.js
 *
 * produit, dans media/ (servi par la route /media, qui répond aux tranches) :
 *   bandeau-offshore-ot.mp4  — 1584 × 396, H.264 4:2:0, 30 images/s, sans son,
 *                              index en tête (`faststart`) ;
 *   bandeau-offshore-ot.jpg  — l'affiche, image de la première scène pleine.
 *                              C'est elle que la page livre ; la vidéo ne
 *                              vient qu'après le chargement (bandeau-ot.js).
 *
 * POURQUOI IMAGE PAR IMAGE. La page ne s'anime pas seule : `poser(t)` fixe
 * l'état de chaque élément à l'instant t. On l'appelle pour chaque image, on
 * capture, et ffmpeg assemble. Une capture vidéo « en direct » dépendrait de
 * la charge de la machine : des images sautées, une boucle qui ne retombe pas
 * juste. Ici, deux exécutions rendent la même vidéo.
 *
 * Les polices viennent de la machine (Inter, Inter Display) : la page n'en
 * charge aucune. Le script refuse de produire si la graisse 900 d'Inter
 * Display manque, plutôt que de livrer une vidéo dans une police de repli.
 */
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const ICI = __dirname;
const RACINE = path.dirname(path.dirname(ICI));
const MEDIA = path.join(RACINE, 'media');
const AFFICHE_T = 3.0;
const IPS = 30;

(async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bandeau-'));
  const nav = await chromium.launch();
  try {
    const pg = await nav.newPage({ viewport: { width: 1584, height: 396 } });
    const erreurs = [];
    pg.on('pageerror', (e) => erreurs.push(e.message));
    await pg.goto('file://' + path.join(ICI, 'bandeau.html'));
    await pg.evaluate(() => document.fonts.ready);
    const polices = await pg.evaluate(() => Array.from(document.fonts)
      .filter((f) => f.status === 'loaded').map((f) => f.family + ' ' + f.weight));
    if (polices.indexOf('Inter D 900') < 0) throw new Error('Inter Display Black introuvable : ' + polices.join(', '));
    const total = await pg.evaluate(() => window.TOTAL);
    const n = Math.round(total * IPS);
    for (let k = 0; k < n; k++) {
      await pg.evaluate((t) => poser(t), k / IPS);
      await pg.screenshot({ path: path.join(tmp, 'i' + String(k).padStart(4, '0') + '.png') });
    }
    await pg.evaluate((t) => poser(t), AFFICHE_T);
    await pg.screenshot({ path: path.join(tmp, 'affiche.png') });
    if (erreurs.length) throw new Error('erreurs dans la page : ' + erreurs.join(' | '));
    const video = path.join(MEDIA, 'bandeau-offshore-ot.mp4');
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-framerate', String(IPS), '-i', path.join(tmp, 'i%04d.png'),
      '-an', '-c:v', 'libx264', '-profile:v', 'high', '-level', '4.0', '-preset', 'slow', '-crf', '22',
      '-pix_fmt', 'yuv420p', '-movflags', '+faststart', video]);
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', path.join(tmp, 'affiche.png'), '-q:v', '3',
      path.join(MEDIA, 'bandeau-offshore-ot.jpg')]);
    console.log(n + ' images, ' + total.toFixed(1) + ' s → ' + path.relative(RACINE, video)
                + ' (' + Math.round(fs.statSync(video).size / 1024) + ' Ko)');
  } finally {
    await nav.close();
    fs.rmSync(tmp, { recursive: true, force: true });
  }
})().catch((e) => { console.error('✗ ' + e.message); process.exit(1); });
