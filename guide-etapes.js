/* LE PARCOURS GUIDÉ DES ÉTAPES NUMÉROTÉES — partagé par toutes les pages qui
   font remplir quelque chose.
   ═══════════════════════════════════════════════════════════════════════════

   CE QU'IL RÉSOUT. Plusieurs pages du site demandent au client de remplir des
   champs, de choisir dans des listes et de lancer un calcul, le tout réparti
   en sections numérotées. Arrivé dessus, on voit onze titres, huit listes
   déroulantes et un bouton « Calculer » : rien ne dit par où commencer, ce que
   chaque étape attend, ni pourquoi elle la demande. Le lecteur remplit au
   hasard, ou renonce. Une seule page portait un parcours ; les autres non.

   CE QU'IL N'EST PAS. Ni une table des matières — la page en a déjà une —, ni
   un tunnel. Il ne DÉPLACE rien, ne MASQUE rien, ne remplit rien : il désigne
   une étape à la fois, dit ce qu'elle attend et pourquoi, et laisse le lecteur
   travailler dans la page. On peut le fermer à tout moment et la page reste
   entière.

   ══ TROIS DÉCISIONS QUI TIENNENT TOUT ══

   1. LES ÉTAPES SONT LUES SUR LA PAGE, JAMAIS ÉCRITES ICI. Elles sortent des
      sections numérotées que la page affiche déjà. Une liste recopiée dans ce
      fichier aurait divergé au premier titre renommé, à la première section
      ajoutée — et un parcours qui annonce huit étapes quand la page en montre
      onze est pire que pas de parcours : il fait chercher ce qui n'existe pas.

   2. CE QU'IL Y A À REMPLIR EST COMPTÉ, JAMAIS DÉCLARÉ. « Trois listes
      déroulantes et deux champs, dont un obligatoire » se lit sur les
      commandes réellement présentes dans la section. Écrite à la main, la
      phrase promettrait des champs disparus depuis.

   3. CE QUI EST FAIT EST CONSTATÉ, JAMAIS COCHÉ. Une étape passe à « fait »
      quand ses champs obligatoires SONT renseignés, pas quand on a cliqué
      « suivant ». Un parcours qui se félicite d'un clic ment sur l'avancement,
      et c'est justement l'avancement qu'on vient lui demander.

   LE SEUL TEXTE ÉCRIT À LA MAIN est le POURQUOI de chaque étape, posé dans la
   page sur la section elle-même (`data-gd`). Une machine sait compter des
   champs ; elle ne sait pas dire pourquoi ils décident de quelque chose. Ce
   texte vit donc à côté de ce qu'il explique, et non dans un registre lointain
   qui se désynchronise.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  var CLE = "cpc_guide_" + location.pathname;

  function $(s, r) { return (r || document).querySelector(s); }
  function tous(s, r) { return [].slice.call((r || document).querySelectorAll(s)); }
  function esc(t) {
    var d = document.createElement("div");
    d.textContent = t == null ? "" : String(t);
    return d.innerHTML;
  }

  /* ── 1. LES ÉTAPES, LUES SUR LA PAGE ─────────────────────────────────────
     Une étape est une section qui porte un numéro visible. On garde l'ordre
     du document et NON l'ordre des numéros : c'est celui que le lecteur a
     sous les yeux, et deux sections peuvent partager un numéro sans que ce
     soit une faute (un « ◆ » de cadrage, par exemple, qu'on ne compte pas). */
  function etapesDeLaPage() {
    return tous("section .rc-etape").map(function (t) {
      var n = t.querySelector(".n");
      var h = t.querySelector("h2, h3");
      var sec = t.closest("section");
      if (!n || !h || !sec) return null;
      var num = (n.textContent || "").trim();
      /* Seules les sections NUMÉROTÉES sont des étapes. Un losange ou une
         puce marque un cadrage : on ne fait pas « l'étape ◆ sur 8 ». */
      if (!/^\d+$/.test(num)) return null;
      /* UNE SECTION MASQUÉE AU DÉPART RESTE UNE ÉTAPE DU CHEMIN. Les résultats
         et la comparaison n'apparaissent qu'une fois le calcul lancé : les
         écarter faisait annoncer « 8 étapes » là où la page en numérote 10, et
         le lecteur cherchait deux étapes qui existent pourtant. Elles sont
         donc comptées, et signalées comme À VENIR — ce qui dit en plus ce qui
         les fera apparaître. */
      if (!sec.id) sec.id = "gd-sec-" + num;
      return {
        num: num, titre: (h.textContent || "").trim(),
        ancre: sec.id, section: sec,
        pourquoi: sec.getAttribute("data-gd") || "",
      };
    }).filter(Boolean);
  }

  /* ── 2. CE QU'IL Y A À REMPLIR, COMPTÉ SUR LES COMMANDES PRÉSENTES ───────
     On ne compte QUE ce qui est visible et actif : un champ caché ou
     désactivé n'est pas à remplir, et l'annoncer enverrait chercher une
     commande introuvable. */
  function utilisable(el) {
    if (el.disabled || el.type === "hidden") return false;
    if (el.closest("[hidden]")) return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 || r.height > 0;
  }

  function aRemplir(sec) {
    var listes = tous("select", sec).filter(utilisable);
    var champs = tous("input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea", sec)
      .filter(utilisable);
    var cases = tous("input[type=checkbox], input[type=radio]", sec).filter(utilisable);
    var oblig = listes.concat(champs).filter(function (e) {
      return e.required || e.getAttribute("aria-required") === "true";
    });
    var action = tous("button", sec).filter(function (b) {
      return utilisable(b) && /calcul|lancer|évalu|evalu|estim|générer|generer|comparer|analyser|qualifier/i.test(b.textContent || "");
    })[0] || null;
    return { listes: listes, champs: champs, cases: cases, oblig: oblig, action: action };
  }

  function phrase(r) {
    var m = [];
    if (r.listes.length) m.push(r.listes.length + " liste" + (r.listes.length > 1 ? "s" : "")
      + " déroulante" + (r.listes.length > 1 ? "s" : ""));
    if (r.champs.length) m.push(r.champs.length + " champ" + (r.champs.length > 1 ? "s" : ""));
    if (r.cases.length) m.push(r.cases.length + " case" + (r.cases.length > 1 ? "s" : "")
      + " à cocher");
    if (!m.length) return "Rien à remplir ici : cette étape se lit.";
    var t = "À remplir : " + m.join(", ") + ".";
    if (r.oblig.length) t += " " + r.oblig.length + " obligatoire" + (r.oblig.length > 1 ? "s" : "") + ".";
    return t;
  }

  /* ── 3. CE QUI EST FAIT, CONSTATÉ ────────────────────────────────────────
     Une étape sans champ obligatoire est réputée faite dès qu'UNE de ses
     commandes est renseignée : elle propose, elle n'exige pas. Une étape sans
     aucune commande ne se « fait » pas — elle se lit — et n'entre donc pas
     dans le compte d'avancement, sans quoi le compte flatterait le lecteur. */
  /* CES FORMULAIRES ARRIVENT DÉJÀ REMPLIS, et c'est tout le problème. Les
     listes déroulantes ouvrent sur une option — souvent une vraie valeur, pas
     un « — choisir — » —, et la moitié des champs porte la valeur par défaut
     du référentiel, ce que la page annonce d'ailleurs franchement. Compter
     « renseigné » tout ce qui porte une valeur faisait lire « fait » à quatre
     étapes d'une page où le lecteur n'avait RIEN touché : le parcours se
     félicitait d'un formulaire livré pré-rempli, et son avancement ne voulait
     plus rien dire.

     UNE SEULE RÈGLE, POUR TOUTES LES COMMANDES : une réponse est une valeur
     qui a BOUGÉ de celle qu'on a vue en arrivant — ou une case partie vide et
     désormais remplie. La valeur de départ est relevée à la PREMIÈRE
     RENCONTRE et non au chargement : plusieurs blocs se peuplent par requête
     bien après, et une liste apparue ensuite n'aurait eu aucune référence —
     elle serait repassée « renseignée » par le seul fait d'exister.

     LE COÛT EST ASSUMÉ : qui accepte la valeur par défaut n'est pas crédité.
     Sous-évaluer l'avancement se corrige d'un clic ; le sur-évaluer fait croire
     à un travail qui n'a pas eu lieu — et c'est l'avancement qu'on vient
     demander à ce parcours. */
  var DEPART = new WeakMap();

  function depart(el) {
    if (!DEPART.has(el)) {
      DEPART.set(el, el.type === "checkbox" || el.type === "radio"
        ? (el.checked ? "1" : "")
        : String(el.value == null ? "" : el.value).trim());
    }
    return DEPART.get(el);
  }

  function rempli(el) {
    var d = depart(el);
    if (el.type === "checkbox" || el.type === "radio") {
      return el.checked ? d === "" : false;
    }
    var v = String(el.value == null ? "" : el.value).trim();
    if (v === "") return false;
    /* Partie vide puis renseignée : c'est une réponse. Partie sur une valeur
       et restée dessus : on ne peut pas savoir, donc on ne l'affirme pas. */
    return d === "" || v !== d;
  }

  function etat(sec) {
    /* À VENIR AVANT TOUT AUTRE ÉTAT : une section masquée n'a ni champ à
       remplir ni contenu à lire, et la déclarer « en lecture » laisserait
       croire qu'il n'y a rien à y faire alors qu'elle n'est pas encore là. */
    if (sec.hidden) return "a-venir";
    var r = aRemplir(sec);
    var toutes = r.listes.concat(r.champs).concat(r.cases);
    if (!toutes.length) return "lecture";
    if (r.oblig.length) return r.oblig.every(rempli) ? "fait" : "a-faire";
    return toutes.some(rempli) ? "fait" : "a-faire";
  }

  /* ── 4. L'INTERFACE ──────────────────────────────────────────────────── */
  var ETAPES = [], COURANT = 0, OUVERT = false;

  function amorce() {
    var n = ETAPES.length;
    var r = ETAPES.reduce(function (a, e) {
      var x = aRemplir(e.section);
      a.listes += x.listes.length;
      a.champs += x.champs.length + x.cases.length;
      return a;
    }, { listes: 0, champs: 0 });
    /* LA PHRASE D'ACCUEIL EST CHIFFRÉE SUR LA PAGE. « Quelques étapes » ne
       prévient de rien ; « onze étapes, huit listes déroulantes » dit au
       lecteur ce dans quoi il entre, avant qu'il n'y entre. */
    var quoi = n + " étape" + (n > 1 ? "s" : "");
    if (r.listes) quoi += ", " + r.listes + " liste" + (r.listes > 1 ? "s" : "")
      + " déroulante" + (r.listes > 1 ? "s" : "");
    if (r.champs) quoi += " et " + r.champs + " champ" + (r.champs > 1 ? "s" : "");
    return '<div class="gd-lanceur">'
      + '<div class="gd-lanceur-t"><b>Vous ne savez pas par où commencer&nbsp;?</b>'
      + '<span>Cette page tient ' + quoi + '. Le parcours guidé les prend '
      + 'une par une&nbsp;: ce que l\'étape attend, pourquoi elle le demande, '
      + 'et ce qui en dépend ensuite.</span></div>'
      + '<button type="button" class="gd-lanceur-b" id="gd-ouvrir" '
      + 'aria-expanded="' + (OUVERT ? "true" : "false") + '" aria-controls="gd-panneau">'
      + (OUVERT ? "Fermer le parcours" : "Ouvrir le parcours guidé") + "</button></div>";
  }

  function panneau() {
    var e = ETAPES[COURANT];
    if (!e) return "";
    var r = aRemplir(e.section);
    var faits = ETAPES.filter(function (x) { return etat(x.section) === "fait"; }).length;
    /* NI LES SECTIONS DE LECTURE NI CELLES À VENIR n'entrent au dénominateur :
       les premières ne se remplissent pas, les secondes ne sont pas encore
       là. Les compter ferait un avancement qui plafonne sans faute du
       lecteur — le genre de compteur qu'on cesse de croire. */
    var comptables = ETAPES.filter(function (x) {
      var s = etat(x.section);
      return s !== "lecture" && s !== "a-venir";
    }).length;

    /* LA JAUGE DIT CE QUI EST FAIT, PAS OÙ L'ON EN EST DANS LE PARCOURS. Ce
       sont deux choses différentes : on peut être à l'étape 6 sans en avoir
       rempli une seule. Colorer la jauge sur la position ferait passer une
       promenade pour un travail. */
    var jauge = ETAPES.map(function (x, i) {
      var s = etat(x.section);
      return '<span class="' + (s === "fait" ? "fa"
        : (i === COURANT ? "ic" : (s === "a-venir" ? "av" : "")))
        + '" title="' + esc(x.num + ". " + x.titre) + '"></span>';
    }).join("");

    var h = '<div class="gd-p" id="gd-panneau">'
      + '<div class="gd-jauge" role="img" aria-label="'
      + esc(faits + " étape(s) remplie(s) sur " + comptables) + '">' + jauge + "</div>"
      + '<p class="gd-n">Étape ' + esc(String(COURANT + 1)) + " sur "
      + ETAPES.length + " · section " + esc(e.num) + " de la page</p>"
      + "<h3>" + esc(e.titre) + "</h3>";

    if (e.pourquoi) h += '<p class="gd-pq">' + esc(e.pourquoi) + "</p>";

    h += '<p class="gd-quoi">' + esc(phrase(r)) + "</p>";
    if (r.action) {
      h += '<p class="gd-act">Cette étape se termine par&nbsp;: <b>'
        + esc((r.action.textContent || "").trim()) + "</b></p>";
    }
    var s = etat(e.section);
    h += '<p class="gd-etat ' + s + '">'
      + (s === "fait" ? "✓ Renseignée."
        : s === "lecture" ? "Rien à saisir ici."
        : s === "a-venir" ? "Pas encore affichée : cette section apparaît une "
            + "fois le calcul lancé."
        : "En attente de vos réponses.") + "</p>";

    h += '<div class="gd-cmd">'
      /* ON N'ENVOIE PAS VERS CE QUI N'EST PAS LÀ. Un bouton qui fait défiler
         vers une section masquée ne produit rien de visible, et le lecteur en
         conclut que la page est cassée. */
      + '<button type="button" class="gd-b" data-gd-aller'
      + (s === "a-venir" ? " disabled" : "") + ">Aller à cette étape</button>"
      + '<button type="button" class="gd-b s" data-gd-prec'
      + (COURANT === 0 ? " disabled" : "") + ">Précédente</button>"
      + '<button type="button" class="gd-b s" data-gd-suiv'
      + (COURANT >= ETAPES.length - 1 ? " disabled" : "") + ">Suivante</button>"
      + '<button type="button" class="gd-lien" data-gd-fermer>Fermer le parcours</button>'
      + "</div>";

    /* LE SOMMAIRE DES ÉTAPES, replié. Il ne remplace pas l'étape courante : il
       permet d'en rejoindre une directement, ce qu'un parcours strictement
       linéaire interdit — et le lecteur qui sait où il va n'a pas à cliquer
       six fois « suivante ». */
    h += '<details class="gd-toutes"><summary>Voir les '
      + ETAPES.length + " étapes</summary><ol>"
      + ETAPES.map(function (x, i) {
          var st = etat(x.section);
          return '<li><button type="button" class="gd-saut" data-gd-i="' + i + '"'
            + (i === COURANT ? ' aria-current="true"' : "") + ">"
            + '<span class="st ' + st + '" aria-hidden="true">'
            + (st === "fait" ? "✓" : st === "lecture" ? "·"
                : st === "a-venir" ? "…" : "○") + "</span>"
            + esc(x.titre) + "</button></li>";
        }).join("")
      + "</ol></details></div>";
    return h;
  }

  function surligner(sec) {
    tous(".gd-vise").forEach(function (e) { e.classList.remove("gd-vise"); });
    if (sec) sec.classList.add("gd-vise");
  }

  function rendre(bouger) {
    var z = $("#gd");
    if (!z) return;
    z.innerHTML = amorce() + (OUVERT ? panneau() : "");
    if (OUVERT) {
      surligner(ETAPES[COURANT] && ETAPES[COURANT].section);
      try { localStorage.setItem(CLE, String(COURANT)); } catch (err) { /* mode privé */ }
    } else {
      surligner(null);
    }
    if (bouger === "ouvrir") {
      var p = $("#gd-panneau");
      if (p) { try { p.focus({ preventScroll: true }); } catch (err) { /* rien */ } }
    }
  }

  function aller() {
    var e = ETAPES[COURANT];
    if (!e || e.section.hidden) return;
    surligner(e.section);
    /* `scrollIntoView` hérite de `scroll-behavior:smooth` de la feuille de
       style : c'est voulu ici — le lecteur doit VOIR d'où il vient, sinon la
       page semble sauter. En mouvement réduit, on y va sans animation. */
    var reduit = window.matchMedia
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    e.section.scrollIntoView(reduit
      ? { behavior: "instant", block: "start" }
      : { behavior: "smooth", block: "start" });
    /* On donne le clavier à la section visée, sinon la tabulation repart du
       haut du document et le lecteur au clavier perd le bénéfice du saut. */
    var cible = tous("select, input:not([type=hidden]), textarea, button", e.section)
      .filter(utilisable)[0];
    if (cible) { setTimeout(function () { try { cible.focus({ preventScroll: true }); } catch (err) { /* rien */ } }, reduit ? 0 : 420); }
  }

  /* ── 5. BRANCHEMENT ──────────────────────────────────────────────────── */
  function demarrer() {
    var z = $("#gd");
    if (!z) return;
    ETAPES = etapesDeLaPage();
    /* MOINS DE DEUX ÉTAPES : PAS DE PARCOURS. Guider quelqu'un à travers une
       seule section ajoute une commande sans rien apprendre. Le bloc reste
       vide plutôt que de se remplir pour exister. */
    if (ETAPES.length < 2) { z.innerHTML = ""; return; }
    /* On relève la référence de TOUTES les commandes présentes avant le
       premier rendu. Celles qui arriveront plus tard prendront la leur à leur
       première rencontre — c'est le même geste, au bon moment. */
    tous("select, input, textarea").forEach(depart);
    try {
      var v = parseInt(localStorage.getItem(CLE), 10);
      if (v >= 0 && v < ETAPES.length) COURANT = v;
    } catch (err) { /* mode privé : on repart de la première */ }
    rendre();

    z.addEventListener("click", function (ev) {
      var t = ev.target;
      if (t.closest("#gd-ouvrir")) {
        OUVERT = !OUVERT;
        rendre(OUVERT ? "ouvrir" : null);
        if (OUVERT) aller();
        return;
      }
      if (t.closest("[data-gd-fermer]")) { OUVERT = false; rendre(); return; }
      if (t.closest("[data-gd-aller]")) { aller(); return; }
      if (t.closest("[data-gd-prec]") && COURANT > 0) { COURANT--; rendre(); aller(); return; }
      if (t.closest("[data-gd-suiv]") && COURANT < ETAPES.length - 1) {
        COURANT++; rendre(); aller(); return;
      }
      var s = t.closest("[data-gd-i]");
      if (s) { COURANT = parseInt(s.getAttribute("data-gd-i"), 10) || 0; rendre(); aller(); }
    });

    /* L'AVANCEMENT SUIT LA SAISIE, SANS LA GÊNER. On réagit à `change` et non
       à `input` : recalculer et redessiner le panneau à chaque frappe volerait
       le focus du champ en cours de frappe — le lecteur perdrait sa saisie de
       vue à chaque lettre. */
    document.addEventListener("change", function () {
      if (OUVERT) rendre();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }

  /* Exposé pour la recette : elle doit pouvoir lire ce que la page a DÉDUIT,
     et non redéduire elle-même — sinon elle éprouverait sa propre copie. */
  window.GUIDE_ETAPES = {
    etapes: function () { return ETAPES; },
    courant: function () { return COURANT; },
    ouvert: function () { return OUVERT; },
    etat: function (i) { return ETAPES[i] ? etat(ETAPES[i].section) : null; },
    aRemplir: function (i) { return ETAPES[i] ? aRemplir(ETAPES[i].section) : null; },
  };
})();
