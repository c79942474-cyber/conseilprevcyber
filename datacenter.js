/* Interface de l'étude de centre de données.
   ─────────────────────────────────────────
   Ce fichier ne calcule RIEN. Chaque chiffre affiché vient du serveur, où
   datacenter.py l'a produit avec sa formule, sa source et son incertitude.
   Recalculer côté navigateur pour « aller plus vite » ferait exister deux
   moteurs qui divergeraient au premier ajustement — et c'est le chiffre affiché
   que le client recopierait dans son offre.

   Le parti pris d'affichage : une valeur n'apparaît JAMAIS seule. Elle est
   toujours accompagnée de sa formule et de son incertitude, dépliables. Un
   tableau de bord de chiffres nus se lit vite et se défend mal ; ici le
   document doit tenir devant un bureau de contrôle. */
(function () {
  "use strict";

  /* LE DESTINATAIRE, S'IL A ÉTÉ CHOISI. « transmettre.js » est un module à
     part : s'il n'a pas chargé, l'export part sans bordereau plutôt que
     d'échouer. Un document sans bordereau reste un document ; un export qui
     casse, non — et le client n'aurait plus rien à transmettre du tout. */
  function TR(o) {
    return (window.TRANSMETTRE && window.TRANSMETTRE.corps)
      ? window.TRANSMETTRE.corps(o) : o;
  }

  var REF = null, PROFIL = {}, ETUDE = null;
  var ART = {};   /* l'état de l'art : sourcé, jamais dans un calcul */
  /* Un seul passage automatique par session de calcul : revenir en
     arrière depuis l'ingénierie ne doit pas relancer la bascule. */
  var SUITE_FAITE = false;

  function $(s, r) { return (r || document).querySelector(s); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ── AUCUNE REQUÊTE SANS DÉLAI ──────────────────────────────────────────
     LE défaut qui fait dire « la page est bloquée ». Un `fetch` sans délai
     attend INDÉFINIMENT : si le serveur tarde — saturé, en train de se
     réveiller, coupure réseau — la page reste sur « Chargement du
     référentiel… » ou « Calcul en cours… » sans un mot, parfois plusieurs
     minutes, jusqu'à ce que le navigateur abandonne de lui-même. Le
     formulaire ne s'affiche jamais : on ne peut RIEN saisir, et rien ne dit
     pourquoi.

     Une requête bornée ne répare pas la lenteur du serveur — elle la rend
     LISIBLE, et rend la main. C'est la différence entre une page en panne et
     une page qui explique.

     Deux budgets, parce que les gestes n'ont pas la même durée légitime : ce
     qui conditionne l'affichage doit échouer vite ; un calcul complet a le
     droit de prendre du temps. */
  var DELAI_COURT = 12000;    // référentiel, aperçu : conditionnent l'affichage
  var DELAI_LONG = 45000;     // étude, export : travail réel côté serveur

  /* ── LA SESSION QUI S'ÉTEINT EN COURS DE VISITE ─────────────────────────
     Comme sur la page d'ingénierie : toutes les requêtes de cette page
     passent par demander(), donc le 401 s'y reconnaît une fois pour toutes
     plutôt que d'être laissé à chaque appelant, qui le dissolvait dans son
     message générique (« référentiel indisponible », « aperçu indisponible »)
     sans jamais dire qu'il fallait se reconnecter. */
  var SESSION_MORTE = false;

  function sessionTexte() {
    return "<b>Votre session n’est plus active.</b> C’est pour cela que plus "
      + "rien ne se calcule ni ne s’affiche au-delà du formulaire. "
      + '<a class="btn btn-s" href="/connexion?next=/datacenter">'
      + "Se reconnecter</a> — vous reviendrez sur cette page.";
  }

  function sessionEteinte() {
    if (SESSION_MORTE) return;
    SESSION_MORTE = true;
    var b = document.createElement("div");
    b.id = "dc-session";
    b.className = "dc-session-alerte";
    b.setAttribute("role", "alert");
    b.innerHTML = sessionTexte();
    var m = document.getElementById("main") || document.body;
    m.insertBefore(b, m.firstChild);
    b.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function demander(url, options, delai) {
    options = options || {};
    var ctrl = (typeof AbortController !== "undefined") ? new AbortController() : null;
    var fini = false;
    var minuteur = setTimeout(function () {
      if (!fini && ctrl) { try { ctrl.abort(); } catch (e) {} }
    }, delai || DELAI_COURT);
    if (ctrl && !options.signal) options.signal = ctrl.signal;
    return fetch(url, options).then(function (r) {
      fini = true; clearTimeout(minuteur);
      if (r.status === 401) {
        sessionEteinte();
        var t = new Error("auth"); t.name = "SessionEteinte";
        throw t;
      }
      return r;
    }, function (e) {
      fini = true; clearTimeout(minuteur);
      /* On distingue le délai dépassé du reste : « le serveur n'a pas répondu
         en douze secondes » et « vous êtes hors ligne » n'appellent pas le
         même geste, et les confondre envoie chercher la panne du mauvais
         côté. */
      if (e && e.name === "AbortError" && !options.__annule) {
        var t = new Error("delai");
        t.name = "DelaiDepasse";
        t.delai = delai || DELAI_COURT;
        throw t;
      }
      throw e;
    });
  }
  /* Séparateur décimal français. Un « 1.47 » dans une note de calcul remise en
     France signale un document non relu — et ce détail-là, les évaluateurs le
     remarquent avant le contenu. */
  /* DÉLÈGUE À `nombres.js`, ET C'EST TOUT L'INTÉRÊT. Ce formateur était l'une
     de quatre copies du même barème — zéro décimale au-dessus de cent, une
     entre dix et cent — qui violait la règle d'or du site : on n'arrondit pas
     en dessous de deux décimales. Sur les valeurs réelles du moteur,
     « 5 857,4178 » s'affichait « 5 857 » et « 1,1489 » s'affichait « 1,1 ».
     Le barème est décidé à un seul endroit désormais ; les appels d'ici n'ont
     pas changé.

     LE REPLI NE MENT PAS. Si le module partagé n'est pas chargé, on formate
     quand même à deux décimales : une page sans chiffres est pire qu'une page
     aux chiffres moins bien groupés. */
  function fr(n, dec) {
    if (typeof window !== "undefined" && window.CPNombres)
      return window.CPNombres.fr(n, dec);
    if (n === null || n === undefined || n === "") return "—";
    var x = Number(n);
    if (!isFinite(x)) return String(n);
    return x.toFixed(Math.floor(x) === x ? 0 : 2).replace(".", ",");
  }
  function exact(n) {
    return (typeof window !== "undefined" && window.CPNombres)
      ? window.CPNombres.exact(n) : fr(n);
  }
  function etat(msg, err) {
    var el = $("#dc-etat");
    if (!el) return;
    el.textContent = msg || "";
    el.style.color = err ? "var(--red, #F0A0A0)" : "";
  }

  /* ── Le formulaire, construit depuis le référentiel du serveur ──────────
     Les listes déroulantes ne sont pas écrites dans le HTML : elles sont
     dérivées des mêmes tables que le calcul. Une option recopiée à la main
     finit toujours par proposer une valeur que le moteur ne connaît plus. */
  function bâtirFormulaire() {
    var champs = REF.champs || [];
    var h = '<div class="dc-grille">';
    champs.forEach(function (c) {
      var id = "dc-" + c.id;
      h += '<label class="dc-champ" for="' + id + '">'
        + '<span class="dc-lab">' + esc(c.label)
        + (c.unite ? ' <span class="dc-unite">(' + esc(c.unite) + ')</span>' : "")
        + (c.requis ? ' <b class="dc-req" title="Champ nécessaire">*</b>' : "")
        + "</span>";
      if (c.type === "liste") {
        h += '<select id="' + id + '" data-champ="' + esc(c.id) + '">';
        h += '<option value="">— non précisé —</option>';
        (c.options || []).forEach(function (o) {
          /* Le libellé vient du CHAMP, plus d'un cas particulier écrit ici.
             La page ne sait pas dans quelle table du référentiel chercher le
             nom d'une option — et n'a pas à le savoir. Faute de libellé, on
             affiche la clé : mieux vaut un code lisible qu'un vide. */
          var lib = (c.options_nom && c.options_nom[o]) || o;
          h += '<option value="' + esc(o) + '"'
            + (c.defaut === o ? " selected" : "") + ">" + esc(lib) + "</option>";
        });
        h += "</select>";
      } else {
        /* UNE LISTE DÉROULANTE, PAS UNE LISTE FERMÉE : le lecteur choisit
           dans le menu, ou tape la valeur réelle de son projet. */
        /* LES BORNES VIENNENT DU RÉFÉRENTIEL, posées sur le champ lui-même :
           le navigateur les connaît, l'assistance vocale les annonce, et la
           page n'en tient aucune copie qui pourrait diverger de celle du
           serveur. `type="text"` reste — un `type="number"` refuse la virgule
           décimale dans plusieurs navigateurs francophones, ce que ce
           formulaire accepte depuis toujours. */
        var d = c.domaine || {};
        h += '<input id="' + id + '" data-champ="' + esc(c.id) + '" type="text" inputmode="decimal"'
          + (d.min !== undefined ? ' data-min="' + esc(d.min) + '"' : "")
          + (d.max !== undefined ? ' data-max="' + esc(d.max) + '"' : "")
          + (d.pourquoi ? ' aria-describedby="' + id + '-dom"' : "")
          + (DEROULANTS.indexOf(c.id) >= 0 ? ' list="dc-dl-' + esc(c.id) + '"' : "")
          + (c.defaut !== undefined ? ' value="' + esc(c.defaut) + '"' : "")
          + ' placeholder="' + (c.defaut !== undefined ? esc(c.defaut) : "—") + '">';
        if (d.pourquoi) {
          h += '<span class="dc-dom" id="' + id + '-dom">Valeurs admises&nbsp;: '
            + esc(fr(d.min)) + " à " + esc(fr(d.max)) + " — " + esc(d.pourquoi)
            + ".</span>";
        }
      }
      if (c.aide) h += '<span class="dc-aide">' + esc(c.aide) + "</span>";
      /* Les valeurs proposées, sous le champ : c'est là qu'on hésite. */
      h += rendreSuggestions(c, "#dc-form");
      h += "</label>";
    });
    h += "</div>";
    $("#dc-form").innerHTML = h;
    brancherSuggestions("#dc-form");
    controlerPlages("#dc-form");
    $("#dc-form").addEventListener("input", function () { controlerPlages("#dc-form"); });
    majSuites();
    /* Les propositions contextuelles suivent les autres champs : la plage de
       PUE suit la famille de refroidissement, l'intensité carbone suit le
       pays. Sans cela, la page conseillerait sur un choix qui n'est plus le
       sien. */
    $("#dc-form").addEventListener("change", function () {
      majSuggestionsContexte("#dc-form");
      controlerPlages("#dc-form");
      expliquerFluides();
    });
    expliquerFluides();

    /* L'aperçu suit la saisie. Un seul écouteur posé sur le conteneur plutôt
       que treize sur les champs : le formulaire est reconstruit depuis le
       référentiel, et des écouteurs par champ seraient à reposer à chaque
       reconstruction — celui-ci survit. */
    $("#dc-form").addEventListener("input", function () { apercuProfil(); });
    $("#dc-form").addEventListener("change", function () { apercuProfil(); });
    apercuProfil(true);
  }


  /* ── Ce que le choix des fluides engage ─────────────────────────────────
     LE DÉFAUT CORRIGÉ. La liste « Famille de refroidissement » proposait sept
     libellés exacts et opaques. Le lecteur qui ne connaissait pas la
     différence entre un free cooling direct, un free cooling indirect à
     assistance adiabatique et une tour évaporative choisissait au hasard — et
     produisait une étude complète, d'apparence normale, sur une conception
     qu'il n'aurait pas retenue en connaissance de cause.

     CINQ CHOSES SONT DITES, dans l'ordre où on les demande en réunion : ce que
     la machine fait, à quelle condition ça marche, ce que ça coûte, ce que ça
     impose au reste du projet, et l'erreur classique. Elles viennent du
     serveur (technique_dc) : la page n'en écrit aucune, et n'a donc rien qui
     puisse diverger du moteur.

     LE MODE QUI N'EST PAS DANS LA LISTE Y FIGURE QUAND MÊME. Le free-chilling
     est une conduite d'une production d'eau glacée, pas une septième famille.
     Le taire ferait chercher une option absente ; le présenter comme une
     famille ferait croire à un choix de calcul qui n'existe pas. Il est donc
     annoncé pour ce qu'il est, sous la famille qui le porte. */
  function fluidesTechnique() {
    return (REF && REF.technique) || {};
  }

  function modeDeFamille(fam) {
    var M = fluidesTechnique().modes_refroidissement || {};
    for (var k in M) {
      if (Object.prototype.hasOwnProperty.call(M, k) && M[k].famille === fam) {
        return { cle: k, mode: M[k] };
      }
    }
    return null;
  }

  function conduitesDe(fam) {
    /* Les modes qui n'ont pas de famille de calcul et que CETTE famille porte.
       Ils ne s'affichent que là : rattachés à toutes les familles, ils
       laisseraient croire qu'un free-chilling se conduit sur un free cooling
       direct, ce qui n'a pas de sens. */
    var M = fluidesTechnique().modes_refroidissement || {}, out = [];
    for (var k in M) {
      if (Object.prototype.hasOwnProperty.call(M, k)
          && !M[k].famille && M[k].porte_par === fam) out.push(M[k]);
    }
    return out;
  }

  function expliquerFluides() {
    var z = $("#dc-fluides");
    if (!z) return;
    var sel = document.querySelector('#dc-form [data-champ="refroidissement"]');
    var fam = sel ? sel.value : "";
    var t = modeDeFamille(fam);
    if (!fam || !t) {
      /* PAS DE CHOIX, PAS D'EXPLICATION — mais on dit ce qui manque. Un bloc
         vide se lit comme un bloc cassé. */
      z.hidden = false;
      z.innerHTML = '<p class="note">Choisissez une famille de refroidissement '
        + "ci-dessus&nbsp;: sa technique, ce qu'elle coûte et ce qu'elle impose "
        + "au reste du projet s'afficheront ici.</p>";
      return;
    }
    var m = t.mode;
    var h = '<h3 class="dc-fl-t">' + esc(m.nom) + "</h3>"
      + '<p class="dc-fl-p">' + esc(m.principe) + "</p>"
      + '<dl class="dc-fl-l">'
      + "<dt>Quand ça marche</dt><dd>" + esc(m.quand) + "</dd>"
      + "<dt>Ce que ça coûte</dt><dd>" + esc(m.cout) + "</dd>"
      + "<dt>Ce que ça impose</dt><dd>" + esc(m.contrainte) + "</dd>"
      + '<dt class="dc-fl-e">L\'erreur classique</dt><dd class="dc-fl-e">'
      + esc(m.erreur) + "</dd></dl>";
    conduitesDe(fam).forEach(function (c) {
      h += '<div class="dc-fl-c"><b>' + esc(c.nom) + "</b> — "
        + esc(c.principe) + '<span class="dc-fl-n">Ce n\'est pas une option de '
        + "la liste ci-dessus&nbsp;: c'est une conduite de la famille retenue, "
        + "et le moteur la calcule sous elle.</span></div>";
    });
    /* LA SOURCE FERME LE BLOC, comme partout ailleurs sur cette page : ces
       descriptions cadrent un métier, elles ne fixent aucune performance. */
    if (fluidesTechnique().modes_source) {
      h += '<p class="dc-fl-s">' + esc(fluidesTechnique().modes_source) + "</p>";
    }
    z.hidden = false;
    z.innerHTML = h;
  }


  /* ── Les valeurs proposées sous un champ ────────────────────────────────
     Neuf champs sur treize sont des nombres libres. Devant « Cycles de
     concentration de la tour », qui ne sait pas déjà répond au hasard ou n'y
     touche pas — et un champ laissé sur son pré-remplissage compte comme non
     renseigné, donc bloque la phase sans que personne ne sache pourquoi.

     Chaque puce porte CE QU'ELLE EST, pas seulement un nombre : « 0,55 » se
     recopie sans réfléchir, « 0,55 — seuil sous lequel la charge partielle
     devient le premier poste de perte » se choisit.

     Deux origines, et la seconde vaut mieux que la première :

       · les propositions DÉCLARÉES au référentiel, servies avec le champ ;

       · les propositions CONTEXTUELLES, tirées de ce que le lecteur vient de
         choisir — la plage de PUE de SA famille de refroidissement,
         l'intensité carbone de SON pays. Ce sont des lectures du référentiel,
         jamais des nombres calculés ici : la page propose ce que le moteur
         sait déjà, elle n'invente rien.

     Ce ne sont pas des listes fermées : ces grandeurs sont continues, et
     imposer un choix parmi cinq interdirait la valeur réelle du projet — celle
     qu'on cherche précisément à obtenir. */
  function suggestionsContextuelles(idChamp, prefixe) {
    var R = (REF && REF.referentiel) || {};
    var lire = function (c) {
      var e = document.querySelector(prefixe + ' [data-champ="' + c + '"]');
      return e ? e.value : "";
    };
    if (idChamp === "pue_cible") {
      var f = (R.refroidissement || {})[lire("refroidissement")];
      if (f && f.pue_partiel) {
        return [
          { valeur: f.pue_partiel[0], nature: "plage_de_conception",
            nom: "bas de la plage de « " + f.nom + " »" },
          { valeur: f.pue_partiel[1], nature: "plage_de_conception",
            nom: "haut de la plage de « " + f.nom + " »" },
        ];
      }
    }
    if (idChamp === "intensite_reseau_g") {
      var pays = lire("pays");
      var v = (R.intensite_reseau || {})[pays];
      var nom = ((R.ewif || {})[pays] || {}).nom || pays;
      if (v !== undefined && v !== null) {
        return [{ valeur: v, nature: "moyenne_annuelle",
                  nom: "moyenne du mix " + nom + " — à remplacer par le "
                       + "facteur du contrat" }];
      }
    }
    /* COMBIEN DE SERVEURS ? Le compte n'est pas une donnée indépendante :
       c'est la puissance informatique — déjà saisie plus haut — divisée par la
       puissance d'un serveur. Les profils et leurs puissances viennent du
       MOTEUR, avec leur source ; la page ne fait que poser la division, et un
       contrôle vérifie qu'elle donne le même compte que lui. */
    if (idChamp === "nb_serveurs") {
      var pit = parseFloat(String(lire("puissance_it_kw")).replace(",", "."));
      var tab = ART.puissance_par_serveur || {};
      var ordre = ART.ordre_serveurs || [];
      if (!isFinite(pit) || pit <= 0 || !ordre.length) {
        return [{ valeur: null, nature: "derivation",
                  nom: "saisissez d'abord la puissance informatique : le "
                       + "nombre de serveurs s'en déduit" }];
      }
      return ordre.map(function (k) {
        var d = tab[k] || {};
        return { valeur: Math.max(1, Math.round(pit / d.kw)),
                 nature: d.obtention === "derive" ? "derive_de_la_source"
                                                  : "hypothese_du_module",
                 nom: d.nom + " — " + fr(d.kw) + " kW par serveur" };
      });
    }
    if (idChamp === "part_evaporative") {
      var g = (R.refroidissement || {})[lire("refroidissement")];
      if (g && g.eau_site) {
        return [{ valeur: null, nature: "usage",
                  nom: "eau de site de cette famille : " + g.eau_site }];
      }
    }
    return [];
  }

  /* Les champs dont les propositions dépendent d'un autre champ. Leur zone est
     posée MÊME VIDE : sans conteneur, rien ne peut s'y insérer quand le
     lecteur choisit enfin sa famille de refroidissement ou son pays — et la
     proposition la plus utile de la page n'apparaîtrait jamais. */
  var CHAMPS_CONTEXTUELS = ["pue_cible", "intensite_reseau_g", "part_evaporative",
                            "nb_serveurs"];

  /* Les champs dont les propositions s'offrent en MENU DÉROULANT plutôt qu'en
     puces. Le nombre de serveurs s'y prête : ses valeurs sont des comptes à
     quatre chiffres, illisibles en puces, et le menu porte le profil supposé
     en regard du nombre. */
  var DEROULANTS = ["nb_serveurs"];


  function rendreSuggestions(c, prefixe) {
    var props = (c.suggestions || []).concat(
      suggestionsContextuelles(c.id, prefixe));
    if (!props.length && CHAMPS_CONTEXTUELS.indexOf(c.id) < 0) return "";
    var h = '<span class="ig-sug" data-sug="' + esc(c.id) + '">';
    /* EN MENU DÉROULANT. Le menu est accroché au champ par son `list` ; il se
       redessine avec cette zone dès que la puissance informatique change,
       parce qu'il vit DEDANS. Posé ailleurs, il aurait gardé les comptes de la
       puissance précédente sans que rien ne le dise. */
    if (DEROULANTS.indexOf(c.id) >= 0) {
      var chiffrees = props.filter(function (s) {
        return s.valeur !== null && s.valeur !== undefined;
      });
      h += '<datalist id="dc-dl-' + esc(c.id) + '">';
      chiffrees.forEach(function (s) {
        h += '<option value="' + esc(s.valeur) + '" label="' + esc(s.nom) + '">';
      });
      h += "</datalist>";
      if (!chiffrees.length) {
        return h + '<span class="s-n">' + esc((props[0] || {}).nom || "") + "</span></span>";
      }
      /* Le menu ne se voit pas tant qu'on ne l'ouvre pas : on DIT ce qu'il
         contient, sinon personne ne pense à cliquer dans un champ vide. */
      h += '<span class="s-n">Menu déroulant&nbsp;: '
        + chiffrees.map(function (s) {
            return esc(fr(s.valeur)) + " — " + esc(s.nom);
          }).join(" · ")
        + ". Le champ reste libre : ces comptes se déduisent de la puissance "
        + "informatique, chacun pour le profil de serveur qu'il nomme.</span>";
      return h + "</span>";
    }
    props.forEach(function (s) {
      if (s.valeur === null || s.valeur === undefined) {
        /* Une indication sans valeur reste utile — « eau de site : modérée,
           saisonnière » oriente — mais elle ne se clique pas : rien à poser. */
        h += '<span class="s-n" title="' + esc(s.nom) + '">' + esc(s.nom) + "</span>";
        return;
      }
      h += '<button type="button" class="s-b" data-champ-cible="' + esc(c.id)
        + '" data-val="' + esc(s.valeur) + '" title="' + esc(s.nom)
        + ' — ' + esc(s.nature.replace(/_/g, " ")) + '">'
        + esc(fr(s.valeur)) + '<i>' + esc(s.nom) + "</i></button>";
    });
    return h + "</span>";
  }

  function brancherSuggestions(prefixe) {
    document.querySelectorAll(prefixe + " .ig-sug .s-b").forEach(function (b) {
      b.addEventListener("click", function () {
        var e = document.querySelector(prefixe + ' [data-champ="'
          + b.getAttribute("data-champ-cible") + '"]');
        if (!e) return;
        e.value = b.getAttribute("data-val");
        /* Les deux événements : « input » pour les champs texte, « change »
           pour que tout ce qui écoute l'un ou l'autre réagisse. Un seul des
           deux laisserait la moitié de la page en arrière. */
        e.dispatchEvent(new Event("input", { bubbles: true }));
        e.dispatchEvent(new Event("change", { bubbles: true }));
        try { e.focus({ preventScroll: true }); } catch (x) { e.focus(); }
      });
    });
  }

  /* Ce qui sort de ce qu'on OBSERVE. Jamais un refus : le calcul reste juste,
     et c'est au projet de savoir s'il est hors norme. Mais le taire laisse
     saisir cinq cents mégawatts sans un mot, et ne le découvrir qu'au
     chiffrage. */
  /* ══ CE QUE VAUT UNE SAISIE, ET COMMENT ON LE MONTRE ═════════════════════
     DEUX VERDICTS QUI NE DISENT PAS LA MÊME CHOSE, et les confondre serait une
     faute dans les deux sens.

       LE DOMAINE dit ce qu'une grandeur PEUT valoir. Un taux de charge est une
       charge rapportée à la puissance installée : il ne dépasse pas 1. Un PUE
       rapporte l'énergie totale à l'énergie informatique : sous 1, le centre
       produirait de l'énergie. Hors domaine, il n'y a rien à calculer — et le
       serveur écarte la valeur, qui n'entre pas dans l'étude.

       LA PLAGE OBSERVÉE est un cadrage du cabinet. Un centre de 15 kW en sort
       et se calcule très bien : la note l'explique. Le signaler comme un défaut
       priverait son auteur d'un résultat juste.

     D'OÙ LES DEUX ÉTATS. VERT : la valeur est recevable, le calcul la prendra.
     BLEU : elle ne l'est pas, et le champ dit POURQUOI — pas « erreur », mais
     la raison, parce que « c'est une part : entre 0 et 1 » se corrige et
     « champ invalide » ne se corrige pas. Un champ vide n'est ni l'un ni
     l'autre : il n'a pas été rempli, ce qui est un choix et se respecte sans
     couleur.

     LES BORNES VIENNENT DU SERVEUR, jamais d'une table écrite ici : une
     seconde source diverge, et c'est alors la page qui laisse passer ce que le
     serveur refusera — le pire des deux, puisque l'utilisateur aura vu du
     vert. */
  function verdictSaisie(c, brut) {
    if (brut === "" || brut === null || brut === undefined) return null;
    var v = parseFloat(String(brut).replace(",", ".").trim());
    if (!isFinite(v)) {
      return { ok: false, pourquoi: "cette saisie ne se lit pas comme un nombre" };
    }
    var d = c.domaine;
    if (d) {
      var tropBas = d.strict_min ? (v <= d.min) : (v < d.min);
      if (d.min !== undefined && tropBas) return { ok: false, pourquoi: d.pourquoi };
      if (d.max !== undefined && v > d.max) return { ok: false, pourquoi: d.pourquoi };
    }
    return { ok: true, valeur: v };
  }

  function controlerPlages(prefixe) {
    (((REF || {}).champs) || []).forEach(function (c) {
      var e = document.querySelector(prefixe + ' [data-champ="' + c.id + '"]');
      if (!e || c.type === "liste") return;
      var lab = e.closest(".dc-champ") || e.parentNode;
      var vieux = lab.querySelector(".ig-hors");
      if (vieux) vieux.remove();
      var vieuxR = lab.querySelector(".dc-refus");
      if (vieuxR) vieuxR.remove();

      var verdict = verdictSaisie(c, e.value);
      lab.classList.remove("dc-ok", "dc-ko");
      e.removeAttribute("aria-invalid");
      if (verdict) {
        lab.classList.add(verdict.ok ? "dc-ok" : "dc-ko");
        if (!verdict.ok) {
          /* `aria-invalid`, et pas seulement une couleur : un lecteur d'écran
             ne voit pas le liseré, et une saisie écartée doit s'entendre. */
          e.setAttribute("aria-invalid", "true");
          var r = document.createElement("span");
          r.className = "dc-refus";
          r.textContent = "Cette valeur n'entrera pas dans le calcul — "
            + verdict.pourquoi + ".";
          lab.appendChild(r);
        }
      }

      /* LA PLAGE OBSERVÉE RESTE UNE NOTE, jamais un refus — et elle ne
         s'affiche que sur une valeur RECEVABLE : commenter « c'est rare » une
         valeur déjà écartée superposerait deux messages contradictoires. */
      if (!c.plage_observee || !verdict || !verdict.ok) return;
      var p = c.plage_observee, msg = null;
      if (verdict.valeur > p.haut) msg = p.note;
      else if (verdict.valeur < p.bas) msg = p.note_bas || p.note;
      if (!msg) return;
      var n = document.createElement("span");
      n.className = "ig-hors";
      n.textContent = "Hors de ce qui s'observe (" + fr(p.bas) + " à "
        + fr(p.haut) + ") — " + msg;
      lab.appendChild(n);
    });
    majAvancement(prefixe);
  }

  /* ══ OÙ L'ON EN EST, ET CE QU'IL RESTE À FAIRE ═══════════════════════════
     Le formulaire dit désormais champ par champ ce qu'il accepte. Il ne disait
     rien de l'ENSEMBLE : combien de champs sont remplis, si l'étude peut
     partir, et ce qui la retient. Le lecteur cliquait « Calculer » pour
     l'apprendre — et découvrait le manque après coup.

     LE COMPTE EST CELUI DES CHAMPS RECEVABLES, pas des champs remplis : une
     saisie bleue ne compte pas, puisqu'elle n'entrera pas dans le calcul. */
  /* ══ LE PASSAGE AU BLOC SUIVANT ═════════════════════════════════════════
     La page est une suite d'étapes — profil, résultats, comparaison,
     équipements, décarbonation — dont plusieurs restent MASQUÉES tant que le
     calcul n'a pas eu lieu. Rien ne disait laquelle vient après : le lecteur
     faisait défiler pour chercher, et manquait les blocs qui venaient
     d'apparaître sous ses yeux plus bas.

     LA FLÈCHE SE RECALCULE À CHAQUE CHANGEMENT D'ÉTAT, parce que la suite
     change : après le calcul, trois sections s'ouvrent et la suivante n'est
     plus la même. Une flèche posée une fois pointerait vers l'étape d'avant.

     ELLE NE S'AFFICHE QUE S'IL Y A UNE SUITE. Une flèche vers rien apprend au
     lecteur à ne plus la regarder — et c'est alors toute la signalétique qui
     ne sert plus. */
  function majSuites() {
    var sections = Array.prototype.slice.call(
      document.querySelectorAll("section.rc-sec[id^='dc-sec-']"));
    var visibles = sections.filter(function (s) { return !s.hidden; });
    sections.forEach(function (s) {
      var vieux = s.querySelector(":scope > .dc-suite");
      if (vieux) vieux.remove();
    });
    visibles.forEach(function (s, i) {
      var suivante = visibles[i + 1];
      if (!suivante) return;
      var titre = suivante.querySelector("h2, h3");
      var nom = titre ? titre.textContent.trim() : "la suite";
      var a = document.createElement("button");
      a.type = "button";
      a.className = "dc-suite";
      a.innerHTML = '<span class="dc-suite-n">Étape ' + (i + 2) + " / "
        + visibles.length + '</span><span>' + esc(nom)
        + '</span><span class="dc-suite-f" aria-hidden="true">→</span>';
      a.setAttribute("aria-label", "Aller à l'étape suivante : " + nom);
      a.addEventListener("click", function () {
        var doux = !(window.matchMedia
          && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
        suivante.scrollIntoView({ behavior: doux ? "smooth" : "auto",
                                  block: "start" });
        /* LE FOCUS SUIT LE DÉFILEMENT. Sans lui, la tabulation repart du haut
           du document et le lecteur au clavier perd l'étape où il vient
           d'arriver — le geste ne l'aurait servi qu'à la souris. */
        var cible = suivante.querySelector("h2, h3") || suivante;
        if (!cible.hasAttribute("tabindex")) cible.setAttribute("tabindex", "-1");
        cible.focus({ preventScroll: true });
      });
      s.appendChild(a);
    });
  }

  function majAvancement(prefixe) {
    var zone = document.querySelector("#dc-avancement");
    if (!zone) return;
    var champs = (((REF || {}).champs) || []).filter(function (c) {
      return c.type !== "liste";
    });
    var verts = 0, bleus = 0, requis = null;
    champs.forEach(function (c) {
      var e = document.querySelector(prefixe + ' [data-champ="' + c.id + '"]');
      if (!e) return;
      var v = verdictSaisie(c, e.value);
      if (!v) return;
      if (v.ok) verts++; else bleus++;
    });
    var pit = document.querySelector(prefixe + ' [data-champ="puissance_it_kw"]');
    var pitOk = pit && (verdictSaisie(
      (((REF || {}).champs) || []).filter(function (c) {
        return c.id === "puissance_it_kw";
      })[0] || {}, pit.value) || {}).ok;
    if (!pitOk) {
      requis = "La puissance informatique installée est nécessaire : toutes les "
        + "grandeurs en dépendent.";
    }
    zone.className = "dc-av" + (pitOk ? " prete" : "");
    zone.innerHTML =
      '<span class="dc-av-n"><b>' + verts + "</b> / " + champs.length
      + " champ" + (champs.length > 1 ? "s" : "") + " recevable"
      + (verts > 1 ? "s" : "") + "</span>"
      + (bleus ? '<span class="dc-av-ko">' + bleus + " à corriger</span>" : "")
      + (requis ? '<span class="dc-av-r">' + esc(requis) + "</span>"
                : '<span class="dc-av-ok">L\'étude peut être lancée. '
                  + "Chaque champ ajouté resserre l'incertitude.</span>");
  }

  function majSuggestionsContexte(prefixe) {
    /* LA LISTE VIENT DE LA CONSTANTE, plus d'une copie écrite ici : les deux
       devaient rester d'accord, et un champ ajouté à l'une sans l'autre posait
       un conteneur que rien ne redessinait. */
    CHAMPS_CONTEXTUELS.forEach(function (id) {
      var zone = document.querySelector(prefixe + ' [data-sug="' + id + '"]');
      if (!zone) return;
      var c = (((REF || {}).champs) || []).filter(function (x) {
        return x.id === id;
      })[0];
      if (!c) return;
      var neuf = rendreSuggestions(c, prefixe);
      if (!neuf) { zone.innerHTML = ""; return; }
      var tmp = document.createElement("div");
      tmp.innerHTML = neuf;
      zone.replaceWith(tmp.firstChild);
      brancherSuggestions(prefixe);
    });
  }

  function lireProfil() {
    var p = {};
    document.querySelectorAll("#dc-form [data-champ]").forEach(function (el) {
      var v = (el.value || "").trim();
      if (v !== "") p[el.getAttribute("data-champ")] = v;
    });
    return p;
  }

  /* ── Une valeur, avec ce qui la rend défendable ─────────────────────────
     La formule et la source sont dans un <details> : présentes pour qui
     vérifie, discrètes pour qui survole. Les cacher tout à fait reviendrait à
     livrer un chiffre nu ; les afficher toujours rendrait la page illisible. */
  /* L'INFOBULLE DU CALCUL — au survol ET au focus clavier.

     CE QU'ELLE PORTE, ET PAS UNE DE MOINS : l'équation, la même AVEC LES
     DONNÉES, le résultat EXACT (l'affichage est arrondi à deux décimales,
     celui-ci ne l'est pas), l'incertitude, la source normative. Une seule qui
     manque, et le chiffre redevient un chiffre qu'on croit sur parole.

     ELLE S'OUVRE AUSSI AU FOCUS. Une infobulle qui n'existe qu'au passage de
     la souris exclut ceux qui n'en ont pas, et perd son texte pour un lecteur
     d'écran comme à l'impression.

     ET ELLE NE MONTRE PAS D'ÉQUATION À MOITIÉ SUBSTITUÉE. Le serveur vérifie
     que l'équation chiffrée retombe sur la valeur ; celle qui n'y retombe pas
     ne décrit pas ce calcul, et se tait en disant pourquoi. */
  function bulleCalcul(v) {
    var l = [];
    if (v.formule) l.push(['<span class="dc-b-t">Équation</span>', esc(v.formule)]);
    if (v.calcul) {
      l.push(['<span class="dc-b-t">Avec vos données</span>',
              '<span class="dc-b-c">' + esc(v.calcul) + "</span>"]);
    } else if (v.calcul_incomplet) {
      l.push(['<span class="dc-b-t">Avec vos données</span>',
              '<span class="dc-b-k">' + esc(v.calcul_incomplet) + "</span>"]);
    }
    if (v.entrees) {
      /* LES ENTRÉES SUIVENT LA MÊME RÈGLE QUE L'ÉQUATION. Rendues brutes,
         elles s'affichaient « 1200 » et « 0.65 » à côté d'une équation qui
         écrit « 1 200 » et « 0,65 » : deux écritures du même nombre dans la
         même infobulle font douter des deux. */
      var e = Object.keys(v.entrees).map(function (k) {
        var x = v.entrees[k];
        return esc(k) + " = "
          + (typeof x === "number" ? fr(x) : esc(x));
      }).join(" · ");
      if (e) l.push(['<span class="dc-b-t">Entrées</span>', e]);
    }
    l.push(['<span class="dc-b-t">Valeur exacte</span>',
            esc(v.exact != null ? v.exact : fr(v.valeur))
            + (v.unite ? " " + esc(v.unite) : "")]);
    if (v.incertitude) l.push(['<span class="dc-b-t">Incertitude</span>', esc(v.incertitude)]);
    if (v.source) l.push(['<span class="dc-b-t">Source</span>', esc(v.source)]);
    return l.map(function (x) { return "<div>" + x[0] + x[1] + "</div>"; }).join("");
  }

  var _bulleN = 0;

  function carte(v) {
    if (!v || v.valeur === undefined) return "";
    var id = "dc-b" + (++_bulleN);
    var h = '<div class="dc-val">'
      + '<div class="dc-val-n">' + esc(v.nom) + "</div>"
      + '<button type="button" class="dc-val-v dc-b-h" aria-describedby="' + id
      + '">' + fr(v.valeur)
      + ' <span class="dc-val-u">' + esc(v.unite) + "</span>"
      + '<span class="dc-bulle" role="tooltip" id="' + id + '">'
      + bulleCalcul(v) + "</span></button>";
    if (v.incertitude) h += '<div class="dc-val-i">' + esc(v.incertitude) + "</div>";
    var det = "";
    if (v.formule) det += "<div><b>Formule</b> — " + esc(v.formule) + "</div>";
    if (v.entrees) {
      var e = Object.keys(v.entrees).map(function (k) {
        return esc(k) + " = " + esc(v.entrees[k]);
      }).join(" · ");
      if (e) det += "<div><b>Entrées</b> — " + e + "</div>";
    }
    if (v.source) det += "<div><b>Source</b> — " + esc(v.source) + "</div>";
    if (v.note) det += "<div class='dc-note'>" + esc(v.note) + "</div>";
    if (det) {
      h += '<details class="dc-det"><summary>méthode et source</summary>'
        + '<div class="dc-det-c">' + det + "</div></details>";
    }
    return h + "</div>";
  }

  function bloc(titre, sous, section, cles) {
    var d = ETUDE[section] || {}, corps = "";
    cles.forEach(function (k) { corps += carte(d[k]); });
    if (!corps) return "";
    return '<section class="dc-bloc"><h3>' + esc(titre) + "</h3>"
      + (sous ? '<p class="dc-sous">' + esc(sous) + "</p>" : "")
      + '<div class="dc-vals">' + corps + "</div></section>";
  }

  function afficherResultats() {
    var h = "";
    h += bloc("Énergie",
      "Le PUE est calculé depuis la conception, pas reçu en entrée : un PUE annoncé "
      + "sans sa décomposition n'est pas vérifiable.",
      "energie", ["pue", "energie_it_MWh", "energie_totale_MWh", "energie_non_it_MWh", "dcie"]);
    h += bloc("Eau",
      "Le WUE de site est celui qu'on publie ; le WUE de source est celui qui doit "
      + "arbitrer. Un rejet sec affiche un WUE de site nul tout en consommant plus "
      + "d'eau à la source si le mix est thermique.",
      "eau", ["evaporation_m3", "purge_m3", "appoint_m3", "wue_site", "wue_source", "eau_amont_m3"]);
    h += bloc("Carbone",
      "Exploitation ET incorporé. Sur un mix décarboné, l'incorporé devient "
      + "majoritaire : l'ignorer conduit à optimiser ce qui ne pèse plus.",
      "carbone", ["cue", "co2_exploitation_localise_t", "co2_exploitation_marche_t", "ref",
                  "incorpore_serveurs_t", "incorpore_batiment_t", "incorpore_technique_t",
                  "empreinte_totale_t", "part_incorpore_pct"]);
    var ch = ETUDE.chaleur || {};
    h += bloc("Chaleur fatale",
      "Température de rejet : " + fr(ch.temperature_rejet_c) + " °C. " + (ch.valorisation || ""),
      "chaleur", ["erf", "ere", "energie_reutilisee_MWh"]);

    var lev = ETUDE.leviers || [];
    if (lev.length) {
      h += '<section class="dc-bloc"><h3>Leviers</h3>'
        + '<p class="dc-sous">Classés par gain carbone. Chaque levier porte sa '
        + 'contrepartie : un levier présenté sans la sienne est un argument '
        + 'commercial, pas une recommandation d\'ingénierie.</p>'
        + '<div class="dc-tab-wrap"><table class="dc-tab"><thead><tr>'
        + "<th>Levier</th><th>tCO2e/an</th><th>m³ eau/an</th><th>MWh/an</th>"
        + "<th>€/an</th><th>Difficulté</th></tr></thead><tbody>";
      lev.forEach(function (l) {
        h += "<tr><th scope='row'>" + esc(l.titre) + "</th>"
          + "<td>" + fr(l.gain_co2_t) + "</td><td>" + fr(l.gain_eau_m3) + "</td>"
          + "<td>" + fr(l.gain_energie_MWh) + "</td><td>" + fr(l.gain_euros) + "</td>"
          + "<td>" + esc(l.difficulte) + "</td></tr>";
      });
      h += "</tbody></table></div>";
      lev.forEach(function (l) {
        h += '<details class="dc-det"><summary>' + esc(l.titre) + "</summary>"
          + '<div class="dc-det-c">'
          + "<div><b>Contrepartie</b> — " + esc(l.contrepartie) + "</div>"
          + "<div><b>Condition</b> — " + esc(l.condition) + "</div>"
          + "<div><b>Fondement</b> — " + esc(l.fondement) + "</div>"
          + (l.note_gain ? "<div class='dc-note'>" + esc(l.note_gain) + "</div>" : "")
          + "</div></details>";
      });
      h += "</section>";
    }

    var conf = ETUDE.conformite || [];
    if (conf.length) {
      h += '<section class="dc-bloc"><h3>Conformité et repères de marché</h3>'
        + '<div class="dc-tab-wrap"><table class="dc-tab"><thead><tr>'
        + "<th>Sujet</th><th>Statut</th><th>Détail</th></tr></thead><tbody>";
      conf.forEach(function (c) {
        h += "<tr><th scope='row'>" + esc(c.sujet) + "</th>"
          + '<td><span class="dc-st dc-st-' + esc(c.statut).replace(/[^a-z]/g, "")
          + '">' + esc(c.statut) + "</span></td>"
          + "<td>" + esc(c.detail) + "</td></tr>";
      });
      h += "</tbody></table></div></section>";
    }

    var av = ETUDE.avertissements || [];
    if (av.length) {
      h += '<section class="dc-bloc dc-limites"><h3>Ce que ce calcul ne dit pas</h3>'
        + '<p class="dc-sous">Ces réserves font partie du résultat. Un moteur qui ne '
        + 'déclare pas ses limites les fait porter par son lecteur, qui ne les '
        + 'connaît pas.</p><ul>';
      av.forEach(function (a) { h += "<li>" + esc(a) + "</li>"; });
      h += "</ul></section>";
    }

    $("#dc-resultats").innerHTML = h;
    $("#dc-sec-res").hidden = false;
    majSuites();
  }

  /* ── Graphiques ────────────────────────────────────────────────────────
     SVG écrit à la main, sans bibliothèque : la page pèse déjà ce qu'elle
     pèse, et trois barres horizontales ne justifient pas trois cents kilo-
     octets de dépendance.

     Toutes les valeurs viennent de la réponse du serveur. Aucune n'est
     recalculée ici : un graphique qui refait le calcul du tableau qu'il
     surplombe finit par en diverger, et c'est le graphique qu'on croit. */
  var COUL = { site: "#22D3EE", source: "#F0B429",
               expl: "#D9603A", inc: "#8B7CF6", retenue: "#F6F0E8" };

  function barres(lignes, sers, opts) {
    opts = opts || {};
    var max = 0;
    lignes.forEach(function (l) {
      sers.forEach(function (s2) { max = Math.max(max, s2.val(l) || 0); });
    });
    if (opts.empile) {
      max = 0;
      lignes.forEach(function (l) {
        var t = 0; sers.forEach(function (s2) { t += s2.val(l) || 0; });
        max = Math.max(max, t);
      });
    }
    if (!max) return "";
    var hL = opts.empile ? 30 : 34, ecart = 12, gauche = 210, droite = 96;
    var larg = 860, H = lignes.length * (hL + ecart) + 8;
    var util = larg - gauche - droite;
    /* Le conteneur défilant : sur un écran étroit, mieux vaut faire glisser le
       graphique que comprimer sept barres jusqu'à ce qu'elles ne comparent
       plus rien. Sans ce wrapper, la règle `overflow-x` de la feuille de style
       ne s'applique à rien. */
    var h = '<div class="dc-g-wrap"><svg class="dc-g" viewBox="0 0 ' + larg + " " + H + '" role="img" '
      + 'preserveAspectRatio="xMinYMin meet" aria-label="' + esc(opts.alt || "") + '">';
    lignes.forEach(function (l, i) {
      var y = i * (hL + ecart) + 4;
      var courante = l.famille === (PROFIL.refroidissement || "");
      h += '<text x="0" y="' + (y + hL / 2 + 4) + '" class="dc-g-l'
        + (courante ? " on" : "") + '">' + esc(abrege(l.nom))
        + (courante ? " ◄" : "") + "</text>";
      if (opts.empile) {
        var x = gauche, tot = 0;
        sers.forEach(function (s2) {
          var v = s2.val(l) || 0, w = util * v / max;
          if (w > 0.4) h += '<rect x="' + x.toFixed(1) + '" y="' + y + '" width="'
            + w.toFixed(1) + '" height="' + hL + '" fill="' + s2.c + '"><title>'
            + esc(s2.nom + " : " + fr(v) + " " + (opts.unite || "")) + "</title></rect>";
          x += w; tot += v;
        });
        h += '<text x="' + (gauche + util * tot / max + 8).toFixed(1) + '" y="'
          + (y + hL / 2 + 4) + '" class="dc-g-v">' + fr(tot)
          + (opts.suffixe ? " " + esc(opts.suffixe) : "") + "</text>";
      } else {
        var hb = (hL - 4) / sers.length;
        sers.forEach(function (s2, j) {
          var v = s2.val(l) || 0, w = util * v / max;
          var yy = y + j * (hb + 2);
          h += '<rect x="' + gauche + '" y="' + yy + '" width="' + Math.max(1, w).toFixed(1)
            + '" height="' + hb.toFixed(1) + '" fill="' + s2.c + '"><title>'
            + esc(s2.nom + " : " + fr(v) + " " + (opts.unite || "")) + "</title></rect>";
          h += '<text x="' + (gauche + w + 8).toFixed(1) + '" y="' + (yy + hb / 2 + 3.5)
            + '" class="dc-g-v">' + fr(v) + "</text>";
        });
      }
    });
    return h + "</svg></div>"
      + '<div class="dc-g-lg">' + sers.map(function (s2) {
          return '<span><i style="background:' + s2.c + '"></i>' + esc(s2.nom) + "</span>";
        }).join("") + (opts.legende ? "<span>" + opts.legende + "</span>" : "") + "</div>";
  }

  /* ── L'aperçu du profil : ce qui reste ouvert avant de calculer ─────────
     L'étape 1 affirme que « renseigner davantage resserre les incertitudes ».
     Cette affirmation était invérifiable — il fallait la croire. Le serveur la
     chiffre maintenant (profil_dc.py) en rejouant l'étude sur le domaine de
     chaque champ vide ; ici, on la dessine. Aucun de ces nombres n'est calculé
     dans le navigateur. */

  /* La couleur dit d'où le balayage tire son autorité. C'est la seule
     information qu'un lecteur ne peut pas deviner en regardant une barre, et
     c'est celle qui décide s'il peut s'en servir dans un dossier. */
  var COUL_NATURE = { referentiel: "#22D3EE", definition: "#8B7CF6", hypothese: "#F0B429" };
  var NOM_NATURE = {
    referentiel: "énuméré au référentiel",
    definition: "borné par définition",
    hypothese: "balayage déclaré",
  };

  /* La courbe de charge partielle. Le coude vient du serveur, qui l'a DÉTECTÉ
     sur les points calculés ; l'écrire ici en dur aurait fabriqué une seconde
     définition du seuil, qui aurait survécu à un changement du moteur. */
  function courbeCharge(c) {
    if (!c || !c.disponible || !(c.points || []).length) return "";
    var P = c.points;
    var L = 880, H = 300, mg = 58, md = 22, mh = 18, mb = 44;
    var x0 = mg, x1 = L - md, y0 = mh, y1 = H - mb;
    var tMin = P[0].taux, tMax = P[P.length - 1].taux;
    var lo = Infinity, hi = -Infinity;
    P.forEach(function (p) {
      lo = Math.min(lo, p.pue_min); hi = Math.max(hi, p.pue_max);
    });
    if (hi - lo < 0.02) { lo -= 0.05; hi += 0.05; }   /* PUE imposé : bande nulle */
    var pad = (hi - lo) * 0.12; lo -= pad; hi += pad;
    var X = function (t) { return x0 + (t - tMin) / (tMax - tMin) * (x1 - x0); };
    var Y = function (v) { return y1 - (v - lo) / (hi - lo) * (y1 - y0); };
    /* Sur un axe, le nombre de décimales doit être CONSTANT. fr() supprime les
       zéros de fin, ce qui donnait « 1,676 » au-dessus de « 1,44 » : l'œil
       compare alors des chiffres qui n'ont pas le même rang. */
    var pas = (hi - lo) / 4;
    var dec = pas >= 1 ? 0 : pas >= 0.1 ? 2 : 3;
    var axe = function (v) { return v.toFixed(dec).replace(".", ","); };

    var h = '<div class="dc-g-wrap"><svg class="dc-g dc-c" viewBox="0 0 ' + L + " " + H + '" '
      + 'role="img" preserveAspectRatio="xMinYMin meet" aria-label="'
      + esc("Courbe du PUE en fonction du taux de charge, de "
            + fr(tMin) + " à " + fr(tMax) + ". PUE de "
            + fr(P[P.length - 1].pue) + " à pleine charge, "
            + fr(P[0].pue) + " au taux le plus bas."
            + (c.coude ? " Coude détecté à " + fr(c.coude.taux) + "." : "")) + '">';

    /* Grille horizontale : quatre lignes suffisent à situer une valeur ; au
       delà elles concurrencent la courbe. */
    var i, v;
    for (i = 0; i <= 4; i++) {
      v = lo + (hi - lo) * i / 4;
      h += '<line class="dc-c-gr" x1="' + x0 + '" y1="' + Y(v).toFixed(1)
        + '" x2="' + x1 + '" y2="' + Y(v).toFixed(1) + '"/>'
        + '<text class="dc-c-ax" x="' + (x0 - 8) + '" y="' + (Y(v) + 4).toFixed(1)
        + '" text-anchor="end">' + axe(v) + "</text>";
    }
    P.forEach(function (p, j) {
      if (j % 4) return;
      h += '<text class="dc-c-ax" x="' + X(p.taux).toFixed(1) + '" y="' + (y1 + 20)
        + '" text-anchor="middle">' + fr(p.taux) + "</text>";
    });
    h += '<text class="dc-c-ti" x="' + ((x0 + x1) / 2).toFixed(0) + '" y="' + (H - 8)
      + '" text-anchor="middle">Taux de charge moyen</text>'
      + '<text class="dc-c-ti" transform="translate(14,' + ((y0 + y1) / 2).toFixed(0)
      + ') rotate(-90)" text-anchor="middle">PUE</text>';

    /* La bande de conception, en aire : c'est elle l'incertitude. Tracer la
       seule ligne médiane donnerait un PUE qui a l'air connu au millième. */
    var haut = P.map(function (p) { return X(p.taux).toFixed(1) + "," + Y(p.pue_max).toFixed(1); });
    var bas = P.slice().reverse().map(function (p) {
      return X(p.taux).toFixed(1) + "," + Y(p.pue_min).toFixed(1);
    });
    h += '<polygon class="dc-c-bd" points="' + haut.concat(bas).join(" ") + '"/>';
    h += '<polyline class="dc-c-li" points="'
      + P.map(function (p) { return X(p.taux).toFixed(1) + "," + Y(p.pue).toFixed(1); }).join(" ")
      + '"/>';

    if (c.coude) {
      h += '<line class="dc-c-cd" x1="' + X(c.coude.taux).toFixed(1) + '" y1="' + y0
        + '" x2="' + X(c.coude.taux).toFixed(1) + '" y2="' + y1 + '"/>'
        + '<text class="dc-c-cl" x="' + (X(c.coude.taux) + 6).toFixed(1) + '" y="' + (y0 + 12)
        + '">coude ' + fr(c.coude.taux) + "</text>";
    }
    /* Chaque point porte son infobulle : la valeur exacte s'y lit sans encombrer
       le tracé, et l'énergie annuelle avec elle — c'est elle qu'on paie. */
    P.forEach(function (p) {
      h += '<circle class="dc-c-pt" cx="' + X(p.taux).toFixed(1) + '" cy="' + Y(p.pue).toFixed(1)
        + '" r="7"><title>' + esc("Taux " + fr(p.taux) + " · PUE " + fr(p.pue)
          + " (bande " + fr(p.pue_min) + "–" + fr(p.pue_max) + ") · "
          + fr(p.energie_totale_MWh) + " MWh/an") + "</title></circle>";
    });
    var k = c.courant;
    if (k) {
      h += '<circle class="dc-c-ic" cx="' + X(k.taux).toFixed(1) + '" cy="' + Y(k.pue).toFixed(1)
        + '" r="5.5"/>'
        + '<text class="dc-c-cl on" x="' + X(k.taux).toFixed(1) + '" y="' + (Y(k.pue) - 12).toFixed(1)
        + '" text-anchor="middle">'
        + esc((c.taux_renseigne ? "votre taux " : "défaut ") + fr(k.taux)) + "</text>";
    }
    h += "</svg></div>";

    /* La pastille de légende reprend EXACTEMENT le remplissage de la bande —
       .dc-c-bd — sinon la légende désigne une couleur qui n'est pas à l'écran. */
    h += '<div class="dc-g-lg"><span><i style="background:#22D3EE"></i>PUE calculé</span>'
      + '<span><i style="background:rgba(34,211,238,.34);'
      + 'outline:1px solid rgba(34,211,238,.55)"></i>plage de conception — '
      + esc(c.famille) + "</span>"
      + (c.coude ? '<span><i style="background:#F0B429"></i>coude détecté sur les points calculés</span>' : "")
      + "</div>";
    h += '<p class="dc-lecture">' + esc(c.note)
      + (c.coude ? " <b>Au-dessous de " + esc(fr(c.coude.taux)) + "</b>, chaque point de "
          + "charge perdu dégrade le PUE ; au-dessus, il n'entre plus dans ce modèle." : "")
      + "</p>";
    return h;
  }

  /* Ce que chaque champ vide laisse encore ouvert. Les barres sont classées par
     portée décroissante : la première est le champ à renseigner en priorité,
     et c'est la seule question que se pose un lecteur devant ce graphique. */
  function tornade(s) {
    if (!s || !s.disponible) return "";
    var F = s.facteurs || [];
    if (!F.length) {
      return '<p class="dc-lecture">Tous les champs à domaine borné sont renseignés. '
        + "Il ne reste que les incertitudes du référentiel lui-même, publiées à l'étape 5.</p>";
    }
    var hL = 26, ec = 10, gauche = 250, droite = 62;
    var larg = 880, H = F.length * (hL + ec) + 8, util = larg - gauche - droite;
    var h = '<div class="dc-g-wrap"><svg class="dc-g" viewBox="0 0 ' + larg + " " + H + '" '
      + 'role="img" preserveAspectRatio="xMinYMin meet" aria-label="'
      + esc("Part de chaque grandeur encore indéterminée, par champ non renseigné. "
            + F.map(function (f) { return f.label + " " + fr(f.portee_max_pct) + " %"; })
                .join(" ; ")) + '">';
    F.forEach(function (f, i) {
      var y = i * (hL + ec) + 4;
      var w = util * Math.max(0, Math.min(100, f.portee_max_pct)) / 100;
      var c = COUL_NATURE[f.nature] || "#F6F0E8";
      var det = (s.indicateurs || []).map(function (ind) {
        var e = (f.etendues || {})[ind.cle];
        if (!e) return "";
        return ind.nom + " : " + fr(e.min) + " – " + fr(e.max)
          + (ind.unite ? " " + ind.unite : "");
      }).filter(Boolean).join("\n");
      h += '<text x="0" y="' + (y + hL / 2 + 4) + '" class="dc-g-l">'
        + esc(abrege(f.label)) + "</text>"
        + '<rect x="' + gauche + '" y="' + y + '" width="' + util + '" height="' + hL
        + '" class="dc-t-fd"/>'
        + '<rect x="' + gauche + '" y="' + y + '" width="' + Math.max(1, w).toFixed(1)
        + '" height="' + hL + '" fill="' + c + '"><title>'
        + esc(f.label + " — " + NOM_NATURE[f.nature] + " (" + f.n_valeurs + " valeurs balayées)\n"
              + det) + "</title></rect>"
        + '<text x="' + (gauche + util + 8) + '" y="' + (y + hL / 2 + 4) + '" class="dc-g-v">'
        + fr(f.portee_max_pct) + " %</text>";
    });
    h += "</svg></div>";

    h += '<div class="dc-g-lg">'
      + Object.keys(NOM_NATURE).map(function (n) {
          return '<span><i style="background:' + COUL_NATURE[n] + '"></i>' + esc(NOM_NATURE[n]) + "</span>";
        }).join("") + "</div>";

    h += '<p class="dc-lecture"><b>' + esc(s.portee_definition) + "</b> "
      + esc(s.note_addition) + " " + esc(s.balayage_note) + "</p>";

    if ((s.leviers_seuls || []).length) {
      h += '<p class="dc-lecture">' + esc(s.leviers_seuls.join(", "))
        + (s.leviers_seuls.length > 1 ? " ne changent " : " ne change ")
        + "aucune des grandeurs suivies, mais " + (s.leviers_seuls.length > 1 ? "modifient" : "modifie")
        + " les leviers que le moteur propose. Une barre à zéro ne veut pas dire "
        + "que le champ est inutile — seulement qu'il agit ailleurs.</p>";
    }
    if ((s.exclus || []).length) {
      h += '<details class="dc-det"><summary>Les champs volontairement non balayés ('
        + s.exclus.length + ")</summary><div class='dc-det-c'>"
        + s.exclus.map(function (x) {
            return "<div><b>" + esc(x.label) + "</b> — " + esc(x.motif) + "</div>";
          }).join("") + "</div></details>";
    }
    return h;
  }

  /* Le relevé des valeurs par défaut. La page promet qu'elles sont « signalées
     comme telles dans la note » ; autant les signaler AVANT le calcul, quand
     il est encore temps de les remplacer. */
  function releveDefauts(d) {
    if (!d) return "";
    /* Trois états, pas deux. Un champ pré-rempli par le formulaire n'est pas
       « renseigné » : la première version les comptait ensemble et annonçait
       sept saisies là où il n'y en avait qu'une. */
    var h = '<div class="dc-rel"><div class="dc-rel-t"><b>' + d.n_renseignes + "</b> champ"
      + (d.n_renseignes > 1 ? "s" : "") + " renseigné" + (d.n_renseignes > 1 ? "s" : "")
      + " sur " + d.n_total + " · <b>" + d.n_valeur_defaut + "</b> laissé"
      + (d.n_valeur_defaut > 1 ? "s" : "") + " sur la valeur par défaut · <b>"
      + d.n_absents + "</b> non précisé" + (d.n_absents > 1 ? "s" : "")
      + "</div><div class='dc-rel-l'>";
    (d.champs || []).forEach(function (c) {
      var t = c.etat === "saisi" ? "renseigné : " + c.valeur
        : c.etat === "defaut" ? "laissé sur la valeur par défaut : " + c.valeur
        : "non précisé — le moteur applique sa valeur de repli";
      h += '<span class="dc-rel-p e-' + esc(c.etat) + '" title="' + esc(t) + '">'
        + esc(abrege(c.label)) + "</span>";
    });
    h += "</div>";
    if (d.note) h += '<p class="dc-rel-n">' + esc(d.note) + "</p>";
    return h + "</div>";
  }

  /* L'appel : différé, et le précédent annulé. Sans annulation, deux frappes
     rapprochées font revenir les réponses dans l'ordre du réseau et non dans
     celui de la saisie — le graphique affiche alors l'avant-dernier profil. */
  var _minuteur = null, _vol = null;

  function apercuProfil(immediat) {
    var zone = $("#dc-apercu");
    if (!zone) return;
    if (_minuteur) clearTimeout(_minuteur);
    _minuteur = setTimeout(function () {
      var p = lireProfil();
      if (!p.puissance_it_kw) {
        zone.innerHTML = '<p class="note dc-ap-vide">Renseignez la puissance informatique '
          + "installée : c'est la seule entrée indispensable, et elle suffit à ouvrir "
          + "l'analyse ci-dessous.</p>";
        return;
      }
      if (_vol) { try { _vol.abort(); } catch (e) {} }
      _vol = (typeof AbortController !== "undefined") ? new AbortController() : null;
      zone.classList.add("occupe");
      demander("/api/datacenter/profil", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(p),
        signal: _vol ? _vol.signal : undefined,
        // L'aperçu s'annule VOLONTAIREMENT à chaque nouvelle frappe : sans ce
        // drapeau, chaque caractère tapé afficherait « délai dépassé ».
        __annule: true,
      }, DELAI_COURT)
        .then(function (r) { return r.json(); })
        .then(function (j) {
          zone.classList.remove("occupe");
          if (!j.ok) throw new Error(j.message || "aperçu");
          rendreApercu(j.apercu);
        })
        .catch(function (e) {
          if (e && e.name === "AbortError") return;   /* remplacé par une saisie plus récente */
          zone.classList.remove("occupe");
          zone.innerHTML = '<p class="note">Aperçu indisponible pour le moment. '
            + "Le calcul complet, lui, reste accessible par « Calculer l'étude ».</p>";
        });
    }, immediat ? 0 : 280);
  }

  function rendreApercu(a) {
    var zone = $("#dc-apercu");
    if (!zone || !a) return;
    var h = "";
    if (a.entete) h += '<p class="dc-ap-tete">' + esc(a.entete) + "</p>";
    h += releveDefauts(a.defauts);
    h += '<div class="dc-ap-b"><h3>Où se situe votre taux de charge</h3>'
      + '<p class="dc-sous">Le PUE ne dépend pas seulement de la technologie : sous un '
      + "certain taux de charge, les auxiliaires ne suivent plus proportionnellement. "
      + "La courbe est calculée par le moteur, point par point.</p>"
      + courbeCharge(a.courbe_charge) + "</div>";
    h += '<div class="dc-ap-b"><h3>Ce que chaque champ vide laisse encore ouvert</h3>'
      + '<p class="dc-sous">Pour chaque champ non renseigné, l\'étude est rejouée sur '
      + "tout le domaine de ce champ. La barre mesure ce qui reste indéterminé — "
      + "renseigner le champ la fait disparaître.</p>"
      + tornade(a.sensibilite) + "</div>";
    zone.innerHTML = h;
  }

  /* Les noms de famille sont longs ; à gauche d'un graphique, ils poussent les
     barres hors du cadre. On coupe au premier segment parlant plutôt que
     d'imposer une police minuscule. */
  function abrege(n) {
    n = String(n || "");
    if (n.length <= 30) return n;
    var c = n.indexOf(" (");
    if (c > 6 && c <= 32) return n.slice(0, c);
    return n.slice(0, 29) + "…";
  }

  /* L'inversion : quelles familles changent de rang entre l'eau du site et
     l'eau de la source. C'est la thèse de la page ; la laisser deviner dans un
     tableau de huit colonnes revenait à ne pas la démontrer. */
  function inversions(lignes) {
    var parSite = lignes.slice().sort(function (a, b) { return a.wue_site - b.wue_site; });
    var parSrc = lignes.slice().sort(function (a, b) { return a.wue_source - b.wue_source; });
    var out = [];
    parSite.forEach(function (l, i) {
      var j = parSrc.findIndex(function (x) { return x.famille === l.famille; });
      if (j !== i) out.push({ nom: l.nom, site: i + 1, source: j + 1 });
    });
    return out;
  }

  function graphiques(d) {
    var L = d.lignes || [];
    if (!L.length) return "";
    var inv = inversions(L);
    var meilleurSite = L.slice().sort(function (a, b) { return a.wue_site - b.wue_site; })[0];
    var meilleurSrc = L.slice().sort(function (a, b) { return a.wue_source - b.wue_source; })[0];

    var h = '<section class="dc-bloc"><h3>Le compromis eau, ramené au kilowattheure informatique</h3>'
      + '<p class="dc-sous">Les volumes annuels ne se comparent pas d’une famille à '
      + 'l’autre : ils dépendent de la consommation, qui dépend elle-même du PUE. '
      + 'Rapportées au kilowattheure informatique, les deux eaux se comparent '
      + 'directement — et l’écart entre elles est ce qui décide.</p>'
      + barres(L, [
          { nom: "Eau du site (WUE site)", c: COUL.site, val: function (l) { return l.wue_site; } },
          { nom: "Eau de la source (WUE source)", c: COUL.source, val: function (l) { return l.wue_source; } },
        ], { unite: "L/kWh_IT", alt: "Eau du site et eau de la source, par famille de "
             + "refroidissement, en litres par kilowattheure informatique",
             legende: "◄ famille retenue" });

    /* Quand la même famille gagne les deux lectures, le dire une fois. Répéter
       « au bilan de site X, au bilan complet X » se lit comme un bégaiement et
       fait manquer l'information réelle, qui est justement l'accord des deux. */
    h += '<div class="dc-lecture"><b>Ce que le graphique montre.</b> ';
    if (meilleurSite.famille === meilleurSrc.famille) {
      h += 'La famille la moins consommatrice est <b>' + esc(abrege(meilleurSite.nom))
        + '</b> dans LES DEUX lectures — ' + fr(meilleurSite.wue_site)
        + ' L/kWh_IT sur le site, ' + fr(meilleurSrc.wue_source)
        + ' au bilan complet. Le classement de tête ne bouge donc pas ; '
        + 'ce qui bouge est en dessous. ';
    } else {
      h += 'Au bilan de SITE, la famille la moins consommatrice est <b>'
        + esc(abrege(meilleurSite.nom)) + '</b> (' + fr(meilleurSite.wue_site)
        + ' L/kWh_IT). Au bilan COMPLET, c’est <b>' + esc(abrege(meilleurSrc.nom))
        + '</b> (' + fr(meilleurSrc.wue_source) + ' L/kWh_IT). ';
    }
    if (inv.length) {
      h += '<b>' + inv.length + ' famille' + (inv.length > 1 ? "s changent" : " change")
        + ' de rang</b> entre les deux lectures : '
        + inv.slice(0, 4).map(function (x) {
            return esc(abrege(x.nom)) + " (" + x.site + "ᵉ → " + x.source + "ᵉ)";
          }).join(" · ")
        + '. Un dossier qui n’aurait regardé que le WUE de site aurait classé '
        + 'ces familles à l’envers.';
    } else {
      h += 'Aucune famille ne change de rang entre les deux lectures : sur ce mix, '
        + 'l’arbitrage de site et l’arbitrage complet concordent. Ce n’est pas '
        + 'toujours le cas — l’écart se creuse à mesure que le mix se charge en '
        + 'production thermique.';
    }
    h += "</div></section>";

    /* Carbone : exploitation contre incorporé. La page l'affirme, le graphique
       le montre — et sur un mix décarboné le second l'emporte. */
    var incMax = 0;
    L.forEach(function (l) {
      var inc = (l.empreinte_totale_t || 0) - (l.co2_exploitation_t || 0);
      if (l.empreinte_totale_t) incMax = Math.max(incMax, 100 * inc / l.empreinte_totale_t);
    });
    h += '<section class="dc-bloc"><h3>Carbone : ce que l’exploitation pèse, et ce que la construction pèse</h3>'
      + '<p class="dc-sous">L’incorporé — fabrication des serveurs, gros œuvre, '
      + 'équipements techniques — est amorti sur la durée de vie. Sur un mix décarboné '
      + 'il devient majoritaire, et optimiser l’exploitation revient alors à travailler '
      + 'sur la plus petite des deux parts.</p>'
      + barres(L, [
          { nom: "Exploitation (électricité consommée)", c: COUL.expl,
            val: function (l) { return l.co2_exploitation_t; } },
          { nom: "Incorporé, amorti (fabrication et construction)", c: COUL.inc,
            val: function (l) { return Math.max(0, (l.empreinte_totale_t || 0)
                                  - (l.co2_exploitation_t || 0)); } },
        ], { empile: true, unite: "tCO2e/an", suffixe: "t",
             alt: "Empreinte annuelle par famille, part d’exploitation et part incorporée",
             legende: "total en tCO2e/an" })
      + '<div class="dc-lecture"><b>Ce que le graphique montre.</b> La part incorporée '
      + 'atteint <b>' + fr(Math.round(incMax)) + ' %</b> du total sur la famille où elle '
      + 'pèse le plus. Ces facteurs sont des ordres de grandeur sectoriels à ±50 % : dès '
      + 'que les équipements sont choisis, leurs déclarations environnementales produit '
      + 'doivent les remplacer, et l’écart peut atteindre un facteur deux.</div></section>';
    return h;
  }

  function afficherComparaison(d) {
    /* Les graphiques d'abord, le tableau ensuite : on montre le compromis,
       puis on donne les chiffres à recopier. L'inverse obligeait à lire huit
       colonnes avant de comprendre ce qu'on cherchait. */
    var h = '<p class="dc-sous">' + esc(d.lecture || "") + "</p>" + graphiques(d)
      + '<div class="dc-tab-wrap"><table class="dc-tab"><thead><tr>'
      + "<th>Famille</th><th>PUE</th><th>MWh/an</th><th>Eau site m³/an</th>"
      + "<th>WUE site</th><th>WUE source</th><th>Empreinte tCO2e/an</th>"
      + "<th>Rejet °C</th></tr></thead><tbody>";
    (d.lignes || []).forEach(function (l) {
      var courante = l.famille === (PROFIL.refroidissement || "");
      h += '<tr' + (courante ? ' class="dc-courante"' : "") + ">"
        + "<th scope='row'>" + esc(l.nom) + (courante ? " <em>(retenue)</em>" : "") + "</th>"
        + "<td>" + fr(l.pue) + "</td><td>" + fr(l.energie_totale_MWh) + "</td>"
        + "<td>" + fr(l.eau_site_m3) + "</td><td>" + fr(l.wue_site) + "</td>"
        + "<td>" + fr(l.wue_source) + "</td><td>" + fr(l.empreinte_totale_t) + "</td>"
        + "<td>" + fr(l.temperature_rejet_c) + "</td></tr>";
    });
    h += "</tbody></table></div>";
    (d.lignes || []).forEach(function (l) {
      h += '<details class="dc-det"><summary>' + esc(l.nom) + "</summary>"
        + '<div class="dc-det-c">' + esc(l.note) + "</div></details>";
    });
    $("#dc-comparaison").innerHTML = h;
    $("#dc-sec-comp").hidden = false;
    majSuites();
  }

  function poster(url, corps, delai) {
    return demander(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps)
    }, delai || DELAI_LONG).then(function (r) {
      return r.json().then(function (j) { return { ok: r.ok, statut: r.status, j: j }; });
    });
  }

  /* Le délai dépassé n'est pas une panne : le serveur n'a simplement pas
     répondu dans le temps accordé. Le dire ainsi, avec la durée, évite de
     chercher une erreur de saisie là où il n'y a qu'une attente. */
  function messageDelai(e, defaut) {
    if (e && e.name === "DelaiDepasse") {
      return "Le serveur n'a pas répondu en " + Math.round(e.delai / 1000)
        + " secondes. Il est peut-être très sollicité : relancez dans un "
        + "instant. Vos saisies sont conservées.";
    }
    return defaut;
  }

  /* Le 401 ne s'y voit plus : demander() l'intercepte désormais avant que
     poster() ne résolve, donc res.statut ne le porte plus jamais — la
     bannière de session éteinte l'a déjà dit. */
  function messageErreur(res) {
    if (res.statut === 503) return (res.j && res.j.message) || "Service momentanément indisponible.";
    return (res.j && res.j.message) || "Le calcul a échoué.";
  }

  function lancer() {
    PROFIL = lireProfil();
    etat("Calcul en cours…");
    poster("/api/datacenter/etude", PROFIL).catch(function (e) {
      // Une promesse rejetée sans .catch laissait « Calcul en cours… » à
      // l'écran pour toujours : le bouton restait inerte et rien n'expliquait.
      etat(messageDelai(e, "Le calcul n'a pas abouti."), true);
      return null;
    }).then(function (res) {
      if (!res) return;
      if (!res.ok || !res.j.ok) { etat(messageErreur(res), true); return; }
      ETUDE = res.j.etude;
      /* Le profil est retenu pour la page d'ingénierie : elle pose le même
         formulaire, et c'est la ressaisie des treize champs qui décourage, pas
         le calcul. Enregistré APRÈS un calcul réussi seulement — un profil qui
         n'a rien produit ici n'a pas de raison d'être proposé ailleurs. */
      if (window.ProfilDC) window.ProfilDC.enregistrer(PROFIL, "datacenter");
      afficherResultats();
      montrerSuite();
      etat("Étude calculée. Chaque valeur porte sa méthode : dépliez « méthode et source ».");
      $("#dc-sec-res").scrollIntoView({ behavior: "smooth", block: "start" });
    }).catch(function (e) {
      // « Réseau indisponible » sur un délai dépassé désigne la mauvaise
      // cause : le réseau marche, le serveur est lent. On ne fait pas chercher
      // la panne du mauvais côté.
      etat(messageDelai(e, "Réseau indisponible. Réessayez."), true);
    });
  }

  /* La suite du chemin, proposée une fois le calcul fait et pas avant : ce que
     la page d'ingénierie apporte — à quelle phase ce chiffre devient recevable
     — n'a aucun sens tant qu'il n'y a pas de chiffre. */
  function montrerSuite() {
    var z = $("#dc-suite");
    if (!z || z.getAttribute("data-pose") === "1") return;
    z.setAttribute("data-pose", "1");
    z.hidden = false;
    z.innerHTML =
      '<div class="dc-suite-i">'
      + "<b>Ce calcul est juste. Il ne dit pas encore s’il est recevable.</b>"
      + "<span>Un PUE tiré d’une plage de conception convient à un "
      + "avant-projet ; le même chiffre reporté dans un CCTP devient une clause "
      + "de pénalité assise sur un ordre de grandeur. La page d’ingénierie "
      + "de projet dit à quelle phase chacune de ces valeurs devient opposable, "
      + "et ce qu’il faut avoir produit pour y arriver.</span></div>"
      + '<a class="dc-suite-b" id="dc-suite-go" href="/ingenierie-datacenter">'
      + "Placer ce calcul dans un projet →</a>"
      + '<p class="dc-suite-n">Votre profil y sera repris tel quel — vous '
      + "n’avez rien à ressaisir, et la page s’ouvrira directement sur la "
      + "première phase qui bloque. Il ne quitte pas ce navigateur et "
      + "disparaît à la fermeture de l’onglet.</p>"
      + '<p class="dc-suite-c" id="dc-suite-c" role="status" aria-live="polite"></p>';
    compteRebours();
  }

  /* ── Le passage automatique ────────────────────────────────────────────
     Le calcul fait, la suite du chemin s'ouvre d'elle-même. Trois précautions,
     et chacune répare un défaut que ce genre de bascule produit :

       · ELLE NE VOLE PAS LES RÉSULTATS. Le lecteur vient de demander un
         calcul ; l'emmener ailleurs avant qu'il l'ait vu répondrait à côté de
         sa question. Le délai lui laisse le temps de regarder, et la moindre
         interaction — molette, clic, touche — l'annule : quelqu'un qui commence
         à lire a déjà répondu.

       · ELLE S'ANNULE D'UN GESTE VISIBLE. Un compte à rebours sans bouton
         d'arrêt est un piège (WCAG 2.2.1) ; celui-ci en porte un, et il est
         annoncé aux lecteurs d'écran.

       · ELLE NE SE REJOUE PAS. Revenir en arrière depuis la page d'ingénierie
         relancerait la bascule et enfermerait le lecteur dans une boucle. Un
         seul passage par calcul. */
  var DELAI_SUITE = 12;

  function compteRebours() {
    var z = $("#dc-suite-c");
    if (!z || SUITE_FAITE) return;
    var reste = DELAI_SUITE, minuteur = null, fini = false;

    function arreter(pourquoi) {
      if (fini) return;
      fini = true;
      clearInterval(minuteur);
      ["wheel", "touchstart", "keydown", "pointerdown"].forEach(function (e) {
        window.removeEventListener(e, surInteraction, true);
      });
      z.innerHTML = pourquoi === "annule"
        ? "Passage automatique annulé. Le bouton ci-dessus y conduit quand vous "
          + "le voudrez ; votre profil reste prêt."
        : "";
    }
    function surInteraction() { arreter("annule"); }

    ["wheel", "touchstart", "keydown", "pointerdown"].forEach(function (e) {
      window.addEventListener(e, surInteraction, true);
    });
    z.innerHTML = "Passage à l’ingénierie de projet dans <b>" + reste
      + "</b> s — <button type=\"button\" id=\"dc-suite-x\">rester sur cette page</button>";
    var b = $("#dc-suite-x");
    if (b) b.addEventListener("click", function () { arreter("annule"); });
    minuteur = setInterval(function () {
      reste -= 1;
      if (fini) return;
      if (reste <= 0) {
        arreter("part");
        SUITE_FAITE = true;
        window.location.href = "/ingenierie-datacenter";
        return;
      }
      var n = z.querySelector("b");
      if (n) n.textContent = reste;
    }, 1000);
  }

  function comparer() {
    PROFIL = lireProfil();
    etat("Comparaison des familles…");
    poster("/api/datacenter/comparer", PROFIL).catch(function (e) {
      etat(messageDelai(e, "La comparaison n'a pas abouti."), true);
      return null;
    }).then(function (res) {
      if (!res) return;
      if (!res.ok || !res.j.ok) { etat(messageErreur(res), true); return; }
      afficherComparaison(res.j);
      etat("Comparaison établie.");
      $("#dc-sec-comp").scrollIntoView({ behavior: "smooth", block: "start" });
    }).catch(function (e) {
      // « Réseau indisponible » sur un délai dépassé désigne la mauvaise
      // cause : le réseau marche, le serveur est lent. On ne fait pas chercher
      // la panne du mauvais côté.
      etat(messageDelai(e, "Réseau indisponible. Réessayez."), true);
    });
  }

  function exporter(fmt) {
    PROFIL = lireProfil();
    etat("Préparation du document…");
    demander("/api/datacenter/export", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(TR(Object.assign({}, PROFIL, { format: fmt })))
    }, DELAI_LONG).then(function (r) {
      /* Le serveur répond soit un fichier, soit du JSON d'erreur. Traiter la
         réponse comme un fichier dans tous les cas téléchargerait un document
         de zéro octet, et l'utilisateur croirait à un export réussi. */
      var ct = r.headers.get("Content-Type") || "";
      if (!r.ok || ct.indexOf("json") >= 0) {
        return r.json().then(function (j) {
          etat((j && j.message) || "L'export a échoué.", true);
        });
      }
      return r.blob().then(function (b) {
        var u = URL.createObjectURL(b), a = document.createElement("a");
        a.href = u; a.download = "note-calcul-datacenter." + fmt;
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
        etat("Document téléchargé.");
      });
    }).catch(function (e) {
      // « Réseau indisponible » sur un délai dépassé désigne la mauvaise
      // cause : le réseau marche, le serveur est lent. On ne fait pas chercher
      // la panne du mauvais côté.
      etat(messageDelai(e, "Réseau indisponible. Réessayez."), true);
    });
  }

  /* ── Le référentiel, publié ────────────────────────────────────────────
     Il vit dans le moteur et n'était affiché nulle part. Or c'est lui qui dit
     que les facteurs eau sont des ordres de grandeur à ±40 %, et qu'il faut
     les remplacer par la valeur du fournisseur. Une page qui calcule sans
     montrer d'où viennent ses constantes demande qu'on la croie.

     Tout est rendu depuis `/api/datacenter/referentiel` : recopier ces
     libellés dans la page les aurait figés au jour de l'écriture. */
  /* Ce que la base de connaissance couvre, COMPTÉ par le serveur.
     La page annonçait « seize thèmes » — vrai le jour où la phrase a été
     écrite, faux depuis que la famille en porte davantage. Un lecteur
     cherchant une analyse de risques en concluait qu'elle n'était pas
     couverte. Un compte figé finit toujours par mentir ; celui-ci est
     demandé. */
  function afficherBase() {
    var el = $("#dc-base");
    if (!el || !REF || !REF.base) return;
    var b = REF.base;
    el.innerHTML = "La famille <b>" + esc(b.famille) + "</b> compte <b>"
      + b.themes + "</b> thèmes — " + b.techniques
      + " techniques, du refroidissement liquide aux appels d'offres, et "
      + b.management + " de management (politique environnementale, analyse de "
      + "risques, incendie, plans de sécurité). Un document mal classé se "
      + "retrouve difficilement&nbsp;: le thème compte autant que le fichier.";
  }

  /* LES LIMITES, CHACUNE AVEC SA RÉPONSE. La liste statique de la page
     disait « le moteur ne connaît pas votre intensité carbone » alors que le
     champ existait dans le formulaire : une limite écrite en dur avait déjà
     menti. Tout vient du serveur, y compris le NOM du champ qui lève la
     limite — vérifié côté module contre le profil réel. */

  /* L'ÉVALUATEUR DE CHIFFRE ANNONCÉ, posé SUR la carte de la limite.
     La simulation TMY et le profil horaire restent hors du moteur — mais le
     geste qui les PRÉCÈDE, juger si le chiffre déjà sur la table est
     recevable, se calcule avec les plages de l'étude elle-même. C'est ce que
     fait le BE fluides devant une plaquette, l'énergéticien devant un
     contrat : situer le chiffre avant de payer l'étude qui le raffinera. */
  function evaluateurLimite(cle) {
    if (cle === "pue_climat") {
      return '<div class="dc-ev" data-ev="pue">'
        + '<span class="dc-lim-t">En attendant la simulation — juger un PUE annoncé</span>'
        + '<div class="dc-ev-l">'
        + '<input type="text" inputmode="decimal" data-ev-pue'
        + ' aria-label="PUE annoncé" placeholder="PUE annoncé — ex. 1,25">'
        + '<button type="button" class="dc-ev-go" data-ev-go>Situer ce chiffre</button>'
        + "</div>"
        + '<div class="dc-ev-r" data-ev-r aria-live="polite"></div>'
        + "</div>";
    }
    if (cle === "carbone_horaire") {
      return '<div class="dc-ev" data-ev="intensite">'
        + '<span class="dc-lim-t">En attendant le profil horaire — juger un facteur annoncé</span>'
        + '<div class="dc-ev-l">'
        + '<input type="text" inputmode="decimal" data-ev-facteur'
        + ' aria-label="Facteur annoncé en grammes par kilowattheure"'
        + ' placeholder="facteur annoncé, g/kWh — ex. 35">'
        + '<input type="text" inputmode="decimal" data-ev-basses'
        + ' aria-label="Facteur des heures basses, facultatif"'
        + ' placeholder="heures basses, g/kWh (facultatif)">'
        + '<button type="button" class="dc-ev-go" data-ev-go>Situer ce chiffre</button>'
        + "</div>"
        + '<div class="dc-ev-r" data-ev-r aria-live="polite"></div>'
        + "</div>";
    }
    if (cle === "eau_pointe") {
      return '<div class="dc-ev" data-ev="eau">'
        + '<span class="dc-lim-t">En attendant le profil mensuel — juger un volume annoncé</span>'
        + '<div class="dc-ev-l">'
        + '<input type="text" inputmode="decimal" data-ev-vol'
        + ' aria-label="Volume annuel annoncé en mètres cubes par an"'
        + ' placeholder="volume annuel annoncé, m³/an">'
        + '<input type="text" inputmode="decimal" data-ev-pointe'
        + ' aria-label="Jour de pointe annoncé, facultatif"'
        + ' placeholder="jour de pointe, m³/j (facultatif)">'
        + '<button type="button" class="dc-ev-go" data-ev-go>Situer ce chiffre</button>'
        + "</div>"
        + '<div class="dc-ev-r" data-ev-r aria-live="polite"></div>'
        + "</div>";
    }
    if (cle === "carbone_incorpore") {
      /* Les postes viennent du référentiel SERVI — la liste recopiée aurait
         divergé le jour où le moteur en aurait porté un quatrième. */
      var postes = Object.keys((REF && REF.referentiel && REF.referentiel.incorpore) || {});
      var NOMS_POSTES = {
        serveur_kgCO2e: "Serveur — kgCO2e par unité",
        batiment_kgCO2e_par_kW_IT: "Bâtiment — kgCO2e par kW IT",
        technique_kgCO2e_par_kW_IT: "Équip. techniques — kgCO2e par kW IT"
      };
      return '<div class="dc-ev" data-ev="incorpore">'
        + '<span class="dc-lim-t">En attendant les déclarations — juger un chiffre fournisseur</span>'
        + '<div class="dc-ev-l">'
        + '<select data-ev-poste aria-label="Poste du référentiel">'
        + postes.map(function (k) {
            return '<option value="' + esc(k) + '">'
              + esc(NOMS_POSTES[k] || k) + "</option>";
          }).join("")
        + "</select>"
        + '<input type="text" inputmode="decimal" data-ev-val'
        + ' aria-label="Valeur annoncée en kilogrammes de CO2 équivalent"'
        + ' placeholder="valeur annoncée, kgCO2e">'
        + '<input type="text" inputmode="decimal" data-ev-dv'
        + ' aria-label="Durée de vie annoncée en années, facultatif"'
        + ' placeholder="durée de vie, ans (facultatif)">'
        + '<button type="button" class="dc-ev-go" data-ev-go>Situer ce chiffre</button>'
        + "</div>"
        + '<div class="dc-ev-r" data-ev-r aria-live="polite"></div>'
        + "</div>";
    }
    return "";
  }

  /* Le verdict, rendu depuis la réponse du serveur — jamais recalculé ici.
     Un refus (PUE < 1, facteur négatif) N'EST PAS une panne : c'est le
     verdict le plus utile de la série, et il s'affiche comme tel. */
  function rendreVerdict(zone, ev, contexte) {
    if (!ev || !ev.verdict && !ev.motif) {
      zone.innerHTML = '<p class="dc-ev-v refus">Réponse illisible du serveur.</p>';
      return;
    }
    if (ev.ok === false) {
      zone.innerHTML = '<div class="dc-ev-v refus"><b>Chiffre refusé — et '
        + "c’est la réponse.</b> " + esc(ev.motif) + "</div>";
      return;
    }
    var TONS = {
      coherent: "ok", coherent_location: "ok",
      coherent_etude: "ok", coherent_secteur: "ok",
      plausible_pleine_charge: "attention", market_based_probable: "attention",
      sous_plage: "attention", au_dessus: "attention",
      sous_borne_physique: "attention", au_dessus_etude: "attention",
      sous_plage_sectorielle: "attention", au_dessus_secteur: "attention"
    };
    var NOMS = {
      coherent: "Cohérent à ce taux de charge",
      coherent_location: "Cohérent avec le réseau (location-based)",
      plausible_pleine_charge: "Plausible à pleine charge — pas à la vôtre",
      market_based_probable: "Facteur contractuel probable (market-based)",
      sous_plage: "Sous la plage de la famille — suspect",
      au_dessus: "Au-dessus de la plage attendue",
      sous_borne_physique: "Sous le plancher physique — suspect",
      coherent_etude: "Cohérent avec le calcul de l’étude",
      au_dessus_etude: "Au-dessus du calcul de l’étude",
      sous_plage_sectorielle: "Sous l’ordre sectoriel — déclaration exigée",
      coherent_secteur: "Dans l’ordre de grandeur sectoriel",
      au_dessus_secteur: "Au-dessus de l’ordre sectoriel"
    };
    /* Une pointe arithmétiquement impossible ne laisse pas la carte au teal
       d'un annuel cohérent : l'irrecevable prime sur le recevable. */
    var ton = TONS[ev.verdict] || "attention";
    if (ev.pointe && ev.pointe.recevable === false) ton = "attention";
    var h = '<div class="dc-ev-v ' + ton + '">'
      + '<span class="dc-ev-b">' + esc(NOMS[ev.verdict] || ev.verdict) + "</span>"
      + "<p>" + esc(ev.lecture) + "</p>"
      + (contexte ? '<p class="dc-ev-ctx">' + contexte + "</p>" : "");
    if (ev.pilotage) {
      h += '<p class="dc-ev-pil"><b>Pilotage horaire, borné&nbsp;:</b> '
        + esc(ev.pilotage.lecture)
        + (ev.pilotage.tonnes_an_max !== undefined
            ? " Soit au plus <b>" + fr(ev.pilotage.tonnes_an_max)
              + " tCO2e/an</b> (" + esc(ev.pilotage.hypotheses) + ")."
            : "") + "</p>";
    }
    if (ev.pointe) {
      h += '<p class="dc-ev-pil"><b>Pointe journalière'
        + (ev.pointe.recevable === false ? " — irrecevable" : "")
        + "&nbsp;:</b> " + esc(ev.pointe.lecture) + "</p>";
    }
    if (ev.amorti) {
      h += '<p class="dc-ev-pil"><b>Amortissement&nbsp;:</b> '
        + esc(ev.amorti.lecture) + "</p>";
    }
    if (ev.exigences && ev.exigences.length) {
      h += '<details class="dc-ev-ex"><summary>À exiger '
        + esc(ev.exige_de || "du bureau d’études")
        + " (" + ev.exigences.length + ")</summary><ul>"
        + ev.exigences.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("")
        + "</ul></details>";
    }
    zone.innerHTML = h + "</div>";
  }

  function brancherEvaluateurs(el) {
    /* PUE : la famille et le taux de charge ne sont PAS redemandés — ils sont
       lus du formulaire de l'étape 2, et le verdict DIT lesquels il a
       employés. Deux jeux de valeurs pour un même chiffre, c'est le début
       des dossiers qui se contredisent. */
    var evp = el.querySelector('[data-ev="pue"]');
    if (evp) {
      evp.querySelector("[data-ev-go]").addEventListener("click", function () {
        var zone = evp.querySelector("[data-ev-r]");
        var brut = (evp.querySelector("[data-ev-pue]").value || "").trim();
        if (!brut) {
          zone.innerHTML = '<p class="dc-ev-v attention">Un chiffre d’abord '
            + ": le PUE annoncé par la fiche, l’offre ou le contrat.</p>";
          return;
        }
        var sel = document.querySelector('#dc-form [data-champ="refroidissement"]');
        var fam = sel && sel.value ? sel.value : null;
        var tc = document.querySelector('#dc-form [data-champ="taux_charge"]');
        var taux = tc && (tc.value || "").trim() ? tc.value.trim().replace(",", ".") : null;
        zone.textContent = "Jugement en cours…";
        poster("/api/datacenter/evaluer", {
          type: "pue", pue: brut.replace(",", "."),
          refroidissement: fam, taux_charge: taux
        }).then(function (r) {
          var ev = (r.j && r.j.evaluation) || null;
          var ctx = ev && ev.ok !== false
            ? "Jugé pour «&nbsp;" + esc(ev.famille) + "&nbsp;» à "
              + fr(ev.taux_charge * 100) + "&nbsp;% de charge — "
              + (fam ? "famille lue du formulaire de l’étape 2"
                     : "famille par défaut du moteur, précisez-la à l’étape 2")
              + (taux ? ", taux lu du formulaire." : ", taux par défaut.")
            : "";
          rendreVerdict(zone, ev, ctx);
        }).catch(function (e) {
          zone.innerHTML = '<p class="dc-ev-v refus">' + esc(e.message) + "</p>";
        });
      });
    }
    /* Intensité : le pays vient du formulaire, la moyenne de comparaison de
       la réponse — le même référentiel que l'étude, et le verdict le dit. */
    var evi = el.querySelector('[data-ev="intensite"]');
    if (evi) {
      evi.querySelector("[data-ev-go]").addEventListener("click", function () {
        var zone = evi.querySelector("[data-ev-r]");
        var brut = (evi.querySelector("[data-ev-facteur]").value || "").trim();
        if (!brut) {
          zone.innerHTML = '<p class="dc-ev-v attention">Un chiffre d’abord '
            + ": le facteur annoncé par le fournisseur ou le contrat, en g/kWh.</p>";
          return;
        }
        var basses = (evi.querySelector("[data-ev-basses]").value || "").trim();
        var selP = document.querySelector('#dc-form [data-champ="pays"]');
        var pays = selP && selP.value ? selP.value : null;
        zone.textContent = "Jugement en cours…";
        poster("/api/datacenter/evaluer", {
          type: "intensite", facteur_g: brut.replace(",", "."),
          pays: pays, heures_basses_g: basses ? basses.replace(",", ".") : null
        }).then(function (r) {
          var ev = (r.j && r.j.evaluation) || null;
          var ctx = ev && ev.ok !== false
            ? "Comparé au réseau " + esc(ev.pays) + " (moyenne location-based "
              + fr(ev.moyenne_location_g) + "&nbsp;g/kWh, celle de l’étude) — "
              + (pays ? "pays lu du formulaire de l’étape 2."
                      : "pays par défaut (France), précisez-le à l’étape 2.")
            : "";
          rendreVerdict(zone, ev, ctx);
        }).catch(function (e) {
          zone.innerHTML = '<p class="dc-ev-v refus">' + esc(e.message) + "</p>";
        });
      });
    }
    /* Eau : la référence est RECALCULÉE par le moteur pour le profil du
       formulaire — puissance comprise. Sans puissance, le serveur REFUSE de
       comparer à un site imaginaire, et ce refus s'affiche tel quel : c'est
       lui qui renvoie à l'étape 2. */
    var eve = el.querySelector('[data-ev="eau"]');
    if (eve) {
      eve.querySelector("[data-ev-go]").addEventListener("click", function () {
        var zone = eve.querySelector("[data-ev-r]");
        var brut = (eve.querySelector("[data-ev-vol]").value || "").trim();
        if (!brut) {
          zone.innerHTML = '<p class="dc-ev-v attention">Un chiffre d’abord '
            + ": le volume annuel annoncé par le dossier ou l’offre, en m³/an.</p>";
          return;
        }
        var pointe = (eve.querySelector("[data-ev-pointe]").value || "").trim();
        var profil = lireProfil();
        zone.textContent = "Jugement en cours…";
        poster("/api/datacenter/evaluer", {
          type: "eau", profil: profil,
          volume_annuel_m3: brut.replace(",", "."),
          pointe_jour_m3: pointe ? pointe.replace(",", ".") : null
        }).then(function (r) {
          var ev = (r.j && r.j.evaluation) || null;
          var ctx = ev && ev.ok !== false
            ? "Référence recalculée pour «&nbsp;" + esc(ev.famille) + "&nbsp;» : appoint "
              + fr(ev.reference.appoint_m3) + "&nbsp;m³/an, évaporation "
              + fr(ev.reference.evaporation_m3) + "&nbsp;m³/an (part évaporative "
              + fr(ev.reference.part_evaporative) + ") — profil lu du formulaire "
              + "de l’étape 2."
            : "";
          rendreVerdict(zone, ev, ctx);
        }).catch(function (e) {
          zone.innerHTML = '<p class="dc-ev-v refus">' + esc(e.message) + "</p>";
        });
      });
    }
    /* Incorporé : le poste vient du référentiel servi, la comparaison des
       ordres de grandeur du serveur — l'interface ne connaît aucun chiffre. */
    var evc = el.querySelector('[data-ev="incorpore"]');
    if (evc) {
      evc.querySelector("[data-ev-go]").addEventListener("click", function () {
        var zone = evc.querySelector("[data-ev-r]");
        var brut = (evc.querySelector("[data-ev-val]").value || "").trim();
        if (!brut) {
          zone.innerHTML = '<p class="dc-ev-v attention">Un chiffre d’abord '
            + ": la valeur annoncée par le fournisseur, en kgCO2e pour le "
            + "poste choisi.</p>";
          return;
        }
        var dv = (evc.querySelector("[data-ev-dv]").value || "").trim();
        var poste = evc.querySelector("[data-ev-poste]").value;
        zone.textContent = "Jugement en cours…";
        poster("/api/datacenter/evaluer", {
          type: "incorpore", poste: poste,
          valeur_kg: brut.replace(",", "."),
          duree_vie_ans: dv ? dv.replace(",", ".") : null
        }).then(function (r) {
          var ev = (r.j && r.j.evaluation) || null;
          var ctx = ev && ev.ok !== false
            ? "Comparé à l’ordre de grandeur du référentiel : "
              + fr(ev.reference.valeur_kg) + "&nbsp;kgCO2e sur "
              + fr(ev.reference.duree_vie_ans) + "&nbsp;ans (±"
              + fr(ev.reference.incertitude_pct) + "&nbsp;%) — le même que l’étude."
            : "";
          rendreVerdict(zone, ev, ctx);
        }).catch(function (e) {
          zone.innerHTML = '<p class="dc-ev-v refus">' + esc(e.message) + "</p>";
        });
      });
    }
  }

  function afficherLimites() {
    var el = $("#dc-limites");
    var lims = (REF && REF.referentiel && REF.referentiel.limites) || [];
    if (!el || !lims.length) return;
    el.innerHTML = '<div class="dc-lim">' + lims.map(function (x) {
      var h = '<article class="dc-lim-c' + (x.leve_par ? " levable" : "") + '">'
        + "<h4>" + esc(x.quoi) + "</h4>";
      if (x.leve_par) {
        h += '<span class="dc-lim-lv">✓ se lève ici — champ « '
          + esc(x.leve_par) + " »</span>";
      }
      h += '<p><span class="dc-lim-t">Ce que le moteur fait déjà</span>'
        + esc(x.moteur_fait) + "</p>"
        + '<p><span class="dc-lim-t">' + (x.leve_par ? "Comment la lever ici"
            : "Pourquoi elle ne se lève pas ici") + "</span>"
        + esc(x.leve_note) + "</p>"
        + '<p><span class="dc-lim-t">La marche professionnelle</span>'
        + esc(x.calcul) + "</p>"
        + '<p><span class="dc-lim-t">Normes et références</span>'
        + x.normes.map(function (n) {
            return '<span class="dc-lim-n">' + esc(n) + "</span>";
          }).join("") + "</p>"
        + '<p class="dc-lim-q"><b>' + esc(x.qui) + "</b> — " + esc(x.quand) + "</p>"
        + evaluateurLimite(x.cle)
        + "</article>";
      return h;
    }).join("") + "</div>";
    brancherEvaluateurs(el);
  }

  function afficherReferentiel() {
    var el = $("#dc-referentiel");
    afficherBase();
    if (!el || !REF || !REF.referentiel) return;
    var R = REF.referentiel, h = "";

    function carteRef(nom, nature, quoi, valeurs, source, remplacer) {
      return '<div class="dc-ref-c"><span class="n">' + esc(nature) + "</span>"
        + "<h4>" + esc(nom) + "</h4>"
        + (quoi ? "<p>" + esc(quoi) + "</p>" : "")
        + (valeurs ? '<div class="v">' + valeurs + "</div>" : "")
        + (source ? "<p style='margin-top:7px'>" + esc(source) + "</p>" : "")
        + (remplacer ? '<span class="rmp">▸ ' + esc(remplacer) + "</span>" : "")
        + "</div>";
    }

    /* Eau de la production électrique : le facteur le plus incertain du lot,
       et celui qui décide de l'arbitrage. Il passe en premier. */
    if (R.ewif) {
      var pays = Object.keys(R.ewif).map(function (k) {
        return esc(k) + " " + fr(R.ewif[k].valeur);
      }).join(" · ");
      h += carteRef("Eau de la production électrique (EWIF)", "ordre de grandeur · ±40 %",
        "Eau CONSOMMÉE — évaporée, non restituée — pour produire un kilowattheure. "
        + "À ne pas confondre avec l’eau prélevée : l’écart atteint un facteur dix "
        + "sur un parc nucléaire en circuit ouvert.",
        pays + " L/kWh", R.ewif_source,
        "la valeur du fournisseur ou du gestionnaire de réseau, dès qu’elle existe");
    }
    if (R.intensite_reseau) {
      var ir = Object.keys(R.intensite_reseau).map(function (k) {
        return esc(k) + " " + fr(R.intensite_reseau[k]);
      }).join(" · ");
      /* Le millésime vient du serveur : l'évaluateur de cette page enseigne
         qu'un facteur sans année ne se défend pas — la règle s'applique
         d'abord aux moyennes du moteur lui-même. */
      h += carteRef("Intensité carbone du réseau",
        "moyenne annuelle" + (R.intensite_millesime
          ? " — millésime " + esc(R.intensite_millesime) : ""),
        "Grammes de CO2e par kilowattheure consommé. Une moyenne annuelle ne "
        + "convient PAS pour arbitrer un pilotage horaire de la charge.",
        ir + " g/kWh", R.intensite_source,
        "la donnée du gestionnaire de réseau de l’année de référence, ou le "
        + "facteur contractuel du fournisseur (GHG Protocol, Scope 2 market-based)");
    }
    if (R.incorpore) {
      var ic = Object.keys(R.incorpore).map(function (k) {
        var v = R.incorpore[k];
        return esc(k.replace(/_/g, " ")) + " : " + fr(v.valeur)
          + (v.duree_vie_ans ? " sur " + v.duree_vie_ans + " ans" : "");
      }).join("<br>");
      h += carteRef("Carbone incorporé", "ordre de grandeur sectoriel · ±50 %",
        "Fabrication et construction, amorties sur la durée de vie — sans quoi "
        + "la comparaison avec l’exploitation n’a aucun sens.",
        ic, R.incorpore_source,
        "les déclarations environnementales produit (FDES / EPD) des équipements "
        + "retenus : l’écart peut atteindre un facteur deux");
    }
    if (R.constantes) {
      var cst = Object.keys(R.constantes).map(function (k) {
        var v = R.constantes[k];
        return esc(v.unite ? k.replace(/_/g, " ") : k) + " : " + fr(v.valeur)
          + " " + esc(v.unite || "");
      }).join("<br>");
      h += carteRef("Constantes physiques", "physique — non négociable",
        "La chaleur latente de vaporisation de l’eau ne dépend d’aucune "
        + "technologie. Un fournisseur qui annonce moins d’eau évaporée par "
        + "kilowattheure thermique décrit un rejet partiellement sec, ou se trompe.",
        cst, (R.constantes[Object.keys(R.constantes)[0]] || {}).source, "");
    }
    if (R.classes_ashrae) {
      var as = Object.keys(R.classes_ashrae).map(function (k) {
        var v = R.classes_ashrae[k];
        return esc(k) + " : " + v.plage_c[0] + " à " + v.plage_c[1] + " °C";
      }).join(" · ");
      h += carteRef("Classes ASHRAE", "norme professionnelle",
        "Température d’air admise à l’entrée des équipements. Élargir la plage "
        + "est le levier le moins cher qui existe — il ne coûte aucun matériel — "
        + "mais il engage la garantie constructeur.",
        as, R.ashrae_source,
        "l’accord écrit du constructeur avant d’élargir la plage");
    }
    /* L'ANCRAGE MANAGEMENT : où vivent ces grandeurs une fois l'étude rendue.
       Le PUE calculé devient l'IPÉ d'un SMÉn ISO 50001 ; les arbitrages
       deviennent des réponses aux questions centrales de l'ISO 26000. */
    if (R.management) {
      var M = R.management;
      var vm = "";
      if (M.iso_50001) {
        vm += "<b>" + esc(M.iso_50001.titre) + "</b><br>"
          + esc(M.iso_50001.ipe_naturel) + "<br><i>"
          + esc(M.iso_50001.certifiable) + "</i>";
      }
      if (M.iso_26000) {
        vm += "<br><br><b>" + esc(M.iso_26000.titre) + "</b><br>"
          + (M.iso_26000.questions_centrales || []).length
          + " questions centrales : "
          + (M.iso_26000.questions_centrales || []).map(esc).join(" · ")
          + "<br><i>" + esc(M.iso_26000.certifiable) + "</i>";
      }
      if (M.ecoconception) {
        vm += "<br><br><b>" + esc(M.ecoconception.titre) + "</b><br>"
          + esc(M.ecoconception.apporte)
          + "<br><i>" + esc(M.ecoconception.certifiable) + "</i>";
      }
      h += carteRef("Management de l’énergie et RSE", "systèmes de management",
        "Une étude ne vit pas seule : le SMÉn ISO 50001 fait suivre en "
        + "exploitation ce que le calcul a promis, et l’ISO 26000 rattache "
        + "les arbitrages énergie-eau-carbone à la stratégie RSE — les deux "
        + "chapitres correspondants figurent dans les livrables exportés.",
        vm, M.source, "");
    }
    if (R.cadre_ue) {
      var C = R.cadre_ue, cu = "";
      if (C.eed_reporting) {
        cu += "<b>" + esc(C.eed_reporting.titre) + "</b><br>"
          + esc(C.eed_reporting.portee) + "<br>"
          + (C.eed_reporting.exige || []).length + " grandeurs à déclarer : "
          + (C.eed_reporting.exige || []).map(esc).join(" · ");
      }
      if (C.eed_audit_smen) {
        cu += "<br><br><b>" + esc(C.eed_audit_smen.titre) + "</b><br>"
          + (C.eed_audit_smen.exige || []).map(esc).join("<br>")
          + "<br><i>" + esc(C.eed_audit_smen.note) + "</i>";
      }
      if (C.cndcp && C.cndcp.cibles) {
        cu += "<br><br><b>" + esc(C.cndcp.titre) + "</b><br>"
          + Object.keys(C.cndcp.cibles).map(function (k) {
              return esc(k.replace(/_/g, " ")) + " : " + esc(String(C.cndcp.cibles[k]));
            }).join(" · ");
      }
      if (C.iso30134 && C.iso30134.parties) {
        cu += "<br><br><b>" + esc(C.iso30134.titre) + "</b><br>"
          + Object.keys(C.iso30134.parties).map(function (k) {
              return esc(k) + " " + esc(C.iso30134.parties[k]);
            }).join(" · ");
      }
      if (C.en50600) cu += "<br><br><b>" + esc(C.en50600.titre) + "</b><br>"
        + esc(C.en50600.note);
      /* REPLIÉ, ET L'INTITULÉ PORTE LE COMPTE. Cette carte s'étalait sur
         toute la largeur sous les six cartes : elle cassait le rythme des
         trois colonnes et allongeait la section — pour de la matière de
         référence qu'on CONSULTE. Le compte est DÉRIVÉ des cadres réellement
         présents : écrit « quatre cadres », il aurait menti au premier
         ajout. */
      var nCadres = [C.eed_reporting, C.eed_audit_smen, C.cndcp, C.iso30134,
                     C.en50600].filter(Boolean).length;
      h += '<details class="dc-ref-c dc-cadre" style="grid-column:1/-1">'
        + '<summary><span class="n">cadre réglementaire et normatif</span> '
        + "<b>Ce qui rend ces grandeurs opposables</b> "
        + '<span class="dc-art-n">' + nCadres + " cadre" + (nCadres > 1 ? "s" : "")
        + " : EED (art. 11 et 12), pacte, ISO 30134, EN 50600</span></summary>"
        + '<div class="v">' + cu + "</div>"
        + (C.eed_reporting && C.eed_reporting.note
            ? '<span class="rmp">▸ ' + esc(C.eed_reporting.note) + "</span>" : "")
        + "</details>";
    }
    /* LES SOURCES CONSULTABLES. Le référentiel citait ses sources en toutes
       lettres, mais aucune n'était cliquable : vérifier demandait de retaper
       un nom d'organisme dans un moteur de recherche. Le menu en propose dix,
       servies par le serveur avec leur LIEN OFFICIEL — la racine du site,
       jamais un lien profond qui pourrit — et « quoi vérifier » une fois sur
       place. CE MENU GARDE SA SÉLECTION, contrairement à celui des pistes :
       il MONTRE une fiche, il n'insère rien — c'est l'idiome du sélecteur de
       thème de l'état de l'art, et deux menus qui montrent doivent se
       comporter pareil. */
    var srcs = (REF.referentiel && REF.referentiel.sources_consultables)
      || REF.sources_consultables || [];
    var menu = "";
    if (srcs.length) {
      menu = '<label class="dc-asel" for="dc-src">'
        + '<span class="dc-asel-l">Consulter une source du référentiel</span>'
        + '<select id="dc-src" data-dc-src>'
        + '<option value="">— ' + srcs.length + " sources officielles, avec "
        + "leur lien —</option>"
        + srcs.map(function (x, i) {
            return '<option value="' + i + '">' + esc(x.organisme) + " — "
              + esc(x.nature) + "</option>";
          }).join("")
        + "</select>"
        + '<span class="dc-asel-a">Chaque fiche donne le lien du site officiel '
        + "et ce qu'il faut y vérifier. Les liens visent la racine du site — "
        + "un lien profond finit toujours par mourir.</span></label>"
        + '<div id="dc-src-fiche"></div>';
    }

    el.innerHTML = menu + '<div class="dc-ref">' + h + "</div>"
      + '<p class="rc-note">Référentiel <b>' + esc(REF.referentiel.version || REF.version || "")
      + '</b> — rendu depuis le moteur, pas recopié : ce que vous lisez ici est ce '
      + 'que le calcul emploie.</p>';

    var sel = el.querySelector("[data-dc-src]");
    if (sel) {
      sel.addEventListener("change", function () {
        var z = el.querySelector("#dc-src-fiche");
        if (sel.value === "") { z.innerHTML = ""; return; }
        var x = srcs[parseInt(sel.value, 10)];
        if (!x) { z.innerHTML = ""; return; }
        z.innerHTML = '<div class="dc-src-c">'
          + '<span class="n">' + esc(x.nature) + "</span>"
          + "<h4>" + esc(x.organisme) + "</h4>"
          + "<p>" + esc(x.porte) + "</p>"
          + '<p class="dc-src-v"><b>À vérifier sur place :</b> '
          + esc(x.verifier) + "</p>"
          /* `rel="noopener noreferrer"` sur tout lien externe en nouvel
             onglet : sans lui, la page cible reçoit `window.opener`. */
          + '<a class="dc-src-l" href="' + esc(x.lien) + '" target="_blank" '
          + 'rel="noopener noreferrer">Ouvrir le site officiel — '
          + esc(x.lien.replace("https://", "")) + " ↗</a></div>";
      });
    }
  }

  /* Le référentiel conditionne TOUT : sans lui, pas de formulaire, donc pas de
     saisie possible. C'est le seul appel dont l'échec laisse la page inerte —
     il doit donc échouer vite, se dire, et se reprendre d'un clic sans
     recharger la page. */
  function chargerReferentiel() {
    $("#dc-form").innerHTML = '<p class="note">Chargement du référentiel…</p>';
    demander("/api/datacenter/referentiel", { credentials: "same-origin" },
             DELAI_COURT)
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) throw new Error("ref");
        REF = j;
        /* L'ÉTAT DE L'ART, pour les profils de serveur. Ces chiffres viennent
           de livres blancs de fournisseurs et n'entrent dans AUCUN calcul : ils
           servent à proposer un nombre de serveurs, en disant d'où il vient.
           Leur absence ne doit rien casser — le champ redevient un nombre
           libre —, donc on n'attend pas cette réponse pour bâtir la page. */
        demander("/api/datacenter/etat-art", { credentials: "same-origin" },
                 DELAI_COURT)
          .then(function (r) { return r.json(); })
          .then(function (a) {
            if (!a || !a.ok || !a.etat) return;
            ART = a.etat;
            majSuggestionsContexte("#dc-form");
          })
          .catch(function () { /* le champ reste un nombre libre */ });
        bâtirFormulaire();
        /* Le référentiel arrive avec le formulaire : il n'attend pas qu'une
           étude soit lancée. Un lecteur doit pouvoir juger les constantes AVANT
           de décider s'il fait confiance au calcul. */
        afficherReferentiel();
        afficherLimites();
        etat("");
      })
      .catch(function (e) {
        var auth = e && e.name === "SessionEteinte";
        var lent = e && e.name === "DelaiDepasse";
        $("#dc-form").innerHTML = '<p class="note">'
          + (auth
              ? "Connectez-vous pour accéder à l'étude."
              : lent
                ? "Le serveur n'a pas répondu en " + Math.round(e.delai / 1000)
                  + " secondes. Il est peut-être en train de se réveiller ou "
                  + "très sollicité — la page ne reste pas bloquée pour autant."
                : "Référentiel indisponible pour le moment.")
          + "</p>"
          + (auth ? "" : '<button type="button" class="btn btn-s" id="dc-ref-retry" '
              + 'style="margin-top:10px">↻ Réessayer</button>');
        var b = $("#dc-ref-retry");
        // Sans ce bouton, la seule issue est de recharger la page — et rien ne
        // le dit. Un rechargement refait tout ; ici on refait le seul appel
        // qui a manqué.
        if (b) b.addEventListener("click", chargerReferentiel);
      });
  }

  function démarrer() {
    chargerReferentiel();

    var b;
    if ((b = $("#dc-lancer"))) b.addEventListener("click", lancer);
    if ((b = $("#dc-comparer"))) b.addEventListener("click", comparer);
    if ((b = $("#dc-docx"))) b.addEventListener("click", function () { exporter("docx"); });
    if ((b = $("#dc-pdf"))) b.addEventListener("click", function () { exporter("pdf"); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", démarrer);
  } else {
    démarrer();
  }
})();
