/* Recette — les équipements informatiques sur /datacenter.
   ───────────────────────────────────────────────────────
   Ce qu'elle protège :
   1. la nomenclature s'affiche AVEC la règle de quantité de chaque poste —
      un tableau de nombres nus se recopie dans un budget sans que personne
      ne sache d'où sortent les commutateurs ;
   2. la part dans les LOTS travaux vaut zéro et le dit — c'est le constat de
      périmètre qui commande tout le chapitre ;
   3. l'allongement de durée de vie affiche son point de bascule, et le
      verdict CHANGE de pays en pays. Une page qui dirait « favorable »
      partout serait une plaquette ;
   4. le module refuse plutôt que d'inventer — au-delà de quinze ans, sur un
      PUE impossible, sur une densité inconnue.

   Usage : node recette_equipements_it.js [http://127.0.0.1:PORT]
*/
const BASE = process.argv[2] || "http://127.0.0.1:8931";
const COMPTE = { email: "recette@local.test", mdp: "RecetteLocale!2026" };

let dur = 0, tot = 0;
function titre(t) { console.log("\n\x1b[36m" + t + "\x1b[0m"); }
function ok(nom, cond, detail) {
  tot++;
  if (cond) { console.log("  \x1b[32m✓\x1b[0m " + nom); }
  else { dur++; console.log("  \x1b[31m✗ " + nom + "\x1b[0m" + (detail ? "  → " + detail : "")); }
}

(async () => {
  const { chromium } = require("/opt/node22/lib/node_modules/playwright");
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1280, height: 900 } });
  const pg = await ctx.newPage();

  /* Le pare-feu applicatif rejette les clients HTTP synthétiques : toute
     requête d'API part donc DE LA PAGE, avec son cookie de session. */
  async function api(url, corps) {
    return pg.evaluate(async ([u, c]) => {
      const r = await fetch(u, {
        method: c ? "POST" : "GET", credentials: "same-origin",
        headers: c ? { "Content-Type": "application/json" } : {},
        body: c ? JSON.stringify(c) : undefined
      });
      return { statut: r.status, j: await r.json().catch(() => null) };
    }, [url, corps || null]);
  }

  // ── Connexion ────────────────────────────────────────────────────────────
  /* Sans session, /datacenter renvoie vers le formulaire de connexion et tout
     ce qui suit ne mesurerait plus que ce formulaire. */
  await pg.goto(BASE + "/connexion", { waitUntil: "domcontentloaded" });
  await pg.evaluate(async ([e, m]) => fetch("/api/auth/login", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: e, password: m })
  }), [COMPTE.email, COMPTE.mdp]);

  const rep = await pg.goto(BASE + "/datacenter", { waitUntil: "networkidle" });
  ok("la page /datacenter s'ouvre pour un compte connecté",
     !!rep && rep.status() === 200 && !/\/connexion/.test(pg.url()),
     rep ? "HTTP " + rep.status() + " " + pg.url() : "pas de reponse");
  if (!rep || rep.status() !== 200 || /\/connexion/.test(pg.url())) {
    console.log("\x1b[31mConnexion impossible : la suite ne mesurerait rien.\x1b[0m");
    await nav.close(); process.exit(2);
  }
  await pg.waitForTimeout(700);

  // ── 1. La section existe et porte son numéro ─────────────────────────────
  titre("1. La section est en place dans le fil des étapes");
  const sect = await pg.evaluate(() => {
    const s = document.getElementById("dc-sec-equip");
    if (!s) return null;
    const n = s.querySelector(".rc-etape .n");
    return {
      numero: n ? n.textContent.trim() : "",
      titre: (s.querySelector("h2") || {}).textContent || "",
      champs: ["eq-pit", "eq-densite", "eq-perimetre", "eq-enveloppe", "eq-go"]
        .filter(id => document.getElementById(id)).length,
      densites: (document.getElementById("eq-densite") || { options: [] }).options.length,
      perimetres: (document.getElementById("eq-perimetre") || { options: [] }).options.length,
      pays: (document.getElementById("eq-pays") || { options: [] }).options.length
    };
  });
  ok("la section /datacenter#dc-sec-equip existe", !!sect);
  ok("…et porte le numéro 4", sect && sect.numero === "4", sect && sect.numero);
  ok("…son titre nomme le scope 3",
     !!sect && /scope\s*.?3/i.test(sect.titre), sect && sect.titre);
  ok("…les cinq commandes sont présentes", sect && sect.champs === 5,
     sect && sect.champs + "/5");
  ok("…les densités viennent du serveur (au moins 4)",
     sect && sect.densites >= 4, sect && String(sect.densites));
  ok("…les trois périmètres sont proposés", sect && sect.perimetres === 3,
     sect && String(sect.perimetres));
  ok("…la liste des pays est remplie depuis le moteur",
     sect && sect.pays >= 8, sect && String(sect.pays));

  // ── 2. Le dimensionnement ────────────────────────────────────────────────
  titre("2. La nomenclature s'affiche avec la règle de chaque quantité");
  await pg.fill("#eq-pit", "1000");
  await pg.fill("#eq-enveloppe", "25000000");
  await pg.selectOption("#eq-perimetre", "propre").catch(() => {});
  await pg.click("#eq-go");
  await pg.waitForTimeout(1400);

  const tab = await pg.evaluate(() => {
    const t = document.querySelector("#eq-sortie .eq-tab");
    if (!t) return null;
    const lignes = [...t.querySelectorAll("tbody tr")].map(tr => ({
      poste: (tr.querySelector("th") || {}).textContent || "",
      regle: (tr.children[1] || {}).textContent || "",
      qte: (tr.children[2] || {}).textContent || ""
    }));
    return {
      n: lignes.length,
      sansRegle: lignes.filter(l => !l.regle.trim()).map(l => l.poste),
      sansQte: lignes.filter(l => !/\d/.test(l.qte)).map(l => l.poste),
      badges: t.querySelectorAll(".eq-badge").length,
      indispensables: t.querySelectorAll("tr.eq-ind").length,
      legende: (t.querySelector("caption") || {}).textContent || "",
      gestes: document.querySelectorAll("#eq-sortie .eq-dl dt").length
    };
  });
  ok("le tableau des postes s'affiche", !!tab && tab.n >= 8, tab && String(tab.n));
  ok("…CHAQUE poste porte sa règle de quantité",
     !!tab && tab.sansRegle.length === 0, tab && tab.sansRegle.join(", "));
  ok("…chaque poste porte une quantité chiffrée",
     !!tab && tab.sansQte.length === 0, tab && tab.sansQte.join(", "));
  ok("…indispensable ou utile est marqué sur chaque ligne",
     !!tab && tab.badges === tab.n, tab && tab.badges + "/" + tab.n);
  ok("…la légende rappelle la puissance ET la densité retenues",
     !!tab && /kW\/baie/.test(tab.legende) && /baies/.test(tab.legende),
     tab && tab.legende);
  ok("…le geste d'achat durable est donné poste par poste",
     !!tab && tab.gestes === tab.n, tab && tab.gestes + "/" + tab.n);

  // ── 3. LE CONSTAT DE PÉRIMÈTRE ───────────────────────────────────────────
  titre("3. L'informatique n'est pas dans les lots travaux — et la page le dit");
  const part = await pg.evaluate(() => {
    const b = document.querySelector("#eq-sortie .eq-part");
    if (!b) return null;
    const c = [...b.querySelectorAll(".eq-c")].map(x => ({
      v: (x.querySelector(".v") || {}).textContent || "",
      l: (x.querySelector(".l") || {}).textContent || ""
    }));
    return { cartes: c, texte: b.textContent || "" };
  });
  const lots = part && part.cartes.find(x => /lots travaux/i.test(x.l));
  ok("la carte « part dans les lots travaux » existe", !!lots,
     part && part.cartes.map(x => x.l).join(" | "));
  ok("…et elle vaut ZÉRO", !!lots && /^0\s*%$/.test(lots.v.trim()), lots && lots.v);
  ok("…la page explique POURQUOI zéro (aménagement des salles ≠ serveurs)",
     !!part && /aménagement des salles/i.test(part.texte));
  const total = part && part.cartes.find(x => /investissement total/i.test(x.l));
  ok("…et donne la part de l'investissement TOTAL en centre propre", !!total,
     total && total.v);

  titre("4. En colocation, les deux budgets ne sont pas additionnés");
  await pg.selectOption("#eq-perimetre", "colocation");
  await pg.click("#eq-go");
  await pg.waitForTimeout(1200);
  const coloc = await pg.evaluate(() => {
    const b = document.querySelector("#eq-sortie .eq-part");
    return b ? {
      texte: b.textContent || "",
      totalAffiche: [...b.querySelectorAll(".eq-c .l")]
        .some(x => /investissement total/i.test(x.textContent))
    } : null;
  });
  ok("aucune part d'investissement total n'est affichée",
     !!coloc && coloc.totalAffiche === false);
  ok("…et la page dit pourquoi : deux bilans distincts",
     !!coloc && /deux bilans/i.test(coloc.texte));
  await pg.selectOption("#eq-perimetre", "propre");
  await pg.click("#eq-go");
  await pg.waitForTimeout(1200);

  // ── 5. La bascule de durée de vie ────────────────────────────────────────
  titre("5. L'allongement de durée de vie affiche son point de bascule");
  const visible = await pg.evaluate(() => {
    const f = document.getElementById("eq-vie-form");
    return !!f && !f.hidden;
  });
  ok("le formulaire de durée de vie apparaît après le dimensionnement", visible);

  async function bascule(pays) {
    await pg.selectOption("#eq-pays", pays);
    await pg.fill("#eq-d0", "5");
    await pg.fill("#eq-d1", "8");
    await pg.fill("#eq-pue", "1.3");
    await pg.click("#eq-vie-go");
    await pg.waitForTimeout(1200);
    return pg.evaluate(() => {
      const b = document.querySelector("#eq-vie .eq-vie");
      if (!b) return null;
      const seuil = [...b.querySelectorAll(".eq-c")]
        .find(x => /bascule/i.test((x.querySelector(".l") || {}).textContent || ""));
      return {
        classe: b.className,
        verdict: (b.querySelector(".eq-verdict") || {}).textContent || "",
        seuil: seuil ? (seuil.querySelector(".v") || {}).textContent : "",
        texte: b.textContent || "",
        formules: b.querySelectorAll(".eq-formules li").length
      };
    });
  }

  const fr = await bascule("FR");
  ok("sur le mix français, l'allongement est FAVORABLE",
     !!fr && /eq-fav/.test(fr.classe) && /Favorable/i.test(fr.verdict),
     fr && fr.verdict);
  ok("…le verdict porte une icône directionnelle, pas seulement une couleur",
     !!fr && /[▲▼]/.test(fr.verdict), fr && fr.verdict);
  ok("…l'intensité de bascule est affichée en g/kWh",
     !!fr && /g\/kWh/.test(fr.seuil), fr && fr.seuil);
  ok("…les formules sont publiées pour être refaites",
     !!fr && fr.formules >= 4, fr && String(fr.formules));
  ok("…la réserve non-carbone est dite (sécurité, correctifs)",
     !!fr && /correctifs/i.test(fr.texte));

  const pl = await bascule("PL");
  ok("sur un mix carboné, le MÊME allongement devient DÉFAVORABLE",
     !!pl && /eq-def/.test(pl.classe) && /Défavorable/i.test(pl.verdict),
     pl && pl.verdict);
  ok("…et la page nomme le levier qui reste : décarboner l'alimentation",
     !!pl && /décarboner/i.test(pl.texte));
  ok("…le seuil de bascule est le MÊME dans les deux pays (il ne dépend "
     + "que du matériel)",
     !!fr && !!pl && fr.seuil.trim() === pl.seuil.trim(),
     fr && pl ? fr.seuil + " ≠ " + pl.seuil : "");

  // ── 6. Le scope 3 ────────────────────────────────────────────────────────
  titre("6. Le scope 3 dit ce qu'il couvre — et ce qu'il ne couvre pas");
  const s3 = await pg.evaluate(() => {
    const b = document.querySelector("#eq-scope3 .eq-s3");
    return b ? {
      texte: b.textContent || "",
      cartes: b.querySelectorAll(".eq-c").length,
      trous: b.querySelectorAll(".eq-trous li").length
    } : null;
  });
  ok("le bilan scope 3 s'affiche", !!s3 && s3.cartes >= 4, s3 && String(s3.cartes));
  ok("…il se présente en complément des scopes 1 et 2",
     !!s3 && /scope/i.test(s3.texte) && /complèt/i.test(s3.texte));
  ok("…il NOMME au moins trois postes non couverts",
     !!s3 && s3.trous >= 3, s3 && String(s3.trous));
  ok("…il avertit du transfert entre scopes quand on prolonge",
     !!s3 && /scope 2/i.test(s3.texte), "");

  // ── 7. Les refus ─────────────────────────────────────────────────────────
  titre("7. Le module refuse plutôt que d'inventer");
  const r1 = await api("/api/datacenter/equipements",
                       { puissance_it_kw: 1000, densite: "supersonique" });
  ok("une densité inconnue est refusée avec son motif",
     r1.statut === 200 && r1.j && r1.j.nomenclature
       && r1.j.nomenclature.ok === false
       && /supersonique/.test(r1.j.nomenclature.motif || ""),
     JSON.stringify(r1.j && r1.j.nomenclature).slice(0, 120));

  const r2 = await api("/api/datacenter/equipements",
                       { puissance_it_kw: 1000, duree_base: 5, duree_cible: 20 });
  ok("un allongement au-delà de quinze ans est refusé",
     r2.statut === 200 && r2.j && r2.j.prolongation
       && r2.j.prolongation.ok === false
       && /quinze ans/.test(r2.j.prolongation.motif || ""),
     JSON.stringify(r2.j && r2.j.prolongation).slice(0, 120));

  const r3 = await api("/api/datacenter/equipements",
                       { puissance_it_kw: 1000, duree_base: 5, duree_cible: 8, pue: 0.8 });
  ok("un PUE inférieur à 1 est refusé comme physiquement impossible",
     r3.statut === 200 && r3.j && r3.j.prolongation
       && r3.j.prolongation.ok === false
       && /impossible/.test(r3.j.prolongation.motif || ""),
     JSON.stringify(r3.j && r3.j.prolongation).slice(0, 120));

  const r4 = await api("/api/datacenter/equipements",
                       { puissance_it_kw: 1000, perimetre: "sous-marin" });
  ok("un périmètre inconnu est refusé",
     r4.statut === 200 && r4.j && r4.j.part && r4.j.part.ok === false,
     JSON.stringify(r4.j && r4.j.part).slice(0, 120));

  const r5 = await api("/api/datacenter/equipements",
                       { puissance_it_kw: 1000, duree_base: 5, duree_cible: 8,
                         pays: "ZZ" });
  ok("un pays dont le mix est inconnu est refusé, jamais supposé",
     r5.statut === 200 && r5.j && r5.j.prolongation
       && r5.j.prolongation.ok === false,
     JSON.stringify(r5.j && r5.j.prolongation).slice(0, 120));

  // ── 8. Le partage avec Sentinel ──────────────────────────────────────────
  titre("8. Les deux ponts vers Sentinel et la maîtrise d'œuvre");
  const ponts = await pg.evaluate(() => {
    const b = document.getElementById("eq-ponts");
    if (!b) return null;
    return {
      liens: [...b.querySelectorAll("a")].map(a => a.getAttribute("href")),
      texte: b.textContent || ""
    };
  });
  ok("le pont vers l'enveloppe d'investissement de Sentinel est nommé",
     !!ponts && ponts.liens.some(h => /conseilprev\.onrender\.com\/enveloppe/.test(h)),
     ponts && ponts.liens.join(" | "));
  ok("…le pont vers la maîtrise d'œuvre l'est séparément",
     !!ponts && ponts.liens.some(h => /ingenierie-datacenter/.test(h)),
     ponts && ponts.liens.join(" | "));
  ok("…et la page dit que le module est PARTAGÉ (mêmes quantités)",
     !!ponts && /mêmes/i.test(ponts.texte) && /partagent/i.test(ponts.texte));

  // ── Bilan ────────────────────────────────────────────────────────────────
  console.log("\n" + (dur === 0
    ? "\x1b[32m" + tot + " contrôles, aucun échec.\x1b[0m"
    : "\x1b[31m" + dur + " échec(s) sur " + tot + " contrôles.\x1b[0m"));
  await nav.close();
  process.exit(dur === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
