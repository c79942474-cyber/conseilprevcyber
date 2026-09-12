/* Ingénierie de projet — le calcul replacé dans la séquence.
   ─────────────────────────────────────────────────────────
   Comme datacenter.js, ce fichier ne calcule RIEN. L'aptitude d'une phase, la
   liste des manques et le verdict sont produits par ingenierie_dc.py. Recalculer
   ici un « il ne manque que deux champs » ferait exister deux jugements, et
   c'est celui de l'écran que le lecteur recopierait dans son planning.

   Le parti pris d'affichage : le premier point d'arrêt est LA seule information
   qui commande une action. Neuf phases affichées à plat se lisent comme neuf
   chantiers parallèles, ce qu'elles ne sont pas. */

/* ═══════════════════════════════════════════════════════════════════════
   RÉSEAU PARTAGÉ — hors des deux IIFE ci-dessous, et c'est voulu.

   DÉFAUT CORRIGÉ. Ce fichier porte DEUX IIFE indépendantes : le calcul
   principal (phases, dossier, rédaction) et, plus loin, le chiffrage des
   honoraires de maîtrise d'œuvre. demander() vivait DANS la première : la
   seconde n'y avait pas accès et repartait en fetch nu, donc sans délai et
   sans le traitement centralisé du 401 — trois requêtes qui pouvaient rester
   bloquées sur « chiffrage en cours… » indéfiniment. Ce bloc est donc sorti
   à la portée du fichier entier, que les deux IIFE partagent déjà (une
   fonction déclarée ici leur est visible à toutes les deux, exactement comme
   les variables globales d'un script classique) — sans dupliquer le
   mécanisme, et sans fusionner les deux modules pour si peu. */

/* ── AUCUNE REQUÊTE SANS DÉLAI ──────────────────────────────────────────
   Le même défaut que sur la page de calcul, et vingt-trois fois : un `fetch`
   sans délai attend INDÉFINIMENT. Serveur saturé, en train de se réveiller,
   coupure réseau — la page reste sur « Chargement… » sans un mot, parfois
   plusieurs minutes, jusqu'à ce que le navigateur abandonne seul.

   Borner ne répare pas la lenteur : cela la rend LISIBLE, et rend la main.
   Trois budgets, parce que trois natures de travail : afficher, calculer,
   rédiger. Le dernier tient compte du budget du modèle côté serveur — le
   dépasser côté navigateur ferait perdre un document déjà écrit.

   `_LENT` distingue le délai dépassé d'une vraie coupure : le geste n'est pas
   le même, et les confondre envoie chercher la panne du mauvais côté. */
var DELAI_COURT = 12000;     // référentiels, états, aperçus
var DELAI_MOYEN = 45000;     // dossiers, plans, exports
var DELAI_LONG = 130000;     // rédaction : au-delà du budget serveur (120 s)

/* ═════════════════════════════════════════════════════════════════════
   LA SESSION QUI S'ÉTEINT EN COURS DE VISITE

   Toutes les commandes de cette page passent par des API réservées. Quand
   la session expire, chacune se met à répondre 401 — et chaque zone
   l'habillait de son message générique : « le parcours n'a pas pu être
   établi », « dossier indisponible », pendant que la frise soutenait qu'il
   manquait la puissance QUE LE LECTEUR VENAIT DE SAISIR. À partir de la
   section 4, plus rien ne s'affichait, et rien ne disait ni pourquoi ni
   quoi faire — « réessayez dans un instant » était même un conseil faux,
   se reconnecter étant le seul remède.

   Le 401 est donc reconnu à l'endroit UNIQUE par où passent toutes les
   requêtes, et il déclenche une bannière qui nomme la cause et offre la
   reconnexion — laquelle ramène ici même. */
var SESSION_MORTE = false;

function sessionTexte() {
  return "<b>Votre session n’est plus active.</b> C’est pour cela que plus "
    + "rien ne se calcule ni ne s’affiche au-delà du formulaire. "
    + '<a class="btn btn-s" href="/connexion?next=/ingenierie-datacenter">'
    + "Se reconnecter</a> — vous reviendrez sur cette page.";
}

function sessionEteinte() {
  if (SESSION_MORTE) return;
  SESSION_MORTE = true;
  var b = document.createElement("div");
  b.id = "ig-session";
  b.className = "ig-session-alerte";
  b.setAttribute("role", "alert");
  b.innerHTML = sessionTexte();
  var m = document.getElementById("main") || document.body;
  m.insertBefore(b, m.firstChild);
  /* Les deux zones qui, sinon, continueraient de raconter autre chose —
     la frise réclamant une puissance déjà saisie, le dossier l'attendant. */
  ["ig-parcours", "ig-dossier"].forEach(function (id) {
    var z = document.getElementById(id);
    if (z) z.innerHTML = '<p class="ig-dep-ko">' + sessionTexte() + "</p>";
  });
  b.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function demander(url, options, delai) {
  options = options || {};
  var ctrl = (typeof AbortController !== "undefined") ? new AbortController() : null;
  var fini = false;
  var m = setTimeout(function () {
    if (!fini && ctrl) { try { ctrl.abort(); } catch (e) {} }
  }, delai || DELAI_COURT);
  if (ctrl && !options.signal) options.signal = ctrl.signal;
  return fetch(url, options).then(function (r) {
    fini = true; clearTimeout(m);
    /* Le 401 est traité ICI, une fois pour toutes les zones : laissé aux
       appelants, chacun le dissolvait dans son message générique. */
    if (r.status === 401) {
      sessionEteinte();
      var t = new Error("auth"); t.name = "SessionEteinte";
      throw t;
    }
    return r;
  }, function (e) {
    fini = true; clearTimeout(m);
    if (e && e.name === "AbortError" && !options.__annule) {
      var t = new Error("delai"); t.name = "DelaiDepasse";
      t.delai = delai || DELAI_COURT;
      throw t;
    }
    throw e;
  });
}

function messageDelai(e, defaut) {
  if (e && e.name === "DelaiDepasse") {
    return "Le serveur n'a pas répondu en " + Math.round(e.delai / 1000)
      + " secondes. Il est peut-être très sollicité : relancez dans un "
      + "instant. Vos saisies sont conservées.";
  }
  return defaut;
}

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

  var REF = null, CADRE = null, FILIERE = "moe", PHASE = null, DERNIER = null;
  var ART = {};   /* l'état de l'art : sourcé, jamais dans un calcul */
  var DOSSIER = null;

  function $(s, r) { return (r || document).querySelector(s); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
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
    var el = $("#ig-etat");
    if (!el) return;
    el.textContent = msg || "";
    el.style.color = err ? "var(--red, #F0A0A0)" : "";
  }

  /* ── Le formulaire, dérivé du même référentiel que /datacenter ──────────
     Les options ne sont pas écrites dans le HTML : une liste recopiée finit
     par proposer une famille que le moteur ne connaît plus. */
  function bâtirFormulaire() {
    var champs = REF.champs || [];
    var h = '<div class="dc-grille">';
    champs.forEach(function (c) {
      var id = "ig-" + c.id;
      h += '<label class="dc-champ" for="' + id + '">'
        + '<span class="dc-lab">' + esc(c.label)
        + (c.unite ? ' <span class="dc-unite">(' + esc(c.unite) + ')</span>' : "")
        + (c.requis ? ' <b class="dc-req" title="Champ nécessaire">*</b>' : "")
        + "</span>";
      if (c.type === "liste") {
        h += '<select id="' + id + '" data-champ="' + esc(c.id) + '">'
          + '<option value="">— non précisé —</option>';
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
        /* UNE LISTE DÉROULANTE, PAS UNE LISTE FERMÉE. `list` accroche un
           menu de valeurs proposées à un champ qui reste libre : le lecteur
           choisit dans le menu, ou tape la valeur réelle de son projet. Un
           `select` interdirait précisément celle-là. */
        h += '<input id="' + id + '" data-champ="' + esc(c.id) + '" type="text" inputmode="decimal"'
          + (DEROULANTS.indexOf(c.id) >= 0 ? ' list="ig-dl-' + esc(c.id) + '"' : "")
          + (c.defaut !== undefined ? ' value="' + esc(c.defaut) + '"' : "")
          + ' placeholder="' + (c.defaut !== undefined ? esc(c.defaut) : "—") + '">';
      }
      if (c.aide) h += '<span class="dc-aide">' + esc(c.aide) + "</span>";
      /* Les valeurs proposées, sous le champ : c'est là qu'on hésite. */
      h += rendreSuggestions(c, "#ig-form");
      h += "</label>";
    });
    $("#ig-form").innerHTML = h + "</div>";
    brancherSuggestions("#ig-form");
    controlerPlages("#ig-form");
    $("#ig-form").addEventListener("input", function () {
      controlerPlages("#ig-form");
      rafraichir();
    });
    $("#ig-form").addEventListener("change", function () {
      /* Les propositions CONTEXTUELLES dépendent d'autres champs — la plage de
         PUE suit la famille de refroidissement, l'intensité carbone suit le
         pays. Changer l'un doit donc redessiner les propositions de l'autre,
         sinon la page conseille sur un choix qui n'est plus le sien. */
      majSuggestionsContexte("#ig-form");
      controlerPlages("#ig-form");
      rafraichir();
    });
  }

  /* Redessine les seules puces dont le contenu dépend d'un autre champ. On ne
     reconstruit pas le formulaire entier : cela effacerait ce que le lecteur
     est en train de taper. */
  function majSuggestionsContexte(prefixe) {
    /* LA LISTE VIENT DE LA CONSTANTE, plus d'une copie écrite ici. Les deux
       existaient et devaient rester d'accord : ajouter un champ contextuel
       sans penser à la seconde posait un conteneur que rien ne redessinait —
       la proposition n'apparaissait donc jamais. */
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
      h += '<datalist id="ig-dl-' + esc(c.id) + '">';
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
  function controlerPlages(prefixe) {
    (((REF || {}).champs) || []).forEach(function (c) {
      if (!c.plage_observee) return;
      var e = document.querySelector(prefixe + ' [data-champ="' + c.id + '"]');
      if (!e) return;
      var lab = e.closest(".dc-champ") || e.parentNode;
      var vieux = lab.querySelector(".ig-hors");
      if (vieux) vieux.remove();
      var v = parseFloat(String(e.value).replace(",", "."));
      if (!isFinite(v) || e.value === "") return;
      var p = c.plage_observee, msg = null;
      if (v > p.haut) msg = p.note;
      else if (v < p.bas) msg = p.note_bas || p.note;
      if (!msg) return;
      var n = document.createElement("span");
      n.className = "ig-hors";
      n.textContent = "Hors de ce qui s'observe (" + fr(p.bas) + " à "
        + fr(p.haut) + ") — " + msg;
      lab.appendChild(n);
    });
  }

  /* LE SIGNAL SE POSE SUR LE CHAMP, pas seulement au pied de la page. Un
     message global oblige à retrouver soi-même lequel des treize champs n'a
     pas été lu — et sur un formulaire de treize champs, personne ne cherche. */
  function marquerRejets(rejets) {
    document.querySelectorAll("#ig-form .ig-rejet").forEach(function (e) {
      e.remove();
    });
    document.querySelectorAll("#ig-form [data-champ]").forEach(function (e) {
      e.classList.remove("ig-illisible");
      e.removeAttribute("aria-invalid");
    });
    (rejets || []).forEach(function (r) {
      var e = document.querySelector('#ig-form [data-champ="' + r.champ + '"]');
      if (!e) return;
      e.classList.add("ig-illisible");
      /* La couleur ne suffit pas : le message est du texte, et le champ se
         déclare invalide pour les technologies d'assistance. */
      e.setAttribute("aria-invalid", "true");
      var p = document.createElement("span");
      p.className = "ig-rejet";
      p.textContent = r.message;
      (e.closest("label") || e.parentNode).appendChild(p);
    });
  }

  function lireProfil() {
    var p = {};
    document.querySelectorAll("#ig-form [data-champ]").forEach(function (el) {
      var v = (el.value || "").trim();
      if (v !== "") p[el.getAttribute("data-champ")] = v;
    });
    return p;
  }

  /* ── Les infobulles ─────────────────────────────────────────────────────
     Cette page aligne des sigles exacts et opaques : ESQ, APD, DCE, FEED,
     EPCI, gel contractuel, accord partiel, classe 3. Sans explication, elle ne
     s'adresse qu'à ceux qui n'en avaient pas besoin.

     Pas d'attribut `title` natif : il n'apparaît qu'après une seconde
     d'immobilité, ne se met pas en forme, ne passe pas à la ligne, et reste
     hors d'atteinte au clavier. On construit donc une infobulle unique,
     déplacée d'une cible à l'autre.

     Un seul attribut à poser dans le rendu — data-info="famille:clé" — et une
     seule recherche dans le glossaire servi par le serveur. C'est ce qui permet
     d'en couvrir douze sortes sans douze mécanismes. */
  var TIP = null, TIP_CIBLE = null;

  function tipEl() {
    if (TIP) return TIP;
    TIP = document.createElement("div");
    TIP.className = "ig-tip";
    TIP.setAttribute("role", "tooltip");
    TIP.id = "ig-tip";
    TIP.hidden = true;
    document.body.appendChild(TIP);
    return TIP;
  }

  function tipTexte(ref) {
    var G = (CADRE && CADRE.glossaire) || {};
    var bout = String(ref || "").split(":");
    var fam = G[bout[0]];
    if (!fam) return null;
    var e = fam[bout.slice(1).join(":")];
    return e && (e.nom || e.aide) ? e : null;
  }

  function tipMontrer(cible) {
    var e = tipTexte(cible.getAttribute("data-info"));
    if (!e) return;
    var t = tipEl();
    t.innerHTML = '<b>' + esc(e.nom) + "</b>"
      /* Les définitions viennent du serveur et contiennent des sauts de ligne
         signifiants (« ce qu'elle décide », « ce qu'elle verrouille ») : on les
         rend, sans jamais interpréter le reste comme du HTML. */
      + (e.aide ? "<p>" + esc(e.aide).replace(/\n/g, "<br>") + "</p>" : "");
    t.hidden = false;
    TIP_CIBLE = cible;
    cible.setAttribute("aria-describedby", "ig-tip");
    tipPlacer(cible);
  }

  function tipCacher() {
    if (!TIP) return;
    TIP.hidden = true;
    if (TIP_CIBLE) TIP_CIBLE.removeAttribute("aria-describedby");
    TIP_CIBLE = null;
  }

  function tipPlacer(cible) {
    var t = tipEl(), r = cible.getBoundingClientRect();
    /* Mesurée AVANT d'être positionnée : sans cela on placerait une boîte dont
       on ignore la taille, et elle sortirait du cadre une fois sur deux. */
    t.style.left = "0px"; t.style.top = "0px";
    var b = t.getBoundingClientRect();
    var marge = 10;
    var x = r.left + r.width / 2 - b.width / 2;
    x = Math.max(marge, Math.min(window.innerWidth - b.width - marge, x));
    /* Au-dessus par défaut ; en dessous s'il n'y a pas la place en haut. Une
       infobulle qui déborde du haut de la fenêtre est illisible et ne se
       rattrape pas au défilement. */
    var y = r.top - b.height - 8;
    if (y < marge) y = r.bottom + 8;
    t.style.left = Math.round(x + window.pageXOffset) + "px";
    t.style.top = Math.round(y + window.pageYOffset) + "px";
  }

  /* Un seul écouteur, posé une fois sur le document, plutôt qu'un par cible :
     la page se redessine à chaque saisie et à chaque changement de phase, et
     des écouteurs par élément seraient à reposer à chaque fois — ou à oublier. */
  function tipBrancher() {
    if (document.__igTip) return;
    document.__igTip = true;
    var dans = function (ev) {
      var c = ev.target && ev.target.closest && ev.target.closest("[data-info]");
      /* On rouvre AUSSI quand la boîte est masquée alors que la cible n'a pas
         changé. Ne comparer que la cible suffisait tant que tipCacher() était
         le seul chemin de fermeture — mais une boîte masquée par ailleurs
         restait alors définitivement close sur cette cible, sans rien pour le
         signaler. Un état interne et l'écran doivent pouvoir se rattraper. */
      if (c && (c !== TIP_CIBLE || (TIP && TIP.hidden))) tipMontrer(c);
    };
    document.addEventListener("mouseover", dans);
    document.addEventListener("mouseout", function (ev) {
      var c = ev.target && ev.target.closest && ev.target.closest("[data-info]");
      if (c && c === TIP_CIBLE) tipCacher();
    });
    /* Le clavier au même titre que la souris : une explication accessible
       seulement au survol n'existe pas pour qui navigue au clavier. */
    document.addEventListener("focusin", dans);
    document.addEventListener("focusout", function (ev) {
      if (ev.target === TIP_CIBLE) tipCacher();
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") tipCacher();
    });
    /* Au défilement, la cible bouge et l'infobulle resterait en arrière. */
    window.addEventListener("scroll", function () {
      if (TIP_CIBLE) tipPlacer(TIP_CIBLE);
    }, { passive: true });
  }

  /* Le marquage d'une cible. `tabindex` la rend atteignable au clavier ; sans
     lui l'explication serait réservée à la souris. */
  function info(ref) {
    return ' data-info="' + esc(ref) + '" tabindex="0"';
  }

  /* ── L'identification du projet ────────────────────────────────────────
     Les listes viennent du référentiel — leur NOMBRE n'est pas écrit ici : un
     compte figé dans un commentaire se répare machinalement au premier ajout et
     cesse alors de décrire quoi que ce soit. Chaque option porte ce qu'elle
     IMPLIQUE, et cette implication est affichée dès la sélection : sans elle, le
     lecteur choisit une étiquette sans savoir ce qu'elle engage, et la liste ne
     vaut pas mieux qu'un champ libre.

     NE RIEN CHOISIR N'EST PAS TOUJOURS NEUTRE. Quand un champ s'applique quand
     même faute de choix — la mission, qui vaut maîtrise d'œuvre par défaut —,
     l'option vide le DIT. « Non précisé » laisserait croire qu'aucune posture
     n'est prise, alors qu'elle l'est, et qu'elle commande ce que la pièce peut
     prescrire. Le libellé vient du serveur : c'est lui qui tient le défaut. */
  function bâtirIdentification() {
    var champs = (CADRE.identification || []);
    if (!champs.length) return;
    var z = $("#ig-ident");
    var h = "";
    champs.forEach(function (c) {
      var id = "ig-" + c.id;
      h += '<label class="dc-champ" for="' + id + '">'
        + '<span class="dc-lab">' + esc(c.label) + "</span>"
        + '<select id="' + id + '" data-ident="' + esc(c.id) + '">'
        + '<option value="">'
        + esc(c.defaut_nom ? "— non précisé : " + c.defaut_nom + " —"
                           : "— non précisé —") + "</option>"
        + (c.options || []).map(function (o) {
            return '<option value="' + esc(o.cle) + '">' + esc(o.nom) + "</option>";
          }).join("")
        + "</select>"
        + '<span class="dc-aide">' + esc(c.aide) + "</span>"
        + '<span class="ig-impl" id="' + id + '-i" hidden></span>'
        + "</label>";
    });
    z.insertAdjacentHTML("beforeend", h);
    z.querySelectorAll("[data-ident]").forEach(function (s) {
      s.addEventListener("change", function () { montrerImplication(s); });
    });
    var n = $("#ig-ident-n");
    if (n) n.textContent = CADRE.identification_note || "";
  }

  function montrerImplication(sel) {
    var cid = sel.getAttribute("data-ident");
    var champ = (CADRE.identification || []).filter(function (c) { return c.id === cid; })[0];
    var box = $("#" + sel.id + "-i");
    if (!champ || !box) return;
    var o = (champ.options || []).filter(function (x) { return x.cle === sel.value; })[0];
    if (!o) { box.hidden = true; box.textContent = ""; return; }
    box.hidden = false;
    box.textContent = o.implique;
  }

  function lireIdentification() {
    var o = {};
    document.querySelectorAll("#ig-ident [data-ident]").forEach(function (s) {
      if (s.value) o[s.getAttribute("data-ident")] = s.value;
    });
    return o;
  }

  /* ── Les onglets de filière ──────────────────────────────────────────── */
  function bâtirOnglets() {
    var f = (CADRE.filieres || {});
    var h = "";
    Object.keys(f).forEach(function (k) {
      h += '<button type="button" role="tab" data-fil="' + esc(k) + '" aria-selected="'
        + (k === FILIERE ? "true" : "false") + '" class="' + (k === FILIERE ? "on" : "")
        + '"' + info("filiere:" + k) + ">" + esc(f[k].nom) + "</button>";
    });
    var z = $("#ig-filieres");
    z.innerHTML = h;
    z.querySelectorAll("button").forEach(function (b) {
      b.addEventListener("click", function () {
        FILIERE = b.getAttribute("data-fil");
        PHASE = null;
        bâtirOnglets();
        /* `rendreParcours` pose lui-même le message des deux zones : PHASE
           vient d'être remis à null, il retombera sur le bon. L'écrire aussi
           ici créerait une seconde source de vérité, et c'est exactement ce
           qui a produit le défaut d'origine. */
        rendreParcours();
        boutons(false);
      });
    });
  }

  /* ── CE QUE LA PAGE DEMANDE DOIT EXISTER À L'ÉCRAN ──────────────────────
     LE DÉFAUT. Le bloc du dossier affichait « Choisissez une phase dans la
     frise ci-dessus » — y compris quand la frise n'était pas là. Or elle n'y
     est PAS tant que la puissance informatique n'est pas saisie, et c'est le
     seul champ du formulaire à n'avoir aucune valeur par défaut : les douze
     autres en ont une. Tout visiteur ouvrait donc la page sur une consigne qui
     désigne un objet absent, et chaque clic sur un onglet de filière la
     réaffirmait — d'où la lecture, exacte, que « la frise ne s'affiche plus
     quand on sélectionne ingénierie ou MOE ».

     CE QU'ON NE FAIT PAS. On ne donne pas de puissance par défaut. Une valeur
     inventée ferait sortir un dossier d'ingénierie complet, chiffré, pour un
     projet qui n'est pas celui du lecteur — et rien ne le lui dirait. Le champ
     reste vide ; c'est la CONSIGNE qu'on corrige, pas la donnée.

     CE QU'ON FAIT. Les deux zones lisent le même état, donc ne peuvent plus se
     contredire ; et le champ qui manque devient atteignable d'un clic, au lieu
     d'être à chercher parmi treize. */
  function friseVide() {
    return !DERNIER || !DERNIER[FILIERE];
  }

  var CHAMP_CLE = "puissance_it_kw";

  function messageAttente() {
    if (!friseVide()) return '<p class="note">Choisissez une phase dans la frise ci-dessus.</p>';
    return '<p class="note">La frise des phases apparaîtra ici dès que la '
      + "<b>puissance informatique installée</b> sera renseignée : c'est le seul "
      + "champ nécessaire, les douze autres ont une valeur par défaut. "
      + '<button type="button" class="ig-vers" data-vers-champ>Aller au champ</button></p>';
  }

  /* Amener au champ ET le désigner. Un défilement seul laisse le lecteur devant
     treize champs de même apparence, sans lui dire lequel on visait. */
  function versChampCle() {
    var e = document.querySelector('#ig-form [data-champ="' + CHAMP_CLE + '"]');
    if (!e) return;
    var l = e.closest(".dc-champ") || e;
    l.scrollIntoView({ behavior: "smooth", block: "center" });
    try { e.focus({ preventScroll: true }); } catch (x) { e.focus(); }
    l.classList.remove("ig-designe");
    void l.offsetWidth;                 /* redémarre l'animation si on reclique */
    l.classList.add("ig-designe");
    setTimeout(function () { l.classList.remove("ig-designe"); }, 2400);
  }

  /* Délégation unique : les deux zones sont reconstruites à chaque rendu, et
     rebrancher un écouteur par bouton en laisserait tôt ou tard un sans. */
  document.addEventListener("click", function (ev) {
    var b = ev.target && ev.target.closest ? ev.target.closest("[data-vers-champ]") : null;
    if (b) { ev.preventDefault(); versChampCle(); }
    var r = ev.target && ev.target.closest ? ev.target.closest("[data-relancer]") : null;
    if (r) { ev.preventDefault(); rafraichir(); }
  });

  /* ── La frise ────────────────────────────────────────────────────────── */
  function rendreParcours() {
    /* Le guidage est remis à jour APRÈS chaque rendu de la frise, jamais
       avant : appelé trop tôt, il désigne une cible qui n'existe pas encore et
       la flèche disparaît — ce qui se lit comme un guidage cassé. */
    setTimeout(majGuidage, 0);
    setTimeout(atterrir, 0);
    planifierVague();
    var z = $("#ig-parcours");
    if (friseVide()) {
      z.innerHTML = '<p class="note">Pour éprouver les phases, il manque la '
        + "<b>puissance informatique installée</b> — le seul champ nécessaire "
        + "de ce formulaire. "
        + '<button type="button" class="ig-vers" data-vers-champ>Aller au champ</button></p>';
      /* Le bloc du dessous parle de CETTE frise : il doit dire la même chose
         qu'elle, sans quoi la page se contredit d'une ligne à l'autre. */
      var d = $("#ig-dossier");
      if (d) d.innerHTML = messageAttente();
      return;
    }
    var P = DERNIER[FILIERE], stop = P.premier_blocage;
    var h = "";
    /* Le résumé AVANT la frise : c'est la conclusion, et une conclusion placée
       sous les données se lit après qu'on s'est fait sa propre idée. */
    if (stop) {
      var e = P.etapes.filter(function (x) { return x.code === stop; })[0] || {};
      h += '<p class="ig-res">Vous tenez <b>' + P.n_franchissables + '</b> phase'
        + (P.n_franchissables > 1 ? "s" : "") + ' sur ' + P.n_total
        + '. Le travail à engager est celui de <b>' + esc(stop) + " — " + esc(e.nom || "")
        + "</b> : " + esc(e.aptitude ? e.aptitude.verdict : "") + "</p>";
    } else {
      h += '<p class="ig-res">Toutes les phases de cette filière sont franchissables au '
        + "regard de ce moteur. Cela ne veut pas dire que le dossier est complet : les "
        + "autres disciplines ne sont pas éprouvées ici.</p>";
    }
    h += '<div class="ig-fil" role="tablist" aria-label="Phases">';
    P.etapes.forEach(function (e) {
      var cl = "ig-p " + (e.franchissable ? "ok" : "ko")
        + (e.code === stop ? " stop" : "") + (e.code === PHASE ? " on" : "");
      h += '<button type="button" class="' + cl + '" data-phase="' + esc(e.code) + '" '
        + 'aria-selected="' + (e.code === PHASE ? "true" : "false") + '" role="tab">'
        + '<span class="c"' + info("phase:" + e.code) + ">" + esc(e.code) + "</span>"
        + '<span class="n">' + esc(e.nom) + "</span>"
        + '<span class="e">' + (e.franchissable ? "franchissable"
            : (e.n_manques + e.n_substitutions) + " point"
              + ((e.n_manques + e.n_substitutions) > 1 ? "s" : "") + " ouvert"
              + ((e.n_manques + e.n_substitutions) > 1 ? "s" : "")) + "</span>"
        + "</button>";
    });
    h += "</div>";
    z.innerHTML = h;
    /* Le bloc du dossier suit l'état de la frise, TOUJOURS et depuis un seul
       endroit. Écrit ailleurs, il restait sur le message d'attente juste après
       la saisie de la puissance : la frise venait d'apparaître, et la ligne du
       dessous continuait d'annoncer qu'elle apparaîtrait. Quand une phase est
       choisie, c'est `chargerDossier` qui remplit — on ne l'écrase pas. */
    if (!PHASE) {
      var d2 = $("#ig-dossier");
      if (d2) d2.innerHTML = messageAttente();
    }
    z.querySelectorAll("[data-phase]").forEach(function (b) {
      b.addEventListener("click", function () {
        PHASE = b.getAttribute("data-phase");
        marquerURL();
        rendreParcours();
        chargerDossier();
      });
    });
  }

  /* ═════════════════════════════════════════════════════════════════════
     LA PAGE EST ADRESSABLE

     Sans cela, un livrable qui écrit « SPC-HVAC, repris en APD » ne peut y
     renvoyer que par un lien vers le haut de la page, à charge pour le lecteur
     de retrouver la filière, la phase et la pièce. Un lien qui oblige à
     chercher n'est pas un lien.

     La forme retenue — #phase=APD&piece=SPC-HVAC — se lit à l'œil dans un
     document imprimé, ce qu'un identifiant opaque ne permettrait pas. */
  function lireURL() {
    var h = (window.location.hash || "").replace(/^#/, "");
    if (!h) return null;
    var o = {};
    h.split("&").forEach(function (p) {
      var kv = p.split("=");
      if (kv.length === 2) o[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1]);
    });
    return o;
  }

  function marquerURL() {
    if (!PHASE) return;
    /* replaceState et non pushState : parcourir les phases n'est pas une
       navigation, et empiler quinze entrées d'historique rendrait le bouton
       « précédent » du navigateur inutilisable. */
    try {
      history.replaceState(null, "", "#phase=" + encodeURIComponent(PHASE));
    } catch (e) { /* navigation locale ou file:// — sans conséquence */ }
  }

  /* Applique ce que l'URL demande, une fois le cadre chargé. Renvoie le code
     de pièce à mettre en évidence, s'il y en a un. */
  function appliquerURL() {
    var o = lireURL();
    if (!o || !o.phase) return null;
    var ph = String(o.phase).toUpperCase();
    var q = (CADRE.phases || []).filter(function (x) { return x.code === ph; })[0];
    if (!q) return null;          // phase inconnue : on ne devine pas
    FILIERE = q.filiere;
    PHASE = ph;
    var t = document.querySelector('#ig-filieres [data-fil="' + FILIERE + '"]');
    if (t) {
      document.querySelectorAll("#ig-filieres [data-fil]").forEach(function (b) {
        b.classList.toggle("on", b === t);
        b.setAttribute("aria-selected", b === t ? "true" : "false");
      });
    }
    return o.piece ? String(o.piece).toUpperCase() : null;
  }

  /* Met en évidence la pièce visée par le lien et l'amène à l'écran. Un
     registre de trente pièces sans repère laisse le lecteur la chercher —
     c'est-à-dire abandonner. */
  function viserPiece(code) {
    if (!code) return false;
    var el = document.querySelector('#ig-dossier .ig-pc [data-piece="' + code + '"]');
    var bloc = el && el.closest(".ig-pc");
    if (!bloc) return false;
    document.querySelectorAll(".ig-pc.ig-vise-pc").forEach(function (e) {
      e.classList.remove("ig-vise-pc");
    });
    bloc.classList.add("ig-vise-pc");
    /* Un lien qui désigne une pièce promet sa fiche : arriver sur une carte
       repliée demanderait un second geste pour voir ce qu'on venait lire. */
    var f = bloc.querySelector(".ig-pc-f");
    if (f && !f.open) { f.open = true; FICHES[code] = true; majToutesFiches(); }
    var doux = !window.matchMedia
      || !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    bloc.scrollIntoView({ behavior: doux ? "smooth" : "auto", block: "center" });
    return true;
  }

  /* ── Le dossier de la phase ──────────────────────────────────────────── */
  function rendreDossier(d) {
    var h = '<div class="ig-d"><h3>' + esc(d.code) + " — " + esc(d.nom) + "</h3>"
      + '<p class="sous">' + esc(d.objet) + "</p>";

    h += '<div class="ig-meta">'
      + "<div><b>Ce qu'elle décide</b>" + esc(d.decide) + "</div>"
      + "<div><b>Ce qu'elle verrouille</b>" + esc(d.verrouille) + "</div>"
      /* Le geste d'écoconception de la phase — servi avec le dossier, le même
         que l'étude exportée : produits de construction spécifiés, exigés et
         vérifiés au bon moment (ISO/TR 14062, ISO 14006). */
      + (d.ecoconception
          ? "<div><b>Écoconception de la phase</b>" + esc(d.ecoconception.geste)
            + " <i>Preuve&nbsp;: " + esc(d.ecoconception.preuve) + "</i>"
            + ' <span class="ig-eco-cl">' + esc(d.ecoconception.clause) + "</span></div>"
          : "")
      + "<div><b>Précision attendue</b>" + esc(d.precision.valeur)
      + ' <span class="dc-unite"><span' + info("nature:" + d.precision.nature) + ">"
      + esc(d.precision.nature) + '</span> · <span' + info("aace:" + d.precision.aace)
      + ">" + esc(d.precision.aace) + "</span></span></div>"
      + "</div>";
    if (d.note) h += '<p class="ig-corr"><b>Précision de vocabulaire.</b> ' + esc(d.note) + "</p>";

    /* Ce que la phase attend d'ailleurs. La faisabilité a besoin d'une
       enveloppe d'investissement, et ce moteur-ci n'en produit pas : il chiffre
       l'énergie, l'eau et le carbone. Le taire laisserait croire qu'une
       faisabilité se boucle ici. */
    if (d.renvoi) {
      h += '<div class="ig-renvoi"><b>' + esc(d.renvoi.titre) + "</b>"
        + "<p>" + esc(d.renvoi.pourquoi) + "</p>"
        + "<p>" + esc(d.renvoi.quoi) + "</p>"
        + '<a href="' + esc(d.renvoi.url) + '" target="_blank" rel="noopener">'
        + "Ouvrir l'étude de faisabilité chiffrée</a></div>";
    }

    h += '<p class="sous" style="margin-top:14px"><span'
      + info("apport:" + d.apport_moteur) + ">" + esc(d.apport_texte) + "</span></p>";
    h += '<div class="ig-g">';
    (d.grandeurs || []).forEach(function (g) {
      var rmp = g.statut !== "recevable";
      h += '<div class="v' + (rmp ? " rmp" : "") + '">'
        + '<div class="n">' + esc(g.nom) + "</div>"
        + '<div class="q">' + fr(g.valeur) + ' <span class="u">' + esc(g.unite) + "</span></div>"
        + (g.incertitude ? '<div class="i">' + esc(g.incertitude) + "</div>" : "")
        + '<span class="st"' + info("statut:" + (rmp ? "a_remplacer" : "recevable")) + ">"
        + (rmp
            ? "à produire — bloquée par " + esc((g.postes_bloquants || []).join(", "))
            : "recevable à ce stade") + "</span></div>";
    });
    h += "</div>";

    var a = d.aptitude || {};
    if ((a.entrees_manquantes || []).length) {
      h += '<div class="ig-man manq"><h4>Entrées à renseigner — '
        + a.entrees_manquantes.length + " pour franchir cette phase</h4><ul>";
      a.entrees_manquantes.forEach(function (m) {
        h += '<li data-manque="' + esc(m.id) + '"><b>' + esc(m.label) + "</b>"
          + (m.unite ? " (" + esc(m.unite) + ")" : "")
          + " — " + esc(m.pourquoi)
          + (m.origine === "propre" ? "" : " <i>; dette d'une phase antérieure</i>")
          + "</li>";
      });
      /* Les nommer ne suffit pas : le lecteur doit ensuite les retrouver parmi
         treize champs, en remontant la page. Le bouton l'y conduit et les
         désigne — c'est le geste qu'il ferait, en moins long. */
      h += '</ul><button type="button" class="ig-man-b" id="ig-man-go">'
        + "Me montrer ces champs dans le formulaire ➜</button></div>";
    }
    if ((a.substitutions_a_faire || []).length) {
      h += '<div class="ig-man"><h4>Facteurs à remplacer par une donnée réelle</h4>';
      a.substitutions_a_faire.forEach(function (s) {
        h += '<div class="ig-sub"><span class="t"' + info("poste:" + s.cle) + ">"
          + esc(s.nom) + "</span>"
          + '<span class="k">' + esc(s.nature)
          + (s.incertitude ? " · " + esc(s.incertitude) : "") + "</span>";
        if (s.devient_insuffisant) {
          h += "<p><b>Pourquoi à ce stade</b> — " + esc(s.devient_insuffisant) + "</p>";
        }
        h += "<p><b>À remplacer par</b> — " + esc(s.remplacer_par) + "</p>";
        /* Une incertitude absente n'est pas une incertitude nulle : c'est la
           réserve la plus facile à oublier, donc celle qu'il faut écrire. */
        if (s.incertitude_absente) {
          h += "<p><b>Réserve</b> — ce poste ne porte aucune incertitude déclarée au "
            + "référentiel. Une incertitude absente n'est pas une incertitude nulle.</p>";
        }
        h += "</div>";
      });
      h += "</div>";
    }

    h += '<div class="ig-plan"><b>Plan de l\'étude</b><ol>'
      + (d.sections || []).map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("")
      + "</ol></div>";

    h += registrePieces(d);

    (d.correspondance || []).forEach(function (c) {
      var autre = d.filiere === "moe" ? c.indus : c.moe;
      h += '<p class="ig-corr"><b>Correspondance — ' + esc(autre) + "</b> (accord "
        + esc(c.accord) + "). " + esc(c.ecart) + "</p>";
    });

    $("#ig-dossier").innerHTML = h + "</div>";
    brancherPieces();
    boutons(true);
    /* Le registre vient d'apparaître. Il ne fait plus battre ses boutons en
       masse : le sélecteur en désignait quatre-vingt-trois d'un coup, ce qui
       est exactement le défaut contre lequel le battement avait été écrit —
       « trente boutons qui clignotent ensemble ne désignent plus rien ». Le
       fil des gestes désigne désormais LE bouton du moment, un seul, et c'est
       à lui de battre. */
  }

  /* ── Le registre des pièces ──────────────────────────────────────────────
     Le plan dit ce qu'on écrit ; le registre dit ce qu'on REMET. Deux choses
     distinctes : confondre les deux fait livrer un rapport là où le marché
     attend des pièces numérotées, chacune avec son émetteur.

     Les pièces sont groupées par TYPE et non par ordre de code : on cherche
     « les tableaux à fournir » ou « les plans », pas « la pièce numéro sept ». */
  var ORDRE_TYPE = ["note", "tableau", "plan", "schema", "contractuel",
                    "procedure", "registre"];

  /* Le registre : ce qu'on REMET, classé par ce que ça pèse.

     Trois partis pris, et le premier est celui qui change tout :

       · L'ORDRE EST CELUI DE L'IMPORTANCE, pas celui du registre. Vingt-trois
         pièces présentées à plat se lisent comme vingt-trois tâches
         équivalentes ; le lecteur commence alors par la plus facile. Chaque
         carte porte son caractère — obligatoire, indispensable, utile — ET son
         fondement, parce qu'un badge sans motif se discute en réunion et ne se
         tranche pas.

       · CE QUI EST FAIT EST SÉPARÉ DE CE QUI RESTE. Un registre qui mélange
         les deux oblige à relire tout le dossier pour savoir où on en est.

       · LES COLONNES ne sont pas une préférence de mise en page : à une carte
         par ligne, vingt-trois pièces font quatre écrans et la dernière n'est
         jamais lue. Le nombre de colonnes est décidé par la feuille de style,
         qui l'adapte à la largeur réelle — l'écrire ici en ferait une seconde
         vérité, et c'est celle du navigateur qui gagnerait. */
  var PLAN = null;

  /* Les fiches ouvertes, par code de pièce. Le registre se redessine à chaque
     rafraîchissement — changement de phase, rédaction terminée, visa posé — et
     sans cette mémoire, la fiche qu'on vient d'ouvrir se refermait sous les
     yeux du lecteur, qui la rouvrait, et ainsi de suite. */
  var FICHES = {};

  function carteP(p) {
    var L = p.livrable;
    var v = L && L.visa;
    return '<article class="ig-pc ig-c-' + esc(p.caractere)
      + (p.moteur ? " mot" : "") + (p.discipline ? " dis" : "")
      + (p.fait ? " fait" : "") + '" data-code="' + esc(p.code) + '">'
      + '<div class="ig-pc-top">'
      + '<span class="ig-car" ' + info("caractere:" + p.caractere) + ">"
      + esc(p.caractere_nom) + "</span>"
      + '<span class="ig-ord">n° ' + p.ordre + "</span>"
      + (v ? '<span class="ig-vis ig-v-' + esc(v.etat) + '"'
             + info("visa:" + v.etat) + ">" + esc(v.nom) + "</span>"
           : (p.fait ? '<span class="ig-vis ig-v-en_attente"'
                       + info("visa:en_attente") + ">En attente de visa</span>" : ""))
      + "</div>"
      + '<div class="ig-pc-h"><code>' + esc(p.code) + "</code> "
      + '<span class="ti">' + esc(p.titre) + "</span></div>"
      + '<div class="ig-pc-meta"><span class="em"' + info("emetteur:" + p.emetteur)
      + ">" + esc(p.emetteur_nom) + "</span>"
      /* Le TYPE de pièce reste porté par la carte. Il servait de titre de
         groupe ; le regroupement est passé à l'avancement, mais un lecteur qui
         ne sait pas ce qu'est une « pièce contractuelle » doit toujours
         pouvoir l'apprendre — sinon la refonte a coûté une information. */
      + '<span class="tp"' + info("type_piece:" + p.type) + ">"
      + esc(p.type_nom) + "</span>"
      + (p.moteur ? '<span class="mo"' + info("moteur:oui")
          + ">alimentée par le calcul</span>" : "")
      + "</div>"
      /* Le NIVEAU attendu reste au résumé : c'est lui qui dit à quelle
         profondeur écrire, et il tient en deux mots. Son AIDE, plus longue,
         part avec le reste de la fiche. */
      + (p.niveau_nom
          ? '<div class="ig-pc-nv"><span class="nv nv-' + esc(p.niveau) + '"'
            + info("niveau:" + p.niveau) + ">" + esc(p.niveau_nom) + "</span>"
            + (p.discipline_nom
                ? ' <span class="di"' + info("discipline:" + p.discipline) + ">"
                  + esc(p.discipline_nom) + "</span>" : "")
            + "</div>"
          : "")
      + (L ? '<div class="ig-pc-l"><b>Rédigée</b> le ' + pjDate(L.created_at)
             + " · " + esc(L.etat)
             + (v && v.bloquants && v.bloquants.length
                 ? '<span class="mtf">Motif — '
                   + esc(v.bloquants[0].motif || "non précisé") + "</span>" : "")
             + "</div>" : "")
      /* LA FICHE, À LA DEMANDE. Vingt-trois cartes déployées font huit écrans,
         et la dernière n'est jamais lue : le registre devient illisible par
         excès de rigueur. Ce qui reste au résumé est ce qui sert à CHOISIR —
         caractère, code, intitulé, émetteur, type, niveau, état. Ce qui sert à
         RÉDIGER — le motif de l'obligation, le contenu exigé point par point,
         le vocabulaire de recherche, la reprise d'une phase à l'autre —
         s'ouvre d'un geste, et rien n'est perdu.

         <details> plutôt qu'un dépliant fait main : le clavier, la lecture
         d'écran et l'impression le connaissent déjà, et il fonctionne même si
         le script de la page ne s'exécute pas. */
      + '<details class="ig-pc-f"' + (FICHES[p.code] ? " open" : "") + ">"
      + "<summary>Fiche complète"
      + ((p.contenu || []).length
          ? ' <span class="n">' + (p.contenu || []).length
            + " point" + ((p.contenu || []).length > 1 ? "s" : "")
            + " exigé" + ((p.contenu || []).length > 1 ? "s" : "") + "</span>"
          : "")
      + "</summary><div class=\"ig-pc-fc\">"
      + (p.niveau_aide ? '<p class="ig-pc-nva">' + esc(p.niveau_aide) + "</p>" : "")
      + (p.autres_phases && p.autres_phases.length
          ? '<p class="ap">document unique, repris en '
            + esc(p.autres_phases.join(", ")) + "</p>" : "")
      /* Le MOTIF du caractère. Sans lui, « Obligatoire » est une affirmation ;
         avec lui, elle se vérifie. */
      + '<p class="ig-car-m">' + esc(p.caractere_motif) + "</p>"
      + '<ul>' + (p.contenu || []).map(function (c) {
          return "<li>" + esc(c) + "</li>"; }).join("") + "</ul>"
      + (p.recherche_origine === "titre"
          ? '<div class="ig-pc-rq tit"><span class="lb"' + info("recherche:titre")
            + ">recherche</span> <i>son intitulé, faute de vocabulaire déclaré</i></div>"
          : '<div class="ig-pc-rq"><span class="lb"'
            + info("recherche:" + p.recherche_origine) + ">recherche</span> "
            + esc(p.recherche) + "</div>")
      + "</div></details>"
      + '<div class="ig-pc-a"><button type="button" class="ig-gen" data-piece="'
      + esc(p.code) + '">' + (p.fait ? "Reprendre" : "Rédiger") + "</button>"
      + '<button type="button" class="ig-voir" data-piece="' + esc(p.code)
      + '">Ce que la base apporte</button>'
      + (L ? '<button type="button" class="ig-visa" data-l="' + esc(L.id)
             + '" data-piece="' + esc(p.code) + '">Viser</button>'
             + '<a class="ig-dl" href="/api/datacenter/projets/'
             + esc(PROJET ? PROJET.id : "") + "/livrable/" + esc(L.id)
             + '.docx">Word</a>'
             + '<button type="button" class="ig-env" data-piece="' + esc(p.code)
             + '">Signaler</button>' : "")
      + (p.type === "plan" || p.type === "schema"
          ? '<span class="ig-pc-n">La rédaction produit la SPÉCIFICATION de la '
            + "pièce graphique — contenu, échelle, conventions — non le dessin.</span>"
          : "")
      + '</div><div class="ig-pc-doc" data-doc="' + esc(p.code) + '"></div></article>';
  }

  function registrePieces(d) {
    var P = (PLAN && PLAN.pieces) || d.pieces || [];
    if (!P.length) return "";
    var R = d.resume_pieces || {};
    var A = PLAN && PLAN.avancement;
    var h = '<div class="ig-reg"><div class="ig-reg-t"><b>' + R.total
      + "</b> pièce" + (R.total > 1 ? "s" : "") + " à fournir · <b>"
      + R.propres_a_la_phase + "</b> propre" + (R.propres_a_la_phase > 1 ? "s" : "")
      + " à la phase · <b>" + R.specifications_de_discipline
      + "</b> spécification" + (R.specifications_de_discipline > 1 ? "s" : "")
      + " de discipline · <b>" + R.alimentees_par_le_moteur + "</b> alimentée"
      + (R.alimentees_par_le_moteur > 1 ? "s" : "") + " par le calcul";
    if (A) {
      /* L'avancement RÉEL du dossier, et surtout les obligatoires qui
         manquent : c'est le seul chiffre qui décide si la phase peut être
         remise. */
      h += "<br><b>" + A.faits + "</b> rédigée" + (A.faits > 1 ? "s" : "")
        + " · <b>" + A.obligatoires_restants + "</b> obligatoire"
        + (A.obligatoires_restants > 1 ? "s" : "") + " restant"
        + (A.obligatoires_restants > 1 ? "es" : "e")
        + (A.valides_client ? " · <b>" + A.valides_client + "</b> validée"
            + (A.valides_client > 1 ? "s" : "") + " par le client" : "")
        + (A.rejetes ? ' · <b class="ko">' + A.rejetes + "</b> rejetée"
            + (A.rejetes > 1 ? "s" : "") : "");
    }
    h += "<span class='ig-reg-c'>"
      + Object.keys(R.par_type || {}).sort().map(function (k) {
          return esc(k) + " " + R.par_type[k];
        }).join(" · ") + "</span>"
      /* Ouvrir vingt-trois fiches une par une n'est pas une lecture : c'est
         une corvée. La commande d'ensemble est ici, au-dessus du registre —
         là où le lecteur décide comment il veut le lire. */
      + '<button type="button" id="ig-fiches-tout" class="ig-reg-b">'
      + "Déplier les fiches</button></div>";

    h += barreProjet(d);

    /* Deux groupes seulement : ce qui reste, ce qui est fait. Le type de pièce
       reste lisible sur chaque carte — en faire un niveau de regroupement
       éparpillerait les obligatoires dans sept sections. */
    var reste = P.filter(function (x) { return !x.fait; });
    var faits = P.filter(function (x) { return x.fait; });
    h += '<div class="ig-reg-cols">';
    h += groupe("À rédiger", reste,
                "Classées par importance décroissante : ce qui bloque la phase "
                + "d'abord, ce qui enrichit le dossier ensuite.");
    if (PLAN) {
      /* Le groupe des pièces faites porte une classe propre : il est signalé
         quand son contenu change — une pièce vient d'être écrite — et jamais à
         chaque redessin. Le signal porte sur le GROUPE, pas sur chaque carte :
         quarante halos simultanés ne désigneraient plus rien. */
      h += groupe("Rédigées et prêtes", faits,
                  "Produites pour ce projet, regroupées ici automatiquement. "
                  + "Le visa dit ce que le client et les collègues en ont fait.",
                  "faits");
    }
    h += "</div>";
    h += '<p class="ig-reg-n">' + esc(d.note_registre) + "</p>";
    return h + '<div id="ig-piece" aria-live="polite"></div></div>';

    function groupe(titre, liste, sous, marque) {
      if (!liste.length) {
        /* Le groupe vide garde sa marque : sans elle, il change d'identité
           entre « vide » et « rempli », et la page ne peut plus le désigner —
           ni le signaler quand la première pièce y arrive. */
        return PLAN
          ? '<section class="ig-reg-g' + (marque ? " g-" + marque : "")
            + '"><h5>' + esc(titre)
            + " <span>aucune pour l'instant</span></h5></section>" : "";
      }
      return '<section class="ig-reg-g' + (marque ? " g-" + marque : "")
        + '"><h5>' + esc(titre) + " <span>"
        + liste.length + " · " + esc(sous) + "</span></h5>"
        + selecteurPieces(liste, marque || "reste")
        + '<div class="ig-grille">'
        + liste.map(carteP).join("") + "</div></section>";
    }

    /* ══ LE SÉLECTEUR DE PIÈCES ═══════════════════════════════════════════
       CINQUANTE-QUATRE CARTES NE SE PARCOURENT PAS. Le registre les affiche
       toutes, classées par importance décroissante, et c'est le bon ordre pour
       DÉCIDER par quoi commencer. Ce n'est pas le bon geste pour ATTEINDRE une
       pièce qu'on a déjà en tête : il faut alors faire défiler une grille de
       cinquante-quatre éléments en lisant chaque titre.

       Le sélecteur donne l'autre geste. Il ne remplace pas le registre, il y
       conduit : choisir une pièce ouvre sa fiche là où elle se trouve, dans son
       groupe et à son rang. Les deux lectures coexistent parce qu'elles
       répondent à deux questions différentes — « par quoi je commence ? » et
       « où est celle-ci ? ».

       POURQUOI PAS UN <select> NATIF. Un `<select>` n'affiche qu'une ligne de
       texte par entrée : ni la pastille de caractère, ni le code, ni le rang ne
       s'y distinguent, et le décompte par groupe ne peut pas y être mis en
       valeur. Or c'est exactement ce que le lecteur vient chercher — combien
       d'obligatoires restent, et lesquelles. On écrit donc une liste de
       sélection ARIA, avec le clavier qu'un `<select>` aurait donné : flèches,
       Origine/Fin, Échap, et la frappe qui cherche. */
    function selecteurPieces(liste, cle) {
      if (!liste.length) return "";
      /* L'ORDRE EST CELUI DU REGISTRE, PAS UN ORDRE DE PLUS. Obligatoire,
         puis indispensable, puis utile : ce qui bloque la phase d'abord, ce qui
         enrichit le dossier ensuite. */
      var ordre = ["obligatoire", "indispensable", "utile"];
      var par = {};
      liste.forEach(function (p) {
        (par[p.caractere] = par[p.caractere] || []).push(p);
      });
      /* Un caractère que le serveur ajouterait demain ne doit pas disparaître
         du sélecteur : les rangs connus d'abord, les autres à la suite. Les
         omettre rendrait le décompte du bouton faux sans que rien ne le dise. */
      Object.keys(par).forEach(function (k) {
        if (ordre.indexOf(k) < 0) ordre.push(k);
      });
      var presents = ordre.filter(function (k) { return par[k]; });
      var bid = "ig-sel-b-" + cle, lid = "ig-sel-l-" + cle;
      var resume = presents.map(function (k) {
        var n = par[k].length;
        return '<span class="ig-sel-r-i"><i class="ig-sel-d d-' + esc(k)
          + '"></i>' + n + " "
          + esc(par[k][0].caractere_nom.toLowerCase()) + (n > 1 ? "s" : "")
          + "</span>";
      }).join("");
      var groupes = presents.map(function (k) {
        var g = par[k];
        return '<div class="ig-sel-g" role="group" aria-label="'
          + esc(g[0].caractere_nom) + " : " + g.length + " pièce"
          + (g.length > 1 ? "s" : "") + '">'
          + '<div class="ig-sel-gh"><i class="ig-sel-d d-' + esc(k) + '"></i>'
          + esc(g[0].caractere_nom) + "<b>" + g.length + "</b></div>"
          + g.map(function (p) {
            return '<div class="ig-sel-o" role="option" aria-selected="false"'
              + ' id="ig-sel-o-' + esc(cle) + "-" + esc(p.code) + '"'
              + ' data-code="' + esc(p.code) + '" data-cherche="'
              + esc(sansAccent(p.code + " " + p.titre)) + '">'
              + "<code>" + esc(p.code) + "</code>"
              + '<span class="ig-sel-ti">' + esc(p.titre) + "</span>"
              + '<em class="ig-sel-no">n° ' + esc(p.ordre) + "</em></div>";
          }).join("") + "</div>";
      }).join("");
      return '<div class="ig-sel" data-sel="' + esc(cle) + '">'
        + '<button type="button" class="ig-sel-b" id="' + bid + '"'
        + ' aria-haspopup="listbox" aria-expanded="false" aria-controls="' + lid + '">'
        + '<span class="ig-sel-n">' + liste.length + "</span>"
        + '<span class="ig-sel-lb">pièce' + (liste.length > 1 ? "s" : "")
        + " · aller à…</span>"
        + '<span class="ig-sel-r">' + resume + "</span>"
        + '<span class="ig-sel-x" aria-hidden="true"></span></button>'
        + '<div class="ig-sel-p" id="' + lid + '" role="listbox" tabindex="-1"'
        + ' aria-labelledby="' + bid + '" hidden>' + groupes + "</div></div>";
    }
  }

  /* La frappe qui cherche doit trouver « énergie » quand on tape « energie ».
     Un registre français sans cette normalisation oblige à composer les accents
     pour atteindre la moitié des pièces. */
  function sansAccent(s) {
    /* La plage est écrite en séquences d'échappement, pas en caractères
       combinants littéraux : un accent isolé dans un fichier source survit mal
       à un copier-coller, à une conversion d'encodage ou à un éditeur qui
       normalise — et la fonction devient alors silencieusement inopérante. */
    return String(s == null ? "" : s).normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  /* La barre de projet : tout emporter, prévenir, inviter. Elle n'apparaît que
     si un projet est ouvert — proposer « tout télécharger » quand rien n'est
     rattaché offrirait une archive vide. */
  function barreProjet(d) {
    if (!PROJET) {
      return '<div class="ig-bar vide">Aucun projet ouvert : les pièces '
        + "rédigées ne seront rattachées à aucun dossier, et ni l'archive ni "
        + "les visas ne seront disponibles. Ouvrez un projet en section 1.</div>";
    }
    var ph = d.code;
    return '<div class="ig-bar">'
      + '<span class="pj">Projet <b>' + esc(PROJET.nom) + "</b></span>"
      + '<a class="btn btn-s" href="/api/datacenter/projets/' + esc(PROJET.id)
      + '/dossier.zip?phase=' + esc(ph) + '">Télécharger la phase (ZIP)</a>'
      + '<a class="btn btn-s" href="/api/datacenter/projets/' + esc(PROJET.id)
      + '/dossier.zip">Tout le projet (ZIP)</a>'
      + '<button type="button" class="btn btn-s" id="ig-inviter">'
      + "Inviter un collègue</button>"
      + '<button type="button" class="btn btn-s" id="ig-envoyer-phase">'
      + "Signaler cette phase</button>"
      + '<div id="ig-bar-r" role="status" aria-live="polite"></div></div>';
  }

  /* ── La continuité : où aller ensuite ────────────────────────────────────
     Un registre dit ce qu'il faut produire. Il ne dit pas par quoi commencer
     ni ce qui vient après, et c'est là que le dossier s'arrête — non par
     désaccord, mais parce que personne ne sait quel est le geste suivant. */
  function railSuite() {
    var z = $("#ig-rail");
    if (!z) return;
    if (!PLAN || !PLAN.suite) { z.innerHTML = ""; z.hidden = true; return; }
    var s = PLAN.suite, h = '<div class="ig-rail-t">La suite</div>';
    if (s.piece) {
      h += '<button type="button" class="ig-fl" id="ig-fl-piece">'
        + '<span class="fx">↓</span><span class="fl-t">Pièce suivante</span>'
        + '<span class="fl-c">' + esc(s.piece.code) + "</span>"
        + '<span class="fl-n">' + esc(s.piece.caractere_nom) + "</span></button>";
    }
    if (s.bloquantes && s.bloquantes.length) {
      h += '<div class="ig-fl-w"><b>' + s.bloquantes.length
        + " obligatoire" + (s.bloquantes.length > 1 ? "s" : "")
        + "</b> restant" + (s.bloquantes.length > 1 ? "es" : "e")
        + " avant de pouvoir remettre cette phase.</div>";
    } else if (PLAN.avancement && PLAN.avancement.total) {
      h += '<div class="ig-fl-ok">Toutes les pièces obligatoires de la phase '
        + "sont rédigées.</div>";
    }
    if (s.phase) {
      h += '<button type="button" class="ig-fl suiv" id="ig-fl-phase">'
        + '<span class="fx">→</span><span class="fl-t">Phase suivante</span>'
        + '<span class="fl-c">' + esc(s.phase.code) + "</span>"
        + '<span class="fl-n">' + esc(s.phase.nom) + "</span></button>";
    } else if (s.fin) {
      h += '<div class="ig-fl-fin">' + esc(s.fin_texte || "Fin de la séquence.")
        + "</div>";
    }
    z.innerHTML = h;
    z.hidden = false;
    var b;
    if ((b = $("#ig-fl-piece"))) {
      b.addEventListener("click", function () { viserPiece(PLAN.suite.piece.code); });
    }
    if ((b = $("#ig-fl-phase"))) {
      b.addEventListener("click", function () {
        PHASE = PLAN.suite.phase.code;
        rafraichir();
        var t = $("#ig-dossier");
        if (t) t.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }

  /* ── Viser une pièce : valider ou rejeter, et dire pourquoi ─────────────
     Un rejet sans motif fait recommencer à l'identique. C'est le pire des
     retours : il coûte deux fois et n'apprend rien. Le serveur le refuse, et
     la page le dit avant d'envoyer plutôt qu'après. */
  function ouvrirVisa(lid, code, bouton) {
    var z = bouton.closest(".ig-pc").querySelector(".ig-pc-doc");
    if (z.querySelector(".ig-visa-f")) { z.innerHTML = ""; return; }
    var R = (PLAN && PLAN.etats_visa) || {};
    z.innerHTML = '<form class="ig-visa-f">'
      + '<label>Vous visez en tant que'
      + '<select class="rl"><option value="client">Client</option>'
      + '<option value="collegue">Collègue du projet</option>'
      + '<option value="moe">Maîtrise d\'œuvre</option></select></label>'
      + '<label>Décision<select class="dc">'
      + '<option value="valide">Validé</option>'
      + '<option value="rejete">Rejeté</option></select></label>'
      + '<label class="mt">Motif <span>obligatoire en cas de rejet</span>'
      + '<input type="text" class="mo" maxlength="800" '
      + 'placeholder="ce qui doit être repris, précisément"></label>'
      + '<div class="ac"><button type="submit" class="btn btn-s">Enregistrer</button>'
      + '<span class="rp"></span></div></form>';
    var f = z.querySelector(".ig-visa-f");
    f.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var rep = f.querySelector(".rp");
      var dec = f.querySelector(".dc").value;
      var mot = f.querySelector(".mo").value.trim();
      if (dec === "rejete" && mot.length < 5) {
        rep.className = "rp ko";
        rep.textContent = "Un rejet doit porter son motif : sans lui, la pièce "
          + "est reprise à l'identique.";
        return;
      }
      rep.className = "rp";
      rep.textContent = "Enregistrement…";
      demander("/api/datacenter/projets/" + PROJET.id + "/livrable/" + lid + "/visa", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: f.querySelector(".rl").value,
                               decision: dec, motif: mot }),
      })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (!j.ok) {
            rep.className = "rp ko";
            rep.textContent = j.message || "Visa refusé.";
            return;
          }
          rep.textContent = "";
          chargerPlan();
        })
        .catch(function () {
          rep.className = "rp ko";
          rep.textContent = "Le visa n'a pas pu être enregistré.";
        });
    });
  }

  function barreMsg(texte, ko) {
    var z = $("#ig-bar-r");
    if (z) {
      z.innerHTML = '<p class="' + (ko ? "ig-dep-ko" : "ig-dep-ok") + '">'
        + esc(texte) + "</p>";
    }
  }

  function inviterCollegue() {
    if (!PROJET) return;
    var email = window.prompt("Adresse électronique du collègue à inviter sur "
      + "le projet « " + PROJET.nom + " ».\n\nIl verra le dossier, son "
      + "historique et les pièces. Il ne pourra ni supprimer le projet ni "
      + "inviter d'autres personnes.");
    if (!email) return;
    demander("/api/datacenter/projets/" + PROJET.id + "/collaborateurs", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email }),
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) { barreMsg(j.message || "Invitation refusée.", true); return; }
        /* On dit si le courriel est PARTI, et sinon on donne le lien à
           transmettre. Annoncer « invitation envoyée » sur un serveur qui n'a
           pas de quoi l'envoyer serait la pire des confirmations. */
        barreMsg(j.courriel_envoye
          ? "Invitation envoyée. " + j.collaborateurs.length
            + " collègue(s) sur le projet."
          : "Collègue ajouté (" + j.collaborateurs.length + " au total). "
            + "L'envoi de courriel n'est pas configuré sur ce serveur : "
            + "transmettez-lui ce lien — " + j.lien);
      })
      .catch(function () { barreMsg("Invitation impossible.", true); });
  }

  function signaler(code) {
    if (!PROJET) return;
    var email = window.prompt("À quel collègue signaler "
      + (code ? "la pièce " + code : "cette phase") + " ?\n\n"
      + "Il doit déjà être invité sur le projet : sans accès, il recevrait un "
      + "lien qu'il ne peut pas ouvrir.");
    if (!email) return;
    var mot = window.prompt("Un mot pour l'accompagner (facultatif) :") || "";
    demander("/api/datacenter/projets/" + PROJET.id + "/envoyer", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, phase: PHASE, piece: code,
                             message: mot }),
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) { barreMsg(j.message || "Envoi refusé.", true); return; }
        barreMsg(j.courriel_envoye
          ? "Signalé à " + email + "."
          : "L'envoi de courriel n'est pas configuré sur ce serveur : "
            + "transmettez ce lien — " + j.lien);
      })
      .catch(function () { barreMsg("Envoi impossible.", true); });
  }

  /* Le plan : le registre confronté à ce que le projet a produit. Demandé
     seulement quand un projet est ouvert — sans projet, il n'y a rien à
     confronter, et l'appeler quand même afficherait « 0 rédigée » comme un
     retard alors qu'aucun dossier n'existe. */
  /* Recharge le plan et redessine le registre SANS refaire tout le dossier :
     après un visa, seule l'annotation change, et rejouer le calcul de phase
     ferait sauter la page pour rien. Le vocabulaire des visas appartient au
     module des projets et arrive avec le plan — on le verse dans le glossaire
     plutôt que d'en tenir une seconde copie côté serveur. */
  function chargerPlan() {
    if (!PROJET || !PHASE || !DOSSIER) return;
    var p = lireProfil();
    p.phase = PHASE;
    var ident = lireIdentification();
    Object.keys(ident).forEach(function (k) { p[k] = ident[k]; });
    demander("/api/datacenter/projets/" + PROJET.id + "/plan", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        PLAN = (j.ok && j.disponible) ? j : null;
        if (PLAN && PLAN.etats_visa && CADRE) {
          CADRE.glossaire = CADRE.glossaire || {};
          CADRE.glossaire.visa = PLAN.etats_visa;
        }
        rendreDossier(DOSSIER);
      })
      .catch(function () { /* le registre reste tel qu'il est */ });
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE GUIDAGE : APRÈS CHAQUE CHOIX, DIRE CE QUI SUIT

     Trois partis pris, et le troisième est celui qui évite que le guidage
     devienne du bruit :

       · LA SÉQUENCE VIENT DU SERVEUR. Le module publie le fil des gestes ;
         la page n'applique qu'une règle générique — le premier geste non fait
         dont les préalables sont remplis. Une séquence réécrite ici se
         contredirait au premier écran ajouté.

       · CHAQUE ÉTAPE DIT CE QU'ELLE DÉCLENCHE. « Choisissez une phase » fait
         cliquer ; « le registre s'affiche alors, classé par importance » fait
         comprendre. C'est la moitié du message, et c'est celle qu'on oublie.

       · LE BATTEMENT NE SE RÉPÈTE PAS. Chaque geste bat UNE fois, à son tour :
         un halo qui revient à chaque rafraîchissement cesse d'être un repère
         et devient une gêne — et l'écran entier finit par clignoter. */
  var GESTE = null;

  /* LES ÉTAPES PASSÉES. Passer n'est pas faire, et les deux ne se rangent pas
     au même endroit : « fait » est un CONSTAT tiré de l'écran, « passé » est
     une DÉCISION du lecteur. Elle vit le temps de la session — un choix de
     confort n'a pas à survivre à la fermeture du navigateur. */
  var CLE_PASSES = "ig_gestes_passes";

  function passes() {
    try {
      var v = JSON.parse(sessionStorage.getItem(CLE_PASSES) || "[]");
      return Array.isArray(v) ? v.filter(function (x) { return typeof x === "string"; }) : [];
    } catch (e) { return []; }
  }

  function passer(id) {
    var p = passes();
    if (p.indexOf(id) < 0) p.push(id);
    try { sessionStorage.setItem(CLE_PASSES, JSON.stringify(p)); } catch (e) { /* sans mémoire */ }
    majGuidage();
  }

  function reprendre(id) {
    var p = passes().filter(function (x) { return x !== id; });
    try { sessionStorage.setItem(CLE_PASSES, JSON.stringify(p)); } catch (e) { /* sans mémoire */ }
    majGuidage();
  }

  function etatGuidage() {
    /* Ce que la page VOIT. Chaque clé est un constat, jamais une supposition :
       une clé absente vaut « pas fait », et un guide qui supposerait l'étape
       accomplie ferait sauter la seule qui manquait. */
    var A = PLAN && PLAN.avancement;
    var t = function (sel) { var e = $(sel); return !!(e && e.innerHTML.trim()); };
    return {
      projet: !!PROJET,
      profil: !!(lireProfil() || {}).puissance_it_kw,
      phase: !!PHASE,
      disponibilite: !!(($("#ig-tier") || {}).value),
      /* LES TROIS CONSTATS D'ARGENT. Un tableau produit, pas un bouton
         cliqué : le clic ne prouve rien, un chiffrage refusé laisse la zone
         vide et le fil doit continuer de proposer l'étape. */
      moe: !!$("#ig-moe-out table"),
      travaux: !!$("#ig-eco-out .ig-eco-t"),
      honoraires: !!$("#ig-pont-out .ig-moe-kpi"),
      piece: !!(A && A.faits > 0),
      visa: !!(A && (A.valides_client > 0 || A.rejetes > 0)),
      obligatoires_faites: !!(A && A.total > 0 && A.obligatoires_restants === 0),
      fin: !!(PLAN && PLAN.suite && PLAN.suite.fin),
    };
  }

  function majGuidage() {
    var z = $("#ig-guidage");
    if (!z || !CADRE || !CADRE.gestes) return;
    var etat = etatGuidage();
    var fil = CADRE.gestes;
    var pss = passes();
    var g = null;
    for (var i = 0; i < fil.gestes.length; i++) {
      var c = fil.gestes[i];
      /* PASSER N'EST PAS FAIRE. Un geste passé n'est plus proposé, sinon le
         fil resterait bloqué sur des prix unitaires qui ne sont pas arrivés et
         cesserait de proposer quoi que ce soit d'autre. Mais il ne remplit
         AUCUN préalable : le geste qui en dépend n'est pas proposé non plus,
         parce qu'il ne pourrait pas aboutir — le pont sans chiffrage de
         travaux ne rendrait qu'un refus. */
      if (etat[c.fait_si] || pss.indexOf(c.id) >= 0) continue;
      var pret = true;
      for (var j = 0; j < c.exige.length; j++) {
        if (!etat[c.exige[j]]) { pret = false; break; }
      }
      if (pret) { g = c; break; }
    }
    GESTE = g;
    var faits = fil.gestes.filter(function (x) { return etat[x.fait_si]; });
    var sautes = fil.gestes.filter(function (x) {
      return !etat[x.fait_si] && pss.indexOf(x.id) >= 0; });
    var n = fil.gestes.length;
    filVertical(fil, etat, pss, g);

    if (!g) {
      z.className = "ig-guid fin";
      z.innerHTML = '<div class="g-t"><span class="g-p">Parcours terminé</span>'
        + "<b>" + esc(fil.fin.titre) + "</b></div>"
        + '<p class="g-x">' + esc(fil.fin.texte) + "</p>"
        + '<p class="g-a"><span class="fx">✓</span>' + esc(fil.fin.apres) + "</p>"
        /* UN PARCOURS « TERMINÉ » DONT DES ÉTAPES ONT ÉTÉ PASSÉES N'EST PAS
           TERMINÉ, et le taire serait le plus commode des mensonges. */
        + (sautes.length
           ? '<p class="g-s"><span class="fx">◇</span><b>' + sautes.length
             + " étape(s) passée(s), pas faite(s) — </b>"
             + sautes.map(function (x) { return esc(x.titre); }).join(" · ")
             + '. <button type="button" class="ig-g-lien" data-reprendre="'
             + esc(sautes[0].id) + '">Reprendre la première</button></p>'
           : "");
      var r0 = z.querySelector("[data-reprendre]");
      if (r0) r0.addEventListener("click", function () {
        reprendre(this.getAttribute("data-reprendre"));
      });
      fleche(null);
      return;
    }

    /* Ce que le lecteur VIENT de faire, nommé avec ses propres valeurs. Le
       référentiel ne le porte pas : il ne connaît ni le nom du projet ni le
       code de la phase, et y mettre des gabarits à trous ferait diverger le
       texte des données qu'il décrit. */
    var dernier = dernierChoix(etat);
    z.className = "ig-guid";
    z.innerHTML =
      (dernier ? '<p class="g-f"><span class="fx">✓</span>' + esc(dernier)
                 + "</p>" : "")
      + '<div class="g-t"><span class="g-p">Étape ' + (faits.length + 1)
      + " sur " + n + "</span><b>" + esc(g.titre) + "</b></div>"
      + '<p class="g-x">' + esc(g.texte) + "</p>"
      + '<p class="g-a"><span class="fx">➜</span><b>Ce que cela déclenche — </b>'
      + esc(g.apres) + "</p>"
      + '<div class="g-b"><button type="button" class="btn btn-s" id="ig-guid-go">'
      + "M'y conduire <span class=\"fx\">➜</span></button>"
      /* PASSER EST OFFERT LÀ OÙ C'EST LÉGITIME, et seulement là. Les prix
         unitaires viennent du bordereau du client : sans le droit de passer,
         le fil s'arrêterait sur une étape que le lecteur ne PEUT pas franchir,
         et ne proposerait plus jamais de rédiger une pièce. */
      + (g.facultatif
         ? '<button type="button" class="ig-g-lien" id="ig-guid-passer">'
           + "Passer cette étape</button>" : "")
      + '<span class="g-o">' + esc(g.fleche) + "</span>"
      + '<span class="g-r">' + faits.length + " / " + n
      + " étapes franchies"
      + (sautes.length ? " · " + sautes.length + " passée(s)" : "")
      + "</span></div>"
      + (g.facultatif && g.passer
         ? '<p class="g-s"><span class="fx">◇</span>' + esc(g.passer) + "</p>" : "")
      + '<div class="g-jauge"><i style="width:'
      + Math.round(faits.length * 100 / n) + '%"></i></div>';

    var b = $("#ig-guid-go");
    if (b) b.addEventListener("click", function () { allerAuGeste(g); });
    var sp = $("#ig-guid-passer");
    if (sp) sp.addEventListener("click", function () { passer(g.id); });
    designer(g);
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE FIL VERTICAL — SAVOIR OÙ L'ON EST SANS AVOIR À REMONTER

     Le bandeau dit CE QU'IL FAUT FAIRE. Il ne dit pas où l'on en est quand on
     a défilé six écrans plus bas : arrivé à la section 7, le lecteur ne voit
     plus rien du parcours et ne sait pas si les sections qu'il a dépassées
     comptaient.

     UNE FLÈCHE PAR SECTION, POSÉE ENTRE LES SECTIONS, dans l'ordre du fil.
     Chacune porte trois choses : son rang, son état, et ce qui passe d'une
     section à la suivante. Une flèche muette occupe la place sans rien
     apprendre — c'est la règle déjà tenue par les flèches de l'étude
     d'enveloppe, et elle vaut ici.

     ELLES N'APPARAISSENT QUE LE PARCOURS ENGAGÉ. Sur une page déjà dense, un
     fil affiché à quelqu'un qui n'a rien commencé est du décor.
     ═════════════════════════════════════════════════════════════════════ */

  var FIL_POSE = false;

  function filVertical(fil, etat, pss, courant) {
    var engage = !!(etat.projet || etat.profil || etat.phase);
    /* Les ancres, dans l'ordre du fil et sans doublon : quatre gestes visent
       le registre des pièces, et quatre flèches devant la même section ne
       diraient rien de plus qu'une seule. */
    var vues = {}, rangs = [];
    fil.gestes.forEach(function (g, i) {
      if (vues[g.ancre] != null) { rangs[vues[g.ancre]].fin = i + 1; return; }
      vues[g.ancre] = rangs.length;
      rangs.push({ ancre: g.ancre, debut: i + 1, fin: i + 1, gestes: [g] });
      return;
    });
    fil.gestes.forEach(function (g) {
      var r = rangs[vues[g.ancre]];
      if (r.gestes.indexOf(g) < 0) r.gestes.push(g);
    });

    if (!FIL_POSE) {
      rangs.forEach(function (r, i) {
        /* LE RAIL EST FIXE ET FLOTTE À DROITE : y glisser une flèche
           verticale la sortirait du fil de lecture, à l'endroit précis où
           elle doit s'y trouver. Son geste reste dans le bandeau. */
        if (r.ancre === "#ig-rail") return;
        var cible = document.querySelector(r.ancre);
        if (!cible || !cible.parentNode) return;
        /* La flèche se pose JUSTE DEVANT l'ancre du geste, pas devant la
           section : deux gestes visent la section 2 et deux la section 7, et
           les empiler devant la même section ferait deux flèches côte à côte
           qui ne désigneraient plus rien. */
        var d = document.createElement("div");
        d.className = "ig-jal";
        d.setAttribute("data-rang", String(i));
        d.hidden = true;
        cible.parentNode.insertBefore(d, cible);
      });
      FIL_POSE = true;
    }

    document.querySelectorAll(".ig-jal").forEach(function (d) {
      var r = rangs[Number(d.getAttribute("data-rang"))];
      if (!r) { d.hidden = true; return; }
      d.hidden = !engage;
      if (!engage) return;

      var faits = r.gestes.filter(function (g) { return etat[g.fait_si]; }).length;
      var passesIci = r.gestes.filter(function (g) {
        return !etat[g.fait_si] && pss.indexOf(g.id) >= 0; }).length;
      var ici = !!(courant && r.gestes.some(function (g) { return g.id === courant.id; }));
      var tous = r.gestes.length;

      var etatMot, cls;
      if (ici) { etatMot = "Vous êtes ici"; cls = "ici"; }
      else if (faits === tous) { etatMot = "Franchie"; cls = "fait"; }
      else if (faits + passesIci === tous && passesIci) { etatMot = "Passée, pas faite"; cls = "saute"; }
      else if (faits > 0) { etatMot = faits + " sur " + tous + " franchie(s)"; cls = "fait"; }
      else { etatMot = "À venir"; cls = "avenir"; }
      d.className = "ig-jal " + cls;

      var rang = r.debut === r.fin ? "Étape " + r.debut
        : "Étapes " + r.debut + " à " + r.fin;
      /* Le geste NOMMÉ est celui qui reste à faire ici, ou le dernier franchi :
         nommer toujours le premier ferait dire « ouvrez un projet » à quelqu'un
         qui en a ouvert un. */
      var nomme = r.gestes.filter(function (g) { return !etat[g.fait_si]; })[0]
                  || r.gestes[r.gestes.length - 1];
      d.innerHTML = '<span class="ig-jal-a" aria-hidden="true">'
        + (cls === "fait" ? "✓" : cls === "saute" ? "◇" : "↓") + "</span>"
        + '<div class="ig-jal-c"><span class="ig-jal-p">' + esc(rang)
        + " sur " + fil.gestes.length + " · " + esc(etatMot) + "</span>"
        + "<b>" + esc(nomme.titre) + "</b>"
        + '<p class="ig-jal-x">' + esc(nomme.apres) + "</p></div>";
      d.setAttribute("data-debut", String(r.debut));
    });

    /* L'ORDRE DU PARCOURS N'EST PAS CELUI DE LA PAGE, et il faut le dire là où
       ça se voit. Le niveau de disponibilité se décide en section 2 mais après
       la phase, qui est en section 3 : sans un mot, le lecteur croit que la
       numérotation est cassée et cesse de s'y fier. */
    var prec = 0;
    document.querySelectorAll(".ig-jal").forEach(function (d) {
      if (d.hidden) return;
      var deb = Number(d.getAttribute("data-debut") || 0);
      if (deb && deb < prec) {
        var p = document.createElement("p");
        p.className = "ig-jal-o";
        p.textContent = "L’ordre du parcours n’est pas celui de la page : "
          + "cette étape se décide après une autre, plus bas.";
        var c = d.querySelector(".ig-jal-c");
        if (c) c.appendChild(p);
      }
      prec = Math.max(prec, deb);
    });
  }

  /* Les calculs de la section 6 et de la section 7 vivent hors de ce module :
     ils préviennent par un événement plutôt que de s'appeler l'un l'autre. Sans
     cela, le fil ne verrait jamais qu'un chiffrage a été produit et resterait
     posé sur une étape déjà franchie. */
  document.addEventListener("ig-chiffrage", function () { majGuidage(); });

  /* Désigne UNE cible, et une seule.
     Le sélecteur d'un geste peut matcher des dizaines d'éléments — « le bouton
     Rédiger de chaque pièce non faite », c'est quatre-vingts boutons à la
     phase DCE. Les faire battre ensemble ne désigne plus rien : c'est
     exactement le défaut contre lequel le battement avait été écrit. On marque
     donc le PREMIER élément, et lui seul bat.

     La cible peut aussi ne pas encore exister : la frise et le registre
     arrivent après leur requête. Plutôt que de renoncer en silence — une
     flèche absente se lit comme un guidage cassé — on réessaie brièvement. */
  var designeMinuteur = null, DESIGNE = null;

  function designer(g, essai) {
    clearTimeout(designeMinuteur);
    /* On n'éteint QUE lors d'un changement de geste. Éteindre à chaque appel
       couperait le halo du geste courant sans pouvoir le rallumer — `battre`
       ne se réarme pas sur un même groupe, et c'est voulu : un halo qui revient
       à chaque rafraîchissement devient une gêne. */
    if (DESIGNE !== g.id) {
      document.querySelectorAll("[data-geste-cible]").forEach(function (e) {
        e.removeAttribute("data-geste-cible");
      });
      /* Le halo dure neuf secondes ; un lecteur rapide enchaîne deux choix
         dans cet intervalle et se retrouverait avec deux boutons désignés en
         même temps — soit aucun. Une désignation à la fois, sinon ce n'est
         plus une désignation. */
      document.querySelectorAll(".ig-bat, .ig-bat-doc").forEach(function (e) {
        e.classList.remove("ig-bat", "ig-bat-doc");
      });
      DESIGNE = g.id;
    }
    var c = $(g.cible);
    if (!c) {
      fleche(null);
      if ((essai || 0) < 12) {
        designeMinuteur = setTimeout(function () {
          if (GESTE && GESTE.id === g.id) designer(g, (essai || 0) + 1);
        }, 400);
      }
      return;
    }
    c.setAttribute("data-geste-cible", g.id);
    fleche(c);
    /* Une seule fois par geste : la clé de groupe porte l'identifiant, donc un
       rafraîchissement qui ne change rien ne rebat pas. */
    battre("[data-geste-cible]", g.classe || "ig-bat", "geste:" + g.id);
  }

  function dernierChoix(etat) {
    /* Le dernier choix constaté, dit avec ses valeurs réelles. On le prend au
       plus avancé, pas au premier trouvé : annoncer « projet ouvert » alors
       qu'on vient de choisir une phase donnerait l'impression d'un guide qui
       n'a pas suivi. */
    if (etat.visa) return "Visa enregistré sur une pièce du dossier.";
    if (etat.piece && PLAN) {
      return "Pièce rédigée et rattachée au projet — "
        + PLAN.avancement.faits + " au dossier de cette phase.";
    }
    if (etat.disponibilite && DISPO && DISPO.redondance) {
      return "Niveau de disponibilité arrêté — "
        + DISPO.redondance.installees + " unités installées.";
    }
    if (etat.phase && DOSSIER) {
      return "Phase " + DOSSIER.code + " retenue — " + DOSSIER.nom + ".";
    }
    if (etat.profil) return "Profil renseigné : le cadre peut éprouver les phases.";
    if (etat.projet && PROJET) return "Projet « " + PROJET.nom + " » ouvert.";
    return "";
  }

  /* La flèche. Un élément RÉEL inséré devant la cible plutôt qu'un pseudo-
     élément : elle se retire proprement, elle ne dépend pas du dépassement du
     conteneur, et elle est masquée aux lecteurs d'écran — le texte du bandeau
     dit déjà où aller, la répéter en ferait un doublon à l'oreille. */
  function fleche(cible) {
    document.querySelectorAll(".ig-fleche").forEach(function (e) { e.remove(); });
    if (!cible || !cible.parentNode) return;
    var f = document.createElement("span");
    f.className = "ig-fleche";
    f.setAttribute("aria-hidden", "true");
    f.textContent = "➜";
    cible.parentNode.insertBefore(f, cible);
  }

  function allerAuGeste(g) {
    var a = $(g.ancre) || $(g.cible);
    if (a) a.scrollIntoView({ behavior: "smooth", block: "center" });
    var c = $(g.cible);
    if (c && c.focus) {
      try { c.focus({ preventScroll: true }); } catch (e) { c.focus(); }
    }
  }

  /* Les intitulés d'échec, courts et distincts. Le message long vient du
     serveur — il connaît la configuration réelle ; le titre sert à distinguer
     d'un coup d'œil une panne passagère d'une configuration absente, parce que
     les deux n'appellent pas le même geste. */
  var ECHECS = {
    not_configured: "Rédaction non configurée sur ce serveur",
    modele_indisponible: "Ce modèle-ci n'est pas configuré",
    auth: "Clé d'API refusée par le service",
    busy: "Service saturé — ce n'est pas une panne",
    network: "Service injoignable depuis ce serveur",
    timeout: "Délai dépassé pour ce document",
    /* Nommé par le RÉSULTAT, pas par ce qui s'est cassé chez le fournisseur.
       Ce titre ne s'affiche plus que là où rien n'a pu être produit : quand un
       document sort, la panne ne le concerne pas et ne se montre plus. */
    upstream: "La rédaction automatique n'a pas abouti",
    empty: "Demande vide",
    rate_limited: "Trop de rédactions en peu de temps",
    puissance_absente: "Puissance informatique non renseignée",
    piece_inconnue: "Phase ou pièce inconnue",
    /* Notre propre garde, pas une panne du fournisseur : le dire ainsi évite
       de faire chercher la cause du mauvais côté. */
    sature: "Trop de rédactions en cours sur le serveur",
    modele_indisponible: "Ce modèle-ci n'est pas configuré",
  };

  var REDACTION = null;

  /* L'état de la chaîne de rédaction, affiché AVANT le registre — exactement
     comme celui de l'analyse antivirus avant le dépôt. Celui qui va lancer une
     rédaction a le droit de savoir CE QUI VA SORTIR, et pas seulement si le
     geste aboutit : le modèle et la base se complètent et se remplacent, et
     selon celles qui répondent, la pièce est rédigée ou assemblée.

     Le bandeau annonce donc le MODE, nommé, avant le premier clic. Le document
     le redira en tête — une trame assemblée prise pour une pièce rédigée est
     la seule vraie faute possible ici, et elle se joue au moment où on la
     remet, pas au moment où on la produit. */
  function redactionEtat() {
    var z = $("#ig-red-etat");
    if (!z) return;
    demander("/api/datacenter/redaction/etat", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) { z.innerHTML = ""; return; }
        REDACTION = j.etat;
        var e = j.etat;
        /* Ambre quand aucun modèle n'écrit — c'est une réserve sur la NATURE
           du document, pas une panne. Le rouge d'échec ne s'applique plus :
           il n'y a plus de cas où le registre ne rend rien. */
        z.className = "ig-dep-etat" + (e.modele_disponible ? " fort" : " trame");
        z.innerHTML = '<p class="t"><b>Ce qui écrira ces pièces.</b> '
          + esc(e.resume) + "</p>"
          + '<ul class="l">'
          + "<li>Modèles configurés — "
          + (e.modeles_prets.length ? esc(e.modeles_prets.join(", "))
                                    : "<b>aucun</b>") + "</li>"
          /* Ce que CE lecteur-là peut atteindre, et le total à côté. Annoncer
             la taille de la base à qui n'en verra que la part publique promet
             des sources qui ne viendront pas ; ne rien dire du total lui
             cacherait qu'il peut en demander l'ouverture. */
          + (e.documents_base === null
              ? "<li>Base de connaissance — état indisponible</li>"
              : "<li>Base de connaissance — " + e.documents_base
                + " document" + (e.documents_base > 1 ? "s" : "")
                + " accessible" + (e.documents_base > 1 ? "s" : "")
                + (e.documents_total && e.documents_total !== e.documents_base
                    ? " sur " + e.documents_total : "")
                + " (" + esc(e.corpus_nom || "") + ")"
                + (e.base_vide
                    ? " : les pièces resteront rédigeables, mais ne citeront "
                      + "aucune source." : ".") + "</li>")
          + e.consignes.map(function (c) { return "<li>" + esc(c) + "</li>"; }).join("")
          + "</ul>"
          + '<p class="ig-dep-n"><b>Mode en vigueur — </b>' + esc(e.mode_nom)
          + ". " + esc(e.mode_aide) + "</p>"
          + (e.modele_disponible ? ""
              : '<p class="ig-dep-n"><b>Ce qui reste possible — </b>'
                + esc(e.repli) + "</p>");
        /* Les boutons portent la mention au survol. Ils gardent en revanche le
           bleu : ils PRODUISENT une pièce dans les quatre modes, et les peindre
           en ambre dirait le contraire. Ce que le mode change est la nature du
           document, et cela se lit sur le bandeau puis en tête du document —
           pas sur le bouton, qui ne dit que le geste. */
        document.querySelectorAll("#ig-dossier .ig-gen").forEach(function (b) {
          b.classList.remove("ko");
          if (e.modele_disponible) b.removeAttribute("title");
          else b.setAttribute("title", e.mode_nom + " — " + e.mode_aide);
        });
      })
      .catch(function () { z.innerHTML = ""; });
  }

  /* ── Ce qui manque pour franchir la phase, DÉSIGNÉ dans le formulaire ───
     Le dossier les nomme déjà. Les nommer ne suffit pas : il faut ensuite les
     retrouver parmi treize champs, en remontant la page — et c'est là qu'on
     renonce. Chaque entrée manquante est donc marquée sur le champ lui-même.

     DEUX SIGNAUX, ET ILS NE DISENT PAS LA MÊME CHOSE :

       · Le MARQUAGE est permanent — un liseré ambre et une mention. Il reste
         tant que le champ n'est pas rempli, et il survit à l'arrêt de toute
         animation. C'est lui qui porte l'information.

       · Le BATTEMENT est un rappel, une fois par phase. Il attire l'œil au
         moment où la phase change ; il ne se rejoue pas à chaque frappe, sans
         quoi le formulaire clignoterait pendant toute la saisie.

     La teinte est l'ambre, pas le cyan : le cyan désigne LE geste suivant, un
     seul à la fois. Deux signaux de même couleur pour deux natures d'
     information se confondraient. */
  /* Le groupe des pièces déjà rédigées se signale QUAND IL CHANGE.
     La clé porte le nombre : une pièce de plus rebat une fois, un simple
     redessin ne rebat pas. Le halo est posé sur le titre du groupe et non sur
     chaque carte — quarante halos simultanés ne désigneraient plus rien, et
     c'est le défaut contre lequel tout ce battement a été écrit. */
  function signalerFaits() {
    if (!PLAN || !PLAN.avancement || !PLAN.avancement.faits) return;
    battre("#ig-dossier .g-faits h5", "ig-bat-fait",
           "faits:" + PHASE + ":" + PLAN.avancement.faits);
  }

  function marquerManquants() {
    var form = $("#ig-form");
    if (!form) return;
    form.querySelectorAll(".ig-manque").forEach(function (e) {
      e.classList.remove("ig-manque");
      var m = e.querySelector(".ig-manque-n");
      if (m) m.remove();
    });
    var a = (DOSSIER && DOSSIER.aptitude) || {};
    var liste = a.entrees_manquantes || [];
    var champs = [];
    liste.forEach(function (m) {
      var el = form.querySelector('[data-champ="' + m.id + '"]');
      if (!el) return;
      var lab = el.closest(".dc-champ") || el.parentNode;
      lab.classList.add("ig-manque");
      if (!lab.querySelector(".ig-manque-n")) {
        var n = document.createElement("span");
        n.className = "ig-manque-n";
        /* Le motif du serveur, pas une formule maison : c'est lui qui sait si
           le champ est absent ou resté sur sa valeur par défaut, et les deux
           ne se corrigent pas de la même façon. */
        n.textContent = "Exigé à la phase " + (DOSSIER.code || "") + " — "
          + (m.pourquoi || "non renseigné");
        lab.appendChild(n);
      }
      champs.push(el);
    });
    var b = $("#ig-man-go");
    if (b) {
      b.addEventListener("click", function () {
        var c = champs[0];
        if (!c) return;
        (c.closest(".ig-bloc") || c).scrollIntoView({ behavior: "smooth",
                                                      block: "center" });
        /* On rejoue le battement à la demande : c'est un geste explicite du
           lecteur, pas une animation qui revient toute seule. */
        delete BATTUS["manque:" + DOSSIER.code];
        delete BATTUS["entrees:" + DOSSIER.code];
        setTimeout(function () {
          battre("#ig-form .ig-manque [data-champ]", "ig-bat-man",
                 "manque:" + DOSSIER.code);
          battre("#ig-dossier .ig-man.manq li[data-manque]", "ig-bat-ent",
                 "entrees:" + DOSSIER.code);
          try { c.focus({ preventScroll: true }); } catch (e) { c.focus(); }
        }, 420);
      });
    }
    if (champs.length) {
      /* Une fois par phase. La clé porte le code : changer de phase re-signale,
         retaper dans un champ ne re-signale pas. */
      battre("#ig-form .ig-manque [data-champ]", "ig-bat-man",
             "manque:" + DOSSIER.code);
      /* Les entrées ANNONCÉES dans le dossier battent aussi, à l'endroit où on
         les lit. Marquer le champ sans signaler la liste laisserait le lecteur
         qui parcourt le dossier ignorer qu'il y a quelque chose à faire — et
         c'est le dossier qu'on lit en premier. */
      battre("#ig-dossier .ig-man.manq li[data-manque]", "ig-bat-ent",
             "entrees:" + DOSSIER.code);
    }
    signalerRediger();
  }

  /* Les boutons « Rédiger » des pièces OBLIGATOIRES battent, en bleu.
     Pas tous : le registre en compte quarante, et quarante halos simultanés ne
     désignent plus rien — c'est le défaut contre lequel ce battement a été
     écrit. Les obligatoires forment un ensemble court et cohérent : ce sont
     celles sans lesquelles la phase ne se franchit pas.

     Tous les boutons portent en revanche le bleu en permanence : c'est
     l'action principale du registre, et elle doit se lire comme telle même
     quand plus rien ne bat. */
  function signalerRediger() {
    /* Aucune condition sur le PLAN : il n'existe qu'une fois un projet
       ouvert, alors que le registre s'affiche et se rédige sans projet — le
       document part simplement « non rattaché ». Exiger le plan ici aurait
       éteint le battement dans le seul cas où il sert le plus : celui du
       lecteur qui arrive et n'a encore rien ouvert. */
    var n = document.querySelectorAll(
      "#ig-dossier .ig-c-obligatoire:not(.fait) .ig-gen").length;
    if (!n) return;
    battre("#ig-dossier .ig-c-obligatoire:not(.fait) .ig-gen", "ig-bat-red",
           "rediger:" + PHASE + ":" + n);
  }

  function brancherPieces() {
    var b;
    if ((b = $("#ig-inviter"))) b.addEventListener("click", inviterCollegue);
    if ((b = $("#ig-envoyer-phase"))) {
      b.addEventListener("click", function () { signaler(""); });
    }
    document.querySelectorAll("#ig-dossier .ig-env").forEach(function (e) {
      e.addEventListener("click", function () { signaler(e.getAttribute("data-piece")); });
    });
    document.querySelectorAll("#ig-dossier .ig-visa").forEach(function (e) {
      e.addEventListener("click", function () {
        ouvrirVisa(e.getAttribute("data-l"), e.getAttribute("data-piece"), e);
      });
    });
    brancherSelecteurs();
    railSuite();
    redactionEtat();
    marquerManquants();
    signalerFaits();
    majGuidage();
    planifierVague();
    document.querySelectorAll("#ig-dossier .ig-gen").forEach(function (b) {
      b.addEventListener("click", function () { redigerPiece(b.getAttribute("data-piece"), b); });
    });
    document.querySelectorAll("#ig-dossier .ig-voir").forEach(function (b) {
      b.addEventListener("click", function () { voirBase(b.getAttribute("data-piece"), b); });
    });
    /* On retient ce que le lecteur a ouvert, pièce par pièce : le prochain
       redessin le lui rendra tel quel. */
    document.querySelectorAll("#ig-dossier .ig-pc-f").forEach(function (f) {
      f.addEventListener("toggle", function () {
        var c = f.closest(".ig-pc");
        var code = c && c.getAttribute("data-code");
        if (!code) return;
        if (f.open) FICHES[code] = true; else delete FICHES[code];
        majToutesFiches();
      });
    });
    majToutesFiches();
    var t = $("#ig-fiches-tout");
    if (t) {
      t.addEventListener("click", function () {
        /* Un seul bouton, qui fait l'inverse de l'état courant : deux boutons
           « tout ouvrir » et « tout fermer » auraient laissé l'un des deux
           sans effet la moitié du temps. */
        var fs = document.querySelectorAll("#ig-dossier .ig-pc-f");
        var ouvrir = t.getAttribute("data-etat") !== "ouvert";
        fs.forEach(function (f) {
          f.open = ouvrir;
          var c = f.closest(".ig-pc");
          var code = c && c.getAttribute("data-code");
          if (!code) return;
          if (ouvrir) FICHES[code] = true; else delete FICHES[code];
        });
        majToutesFiches();
      });
    }
  }

  /* ══ COMPORTEMENT DU SÉLECTEUR ════════════════════════════════════════════
     Une liste de sélection n'est utilisable au clavier que si elle rend TOUT ce
     qu'un <select> natif donnait : ouvrir à la flèche, parcourir, revenir au
     bouton par Échap, et trouver en tapant. Un composant qui n'en rend qu'une
     partie est un recul par rapport à l'élément qu'il remplace — c'est le prix
     de l'avoir remplacé, et il se paie ici. */
  function brancherSelecteurs() {
    document.querySelectorAll("#ig-dossier .ig-sel").forEach(function (sel) {
      var bouton = sel.querySelector(".ig-sel-b");
      var panneau = sel.querySelector(".ig-sel-p");
      if (!bouton || !panneau) return;
      var options = Array.prototype.slice.call(panneau.querySelectorAll(".ig-sel-o"));
      if (!options.length) return;
      var actif = -1, frappe = "", minuteur = null;

      function ouvert() { return !panneau.hidden; }

      function ouvrir(depuis) {
        panneau.hidden = false;
        bouton.setAttribute("aria-expanded", "true");
        panneau.focus();
        viser(depuis === "fin" ? options.length - 1 : 0);
      }

      function fermer(rendreFocus) {
        if (!ouvert()) return;
        panneau.hidden = true;
        bouton.setAttribute("aria-expanded", "false");
        panneau.removeAttribute("aria-activedescendant");
        if (actif >= 0) options[actif].setAttribute("aria-selected", "false");
        actif = -1;
        if (rendreFocus) bouton.focus();
      }

      function viser(i) {
        if (i < 0 || i >= options.length) return;
        if (actif >= 0) options[actif].setAttribute("aria-selected", "false");
        actif = i;
        var o = options[i];
        o.setAttribute("aria-selected", "true");
        /* aria-activedescendant plutôt que le focus réel sur l'option : dans
           une liste longue, déplacer le focus fait défiler le document entier
           et le panneau se dérobe sous le curseur. */
        panneau.setAttribute("aria-activedescendant", o.id);
        var pr = panneau.getBoundingClientRect(), orr = o.getBoundingClientRect();
        if (orr.top < pr.top) panneau.scrollTop -= pr.top - orr.top;
        else if (orr.bottom > pr.bottom) panneau.scrollTop += orr.bottom - pr.bottom;
      }

      function choisir(i) {
        if (i < 0 || i >= options.length) return;
        var code = options[i].getAttribute("data-code");
        fermer(false);
        allerALaPiece(code);
      }

      /* LA FRAPPE QUI CHERCHE. Un <select> saute à la première entrée dont le
         libellé commence par la lettre tapée. Ici on cherche aussi dans le
         TITRE et n'importe où dedans : un code de pièce ne se retient pas, et
         un titre commence rarement par le mot qu'on a en tête. La mémoire de
         frappe s'efface après une seconde de silence. */
      function chercher(c) {
        frappe += sansAccent(c);
        clearTimeout(minuteur);
        minuteur = setTimeout(function () { frappe = ""; }, 1000);
        /* Une seule lettre répétée fait avancer d'une correspondance à la
           suivante ; une frappe qui s'allonge réévalue depuis la position
           courante. Repartir toujours du début ramènerait sans cesse à la
           première pièce dont le titre contient la lettre. */
        var depart = (actif < 0 ? -1 : actif) + (frappe.length > 1 ? 0 : 1);
        for (var k = 0; k < options.length; k++) {
          var i = ((depart + k) % options.length + options.length) % options.length;
          if (options[i].getAttribute("data-cherche").indexOf(frappe) >= 0) {
            viser(i);
            return;
          }
        }
      }

      bouton.addEventListener("click", function () {
        if (ouvert()) fermer(true); else ouvrir();
      });
      bouton.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
          e.preventDefault(); ouvrir();
        } else if (e.key === "ArrowUp") {
          e.preventDefault(); ouvrir("fin");
        }
      });

      panneau.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown") { e.preventDefault(); viser(Math.min(actif + 1, options.length - 1)); }
        else if (e.key === "ArrowUp") { e.preventDefault(); viser(Math.max(actif - 1, 0)); }
        else if (e.key === "Home") { e.preventDefault(); viser(0); }
        else if (e.key === "End") { e.preventDefault(); viser(options.length - 1); }
        else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choisir(actif); }
        else if (e.key === "Escape") { e.preventDefault(); fermer(true); }
        else if (e.key === "Tab") { fermer(false); }
        else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
          e.preventDefault(); chercher(e.key);
        }
      });

      panneau.addEventListener("click", function (e) {
        var o = e.target.closest && e.target.closest(".ig-sel-o");
        if (!o) return;
        choisir(options.indexOf(o));
      });
      panneau.addEventListener("mousemove", function (e) {
        var o = e.target.closest && e.target.closest(".ig-sel-o");
        if (o) viser(options.indexOf(o));
      });

      /* Le clic AILLEURS ferme. Sans cela le panneau reste ouvert pendant qu'on
         travaille dans la page, et recouvre les cartes qu'il sert à atteindre. */
      document.addEventListener("click", function (e) {
        if (!sel.contains(e.target)) fermer(false);
      });
    });
  }

  /* ALLER À UNE PIÈCE, C'EST TROIS GESTES : la trouver, ouvrir sa fiche, et
     dire OÙ l'on vient d'arriver. Le troisième est le moins évident et le plus
     nécessaire : après un défilement, une carte parmi cinquante-quatre ne se
     distingue de ses voisines par rien du tout. */
  function allerALaPiece(code) {
    var carte = document.querySelector('#ig-dossier .ig-pc[data-code="'
      + (window.CSS && CSS.escape ? CSS.escape(code) : code) + '"]');
    if (!carte) return;
    var f = carte.querySelector(".ig-pc-f");
    if (f && !f.open) {
      f.open = true;
      FICHES[code] = true;
      majToutesFiches();
    }
    /* Le défilement suit la préférence système. Un saut animé de trente cartes
       est exactement le mouvement que « réduire les animations » demande
       d'éviter, et la CSS ne peut pas l'annuler ici : le comportement est
       demandé par le script. */
    var doux = !(window.matchMedia
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    carte.scrollIntoView({ block: "center", behavior: doux ? "smooth" : "auto" });
    /* Le repère s'efface tout seul. Un surlignage permanent se lirait comme un
       ÉTAT de la pièce — sélectionnée, en cours, à traiter — alors qu'il ne dit
       que « c'est ici que vous venez d'arriver ». */
    carte.classList.remove("ig-vise");
    void carte.offsetWidth;
    carte.classList.add("ig-vise");
    setTimeout(function () { carte.classList.remove("ig-vise"); }, 2200);
  }

  /* Le bouton dit ce qu'il VA faire, pas ce qui est. « Tout replier » sur un
     registre déjà replié est un clic sans effet, et le lecteur en conclut que
     la commande est cassée. */
  function majToutesFiches() {
    var t = $("#ig-fiches-tout");
    if (!t) return;
    var fs = document.querySelectorAll("#ig-dossier .ig-pc-f");
    if (!fs.length) { t.style.display = "none"; return; }
    t.style.display = "";
    var ouvertes = 0;
    fs.forEach(function (f) { if (f.open) ouvertes++; });
    var tout = ouvertes === fs.length;
    t.setAttribute("data-etat", tout ? "ouvert" : "ferme");
    t.textContent = tout ? "Replier les fiches" : "Déplier les fiches";
    t.setAttribute("aria-label", (tout ? "Replier" : "Déplier")
      + " la fiche complète des " + fs.length + " pièces du registre");
  }

  /* Ce que la base rendrait pour cette pièce, AVANT de rédiger. Consulter ne
     consomme rien ; c'est écrire qui coûte. La distinction vaut d'être offerte :
     elle permet de constater que la base est vide, plutôt que de le découvrir
     dans un document qui n'en dit rien. */
  function voirBase(code, bouton) {
    var z = document.querySelector('#ig-dossier .ig-pc-doc[data-doc="' + code + '"]');
    if (!z || !PHASE) return;
    if (z.getAttribute("data-ouvert") === "1") {
      z.innerHTML = ""; z.removeAttribute("data-ouvert");
      bouton.textContent = "Ce que la base apporte"; return;
    }
    var p = lireProfil();
    p.phase = PHASE; p.piece = code;
    bouton.disabled = true;
    z.innerHTML = '<p class="ig-pc-att">Interrogation de la base…</p>';
    demander("/api/datacenter/ingenierie/apercu", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    }, DELAI_MOYEN).then(function (r) { return r.json().then(function (j) { return [r.status, j]; }); })
      .then(function (rj) {
        var st = rj[0], j = rj[1];
        bouton.disabled = false;
        z.setAttribute("data-ouvert", "1");
        bouton.textContent = "Masquer";
        if (st === 401 || st === 403) {
          z.innerHTML = '<p class="ig-pc-att">Connectez-vous pour consulter '
            + "la base documentaire.</p>"; return;
        }
        if (!j || !j.ok) {
          /* Une interrogation EN ÉCHEC et une base VIDE se ressemblent à
             l'écran et n'appellent pas la même réaction. On les distingue. */
          z.innerHTML = '<p class="ig-pc-att err">'
            + esc((j && j.message) || "La base n'a pas pu être interrogée.")
            + " — ce n'est pas la même chose qu'une base sans document sur le "
            + "sujet.</p>"; return;
        }
        var h = '<p class="ig-pc-rqv"><b>Demandé à la base :</b> '
          + esc(j.query || "") + "</p>"
          /* L'ORDRE n'est pas celui de la seule pertinence : la famille du
             sujet passe devant. Sans le dire, un lecteur qui voit un document
             mieux tourné arriver en second croirait à un défaut de
             classement. */
          + (j.famille_prioritaire
              ? '<p class="ig-pc-rqv"><b>Cherché d’abord dans :</b> '
                + esc(j.famille_prioritaire)
                + " — le reste de la base complète ensuite, rien n’est écarté.</p>"
              : "");
        if (!j.documents || !j.documents.length) {
          h += '<p class="ig-pc-att">Aucun document de la base ne traite ce '
            + "sujet. La pièce sera rédigée sans source interne — le document "
            + "produit le dira, et appellera une relecture renforcée.</p>";
        } else {
          h += '<p class="ig-pc-rqv">' + j.documents.length + " document"
            + (j.documents.length > 1 ? "s" : "") + " · " + j.extraits
            + " extrait" + (j.extraits > 1 ? "s" : "") + "</p><ul class=\"ig-pc-dl\">"
            + j.documents.map(function (d) {
                return "<li>" + esc(d.title || "sans titre")
                  + ' <span class="vi">'
                  + (d.visibility === "internal" ? "interne" : "publique")
                  + "</span> <span class=\"ex\">" + d.extraits + " extrait"
                  + (d.extraits > 1 ? "s" : "") + "</span></li>";
              }).join("") + "</ul>";
        }
        z.innerHTML = h;
      }).catch(function () {
        bouton.disabled = false;
        z.setAttribute("data-ouvert", "1");
        bouton.textContent = "Masquer";
        z.innerHTML = '<p class="ig-pc-att err">La base n\'a pas répondu.</p>';
      });
  }

  function redigerPiece(code, bouton) {
    var z = $("#ig-piece");
    if (!z || !PHASE) return;
    var p = lireProfil();
    p.phase = PHASE;
    p.piece = code;
    p.client = (($("#ig-client") || {}).value || "").trim();
    /* Le rattachement au dossier. Envoyé au moment de la rédaction et non
       recollé après coup : un document produit sans projet devrait sinon être
       reclassé à la main, et personne ne le fait. Le serveur vérifie que ce
       projet est bien celui du compte — l'identifiant n'est pas une
       autorisation. */
    p.projet_id = PROJET ? PROJET.id : "";
    p.filiere = FILIERE;
    /* Le niveau de disponibilité visé part avec TOUTES les pièces, pas
       seulement avec le dossier de disponibilité : une spécification CVC
       rédigée sans savoir qu'on vise deux chaînes complètes décrit une
       installation qui n'existera pas. */
    var dsp = lireDisponibilite();
    Object.keys(dsp).forEach(function (k) { if (dsp[k]) p[k] = dsp[k]; });
    /* Les clés d'identification, pas des libellés : c'est le serveur qui sait
       ce que chacune implique, et lui envoyer le texte affiché l'obligerait à
       le réinterpréter. */
    var ident = lireIdentification();
    Object.keys(ident).forEach(function (k) { p[k] = ident[k]; });
    bouton.disabled = true;
    var ancien = bouton.textContent;
    bouton.textContent = "Rédaction…";
    /* LA RÉDACTION EN COURS SE VOIT, ET SUR LES DEUX BLOCS. Elle prend
       plusieurs dizaines de secondes : un bouton grisé au milieu d'un registre
       de trente pièces ne dit pas lequel travaille, et on relance ailleurs en
       croyant que rien ne s'est passé. La fiche de la pièce bat donc en bleu,
       et le bloc de résultat aussi — c'est là que le document arrivera. */
    var carte = bouton.closest ? bouton.closest(".ig-pc") : null;
    if (carte) carte.classList.add("ig-redac");
    z.innerHTML = '<div class="ig-encours" role="status">'
      + '<span class="pt">Rédaction en cours</span>'
      + "<b>" + esc(code) + "</b>"
      + '<span class="qu">Le moteur assemble le document à partir du calcul '
      + "et de la base de connaissance. Quelques dizaines de secondes.</span>"
      + "</div>";
    z.scrollIntoView({ behavior: "smooth", block: "nearest" });
    /* La porte du CLIENT. Elle était administrateur, et tout le registre — le
       battement, les flèches, le fil des gestes — conduisait un lecteur
       ordinaire vers un refus. La rédaction lui est ouverte ; ce qui reste
       réservé est le corpus interne de la base, pas le geste. */
    demander("/api/datacenter/piece", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    }, DELAI_LONG)
      .then(function (r) { return r.json().then(function (j) { return { s: r.status, j: j }; }); })
      .then(function (o) {
        bouton.disabled = false;
        bouton.textContent = ancien;
        /* Le battement s'arrête dès que la rédaction rend la main, QUELLE QUE
           SOIT l'issue. Laissé sur un refus, il annoncerait indéfiniment un
           travail qui ne viendra pas. */
        if (carte) carte.classList.remove("ig-redac");
        if (!o.j.ok) {
          /* L'échec est affiché SUR LA PIÈCE, avec sa cause, ce qui reste
             possible et — seulement s'il en existe un — le modèle de repli.
             Un « la génération a échoué » sec fait réessayer à l'identique :
             c'est le pire des retours, celui qui coûte deux fois. */
          var admin = o.s === 403;
          var titre = admin ? "Rédaction réservée à l'administrateur"
                            : (ECHECS[o.j.error] || "La rédaction n'a pas abouti");
          z.innerHTML = '<div class="ig-ech"><div class="ig-ech-t">'
            + '<span class="fx">✕</span><b>' + esc(titre) + "</b>"
            + (o.j.error ? '<code>' + esc(o.j.error) + "</code>" : "") + "</div>"
            + "<p>" + esc(admin
                ? "Le registre ci-dessus reste consultable, et l'étude de phase "
                  + "s'exporte en Word et en PDF sans passer par la rédaction."
                : (o.j.message || "Cause non qualifiée par le serveur.")) + "</p>"
            + (o.j.repli ? '<p class="rp">' + esc(o.j.repli) + "</p>" : "")
            + "</div>";
          /* L'état affiché en tête du registre est rafraîchi : si la cause est
             une configuration absente, le bandeau doit cesser d'annoncer une
             rédaction disponible. */
          redactionEtat();
          return;
        }
        z.innerHTML = ""
          /* NOS PANNES NE SONT PAS UNE NOUVELLE POUR LE LECTEUR. Un document
             est là, complet, enregistré au dossier ; le surmonter d'un
             bandeau rouge sur le service d'IA ne lui apprend rien qu'il puisse
             faire, et jette un doute sur ce qui suit — alors que rien n'y
             manque.
             La seule question qui le concerne est QUI A ÉCRIT ce document, et
             le bandeau de mode y répond déjà, nommément. Le reste — le code
             d'échec, le modèle tenté, le message — part dans la réponse de
             l'API et dans le journal du serveur, où il se diagnostique. */
          /* LE BLOC ENTIER SIGNALE QU'IL Y A QUELQUE CHOSE À LIRE. Il
             apparaissait au bas d'une page longue, du même gris que le reste
             du registre : rien ne disait que le document était sorti, et la
             rédaction se relançait sur une pièce déjà écrite. Il bat donc en
             bleu clair tant que personne ne l'a ouvert, et se calme dès qu'on
             le lit ou qu'on l'emporte. */
          + '<div class="ig-doc neuf" id="ig-pc-bloc">'
          + bandeauEtat(o.j)
          + '<div class="ig-doc-h">'
          /* « Brouillon rédigé » sur une trame assemblée serait faux dès la
             première ligne, et c'est cette ligne-là qu'on recopie en tête de
             dossier. Le mot suit ce que le document est. */
          + "<b>" + esc(code) + "</b> — "
          + (o.j.sans_modele ? "trame assemblée" : "brouillon rédigé")
          + (o.j.model ? " · " + esc(o.j.model) : "")
          + ((o.j.sources || []).length
              ? " · " + o.j.sources.length + " document"
                + (o.j.sources.length > 1 ? "s" : "") + " de la base cité"
                + (o.j.sources.length > 1 ? "s" : "")
                /* D'où l'on a puisé EN PREMIER. Le document liste ses sources
                   dans cet ordre-là, et non dans celui de la seule
                   pertinence : le dire évite de le prendre pour un défaut. */
                + (o.j.famille_prioritaire
                    ? " · « " + esc(o.j.famille_prioritaire) + " » d'abord" : "")
              : " · aucun document de la base n'a été retrouvé")
          /* Dire où le document a ATTERRI, et le dire aussi quand il n'a
             atterri nulle part : c'est la seule occasion où le lecteur peut
             encore ouvrir un projet et recommencer. */
          + (PROJET ? " · rattaché au projet " + esc(PROJET.nom)
                    : " · non rattaché — aucun projet n'est ouvert")
          + "</div>"
          /* LE MODE, en tête du document et non en note. Une trame assemblée
             présentée comme une pièce rédigée serait la seule vraie faute
             ici : elle se remettrait au client telle quelle. */
          /* LE LIVRABLE, PAS SON TEXTE. Le document s'affichait en entier,
             brut, dans la page : dix mille signes de Markdown déroulés sous
             le registre. On n'y lit rien et on n'en fait rien — un livrable
             se relit dans un traitement de texte, se corrige, se vise, et
             part au dossier. Ce qui doit être ici, c'est de quoi le PRENDRE
             et de quoi le LIRE, pas le texte lui-même. */
          + '<div class="ig-doc-a"><span class="lb">Emporter&nbsp;:</span>'
          + '<button type="button" id="ig-pc-lire">Lire</button>'
          + '<button type="button" id="ig-pc-docx">Word</button>'
          + '<button type="button" id="ig-pc-pdf">PDF</button>'
          + '<button type="button" id="ig-pc-xlsx">Excel</button>'
          + '<button type="button" id="ig-pc-md">Markdown</button>'
          + '<span class="dit" id="ig-pc-dit" aria-live="polite"></span></div>'
          + (o.j.mode
              ? '<div class="ig-mode' + (o.j.sans_modele ? " brut" : "") + '">'
                + '<b>' + esc(o.j.mode_nom) + "</b> "
                + esc(o.j.mode_aide) + "</div>"
              : "")
          + ficheLivrable(o.j, code)
          + "</div>";
        brancherEmport(p, code, o.j);
        if (PROJET) pjHistorique(PROJET.id);
      })
      .catch(function () {
        bouton.disabled = false;
        bouton.textContent = ancien;
        if (carte) carte.classList.remove("ig-redac");
        z.innerHTML = '<p class="note">Rédaction indisponible pour le moment.</p>';
      });
  }

  /* ── EMPORTER LA PIÈCE ────────────────────────────────────────────────

     Word et PDF passent par le serveur : c'est lui qui porte l'en-tête, la
     police et la mise en page — les mêmes que l'étude de phase, pour que deux
     documents du même dossier ne se ressemblent pas de loin seulement.

     Markdown part du navigateur, sans aller-retour : le texte est déjà là, et
     c'est la forme qui se recolle ailleurs sans rien perdre.

     Ce qui est envoyé au serveur est le document AFFICHÉ, pas le code de la
     pièce : celui-ci a pu être rédigé par le modèle. Le reconstruire depuis le
     registre rendrait un autre document que celui qu'on a sous les yeux. */
  /* CE QUE PÈSE LE LIVRABLE, ET CE QU'IL DEVIENT.

     Un document se juge d'abord à ce qu'il est : combien de pages, combien de
     chapitres, sur quelles sources, et ce qu'il reste à en faire. Le lire en
     entier vient APRÈS — et se fait dans le lecteur, ou dans le Word. */
  /* CE QUE LE DOCUMENT EST, ET CE QU'IL ATTEND. Deux faits, en tête du bloc
     et avant tout le reste : il est sorti, et personne ne l'a encore ouvert.

     « Rédigé » sur une trame assemblée serait faux dès le premier mot — et
     c'est ce mot-là qu'on recopie en tête de dossier. Le verbe suit donc ce
     que le document EST ; « généré » et « en attente de lecture » valent, eux,
     dans les deux cas. */
  function bandeauEtat(j) {
    return '<div class="ig-doc-e" id="ig-pc-etat" role="status">'
      + '<span class="pt">En attente de lecture</span>'
      + "<b>Document " + (j.sans_modele ? "composé par le moteur et généré"
                                        : "rédigé et généré") + ".</b>"
      + '<span class="qu">Personne ne l\'a encore ouvert. Lisez-le ici, ou '
      + "emportez-le en Word : c'est là que les corrections se font.</span>"
      + "</div>";
  }

  /* LE BATTEMENT S'ARRÊTE QUAND IL A FAIT SON OFFICE. Le garder après
     l'ouverture ferait ignorer le suivant — et un clignotement qu'on ne peut
     pas arrêter est une gêne, pas un signal. Les quatre boutons d'emport
     l'arrêtent, chacun en disant ce qui a été fait. */
  function marquerLu(quoi) {
    var b = $("#ig-pc-bloc");
    if (!b || b.classList.contains("lu")) return;
    b.classList.remove("neuf");
    b.classList.add("lu");
    var e = $("#ig-pc-etat");
    if (e) {
      e.innerHTML = '<span class="pt">Lu</span><b>' + esc(quoi) + "</b>"
        + '<span class="qu">Il reste à le relire, le corriger, puis le faire '
        + "viser pour qu'il parte au dossier.</span>";
    }
  }

  function ficheLivrable(j, code) {
    var md = j.document || "";
    var m = (window.CPMarkdown && CPMarkdown.mesurer)
      ? CPMarkdown.mesurer(md)
      : { pages: 1, chapitres: 0, signes: md.length };
    var srcs = (j.sources || []).length;
    var faits = [
      "environ " + m.pages + " page" + (m.pages > 1 ? "s" : ""),
      m.chapitres + " chapitre" + (m.chapitres > 1 ? "s" : ""),
      srcs ? (srcs + " document" + (srcs > 1 ? "s" : "") + " de la base cité"
              + (srcs > 1 ? "s" : ""))
           : "aucun document de la base retrouvé",
    ];
    return '<div class="ig-liv">'
      + '<div class="ig-liv-t"><span class="pt">Livrable prêt</span> '
      + esc(code) + "</div>"
      + '<div class="ig-liv-f">' + faits.map(esc).join(" · ") + "</div>"
      /* LA SUITE, écrite ici et pas ailleurs : c'est le moment où on la
         décide. Un livrable qui apparaît sans qu'on dise ce qu'il reste à en
         faire finit relu par personne — et versé au dossier tel quel. */
      + '<ol class="ig-liv-s"><li>Relire et corriger — dans le Word, c\'est '
      + "là que les corrections se font.</li>"
      + "<li>Faire accepter, puis viser — le visa dit qui a validé, et "
      + "bloque la remise s'il est refusé.</li>"
      + "<li>Une fois visé, il est versé au dossier du projet, dans sa "
      + "phase.</li></ol>"
      + '<div class="ig-liv-d">'
      + (PROJET
          ? "Rattaché au projet <b>" + esc(PROJET.nom) + "</b>"
            + (PHASE ? ", phase <b>" + esc(PHASE) + "</b>" : "")
            + ". Il figure au dossier ci-dessous, à l'état « brouillon » "
            + "jusqu'à son visa."
          : "<b>Aucun projet n'est ouvert</b> : ce document n'est rattaché à "
            + "aucun dossier. Emportez-le maintenant, ou ouvrez un projet et "
            + "relancez la rédaction pour qu'il y soit classé.")
      + "</div></div>";
  }

  /* LE LECTEUR. Le document reste lisible sur le site — mais dans un espace
     qui lui est propre, mis en forme, et qu'on ferme. Il n'encombre plus le
     registre, qui sert à choisir la pièce suivante. */
  function lireDocument(md, titre) {
    var d = $("#ig-lecteur");
    if (!d) {
      d = document.createElement("dialog");
      d.id = "ig-lecteur";
      d.className = "ig-lec";
      document.body.appendChild(d);
    }
    var html = (window.CPMarkdown && CPMarkdown.versHtml)
      ? CPMarkdown.versHtml(md)
      /* Sans le moteur de rendu — fichier non chargé — on montre le texte
         plutôt que rien : un lecteur vide serait pire qu'un texte brut. */
      : "<pre>" + esc(md) + "</pre>";
    d.innerHTML = '<div class="ig-lec-h"><b>' + esc(titre || "Document")
      + '</b><button type="button" class="x" id="ig-lec-x" '
      + 'aria-label="Fermer le lecteur">Fermer</button></div>'
      + '<article class="ig-lec-c">' + html + "</article>";
    var x = $("#ig-lec-x");
    if (x) x.addEventListener("click", function () { d.close(); });
    if (d.showModal) d.showModal(); else d.setAttribute("open", "");
    var c = d.querySelector(".ig-lec-c");
    if (c) c.scrollTop = 0;
    if (x) x.focus();
  }

  function telecharger(blob, nom) {
    var u = URL.createObjectURL(blob), a = document.createElement("a");
    a.href = u;
    a.download = nom;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
  }

  function brancherEmport(profil, code, j) {
    var dit = $("#ig-pc-dit");
    var nom = (code || "piece").toLowerCase().replace(/[^a-z0-9-]+/g, "-");
    function note(m, ko) {
      if (dit) {
        dit.textContent = m || "";
        dit.style.color = ko ? "var(--danger)" : "";
      }
    }
    var lire = $("#ig-pc-lire");
    if (lire) {
      lire.addEventListener("click", function () {
        lireDocument(j.document || "", code + " — lecture");
        marquerLu("Ouvert dans le lecteur.");
      });
    }
    var md = $("#ig-pc-md");
    if (md) {
      md.addEventListener("click", function () {
        telecharger(new Blob([j.document || ""],
                             { type: "text/markdown;charset=utf-8" }),
                    nom + ".md");
        note("Markdown enregistré.");
        marquerLu("Emporté en Markdown.");
      });
    }
    /* Le document vient d'arriver : c'est l'instant où ces boutons ont
       quelque chose à dire. Les faire battre plus tôt aurait désigné des
       commandes sans objet. */
    battre(".ig-doc-a button", "ig-bat-doc", "emport");
    [["#ig-pc-docx", "docx", "Word"], ["#ig-pc-pdf", "pdf", "PDF"],
     ["#ig-pc-xlsx", "xlsx", "Excel"]]
      .forEach(function (t) {
        var b = $(t[0]);
        if (!b) return;
        b.addEventListener("click", function () {
          var tous = [$("#ig-pc-docx"), $("#ig-pc-pdf"), $("#ig-pc-xlsx")];
          tous.forEach(function (x) { if (x) x.disabled = true; });
          note("Mise en page " + t[2] + "…");
          var corps = {};
          Object.keys(profil || {}).forEach(function (k) { corps[k] = profil[k]; });
          corps.markdown = j.document || "";
          corps.format = t[1];
          corps.model = j.model || "";
          corps.sources = j.sources || [];
          /* Le cartouche du Word et du PDF : numéro et indice viennent du
             serveur au moment de la rédaction. Les recalculer ici donnerait un
             numéro à l'écran et un autre sur le document. */
          corps.numero = j.numero || "";
          corps.indice = j.indice || "";
          demander("/api/datacenter/piece/export", {
            method: "POST", credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(TR(corps)),
          }, DELAI_MOYEN)
            .then(function (r) {
              if (!r.ok) {
                /* La cause vient du serveur quand il la donne : « la mise en
                   page a échoué » sans un mot de plus fait recommencer à
                   l'identique. */
                return r.json().catch(function () { return {}; })
                  .then(function (e) { throw new Error(e.message || ""); });
              }
              return r.blob();
            })
            .then(function (bl) {
              telecharger(bl, nom + "." + t[1]);
              note(t[2] + " enregistré.");
              marquerLu("Emporté en " + t[2] + ".");
            })
            .catch(function (e) {
              note(String(e.message || "").trim()
                   || "La mise en page a échoué. Le Markdown reste "
                      + "téléchargeable.", true);
            })
            .then(function () {
              tous.forEach(function (x) { if (x) x.disabled = false; });
            });
        });
      });
  }

  /* ── Les correspondances entre filières ──────────────────────────────── */
  function rendreCorrespondances() {
    var C = CADRE.correspondances || [];
    var h = '<div class="ig-tab-wrap"><table class="ig-tab"><thead><tr>'
      + "<th>Maîtrise d'œuvre</th><th>Ingénierie</th><th>Accord</th>"
      + "<th>Ce qui les sépare</th></tr></thead><tbody>";
    C.forEach(function (c) {
      h += "<tr><td><code>" + esc(c.moe) + "</code></td><td><code>" + esc(c.indus)
        + "</code></td><td><span class='ig-acc a-" + esc(c.accord) + "'"
        + info("accord:" + c.accord) + ">" + esc(c.accord)
        + "</span></td><td>" + esc(c.ecart) + "</td></tr>";
    });
    $("#ig-correspondances").innerHTML = h + "</tbody></table></div>";
  }

  /* ── Les appels ──────────────────────────────────────────────────────── */
  var _minuteur = null, _vol = null;

  function rafraichir() {
    if (_minuteur) clearTimeout(_minuteur);
    _minuteur = setTimeout(function () {
      var p = lireProfil();
      if (!p.puissance_it_kw) {
        DERNIER = null;
        /* C'est ICI que le message était le plus faux : on venait d'effacer la
           frise faute de puissance, et la ligne suivante invitait à y choisir
           une phase. `rendreParcours` pose désormais lui-même le message des
           deux zones. */
        rendreParcours();
        boutons(false);
        return;
      }
      /* La requête précédente est annulée : sans cela, deux frappes rapprochées
         font revenir les réponses dans l'ordre du réseau, et la frise affiche
         l'avant-dernier profil. */
      if (_vol) { try { _vol.abort(); } catch (e) {} }
      _vol = (typeof AbortController !== "undefined") ? new AbortController() : null;
      etat("");
      demander("/api/datacenter/ingenierie/parcours", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(p),
        signal: _vol ? _vol.signal : undefined,
        // Annulé VOLONTAIREMENT par la frappe suivante : sans ce drapeau,
        // chaque caractère tapé afficherait « délai dépassé ».
        __annule: true,
      }, DELAI_MOYEN)
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (!j.ok) throw new Error(j.message || "parcours");
          DERNIER = j.parcours;
          rendreParcours();
          /* CE QUI N'A PAS ÉTÉ LU SE DIT ICI. Sans cela le résultat est exact
             et trompeur : identique à celui d'une saisie valide. Mesuré,
             « 75 % » tapé dans un champ noté « 0–1 » produisait un parcours
             complet calculé sur la valeur par défaut, sans un mot. */
          marquerRejets(j.rejets);
          etat(j.lecture_rejets || "", !!j.lecture_rejets);
          if (PHASE) chargerDossier();
        })
        .catch(function (e) {
          if (e && e.name === "AbortError") return;
          if (e && e.name === "SessionEteinte") return;   /* la bannière l'a dit */
          /* LA PANNE S'ÉCRIT LÀ OÙ LE LECTEUR REGARDE. Le message n'allait
             qu'au pied du formulaire (section 2) ; la frise, elle, continuait
             de réclamer une puissance déjà saisie, et le dossier (section 4)
             d'attendre — la page semblait morte à partir de là, sans un mot. */
          var msg = messageDelai(e,
            "Le parcours n'a pas pu être établi. Réessayez dans un instant.");
          etat(msg, true);
          var zp = $("#ig-parcours");
          if (zp) zp.innerHTML = '<p class="ig-dep-ko">' + esc(msg)
            + ' <button type="button" class="ig-vers" data-relancer>Relancer</button></p>';
          var zd = $("#ig-dossier");
          if (zd) zd.innerHTML = '<p class="note">L’étude de phase suivra dès '
            + "que le parcours ci-dessus aura pu être établi.</p>";
        });
    }, 280);
  }

  /* Pièce demandée par l'URL, mise en évidence une fois le registre rendu —
     et une seule fois : au clic suivant sur une autre phase, le lecteur ne
     cherche plus cette pièce-là. */
  var PIECE_VISEE = null;

  function chargerDossier() {
    if (!PHASE) return;
    var p = lireProfil();
    p.phase = PHASE;
    demander("/api/datacenter/ingenierie/dossier", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    }, DELAI_MOYEN)
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) throw new Error(j.message || "dossier");
        if (!j.dossier.disponible) {
          $("#ig-dossier").innerHTML = '<p class="note">' + esc(j.dossier.motif) + "</p>";
          boutons(false);
          return;
        }
        DOSSIER = j.dossier;
        /* Le plan d'abord, le rendu ensuite : dessiner le registre nu puis le
           redessiner annoté le ferait clignoter, et un lecteur qui voit une
           liste changer sous ses yeux se demande laquelle est la bonne. */
        planPuisRendre(j.dossier);
      })
      .catch(function (e) {
        if (e && e.name === "SessionEteinte") { boutons(false); return; }
        $("#ig-dossier").innerHTML = '<p class="note">'
          + esc(messageDelai(e, "Dossier indisponible pour le moment."))
          + "</p>";
        boutons(false);
      });
  }

  function planPuisRendre(d) {
    var fini = function () {
      rendreDossier(d);
      /* La cible n'est oubliée QUE si elle a été trouvée. Le premier dessin du
         registre peut arriver avant que le profil soit complet — il est alors
         vide, et effacer la cible à ce moment perdait le lien : le lecteur
         arrivait sur la page qu'il avait demandée, sans la pièce qu'il venait
         y lire. */
      if (PIECE_VISEE && viserPiece(PIECE_VISEE)) PIECE_VISEE = null;
    };
    if (!PROJET || !PHASE) { PLAN = null; fini(); return; }
    var p = lireProfil();
    p.phase = PHASE;
    var ident = lireIdentification();
    Object.keys(ident).forEach(function (k) { p[k] = ident[k]; });
    demander("/api/datacenter/projets/" + PROJET.id + "/plan", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        PLAN = (j.ok && j.disponible) ? j : null;
        if (PLAN && PLAN.etats_visa && CADRE) {
          CADRE.glossaire = CADRE.glossaire || {};
          CADRE.glossaire.visa = PLAN.etats_visa;
        }
      })
      .catch(function () { PLAN = null; })
      .then(fini);
  }

  /* Où atterrit un lecteur venu de la page de calcul.

     Sur la PREMIÈRE PHASE QUI BLOQUE, et sur elle seule. C'est la seule
     information que le cadre produise et qui commande une action : les phases
     antérieures sont franchies, les suivantes ne se travaillent pas encore. Y
     conduire d'emblée épargne le clic que tout le monde fait de toute façon.

     Trois conditions, et la troisième compte : la reprise a eu lieu, aucune
     phase n'est déjà choisie, et l'URL n'en imposait pas. Un lien profond
     « #phase=DCE » exprime une intention plus précise que la nôtre — la
     recouvrir ferait atterrir le lecteur ailleurs qu'où il a demandé. */
  var ATTERRI = false;

  function atterrir() {
    if (ATTERRI || !REPRIS || PHASE) return;
    if (/[#&]phase=/.test(window.location.hash || "")) { ATTERRI = true; return; }
    var d = DERNIER && DERNIER[FILIERE];
    if (!d) return;
    var cible = d.premier_blocage
      || (d.phases && d.phases.length ? d.phases[0].code : null);
    if (!cible) return;
    ATTERRI = true;
    PHASE = cible;
    rafraichir();
  }

  function boutons(actif) {
    ["#ig-docx", "#ig-pdf", "#ig-xlsx"].forEach(function (s) {
      var b = $(s);
      if (b) b.disabled = !actif;
    });
    /* Les exports viennent de devenir possibles : c'est l'instant où le
       battement a quelque chose à dire. Avant, il aurait désigné des boutons
       inactifs — une promesse que le clic n'aurait pas tenue. */
    if (actif) battre("#ig-docx, #ig-pdf, #ig-xlsx", "ig-bat-doc", "export");
  }

  function exporter(fmt) {
    if (!PHASE) return;
    var p = lireProfil();
    p.phase = PHASE;
    p.format = fmt;
    etat("Mise en page de l'étude " + PHASE + "…");
    demander("/api/datacenter/ingenierie/export", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(TR(p)),
    }, DELAI_MOYEN)
      .then(function (r) {
        if (!r.ok) throw new Error("export");
        return r.blob();
      })
      .then(function (b) {
        var u = URL.createObjectURL(b), a = document.createElement("a");
        a.href = u;
        a.download = "etude-" + PHASE.toLowerCase() + "." + fmt;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
        etat("");
      })
      .catch(function () { etat("La mise en page a échoué.", true); });
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE PARCOURS GUIDÉ — par rôle et par thème

     Trois états, et un seul visible à la fois : le CHOIX (qui êtes-vous, ce
     qui vous amène), puis les ÉTAPES, une par section de la page. On ne
     déroule pas les cinq étapes d'un coup : une étape à l'écran, celle de la
     section où l'on se trouve, sinon le parcours redevient la table des
     matières qu'il est censé remplacer.

     Le parcours ne DÉPLACE rien et ne masque rien de la page : il fait
     défiler vers la section concernée et la met en relief. Une page qui se
     réorganise sous le lecteur lui fait perdre ce qu'il venait de lire. */
  /* GUIDE_THEMES EST UN TABLEAU, PAS UN SCALAIRE : « qu'est-ce qui vous
     amène » admet plusieurs réponses — un projet arrive rarement pour
     l'énergie SEULE, sans l'eau ni le coût qui vont avec. Le rôle, lui,
     reste unique : on répond à la question depuis UNE position sur le
     projet, pas plusieurs à la fois. */
  var GUIDE = null, GUIDE_ETAPE = 0, GUIDE_ROLE = null, GUIDE_THEMES = [];

  function guideZone() { return $("#ig-guide"); }

  function guideOuvrir(ouvert) {
    var z = guideZone(), b = $("#ig-lanceur-b");
    if (!z || !b) return;
    z.hidden = !ouvert;
    b.setAttribute("aria-expanded", ouvert ? "true" : "false");
    b.textContent = ouvert ? "Fermer le parcours" : "Ouvrir le parcours guidé";
    if (!ouvert) { guideSurligner(null); GUIDE = null; GUIDE_ETAPE = 0; }
  }

  /* Mettre en relief la section visée. Une seule à la fois, et on retire la
     précédente : deux sections en relief ne désignent plus rien. */
  function guideSurligner(ancre) {
    document.querySelectorAll(".ig-vise").forEach(function (e) {
      e.classList.remove("ig-vise");
    });
    if (!ancre) return;
    var el = document.getElementById(ancre);
    if (!el) return;
    var sec = el.closest("section") || el;
    sec.classList.add("ig-vise");
  }

  /* Le numéro de section, lu LÀ OÙ IL S'AFFICHE.

     LE DÉFAUT CORRIGÉ. Le serveur servait ce numéro, écrit à la main dans une
     table. La page en a gagné huit sections ; les cinq numéros servis sont
     alors devenus faux — le profil annoncé « section 1 » quand la page
     l'affiche en 2, les limites annoncées « section 5 » quand elle les affiche
     en 13. Deux endroits pour un même nombre, c'était garantir qu'ils
     divergeraient.

     Le nombre vit désormais à un seul endroit : la puce de la section. On
     remonte de l'ancre à sa section, on lit sa puce, et un renumérotage suit
     tout seul. Faute de puce, on ne dit rien plutôt qu'un numéro inventé. */
  function guideSection(ancre) {
    var el = document.getElementById(ancre);
    if (!el) return null;
    var sec = el.closest("section");
    var n = sec && sec.querySelector(".rc-etape .n");
    var t = n && (n.textContent || "").trim();
    return t || null;
  }

  function guideChoix() {
    var roles = (CADRE && CADRE.guide_roles) || [];
    var themes = (CADRE && CADRE.guide_themes) || [];
    var h = '<div class="ig-g-choix"><p class="ig-g-q">Qui êtes-vous sur ce projet&nbsp;?</p>'
      + '<div class="ig-g-liste" role="group" aria-label="Rôle">'
      + roles.map(function (r) {
          /* La couleur est portée par une variable CSS locale : le style dit
             comment s'en servir (filet, pastille, fond), la donnée dit
             laquelle. Écrire ici « border-color: … » figerait l'usage. */
          return '<button type="button" class="ig-g-c'
            + (GUIDE_ROLE === r.id ? " on" : "") + '" data-role="' + esc(r.id)
            + '" style="--c:' + esc(r.couleur || "var(--cyan)") + '">'
            + '<span class="ic" aria-hidden="true">' + esc(r.icone) + "</span>"
            + '<span class="nm">' + esc(r.nom) + "</span>"
            + '<span class="qs">' + esc(r.question) + "</span></button>";
        }).join("")
      + '</div><p class="ig-g-q">Et qu\'est-ce qui vous amène&nbsp;? '
      + '<span class="ig-g-plu">Choisissez-en plusieurs si plusieurs vous '
      + "concernent.</span></p>"
      /* aria-multiselectable, PAS role="radiogroup" : la sémantique doit
         dire au lecteur d'écran que plusieurs boutons peuvent rester
         enfoncés à la fois — un radiogroup promettrait un seul choix
         possible et contredirait ce que le clic permet réellement. */
      + '<div class="ig-g-liste th" role="group" aria-label="Thèmes" '
      + 'aria-multiselectable="true">'
      + themes.map(function (t) {
          var choisi = GUIDE_THEMES.indexOf(t.id) >= 0;
          return '<button type="button" class="ig-g-c' + (choisi ? " on" : "")
            + '" data-theme="' + esc(t.id) + '" aria-pressed="'
            + (choisi ? "true" : "false") + '" style="--c:'
            + esc(t.couleur || "var(--cyan)") + '">'
            + '<span class="ic" aria-hidden="true">' + esc(t.icone) + "</span>"
            + '<span class="nm">' + esc(t.nom) + "</span>"
            + '<span class="qs">' + esc(t.question) + "</span></button>";
        }).join("")
      + "</div>";
    /* Le bouton n'apparaît QUE lorsque les deux choix sont faits : un bouton
       présent mais inopérant se lit comme une panne. */
    h += GUIDE_ROLE && GUIDE_THEMES.length
      ? '<div class="ig-g-go"><button type="button" class="ig-g-b" id="ig-g-go">'
        + "Commencer le parcours →</button></div>"
      : '<p class="ig-g-att">Choisissez un rôle et au moins un thème pour '
        + "commencer.</p>";
    return h + "</div>";
  }

  function guideRendreChoix() {
    var z = guideZone();
    if (!z) return;
    z.innerHTML = guideChoix();
    z.querySelectorAll("[data-role]").forEach(function (b) {
      b.addEventListener("click", function () {
        GUIDE_ROLE = b.getAttribute("data-role"); guideRendreChoix();
      });
    });
    z.querySelectorAll("[data-theme]").forEach(function (b) {
      b.addEventListener("click", function () {
        var id = b.getAttribute("data-theme");
        var i = GUIDE_THEMES.indexOf(id);
        // BASCULE, PAS REMPLACEMENT : un thème déjà choisi se retire au
        // second clic, comme n'importe quelle case à cocher — remplacer la
        // sélection entière ferait perdre les autres thèmes déjà choisis.
        if (i >= 0) GUIDE_THEMES.splice(i, 1); else GUIDE_THEMES.push(id);
        guideRendreChoix();
      });
    });
    /* La carte retenue bat un instant, dans SA couleur. C'est la confirmation
       du choix — sans elle, cliquer une carte parmi onze ne produit qu'un
       changement de bordure, qu'on manque quand le regard est ailleurs. Deux
       cycles seulement : une confirmation n'a pas à durer neuf secondes. */
    z.querySelectorAll(".ig-g-c.on").forEach(function (b) {
      b.classList.remove("ig-g-choisi");
      void b.offsetWidth;               // force le redémarrage de l'animation
      b.classList.add("ig-g-choisi");
    });
    var g = $("#ig-g-go");
    if (g) {
      g.addEventListener("click", guideCharger);
      /* Le bouton n'existe qu'une fois les deux choix faits : son apparition
         EST l'information, et le battement la souligne. Le groupe est
         réarmé à chaque fois qu'on revient au choix — c'est un nouveau
         départ, pas une répétition. */
      delete BATTUS["guide"];
      battre("#ig-g-go", "ig-bat", "guide");
    }
  }

  function guideCharger() {
    var z = guideZone();
    if (!z || !GUIDE_ROLE || !GUIDE_THEMES.length) return;
    var p = lireProfil();
    p.role = GUIDE_ROLE; p.themes = GUIDE_THEMES;
    if (PHASE) p.phase = PHASE;
    z.innerHTML = '<p class="ig-g-att">Établissement du parcours…</p>';
    demander("/api/datacenter/ingenierie/guide", {
      method: "POST", headers: { "Content-Type": "application/json" },
      credentials: "same-origin", body: JSON.stringify(p),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) {
          z.innerHTML = '<p class="ig-g-att err">'
            + esc((j && j.message) || "Le parcours n'a pas pu être établi.")
            + ' <button type="button" class="ig-g-lien" id="ig-g-retour">Revenir au choix</button></p>';
          var rb = $("#ig-g-retour");
          if (rb) rb.addEventListener("click", guideRendreChoix);
          return;
        }
        GUIDE = j.guide; GUIDE_ETAPE = 0;
        guideRendreEtape();
      }).catch(function () {
        z.innerHTML = '<p class="ig-g-att err">Le parcours n\'a pas répondu.</p>';
      });
  }

  function guideRendreEtape() {
    var z = guideZone();
    if (!z || !GUIDE) return;
    var e = GUIDE.etapes[GUIDE_ETAPE];
    var n = GUIDE.etapes.length;
    /* Le panneau porte les DEUX couleurs du parcours choisi : celle du rôle en
       filet de gauche, celle du PREMIER thème sur la jauge — un dégradé
       mêlant jusqu'à six couleurs serait moins lisible qu'un seul accent, et
       l'ordre vient du catalogue, pas du clic, donc « premier thème » ne
       bouge pas d'une bascule à l'autre. Le lecteur reconnaît son parcours
       d'un coup d'œil, sans relire l'en-tête. */
    var sec = guideSection(e.ancre);
    var cr = (GUIDE.role && GUIDE.role.couleur) || "var(--cyan)";
    var ct = (GUIDE.themes[0] && GUIDE.themes[0].couleur) || "var(--cyan)";
    var h = '<div class="ig-g-p" style="--cr:' + esc(cr) + ";--ct:" + esc(ct) + '">'
      + '<div class="ig-g-h"><span class="ig-g-rt">'
      + '<span aria-hidden="true">' + esc(GUIDE.role.icone) + "</span> "
      + esc(GUIDE.role.nom) + " · "
      + GUIDE.themes.map(function (t) {
          return '<span aria-hidden="true">' + esc(t.icone) + "</span> "
            + esc(t.nom);
        }).join(" · ") + "</span>"
      + '<button type="button" class="ig-g-lien" id="ig-g-changer">Changer</button>'
      + '<button type="button" class="ig-g-lien" id="ig-g-fermer">Fermer</button></div>'
      /* La barre d'avancement : savoir combien il reste change la disposition
         à continuer. */
      + '<div class="ig-g-jauge" role="progressbar" aria-valuemin="1" aria-valuemax="'
      + n + '" aria-valuenow="' + (GUIDE_ETAPE + 1) + '" aria-label="Avancement">'
      + GUIDE.etapes.map(function (x, i) {
          return '<span class="' + (i < GUIDE_ETAPE ? "fa" : (i === GUIDE_ETAPE ? "ic" : ""))
            + '"></span>';
        }).join("") + "</div>"
      + '<p class="ig-g-n">Étape ' + (GUIDE_ETAPE + 1) + " sur " + n
      + (sec ? " · section " + esc(sec) : "")
      + (e.duree ? ' · <span class="ig-g-du">' + esc(e.duree) + "</span>" : "")
      + "</p>"
      + "<h3>" + esc(e.titre) + "</h3>"
      /* CE QUE LA SECTION EST, avant ce qu'il faut y faire. Quelqu'un qui
         découvre la page a besoin de savoir où il arrive : un impératif servi
         sans son contexte s'exécute sans se comprendre, et ne se retient
         pas. */
      + (e.objet ? '<p class="ig-g-ob">' + esc(e.objet) + "</p>" : "")
      + '<p class="ig-g-f">' + esc(e.faire) + "</p>"
      + '<p class="ig-g-ga"><b>Ce que vous y gagnez.</b> ' + esc(e.gain) + "</p>";
    /* POURQUOI CETTE ÉTAPE ICI. C'est la partie qui manquait : une suite
       d'écrans sans logique se subit ; une séquence dont on comprend l'ordre
       se retient, et se refait seul la fois suivante. */
    if (e.pourquoi_ici) {
      h += '<p class="ig-g-pq"><b>Pourquoi maintenant.</b> '
        + esc(e.pourquoi_ici) + "</p>";
    }
    /* CE QU'ON PERD À SAUTER. Dire qu'une étape peut se sauter est plus
       honnête — et plus efficace — que de présenter sept étapes comme
       également obligatoires : le lecteur pressé saute de toute façon, autant
       qu'il sache laquelle. */
    if (e.si_vous_sautez) {
      h += '<p class="ig-g-sa"><b>Si vous passez outre.</b> '
        + esc(e.si_vous_sautez) + "</p>";
    }
    /* LES SIGLES DE L'ÉTAPE, désignés au lieu d'être supposés connus. Ils
       portent le même attribut que partout ailleurs sur la page : l'infobulle
       existante les explique, au survol comme au clavier. */
    if (e.notions && e.notions.length) {
      h += '<p class="ig-g-no"><span class="lb">À connaître ici</span>'
        + e.notions.map(function (x) {
            return '<span class="ig-g-nt"' + info(x.ref) + ">"
              + esc(x.nom) + "</span>";
          }).join("") + "</p>";
    }
    if (e.chiffres && e.chiffres.length) {
      /* Les chiffres viennent du registre réel, recalculés pour ce croisement.
         Ils portent la mention de leur origine : sans elle, ils passeraient
         pour une illustration. */
      h += '<ul class="ig-g-ch">'
        + e.chiffres.map(function (c) { return "<li>" + esc(c) + "</li>"; }).join("")
        + '</ul><p class="ig-g-src">Calculé sur le registre pour ce rôle et ce '
        + "thème, à la phase " + esc(GUIDE.phase) + ".</p>";
    }
    /* Le conseil de terrain de la phase, à l'étape où l'on ouvre son dossier :
       c'est le moment où il sert, et pas avant. Le poser sur chaque étape en
       ferait un bandeau qu'on cesse de lire. */
    if (GUIDE.conseil && e.ancre === "ig-dossier") {
      h += '<div class="ig-g-cons"><b>' + esc(GUIDE.conseil.titre)
        + "</b><span>" + esc(GUIDE.conseil.texte).replace(/\n\n/g, "<br><br>")
        + "</span></div>";
    }
    if (GUIDE_ETAPE === n - 1) {
      /* UN BLOC PAR THÈME, PAS UN TEXTE FUSIONNÉ : chaque thème garde son
         propre piège, avec son propre nom au-dessus. Les fondre en un seul
         paragraphe aurait perdu lequel vient d'où — et un lecteur qui n'a
         choisi qu'« énergie » n'a pas à lire le piège de l'eau caché dedans. */
      h += GUIDE.themes.map(function (t) {
        return '<div class="ig-g-fin"><b>Le piège — ' + esc(t.nom) + '.</b> '
          + esc(t.piege) + "</div>";
      }).join("")
        + '<div class="ig-g-fin ok"><b>Au terme du parcours.</b> '
        + esc(GUIDE.role.fin) + "</div>";
    }
    if (!GUIDE.profil_renseigne) {
      h += '<p class="ig-g-att">La puissance informatique n\'est pas encore '
        + "renseignée : les chiffres de dossier restent vides tant qu'elle "
        + "manque.</p>";
    }
    h += '<div class="ig-g-nav">'
      + '<button type="button" class="ig-g-b s" id="ig-g-prec"'
      + (GUIDE_ETAPE === 0 ? " disabled" : "") + ">← Précédent</button>"
      + '<button type="button" class="ig-g-b" id="ig-g-suiv"'
      + (GUIDE_ETAPE === n - 1 ? " disabled" : "") + ">Suivant →</button>"
      + '<button type="button" class="ig-g-lien" id="ig-g-aller">Aller à la section</button>'
      + "</div></div>";
    z.innerHTML = h;

    var b;
    if ((b = $("#ig-g-prec"))) b.addEventListener("click", function () {
      if (GUIDE_ETAPE > 0) { GUIDE_ETAPE--; guideRendreEtape(); }
    });
    if ((b = $("#ig-g-suiv"))) b.addEventListener("click", function () {
      if (GUIDE_ETAPE < GUIDE.etapes.length - 1) { GUIDE_ETAPE++; guideRendreEtape(); }
    });
    if ((b = $("#ig-g-aller"))) b.addEventListener("click", function () { guideAller(e.ancre); });
    if ((b = $("#ig-g-changer"))) b.addEventListener("click", function () {
      guideSurligner(null); GUIDE = null; guideRendreChoix();
    });
    if ((b = $("#ig-g-fermer"))) b.addEventListener("click", function () { guideOuvrir(false); });
    guideSurligner(e.ancre);
  }

  function guideAller(ancre) {
    var el = document.getElementById(ancre);
    if (!el) return;
    var sec = el.closest("section") || el;
    /* prefers-reduced-motion respecté : un défilement animé déclenche des
       troubles vestibulaires chez une part réelle des lecteurs. */
    var doux = !window.matchMedia
      || !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    sec.scrollIntoView({ behavior: doux ? "smooth" : "auto", block: "start" });
  }

  function brancherGuide() {
    var b = $("#ig-lanceur-b");
    if (!b) return;
    b.addEventListener("click", function () {
      var z = guideZone();
      var ouvrir = z.hidden;
      guideOuvrir(ouvrir);
      if (ouvrir && !GUIDE) guideRendreChoix();
    });
    /* Échap ferme le parcours, comme l'infobulle : deux couches superposées
       qui ne se ferment pas de la même façon désorientent. */
    document.addEventListener("keydown", function (ev) {
      var z = guideZone();
      if (ev.key === "Escape" && z && !z.hidden) guideOuvrir(false);
    });
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE BATTEMENT DES BOUTONS

     Ce que le battement dit : « ceci vient de devenir possible ». Il est donc
     posé au moment où un bouton devient actionnable, et pas avant — un bouton
     d'export qui clignote alors qu'aucune phase n'est choisie promet une
     action qui échouera.

     Trois règles, et la deuxième est celle qui fait la différence entre un
     repère et une gêne :

       · UNE FOIS PAR GROUPE. La page se redessine à chaque frappe dans le
         formulaire. Reposer la classe à chaque rendu ferait battre les boutons
         en permanence, ce qui est exactement ce qu'on veut éviter.

       · L'INTERACTION L'ARRÊTE. Un bouton qui continue de clignoter après
         qu'on s'en est servi n'est plus un repère, c'est du bruit. Survol,
         clic ou focus clavier suffisent : le lecteur l'a vu.

       · L'ANIMATION S'ARRÊTE SEULE. Cinq cycles, neuf secondes. Aucun bouton
         « arrêter » à chercher. */
  var BATTUS = {};

  /* `pas` est le décalage, en millisecondes, entre deux éléments d'un même
     groupe. À zéro, tout part ensemble — c'est ce qu'il faut quand deux ou
     trois boutons forment un ensemble. Au-delà d'une poignée d'éléments, un
     départ simultané devient une pulsation de page entière : le décalage la
     transforme en vague, qui se lit de haut en bas et donne un ORDRE plutôt
     qu'une alarme. */
  function battre(selecteur, classe, groupe, pas) {
    if (BATTUS[groupe]) return;
    var els = document.querySelectorAll(selecteur);
    if (!els.length) return;
    BATTUS[groupe] = true;
    var rang = 0;
    els.forEach(function (el) {
      if (el.disabled) return;
      /* Un bouton qui bat déjà pour une raison PLUS PRÉCISE garde la sienne.
         Le bleu de la vague dit « voici les gestes de cette page » ; le
         battement de « Rédiger » dit « celle-ci, maintenant ». Superposer les
         deux ferait gagner le dernier posé, c'est-à-dire le moins précis.

         Comparé à `classe` et non à la seule présence d'un battement : sans
         cela, une vague laisserait la précédente en place sur les boutons
         communs, et les décalages des deux se mélangeraient — l'ordre de
         lecture, qui est tout l'intérêt du procédé, disparaîtrait.

         Le suffixe est FACULTATIF dans le motif : la désignation du fil des
         gestes et celle du lanceur portent « ig-bat » tout court. Ne
         reconnaître que les formes suffixées laissait la vague écraser leurs
         animations — deux règles sur la même propriété, la dernière écrite
         l'emporte, et c'était la moins précise. */
      if (pas && (el.className.match(/\big-bat(?:-[a-z]+)?\b/g) || [])
                   .some(function (c) { return c !== classe; })) return;
      /* Et dans l'autre sens : une désignation précise CHASSE la vague. Sans
         cela, l'ordre d'arrivée déciderait — la vague part une demi-seconde
         après le rendu, le lanceur une seconde après le chargement, et selon
         ce qui gagne la course le geste du moment se retrouverait peint comme
         les cent-treize autres. */
      if (!pas && classe !== "ig-bat-b") {
        el.classList.remove("ig-bat-b");
        el.style.animationDelay = "";
      }
      if (pas) {
        /* Plafonné : au-delà, les derniers boutons battraient si tard que le
           lecteur aurait déjà agi, et le rappel deviendrait une interruption. */
        el.style.animationDelay = Math.min(rang * pas, 2600) + "ms";
        rang++;
      }
      el.classList.add(classe);
      var stop = function () {
        el.classList.remove(classe);
        el.style.animationDelay = "";
        el.removeEventListener("mouseenter", stop);
        el.removeEventListener("focus", stop);
        el.removeEventListener("click", stop);
      };
      el.addEventListener("mouseenter", stop);
      el.addEventListener("focus", stop);
      el.addEventListener("click", stop);
      /* Filet : si l'animation n'émet pas son événement de fin — onglet en
         arrière-plan, moteur qui l'a coupée — la classe resterait posée et le
         bouton garderait un halo figé. */
      el.addEventListener("animationend", function () {
        el.classList.remove(classe);
        el.style.animationDelay = "";
      });
    });
  }

  /* ── LA VAGUE BLEUE : TOUS LES GESTES DE LA PAGE, UNE FOIS ──────────────
     Les battements précédents désignent UN geste : celui qui manque, celui
     qu'il faut poser maintenant. Ils répondent à « par quoi je continue ? ».

     Il reste l'autre question, celle du lecteur qui arrive : « qu'est-ce que
     je peux faire ici ? » Sept sections, une soixantaine de gestes, et rien
     qui les distingue du texte au premier coup d'œil. La vague les montre
     tous, en bleu — la couleur des actions du site — et une seule fois.

     TROIS PRÉCAUTIONS, sans lesquelles elle deviendrait le bruit qu'elle veut
     éviter :

       · UNE VAGUE, PAS UN CLIGNOTEMENT D'ENSEMBLE. Chaque bouton part
         soixante-dix millisecondes après le précédent, dans l'ordre du
         document : le regard descend la page au lieu de la subir. Aucune
         surface large ne s'allume d'un coup — c'est aussi ce qui la garde
         hors du seuil de photosensibilité du WCAG 2.3.1.

       · TROIS CYCLES, PAS CINQ. Elle informe, elle n'insiste pas. Ce sont les
         désignations précises qui insistent.

       · CE QUI BAT DÉJÀ GARDE SON BATTEMENT. Un bouton désigné pour lui-même
         ne redevient pas un bouton parmi soixante.

     La clé porte l'état de la page : ouvrir un projet ou changer de phase fait
     apparaître des gestes qui n'existaient pas, et ceux-là méritent d'être
     montrés à leur tour. Un simple redessin, lui, ne rejoue rien. */
  /* L'inventaire est ÉNUMÉRÉ, pas deviné par un « tous les boutons de la
     page » : celui-ci emporterait le bouton du menu latéral, les fermetures de
     panneaux et les bascules d'infobulle — des commandes d'interface, pas des
     gestes du projet. Un balayage a vérifié qu'il ne reste rien dehors. */
  var GESTES_SEL = [
    "#ig-lanceur-b", "#ig-guid-go", "#ig-rep-x",
    "#ig-sec-projet button", "#ig-sec-projet .btn",
    "#ig-form .s-b",
    "#ig-filieres button",
    "#ig-parcours [data-phase]",
    "#ig-guidage button", "#ig-guidage .ig-g-lien",
    "#ig-dossier button", "#ig-dossier a.btn", "#ig-dossier a.ig-dl",
    "#ig-rail button",
    "#ig-docx", "#ig-pdf", "#ig-xlsx",
    ".ig-doc-a button",
    "#ig-depot button", "#ig-depot .btn", "#ig-depot-liste button",
  ].join(",");

  function battreLaPage() {
    var n = document.querySelectorAll(GESTES_SEL).length;
    if (!n) return;
    /* Le décalage se calcule sur le NOMBRE, pour que la vague dure toujours à
       peu près deux secondes : à pas fixe, soixante boutons mettraient quatre
       secondes à s'allumer, et les derniers battraient longtemps après que le
       lecteur a agi. */
    var pas = Math.max(20, Math.min(70, Math.round(2000 / n)));
    /* La clé porte l'ÉTAT, jamais le nombre de boutons : celui-ci change à
       chaque fragment qui arrive, et la vague se rejouerait quatre fois au
       chargement. L'état, lui, ne change que sur un choix du lecteur. */
    var cle = "page:" + (PROJET ? PROJET.id : "-") + ":" + (PHASE || "-")
            + ":" + (FILIERE || "-");
    if (BATTUS[cle]) return;
    /* La vague précédente est EFFACÉE avant la nouvelle. Sans cela, les
       boutons déjà marqués seraient sautés et garderaient leur ancien
       décalage : deux vagues entrelacées, dont l'ordre de lecture — la seule
       raison d'être du décalage — ne veut plus rien dire. */
    document.querySelectorAll(".ig-bat-b").forEach(function (el) {
      el.classList.remove("ig-bat-b");
      el.style.animationDelay = "";
    });
    battre(GESTES_SEL, "ig-bat-b", cle, pas);
  }

  /* Les fragments de la page arrivent séparément — référentiel, projets,
     frise, dossier. Lancer la vague au premier laisserait dehors tous les
     suivants ; on attend donc que ça se pose. */
  var VAGUE_T = null;

  function planifierVague() {
    if (VAGUE_T) clearTimeout(VAGUE_T);
    VAGUE_T = setTimeout(battreLaPage, 500);
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE PROFIL REPRIS DE LA PAGE DE CALCUL

     Le formulaire de cette page est le MÊME que celui de /datacenter — même
     référentiel, mêmes champs. Le ressaisir est du travail perdu.

     Deux règles de conduite, et la seconde compte plus que la première :

       · on ne reprend que des VALEURS. Le serveur décide ensuite, champ par
         champ, si la valeur s'écarte de son défaut — donc si elle est SAISIE.
         Reprendre un drapeau « rempli » ferait franchir des phases sur des
         valeurs que personne n'a choisies ;

       · on le DIT. Un formulaire qui se remplit tout seul sans explication
         inquiète plus qu'il n'aide, et le lecteur ne sait plus ce qu'il a
         choisi lui-même. Le bandeau nomme l'origine et offre de repartir à
         vide. */
  var REPRIS = false;

  function reprendreProfil() {
    if (!window.ProfilDC) return;
    var p = window.ProfilDC.lire();
    if (!p) return;
    var poses = window.ProfilDC.appliquer("#ig-form", p.champs);
    if (!poses.length) return;
    /* Le fait de la reprise est retenu : c'est lui qui décide si la page doit
       s'ouvrir directement sur la phase qui compte. Un lecteur qui arrive avec
       un calcul déjà fait n'a pas à recliquer pour retrouver l'endroit où son
       chiffre devient — ou ne devient pas — recevable. */
    REPRIS = true;
    var z = $("#ig-repris");
    if (!z) return;
    z.hidden = false;
    z.innerHTML =
      '<div class="ig-rep-t"><b>Profil repris de la page ' +
      '<a href="/datacenter">Énergie, eau et carbone</a>.</b> '
      + poses.length + " champ" + (poses.length > 1 ? "s" : "")
      + " recopié" + (poses.length > 1 ? "s" : "")
      + " — rien n’a été ressaisi.<br>"
      + "<span>Les valeurs restées sur leur pré-remplissage là-bas le restent "
      + "ici : elles comptent comme non renseignées, et c’est ce qui décide du "
      + "franchissement des phases.</span></div>"
      + '<button type="button" class="ig-rep-b" id="ig-rep-x">'
      + "Repartir d’un formulaire vierge</button>";
    var b = $("#ig-rep-x");
    if (b) b.addEventListener("click", function () {
      window.ProfilDC.oublier();
      /* Remise aux valeurs déclarées du référentiel — et non à vide : le
         formulaire est PRÉ-REMPLI par conception, et le vider produirait un
         état que la page ne sait pas décrire. */
      bâtirFormulaire();
      REPRIS = false;
      PHASE = null;
      z.hidden = true;
      z.innerHTML = "";
      rafraichir();
    });
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE DÉPÔT DE DOCUMENTS CLIENT

     Deux règles, et la première n'est pas négociable :

       · ON DIT CE QUI SERA APPLIQUÉ, AVANT. La page interroge l'état de la
         chaîne d'analyse et l'affiche tel quel. Si aucun antivirus à
         signatures n'est configuré sur le serveur, elle l'écrit — annoncer
         « analyse antivirus » sans en avoir un serait la pire des assurances,
         celle qui ne se vérifie jamais.

       · LE REFUS EXPLIQUE. Un « fichier rejeté » sec fait recommencer à
         l'identique. Le motif dit ce qui a été trouvé et ce qu'il faut faire —
         réenregistrer sans macros, exporter en PDF simple. */
  // Ce que le dépôt accepte réellement, tel que le serveur l'annonce. Tant
  // qu'il n'a pas répondu, le sélecteur s'en tient au sous-ensemble sûr —
  // jamais à une liste plus large que ce qui sera accepté.
  var FORMATS_DEPOT = null;

  function depotEtat() {
    var z = $("#ig-depot-etat");
    if (!z) return;
    demander("/api/datacenter/depot/etat", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) { z.innerHTML = ""; return; }
        var e = j.etat;
        var fort = e.antivirus_configure && e.antivirus_joignable;
        z.className = "ig-dep-etat" + (fort ? " fort" : "");
        z.innerHTML =
          '<p class="t"><b>Ce qui est appliqué à chaque dépôt.</b> '
          + esc(e.resume) + "</p>"
          + '<ul class="l"><li>Formats acceptés — ' + e.extensions_admises.join(", ")
          + "</li><li>Refusés d'office — " + e.formats_macros_refuses.join(", ")
          + " : ces formats portent des macros par construction.</li>"
          + "<li>Sans texte, rien à indexer — une image, un plan DWG ou un PDF "
          + "scanné franchit l'analyse mais n'apporte aucun contenu à la base. "
          + "Fournissez une version avec couche texte (OCR) ou le fichier "
          + "source.</li>"
          + "<li>Taille maximale — " + e.taille_max_mo + " Mo par fichier.</li>"
          + "<li>Vérifications — le contenu doit correspondre à l'extension ; "
          + "les macros, objets incorporés, JavaScript de PDF, liens externes "
          + "et archives disproportionnées sont refusés.</li></ul>";
        // Le sélecteur proposait sa propre liste, écrite à la main : elle
        // invitait à choisir des images et des plans DWG, que le dépôt refuse
        // ensuite. On l'aligne sur ce que le serveur vient d'annoncer.
        if (e.extensions_admises.length) {
          FORMATS_DEPOT = e.extensions_admises.slice();
          var f = $("#ig-dep-f");
          if (f) f.setAttribute("accept", accepteDepot());
        }
      }).catch(function () { z.innerHTML = ""; });
  }

  function accepteDepot() {
    return (FORMATS_DEPOT || ["pdf", "docx", "xlsx", "pptx", "txt", "md", "csv",
                              "json"]).map(function (x) { return "." + x; }).join(",");
  }

  function depotFormulaire() {
    var z = $("#ig-depot");
    if (!z) return;
    z.innerHTML =
      '<label class="dc-champ" for="ig-dep-f"><span class="dc-lab">Document à '
      + 'apporter</span><input id="ig-dep-f" type="file" '
      + 'accept="' + accepteDepot() + '">'
      + '<span class="dc-aide">Le fichier est analysé avant tout '
      + "enregistrement.</span></label>"
      + '<label class="dc-champ" for="ig-dep-t"><span class="dc-lab">Intitulé '
      + '(facultatif)</span><input id="ig-dep-t" type="text" '
      + 'placeholder="— le nom du fichier par défaut —"></label>'
      + '<div class="ig-pc-a"><button type="button" class="ig-gen" '
      + 'id="ig-dep-go">Analyser et déposer</button></div>'
      + '<div id="ig-dep-r" aria-live="polite"></div>';
    var b = $("#ig-dep-go");
    if (b) b.addEventListener("click", depotEnvoyer);
  }

  function depotEnvoyer() {
    var f = $("#ig-dep-f"), r = $("#ig-dep-r"), b = $("#ig-dep-go");
    if (!f || !f.files || !f.files.length) {
      r.innerHTML = '<p class="ig-dep-ko">Choisissez un fichier.</p>';
      return;
    }
    var fichier = f.files[0];
    b.disabled = true;
    r.innerHTML = '<p class="note">Analyse de « ' + esc(fichier.name) + " »…</p>";
    var lect = new FileReader();
    lect.onerror = function () {
      b.disabled = false;
      r.innerHTML = '<p class="ig-dep-ko">Le fichier n\'a pas pu être lu.</p>';
    };
    lect.onload = function () {
      var b64 = String(lect.result).split(",")[1] || "";
      demander("/api/datacenter/depot", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: fichier.name, contenu: b64,
                               titre: ($("#ig-dep-t") || {}).value || "" }),
      }).then(function (x) { return x.json().then(function (j) { return [x.status, j]; }); })
        .then(function (xj) {
          var st = xj[0], j = xj[1];
          b.disabled = false;
          if (st === 401 || st === 403) {
            r.innerHTML = '<p class="ig-dep-ko">Le dépôt est réservé aux '
              + "comptes d'administration : un document déposé alimente les "
              + "études et la base de connaissance.</p>";
            return;
          }
          if (!j || !j.ok) {
            /* Le motif du refus vient du serveur et dit quoi faire. On
               l'affiche tel quel plutôt que de le résumer : c'est lui qui
               évite au client de recommencer à l'identique. */
            r.innerHTML = '<p class="ig-dep-ko"><b>Document refusé.</b> '
              + esc((j && j.message) || "Analyse en échec.") + "</p>"
              + ((j && j.analyse && j.analyse.portes)
                  ? '<p class="ig-dep-n">Portes appliquées : '
                    + esc(j.analyse.portes.join(", ")) + ".</p>" : "");
            return;
          }
          r.innerHTML = '<p class="ig-dep-ok"><b>Document accepté et '
            + 'enregistré.</b> ' + esc(j.document.title || fichier.name)
            + "</p><p class=\"ig-dep-n\">Portes appliquées : "
            + esc((j.analyse.portes || []).join(", ")) + " · visibilité interne."
            + ((j.analyse.alertes && j.analyse.alertes.length)
                ? " " + esc(j.analyse.alertes[0]) : "") + "</p>";
          f.value = "";
        }).catch(function () {
          b.disabled = false;
          r.innerHTML = '<p class="ig-dep-ko">Le dépôt n\'a pas répondu.</p>';
        });
    };
    lect.readAsDataURL(fichier);
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE NIVEAU DE DISPONIBILITÉ, ET LE NOMBRE D'UNITÉS QU'IL INSTALLE

     Ce bloc ne calcule rien lui-même — le compte vient du serveur, comme tout
     le reste de la page. Ce qu'il fait, c'est RENDRE VISIBLE une conséquence
     qu'on découvre d'habitude au chiffrage : pour six groupes froid
     nécessaires, viser un niveau tolérant à la panne en installe douze, ou
     quatorze en 2(N+1). C'est le genre de compte qu'on croit évident et qu'on
     rate en réunion.

     Le bloc affiche aussi, systématiquement, ce que le niveau NE garantit
     PAS. C'est la partie qui se perd, et c'est celle qui coûte cher : un
     dossier annoncé tolérant à la panne dont les deux arrivées partent du même
     poste source n'est pas tolérant à la panne. */
  var DISPO = null;

  function bâtirDisponibilite() {
    var z = $("#ig-dispo");
    if (!z || !CADRE || !CADRE.disponibilite) return;
    var d = CADRE.disponibilite;
    /* LES CASES QUI FONT UN CALCUL VIENNENT D'ABORD. `dispoDemander` n'envoie
       RIEN au serveur tant que ni le niveau ni le schéma ne sont renseignés
       (silence pur, aucune requête) ; et sans le nombre d'unités, la requête
       part mais `redondance()` rend `null` — aucun compte affiché, seule
       l'exigence du niveau reste visible. Le schéma reste en DERNIER : il est
       facultatif dès que le niveau est renseigné, jamais les deux ensemble —
       ce n'est qu'une alternative au niveau, pas une troisième case requise. */
    var h = '<label class="dc-champ" for="ig-tier">'
      + '<span class="dc-lab">Niveau de disponibilité visé'
      + ' <b class="dc-req" title="Champ nécessaire — ou, à défaut, le schéma '
      + 'de redondance plus bas.">*</b></span>'
      + '<select id="ig-tier"><option value="">— non arrêté —</option>';
    (d.niveaux_ordre || []).forEach(function (k) {
      h += '<option value="' + esc(k) + '">' + esc(d.niveaux[k].nom) + "</option>";
    });
    h += '</select><span class="dc-aide">Le niveau qualifie une TOPOLOGIE. '
      + "Ce cadre dit ce qu'il exige et compte ce qu'il installe&nbsp;; il ne "
      + "décerne aucune certification.</span></label>";
    h += '<label class="dc-champ" for="ig-nunites">'
      + '<span class="dc-lab">Unités nécessaires par chaîne '
      + '<span class="dc-unite">(hors réserve)</span>'
      + ' <b class="dc-req" title="Champ nécessaire">*</b></span>'
      + '<input id="ig-nunites" type="text" inputmode="numeric" placeholder="ex. 6">'
      + '<span class="dc-aide">Le nombre de groupes froid, de chaînes onduleur '
      + "ou de groupes électrogènes que la charge exige, réserve exclue.</span></label>";
    h += '<label class="dc-champ" for="ig-schema">'
      + '<span class="dc-lab">Schéma de redondance</span>'
      + '<select id="ig-schema"><option value="">— déduit du niveau —</option>';
    (d.schemas_ordre || []).forEach(function (k) {
      h += '<option value="' + esc(k) + '">' + esc(d.schemas[k].nom) + "</option>";
    });
    h += '</select><span class="dc-aide">Laissez « déduit » pour prendre le '
      + "schéma que le niveau appelle, ou imposez le vôtre — y compris si "
      + "aucun niveau n'est renseigné : lui seul suffit alors, avec le nombre "
      + "d'unités.</span></label>";
    z.innerHTML = h;
    ["#ig-tier", "#ig-schema", "#ig-nunites"].forEach(function (s) {
      var e = $(s);
      if (e) e.addEventListener(s === "#ig-nunites" ? "input" : "change", dispoDemander);
    });
    bâtirQualification();
  }


  /* ── La qualification du niveau, sous-système par sous-système ──────────
     CE QUE CE BLOC AJOUTE, et que le champ « niveau visé » ne pouvait pas
     donner. Le champ au-dessus recueille une INTENTION ; celui-ci constate ce
     que la topologie décrite permettrait de revendiquer — et surtout ce qui
     l'en empêche.

     LA RÈGLE QUI FAIT TOUT LE BLOC : le niveau d'un site est le PLUS BAS de
     ses sous-systèmes. Jamais leur moyenne, et il n'existe pas de niveau
     fractionnaire. Neuf listes déroulantes plutôt qu'une, parce que c'est le
     seul moyen de faire apparaître le maillon faible — celui qu'on ne regarde
     pas, en général la distribution mécanique ou l'eau d'appoint.

     RIEN N'EST OBLIGATOIRE. Un sous-système non noté ne vaut pas « conforme » :
     il ressort NON ÉVALUÉ, et le résultat est alors annoncé comme un plafond.
     Exiger les neuf notes ferait cocher au hasard pour obtenir un chiffre. */
  function bâtirQualification() {
    var z = $("#ig-qualif");
    if (!z || !CADRE) return;
    var SS = CADRE.tier_sous_systemes || {};
    var ordre = CADRE.tier_ordre || ["I", "II", "III", "IV"];
    var noms = ((CADRE.disponibilite || {}).niveaux) || {};
    var cles = Object.keys(SS);
    if (!cles.length) { z.innerHTML = ""; return; }
    var h = '<p class="ig-qua-t"><b>Ce que la topologie permettrait de '
      + "revendiquer.</b> Notez chaque sous-système&nbsp;: le niveau du site "
      + "sera le PLUS BAS d'entre eux, jamais leur moyenne. Laissez vide ce "
      + "que vous ne savez pas — un sous-système non noté n'est pas conforme, "
      + 'il est inconnu.</p><div class="dc-grille">';
    cles.forEach(function (k) {
      var id = "ig-ss-" + k;
      h += '<label class="dc-champ" for="' + id + '"><span class="dc-lab">'
        + esc(SS[k].nom) + "</span>"
        + '<select id="' + id + '" data-ss="' + esc(k) + '">'
        + '<option value="">— non évalué —</option>';
      ordre.forEach(function (n) {
        h += '<option value="' + esc(n) + '">'
          + esc((noms[n] || {}).nom || ("Tier " + n)) + "</option>";
      });
      h += '</select><span class="dc-aide">' + esc(SS[k].aide) + "</span></label>";
    });
    z.innerHTML = h + "</div>"
      + '<button type="button" class="ig-lanceur-b" id="ig-qua-go">'
      + "Qualifier la topologie →</button>"
      + '<p class="note" id="ig-qua-msg" style="margin-top:10px"></p>'
      + '<div id="ig-qua-out"></div>';
    var b = $("#ig-qua-go");
    if (b) b.addEventListener("click", qualifier);
  }

  function qualifierLire() {
    var ss = {};
    document.querySelectorAll("#ig-qualif [data-ss]").forEach(function (e) {
      var v = (e.value || "").trim();
      if (v) ss[e.getAttribute("data-ss")] = v;
    });
    return ss;
  }

  function qualifier() {
    var msg = $("#ig-qua-msg"), out = $("#ig-qua-out");
    if (!out) return;
    var ss = qualifierLire();
    if (!Object.keys(ss).length) {
      msg.textContent = "Notez au moins un sous-système.";
      return;
    }
    msg.textContent = "Qualification…";
    var corps = lireProfil();
    corps.sous_systemes = ss;
    corps.vise = (($("#ig-tier") || {}).value || "");
    demander("/api/datacenter/tier", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) {
          msg.textContent = (j && j.message) || "Qualification indisponible.";
          return;
        }
        msg.textContent = "";
        qualifierRendre(j);
      })
      .catch(function () { msg.textContent = "Qualification indisponible."; });
  }

  function qualifierRendre(j) {
    var out = $("#ig-qua-out"), q = j.qualification;
    if (!q.evalue) {
      out.innerHTML = '<p class="note">' + esc(q.pourquoi) + "</p>";
      return;
    }
    /* LE NIVEAU, ET AUSSITÔT SON STATUT. Un plafond affiché comme un verdict
       ferait annoncer au client un niveau qui ne peut que descendre. */
    var h = '<div class="ig-qua-tete' + (q.plafond ? " ig-qua-plafond" : "") + '">'
      + '<span class="ig-qua-n"' + info("tier_exigence:" + q.niveau) + ">"
      + esc(q.niveau_nom) + "</span>"
      + (q.plafond ? '<span class="ig-qua-b">plafond, pas verdict</span>' : "")
      + '<span class="ig-qua-l">' + esc(q.lecture) + "</span></div>";
    /* LE SOUS-SYSTÈME LIMITANT, mis en évidence : c'est lui, et lui seul, qui
       décide du niveau du site. */
    h += '<ul class="ig-qua-ss">';
    q.sous_systemes.forEach(function (s) {
      /* LES TROIS ÉTATS SE NOMMENT, aucun n'est déduit par défaut. Écrit
         en « sinon », un quatrième état ajouté un jour au serveur tomberait
         en silence dans le seau du non-évalué et s'afficherait comme lui —
         faux, et invisible. */
      var cls = s.etat === "note" ? (s.limitant ? " ig-qua-lim" : "")
        : s.etat === "hors_perimetre" ? " ig-qua-hors"
        : s.etat === "non_evalue" ? " ig-qua-ko" : " ig-qua-inconnu";
      h += '<li class="ig-qua-s' + cls + '"><b>' + esc(s.nom) + "</b>"
        + (s.etat === "note"
            ? '<span class="ig-qua-v">' + esc(s.niveau) + "</span>"
              + (s.limitant ? '<span class="ig-qua-b">limitant</span>' : "")
            : '<span class="ig-qua-p">' + esc(s.pourquoi || "") + "</span>")
        + "</li>";
    });
    h += "</ul>";
    /* L'ÉCART AU NIVEAU VISÉ. Il ne s'affiche que si un niveau est visé :
       sans intention déclarée, un écart n'a pas de sens. */
    if (j.ecart && j.ecart.vise) {
      var e = j.ecart;
      h += '<div class="ig-qua-ec"><b>Écart au ' + esc(e.vise_nom) + "</b>"
        + '<p class="ig-qua-l">' + esc(e.lecture) + "</p>";
      if (e.manquants.length) {
        h += "<ul>";
        e.manquants.forEach(function (m) {
          h += "<li>" + esc(m.nom) + " — " + esc(m.ecart) + "</li>";
        });
        h += "</ul>";
      }
      h += '<p class="ig-qua-es"><b' + info("tier_essai:" + e.vise)
        + ">Ce qu'il faudra DÉMONTRER</b> — le niveau se constate par des "
        + "essais dont l'issue est observable, pas par une liste de "
        + "matériel.</p><ul>";
      e.essais_a_demontrer.forEach(function (x) {
        h += "<li>" + esc(x) + "</li>";
      });
      h += "</ul></div>";
    }
    /* LES GROUPES : la classe de service décide de ce qui compte. */
    if (j.groupes) {
      var g = j.groupes;
      h += '<div class="ig-qua-gr"><b' + info("tier_regle:groupe_illimite")
        + ">Groupes électrogènes</b>";
      h += g.nature === "refus"
        ? '<p class="ig-qua-p">' + esc(g.message) + "</p>"
        : "<p>" + esc(nombreFr(g.qualifiante_kw)) + " kW comptent pour un "
          + "niveau III ou IV sur " + esc(nombreFr(g.puissance_nominale_kw))
          + " kW de plaque — " + esc(g.origine) + '.</p><p class="ig-qua-p">'
          + esc(g.note) + "</p>";
      h += "</div>";
    }
    /* L'AUTONOMIE, et son lien avec le régime administratif. */
    if (j.autonomie) {
      var a = j.autonomie;
      h += '<div class="ig-qua-au"><b' + info("tier_regle:autonomie_douze_heures")
        + ">Autonomie sur site — " + a.heures + " heures à la capacité N</b>";
      if (a.combustible) {
        h += "<p>Combustible : au moins " + esc(nombreFr(a.combustible.volume_m3, 1))
          + " m³ stockés.</p>";
      }
      if (a.eau_appoint && a.eau_appoint.volume_m3) {
        h += "<p>Eau d'appoint : au moins "
          + esc(nombreFr(a.eau_appoint.volume_m3, 1)) + " m³ en réserve.</p>"
          + '<p class="ig-qua-p">' + esc(a.eau_appoint.note) + "</p>";
      } else if (a.eau_appoint && a.eau_appoint.pourquoi) {
        h += '<p class="ig-qua-p">' + esc(a.eau_appoint.pourquoi) + "</p>";
      }
      (a.manques || []).forEach(function (m) {
        h += '<p class="ig-qua-p">Il manque ' + esc(m) + ".</p>";
      });
      h += '<p class="ig-qua-p">' + esc(a.lien_icpe) + "</p></div>";
    }
    /* LES RÈGLES DURES, et la réserve. La réserve ferme le bloc parce que
       c'est elle qui distingue une qualification d'une certification. */
    h += '<div class="ig-qua-rg"><b>Les règles qui décident</b><ul>';
    Object.keys(j.referentiel.regles).forEach(function (k) {
      h += '<li><span' + info("tier_regle:" + k) + ">"
        + esc(j.referentiel.regles[k].nom) + "</span></li>";
    });
    h += "</ul></div>"
      + '<p class="ig-icpe-res">' + esc(q.reserve) + "</p>"
      + '<p class="ig-icpe-res">' + esc(q.source) + "</p>";
    out.innerHTML = h;
  }

  var dispoMinuteur = null;
  function dispoDemander() {
    clearTimeout(dispoMinuteur);
    dispoMinuteur = setTimeout(function () {
      var tier = (($("#ig-tier") || {}).value || "");
      var sch = (($("#ig-schema") || {}).value || "");
      var n = (($("#ig-nunites") || {}).value || "").replace(",", ".");
      if (!tier && !sch) { DISPO = null; rendreDisponibilite(null); return; }
      demander("/api/datacenter/ingenierie/disponibilite", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tier: tier, schema: sch, n_unites: n }),
      })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (!j.ok) return;
          DISPO = j.disponibilite;
          rendreDisponibilite(DISPO);
          majGuidage();
        })
        .catch(function () { /* le reste de la page continue de fonctionner */ });
    }, 320);
  }

  function rendreDisponibilite(d) {
    var z = $("#ig-dispo-r");
    if (!z) return;
    if (!d) { z.innerHTML = ""; return; }
    var h = "";
    if (d.tier) {
      h += '<p class="ig-dsrc"><b'
        + info("tier:" + d.tier.code) + ">" + esc(d.tier.nom)
        + "</b> — survolez pour ce que le niveau exige, phase par phase.</p>"
        + '<div class="ig-dr">'
        + bloc("Chemins de distribution", d.tier.chemins)
        + bloc("Entretien", d.tier.maintenance)
        + bloc("Comportement au défaut", d.tier.defaut)
        + "</div>"
        + '<p class="ig-dsrc"><b>Ce que le niveau exige — </b>'
        + esc(d.tier.consequence) + "</p>";
    }
    var r = d.redondance;
    /* UN REFUS N'EST PAS UN COMPTE. Le test ne portait que sur l'existence de
       l'objet : le moteur disant désormais POURQUOI il ne compte pas, ce même
       test aurait affiché « undefined unités installées » sur un message
       d'erreur. On rend le motif, à la place du compte. */
    if (r && r.nature === "refus") {
      h += '<p class="ig-drefus"><b>Ce compte n’a pas pu être fait.</b> '
        + esc(r.message) + "</p>";
    } else if (r) {
      /* Le compte, en gros. C'est le chiffre qu'on vient chercher, et celui
         qui surprend : la marge est le PRIX du niveau, pas un excédent. */
      h += '<div class="ig-dr">'
        + '<div class="b"><div class="n">Unités installées'
        + (r.origine_schema === "deduit_du_niveau"
            ? " — schéma déduit du niveau" : "") + '</div>'
        + '<div class="q">' + r.installees
        + ' <span class="u">unités</span></div>'
        + '<div class="i">' + r.chaines + " chaîne" + (r.chaines > 1 ? "s" : "")
        + " de " + r.par_chaine + " · besoin " + r.besoin + " · calculé</div></div>"
        + '<div class="b"><div class="n">Marge de capacité installée</div>'
        + '<div class="q">' + (r.marge_pct > 0 ? "+" : "") + fr(r.marge_pct)
        + ' <span class="u">%</span></div>'
        + '<div class="i"' + info("redondance:" + r.schema) + ">"
        + esc(r.nom) + "</div></div>"
        + '<div class="b"><div class="n">Pertes absorbées sans coupure</div>'
        + '<div class="q">' + r.perte_admissible
        + ' <span class="u">unité' + (r.perte_admissible > 1 ? "s" : "")
        + '</span></div>'
        + '<div class="i">à la température de dimensionnement</div></div>'
        + "</div>"
        + '<p class="ig-dsrc">' + esc(r.note) + "</p>";
      /* Hors de ce qu'on observe : jamais un refus, le calcul reste juste —
         mais le taire laisserait passer une chaîne de mille groupes froid
         sans un mot, là où le formulaire du profil signale déjà les siennes. */
      if (r.hors_plage)
        h += '<p class="ig-drefus">' + esc(r.hors_plage) + "</p>";
    }
    /* Toujours affiché, même quand tout va bien : ces quatre points sont ce
       qu'un niveau ne couvre pas, et les taire ferait passer une topologie
       pour une garantie de service. */
    h += '<div class="ig-dx"><b>Ce que ce niveau ne garantit pas</b><ul>'
      + (d.ne_garantit_pas || []).map(function (x) {
          return "<li>" + esc(x) + "</li>";
        }).join("") + "</ul></div>"
      + '<p class="ig-dsrc">' + esc(d.tier_source) + "</p>";
    z.innerHTML = h;

    function bloc(t, v) {
      return '<div class="b"><div class="n">' + esc(t) + "</div>"
        + '<div class="i" style="font-family:inherit;font-size:12px;color:var(--muted)">'
        + esc(v) + "</div></div>";
    }
  }

  function lireDisponibilite() {
    return {
      tier: (($("#ig-tier") || {}).value || ""),
      schema_redondance: (($("#ig-schema") || {}).value || ""),
      n_unites: (($("#ig-nunites") || {}).value || "").replace(",", "."),
    };
  }

  /* ═════════════════════════════════════════════════════════════════════
     LE PROJET ET SON HISTORIQUE

     Ce qui manquait n'était pas le stockage — les livrables étaient déjà
     conservés — mais le DESTINATAIRE. Un historique à plat, où chaque document
     ne portait qu'un nom de client en texte libre, obligeait à lire les
     intitulés un par un pour retrouver « ce qui a été produit pour Amsterdam,
     en phase APD ». Un projet donne un identifiant à ce regroupement.

     Trois partis pris :

       · L'ORDRE VIENT DU SERVEUR. Les phases sont groupées et triées par
         ingenierie_dc, dans la séquence du projet. Trier ici reviendrait à
         trier par ordre alphabétique — APD avant ESQ — ce qui se lit comme un
         dossier qui commence par sa fin.

       · LE PROJET OUVERT EST VISIBLE EN PERMANENCE. Tout ce que la page
         produit plus bas s'y rattache ; ne pas le montrer ferait écrire des
         pièces dans un dossier qu'on croit être un autre.

       · ON NE STOCKE QU'UN IDENTIFIANT au fil des visites, jamais le contenu
         du dossier. Le navigateur retrouve le projet ; c'est le serveur qui
         dit s'il a le droit de le lire. */
  var PROJETS = [], PROJET = null, PJREF = null;
  var CLE_PROJET = "cp_projet_dc";

  function pjSouvenir(id) {
    try {
      if (id) window.sessionStorage.setItem(CLE_PROJET, id);
      else window.sessionStorage.removeItem(CLE_PROJET);
    } catch (e) { /* navigation privée : on continue sans mémoire */ }
  }
  function pjRappel() {
    try { return window.sessionStorage.getItem(CLE_PROJET) || ""; }
    catch (e) { return ""; }
  }

  function pjDate(ms) {
    if (!ms) return "—";
    var d = new Date(Number(ms));
    if (isNaN(d.getTime())) return "—";
    var z = function (n) { return (n < 10 ? "0" : "") + n; };
    return z(d.getDate()) + "/" + z(d.getMonth() + 1) + "/" + d.getFullYear()
      + " à " + z(d.getHours()) + "h" + z(d.getMinutes());
  }

  function pjMsg(texte, sorte) {
    var z = $("#ig-pj-msg");
    if (!z) return;
    z.innerHTML = texte
      ? '<p class="' + (sorte === "ko" ? "ig-dep-ko" : "ig-dep-ok") + '">'
        + esc(texte) + "</p>"
      : "";
  }

  function pjFormulaire() {
    var z = $("#ig-pj-form");
    if (!z) return;
    var sts = (PJREF && PJREF.statuts) || {};
    var h = '<div class="ch lg"><label for="ig-pj-sel">Projet ouvert</label>'
      + '<select id="ig-pj-sel"><option value="">— aucun projet ouvert —</option>';
    PROJETS.forEach(function (p) {
      h += '<option value="' + esc(p.id) + '"'
        + (PROJET && PROJET.id === p.id ? " selected" : "") + ">"
        + esc(p.nom) + (p.client ? " — " + esc(p.client) : "") + "</option>";
    });
    h += '<option value="+">＋ Ouvrir un nouveau projet…</option></select></div>'
      + '<div class="ch lg" id="ig-pj-nouveau" hidden>'
      + '<label for="ig-pj-nom">Nom du nouveau projet</label>'
      + '<input id="ig-pj-nom" type="text" maxlength="160" '
      + 'placeholder="ex. Amsterdam DC1 — extension salle 2"></div>'
      + '<div class="ch"><label for="ig-pj-statut">Statut</label>'
      + '<select id="ig-pj-statut">';
    /* L'ordre et le défaut viennent du SERVEUR, jamais de la position dans le
       dictionnaire : celui-ci est trié par clé à la sérialisation, si bien que
       « Archivé » arrivait en tête. Le premier choix étant celui que le
       navigateur retient quand rien n'est sélectionné, les projets naissaient
       archivés — donc absents de leur propre liste, sans erreur nulle part. */
    var ordre = (PJREF && PJREF.statuts_ordre) || Object.keys(sts);
    var defaut = (PROJET && PROJET.statut)
      || (PJREF && PJREF.statut_defaut) || ordre[0];
    ordre.forEach(function (k) {
      if (!sts[k]) return;
      h += '<option value="' + esc(k) + '"' + (k === defaut ? " selected" : "")
        + ' title="' + esc(sts[k].aide || "") + '">'
        + esc(sts[k].nom) + "</option>";
    });
    h += "</select></div>";
    z.innerHTML = h;
    z.querySelector("#ig-pj-sel").addEventListener("change", pjChoix);
    var st = z.querySelector("#ig-pj-statut");
    /* Le statut s'enregistre au changement, sans bouton : un « Enregistrer »
       qu'on oublie de cliquer laisse à l'écran un statut que le serveur ignore,
       et c'est celui de l'écran qu'on recopie dans son compte rendu. */
    st.addEventListener("change", function () {
      if (PROJET) pjModifier({ statut: st.value });
    });
    pjChoix();
  }

  function pjChoix() {
    var sel = $("#ig-pj-sel"), nv = $("#ig-pj-nouveau");
    if (!sel) return;
    var neuf = sel.value === "+";
    if (nv) nv.hidden = !neuf;
    if (neuf) {
      PROJET = null;
    } else if (sel.value) {
      PROJET = PROJETS.filter(function (p) { return p.id === sel.value; })[0] || null;
    } else {
      PROJET = null;
    }
    pjSouvenir(PROJET ? PROJET.id : "");
    pjBoutons(neuf);
    pjOuvert();
    majGuidage();
    if (PROJET) pjHistorique(PROJET.id);
    else { var h = $("#ig-pj-hist"); if (h) h.innerHTML = ""; }
  }

  function pjBoutons(neuf) {
    var z = $("#ig-pj-actions");
    if (!z) return;
    var h = "";
    if (neuf) {
      h = '<button type="button" class="btn btn-s" id="ig-pj-creer">'
        + "Ouvrir le projet</button>";
    } else if (PROJET) {
      h = '<button type="button" class="btn btn-s" id="ig-pj-sauve">'
        + "Télécharger la sauvegarde complète</button>"
        + '<button type="button" class="btn btn-s" id="ig-pj-fermer">'
        + "Fermer ce projet</button>"
        + '<button type="button" class="btn btn-s" id="ig-pj-suppr">'
        + "Supprimer le projet</button>";
    }
    z.innerHTML = h;
    planifierVague();
    var b;
    if ((b = $("#ig-pj-creer"))) b.addEventListener("click", pjCreer);
    if ((b = $("#ig-pj-sauve"))) {
      b.addEventListener("click", function () {
        if (PROJET) {
          window.location.href = "/api/datacenter/projets/" + PROJET.id + "/sauvegarde";
        }
      });
    }
    if ((b = $("#ig-pj-fermer"))) {
      b.addEventListener("click", function () {
        PROJET = null;
        pjSouvenir("");
        pjFormulaire();
        pjMsg("");
      });
    }
    if ((b = $("#ig-pj-suppr"))) b.addEventListener("click", pjSupprimer);
  }

  function pjOuvert() {
    var z = $("#ig-pj-ouvert");
    if (!z) return;
    if (!PROJET) {
      z.innerHTML = '<div class="ig-pj-vide"><b>Aucun projet ouvert.</b> '
        + "Les pièces rédigées plus bas seront produites, mais ne seront "
        + "rattachées à aucun dossier — vous ne les retrouverez pas ici, ni "
        + "dans une sauvegarde. Ouvrez un projet avant de rédiger.</div>";
      return;
    }
    var sts = (PJREF && PJREF.statuts) || {};
    var nomStatut = (sts[PROJET.statut] || {}).nom || PROJET.statut || "—";
    z.innerHTML = '<div class="ig-pj-o"><div class="nm">' + esc(PROJET.nom)
      + '<span class="ig-st ' + esc(PROJET.statut || "") + '">'
      + esc(nomStatut) + "</span></div>"
      + '<p class="sb">'
      + (PROJET.client ? esc(PROJET.client) + " · " : "")
      + "ouvert le " + pjDate(PROJET.cree_le)
      + " · dernière activité " + pjDate(PROJET.maj_le)
      + "</p></div>";
  }

  function pjCharger(viser) {
    return demander("/api/datacenter/projets", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) throw new Error("liste");
        PROJETS = j.projets || [];
        PJREF = j.referentiel || null;
        var cible = viser || (PROJET && PROJET.id) || pjRappel();
        PROJET = PROJETS.filter(function (p) { return p.id === cible; })[0] || null;
        pjFormulaire();
      })
      .catch(function (e) {
        var z = $("#ig-pj-form");
        if (!z) return;
        z.innerHTML = (e && e.name === "SessionEteinte")
          ? '<p class="note">Reconnectez-vous pour retrouver vos projets.</p>'
          : '<p class="note">Vos projets n\'ont pas pu être '
            + "chargés. Le reste de la page fonctionne&nbsp;; les pièces "
            + "rédigées ne seront simplement rattachées à aucun dossier.</p>";
      });
  }

  function pjCreer() {
    var nom = (($("#ig-pj-nom") || {}).value || "").trim();
    if (!nom) {
      pjMsg("Donnez un nom au projet : c'est lui qui vous permettra de le "
        + "retrouver.", "ko");
      var c = $("#ig-pj-nom");
      if (c) c.focus();
      return;
    }
    var b = $("#ig-pj-creer");
    if (b) { b.disabled = true; b.textContent = "Ouverture…"; }
    /* Le nom du client et la filière courante sont repris du formulaire :
       les redemander ici ferait saisir deux fois la même chose, et les deux
       saisies finiraient par diverger. */
    demander("/api/datacenter/projets", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nom: nom,
        client: (($("#ig-client") || {}).value || "").trim(),
        filiere: FILIERE,
        phase: PHASE || "",
        statut: (($("#ig-pj-statut") || {}).value || ""),
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (b) { b.disabled = false; b.textContent = "Ouvrir le projet"; }
        if (!j.ok) { pjMsg(j.message || "Le projet n'a pas pu être ouvert.", "ko"); return; }
        pjSouvenir(j.projet.id);
        pjMsg("Projet « " + j.projet.nom + " » ouvert. Les pièces rédigées "
          + "plus bas s'y rattacheront automatiquement.");
        pjCharger(j.projet.id);
      })
      .catch(function () {
        if (b) { b.disabled = false; b.textContent = "Ouvrir le projet"; }
        pjMsg("Le projet n'a pas pu être ouvert.", "ko");
      });
  }

  function pjModifier(champs) {
    if (!PROJET) return;
    demander("/api/datacenter/projets/" + PROJET.id, {
      method: "PATCH", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(champs),
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) { pjMsg(j.message || "Modification refusée.", "ko"); return; }
        PROJET = j.projet;
        PROJETS = PROJETS.map(function (p) {
          return p.id === j.projet.id ? j.projet : p;
        });
        pjOuvert();
        pjMsg("Statut enregistré.");
      })
      .catch(function () { pjMsg("Modification impossible.", "ko"); });
  }

  function pjSupprimer() {
    if (!PROJET) return;
    /* Le libellé de la confirmation dit ce qui DISPARAÎT et ce qui RESTE.
       « Êtes-vous sûr ? » ne renseigne sur rien, et fait cliquer au hasard. */
    if (!window.confirm("Supprimer le projet « " + PROJET.nom + " » ?\n\n"
        + "Les livrables déjà produits sont CONSERVÉS : ils cessent seulement "
        + "d'être regroupés sous ce projet. Téléchargez la sauvegarde avant si "
        + "vous voulez en garder le dossier complet.")) {
      return;
    }
    demander("/api/datacenter/projets/" + PROJET.id, {
      method: "DELETE", credentials: "same-origin",
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) { pjMsg(j.message || "Suppression refusée.", "ko"); return; }
        pjSouvenir("");
        PROJET = null;
        pjMsg("Projet supprimé. Les livrables produits restent enregistrés.");
        pjCharger("");
      })
      .catch(function () { pjMsg("Suppression impossible.", "ko"); });
  }

  function pjHistorique(pid) {
    var z = $("#ig-pj-hist");
    if (!z) return;
    z.innerHTML = '<p class="note">Chargement de l\'historique…</p>';
    demander("/api/datacenter/projets/" + pid, { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) { z.innerHTML = ""; return; }
        pjRendreHistorique(j.historique, pid);
      })
      .catch(function () { z.innerHTML = ""; });
  }

  /* LA LISTE DES DOCUMENTS DU PROJET — la LDD.

     Sur un projet d'ingénierie, elle est elle-même une pièce contractuelle :
     elle dit ce qui existe, à quel indice, émis par qui, pour quelle phase.
     C'est le document qu'ouvre en premier un bureau de contrôle, un repreneur
     d'affaire ou un exploitant six mois après la livraison.

     Elle s'ouvre au premier visa, et pas avant : un registre vide n'est pas un
     registre, et un registre qui porterait des brouillons ferait figurer au
     contractuel des documents que personne n'a relus. */
  function blocListeDocuments(pid, vises, total) {
    if (!vises) {
      return '<div class="ig-ldd vide"><b>Liste des documents</b> '
        + "<span>Elle s'ouvrira au premier visa. Un registre qui porterait des "
        + "brouillons ferait figurer au contractuel des documents que personne "
        + "n'a relus.</span></div>";
    }
    var reste = Math.max(0, total - vises);
    return '<div class="ig-ldd">'
      + '<div class="ig-ldd-t"><span class="pt">Liste des documents</span>'
      + "<b>" + vises + " document" + (vises > 1 ? "s" : "") + " visé"
      + (vises > 1 ? "s" : "") + "</b>"
      + '<span class="qu">Le registre de ce qui engage'
      + (reste ? ". " + reste + " autre" + (reste > 1 ? "s" : "")
                 + " reste" + (reste > 1 ? "nt" : "") + " au dossier, non visé"
                 + (reste > 1 ? "s" : "") : "")
      + ".</span></div>"
      + '<div class="ig-ldd-a"><button type="button" id="ig-ldd-lire">Lire</button>'
      + '<a href="/api/datacenter/projets/' + esc(pid) + '/documents.docx">Word</a>'
      + '<a href="/api/datacenter/projets/' + esc(pid) + '/documents.pdf">PDF</a>'
      + "</div></div>";
  }

  function brancherListeDocuments(pid) {
    var b = $("#ig-ldd-lire");
    if (!b) return;
    b.addEventListener("click", function () {
      var ancien = b.textContent;
      b.disabled = true;
      b.textContent = "…";
      demander("/api/datacenter/projets/" + pid + "/documents.md",
               { credentials: "same-origin" }, DELAI_MOYEN)
        .then(function (r) {
          if (!r.ok) throw new Error("liste");
          return r.text();
        })
        .then(function (md) { lireDocument(md, "Liste des documents du projet"); })
        .catch(function () { pjMsg("Liste indisponible pour le moment.", "ko"); })
        .then(function () { b.disabled = false; b.textContent = ancien; });
    });
  }

  function pjRendreHistorique(h, pid) {
    var z = $("#ig-pj-hist");
    if (!z || !h) return;
    if (!h.total) {
      z.innerHTML = '<p class="note">Aucun livrable rattaché à ce projet pour '
        + "l'instant. Rédigez une pièce depuis le registre de phase&nbsp;: elle "
        + "apparaîtra ici, datée et classée dans sa phase.</p>";
      return;
    }
    var etats = h.etats || {};
    /* LA LISTE DES DOCUMENTS s'ouvre au PREMIER VISA. Elle ne se confond pas
       avec le dossier : le dossier porte tout ce qui a été produit, brouillons
       compris — c'est un plan de travail. La liste ne porte que ce qui est
       visé, et elle engage. */
    var vises = 0;
    (h.phases || []).forEach(function (g) {
      (g.livrables || []).forEach(function (l) {
        if ((l.etat || "") === "vise") vises++;
      });
    });
    var html = '<p class="note" style="margin:0 0 12px"><b>'
      + h.total + " livrable" + (h.total > 1 ? "s" : "")
      + "</b> rattaché" + (h.total > 1 ? "s" : "") + " à ce projet, groupé"
      + (h.total > 1 ? "s" : "") + " par phase dans l'ordre de la séquence.</p>"
      + blocListeDocuments(pid, vises, h.total);
    (h.phases || []).forEach(function (g) {
      html += '<div class="ig-hi-g"><h4>' + esc(g.phase) + " — "
        + esc(g.phase_nom) + '<span>' + g.n + " document" + (g.n > 1 ? "s" : "")
        + " · dernier le " + pjDate(g.dernier) + "</span></h4>";
      (g.livrables || []).forEach(function (l) {
        var e = l.etat || "brouillon";
        /* L'ÉTAT SE VOIT. La feuille de style distingue déjà « visé », « relu »
           et « obsolète » par la couleur — mais la classe n'était jamais
           posée : un document validé se présentait exactement comme un
           brouillon, dans un dossier fait pour distinguer les deux. */
        html += '<div class="ig-hi-l"><span class="ti">' + esc(l.label || l.type)
          + '</span><span class="dt">' + pjDate(l.created_at) + "</span>"
          + '<select class="et ' + esc(e) + '" data-etat="' + esc(l.id) + '" '
          + 'aria-label="État du livrable ' + esc(l.label || l.type) + '">';
        // Même règle que pour les statuts : l'ordre vient du serveur, sans
        // quoi « Obsolète » se glisserait entre « Brouillon » et « Relu ».
        ((h.etats_ordre) || Object.keys(etats)).forEach(function (k) {
          if (!etats[k]) return;
          html += '<option value="' + esc(k) + '"' + (k === e ? " selected" : "")
            + ">" + esc(etats[k].nom) + "</option>";
        });
        html += "</select>"
          + '<a href="/api/datacenter/projets/' + esc(pid) + "/livrable/"
          + esc(l.id) + '.docx">Word</a>'
          + '<a href="/api/datacenter/projets/' + esc(pid) + "/livrable/"
          + esc(l.id) + '.pdf">PDF</a>'
          /* Lire sans rien télécharger : c'est le geste de la revue, celui
             qu'on répète, et il n'existait pas — il fallait ouvrir le Word
             pour savoir ce qu'on visait. */
          + '<button type="button" class="ig-hi-lire" data-lire="' + esc(l.id)
          + '" data-titre="' + esc(l.label || l.type) + '">Lire</button></div>';
      });
      html += "</div>";
    });
    z.innerHTML = html;
    brancherListeDocuments(pid);
    z.querySelectorAll("[data-etat]").forEach(function (s) {
      s.addEventListener("change", function () {
        /* La couleur suit l'état IMMÉDIATEMENT, sans attendre le serveur : la
           liste se redessine ensuite sur sa réponse, qui a le dernier mot. */
        s.className = "et " + s.value;
        pjEtatLivrable(pid, s.getAttribute("data-etat"), s.value);
      });
    });
    z.querySelectorAll("[data-lire]").forEach(function (b) {
      b.addEventListener("click", function () {
        var ancien = b.textContent;
        b.disabled = true;
        b.textContent = "…";
        demander("/api/datacenter/projets/" + pid + "/livrable/"
                 + b.getAttribute("data-lire") + ".md",
                 { credentials: "same-origin" }, DELAI_MOYEN)
          .then(function (r) {
            if (!r.ok) throw new Error("lecture");
            return r.text();
          })
          .then(function (md) { lireDocument(md, b.getAttribute("data-titre")); })
          .catch(function () { pjMsg("Document illisible pour le moment.", "ko"); })
          .then(function () { b.disabled = false; b.textContent = ancien; });
      });
    });
  }

  function pjEtatLivrable(pid, lid, etat) {
    demander("/api/datacenter/projets/" + pid + "/livrable/" + lid, {
      method: "PATCH", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ etat: etat }),
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) { pjMsg(j.message || "État non enregistré.", "ko"); return; }
        pjMsg("État enregistré.");
        /* On redessine à partir de la réponse du SERVEUR, pas de ce qu'on
           vient d'envoyer : c'est lui qui a le dernier mot sur ce qui a été
           réellement retenu. */
        pjRendreHistorique(j.historique, pid);
      })
      .catch(function () { pjMsg("État non enregistré.", "ko"); });
  }

  /* ══════════════════════════════════════════════════════════════════════
     LE PROGRAMME MULTI-SITES
     ══════════════════════════════════════════════════════════════════════
     UNE LIGNE PAR SITE, ET RIEN D'OBLIGATOIRE. Un site connu par son seul nom
     compte dans l'effectif et figure dans les absents de tout le reste : c'est
     exactement l'information utile au début d'un programme, quand la moitié
     des sites n'est encore qu'une intention. Un formulaire qui exigerait tout
     ferait inventer des chiffres pour pouvoir cliquer.

     LES TOTAUX PORTENT LEUR PÉRIMÈTRE. C'est la page qui l'affiche, mais c'est
     le serveur qui le compte : un total dont on ne sait pas combien de sites
     il couvre n'est pas un total, c'est une impression. */
  var PROG_CHAMPS = null, PROG_N = 0;

  function progFormulaire(champs) {
    PROG_CHAMPS = champs || [];
    var z = $("#ig-prog-sites");
    if (!z) return;
    z.innerHTML = "";
    PROG_N = 0;
    progAjouter();
    progAjouter();
  }

  /* Le nom lisible d'une nature de site, et ce qu'elle engage — tous deux
     pris au glossaire servi par le cadre. La liste affichait jusqu'ici la
     clé brute, « greenfield », avec une infobulle qui ne s'affichait pas. */
  function nomNature(cle) {
    var g = CADRE.glossaire && CADRE.glossaire.nature_site;
    return (g && g[cle] && g[cle].nom) || cle;
  }

  function progImplication(sel) {
    var box = $("#" + sel.id + "-i");
    if (!box) return;
    var g = CADRE.glossaire && CADRE.glossaire.nature_site;
    var e = g && g[sel.value];
    if (!e) { box.hidden = true; box.textContent = ""; return; }
    box.hidden = false;
    box.textContent = e.aide || e.nom || "";
  }

  function progAjouter() {
    var z = $("#ig-prog-sites");
    if (!z || !PROG_CHAMPS) return;
    var i = PROG_N++;
    var d = document.createElement("div");
    d.className = "ig-prog-s";
    d.setAttribute("data-site", String(i));
    var h = '<div class="ig-prog-h"><b>Site ' + (i + 1) + "</b>"
      + '<button type="button" class="ig-prog-x" aria-label="Retirer ce site">×</button>'
      + "</div><div class=\"dc-grille\">";
    PROG_CHAMPS.forEach(function (c) {
      var id = "ig-prog-" + i + "-" + c.id;
      h += '<label class="dc-champ" for="' + id + '"><span class="dc-lab">'
        + esc(c.label)
        + (c.unite ? ' <span class="dc-unite">(' + esc(c.unite) + ')</span>' : "")
        + "</span>";
      if (c.type === "liste") {
        /* PAS D'INFOBULLE SUR L'OPTION. Le menu déroulant natif est dessiné
           par le système d'exploitation, qui ignore les attributs de la
           page : un `data-info` posé là ne s'affiche dans aucun navigateur.
           L'explication de la nature retenue se montre APRÈS sélection, comme
           pour l'identification du projet. */
        h += '<select id="' + id + '" data-prog="' + esc(c.id) + '">'
          + '<option value="">— non précisé —</option>';
        (c.options || []).forEach(function (o) {
          h += '<option value="' + esc(o) + '">' + esc(nomNature(o))
            + "</option>";
        });
        h += "</select>";
      } else if (c.type === "booleen") {
        h += '<select id="' + id + '" data-prog="' + esc(c.id) + '">'
          + '<option value="">— non précisé —</option>'
          + '<option value="oui">Oui</option><option value="non">Non</option>'
          + "</select>";
      } else {
        h += '<input id="' + id + '" data-prog="' + esc(c.id) + '" type="text"'
          + (c.type === "nombre" ? ' inputmode="decimal"' : "")
          + ' placeholder="—">';
      }
      if (c.aide) h += '<span class="dc-aide">' + esc(c.aide) + "</span>";
      h += '<span class="ig-impl" id="' + id + '-i" hidden></span></label>';
    });
    d.innerHTML = h + "</div>";
    z.appendChild(d);
    d.querySelectorAll('select[data-prog="nature"]').forEach(function (sel) {
      sel.addEventListener("change", function () { progImplication(sel); });
    });
    var x = d.querySelector(".ig-prog-x");
    if (x) {
      x.addEventListener("click", function () {
        /* On ne renumérote PAS les lignes restantes : un « Site 3 » qui
           devient « Site 2 » sous les yeux de celui qui vient de supprimer le
           deuxième fait douter de ce qu'il a supprimé. Le libellé est un
           repère de saisie, pas un rang. */
        d.remove();
      });
    }
  }

  function progLire() {
    var sites = [];
    document.querySelectorAll("#ig-prog-sites .ig-prog-s").forEach(function (d) {
      var s = {}, rempli = false;
      d.querySelectorAll("[data-prog]").forEach(function (e) {
        var v = (e.value || "").trim();
        if (v === "") return;
        rempli = true;
        var cle = e.getAttribute("data-prog");
        s[cle] = (v === "oui") ? true : (v === "non") ? false : v;
      });
      /* Une ligne entièrement vide n'est pas un site : la compter gonflerait
         l'effectif du programme et ferait apparaître un « site sans nom »
         dans la liste des absents de chaque total. */
      if (rempli) sites.push(s);
    });
    return sites;
  }

  function progConsolider() {
    var msg = $("#ig-prog-msg"), out = $("#ig-prog-out");
    if (!out) return;
    var sites = progLire();
    if (!sites.length) {
      msg.textContent = "Renseignez au moins un site.";
      return;
    }
    msg.textContent = "Consolidation de " + sites.length + " site"
      + (sites.length > 1 ? "s" : "") + "…";
    demander("/api/datacenter/programme", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sites: sites }),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) {
          msg.textContent = (j && j.message) || "Consolidation indisponible.";
          return;
        }
        msg.textContent = "";
        progRendre(j);
      })
      .catch(function () { msg.textContent = "Consolidation indisponible."; });
  }

  /* Un total avec son périmètre. LE PÉRIMÈTRE N'EST PAS UNE NOTE DE BAS DE
     PAGE : c'est lui qui décide de ce que le total vaut, et il s'affiche
     contre le chiffre. */
  function progTotal(cle, agr, unite, dec) {
    if (!agr || agr.valeur === null || agr.valeur === undefined) {
      return '<div class="ig-prog-k"><span class="ig-prog-kn"'
        + info("kpi:" + cle) + ">" + esc(((CADRE.glossaire || {}).kpi
            || {})[cle] ? CADRE.glossaire.kpi[cle].nom : cle)
        + '</span><b class="ig-prog-kv">—</b>'
        + '<span class="ig-prog-kp">non renseigné</span></div>';
    }
    var g = ((CADRE.glossaire || {}).kpi || {})[cle];
    return '<div class="ig-prog-k' + (agr.complet ? "" : " ig-prog-partiel")
      + '"><span class="ig-prog-kn"' + info("kpi:" + cle) + ">"
      + esc(g ? g.nom : cle) + "</span>"
      + '<b class="ig-prog-kv">' + esc(nombreFr(agr.valeur, dec))
      + (unite ? ' <span class="ig-prog-ku">' + esc(unite) + "</span>" : "")
      + "</b>"
      + '<span class="ig-prog-kp">'
      + (agr.complet
          ? "sur les " + agr.sites_comptes + " sites"
          : "SOUS-TOTAL — " + agr.sites_comptes + " site"
            + (agr.sites_comptes > 1 ? "s" : "") + " sur "
            + (agr.sites_comptes + (agr.sites_absents || []).length))
      + "</span>"
      + ((agr.sites_absents && agr.sites_absents.length)
          ? '<span class="ig-prog-ka">absents : '
            + esc(agr.sites_absents.join(", ")) + "</span>" : "")
      + "</div>";
  }

  function nombreFr(x, dec) {
    if (x === null || x === undefined) return "—";
    var n = Number(x);
    var s = (dec === undefined) ? String(Math.round(n)) : n.toFixed(dec);
    return s.replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }

  function progRendre(j) {
    var out = $("#ig-prog-out"), v = j.programme;
    if (v.vide) {
      out.innerHTML = '<p class="note">' + esc(v.note) + "</p>";
      return;
    }
    var h = '<p class="ig-prog-l">' + esc(v.lecture) + "</p>";
    h += '<div class="ig-prog-kpi">'
      + progTotal("capacite_engagee", v.capacite_engagee_kw, "kW")
      + progTotal("capacite_livree", v.capacite_livree_kw, "kW")
      + progTotal("capex_par_kw", v.capex_par_kw.valeur !== null
          ? { valeur: v.capex_par_kw.valeur, complet: v.capex_par_kw.complet,
              sites_comptes: v.capex_par_kw.sites_comptes, sites_absents: [] }
          : null, "€/kW")
      + progTotal("opex_par_kw_an", v.opex_par_kw_an.valeur !== null
          ? { valeur: v.opex_par_kw_an.valeur, complet: v.opex_par_kw_an.complet,
              sites_comptes: v.opex_par_kw_an.sites_comptes, sites_absents: [] }
          : null, "€/kW/an")
      + progTotal("pue_programme", v.pue_programme, "", 3)
      + "</div>";
    /* UN RATIO NON RENDU DIT POURQUOI. « — » sans motif se lit comme une
       panne ; « les deux grandeurs ne couvrent pas les mêmes sites » se lit
       comme une consigne. */
    ["capex_par_kw", "opex_par_kw_an"].forEach(function (k) {
      if (v[k] && v[k].valeur === null && v[k].pourquoi) {
        h += '<p class="ig-prog-w">' + esc(v[k].pourquoi) + "</p>";
      }
    });
    /* LE CHEMIN CRITIQUE. Pas une moyenne : un programme livre quand son
       dernier site livre. */
    var cc = v.chemin_critique;
    h += '<div class="ig-prog-cc">' + (cc.connu
      ? "<b>Chemin critique — " + esc(cc.site) + "</b> · mise en service "
        + esc(String(cc.date)) + '<span class="ig-tr-r">' + esc(cc.note)
        + "</span>"
      : "<b>Chemin critique inconnu</b>" + '<span class="ig-tr-r">'
        + esc(cc.pourquoi) + "</span>") + "</div>";
    /* LA PROMESSE « ZÉRO DÉFAUT », avec ses deux chiffres ensemble. */
    var z = v.zero_defaut;
    h += '<div class="ig-prog-z"><b>Livraison « zéro défaut »</b>'
      + '<p class="ig-prog-zl">' + esc(z.lecture) + "</p>"
      + '<p class="ig-prog-zn"><i>Ce que ce n\'est pas</i> — '
      + esc(z.n_est_pas) + "</p>";
    if (j.zero_defaut && j.zero_defaut.conditions) {
      h += "<ul class=\"ig-prog-zc\">";
      j.zero_defaut.conditions.forEach(function (c) {
        h += "<li>" + esc(c) + "</li>";
      });
      h += "</ul><p class=\"ig-prog-zn\"><i>Ce que la promesse coûte</i> — "
        + esc(j.zero_defaut.cout) + "</p>";
    }
    h += "</div>";
    /* LA RÉPARTITION par nature et par phase. */
    h += '<div class="ig-prog-rep"><b>Répartition</b><ul>';
    Object.keys(v.par_nature).forEach(function (k) {
      var n = v.par_nature[k];
      if (!n.sites) return;
      h += "<li>" + (k.charAt(0) === "_" ? "" : '<span' + info("nature_site:" + k) + ">")
        + esc(n.nom) + (k.charAt(0) === "_" ? "" : "</span>")
        + " — " + n.sites + " site" + (n.sites > 1 ? "s" : "")
        + (n.capacite_kw ? " · " + esc(nombreFr(n.capacite_kw)) + " kW" : "")
        + (n.pourquoi ? '<span class="ig-prog-ka">' + esc(n.pourquoi) + "</span>" : "")
        + "</li>";
    });
    (v.par_phase || []).forEach(function (p) {
      h += "<li>Phase " + esc(p.code) + " — " + esc(p.nom) + " : " + p.sites
        + (p.hors_cadre ? " <i>(hors du cadre de phases)</i>" : "") + "</li>";
    });
    h += "</ul></div>";
    /* CE QUI NE SE RÉPLIQUE PAS d'un pays à l'autre — affiché seulement quand
       le programme est effectivement multi-pays. Une mise en garde servie à
       un programme national apprend à ne plus les lire. */
    if (v.par_pays.multi_pays) {
      h += '<div class="ig-prog-int"><b>Programme multi-pays : ce qui ne se '
        + "réplique pas</b>";
      v.par_pays.ce_qui_ne_se_replique_pas.forEach(function (x) {
        h += '<div class="ig-prog-i"><b>' + esc(x.sujet) + "</b>"
          + "<p>" + esc(x.detail) + "</p>"
          + '<p class="ig-prog-if"><i>À faire</i> — ' + esc(x.a_faire)
          + "</p></div>";
      });
      h += "</div>";
    }
    /* CE QUI NE SE CONSOLIDE PAS DU TOUT. Une absence silencieuse se lirait
       comme un oubli. */
    (v.non_consolidables || []).forEach(function (x) {
      h += '<div class="ig-prog-nc"><b>' + esc(x.grandeur)
        + " — ne se consolide pas</b><p>" + esc(x.pourquoi) + "</p>"
        + '<p class="ig-prog-if"><i>À la place</i> — ' + esc(x.a_la_place)
        + "</p><ul>";
      x.sites.forEach(function (s) {
        h += "<li>" + esc(s.nom) + " (" + esc(s.pays) + ") — "
          + esc(s.regime) + "</li>";
      });
      h += "</ul></div>";
    });
    /* LES PARTIES PRENANTES, et leur FENÊTRE — le moment après lequel leur
       décision coûte cher. C'est l'information qui manque le plus souvent,
       parce qu'elle ne figure dans aucun organigramme. */
    if (j.parties_prenantes) {
      h += '<h3 class="ig-tr-st">Qui décide, et jusqu\'à quand</h3>'
        + '<div class="ig-tr-sol">';
      Object.keys(j.parties_prenantes).forEach(function (k) {
        var pp = j.parties_prenantes[k];
        h += '<div class="ig-tr-s"><b' + info("partie_prenante:" + k) + ">"
          + esc(pp.nom) + "</b>"
          + "<p><i>Décide</i> — " + esc(pp.decide) + "</p>"
          + "<p><i>Sa fenêtre</i> — " + esc(pp.fenetre) + "</p>"
          + "<p><i>Quand ça coince</i> — " + esc(pp.quand_ca_coince) + "</p></div>";
      });
      h += "</div>";
    }
    h += '<p class="ig-icpe-res">' + esc(v.reserve) + "</p>";
    out.innerHTML = h;
  }


  /* ══════════════════════════════════════════════════════════════════════
     LE CRIBLAGE ICPE
     ══════════════════════════════════════════════════════════════════════
     CE QUE LA LISTE DÉROULANTE REND POSSIBLE. Cinq rubriques, trois états —
     atteinte, sans donnée, écartée — et pour chacune un régime, une distance
     au seuil suivant et ce qu'elle change pour la mission. Tout afficher à
     plat noierait les deux qui comptent ; une liste ordonnée par gravité met
     en tête celle qui commande le planning.

     L'ORDRE EST CELUI DE L'ACTION, pas celui de la nomenclature : ce qui est
     atteint d'abord — du régime le plus lourd au plus léger —, ce qui manque
     ensuite, ce qui est écarté en dernier. Il vient du serveur : la page ne
     retrie rien, sans quoi les deux ordres divergeraient. */
  /* ═══════════════════════════════════════════════════════════════════════
     LE RACCORDEMENT ET LA PRODUCTION SUR SITE

     CE QUE CE BLOC AFFICHE ET QU'AUCUN AUTRE N'AFFICHE : les TERMES du calcul,
     ligne à ligne. Une part de calcul non servie livrée comme un pourcentage
     nu ne se discute ni avec un gestionnaire de réseau, ni avec un client :
     elle se croit ou elle se rejette. Montrer la puissance tenue, la puissance
     appelée, le déficit horaire, le creux de rattrapage et ce qui a pu y être
     reporté, c'est donner de quoi contester — donc de quoi convaincre.

     LES TROIS BANDEAUX QUI ACCOMPAGNENT LE CHIFFRE, et pourquoi aucun n'est
     décoratif : le plafonnement par le creux dit si ajouter de la flexibilité
     servira encore ; la bascule de régime dit ce que la production sur site
     coûte en instruction administrative ; l'écart de duty dit ce qui, dans la
     pile installée, compte pour le niveau de disponibilité — et ce qui n'y
     compte pas. */
  var RESEAU_CHAMPS = null, RESEAU = null;

  function reseauFormulaire(champs) {
    var z = $("#ig-res-form");
    if (!z) return;
    RESEAU_CHAMPS = champs || [];
    var h = '<div class="dc-grille">';
    RESEAU_CHAMPS.forEach(function (c) {
      var id = "ig-res-" + c.id;
      h += '<label class="dc-champ" for="' + id + '">'
        + '<span class="dc-lab">' + esc(c.label)
        + (c.unite ? ' <span class="dc-unite">(' + esc(c.unite) + ')</span>' : "")
        + "</span>";
      if (c.type === "choix") {
        /* « — non précisé — » EN PREMIER, et jamais présélectionné. Sur ce
           formulaire plus qu'ailleurs, une valeur par défaut deviendrait la
           réponse : personne ne conteste un champ déjà rempli, et une
           fréquence d'effacement supposée déplace le résultat d'un facteur
           trois. */
        h += '<select id="' + id + '" data-res="' + esc(c.id) + '">'
          + '<option value="">— non précisé —</option>';
        (c.options || []).forEach(function (o) {
          h += '<option value="' + esc(o) + '">' + esc(nomOption(c.id, o))
            + "</option>";
        });
        h += "</select>";
      } else {
        h += '<input id="' + id + '" data-res="' + esc(c.id)
          + '" type="text" inputmode="decimal" placeholder="—">';
      }
      if (c.aide) h += '<span class="dc-aide">' + esc(c.aide) + "</span>";
      /* CE QUE L'OPTION ENGAGE, APRÈS SÉLECTION — et non en infobulle sur
         l'option. Le menu déroulant natif est dessiné par le système : un
         `data-info` posé sur une <option> ne s'affiche jamais, et la règle
         qui vérifierait sa présence passerait sur une infobulle morte. */
      h += '<span class="ig-impl" id="' + id + '-i" hidden></span></label>';
    });
    z.innerHTML = h + "</div>";
    z.querySelectorAll("select[data-res]").forEach(function (sel) {
      sel.addEventListener("change", function () { reseauImplication(sel); });
    });
  }

  /* La famille de glossaire qui explique les options d'un champ, ou null
     quand le champ n'en a pas. Une seule fonction pour le nom et pour
     l'explication : deux tables de correspondance auraient divergé. */
  function familleOption(champ) {
    return (champ === "mode_raccordement") ? "mode_raccordement"
      : (champ === "btm_classe_iso") ? "classe_groupe" : null;
  }

  /* Le nom lisible d'une option, pris au glossaire du module quand il en
     tient un. Sans cela, la liste afficherait « non_ferme ». */
  function nomOption(champ, val) {
    var fam = familleOption(champ);
    var g = fam && CADRE.glossaire && CADRE.glossaire[fam];
    return (g && g[val] && g[val].nom) || val;
  }

  function reseauImplication(sel) {
    var cid = sel.getAttribute("data-res");
    var box = $("#" + sel.id + "-i");
    if (!box) return;
    var fam = familleOption(cid);
    var g = fam && CADRE.glossaire && CADRE.glossaire[fam];
    var e = g && g[sel.value];
    if (!e) { box.hidden = true; box.textContent = ""; return; }
    box.hidden = false;
    box.textContent = e.aide || e.nom || "";
  }

  function reseauLire() {
    /* LE PROFIL DU MOTEUR ET LES GRANDEURS DU CRIBLAGE VOYAGENT AVEC. La
       production sur site s'ajoute aux groupes de secours déjà déclarés
       ailleurs sur la page, et c'est le CUMUL qui décide du régime. Les
       demander une seconde fois ici les ferait diverger. */
    var p = (typeof icpeLire === "function") ? icpeLire() : lireProfil();
    document.querySelectorAll("#ig-res-form [data-res]").forEach(function (el) {
      var v = (el.value || "").trim();
      if (v !== "") p[el.getAttribute("data-res")] = v;
    });
    return p;
  }

  function reseauChiffrer() {
    var msg = $("#ig-res-msg"), out = $("#ig-res-out");
    if (!out) return;
    msg.textContent = "Chiffrage…";
    demander("/api/datacenter/reseau", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(reseauLire()),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) {
          msg.textContent = (j && j.message) || "Chiffrage indisponible.";
          return;
        }
        RESEAU = j;
        msg.textContent = "";
        reseauRendre(j);
      })
      .catch(function () { msg.textContent = "Chiffrage indisponible."; });
  }

  function pourcent(x) {
    return (x === null || x === undefined) ? "—"
      : (Math.round(x * 1000) / 10).toFixed(1) + " %";
  }

  function mwh(x) {
    return (x === null || x === undefined) ? "—"
      : Math.round(x / 1000).toLocaleString("fr-FR") + " MWh";
  }

  function reseauRendre(j) {
    var out = $("#ig-res-out"), e = j.etude || {};
    if (e.nature === "refus") {
      out.innerHTML = '<p class="note">' + esc(e.message) + "</p>";
      return;
    }
    var h = "";

    /* Les saisies refusées d'abord : une valeur illisible écartée en silence
       ferait calculer sur un champ absent, et le résultat serait juste pour
       une question qui n'a pas été posée. */
    if (j.rejets && j.rejets.length) {
      h += '<div class="ig-encart"><b>Saisies non retenues.</b><ul>';
      j.rejets.forEach(function (r) {
        h += "<li>" + esc(r.label) + " — " + esc(r.message) + "</li>";
      });
      h += "</ul></div>";
    }

    if (e.mode) h += reseauMode(e.mode);
    h += reseauNonServi(e.non_servi, e.marge);
    if (e.production_sur_site) h += reseauProduction(e.production_sur_site);
    h += '<p class="ig-icpe-res">' + esc(e.reserve) + "</p>";
    out.innerHTML = h;
  }

  function reseauMode(m) {
    var h = '<div class="rc-card"><h3>' + esc(m.nom) + "</h3>"
      + "<p><b>Ce que le gestionnaire garantit —</b> " + esc(m.garantit) + "</p>"
      + "<p><b>Ce qu'il ne garantit pas —</b> " + esc(m.ne_garantit_pas) + "</p>"
      + "<p><b>Ce qui fixe le délai —</b> " + esc(m.ce_qui_fixe_le_delai) + "</p>";
    if (m.a_ecrire_dans_la_convention) {
      h += '<div class="ig-encart"><b>À faire écrire dans la convention.</b> '
        + esc(m.a_ecrire_dans_la_convention) + "</div>";
    }
    /* LE REPÈRE PUBLIÉ, AVEC SON AUTEUR ET SA RÉSERVE — et la mention qu'il
       n'entre dans aucun calcul. Un ordre de grandeur de marché affiché sans
       son auteur se lit comme un résultat du moteur. */
    if (m.repere) {
      h += '<div class="ig-encart ig-repere"><b>Ce qui s\'observe ailleurs.</b> '
        + esc(m.repere.enonce)
        + ' <span class="note">' + esc(m.repere.editeur || "")
        + (m.repere.date ? ", " + esc(m.repere.date) : "")
        + (m.repere.nature ? " — " + esc(m.repere.nature) : "")
        + ". Repère de comparaison : il n'entre dans aucun calcul de cette "
        + "page.</span>";
      if (m.repere.reserve) {
        h += '<p class="note">' + esc(m.repere.reserve) + "</p>";
      }
      h += "</div>";
    }
    return h + "</div>";
  }

  function reseauNonServi(r, marge) {
    if (!r) return "";
    if (r.nature === "incomplet" || r.nature === "refus") {
      var hh = '<div class="rc-card"><h3>Le calcul non servi</h3>'
        + "<p>" + esc(r.message) + "</p>";
      if (r.manques && r.manques.length) {
        hh += "<ul>";
        r.manques.forEach(function (m) { hh += "<li>" + esc(m) + "</li>"; });
        hh += "</ul>";
      }
      return hh + "</div>";
    }
    var t = r.termes, hy = r.hypotheses;
    var h = '<div class="rc-card"><h3>Le calcul non servi</h3>'
      + '<div class="ig-icpe-tete"><span class="ig-icpe-reg">'
      + pourcent(r.part_non_servie) + " du calcul annuel</span>"
      + '<span class="ig-icpe-n">' + esc(r.lecture) + "</span></div>";

    /* LES TERMES, DANS L'ORDRE OÙ ILS S'ENCHAÎNENT. C'est la partie qui rend
       le chiffre opposable ; la masquer derrière un dépliant reviendrait à ne
       pas la donner. */
    h += '<table class="ig-tab"><tbody>'
      + reseauLigne("Puissance informatique installée", t.puissance_installee_kw, "kW")
      + reseauLigne("Puissance appelée par le calcul", t.puissance_appelee_kw, "kW")
      + reseauLigne("Puissance tenue pendant l'effacement",
                    t.puissance_tenue_en_effacement_kw, "kW")
      + reseauLigne("Déficit à l'heure d'appel", t.deficit_horaire_kw, "kW")
      + "<tr><td>Non servi avant report</td><td>" + mwh(t.non_servi_brut_kwh_an) + "</td></tr>"
      + "<tr><td>Creux disponible pour rattraper</td><td>" + mwh(t.creux_de_rattrapage_kwh_an) + "</td></tr>"
      + "<tr><td>Effectivement reporté</td><td>" + mwh(t.reporte_kwh_an) + "</td></tr>"
      + "<tr><td><b>Non servi net</b></td><td><b>" + mwh(t.non_servi_net_kwh_an) + "</b></td></tr>"
      + "</tbody></table>";

    h += '<p class="note">Hypothèses retenues — part non ferme '
      + pourcent(hy.part_non_ferme) + ", appelée sur "
      + pourcent(hy.frequence_effacement) + " des heures, profondeur "
      + pourcent(hy.profondeur_effacement)
      + (hy.profondeur_supposee ? " (supposée)" : "")
      + ", taux de charge " + pourcent(hy.taux_charge)
      + ", part reportable " + pourcent(hy.part_reportable)
      + " — " + esc(hy.origine_part_reportable) + ".</p>";

    if (r.alerte_profondeur) {
      h += '<div class="ig-encart"><b>Profondeur supposée.</b> '
        + esc(r.alerte_profondeur) + "</div>";
    }
    /* LE BANDEAU QUI CHANGE UNE DÉCISION. Tant que le report n'est pas
       plafonné, chercher de la flexibilité réduit encore le chiffre ; une
       fois plafonné, cela ne sert plus à rien et seule de la puissance ferme
       agit. Les deux conduites sont opposées, et rien d'autre sur la page ne
       le dit. */
    if (r.plafonne_par_le_creux) {
      h += '<div class="ig-encart ig-alerte"><b>Le report est plafonné par le '
        + "creux, pas par la flexibilité.</b> Il ne reste pas assez d'heures "
        + "libres pour rattraper le travail décalé : chercher davantage de "
        + "charge reportable ne réduira plus ce chiffre. À ce point, seule de "
        + "la puissance ferme sur site agit encore.</div>";
    }
    if (marge && marge.nature === "calcule") {
      h += '<div class="ig-encart"><b>Effet sur le résultat.</b> '
        + esc(marge.lecture) + ' <span class="note">' + esc(marge.pourquoi)
        + "</span></div>";
    } else if (marge && marge.nature === "refus") {
      h += '<p class="note">' + esc(marge.message) + "</p>";
    }
    h += '<p class="note">' + esc(r.limite) + "</p>";
    return h + "</div>";
  }

  function reseauLigne(nom, val, unite) {
    return "<tr><td>" + esc(nom) + "</td><td>"
      + ((val === null || val === undefined) ? "—"
         : Math.round(val).toLocaleString("fr-FR") + " " + unite)
      + "</td></tr>";
  }

  function reseauProduction(p) {
    var h = '<div class="rc-card"><h3>La production sur site, et ce qu\'elle '
      + "déclenche</h3>";
    if (p.nature === "incomplet") {
      h += "<ul>";
      (p.manques || []).forEach(function (m) { h += "<li>" + esc(m) + "</li>"; });
      return h + "</ul></div>";
    }
    (p.alertes || []).forEach(function (a) {
      h += '<div class="ig-encart ig-alerte">' + esc(a) + "</div>";
    });
    if (p.icpe) {
      h += "<p><b>Régime administratif —</b> sans la production sur site&nbsp;: "
        + esc(p.icpe.regime_sans_production_nom) + ". Avec&nbsp;: "
        + esc(p.icpe.regime_avec_production_nom) + ".</p>";
    }
    if (p.allegement_heures) {
      h += '<div class="ig-encart">' + esc(p.allegement_heures) + "</div>";
    }
    if (p.combustible) {
      var c = p.combustible;
      h += "<p><b>Combustible —</b> ";
      if (c.voie === "gaz") {
        h += esc(c.stockage) + " " + esc(c.en_echange) + "</p>"
          + '<p class="note">' + esc(c.a_obtenir) + "</p>";
      } else {
        h += "réserve de douze heures au titre de la disponibilité : "
          + Math.round(c.reserve_tier_m3 || 0).toLocaleString("fr-FR") + " m³";
        if (c.volume_m3) {
          h += " ; volume pour les heures de production déclarées : "
            + Math.round(c.volume_m3).toLocaleString("fr-FR") + " m³";
        }
        h += ".</p>";
        if (c.manque) h += '<p class="note">Manque — ' + esc(c.manque) + "</p>";
        if (c.hors_perimetre) {
          h += '<div class="ig-encart ig-alerte">' + esc(c.hors_perimetre)
            + "</div>";
        }
      }
    }
    if (p.duty) {
      h += '<div class="ig-encart"><b>Tenir un effacement n\'est pas '
        + "secourir.</b> "
        + esc(p.duty.lecture || p.duty.manque || "")
        + ' <span class="note">' + esc(p.duty.pourquoi || "") + "</span></div>";
    }
    return h + "</div>";
  }

  var ICPE_CHAMPS = null, ICPE = null;

  function icpeFormulaire(champs) {
    var z = $("#ig-icpe-form");
    if (!z) return;
    ICPE_CHAMPS = champs || [];
    var h = '<div class="dc-grille">';
    ICPE_CHAMPS.forEach(function (c) {
      var id = "ig-icpe-" + c.id;
      h += '<label class="dc-champ" for="' + id + '">'
        + '<span class="dc-lab">' + esc(c.label)
        + (c.unite ? ' <span class="dc-unite">(' + esc(c.unite) + ')</span>' : "")
        /* La rubrique concernée est portée par le champ lui-même, et son
           infobulle explique ce que la nomenclature vise. Sans elle, on
           demande une puissance thermique sans dire pourquoi. */
        + ' <span class="ig-icpe-r"' + info("rubrique_icpe:" + c.rubrique)
        + ">" + esc(c.rubrique) + "</span></span>";
      if (c.type === "booleen") {
        /* TROIS ÉTATS, PAS DEUX. « Non précisé » n'est pas « non » : le seuil
           de la rubrique 2925 n'est pas le même selon la technologie, et une
           case décochée par défaut ferait retenir le seuil le plus permissif
           pour un local dont personne n'a rien dit. */
        h += '<select id="' + id + '" data-icpe="' + esc(c.id) + '">'
          + '<option value="">— non précisé —</option>'
          + '<option value="oui">Oui — accumulateurs au plomb ouverts</option>'
          + '<option value="non">Non — technologie étanche ou lithium</option>'
          + "</select>";
      } else {
        h += '<input id="' + id + '" data-icpe="' + esc(c.id)
          + '" type="text" inputmode="decimal" placeholder="—">'
          /* LE MENU DES VALEURS D'ESSAI, et l'échelle des seuils sous le
             champ. Les deux viennent du serveur DÉJÀ CONVERTIS dans l'unité
             de saisie : deux de ces champs se saisissent dans une unité qui
             n'est pas celle du seuil, et refaire la conversion ici la ferait
             diverger de celle du criblage. */
          + '<select class="ig-seuil-sel" data-vise="' + esc(c.id) + '">'
          + '<option value="">— proposer une valeur d\u2019essai —</option>'
          + "</select>"
          + '<span class="ig-echelle" id="' + id + '-e"></span>';
      }
      if (c.aide) h += '<span class="dc-aide">' + esc(c.aide) + "</span>";
      h += "</label>";
    });
    z.innerHTML = h + "</div>";
    /* Le contour se remet à jour à chaque frappe, pas seulement au criblage :
       le lecteur doit voir le seuil se franchir pendant qu'il tape, sinon il
       ne fait le lien qu'après coup — et souvent pas du tout. */
    z.querySelectorAll("input[data-icpe]").forEach(function (el) {
      el.addEventListener("input", function () { icpeSeuilEtat(el); });
    });
    z.querySelectorAll("select[data-icpe]").forEach(function (el) {
      el.addEventListener("change", icpeEchelles);
    });
    z.querySelectorAll(".ig-seuil-sel").forEach(function (sel) {
      sel.addEventListener("change", function () {
        if (!sel.value) return;
        var cible = $("#ig-icpe-" + sel.getAttribute("data-vise"));
        if (cible) { cible.value = sel.value; icpeSeuilEtat(cible); }
        sel.value = "";
      });
    });
    icpeEchelles();
  }

  /* LE BARÈME COMPLET, LES CINQ RUBRIQUES. Le formulaire ne porte que les
     grandeurs qu'il demande ; une rubrique dont la grandeur se saisit
     ailleurs — la charge en fluide frigorigène, au profil de l'installation —
     n'y apparaîtrait pas, et le lecteur conclurait qu'elle n'est pas criblée.
     Le tableau les montre toutes, dans l'unité de la NOMENCLATURE, et dit où
     se saisit ce qui manque. */
  function icpeBareme() {
    var z = $("#ig-icpe-bareme");
    var b = CADRE.icpe_bareme || {};
    if (!z || !b.rubriques) return;
    var h = '<div class="rc-card"><h3>Les seuils, rubrique par rubrique</h3>'
      + '<div class="ig-bareme-w"><table class="ig-bareme"><thead><tr>'
      + "<th>Rubrique</th><th>Grandeur mesurée</th><th>Seuils</th>"
      + "</tr></thead><tbody>";
    Object.keys(b.rubriques).forEach(function (code) {
      var r = b.rubriques[code];
      h += '<tr><td class="n"' + info("rubrique_icpe:" + code) + ">"
        + esc(r.numero) + "<br><span class=\"dc-unite\">" + esc(r.unite)
        + "</span></td><td>" + esc(r.intitule)
        + '<br><span class="ig-echelle-n">' + esc(r.grandeur) + "</span>"
        + (r.saisie_ailleurs
            ? '<br><span class="ig-echelle-n">' + esc(r.saisie_ailleurs)
              + "</span>"
            : "")
        + "</td><td>";
      (r.variantes || []).forEach(function (v) {
        h += '<div class="ig-echelle">';
        if (v.quand) h += '<span class="ig-echelle-q">' + esc(v.quand) + "</span>";
        if (v.regime_impose) {
          h += '<span class="ig-echelle-n">Régime imposé&nbsp;: '
            + esc(v.regime_impose_nom) + "</span>";
        }
        (v.paliers || []).forEach(function (p) {
          h += '<span class="ig-palier ig-palier-' + esc(p.regime) + '">'
            + (p.des_le_premier ? "dès la première unité"
                                : "≥ " + esc(String(p.a_partir_de)) + " "
                                  + esc(r.unite))
            + " → " + esc(p.regime_nom) + "</span>";
        });
        h += "</div>";
      });
      h += "</td></tr>";
    });
    h += "</tbody></table></div>"
      + '<p class="ig-icpe-res">' + esc(b.texte || "")
      + " " + esc(b.marge_note || "") + "</p></div>";
    z.innerHTML = h;
  }

  /* ── LES SEUILS SOUS LE CHAMP ─────────────────────────────────────────────
     TROIS RUBRIQUES CHANGENT DE BARÈME selon une caractéristique du projet —
     le circuit ouvert ou fermé du refroidissement, le dégagement d'hydrogène
     des batteries. Le barème affiché doit suivre le choix en cours, sinon le
     lecteur vise un seuil qui ne le concerne pas. La variante applicable se
     lit sur le DISCRIMINANT servi par le module ; aucune règle n'est écrite
     ici. */
  function icpeVariante(e) {
    var vs = e.variantes || [];
    var d = e.discriminant;
    if (!d) return vs[0];
    var val = null;
    if (d.champ === "refroidissement") {
      val = (lireProfil() || {}).refroidissement || "";
    } else {
      var el = $("#ig-icpe-" + d.champ);
      val = el ? el.value : "";
    }
    var cle = (d.valeurs || {})[val];
    if (cle === undefined) cle = d.sinon;
    if (cle === null || cle === undefined) return null;
    return vs.filter(function (v) { return v.cle === cle; })[0] || null;
  }

  function icpeBaremeChamp(cid) {
    var b = CADRE.icpe_bareme || {};
    return (b.champs || {})[cid] || null;
  }

  function icpeEchelles() {
    (ICPE_CHAMPS || []).forEach(function (c) {
      if (c.type === "booleen") return;
      var e = icpeBaremeChamp(c.id);
      var box = $("#ig-icpe-" + c.id + "-e");
      var sel = document.querySelector('.ig-seuil-sel[data-vise="' + c.id + '"]');
      if (!e || !box) return;
      var v = icpeVariante(e);
      box.innerHTML = icpeEchelleTexte(e, v);
      if (sel) {
        var h = '<option value="">— proposer une valeur d\u2019essai —</option>';
        ((v && v.reperes) || []).forEach(function (r) {
          h += '<option value="' + esc(String(r.valeur)) + '">'
            + esc(String(r.valeur)) + " " + esc(e.unite || "") + " — "
            + esc(r.libelle) + " (" + esc(r.regime_nom) + ")</option>";
        });
        sel.innerHTML = h;
        /* Un menu sans proposition n'invite à rien et laisse croire à une
           panne : il disparaît au lieu de rester vide. */
        sel.hidden = !((v && v.reperes) || []).length;
      }
      var el = $("#ig-icpe-" + c.id);
      if (el) icpeSeuilEtat(el);
    });
  }

  function icpeEchelleTexte(e, v) {
    if (!v) {
      var d = e.discriminant || {};
      return '<span class="ig-echelle-n">'
        + esc(d.sinon_pourquoi || "Rubrique non applicable en l\u2019état.")
        + "</span>";
    }
    var h = "";
    if (v.quand) h += '<span class="ig-echelle-q">' + esc(v.quand) + "</span>";
    if (v.regime_impose) {
      return h + '<span class="ig-echelle-n">Régime imposé&nbsp;: '
        + esc(v.regime_impose_nom) + ". " + esc(v.note || "") + "</span>";
    }
    (v.paliers || []).forEach(function (p) {
      h += '<span class="ig-palier ig-palier-' + esc(p.regime) + '">'
        + (p.des_le_premier
            ? "dès la première unité"
            : "≥ " + esc(String(p.a_partir_de_champ)) + " "
              + esc(e.unite || ""))
        + " → " + esc(p.regime_nom) + "</span>";
    });
    if (e.conversion) {
      h += '<span class="ig-echelle-n">Seuils convertis depuis les '
        + esc(e.unite_rubrique) + " de la rubrique — "
        + esc(e.conversion.formule)
        + (e.conversion.estimee ? ". Conversion ESTIMÉE : " : ". ")
        + esc(e.conversion.note) + "</span>";
    }
    return h;
  }

  /* LE CONTOUR. Rouge dès qu'un seuil est franchi — c'est ce qui a été
     demandé, et c'est le bon signal : le régime administratif entre alors au
     chemin critique du projet. Le régime atteint est écrit à côté, parce
     qu'un contour rouge sans nom laisse le lecteur deviner LEQUEL des trois
     régimes il vient de déclencher, et ils ne coûtent pas la même chose. */
  function icpeSeuilEtat(el) {
    var cid = el.getAttribute("data-icpe");
    var e = icpeBaremeChamp(cid);
    var box = $("#ig-icpe-" + cid + "-e");
    if (!e || !box) return;
    var v = icpeVariante(e);
    var brut = (el.value || "").trim().replace(",", ".");
    var n = brut === "" ? null : Number(brut);
    var franchi = null;
    if (v && n !== null && isFinite(n)) {
      (v.paliers || []).forEach(function (p) {
        if (n >= p.a_partir_de_champ) franchi = p;
      });
    }
    el.classList.toggle("ig-depasse", !!franchi);
    if (franchi) {
      el.setAttribute("aria-describedby", "ig-icpe-" + cid + "-e");
    } else {
      el.removeAttribute("aria-describedby");
    }
    var marque = box.querySelector(".ig-franchi");
    if (marque) marque.remove();
    if (franchi) {
      var sp = document.createElement("span");
      sp.className = "ig-franchi";
      /* PAS SEULEMENT UNE COULEUR. Un contour rouge seul est invisible pour
         qui ne distingue pas les rouges, et muet pour un lecteur d'écran :
         le régime atteint s'écrit. */
      sp.textContent = "Seuil franchi — " + franchi.regime_nom;
      box.insertBefore(sp, box.firstChild);
    }
  }

  function icpeLire() {
    var p = lireProfil();
    document.querySelectorAll("#ig-icpe-form [data-icpe]").forEach(function (el) {
      var v = (el.value || "").trim();
      if (v === "") return;
      p[el.getAttribute("data-icpe")] = (v === "oui") ? true
        : (v === "non") ? false : v;
    });
    return p;
  }

  function icpeCribler() {
    var msg = $("#ig-icpe-msg"), out = $("#ig-icpe-out");
    if (!out) return;
    msg.textContent = "Criblage…";
    demander("/api/datacenter/icpe", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(icpeLire()),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) {
          msg.textContent = (j && j.message) || "Criblage indisponible.";
          return;
        }
        ICPE = j;
        msg.textContent = j.lecture || "";
        icpeRendre(j);
      })
      .catch(function () { msg.textContent = "Criblage indisponible."; });
  }

  function icpeRendre(j) {
    var out = $("#ig-icpe-out"), c = j.criblage;
    var atteintes = j.rubriques.filter(function (r) { return r.etat === "declenchee"; });
    var manquent = j.rubriques.filter(function (r) { return r.etat === "a_verifier"; });
    var h = '<div class="ig-icpe-tete">'
      + '<span class="ig-icpe-reg"' + info("regime_icpe:" + c.regime_site) + ">"
      + esc(c.regime_site_detail.nom) + "</span>"
      + '<span class="ig-icpe-n">' + esc(c.regime_site_note) + "</span></div>";
    /* LE SÉLECTEUR. Une liste déroulante plutôt que cinq blocs dépliés : les
       rubriques se consultent une à une, et celle qui commande le planning est
       en tête. Le compte figure dans le libellé du bouton — « 5 rubriques,
       3 atteintes » se lit sans ouvrir. */
    h += '<div class="ig-sel"><button type="button" class="ig-sel-b" '
      + 'id="ig-icpe-sel" aria-expanded="false" aria-haspopup="listbox">'
      + '<span class="ig-sel-n">' + j.rubriques.length + " rubrique"
      + (j.rubriques.length > 1 ? "s" : "") + "</span> · "
      + atteintes.length + " atteinte" + (atteintes.length > 1 ? "s" : "")
      + (manquent.length ? " · " + manquent.length + " sans donnée" : "")
      + '<span class="ig-sel-c" aria-hidden="true">▾</span></button>'
      + '<div class="ig-sel-p" id="ig-icpe-liste" role="listbox" hidden>';
    j.rubriques.forEach(function (r) {
      h += '<button type="button" class="ig-sel-o ig-icpe-o" role="option" '
        + 'aria-selected="false" data-code="' + esc(r.code) + '">'
        + '<span class="ig-icpe-b ig-icpe-b-' + esc(r.etat) + '">'
        + esc(r.badge) + "</span>"
        + '<span class="ig-sel-l">' + esc(r.libelle)
        + '<span class="ig-sel-d">' + esc(r.resume) + "</span></span></button>";
    });
    h += "</div></div><div id=\"ig-icpe-fiche\"></div>";
    h += '<div class="ig-icpe-mis"><b>Ce que le régime ajoute à la mission</b><ul>';
    (j.mission.actions || []).forEach(function (a) {
      h += "<li>" + esc(a) + "</li>";
    });
    h += "</ul><p class=\"ig-icpe-res\">" + esc(j.mission.reserve) + "</p></div>";
    h += '<p class="ig-icpe-res">' + esc(c.reserve) + "</p>"
      + '<p class="ig-icpe-res">' + esc(c.connexes) + "</p>";
    out.innerHTML = h;
    var b = $("#ig-icpe-sel"), liste = $("#ig-icpe-liste");
    if (b) {
      b.addEventListener("click", function () {
        var ouvert = liste.hidden;
        liste.hidden = !ouvert;
        b.setAttribute("aria-expanded", ouvert ? "true" : "false");
      });
    }
    out.querySelectorAll(".ig-icpe-o").forEach(function (o) {
      o.addEventListener("click", function () {
        out.querySelectorAll(".ig-icpe-o").forEach(function (x) {
          x.setAttribute("aria-selected", "false");
          x.classList.remove("ig-sel-actif");
        });
        o.setAttribute("aria-selected", "true");
        o.classList.add("ig-sel-actif");
        liste.hidden = true;
        b.setAttribute("aria-expanded", "false");
        icpeFiche(o.getAttribute("data-code"));
      });
    });
    /* La première rubrique est ouverte d'emblée : c'est celle qui commande le
       planning, et un panneau vide sous un sélecteur n'invite personne. */
    var premier = out.querySelector(".ig-icpe-o");
    if (premier) premier.click();
  }

  function icpeFiche(code) {
    var z = $("#ig-icpe-fiche");
    var r = (ICPE.rubriques || []).filter(function (x) { return x.code === code; })[0];
    if (!z || !r) return;
    var l = r.ligne;
    var h = '<div class="ig-icpe-f"><h4' + info("rubrique_icpe:" + code) + ">"
      + esc(l.numero) + " — " + esc(l.intitule) + "</h4>"
      + '<p class="ig-icpe-s">' + esc(l.sous) + "</p>";
    if (r.etat === "declenchee") {
      h += '<p class="ig-icpe-v"><b>' + esc(l.regime_nom) + "</b> — "
        + esc(l.grandeur) + " : <b>" + esc(String(l.valeur).replace(".", ","))
        + " " + esc(l.unite) + "</b>"
        + (l.estimee ? " <i>(estimée — voir le détail)</i>" : "") + "</p>";
      if (l.detail && Object.keys(l.detail).length) {
        h += '<dl class="ig-icpe-d">';
        Object.keys(l.detail).forEach(function (k) {
          h += "<dt>" + esc(k) + "</dt><dd>"
            + esc(String(l.detail[k]).replace(".", ",")) + "</dd>";
        });
        h += "</dl>";
      }
      if (l.marge) {
        h += '<p class="ig-icpe-m">Seuil suivant à <b>'
          + esc(String(l.marge.prochain_seuil).replace(".", ",")) + " "
          + esc(l.unite) + "</b> — au-delà, régime "
          + esc(l.marge.regime_au_dela) + ". Vous en êtes à "
          + Math.round((l.marge.part_du_seuil || 0) * 100) + " %.</p>";
      }
      h += '<ul class="ig-icpe-se">';
      (l.seuils || []).forEach(function (s) {
        h += "<li>" + esc(String(s.a_partir_de).replace(".", ",")) + " "
          + esc(l.unite)
          + (s.jusqu_a !== null && s.jusqu_a !== undefined
              ? " à " + esc(String(s.jusqu_a).replace(".", ",")) + " " + esc(l.unite)
              : " et au-delà")
          + " → <b>" + esc(s.regime_nom) + "</b></li>";
      });
      h += "</ul>";
    } else if (r.etat === "a_verifier") {
      h += '<p class="ig-icpe-k">Il manque ' + esc(l.manque)
        + ". Une donnée absente n'est pas un seuil non atteint.</p>";
    } else {
      h += '<p class="ig-icpe-x">' + esc(l.pourquoi || "") + "</p>";
    }
    h += '<dl class="ig-icpe-q"><dt>Ce qui la déclenche</dt><dd>'
      + esc(l.declenche_par) + "</dd>"
      + "<dt>Ce qui surprend</dt><dd>" + esc(l.ce_qui_surprend) + "</dd>"
      + "<dt>En conception</dt><dd>" + esc(l.conception) + "</dd>"
      + "<dt>Pour la mission</dt><dd>" + esc(l.moe) + "</dd></dl>"
      + '<p class="ig-icpe-res">' + esc(l.texte) + "</p></div>";
    z.innerHTML = h;
  }


  /* ══════════════════════════════════════════════════════════════════════
     LA PHASE TRAVAUX
     ══════════════════════════════════════════════════════════════════════
     DEUX RÉGLAGES SEULEMENT, et ils changent le plan pour de bon : la nature
     des travaux — neuf, fit-out, rétrofit — et l'existence d'une mission de
     commissioning. Le reste est une structure, pas un planning : elle ne porte
     aucune durée, parce qu'une durée dépend du site. */
  function travauxFormulaire() {
    var z = $("#ig-tr-form");
    if (!z || !CADRE) return;
    var N = (CADRE.natures_travaux || {});
    var h = '<label class="dc-champ" for="ig-tr-nat"><span class="dc-lab">'
      + "Nature des travaux</span>"
      + '<select id="ig-tr-nat"><option value="">— non précisée —</option>';
    Object.keys(N).forEach(function (k) {
      h += '<option value="' + esc(k) + '">' + esc(N[k].nom) + "</option>";
    });
    h += "</select><span class=\"dc-aide\">Elle ne change ni le nom des phases "
      + "ni la liste des pièces, mais elle change ce qu'il faut y mettre et où "
      + "se trouve le risque.</span></label>"
      + '<label class="dc-champ" for="ig-tr-cx"><span class="dc-lab">'
      + "Mission de commissioning</span>"
      + '<select id="ig-tr-cx"><option value="oui">Commandée</option>'
      + '<option value="non">Non commandée</option></select>'
      + '<span class="dc-aide">Non commandée, les opérations d\'essais ne '
      + "disparaissent pas du plan : elles y restent avec la mention de qui "
      + "devra les assumer.</span></label>";
    z.innerHTML = h;
    z.addEventListener("change", travauxPlan);
    travauxPlan();
  }

  function travauxPlan() {
    var msg = $("#ig-tr-msg"), out = $("#ig-tr-out");
    if (!out) return;
    var nat = ($("#ig-tr-nat") || {}).value || "";
    var cx = (($("#ig-tr-cx") || {}).value || "oui") !== "non";
    msg.textContent = "";
    demander("/api/datacenter/travaux", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nature_travaux: nat, commissioning: cx }),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) {
          msg.textContent = (j && j.message) || "Plan indisponible.";
          return;
        }
        travauxRendre(j.plan, j.nature_detail);
        travauxBrancherMenu();
        travauxBrancherMenuSolutions();
      })
      .catch(function () { msg.textContent = "Plan indisponible."; });
  }

  /* ── LE MENU DES OPÉRATIONS — DOUZE CHANTIERS À LA SUITE NE SONT PAS DOUZE
     CHANTIERS PARALLÈLES. C'est exactement le défaut déjà nommé en tête de ce
     fichier pour les phases de maîtrise d'œuvre : affichées à plat, des
     étapes SÉQUENTIELLES se lisent comme des blocs indépendants. Chaque
     opération porte ici quatre à six lignes — objet, préalable, point d'arrêt
     éventuel, acteurs — et douze à la suite font un mur qu'on parcourt en
     diagonale plutôt qu'une séquence qu'on comprend.

     UNE SEULE EST OUVERTE AU CHARGEMENT — la première, « Période de
     préparation » — comme les phases de maîtrise d'œuvre plus haut dans ce
     fichier. Les opérations SE LISENT, elles ne SE COMPTENT PAS : c'est
     l'inverse du menu des pièces du dossier (`aoMenuDocs`), qui garde ses
     dix-neuf cartes visibles parce qu'on y vient vérifier ce qui existe, pas
     suivre un ordre.

     GROUPÉES PAR FAMILLE, en revanche, MÊME IDIOME que `aoMenuDocs` : suivi,
     contrôle, commissioning, réception sont quatre moments d'attention
     différents, pour des rôles différents — le CSPS suit le contrôle, l'agent
     de commissioning les essais, le client la réception. Le `<optgroup>` sert
     ici à SCANNER, pas à choisir un groupe entier : chaque option reste une
     opération unique. */
  var TR_TOUTES = "__toutes";
  var TR_OP = null;

  /* ── LE MENU DES SOLUTIONS — DIX LEVIERS NE SONT PAS DIX RECOMMANDATIONS
     Chaque solution porte quatre lignes : ce qu'elle obtient, ce qu'elle
     coûte, où et quand la poser. Dix à la suite font le même mur que les
     douze opérations juste au-dessus, et se parcourent de la même façon —
     en diagonale.

     LE GROUPEMENT N'EST PAS LA NATURE, C'EST CE QUE LE PROJET IMPOSE. La
     nature (« technique » / « managériale ») est une phrase entière dans le
     module — « Se pose dans les pièces techniques et se démontre par un
     document ou un essai. » — et ne fait pas un intitulé de groupe. Surtout,
     ce n'est pas la question qu'on se pose devant ce bloc : le phasage
     d'exploitation d'un rétrofit n'est pas une bonne pratique à arbitrer,
     c'est une condition de faisabilité. Le menu range donc par CE QUI SE
     DÉCIDE et CE QUI NE SE DÉCIDE PAS.

     ET CE QUE LE PROJET IMPOSE EST OUVERT AU CHARGEMENT, pas la première
     solution par ordre alphabétique. C'est la seule différence avec le menu
     des opérations, et elle est délibérée : ouvrir sur une solution
     arbitrable laisserait masquée celle qui n'est pas négociable. */
  var TR_IMPOSEES = "__imposees";
  var TR_SOL = null;

  /* LE CHOIX EST PASSÉ EN PARAMÈTRE, PAS LU DANS TR_OP — même discipline que
     `aoMenuDocs` : c'est ce qui permet d'exécuter cette fonction hors du
     navigateur pour l'éprouver, et ce qui empêche le rendu de dépendre d'un
     état qu'un appelant oublierait de poser. */
  function travauxMenu(p, choix) {
    var parFamille = {};
    p.operations.forEach(function (o) {
      (parFamille[o.famille] = parFamille[o.famille] || []).push(o);
    });
    var h = '<label class="ig-ao-menu"><span class="dc-lab">'
      + p.operations.length + " opérations, dans l'ordre du chantier — en "
      + "choisir une</span>"
      /* LA VALEUR « TOUTES » EST UN LITTÉRAL ICI, PAS `TR_TOUTES` : cette
         fonction ne doit dépendre d'AUCUN état ni constante du module — même
         discipline que `aoMenuDocs`, qui n'en lit aucun. `TR_TOUTES` reste
         le nom partagé entre le rendu et le filtre, mais seul le filtre,
         qui n'a pas besoin d'être pur, le lit. */
      + '<select id="ig-tr-op"><option value="__toutes">Les '
      + p.operations.length + " opérations, à la suite</option>";
    Object.keys(p.familles).forEach(function (f) {
      var liste = parFamille[f] || [];
      if (!liste.length) return;
      h += '<optgroup label="' + esc(p.familles[f].nom) + " (" + liste.length + ')">';
      liste.forEach(function (o) {
        h += '<option value="' + esc(o.cle) + '"' + (o.cle === choix ? " selected" : "")
          + ">" + esc(o.nom) + "</option>";
      });
      h += "</optgroup>";
    });
    h += "</select><span class=\"dc-aide\">La sortie d'une opération est "
      + "l'entrée de la suivante&nbsp;: l'ordre porte autant que le contenu."
      + "</span></label>";
    return h;
  }

  /* Le filtre MASQUE, il ne redessine pas — la règle tenue partout ailleurs
     dans ce fichier (`aoBrancherMenu`, les listes de la page de calcul) :
     redessiner perdrait tout ce que la saisie de la section a construit
     autour, et referait le menu au moment même où on vient de le poser. */
  function travauxBrancherMenu() {
    var sel = $("#ig-tr-op");
    if (!sel) return;
    sel.addEventListener("change", function () {
      TR_OP = sel.value;
      document.querySelectorAll("#ig-tr-out [data-op]").forEach(function (li) {
        li.hidden = TR_OP !== TR_TOUTES && li.dataset.op !== TR_OP;
      });
    });
  }

  /* LE CHOIX EST PASSÉ EN PARAMÈTRE, PAS LU DANS TR_SOL — même discipline
     que `travauxMenu` et `aoMenuDocs` : c'est ce qui permet d'exécuter cette
     fonction hors du navigateur pour l'éprouver. */
  function travauxMenuSolutions(p, choix) {
    var imposees = p.solutions.filter(function (s) { return s.impose; });
    var libres = p.solutions.filter(function (s) { return !s.impose; });
    var h = '<label class="ig-ao-menu"><span class="dc-lab">'
      + p.solutions.length + " solutions pour faire tenir les termes du "
      + "marché — en choisir une</span>"
      /* LES DEUX VALEURS SONT DES LITTÉRAUX ICI, PAS `TR_TOUTES` NI
         `TR_IMPOSEES` : cette fonction ne doit dépendre d'AUCUN état ni
         constante du module, même discipline que `travauxMenu`. */
      + '<select id="ig-tr-sol"><option value="__toutes">Les '
      + p.solutions.length + " solutions, à la suite</option>";
    if (imposees.length) {
      h += '<option value="__imposees"'
        + (choix === "__imposees" ? " selected" : "") + ">Les "
        + imposees.length + " que ce projet IMPOSE</option>";
    }
    [["Imposées par ce projet", imposees],
     ["À arbitrer", libres]].forEach(function (g) {
      if (!g[1].length) return;
      h += '<optgroup label="' + esc(g[0]) + " (" + g[1].length + ')">';
      g[1].forEach(function (x) {
        h += '<option value="' + esc(x.cle) + '"'
          + (x.cle === choix ? " selected" : "") + ">" + esc(x.nom)
          + "</option>";
      });
      h += "</optgroup>";
    });
    h += '</select><span class="dc-aide">Ce que le projet impose n\'est pas '
      + "négociable&nbsp;: c'est une condition de faisabilité, pas une bonne "
      + "pratique.</span></label>";
    return h;
  }

  /* UNE SEULE DÉFINITION DE « CETTE SOLUTION EST-ELLE VISIBLE ? », lue par le
     RENDU et par le FILTRE.

     POURQUOI PAS DEUX, COMME POUR LES OPÉRATIONS. Le menu des opérations
     porte la même règle écrite deux fois — dans le `hidden` de `<li>` et dans
     le gestionnaire —, et c'est précisément ce qui avait laissé passer un
     défaut mesuré en navigateur : le gestionnaire traitait « toutes », le
     rendu non, si bien qu'un changement de nature faisait disparaître les
     douze opérations. Deux copies d'une règle divergent ; celle-ci n'a qu'un
     exemplaire.

     LES DEUX VALEURS SONT DES LITTÉRAUX — même discipline que
     `travauxMenuSolutions` : la fonction reste exécutable hors du navigateur,
     donc éprouvable sur les quatre formes de projet. */
  function travauxSolVisible(choix, cle, impose) {
    return choix === "__toutes"
      || (choix === "__imposees" && !!impose)
      || cle === choix;
  }

  /* Le filtre MASQUE, il ne redessine pas — la règle tenue partout ailleurs
     dans ce fichier. */
  function travauxBrancherMenuSolutions() {
    var sel = $("#ig-tr-sol");
    if (!sel) return;
    sel.addEventListener("change", function () {
      TR_SOL = sel.value;
      document.querySelectorAll("#ig-tr-out [data-sol]").forEach(function (d) {
        d.hidden = !travauxSolVisible(TR_SOL, d.dataset.sol,
                                      d.dataset.impose === "1");
      });
    });
  }

  function travauxRendre(p, nature) {
    var out = $("#ig-tr-out");
    var h = "";
    if (nature) {
      h += '<div class="ig-encart"><b>' + esc(nature.nom) + "</b> — "
        + esc(nature.ce_que_c_est)
        + '<span class="ig-tr-r">Le risque propre — ' + esc(nature.risque)
        + "</span><span class=\"ig-tr-r\">La maîtrise d'œuvre — "
        + esc(nature.moe) + "</span></div>";
    }
    /* LES PRÉALABLES BLOQUANTS EN TÊTE, et signalés comme tels. Un rétrofit
       dont le phasage d'exploitation n'est pas étudié n'a pas de plan de
       travaux : il a une liste de vœux. */
    if (p.prealables && p.prealables.length) {
      h += '<div class="ig-tr-pre"><b>À faire avant tout le reste</b>';
      p.prealables.forEach(function (x) {
        h += '<div class="ig-tr-pre-l"><b>' + esc(x.nom) + "</b> — "
          + esc(x.pourquoi) + "</div>";
      });
      h += "</div>";
    }
    /* L'EFFECTIF DU CHOIX SE DÉCIDE ICI, UNE SEULE FOIS : s'il n'y en a pas
       encore, ou si le précédent ne désigne plus une opération du plan
       courant (un changement de nature pourrait en théorie faire varier la
       liste), on retombe sur la première. `TR_OP` est mis à jour ici, et nulle
       part ailleurs. */
    /* « TOUTES » EST TOUJOURS UN CHOIX VALIDE, même si aucune opération ne
       porte cette clé — sinon un plan redessiné (nature ou commissioning
       changés) le traiterait comme absent et retomberait sur la première
       opération, perdant la vue d'ensemble qu'on venait de choisir. */
    var choix = TR_OP === TR_TOUTES
      || (TR_OP && p.operations.some(function (o) { return o.cle === TR_OP; }))
      ? TR_OP : (p.operations[0] || {}).cle;
    TR_OP = choix;
    h += travauxMenu(p, choix);
    h += '<ol class="ig-tr-l">';
    p.operations.forEach(function (o) {
      h += '<li data-op="' + esc(o.cle) + '"'
        + (choix === TR_TOUTES || o.cle === choix ? "" : " hidden")
        + ' class="ig-tr-o' + (o.sans_titulaire ? " ig-tr-orph" : "") + '">'
        + '<div class="ig-tr-h"><span class="ig-tr-f">' + esc(o.famille_nom)
        + "</span>"
        + '<b' + info("operation:" + o.cle) + ">" + esc(o.nom) + "</b>"
        + '<span class="ig-tr-ph">' + esc(o.phase) + "</span></div>"
        + '<p class="ig-tr-ob">' + esc(o.objet) + "</p>"
        + '<p class="ig-tr-pa"><i>Ce qu\'il faut avant</i> — ' + esc(o.prealable)
        + "</p>";
      if (o.point_arret) {
        h += '<p class="ig-tr-ar"><b>Point d\'arrêt</b> — '
          + esc(o.point_arret) + "</p>";
      }
      if (o.sans_titulaire) {
        h += '<p class="ig-tr-so">' + esc(o.sans_titulaire) + "</p>";
      }
      h += '<p class="ig-tr-ac">';
      o.acteurs.forEach(function (a) {
        h += '<span class="ig-tr-a ig-tr-a-' + esc(a.lien) + '"'
          + info("intervenant:" + a.cle) + ">" + esc(a.nom) + "</span>";
      });
      h += "</p></li>";
    });
    h += "</ol>";
    /* LES SOLUTIONS. Celles que le projet IMPOSE sont en tête et le disent :
       le phasage d'exploitation d'un rétrofit n'est pas une bonne pratique,
       c'est une condition de faisabilité. */
    h += '<h3 class="ig-tr-st">Ce qui fait tenir les termes du marché</h3>';
    /* LE CHOIX EFFECTIF SE DÉCIDE ICI, UNE SEULE FOIS — même construction que
       pour les opérations. Trois cas de repli, et chacun a sa raison :

       · « toutes » reste valide quoi qu'il arrive — aucune solution ne porte
         cette clé, et la traiter comme une clé absente ferait disparaître les
         dix, défaut déjà mesuré sur le menu des opérations ;
       · « imposées » n'est valide QUE s'il en reste. Changer la nature des
         travaux ou retirer le commissioning peut vider ce groupe, et le
         garder choisi n'afficherait plus rien ;
       · sinon on ouvre sur les imposées quand il y en a — elles ne se
         négocient pas —, et à défaut sur la liste entière. */
    var impCount = p.solutions.filter(function (s) { return s.impose; }).length;
    var cs = TR_SOL === TR_TOUTES
      || (TR_SOL === TR_IMPOSEES && impCount)
      || (TR_SOL && p.solutions.some(function (s) { return s.cle === TR_SOL; }))
      ? TR_SOL : (impCount ? TR_IMPOSEES : TR_TOUTES);
    TR_SOL = cs;
    h += travauxMenuSolutions(p, cs) + '<div class="ig-tr-sol">';
    p.solutions.forEach(function (s) {
      h += '<div class="ig-tr-s' + (s.impose ? " ig-tr-simp" : "") + '"'
        + ' data-sol="' + esc(s.cle) + '" data-impose="' + (s.impose ? "1" : "0")
        + '"' + (travauxSolVisible(cs, s.cle, s.impose) ? "" : " hidden") + ">"
        + '<b' + info("solution:" + s.cle) + ">" + esc(s.nom) + "</b>"
        + (s.impose ? '<span class="ig-tr-sb">imposée par le projet</span>' : "")
        + '<span class="ig-tr-sn">' + esc(s.nature_nom) + "</span>"
        + "<p><i>Ce que ça obtient</i> — " + esc(s.obtient) + "</p>"
        + "<p><i>Ce que ça coûte</i> — " + esc(s.coute) + "</p>"
        + "<p><i>Où et quand la poser</i> — " + esc(s.quand_poser) + "</p></div>";
    });
    h += "</div>" + '<p class="ig-icpe-res">' + esc(p.note) + "</p>";
    out.innerHTML = h;
  }


  /* ══════════════════════════════════════════════════════════════════════
     L'APPEL D'OFFRES — lire le dossier, préparer la réponse
     ══════════════════════════════════════════════════════════════════════
     LES PIÈCES SE TRANSMETTENT SANS ÊTRE DÉPOSÉES, et c'est délibéré. On lit
     un dossier de consultation AVANT de décider s'il vaut la peine d'être
     conservé, et les pièces d'une consultation à laquelle on ne répondra pas
     n'ont rien à faire dans la base de connaissance. Celles qu'on veut garder
     passent par l'étape précédente, qui les indexe.

     TOUTES ENSEMBLE, PAS UNE PAR UNE. L'information la plus utile d'une
     analyse de dossier de consultation est CE QUI MANQUE — et cela ne se voit
     qu'en regardant le dossier entier. */
  var AO_ANALYSE = null;
  /* LA SÉLECTION, ET LES DEUX GESTES QUI LA CORRIGENT.
     Ils vivent ici et pas au serveur : l'opérateur connaît la consultation,
     le moteur ne fait que lire un texte. Ils repartent à chaque analyse pour
     que la sélection soit recalculée AVEC eux — la recalculer sans les
     emporter les effacerait au premier redépôt. */
  var AO_SELECTION = null;
  var AO_SEL_AJOUTS = {};
  var AO_SEL_ECARTEES = {};
  /* LE TEXTE DES PIÈCES LUES, GARDÉ POUR POUVOIR ÊTRE CONSERVÉ — et pour rien
     d'autre. Sans lui, rattacher un projet obligerait à re-choisir les
     fichiers : l'analyse ne garde que ce qu'elle a relevé, pas ce qu'elle a
     lu. Il reste dans cette page tant qu'aucun projet n'est choisi. */
  var AO_DOCS = null;
  /* ── LE TEXTE LU DE CHAQUE PIÈCE, POUR POUVOIR LE RELIRE ────────────────
     CE QUI MANQUAIT. La page montrait des citations de trois lignes et rien
     autour. Vérifier une valeur dans son contexte, ou comprendre pourquoi une
     pièce n'avait pas été reconnue, supposait d'aller rouvrir le fichier
     ailleurs — c'est-à-dire de sortir de l'outil au moment précis où il
     demande de vérifier.

     DEUX SOURCES, UNE SEULE TABLE. L'analyse d'une session rend le texte
     qu'elle vient de lire ; le dossier conservé rend le sien, déchiffré. Deux
     tables auraient divergé, et l'écran aurait montré l'une ou l'autre selon
     l'ordre d'arrivée des réponses.

     LA RÈGLE DE PRÉSÉANCE EST EXPLICITE, ET C'EST NÉCESSAIRE. Les deux
     réponses n'arrivent pas dans un ordre garanti : l'analyse d'abord, puis
     l'état du projet — sauf quand l'état arrive au chargement, avant toute
     analyse. Ce qui vient d'être lu l'emporte TOUJOURS (`ecraser`), le coffre
     ne fait que COMBLER. Sans cette règle, le texte du coffre écraserait
     parfois celui d'une pièce qu'on vient de redéposer. */
  var AO_TEXTES = {};
  var AO_TEXTE_OUVERT = null;

  /* Le texte lu d'une pièce entre dans la table. `ecraser` distingue les deux
     sources : vrai pour ce qui vient d'être lu, faux pour le coffre. */
  function aoTextesPoser(table, ecraser) {
    Object.keys(table || {}).forEach(function (nom) {
      var t = table[nom];
      if (typeof t !== "string" || !t) return;
      if (ecraser || !AO_TEXTES[nom]) AO_TEXTES[nom] = t;
    });
  }

  /* LES PASSAGES RELEVÉS DANS UNE PIÈCE, AVEC LEUR POSITION EXACTE.
     On les tire de l'analyse et non d'une recherche dans le texte : le
     releveur a déjà donné l'offset du passage qu'il a retenu, et rechercher
     la chaîne surlignerait aussi ses occurrences ailleurs — y compris celles
     que le relevé n'a PAS retenues. Ce qu'on montre doit être ce qui a servi,
     pas ce qui lui ressemble. */
  /* LA FIN RÉELLE D'UNE CITATION DANS LE TEXTE D'ORIGINE.
     CE QUI A ÉTÉ MESURÉ, ET QUI CONDAMNE LA MÉTHODE ÉVIDENTE. La citation
     rendue par le relevé est NORMALISÉE — le releveur fait l'équivalent de
     `" ".join(split())` — si bien que « Objet :\nconstruction… » y devient
     « Objet : construction… ». Sa longueur n'est donc PAS celle du passage
     d'origine dès qu'il contient un saut de ligne ou deux espaces. Prendre
     `position + citation.length` décalait la marque d'un caractère sur
     l'essai le plus simple — et d'autant plus que le texte vient d'un PDF,
     où les retours à la ligne sont partout. Un surlignage décalé de dix
     caractères désigne la phrase d'à côté, avec l'aplomb d'une preuve.

     ON REJOUE DONC LA NORMALISATION À L'ENVERS : on avance dans le texte
     d'origine en consommant la citation, une suite d'espaces valant un
     espace. ET ON REND -1 DÈS QUE ÇA DIVERGE — on ne surligne que ce qu'on
     peut prouver. Ne rien surligner se voit ; surligner à côté, non. */
  function aoTexteFin(texte, i, frag) {
    var k = i, f = 0;
    while (k < texte.length && /\s/.test(texte.charAt(k))) k++;   /* le motif
        peut commencer sur l'espace que la normalisation a ôté */
    while (f < frag.length) {
      if (frag.charAt(f) === " ") {
        if (k >= texte.length || !/\s/.test(texte.charAt(k))) return -1;
        while (k < texte.length && /\s/.test(texte.charAt(k))) k++;
        f++;
      } else {
        if (texte.charAt(k) !== frag.charAt(f)) return -1;
        k++; f++;
      }
    }
    return k;
  }

  function aoTexteMarques(nom, texte) {
    var a = AO_ANALYSE || {}, out = [];
    texte = texte || "";
    [].concat(a.pieces || [], a.inconnues || []).forEach(function (p) {
      if (p.fichier !== nom) return;
      (p.releves || []).forEach(function (r) {
        (r.citations || []).forEach(function (c) {
          var i = Number(c.position);
          if (!isFinite(i) || i < 0 || !c.texte) return;
          var deb = i;
          while (deb < texte.length && /\s/.test(texte.charAt(deb))) deb++;
          var j = aoTexteFin(texte, i, String(c.texte));
          if (j < 0 || j <= deb) return;        /* non réaligné : pas de marque */
          out.push({ i: deb, j: j, cle: r.cle, libelle: r.libelle });
        });
      });
    });
    /* Les relevés se recouvrent parfois — « Objet : ... » est cité par deux
       motifs. Deux balises imbriquées produiraient du HTML cassé ; on garde la
       première et on saute ce qui chevauche. */
    out.sort(function (x, y) { return x.i - y.i || y.j - x.j; });
    var gardes = [], fin = -1;
    out.forEach(function (m) {
      if (m.i < fin) return;
      gardes.push(m);
      fin = m.j;
    });
    return gardes;
  }

  /* Le texte d'une pièce en HTML, ses passages relevés surlignés.
     ÉCRIT À PART POUR ÊTRE MESURABLE : une règle peut l'exécuter sur un texte
     et des marques connus, au lieu de constater qu'un mot figure dans le
     fichier. */
  function aoTexteHtml(texte, marques) {
    var h = "", k = 0;
    (marques || []).forEach(function (m) {
      if (m.i < k || m.j > texte.length) return;
      h += esc(texte.slice(k, m.i))
        + '<mark class="ig-ao-mk" data-releve="' + esc(m.cle) + '" title="'
        + esc(m.libelle || m.cle) + '">' + esc(texte.slice(m.i, m.j))
        + "</mark>";
      k = m.j;
    });
    return h + esc(texte.slice(k));
  }
  /* LA FILE D'ATTENTE DES PIÈCES CHOISIES, avant analyse. Tenue à la main
     parce qu'un FileList natif n'est ni modifiable ni cumulable : on ne peut
     pas en ôter UN fichier, et re-choisir REMPLACE tout. Elle porte {nom,file},
     s'ajoute à chaque dépôt, et se défait pièce par pièce. Jamais relue d'un
     stockage local — une pièce d'une consultation ne doit pas reparaître sur
     la suivante, exactement comme AO_FOURNIES. */
  var AO_EN_ATTENTE = [];

  /* CE QUE LE SERVEUR ACCEPTE EN UNE REQUÊTE, moins l'inflation du base64 —
     un fichier binaire pèse un tiers de plus une fois encodé. La valeur suit
     `RAG_UPLOAD_MAX` côté serveur ; l'annoncer permet de choisir ses fichiers
     avant de les envoyer plutôt que d'apprendre le plafond en le heurtant. */
  var AO_TRANSPORT_MAX = 32 * 1024 * 1024 * 3 / 4;

  /* ── QUI A DROIT AU §14, DEMANDÉ AVANT LE PREMIER CLIC ───────────────
     Les douze interfaces de la réponse à consultation sont réservées à
     l'administration — la décision est écrite dans `acces.API_ADMIN` côté
     serveur, avec son motif, et le service refuse de démarrer si l'une
     d'elles s'ouvrait. Ici on ne DÉCIDE rien : on demande au serveur qui
     regarde, et on règle la section dessus.

     LE VERROU RESTE CELUI DU SERVEUR. Masquer un bouton n'a jamais protégé
     une route ; ce qui change ici est seulement qu'on cesse de faire
     travailler quelqu'un pour rien — choisir ses fichiers, attendre le
     téléversement, et lire un refus. */
  var AO_INTERNE_OUVERT = null;   /* null = pas encore su */

  function aoInterne() {
    return demander("/api/auth/me", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) { AO_INTERNE_OUVERT = !!j && j.role === "admin"; })
      .catch(function () { AO_INTERNE_OUVERT = false; })
      .then(function () {
        var b = $("#ig-ao-interne");
        if (b) b.classList.toggle("on", !AO_INTERNE_OUVERT);
        /* LES COMMANDES PARTENT, L'EXPLICATION RESTE. Laisser un champ de
           fichier inerte ferait croire à une panne ; le retirer sous un
           bandeau qui dit pourquoi se comprend.

           UNE CLASSE SUR LA SECTION, PAS UNE LISTE D'IDENTIFIANTS. La liste
           avait laissé DEUX BOUTONS VIDES à l'écran — mesuré en navigateur :
           `el.hidden` ne pèse rien face au `display:inline-block` de `.btn`,
           et « Mesurer les sept étapes » restait cliquable vers une route qui
           refuse. Ce qui s'adresse à celui qui opère porte `ig-ao-op` ; une
           seule règle de feuille les ferme tous, et un bloc ajouté demain la
           reçoit sans qu'on ait à se souvenir de cette fonction. */
        var sec = $("#ig-ao");
        if (sec) sec.classList.toggle("ig-ao-ferme", !AO_INTERNE_OUVERT);
        return AO_INTERNE_OUVERT;
      });
  }

  function aoDocuments() {
    var z = $("#ig-ao-depot");
    if (!z) return;
    z.innerHTML =
      '<label class="dc-champ" for="ig-ao-f"><span class="dc-lab">Pièces de '
      + "la consultation</span>"
      + '<input id="ig-ao-f" type="file" multiple accept="' + accepteDepot() + '">'
      + '<span class="dc-aide">Plusieurs fichiers à la fois, ou un par un — '
      + "chaque dépôt s'ajoute au précédent. Ils sont analysés puis lus, et ne "
      + "sont PAS enregistrés dans la base de connaissance : pour cela, passez "
      + "par l'étape précédente. "
      /* LA LIMITE EST DITE, PARCE QU'ELLE EXISTE. Elle valait 380 Ko pour
         l'ensemble des fichiers, sans que rien ne l'annonce : on choisissait
         son dossier de consultation, on cliquait, et on lisait « Contenu trop
         volumineux » sans savoir quel chiffre on avait dépassé. */
      + "Taille : jusqu'à " + aoOctets(AO_TRANSPORT_MAX) + " pour l'ensemble "
      + "des fichiers d'un même envoi.</span></label>"
      + '<div id="ig-ao-liste" class="ig-ao-docs"></div>';
    var f = $("#ig-ao-f");
    if (f) {
      /* CHAQUE DÉPÔT S'AJOUTE — ET DEVIENT RETIRABLE. On ne se contente plus du
         FileList natif : chaque sélection AJOUTE à `AO_EN_ATTENTE` (un même nom
         remplace le sien, comme le dossier conservé), et une liste déroulante
         la donne à voir et à défaire pièce par pièce. L'input est vidé après
         coup, sinon « Aucun fichier choisi » contredirait la liste, et
         re-choisir le même fichier ne rejouerait pas `change`. */
      f.addEventListener("change", function () {
        for (var i = 0; i < f.files.length; i++) {
          var fic = f.files[i], j = aoEnAttenteIndex(fic.name);
          if (j >= 0) AO_EN_ATTENTE[j] = { nom: fic.name, file: fic };
          else AO_EN_ATTENTE.push({ nom: fic.name, file: fic });
        }
        f.value = "";
        aoEnAttenteRendre();
      });
    }
    aoEnAttenteRendre();
  }

  /* L'INDEX D'UN NOM DANS LA FILE, ou -1. Le nom fait l'identité, comme au
     dossier conservé : re-déposer « CCTP.pdf » corrigé remplace le premier au
     lieu d'en garder deux. */
  function aoEnAttenteIndex(nom) {
    for (var i = 0; i < AO_EN_ATTENTE.length; i++) {
      if (AO_EN_ATTENTE[i].nom === nom) return i;
    }
    return -1;
  }

  /* LA LISTE DÉROULANTE DES PIÈCES CHOISIES, avec le retrait pièce par pièce.
     Elle rend ce que `aoAnalyser` va RÉELLEMENT lire : la même file. Ôter une
     pièce ici l'ôte donc de l'analyse — pas seulement de l'écran. */
  function aoEnAttenteRendre() {
    var l = $("#ig-ao-liste");
    if (!l) return;
    if (!AO_EN_ATTENTE.length) { l.innerHTML = ""; return; }
    var octets = AO_EN_ATTENTE.reduce(function (n, d) {
      return n + ((d.file && d.file.size) || 0); }, 0);
    var h = '<label class="dc-lab" for="ig-ao-sel">Pièces choisies ('
      + AO_EN_ATTENTE.length + " · " + esc(aoOctets(octets)) + ")</label>"
      + '<div class="ig-ao-choisis"><select id="ig-ao-sel" '
      + 'aria-label="Pièces de la consultation choisies">';
    AO_EN_ATTENTE.forEach(function (d, i) {
      h += '<option value="' + i + '">' + esc(d.nom) + " · "
        + esc(aoOctets((d.file && d.file.size) || 0)) + "</option>";
    });
    h += "</select>"
      + '<button type="button" class="btn btn-s" id="ig-ao-ret">'
      + "Retirer le fichier sélectionné</button></div>";
    l.innerHTML = h;
    var ret = $("#ig-ao-ret");
    if (ret) ret.addEventListener("click", function () {
      var sel = $("#ig-ao-sel");
      var i = sel ? parseInt(sel.value, 10) : -1;
      if (i >= 0 && i < AO_EN_ATTENTE.length) {
        AO_EN_ATTENTE.splice(i, 1);
        aoEnAttenteRendre();
      }
    });
  }

  /* Un fichier lu en base64, rendu comme une promesse. Le lecteur du
     navigateur est événementiel ; l'envelopper ici évite d'imbriquer autant de
     rappels que de fichiers, et surtout de perdre l'ordre. */
  /* CE QUI A ÉCHOUÉ, DIT EN TOUTES LETTRES. « Analyse indisponible. »
     couvrait indifféremment le délai dépassé, la coupure réseau et le refus du
     serveur : trois pannes, trois gestes différents, un seul message. Le
     lecteur qui charge un dossier de consultation de plusieurs mégaoctets a
     besoin de savoir s'il doit attendre, se reconnecter, ou alléger. */
  function aoPanne(e, octets) {
    if (e && e.name === "DelaiDepasse") {
      return "Le serveur n'a pas répondu en "
        + Math.round((e.delai || DELAI_LONG) / 1000) + " s pour "
        + aoOctets(octets) + ". Réessayez, ou chargez les pièces "
        + "en plusieurs fois : chaque dépôt s'ajoute au précédent.";
    }
    if (e && e.name === "SessionEteinte") {
      return "Votre session a expiré. Reconnectez-vous, puis relancez "
        + "l'analyse : rien n'est perdu.";
    }
    return "L'analyse n'a pas abouti (" + ((e && e.message) || "erreur réseau")
      + "). Le transfert de " + aoOctets(octets) + " n'est pas allé au bout.";
  }

  function aoLire(fichier) {
    return new Promise(function (ok) {
      var l = new FileReader();
      l.onerror = function () {
        ok({ nom: fichier.name, erreur: "Le fichier n'a pas pu être lu." });
      };
      l.onload = function () {
        ok({ nom: fichier.name,
             contenu: String(l.result).split(",")[1] || "" });
      };
      l.readAsDataURL(fichier);
    });
  }

  function aoAnalyser() {
    var msg = $("#ig-ao-msg");
    /* L'ANALYSE LIT LA FILE D'ATTENTE, PAS LE FILELIST BRUT. C'est ce qui rend
       le retrait réel : ôter une pièce de la liste déroulante l'ôte de ce qui
       part à l'analyse, puisque c'est cette même file qu'on lit ici. */
    if (!AO_EN_ATTENTE.length) {
      msg.textContent = "Choisissez les pièces de la consultation.";
      return;
    }
    var n = AO_EN_ATTENTE.length;
    msg.textContent = "Lecture de " + n + " pièce" + (n > 1 ? "s" : "") + "…";
    var lectures = [], docs_octets = 0;
    for (var i = 0; i < n; i++) lectures.push(aoLire(AO_EN_ATTENTE[i].file));
    Promise.all(lectures).then(function (lus) {
      var docs = lus.filter(function (x) { return !x.erreur; });
      if (!docs.length) {
        msg.textContent = "Aucun fichier n'a pu être lu.";
        return;
      }
      docs_octets = docs.reduce(function (n, d) {
        return n + (d.contenu || "").length * 3 / 4;
      }, 0);
      msg.textContent = "Analyse de " + docs.length + " pièce"
        + (docs.length > 1 ? "s" : "") + " · " + aoOctets(docs_octets) + "…";
      /* LE DÉLAI LONG, PARCE QUE LE TRAVAIL EST LONG. Le délai par défaut est
         de douze secondes — un budget d'aperçu. Ici on téléverse plusieurs
         mégaoctets, on les passe à l'antivirus, puis on en extrait le texte
         PDF par PDF. Douze secondes coupaient la requête en plein transfert,
         et l'abandon ressortait comme « Analyse indisponible. » : le lecteur
         apprenait qu'il avait échoué, jamais pourquoi. */
      return demander("/api/datacenter/marche/analyser", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        /* LES DEUX GESTES PARTENT AVEC LES DOCUMENTS. Les garder au
           navigateur et recalculer la sélection sans eux les effacerait au
           premier redépôt — et l'opérateur verrait revenir une pièce qu'il
           venait d'écarter, sans savoir pourquoi. */
        body: JSON.stringify({ documents: docs,
                               ajouts: Object.keys(AO_SEL_AJOUTS),
                               ecartees: Object.keys(AO_SEL_ECARTEES) }),
      }, DELAI_LONG)
        .then(function (x) { return x.json().then(function (j) { return [x.status, j]; }); })
        .then(function (xj) {
          var st = xj[0], j = xj[1];
          if (st === 401 || st === 403) {
            msg.textContent = "L'analyse d'un dossier de consultation est "
              + "réservée aux comptes d'administration : elle rend le contenu "
              + "des pièces du client.";
            return;
          }
          if (!j || !j.ok) {
            msg.textContent = (j && j.message) || "Analyse indisponible.";
            if (j && j.ignores) aoIgnores(j.ignores);
            return;
          }
          AO_ANALYSE = j.analyse;
          AO_DOCS = docs;
          /* CE QUI VIENT D'ÊTRE LU L'EMPORTE. Une pièce redéposée sous le
             même nom remplace la sienne au dossier ; son texte doit suivre,
             sinon le lecteur montrerait l'ancienne version sous le relevé de
             la nouvelle. */
          aoTextesPoser(j.textes, true);
          msg.textContent = "";
          /* LE PARCOURS SE REMESURE ICI, ET NULLE PART AILLEURS EN AUTOMATIQUE.
             C'est le seul instant où l'état change assez pour que le compte
             bouge d'un coup ; le remesurer à chaque frappe dans la fiche
             enverrait une requête par caractère pour un nombre qui bouge de
             un. Le bouton reste là pour le reste du temps. */
          aoParcours(null);
          /* LE BLOC PROJET SUIT L'ANALYSE : il n'a rien à proposer avant
             qu'il y ait des pièces à conserver. */
          aoProjetsCharger().then(aoProjetEtat);
          aoRendre(j.analyse);
          /* LA SÉLECTION VIENT DU MÊME APPEL QUE L'ANALYSE, et c'est voulu :
             deux requêtes auraient permis d'afficher une sélection calculée
             sur une analyse à côté d'un relevé issu d'une autre. */
          aoSelectionRendre(j.selection);
          /* LE TEMPS RÉEL COMMENCE ICI. Les rubriques qui viennent des pièces
             de l'acheteur — l'acheteur, l'objet, la référence, les lots — se
             remplissent au moment où l'analyse arrive, sans qu'on ait à
             redemander quoi que ce soit. */
          aoRemplir(true);
        });
    }).catch(function (e) { msg.textContent = aoPanne(e, docs_octets); });
  }

  /* CE QUI N'A PAS PU ÊTRE LU EST DIT, avec son motif. Un fichier écarté en
     silence se lit comme un fichier analysé — et le lecteur croirait son
     dossier complet. */
  function aoIgnores(ignores) {
    var out = $("#ig-ao-out");
    if (!out || !ignores || !ignores.length) return;
    var h = '<div class="ig-ao-mq"><b>Écarté de l\'analyse</b><ul>';
    ignores.forEach(function (x) {
      h += "<li><b>" + esc(x.fichier) + "</b> — " + esc(x.pourquoi) + "</li>";
    });
    out.innerHTML = h + "</ul></div>" + out.innerHTML;
  }

  /* ── LE LECTEUR D'UNE PIÈCE ──────────────────────────────────────────────
     CE QU'IL MONTRE, ET CE QU'IL NE MONTRE PAS. Il montre LE TEXTE EXTRAIT —
     exactement ce sur quoi les relevés ont tourné. Il ne montre pas le fichier
     d'origine : le PDF n'est pas conservé, il est passé à l'antivirus, ouvert
     par l'extracteur, puis abandonné. Laisser croire le contraire ferait
     chercher une mise en page qui n'existe plus ici, et surtout ferait
     prendre une extraction incomplète pour le document lui-même. L'écran le
     dit en toutes lettres, et une règle l'exige.

     POURQUOI LE TEXTE EXTRAIT EST LA BONNE CHOSE À MONTRER. Quand l'outil
     annonce « non trouvé dans cette pièce », la question suivante est
     toujours la même : le document ne le porte pas, ou l'extraction l'a
     perdu ? Un PDF scanné rend trois lignes de bruit ; un tableau à deux
     colonnes ressort entrelacé. Aucune citation ne le dit. Le texte lu, si. */
  function aoTexteFermer() {
    AO_TEXTE_OUVERT = null;
    var z = $("#ig-ao-lect");
    if (z) z.innerHTML = "";
  }

  function aoTexteOuvrir(nom) {
    var z = $("#ig-ao-lect");
    if (!z) return;
    if (AO_TEXTE_OUVERT === nom) { aoTexteFermer(); return; }
    AO_TEXTE_OUVERT = nom;
    var t = AO_TEXTES[nom];
    var h = '<div class="ig-ao-lec"><div class="ig-ao-lech">'
      + "<b>" + esc(nom) + "</b>"
      + '<button type="button" class="btn btn-s" id="ig-ao-lecx">Fermer'
      + "</button></div>";
    if (typeof t !== "string" || !t) {
      /* PAS DE TEXTE N'EST PAS UNE PANNE, ET LE DIRE ÉVITE DE LA CHERCHER.
         Un DWG, un ZIP, un PDF scanné franchissent l'analyse sans rendre une
         ligne. Un lecteur vide et muet se lirait comme un bogue. */
      h += '<p class="ig-ao-k">Aucun texte n\'a pu être extrait de cette '
        + "pièce. C'est le cas d'un fichier de dessin, d'une archive, ou d'un "
        + "PDF scanné sans couche texte. Les relevés n'ont donc rien pu y "
        + "chercher&nbsp;: ce qu'elle porte est à lire dans le fichier "
        + "d'origine, hors de cet outil.</p></div>";
      z.innerHTML = h;
      aoTexteBrancher(z);
      return;
    }
    var marques = aoTexteMarques(nom, t);
    h += '<p class="ig-ao-lecn"><b>Ceci est le texte extrait, pas le fichier '
      + "d'origine.</b> Le site ne conserve pas le PDF&nbsp;: il est analysé, "
      + "lu, puis abandonné. Ce que vous voyez ici est exactement ce sur quoi "
      + "les relevés ont tourné — c'est donc ici, et nulle part ailleurs, "
      + "qu'on voit si un « non trouvé » vient du document ou de "
      + "l'extraction.</p>"
      + '<p class="ig-ao-lecc">' + fr(t.length) + " caractères lus · "
      + marques.length + " passage(s) relevé(s), surlignés.</p>"
      + '<pre class="ig-ao-lect-t">' + aoTexteHtml(t, marques) + "</pre></div>";
    z.innerHTML = h;
    aoTexteBrancher(z);
    if (z.scrollIntoView) z.scrollIntoView({ block: "nearest" });
  }

  function aoTexteBrancher(z) {
    var x = $("#ig-ao-lecx", z);
    if (x) x.addEventListener("click", aoTexteFermer);
  }

  /* Le bouton, écrit UNE FOIS : il apparaît sur les pièces identifiées, sur
     les fichiers non reconnus et sur les pièces du dossier conservé. Trois
     copies auraient divergé le jour où l'une des trois change. */
  function aoTexteBouton(nom) {
    return '<button type="button" class="ig-ao-lb" data-lire="' + esc(nom)
      + '" title="Lire le texte extrait de cette pièce" '
      + 'aria-label="Lire le texte extrait de ' + esc(nom) + '">Lire</button>';
  }

  function aoTexteBrancherListe(z) {
    z.querySelectorAll("[data-lire]").forEach(function (b) {
      b.addEventListener("click", function () { aoTexteOuvrir(b.dataset.lire); });
    });
  }

  function aoRendre(a) {
    var out = $("#ig-ao-out");
    var h = "";
    /* LES ALERTES EN TÊTE, dans l'ordre du risque. Ce qui rend l'offre
       irrecevable d'abord — une pièce essentielle absente ou une date de
       remise non trouvée se traite avant de lire un CCTP. */
    if (a.alertes && a.alertes.length) {
      h += '<div class="ig-ao-al">';
      a.alertes.forEach(function (x) {
        h += '<p class="ig-ao-a ig-ao-a-' + esc(x.niveau) + '">'
          + esc(x.texte) + "</p>";
      });
      h += "</div>";
    }
    if (a.manquantes && a.manquantes.length) {
      h += '<div class="ig-ao-mq"><b>Absent du dossier déposé</b><ul>';
      a.manquantes.forEach(function (m) {
        h += "<li><b" + info("piece_marche:" + m.code) + ">" + esc(m.sigle)
          + "</b> — " + esc(m.ce_que_c_est)
          + (m.gravite === "bloquante"
              ? ' <span class="ig-ao-bl">essentielle</span>' : "")
          + "</li>";
      });
      h += "</ul></div>";
    }
    a.pieces.forEach(function (p) {
      h += '<div class="ig-ao-p"><div class="ig-ao-ph">'
        + '<b' + info("piece_marche:" + p.code) + ">" + esc(p.sigle) + "</b>"
        + '<span class="ig-ao-fn">' + esc(p.fichier) + "</span>"
        + '<span class="ig-ao-cf ig-ao-cf-' + esc(p.identification.confiance)
        + '">identifié · confiance ' + esc(p.identification.confiance)
        + "</span>" + aoTexteBouton(p.fichier) + "</div>"
        + '<p class="ig-ao-en"><i>Ce qu\'elle engage</i> — ' + esc(p.engage)
        + "</p>"
        + '<p class="ig-ao-pg"><i>Le piège</i> — ' + esc(p.piege) + "</p>";
      if (p.sans_texte) h += '<p class="ig-ao-k">' + esc(p.sans_texte) + "</p>";
      (p.releves || []).forEach(function (r) {
        h += '<div class="ig-ao-r' + (r.trouve ? "" : " ig-ao-rk") + '">'
          + "<b>" + esc(r.libelle) + "</b>";
        if (r.trouve) {
          r.citations.forEach(function (c) {
            h += '<blockquote class="ig-ao-c">' + esc(c.texte)
              + '<cite>à ' + c.part + " % du document</cite></blockquote>";
          });
        } else {
          h += '<p class="ig-ao-n">' + esc(r.note) + "</p>";
        }
        h += '<p class="ig-ao-w">' + esc(r.piege) + "</p></div>";
      });
      h += "</div>";
    });
    /* UN FICHIER NON RECONNU N'EST PAS UN FICHIER PERDU. L'écran ne disait
       que « non reconnu, voici pourquoi » — et l'utilisateur en concluait,
       à raison jusqu'ici, que son dépôt n'avait servi à rien. Le module
       relève désormais ce que le fichier porte ; encore faut-il le MONTRER,
       sinon le gain reste invisible et personne ne saura qu'il existe. */
    (a.inconnues || []).forEach(function (p) {
      /* LE BOUTON COMPTE DOUBLE ICI. « Non reconnu » laisse une question
         sans réponse : le fichier ne portait rien, ou l'identification n'a
         pas su le nommer ? Les deux se distinguent en lisant le texte, et
         d'aucune autre manière. */
      h += '<div class="ig-ao-p ig-ao-inc"><div class="ig-ao-ph"><b>'
        + esc(p.fichier) + "</b>" + aoTexteBouton(p.fichier) + "</div>"
        + "<p>" + esc(p.pourquoi) + "</p>";
      if ((p.releves || []).length) {
        h += '<p class="ig-ao-k">Le fichier n\'a pas été identifié, mais son '
          + "texte a été lu : ce qu'il porte est repris ci-dessous et versé "
          + "au remplissage EN DERNIER — une pièce identifiée l'emporte "
          + "toujours. Ouvrez-le avant de reporter ces valeurs.</p>";
        p.releves.forEach(function (r) {
          h += '<div class="ig-ao-r"><b>' + esc(r.libelle) + "</b>";
          (r.citations || []).forEach(function (c) {
            h += '<blockquote class="ig-ao-c">' + esc(c.texte)
              + '<cite>à ' + c.part + " % du document</cite></blockquote>";
          });
          h += '<p class="ig-ao-w">' + esc(r.piege) + "</p></div>";
        });
      }
      h += "</div>";
    });
    /* LES PIÈCES QUI SONT LES NÔTRES, DÉPOSÉES ICI PAR MÉGARDE. Elles ne se
       rangent pas avec les fichiers non reconnus : on sait exactement ce
       qu'elles sont. « RC » est le sigle du règlement de consultation, mais
       aussi celui de la responsabilité civile — et « RCS » celui du registre
       du commerce. Les confondre faisait déclarer PRÉSENT un règlement de
       consultation absent, sur la foi d'une attestation d'assurance. */
    if ((a.pieces_candidat || []).length) {
      h += '<div class="ig-ao-p ig-ao-nous"><b>Des pièces de VOTRE dossier '
        + "ont été déposées ici</b>"
        + "<p>Elles ne sont pas analysées avec le dossier de consultation — "
        + "elles n'en font pas partie. Leur place est au dossier "
        + "d'entreprise.</p>";
      a.pieces_candidat.forEach(function (p) {
        h += '<div class="ig-ao-r"><b>' + esc(p.fichier) + "</b>"
          + "<p>" + esc(p.nom) + "</p>"
          + '<p class="ig-ao-w">' + esc(p.ou) + "</p></div>";
      });
      h += "</div>";
    }
    h += '<p class="ig-icpe-res">' + esc(a.reserve) + "</p>";
    out.innerHTML = h;
    aoTexteBrancherListe(out);
    /* LE LECTEUR SE FERME QUAND LE RELEVÉ EST REFAIT. Il montrerait sinon le
       texte d'une pièce qu'on vient de retirer du dossier, sous un relevé qui
       ne la mentionne plus. */
    aoTexteFermer();
    /* Posé APRÈS le rendu, qui écrase le contenu du bloc : appelé avant, le
       relevé des fichiers écartés disparaîtrait sans laisser de trace. */
    aoIgnores(a.ignores);
  }

  function aoCandidature() {
    var msg = $("#ig-ao-msg"), out = $("#ig-ao-cand-out");
    msg.textContent = "";
    demander("/api/datacenter/marche/candidature", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analyse: AO_ANALYSE, groupement: true }),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) {
          msg.textContent = (j && j.message) || "Plan indisponible.";
          return;
        }
        aoCandRendre(j.plan);
        offreRendre(j.dossier_offre);
      })
      .catch(function () { msg.textContent = "Plan indisponible."; });
  }

  /* LA PASTILLE « REPÉRÉE DANS LE DOSSIER » — détection, jamais décision.
     Partagée par les cartes de candidature et d'offre. Elle ne s'affiche que
     lorsqu'un dossier a été analysé (`actives`) : hors dossier, on ne peut
     rien dire de ce que le RC exige. « Repérée » porte la citation en
     infobulle — le passage qui l'a déclenchée, pour aller vérifier. « Non
     repérée » n'affirme rien : le règlement de la consultation fait foi. */
  function aoExigence(actives, piece) {
    if (!actives) return "";
    if (piece.repere) {
      var c = piece.citation_exigence || {};
      return '<span class="ig-ao-ex ig-ao-ex-oui"'
        + (c.texte ? ' title="' + esc((c.sigle ? c.sigle + " · " : "")
                                       + c.texte) + '"' : "")
        + ">repérée dans le dossier</span>";
    }
    return '<span class="ig-ao-ex ig-ao-ex-non" title="Le repérage '
      + 'automatique ne l\'a pas vue : le règlement de votre consultation '
      + 'fait foi.">non repérée ici</span>';
  }

  /* ══ LA COLONNE DROITE : CE QUE CE DOSSIER-LÀ DEMANDE ═══════════════════

     ELLE REND UNE DÉCISION, PAS UN CATALOGUE. Avant ce tour, l'écran montrait
     les vingt-trois pièces quoi qu'il arrive : le nombre affiché était une
     propriété du catalogue, jamais du dossier de l'acheteur, et
     « 23 documents à remplir » se lisait comme une exigence de la
     consultation.

     TROIS GROUPES, ET LE TROISIÈME EST LE PLUS UTILE. Candidature et offre
     parce que ce sont deux dossiers distincts — l'un établit qui vous êtes,
     l'autre ce que vous proposez. Puis « non repérées », qui reste OUVERT :
     masquer ce que le moteur n'a pas trouvé ferait passer un défaut de
     reconnaissance pour une absence d'exigence, et c'est là qu'un opérateur
     qui connaît la consultation rattrape la lecture.

     CE QUI SE REMPLIT VRAIMENT EST DIT À PART. Quatre modèles de l'État se
     remplissent ; les autres pièces se rédigent ou s'obtiennent d'un tiers.
     Annoncer « sept documents remplis automatiquement » quand trois le sont
     est la promesse la plus facile à démentir de tout ce module. */
  function aoSelectionRendre(sel) {
    var z = $("#ig-ao-retenus");
    if (!z) return;
    AO_SELECTION = sel || null;
    if (!sel) {
      z.innerHTML = '<p class="note">La sélection n\'a pas pu être établie. '
        + "Le relevé ci-dessous reste valable ; les pièces se choisissent à "
        + "la main.</p>";
      return;
    }
    var groupes = [
      ["candidature", "Dossier de candidature", true],
      ["offre", "Dossier d'offre", true],
      ["__non", "Non repérées dans le dossier", false],
    ];
    var h = '<p class="note ig-ao-colp"><b>' + sel.retenues + " document(s)</b> "
      + "retenus sur " + sel.catalogue + " au catalogue — dont <b>"
      + sel.remplissables.length + "</b> que ce module remplit, et "
      + sel.a_produire.length + " à rédiger ou à obtenir d'un tiers.</p>";
    groupes.forEach(function (g) {
      var lignes = sel.lignes.filter(function (x) {
        return g[2] ? (x.retenue && x.dossier === g[0]) : !x.retenue;
      });
      h += '<div class="ig-ao-sg"><h4>' + esc(g[1]) + "</h4>"
        + '<span class="ig-ao-sn">' + lignes.length + " pièce(s)</span>";
      if (!lignes.length) {
        h += '<p class="note" style="margin:7px 0 0">'
          + (g[2] ? "Aucune pièce de ce dossier n'est demandée par la "
                  + "consultation analysée."
                  : "Toutes les pièces du catalogue sont retenues.")
          + "</p></div>";
        return;
      }
      /* LA LISTE DÉROULANTE ET LA LISTE DÉTAILLÉE DISENT LA MÊME CHOSE. La
         déroulante sert à parcourir vite quand il y en a quinze ; le détail
         sert à lire le motif et à défaire. Les tenir séparément aurait
         garanti qu'elles divergent. */
      h += '<select id="ig-ao-grp-' + g[0] + '" aria-label="' + esc(g[1]) + '">'
        + '<option value="">' + lignes.length + " pièce(s) — parcourir…</option>";
      lignes.forEach(function (x) {
        h += '<option value="' + esc(x.cle) + '">' + esc(x.nom) + "</option>";
      });
      h += "</select>" + '<ul class="ig-ao-sl">';
      lignes.forEach(function (x) {
        var cls = x.pourquoi === "citee" ? " p-citee"
                : x.pourquoi === "socle" ? " p-socle" : "";
        h += '<li><span class="n">' + esc(x.nom)
          + (x.remplissable ? "" : ' <span class="ig-ao-sn">à produire</span>')
          + "</span>"
          + '<span class="p' + cls + '">' + esc(x.pourquoi.replace("_", " "))
          + "</span>"
          + '<button type="button" data-sel-' + (x.retenue ? "off" : "on")
          + '="' + esc(x.cle) + '">' + (x.retenue ? "retirer" : "ajouter")
          + "</button></li>";
        /* LA CITATION QUI DÉCLENCHE LA PIÈCE, AVEC SA POSITION. Sans elle,
           « citée » est une affirmation — et c'est la doctrine du module
           depuis le début : chaque point relevé se vérifie. */
        if (x.citation && x.citation.texte) {
          h += '<li class="ig-ao-sc">« ' + esc(x.citation.texte) + " » — "
            + esc(x.citation.fichier || "")
            + (x.citation.part != null
               ? ", à " + Math.round(x.citation.part * 100) + " % du document"
               : "") + "</li>";
        } else if (!x.retenue || x.pourquoi !== "citee") {
          h += '<li class="ig-ao-sc">' + esc(x.motif || "") + "</li>";
        }
      });
      h += "</ul></div>";
    });
    z.innerHTML = h;
    aoSelectionBrancher(z);
  }


  /* LES DEUX GESTES, ET LE RECALCUL QU'ILS DÉCLENCHENT.

     ON NE CORRIGE PAS LA LISTE À L'ÉCRAN : on renvoie le geste au moteur et
     on réaffiche ce qu'il rend. Retoucher l'affichage aurait donné deux
     vérités — celle de l'écran et celle du serveur — qui divergeraient au
     premier rechargement. */
  function aoSelectionBrancher(z) {
    z.querySelectorAll("[data-sel-off]").forEach(function (b) {
      b.addEventListener("click", function () {
        var c = b.dataset.selOff;
        delete AO_SEL_AJOUTS[c];
        AO_SEL_ECARTEES[c] = 1;
        aoSelectionRecalculer();
      });
    });
    z.querySelectorAll("[data-sel-on]").forEach(function (b) {
      b.addEventListener("click", function () {
        var c = b.dataset.selOn;
        delete AO_SEL_ECARTEES[c];
        AO_SEL_AJOUTS[c] = 1;
        aoSelectionRecalculer();
      });
    });
    /* LA DÉROULANTE MÈNE À LA PIÈCE dans le dossier rempli, en dessous : elle
       sert à ATTEINDRE, pas à choisir. Un sélecteur qui modifierait la
       sélection ferait de chaque parcours de la liste une décision. */
    ["candidature", "offre", "__non"].forEach(function (g) {
      var sl = $("#ig-ao-grp-" + g, z);
      if (!sl) return;
      sl.addEventListener("change", function () {
        var cible = document.getElementById("ig-ao-p-" + sl.value);
        if (cible && cible.scrollIntoView) {
          cible.scrollIntoView({ block: "center" });
        }
        sl.value = "";
      });
    });
  }


  /* LE RECALCUL PASSE PAR LE SERVEUR, avec les documents déjà lus. Recalculer
     au navigateur supposerait d'y recopier `SOCLE_REPONSE` et les motifs
     d'exigence — deux définitions de « retenue », qui divergeraient le jour
     où l'une des deux serait corrigée. */
  function aoSelectionRecalculer() {
    if (!AO_ANALYSE) return;
    return demander("/api/datacenter/marche/selection", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analyse: AO_ANALYSE,
                             ajouts: Object.keys(AO_SEL_AJOUTS),
                             ecartees: Object.keys(AO_SEL_ECARTEES) }),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) return;
        aoSelectionRendre(j.selection);
        /* LE REMPLISSAGE SUIT LE PÉRIMÈTRE. Sans ce rappel, l'écran de droite
           dirait six pièces et le dossier rempli en dessous en montrerait
           vingt-trois. */
        aoRemplir(true);
      });
  }


  /* LE PÉRIMÈTRE, POUR TOUT CE QUI PRODUIT LE DOSSIER. Une seule fonction le
     donne : le remplissage, l'export, l'archive et le parcours doivent voir
     le MÊME. `null` tant qu'aucune sélection n'existe — c'est-à-dire tout le
     catalogue, le comportement d'avant. */
  function aoPerimetre() {
    if (!AO_SELECTION) return null;
    return AO_SELECTION.lignes.filter(function (x) { return x.retenue; })
      .map(function (x) { return x.cle; });
  }


  function aoCandRendre(p) {
    var out = $("#ig-ao-cand-out");
    var red = {};
    (p.redaction || []).forEach(function (r) { red[r.piece] = r; });
    var h = '<h3 class="ig-tr-st">Le dossier de candidature</h3>';
    if (p.consultation) {
      h += '<div class="ig-encart">';
      if (p.consultation.note) {
        h += esc(p.consultation.note);
      } else {
        Object.keys(p.consultation).forEach(function (k) {
          var c = p.consultation[k];
          h += "<b>" + esc(c.libelle) + "</b> — "
            + esc((c.citations[0] || {}).texte || "") + "<br>";
        });
      }
      h += "</div>";
    }
    h += '<p class="note">L\'ordre n\'est pas celui du règlement de '
      + "consultation : ce qui a un délai d'obtention passe en premier, parce "
      + "que c'est la seule chose qu'on ne rattrape pas la dernière nuit.</p>";
    if (p.exigences_actives) {
      h += '<p class="note ig-ao-exn">' + esc(p.note_exigences || "") + "</p>";
    }
    h += '<div class="ig-ao-cd">';
    p.pieces.forEach(function (x) {
      h += '<div class="ig-ao-cp' + (x.bloquant ? " ig-ao-cpb" : "") + '">'
        + '<div class="ig-ao-cph"><b' + info("piece_candidature:" + x.cle) + ">"
        + esc(x.nom) + "</b>"
        + '<span class="ig-ao-cn">' + esc(x.nature_nom) + "</span>"
        + (x.bloquant ? '<span class="ig-ao-bl">bloquante</span>' : "")
        + aoExigence(p.exigences_actives, x)
        + "</div>"
        + '<p class="ig-ao-cq"><i>Produite par</i> — ' + esc(x.produit_par)
        + "</p><ul class=\"ig-ao-cc\">";
      x.contient.forEach(function (c) { h += "<li>" + esc(c) + "</li>"; });
      h += "</ul>"
        + '<p class="ig-ao-pg"><i>Le piège</i> — ' + esc(x.piege) + "</p>";
      if (x.delai) {
        h += '<p class="ig-ao-dl"><b>Délai d\'obtention</b> — ' + esc(x.delai)
          + "</p>";
      }
      if (x.en_groupement) {
        h += '<p class="ig-ao-gr"><i>En groupement</i> — '
          + esc(x.en_groupement) + "</p>";
      }
      if (red[x.cle]) {
        h += '<div class="ig-ao-red">'
          + '<span>Cette note se rédige — livrable «&nbsp;'
          + esc(red[x.cle].label) + "&nbsp;».</span>"
          + '<button type="button" class="btn btn-s ig-ao-redb" '
          + 'data-rediger="' + esc(x.cle) + '">Mettre en brouillon</button>'
          + '<div class="ig-ao-redo" data-redout="' + esc(x.cle) + '"></div>'
          + "</div>";
      }
      h += "</div>";
    });
    h += "</div>" + '<p class="ig-icpe-res">' + esc(p.note) + "</p>";
    out.innerHTML = h;
  }


  /* ── METTRE UNE NOTE EN BROUILLON ─────────────────────────────────────
     PAR DÉLÉGATION, ET C'EST NÉCESSAIRE : la carte du dossier est reconstruite
     à chaque remplissage, et rebrancher un écouteur par bouton en laisserait
     tôt ou tard un sans. Un écouteur posé sur le document survit à un élément
     qui n'existe pas encore.

     LE BROUILLON DIT SUR QUOI IL S'APPUIE. Un texte qui cite « [CCTP Sud] »
     sans que la page dise d'où vient ce document est invérifiable — et c'est
     exactement ce qu'on interdit au modèle de faire. Les documents du socle
     sont donc affichés SOUS le brouillon, et son absence est affichée aussi :
     elle explique pourquoi le texte est plus pauvre. */
  function aoRedigerRendre(z, j) {
    var h = "";
    if (j.socle_sources && j.socle_sources.length) {
      h += '<p class="ig-ao-reds"><b>Socle documentaire</b> — ' + fr(j.socle_sources.length)
        + " document(s) du fonds : ";
      h += j.socle_sources.map(function (x) {
        return esc(x.titre) + (x.date_source ? " (" + esc(x.date_source) + ")" : "");
      }).join(" · ") + "</p>";
    } else {
      /* NOMMER L'ABSENCE PLUTÔT QUE DE LAISSER LE VIDE PARLER. Un brouillon
         sans socle n'est pas le même document qu'un brouillon avec : le
         relecteur doit savoir lequel il tient. */
      h += '<p class="ig-ao-reds ig-ao-redk"><b>Sans socle documentaire</b> — '
        + esc({ magasin_non_joint: "la base de connaissance n'a pas été jointe",
                base_injoignable: "la base de connaissance est injoignable",
                aucun_extrait: "aucun extrait du thème appels d'offres et CCTP "
                               + "n'a été jugé pertinent"
              }[j.socle_absent] || "aucun extrait retenu")
        + ". Le texte ne s'appuie sur aucun dossier antérieur.</p>";
    }
    if (j.a_completer) {
      h += '<p class="ig-ao-reds"><b>' + fr(j.a_completer) + "</b> passage(s) "
        + "marqué(s) À COMPLÉTER : ce sont les endroits que le modèle n'a pas "
        + "inventés.</p>";
    }
    if (j.tronque) {
      h += '<p class="ig-ao-reds ig-ao-redk"><b>Brouillon tronqué</b> — la '
        + "limite de longueur a été atteinte : la fin manque.</p>";
    }
    /* Sans le moteur de rendu — fichier non chargé — on montre le texte
       plutôt que rien : un lecteur vide serait pire qu'un texte brut. */
    h += '<div class="ig-ao-redm">'
      + ((window.CPMarkdown && CPMarkdown.versHtml)
          ? CPMarkdown.versHtml(j.markdown)
          : "<pre>" + esc(j.markdown) + "</pre>") + "</div>";
    z.innerHTML = h;
  }

  /* ── AFFIRMER « JE L'AI FOURNIE » ────────────────────────────────────
     PAR DÉLÉGATION, comme la rédaction : la carte du dossier se reconstruit à
     chaque remplissage. Le geste bascule l'affirmation et RELANCE le
     remplissage — c'est le serveur qui décide si elle lève un blocage (une
     pièce mesurable ou inconnue reste sans effet), jamais la page. */
  document.addEventListener("click", function (ev) {
    var b = ev.target && ev.target.closest
      ? ev.target.closest("[data-fournie]") : null;
    if (!b) return;
    ev.preventDefault();
    var cle = b.getAttribute("data-fournie");
    if (AO_FOURNIES[cle]) delete AO_FOURNIES[cle];
    else AO_FOURNIES[cle] = true;
    aoRemplir(true);
  });

  document.addEventListener("click", function (ev) {
    var b = ev.target && ev.target.closest
      ? ev.target.closest("[data-rediger]") : null;
    if (!b) return;
    ev.preventDefault();
    var cle = b.getAttribute("data-rediger");
    var z = $('[data-redout="' + cle + '"]');
    if (!z) return;
    b.disabled = true;
    z.innerHTML = '<p class="note">Rédaction en cours — le modèle écrit, '
      + "cela prend une minute ou deux.</p>";
    demander("/api/datacenter/marche/rediger", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ piece: cle, fiche: AO_FICHE,
                             analyse: AO_ANALYSE, saisies: AO_SAISIES })
    }, DELAI_LONG)
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) {
          z.innerHTML = '<p class="ig-dep-ko">'
            + esc((j && j.message) || "Le brouillon n'a pas pu être écrit.")
            + "</p>";
          return;
        }
        aoRedigerRendre(z, j);
      })
      .catch(function (e) {
        if (e && e.name === "SessionEteinte") return;
        z.innerHTML = '<p class="ig-dep-ko">'
          + esc(messageDelai(e, "Le brouillon n'a pas pu être écrit."))
          + "</p>";
      })
      .then(function () { b.disabled = false; });
  });


  /* ── LA DENSITÉ CONTRE LE BÂTIMENT (section 11) ────────────────────────
     CE QUE CE RENDU DOIT FAIRE COMPRENDRE, ET DANS QUEL ORDRE. Le lecteur
     arrive avec une idée de refroidissement et repart avec une question de
     structure : l'ordre des blocs est donc VERDICT DE PLANCHER D'ABORD, froid
     ensuite. L'inverse — les familles de refroidissement en tête — laisserait
     lire « il faut du liquide » et refermer la page, ce qui est exactement
     l'erreur que cette section existe pour corriger.

     LE FORMULAIRE NE PRÉ-REMPLIT RIEN. Ni la densité, ni la masse, ni le
     plancher : sur ce sujet une valeur par défaut deviendrait la réponse, et
     un verdict de plancher calculé sur une masse supposée serait pire que pas
     de verdict du tout. Le choix d'un régime REMPLIT la masse, visiblement, et
     le résultat dit d'où elle vient. */
  var DENSITE = null;

  /* L'ÉCHELLE, AVANT LE FORMULAIRE. Une salle éprouvée seule ne dit pas
     pourquoi le sujet presse : c'est le PARC qui le dit. Ce bloc est le seul
     de la section qui ne dépende d'aucune saisie — il pose la question à
     laquelle le formulaire ci-dessous répond pour VOTRE bâtiment.

     LE CHIFFRE EST UNE PROJECTION, ET LE RENDU LE DIT AVANT DE S'EN SERVIR.
     La source et la réserve sortent avec la lecture, pas en note de bas de
     page : un ordre de grandeur repris sans son émetteur devient un fait au
     bout de deux citations. */
  function densiteEchelle() {
    var z = $("#ig-den-echelle"), R = (REF && REF.densite) || null;
    if (!z || !R || !R.pression_construction) return;
    var e = R.pression_construction, m = e.projection || {};
    z.innerHTML = '<div class="ig-encart" style="margin:14px 0">'
      + "<b>À l’échelle du parc français.</b> " + esc(e.lecture)
      + '<br><span class="note">Source — ' + esc(m.source) + " "
      + esc(m.reserve) + "</span></div>";
  }

  function densiteFormulaire() {
    var z = $("#ig-den-form"), R = (REF && REF.densite) || null;
    if (!z || !R) return;
    var h = '<div class="dc-grille">';
    h += '<label class="dc-champ" for="ig-den-kw"><span class="dc-lab">'
      + 'Puissance par baie <span class="dc-unite">(kW)</span></span>'
      + '<input id="ig-den-kw" type="number" min="0.5" step="0.5" '
      + 'placeholder="— à préciser —"></label>';

    h += '<label class="dc-champ" for="ig-den-regime"><span class="dc-lab">'
      + 'Reprendre un régime connu</span><select id="ig-den-regime">'
      + '<option value="">— non, je saisis la masse —</option>';
    (R.ordre_regimes || Object.keys(R.regimes)).forEach(function (k) {
      var v = R.regimes[k];
      h += '<option value="' + esc(k) + '">' + esc(v.nom) + ' — '
        + fr(v.kw_baie, 0) + ' kW, ' + fr(v.masse_baie_kg, 0) + ' kg</option>';
    });
    h += "</select></label>";

    h += '<label class="dc-champ" for="ig-den-masse"><span class="dc-lab">'
      + 'Masse d’une baie en ordre de marche <span class="dc-unite">(kg)</span>'
      + '</span><input id="ig-den-masse" type="number" min="1" step="10" '
      + 'placeholder="— à préciser —"></label>';

    h += '<label class="dc-champ" for="ig-den-plancher"><span class="dc-lab">'
      + 'Plancher du bâtiment</span><select id="ig-den-plancher">'
      + '<option value="">— non précisé —</option>';
    Object.keys(R.planchers).forEach(function (k) {
      h += '<option value="' + esc(k) + '">' + esc(R.planchers[k].nom) + ' — '
        + fr(R.planchers[k].kpa, 1) + ' kPa</option>';
    });
    h += "</select></label>";

    h += '<label class="dc-champ" for="ig-den-fp"><span class="dc-lab">'
      + 'Faux-plancher</span><select id="ig-den-fp">'
      + '<option value="">— non précisé —</option>';
    Object.keys(R.faux_planchers).forEach(function (k) {
      var v = R.faux_planchers[k];
      h += '<option value="' + esc(k) + '">' + esc(v.nom)
        + (v.ponctuel_service_kg ? ' — ' + fr(v.ponctuel_service_kg, 0)
          + ' kg par pied' : "") + "</option>";
    });
    h += "</select></label>";

    h += '<label class="dc-champ" for="ig-den-diff"><span class="dc-lab">'
      + 'Famille en place dans la salle</span><select id="ig-den-diff">'
      + '<option value="">— non précisée, ou construction neuve —</option>';
    (R.ordre_diffusion || []).forEach(function (k) {
      h += '<option value="' + esc(k) + '">' + esc(R.diffusion[k].nom)
        + "</option>";
    });
    h += "</select></label></div>";
    h += '<p class="note" style="margin:10px 0 0">' + esc(R.diffusion_source)
      + "</p>";
    z.innerHTML = h;

    /* Choisir un régime REMPLIT les deux champs au lieu de les remplacer en
       coulisses : le lecteur voit la valeur reprise, et peut la corriger. */
    var sel = $("#ig-den-regime");
    if (sel) sel.addEventListener("change", function () {
      var v = R.regimes[sel.value];
      if (!v) return;
      $("#ig-den-kw").value = v.kw_baie;
      $("#ig-den-masse").value = v.masse_baie_kg;
    });
  }

  function densiteLire() {
    function val(id) { var e = $(id); return e ? (e.value || "").trim() : ""; }
    return {
      kw_baie: val("#ig-den-kw"),
      masse_baie_kg: val("#ig-den-masse"),
      regime: val("#ig-den-regime"),
      plancher: val("#ig-den-plancher"),
      faux_plancher: val("#ig-den-fp"),
      diffusion_existante: val("#ig-den-diff"),
    };
  }

  function densiteEprouver() {
    var msg = $("#ig-den-msg"), out = $("#ig-den-out");
    if (!out) return;
    msg.textContent = "Calcul…";
    demander("/api/datacenter/densite", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(densiteLire()),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) {
          msg.textContent = (j && j.message) || "Calcul indisponible.";
          out.innerHTML = "";
          return;
        }
        DENSITE = j;
        msg.textContent = "";
        densiteRendre(j.etude);
      })
      .catch(function (e) {
        if (e && e.name === "SessionEteinte") return;
        msg.textContent = messageDelai(e, "Calcul indisponible.");
      });
  }

  function densiteRendre(e) {
    var out = $("#ig-den-out");
    out.innerHTML = densitePlancher(e) + densiteFroid(e) + densiteTransport(e)
      + densiteRenovation(e) + densiteReserve(e.reserve_charge);
  }

  /* LE PLANCHER VIENT EN PREMIER, et c'est délibéré : voir plus haut.

     LES DEUX CRITÈRES SORTENT ENSEMBLE, et le verdict DIT lequel mord. Ce
     n'est pas de la complétude : une salle dont la dalle tient et dont les
     panneaux non se répare en retirant le faux-plancher, quand une salle dont
     la dalle ne tient pas ne se répare pas du tout. Un verdict qui ne dirait
     pas lequel des deux enverrait reprendre une structure là où il suffisait
     de démonter un plancher technique. */
  function densitePlancher(e) {
    var p = e.plancher;
    var h = '<div class="rc-card" style="margin-top:14px"><h3>Le plancher</h3>';
    if (p.verdict === "indetermine") {
      return h + '<p class="note">' + esc(p.message) + "</p></div>";
    }
    var MOT = { go: "PASSE", limite: "PASSE SANS RÉSERVE", nogo: "NE PASSE PAS" };
    h += "<p><b>" + esc(MOT[p.verdict]) + "</b> — " + esc(p.message) + "</p>";

    var d = p.dalle;
    h += "<p><b>La dalle, en charge répartie —</b> " + fr(p.masse_baie_kg, 0)
      + " kg sur " + fr(d.surface_influence_m2, 2) + " m² de surface "
      + "d’influence, soit <b>" + fr(d.charge_repartie_kg_m2, 0)
      + " kg/m²</b> (" + fr(d.charge_repartie_kpa, 2) + " kPa) pour "
      + fr(d.capacite_kg_m2, 0) + " kg/m² déclarés — "
      + fr(d.taux_occupation * 100, 0) + " % de la capacité. ("
      + esc(MOT[d.verdict]) + ")</p>";

    var f = p.faux_plancher;
    h += "<p><b>Le faux-plancher, en charge ponctuelle —</b> ";
    if (f.ponctuel_admis_kg) {
      h += "<b>" + fr(f.charge_par_pied_kg, 0) + " kg par pied</b> pour "
        + fr(f.ponctuel_admis_kg, 0) + " kg admis par un « "
        + esc(f.nom) + " » — " + fr(f.taux_occupation * 100, 0)
        + " % de la capacité. (" + esc(MOT[f.verdict]) + ")</p>";
    } else {
      h += esc(f.message) + "</p>";
    }

    h += '<p class="note">Pour information, la pression sous l’emprise nue de '
      + "la baie est de " + fr(e.plancher.pression_sous_emprise_kg_m2, 0)
      + " kg/m². Elle ne se compare à aucune des deux capacités ci-dessus : "
      + "une capacité en kilopascals est une charge RÉPARTIE.</p>";

    h += "<p><b>À vérifier, et qui ne figure dans aucun des deux verdicts :"
      + "</b></p><ul>";
    (p.a_verifier || []).forEach(function (x) { h += "<li>" + esc(x) + "</li>"; });
    h += '</ul><p class="note">' + esc(p.source) + "</p></div>";
    return h;
  }

  function densiteFroid(e) {
    var d = e.diffusion;
    var h = '<div class="rc-card" style="margin-top:14px">'
      + "<h3>Les familles de refroidissement</h3>";
    if (d.premiere_admise) {
      h += "<p>À " + fr(e.kw_baie, 0) + " kW par baie, la famille la moins "
        + "coûteuse en bâtiment qui tienne cette densité est <b"
        + info("diffusion:" + d.premiere_admise.cle) + ">"
        + esc(d.premiere_admise.nom) + "</b>.";
      if (d.liquide_impose) {
        h += " L’air n’est plus une option : ce n’est pas un arbitrage de "
          + "coût, c’est la section de passage qui ne tient plus dans le "
          + "bâtiment.";
      }
      h += "</p>";
    }
    if ((d.exclues || []).length) {
      h += "<p><b>Écartées par la densité —</b></p><ul>";
      d.exclues.forEach(function (x) {
        h += "<li><b" + info("diffusion:" + x.cle) + ">" + esc(x.nom)
          + "</b> : plafond " + fr(x.plafond_kw_baie, 0) + " kW/baie, dépassé "
          + fr(x.depassement, 1) + " fois. " + esc(x.ce_qui_plafonne) + "</li>";
      });
      h += "</ul>";
    } else {
      h += '<p class="note">Aucune famille n’est écartée à cette densité.</p>';
    }
    return h + "</div>";
  }

  function densiteTransport(e) {
    var t = e.transport;
    return '<div class="rc-card" style="margin-top:14px">'
      + "<h3>Ce qu’il faut de section à l’eau et à l’air</h3>"
      + "<p>Pour la même chaleur&nbsp;: <b>" + fr(t.eau.debit_m3_h, 1)
      + " m³/h d’eau</b> dans un tube de " + fr(t.eau.diametre_equivalent_mm, 0)
      + " mm (écart " + fr(t.eau.delta_t_k, 0) + " K, "
      + fr(t.eau.vitesse_m_s, 1) + " m/s), contre <b>"
      + fr(t.air.debit_m3_h, 0) + " m³/h d’air</b> dans une gaine de "
      + fr(t.air.cote_carre_m, 2) + " m de côté (écart "
      + fr(t.air.delta_t_k, 0) + " K, " + fr(t.air.vitesse_m_s, 1)
      + " m/s).</p><p>" + esc(t.lecture) + "</p></div>";
  }

  function densiteRenovation(e) {
    var r = e.renovation;
    var h = '<div class="rc-card" style="margin-top:14px">'
      + "<h3>Ce que cela veut dire pour un site existant</h3>";
    (r.leves || []).forEach(function (x) { h += "<p>" + esc(x) + "</p>"; });
    if ((r.obstacles || []).length) {
      h += "<ul>";
      r.obstacles.forEach(function (x) { h += "<li>" + esc(x) + "</li>"; });
      h += "</ul>";
    }
    return h + '<p class="note">' + esc(r.note) + "</p></div>";
  }

  function densiteReserve(v) {
    if (!v) return "";
    return '<div class="ig-encart" style="margin-top:14px">'
      + "<b>La réserve de charge, à spécifier avant la commande de la "
      + "charpente.</b> Environ " + fr(v.valeur_kg, 0) + " kg portés par "
      + esc(v.porte_par) + ". " + esc(v.quand) + " " + esc(v.qui)
      + '<br><span class="note">' + esc(v.reserve) + "</span></div>";
  }

  /* LES PRATIQUES ET LES ÉCARTS SORTENT ENSEMBLE, dans le même dépliant. Un
     tri qui ne montre que ce qu'il garde n'est pas un tri : c'est une reprise.
     Séparer les deux blocs sur deux écrans reviendrait au même. */
  function densitePratiques() {
    var z = $("#ig-den-prat-c"), R = (REF && REF.densite) || null;
    if (!z || !R) return;
    var h = '<p class="note">' + esc(R.construction_source) + "</p>";
    h += "<h4>Retenues — le mécanisme, et ce qu’il ne couvre pas</h4><ul>";
    Object.keys(R.construction).forEach(function (k) {
      var v = R.construction[k];
      h += "<li><b" + info("pratique_construction:" + k) + ">" + esc(v.nom)
        + "</b> — " + esc(v.pratique) + " <i>Pourquoi cela marche :</i> "
        + esc(v.mecanisme) + " <i>Ce que cela ne couvre pas :</i> "
        + esc(v.ne_couvre_pas)
        + (v.reserve ? ' <span class="note">Réserve : ' + esc(v.reserve)
          + "</span>" : "") + "</li>";
    });
    h += "</ul><h4>Écartées — l’affirmation, et le motif du refus</h4><ul>";
    Object.keys(R.ecartes).forEach(function (k) {
      var v = R.ecartes[k];
      h += "<li>" + esc(v.affirmation) + " <b>Motif —</b> " + esc(v.motif)
        + "</li>";
    });
    z.innerHTML = h + "</ul>";
  }

  /* ── LE DOSSIER D'OFFRE — CE QUE VOUS PROPOSEZ, PAS QUI VOUS ÊTES ───────
     UN BLOC À PART, PAS UN GROUPE DE PLUS DANS `aoCandRendre`. Cette page,
     comme tout le reste du fichier, appelle « dossier de candidature » celui
     qui établit qui vous êtes ; l'acte d'engagement, la DPGF et le mémoire
     technique établissent ce que vous PROPOSEZ. Les y ranger sous le même
     intitulé dirait quelque chose de faux.

     TOUTES LES PIÈCES SONT VISIBLES, AUCUN MENU : à la différence des dix-
     neuf pièces de candidature, qui se lisent une à la fois derrière un menu
     tant elles sont nombreuses et denses, les trois pièces de l'offre se
     comptent — c'est un inventaire à vérifier avant dépôt, pas un parcours à
     dérouler. */
  function offreRendre(o) {
    var out = $("#ig-ao-offre-out");
    var h = '<h3 class="ig-tr-st">Le dossier d\'offre</h3>';
    if (o.exigences_actives) {
      h += '<p class="note ig-ao-exn">' + esc(o.note_exigences || "") + "</p>";
    }
    h += '<div class="ig-ao-cd">';
    o.pieces.forEach(function (p) {
      h += '<div class="ig-ao-cp' + (p.bloquant ? " ig-ao-cpb" : "") + '">'
        + '<div class="ig-ao-cph"><b' + info("piece_offre:" + p.cle) + ">"
        + esc(p.nom) + "</b>"
        + '<span class="ig-ao-cn">' + esc(p.nature_nom) + "</span>"
        + '<span class="ig-ao-cn">' + esc(p.famille_nom) + "</span>"
        + (p.bloquant ? '<span class="ig-ao-bl">bloquante</span>' : "")
        + aoExigence(o.exigences_actives, p)
        + "</div>"
        + '<p class="ig-ao-cq"><i>Produite par</i> — ' + esc(p.produit_par)
        + "</p><ul class=\"ig-ao-cc\">";
      p.contient.forEach(function (c) { h += "<li>" + esc(c) + "</li>"; });
      h += "</ul>"
        + '<p class="ig-ao-pg"><i>Le piège</i> — ' + esc(p.piege) + "</p>";
      if (p.en_groupement) {
        h += '<p class="ig-ao-gr"><i>En groupement</i> — '
          + esc(p.en_groupement) + "</p>";
      }
      h += "</div>";
    });
    /* MÊME PLACE, MÊME CLASSE QUE LA RÉSERVE DU DOSSIER DE CANDIDATURE
       (`aoCandRendre`, juste au-dessus) : en pied de bloc, dans le style
       discret des réserves légales du fichier — jamais en tête, en pleine
       intensité, comme si c'était le message principal de la carte. */
    h += "</div>" + '<p class="ig-icpe-res">' + esc(o.note) + "</p>";
    out.innerHTML = h;
  }


  /* ── LA FICHE DU CANDIDAT, ET LE REMPLISSAGE EN TEMPS RÉEL ─────────────
     CE QUE CE BLOC RÉSOUT. Un dossier de candidature, c'est dix-neuf pièces
     qui redemandent les mêmes vingt informations. Les recopier à la main est
     le travail qui produit les fautes de cohérence dont les candidatures
     meurent — un SIRET d'une autre filiale sur un DC2, un objet de marché
     amputé sur un DC1.

     LA FICHE NE QUITTE PAS CE NAVIGATEUR. Elle est gardée en local, comme les
     pièces de la consultation ne sont pas déposées : on prépare une réponse
     avant de décider si on la remet, et l'identité d'une entreprise n'a pas à
     s'enregistrer quelque part pour cela.

     LE CRITÈRE DE REMPLISSAGE VIT AU SERVEUR. Recopié ici, il dériverait de
     celui du module à la première rubrique ajoutée — et une pièce annoncée
     prête pour un critère périmé est pire qu'une pièce annoncée incomplète. */
  var AO_FICHE = {};
  var AO_SAISIES = {};
  var AO_REMPLI = null;
  var _aoTempo = null;

  function aoFicheCharger() {
    try {
      AO_FICHE = JSON.parse(localStorage.getItem("ao-fiche-v1") || "{}") || {};
      AO_SAISIES = JSON.parse(localStorage.getItem("ao-saisies-v1") || "{}") || {};
    } catch (e) { AO_FICHE = {}; AO_SAISIES = {}; }
  }
  function aoFicheEnregistrer() {
    try {
      localStorage.setItem("ao-fiche-v1", JSON.stringify(AO_FICHE));
      localStorage.setItem("ao-saisies-v1", JSON.stringify(AO_SAISIES));
    } catch (e) { /* navigation privée, stockage refusé : rien ne casse */ }
  }

  /* L'UNIQUE APPEL. Débounce à 450 ms : on tape à deux mains, et une requête
     par frappe ferait vingt allers-retours pour une ligne d'adresse. */
  function aoRemplir(immediat) {
    if (_aoTempo) clearTimeout(_aoTempo);
    /* L'ÉTAT DES MODÈLES EST DEMANDÉ UNE SEULE FOIS, et son échec ne coûte que
       les boutons : le report reste affiché. Le redemander à chaque frappe
       dans la fiche solliciterait le serveur pour une réponse qui ne change
       pas d'une saisie à l'autre. */
    if (AO_FORMULAIRES === null) {
      AO_FORMULAIRES = {};                      /* une seule tentative */
      aoFormulairesCharger().then(function () {
        if (AO_REMPLI) aoRempliRendre(AO_REMPLI);
      });
    }
    _aoTempo = setTimeout(function () {
      demander("/api/datacenter/marche/remplir", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fiche: AO_FICHE, analyse: AO_ANALYSE,
                               saisies: AO_SAISIES, groupement: false,
                               fournies: Object.keys(AO_FOURNIES) ,
                               perimetre: aoPerimetre() }),
      }).then(function (r) { return r.json(); })
        .then(function (j) {
          if (!j || !j.ok) return;
          AO_REMPLI = j.remplissage;
          if (!$("#ig-ao-fiche").innerHTML) aoFicheRendre(j.remplissage);
          aoRempliRendre(j.remplissage);
          /* LES VINGT-TROIS PIÈCES SONT CHOISIES D'OFFICE DÈS QU'UN DOSSIER
             A ÉTÉ ANALYSÉ.

             POURQUOI ICI ET PAS APRÈS `aoRemplir`. Cette fonction est
             asynchrone : choisir juste après l'avoir appelée reviendrait à
             parcourir un remplissage pas encore arrivé, et à ne rien cocher.
             C'est à la réponse que l'état existe.

             POURQUOI D'OFFICE. Analyser un dossier de consultation n'a qu'un
             but : produire la réponse. Laisser la sélection vide obligeait à
             cocher vingt-trois cartes pour dire « oui, tout » — qui est le cas
             courant. Le choix reste défaisable : on décoche ce qu'on ne
             dépose pas. Et il ne se fait QU'UNE FOIS, à la première réponse
             qui suit une analyse : le refaire à chaque frappe dans la fiche
             recocherait ce qu'on vient de décocher. */
          if (AO_ANALYSE && !AO_CHOIX_FAIT) {
            AO_CHOIX_FAIT = true;
            aoToutChoisir();
          }
        })
        .catch(function () { /* l'état affiché reste tel quel */ });
    }, immediat ? 0 : 450);
  }

  function aoFicheRendre(r) {
    var z = $("#ig-ao-fiche");
    if (!z) return;
    var parGroupe = {};
    r.champs.forEach(function (c) {
      (parGroupe[c.groupe] = parGroupe[c.groupe] || []).push(c);
    });
    var h = '<h3 class="ig-tr-st">Votre fiche — saisie une fois, reportée '
      + "partout</h3>"
      + '<p class="note">Elle ne quitte pas ce navigateur : rien n\'est '
      + "envoyé au serveur pour être conservé, et rien n\'est enregistré. "
      + "Chaque valeur saisie ici se reporte, en dessous, dans toutes les "
      + "pièces qui la demandent — avec la mention de son origine.</p>"
      /* LE GESTE QUI MANQUAIT, ET LE DÉFAUT QU'IL CORRIGE.
         `_ao_charge()` verse DÉJÀ la fiche du cabinet comme socle côté
         serveur : le SIRET, le SIREN, la TVA et les trois chiffres d'affaires
         atteignent les formulaires à chaque appel. Mais ces champs-ci lisent
         le stockage du navigateur, et affichaient donc « non renseigné » sur
         des valeurs que le serveur allait employer. Mesuré en navigateur.
         L'écran disait le contraire de ce qu'il produisait — ce qui fait
         ressaisir à la main ce qui était déjà là, ou pousser une valeur
         approximative par-dessus une valeur vérifiée.
         C'EST UN GESTE, PAS UN PRÉ-REMPLISSAGE. Le faire au chargement
         supposerait que toute consultation se réponde au nom de CONSEILPREV ;
         or ce § sert aussi à instruire le dossier d'un client, et un client
         répond avec SON identité. */
      + '<div class="ig-ao-cab">'
      + '<button type="button" class="btn btn-s" id="ig-ao-cab-go">'
      + "Charger la fiche du cabinet</button>"
      + '<span class="note" id="ig-ao-cab-msg">Les valeurs du dossier '
      + "d'entreprise CONSEILPREV — dénomination, SIRET, chiffres d'affaires — "
      + "s'écrivent dans les champs ci-dessous. Ce que vous avez déjà saisi "
      + "n'est pas écrasé.</span></div>";
    r.groupes.forEach(function (g) {
      var champs = parGroupe[g[0]] || [];
      if (!champs.length) return;
      h += '<div class="ig-ao-fg"><h4>' + esc(g[1]) + "</h4>"
        + '<div class="ig-ao-ff">';
      champs.forEach(function (c) {
        h += '<label class="ig-ao-fc"><span class="ig-ao-fl">' + esc(c.nom)
          + "</span>"
          + '<input type="text" data-fiche="' + esc(c.cle) + '" value="'
          + esc(AO_FICHE[c.cle] || "") + '" placeholder="non renseigné">'
          + (c.ou ? '<span class="ig-ao-fo">' + esc(c.ou) + "</span>" : "")
          + "</label>";
      });
      h += "</div></div>";
    });
    z.innerHTML = h;
    z.querySelectorAll("[data-fiche]").forEach(function (i) {
      i.addEventListener("input", function () {
        AO_FICHE[i.dataset.fiche] = i.value;
        aoFicheEnregistrer();
        aoRemplir();
      });
    });
    var cab = $("#ig-ao-cab-go", z);
    if (cab) cab.addEventListener("click", aoFicheCabinet);
  }


  /* LA FICHE DU CABINET, ÉCRITE DANS LES CHAMPS SOUS LES YEUX DE QUI DEMANDE.

     CE QU'ELLE N'ÉCRASE PAS : ce qui est déjà saisi. Une consultation peut
     demander une variante — un établissement secondaire, un autre signataire
     — et celui qui l'a tapée en sait plus que le dossier. C'est le même ordre
     que côté serveur, où le socle passe DERRIÈRE la saisie : les deux
     divergeraient si l'un des deux s'inversait.

     ELLE DIT AUSSI CE QUI MANQUE AU DOSSIER. Le RCS, le code NAF, l'effectif
     et l'assurance n'y sont pas ; annoncer « fiche chargée » sans le dire
     ferait croire la fiche complète, et c'est au dépôt des plis qu'on s'en
     apercevrait. */
  function aoFicheCabinet() {
    var msg = $("#ig-ao-cab-msg"), b = $("#ig-ao-cab-go");
    if (b) b.disabled = true;
    if (msg) msg.textContent = "Lecture du dossier d'entreprise…";
    return demander("/api/datacenter/marche/fiche-cabinet",
                    { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) throw new Error((j && j.message) || "dossier");
        var pose = 0, gardes = 0;
        Object.keys(j.fiche || {}).forEach(function (k) {
          if (String(AO_FICHE[k] || "").trim()) { gardes++; return; }
          AO_FICHE[k] = j.fiche[k];
          pose++;
        });
        aoFicheEnregistrer();
        var absents = (j.manques || []).map(function (m) { return m.cle; });
        /* ON REDESSINE LA FICHE AVANT DE PARLER. Les champs portent les
           anciennes valeurs dans leur attribut `value` : sans ce tour, on
           annoncerait « 16 valeurs écrites » au-dessus de seize champs
           restés vides. `aoRemplir` ne redessine la fiche que si elle est
           VIDE — mesuré dans le source — donc c'est ici, et nulle part
           ailleurs, que le redessin doit se faire. */
        if (AO_REMPLI) aoFicheRendre(AO_REMPLI);
        aoRemplir();
        var m2 = $("#ig-ao-cab-msg");
        if (m2) m2.textContent =
          pose + " valeur(s) écrite(s)"
          + (gardes ? ", " + gardes + " saisie(s) conservée(s)" : "")
          + ". Le dossier fournit " + j.fournis + " champ(s) sur " + j.attendus
          + (absents.length
             ? " — absents : " + absents.join(", ")
               + ". Ils ne s'inventent pas : portez-les au dossier "
               + "d'entreprise."
             : ".");
      })
      .catch(function (e) {
        var m2 = $("#ig-ao-cab-msg");
        if (m2) m2.textContent =
          "Le dossier d'entreprise n'a pas pu être lu : " + (e.message || e);
      })
      .then(function () { var b2 = $("#ig-ao-cab-go"); if (b2) b2.disabled = false; });
  }


  /* L'EXPORT REFAIT LE CALCUL AU SERVEUR au lieu de mettre en page ce que la
     page a sous les yeux : le document emporté doit dire la même chose que
     l'écran, et le seul moyen de le garantir est qu'il vienne de la même
     fonction. Renvoyer l'état affiché ferait circuler un dossier construit
     depuis un état que le serveur n'a jamais validé. */
  /* ── LE FORMULAIRE OFFICIEL LUI-MÊME ──────────────────────────────────
     CE QUI LE SÉPARE DE L'EXPORT JUSTE AU-DESSUS. L'export produit un report
     tracé, à recopier sur le formulaire en le vérifiant. Ici, le serveur ouvre
     le fichier du ministère — sa version, sa mise en page, sa date de mise à
     jour — et écrit dans les emplacements qu'il laisse vides. Un fac-similé
     redessiné serait refusé par l'acheteur, ou pire, accepté et faux.

     LA PAGE NE DEVINE PAS QUELS FORMULAIRES SONT DISPONIBLES : elle le
     demande. Un bouton proposé pour un modèle absent produirait une erreur au
     clic ; un bouton caché sans explication ferait croire que la fonction
     n'existe pas. */
  var AO_FORMULAIRES = null;

  function aoFormulairesCharger() {
    return demander("/api/datacenter/marche/formulaires",
                    { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) { if (j && j.ok) AO_FORMULAIRES = j; })
      .catch(function () { AO_FORMULAIRES = null; });
  }

  function aoFormulairesBoutons() {
    /* `{}` EST L'ÉTAT « DEMANDÉ, PAS ENCORE REÇU », et il ne doit pas lever :
       `AO_FORMULAIRES.etat` n'existe pas encore. Un `.etat.prets` nu ferait
       tomber tout le rendu du report pour une liste de boutons. */
    if (!AO_FORMULAIRES || !AO_FORMULAIRES.etat
        || !AO_FORMULAIRES.etat.prets.length) return "";
    var h = "";
    AO_FORMULAIRES.etat.prets.forEach(function (cle) {
      var m = AO_FORMULAIRES.modeles[cle] || {};
      h += '<button type="button" class="btn btn-s" data-ao-form="'
        + esc(cle) + '">Remplir le ' + esc(m.nom || cle.toUpperCase())
        + " (Word)</button>";
    });
    return h;
  }

  function aoFormulaireRemplir(cle, bouton) {
    var libelle = bouton.textContent;
    var msg = $("#ig-ao-msg");
    bouton.disabled = true;
    bouton.textContent = "Remplissage…";
    var etat = null;
    demander("/api/datacenter/marche/formulaire", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modele: cle, fiche: AO_FICHE,
                             analyse: AO_ANALYSE, saisies: AO_SAISIES }),
    }, DELAI_MOYEN).then(function (r) {
      if (!r.ok) throw new Error("remplissage");
      /* CE QUI N'A PAS ÉTÉ PLACÉ VOYAGE DANS UN EN-TÊTE : un téléchargement
         ne rend pas de JSON, et un formulaire partiel se lirait comme
         complet si personne ne disait ce qui manque. */
      try { etat = JSON.parse(r.headers.get("X-Remplissage") || "null"); }
      catch (e) { etat = null; }
      return r.blob();
    }).then(function (b) {
      var u = URL.createObjectURL(b);
      var a = document.createElement("a");
      a.href = u;
      a.download = cle + "-projet-non-signe.docx";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
      if (msg) {
        msg.textContent = etat
          ? (etat.places + " rubrique(s) écrite(s) dans le formulaire officiel"
             + " (version du " + etat.maj + "). NON SIGNÉ : les déclarations "
             + "sur l'honneur et les blocs de signature sont restés vides."
             + (etat.non_places.length
                ? " Sans emplacement trouvé : " + etat.non_places.join(", ")
                  + "." : "")
             + (etat.ignores.length
                ? " Sans valeur, donc laissées vides : "
                  + etat.ignores.join(", ") + "." : "")
             /* CE QU'ON DÉTIENT ET QUE LE FORMULAIRE N'OFFRE PAS D'ÉCRIRE.
                Ni « non placée » — le modèle n'a pas d'emplacement —, ni
                « sans valeur » : la valeur est là et juste. Se taire ferait
                croire le formulaire aussi complet qu'il peut l'être, alors
                qu'il reste trois lignes à recopier. */
             + ((etat.sans_ancre || []).length
                ? " À RECOPIER À LA MAIN — le formulaire n'a pas de case "
                  + "pour : " + etat.sans_ancre.join(", ") + "." : ""))
          : "Formulaire téléchargé.";
      }
    }).catch(function () {
      if (msg) {
        msg.textContent = "Le formulaire n'a pas pu être rempli. Le modèle "
          + "est peut-être absent du serveur, ou modifié depuis que ses "
          + "emplacements ont été repérés — auquel cas le remplissage est "
          + "refusé plutôt que fait à côté.";
      }
    }).then(function () {
      bouton.disabled = false;
      bouton.textContent = libelle;
    });
  }

  function aoExporter(fmt, bouton) {
    var libelle = bouton.textContent;
    bouton.disabled = true;
    bouton.textContent = "Mise en page…";
    demander("/api/datacenter/marche/export", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fiche: AO_FICHE, analyse: AO_ANALYSE,
                             saisies: AO_SAISIES, format: fmt ,
                               perimetre: aoPerimetre() }),
    }, DELAI_MOYEN).then(function (r) {
      if (!r.ok) throw new Error("export");
      return r.blob();
    }).then(function (b) {
      var u = URL.createObjectURL(b);
      var a = document.createElement("a");
      a.href = u;
      a.download = "dossier-candidature." + fmt;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
    }).catch(function () {
      $("#ig-ao-msg").textContent = "La mise en page du dossier a échoué.";
    }).then(function () {
      bouton.disabled = false;
      bouton.textContent = libelle;
    });
  }

  /* ── LE PARCOURS GUIDÉ DE LA RÉPONSE ──────────────────────────────────
     LA PAGE AFFICHE, ELLE NE CALCULE PAS. Le compte des rubriques, des
     pièces et des champs tenus vient du serveur, qui le tire du même
     `ao_dc.remplir` que le remplissage affiché plus bas. Le refaire ici
     donnerait deux comptes qui divergeraient — et c'est celui qu'on oublie
     de corriger qui resterait sous les yeux.

     LE PROJET EST TRANSMIS QUAND IL Y EN A UN : sans lui, les affirmations
     ne se lisent pas, et l'étape des déclarations dit alors « 0 sur 6 », ce
     qui est exact — une affirmation qui ne laisse pas de trace n'engage
     personne. */
  function aoParcoursRendre(p) {
    var z = $("#ig-aop-out");
    if (!z) return;
    var h = '<p class="ig-aop-b">' + p.faites + " / " + p.total
          + " étape(s) mesurée(s) comme faites"
          + (p.pret ? " · rien de bloquant ne manque"
                    : " · " + p.bloquants.length + " étape(s) bloquante(s)")
          + "</p><ol class=\"ig-aop-l\">";
    p.etapes.forEach(function (e) {
      var cls = "ig-aop-e" + (e.fait ? " faite" : "")
              + (!e.fait && e.bloquant ? " bloque" : "")
              + (e.id === p.ou_en_est ? " ici" : "");
      h += '<li class="' + cls + '">'
        + "<b>" + esc(e.nom) + "</b>"
        + (e.bloquant ? ' <span class="pg">— bloquante</span>' : "")
        + '<span class="ig-aop-m">' + esc(e.mesure) + "</span>"
        + "<p>" + esc(e.question) + "</p>"
        + (e.fait ? ""
                  : "<p>" + esc(e.geste)
                    + (e.reste && e.reste.length
                        ? " <i>Reste&nbsp;: " + esc(e.reste.join(", ")) + "</i>"
                        : "") + "</p>")
        + '<p class="pg"><i>Le piège</i> — ' + esc(e.piege) + "</p>"
        + "</li>";
    });
    h += "</ol>" + '<p class="ig-aop-r">' + esc(p.reserve) + "</p>";
    z.innerHTML = h;
  }

  function aoParcours(bouton) {
    var z = $("#ig-aop-out");
    var libelle = bouton ? bouton.textContent : "";
    if (bouton) { bouton.disabled = true; bouton.textContent = "Mesure…"; }
    /* LE PÉRIMÈTRE ENTRE ICI AUSSI, et il a failli être oublié : cette
       fonction prépare sa charge dans une VARIABLE au lieu de l'écrire dans
       l'appel, si bien que le câblage automatique des trois autres l'a
       sautée. C'est exactement l'indirection qui avait déjà fait passer cette
       fonction sous une règle de la maison, le 06/09/2026. Sans le périmètre,
       le parcours compterait les blocages des vingt-trois pièces tandis que
       l'écran en annonce six. */
    var corps = { fiche: AO_FICHE, analyse: AO_ANALYSE, saisies: AO_SAISIES,
                  perimetre: aoPerimetre() };
    if (AO_PROJET) corps.projet = AO_PROJET;
    demander("/api/datacenter/marche/parcours", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps),
    }, DELAI_MOYEN).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) throw new Error(j.message || "parcours");
        aoParcoursRendre(j.parcours);
      })
      .catch(function () {
        if (z) z.innerHTML = '<p class="note">Le parcours n\'a pas pu être '
          + "mesuré. Rien n'est perdu : votre fiche et vos pièces sont "
          + "intactes.</p>";
      })
      .then(function () {
        if (bouton) { bouton.disabled = false; bouton.textContent = libelle; }
      });
  }

  /* TOUT LE DOSSIER, ET CE QU'IL A MANQUÉ. Le compte revient dans un
     en-tête : un téléchargement ne rend pas de JSON, et une archive dont on
     ne sait pas combien de pièces elle porte se compte à la main en
     l'ouvrant. Un manque se DIT — un zip silencieusement incomplet est pire
     que pas d'archive, parce qu'il a l'air complet. */
  function aoDossierComplet(fmt, bouton) {
    var libelle = bouton.textContent;
    bouton.disabled = true;
    bouton.textContent = "Composition du dossier…";
    var entete = null;
    demander("/api/datacenter/marche/dossier.zip", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fiche: AO_FICHE, analyse: AO_ANALYSE,
                             saisies: AO_SAISIES, format: fmt ,
                               perimetre: aoPerimetre() }),
    }, DELAI_LONG).then(function (r) {
      if (!r.ok) throw new Error("dossier");
      entete = r.headers.get("X-Dossier");
      return r.blob();
    }).then(function (b) {
      var u = URL.createObjectURL(b);
      var a = document.createElement("a");
      a.href = u;
      a.download = "dossier-reponse-consultation.zip";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
      var d = null;
      try { d = JSON.parse(entete || "null"); } catch (e) { d = null; }
      var m = $("#ig-ao-msg");
      if (m && d) {
        m.textContent = d.manques && d.manques.length
          ? d.pieces + " pièce(s) dans l'archive ; " + d.manques.length
            + " n'a pas pu être produite (" + d.manques.join(", ")
            + ") — le bordereau dit pourquoi."
          : d.pieces + " pièce(s) dans l'archive, aucune manquante.";
      }
    }).catch(function () {
      var m = $("#ig-ao-msg");
      if (m) m.textContent = "La composition du dossier a échoué.";
    }).then(function () {
      bouton.disabled = false;
      bouton.textContent = libelle;
    });
  }

  /* ── LE MENU DES PIÈCES À PRODUIRE ────────────────────────────────────
     POURQUOI UN MENU, ET PAS SEULEMENT DIX-NEUF CARTES À LA SUITE. Un
     dossier de candidature ne se prépare pas d'un seul tenant : l'administratif se
     rassemble — il existe déjà quelque part, ou il s'obtient d'un tiers — et
     le technique s'écrit. Ce ne sont ni les mêmes personnes, ni les mêmes
     délais. Empilées sans séparation, les dix-neuf pièces font commencer par
     les formulaires, qui sont courts et rassurants, et laissent pour la fin
     les notes techniques, qui départagent les candidats.

     LES DEUX GROUPES SONT DES `optgroup`, ET C'EST EXACTEMENT LEUR OFFICE :
     le navigateur les dessine lui-même, et la feuille partagée du site tient
     déjà leur contraste. Chaque entrée dit ce qu'il y a à FAIRE du document —
     le remplir ici, l'écrire, l'obtenir — et signale les bloquantes : sans
     cela, le menu proposerait dix-neuf documents d'égale urgence, ce qui
     revient à n'en signaler aucun. */
  /* LE CHOIX SURVIT AU REDESSIN, et sans cela le menu est inutilisable. Le
     bloc est redessiné à CHAQUE FRAPPE dans la fiche : la version précédente
     perdait la sélection à la première lettre tapée, et les dix-neuf cartes
     revenaient. Éprouvé dans un navigateur — on filtre sur « Références », on
     tape un caractère, et on se retrouve devant tout le dossier.

     LE CHOIX EST PASSÉ EN PARAMÈTRE plutôt que lu dans une variable globale :
     c'est ce qui permet d'exécuter cette fonction hors du navigateur pour
     l'éprouver. */
  var AO_DOC = "";

  function aoMenuDocs(r, choix) {
    var groupes = {};
    r.pieces.forEach(function (p) {
      (groupes[p.famille] = groupes[p.famille] || []).push(p);
    });
    var h = '<label class="ig-ao-menu"><span class="dc-lab">Aller à une pièce '
      + "du dossier</span>"
      + '<select id="ig-ao-doc"><option value="">Toutes les pièces ('
      + r.pieces.length + ")</option>";
    Object.keys(r.familles).forEach(function (f) {
      var liste = groupes[f] || [];
      if (!liste.length) return;
      h += '<optgroup label="' + esc(r.familles[f].nom) + " ("
        + liste.length + ')">';
      liste.forEach(function (p) {
        h += '<option value="' + esc(p.cle) + '"'
          + (choix === p.cle ? " selected" : "") + ">" + esc(p.nom)
          + " — " + esc(p.voie_nom.toLowerCase())
          + (p.bloquant ? " · bloquante" : "") + "</option>";
      });
      h += "</optgroup>";
    });
    h += "</select>";
    /* LA FAMILLE RETENUE DIT CE QU'ELLE ÉTABLIT ET QUI LA PRODUIT. Un menu
       qui range sans expliquer son rangement laisse deviner le critère. */
    h += '<span class="dc-aide" id="ig-ao-doc-aide"></span>'
      + '<span class="dc-aide">Choisir une pièce ici l\'ajoute au lot à '
      + "remplir, et y descend.</span></label>";
    return h;
  }

  /* Le filtre agit sur ce qui est DÉJÀ dessiné : il masque, il ne redessine
     pas. Redessiner ferait perdre les saisies en cours dans les champs propres
     à la consultation. */
  function aoBrancherMenu(r) {
    var sel = $("#ig-ao-doc");
    if (!sel) return;
    var aide = $("#ig-ao-doc-aide");
    var parCle = {};
    r.pieces.forEach(function (p) { parCle[p.cle] = p; });

    function appliquer(defiler) {
      var cle = AO_DOC;
      document.querySelectorAll("#ig-ao-rempli [data-doc]").forEach(function (c) {
        c.hidden = !!cle && c.dataset.doc !== cle;
      });
      if (!aide) return;
      if (!cle || !parCle[cle]) {
        aide.textContent = "";
        return;
      }
      var p = parCle[cle];
      var f = r.familles[p.famille];
      aide.textContent = f.nom + " — " + f.etablit + " " + f.qui
        + "  ·  " + p.voie_nom + " : " + p.voie_aide;
      if (!defiler) return;
      var carte = document.querySelector('#ig-ao-rempli [data-doc="' + cle + '"]');
      if (carte) carte.scrollIntoView({ block: "nearest" });
    }

    sel.addEventListener("change", function () {
      AO_DOC = sel.value;
      /* ELLE NAVIGUE ET ELLE CHOISIT. Le geste demandé est « au clic ou dans
         la liste » : une liste qui ne ferait que défiler obligerait à
         retrouver la carte pour la cliquer, c'est-à-dire à faire deux fois le
         même travail. Elle AJOUTE au choix — elle ne le remplace pas, sans
         quoi parcourir la liste effacerait ce qu'on vient de cocher. */
      if (AO_DOC) {
        AO_CHOISIES[AO_DOC] = true;
        aoLotRafraichirCarte(AO_DOC);
        aoLotCompter();
      }
      appliquer(true);
    });
    /* APPLIQUÉ AUSSI APRÈS LE REDESSIN, sans défiler : la page ne doit pas
       sauter sous les doigts de quelqu'un qui est en train de saisir. */
    appliquer(false);
  }

  var AO_ETAT_CLASSE = { rempli: "ok", a_saisir: "att", a_declarer: "dec",
                         non_trouve: "att", invalide: "mal" };

  /* ── CHOISIR PLUSIEURS PIÈCES, ET LES FAIRE PRODUIRE ENSEMBLE ─────────
     LES CHOIX SURVIVENT AU REDESSIN. Le bloc est redessiné à chaque frappe
     dans la fiche : garder la sélection dans le DOM la perdrait à la
     première lettre tapée, et l'on recommencerait à cliquer vingt-trois
     cartes. Elle vit donc ici, et le rendu la relit.

     CE QUI EST PRODUIT VIT ICI AUSSI, pour la même raison : une carte verte
     qui redeviendrait grise sous les doigts ferait relancer une production
     déjà faite. */
  var AO_CHOISIES = {};        /* clé -> true */
  /* CE QU'ON AFFIRME AVOIR FOURNI HORS OUTIL, EN MÉMOIRE SEULEMENT — et c'est
     un choix de sûreté, pas un oubli. Persisté dans le navigateur, un « fourni »
     posé pour une consultation reparaîtrait sur la suivante et affirmerait une
     pièce qu'on n'a pas : une fausse affirmation est pire qu'un blocage
     honnête. Il repart donc à chaque rechargement. */
  var AO_FOURNIES = {};        /* clé -> true (bloquantes non remplissables) */
  var AO_CHOIX_FAIT = false;   /* le choix d'office n'a lieu qu'une fois */
  var AO_PRODUIT = {};         /* clé -> {etat, texte, url, nom} */
  var AO_LOT_FMT = "docx";
  /* SIX À LA FOIS, ET PAS VINGT-TROIS. « Simultanément » veut dire que les
     productions se RECOUVRENT, pas qu'on ouvre vingt-trois connexions d'un
     coup : au-delà, le navigateur les met en file lui-même et le serveur
     répond plus lentement à chacune. Six se recouvrent franchement et
     laissent la page réactive. */
  var AO_LOT_FRONT = 6;

  /* ── LA BARRE DU LOT ──────────────────────────────────────────────────
     ELLE COMPTE AVANT DE PROPOSER. « Remplir les pièces choisies » sans le
     nombre laisse lancer vingt-trois productions en croyant en lancer une —
     et c'est le genre de clic qu'on ne retire pas. */
  /* CE QUE LA CARTE PRODUIRA, DIT AVANT LE CHOIX. Sans cela on coche
     vingt-trois pièces en croyant recevoir vingt-trois formulaires, et l'on
     découvre après coup que dix-neuf sont des plans à écrire. Le savoir AVANT
     change ce qu'on choisit ; le savoir après ne change rien.

     LA LISTE DES MODÈLES VIENT DU SERVEUR, qui vérifie l'empreinte du fichier
     déposé. Annoncer « formulaire officiel » sur un modèle absent ferait
     promettre ce que le remplissage refuserait ensuite. */
  function aoProduira(p) {
    var prets = (AO_FORMULAIRES && AO_FORMULAIRES.etat
                 && AO_FORMULAIRES.etat.prets) || [];
    var mod = (AO_FORMULAIRES && AO_FORMULAIRES.modeles) || {};
    var a = prets.filter(function (c) {
      return (mod[c] || {}).piece === p.cle;
    })[0];
    if (a) {
      return '<span class="ig-ao-pr off">formulaire officiel — se remplit</span>';
    }
    return '<span class="ig-ao-pr">'
      + (p.voie === "obtenir" ? "à demander — le document dit à qui"
         : p.voie === "remplir" ? "report de ses rubriques"
         : "plan de ce qu'elle doit démontrer") + "</span>";
  }

  function aoLotBarre(r) {
    var n = Object.keys(AO_CHOISIES).length;
    var faites = 0, mal = 0;
    Object.keys(AO_PRODUIT).forEach(function (k) {
      if (AO_PRODUIT[k].etat === "fait") faites++;
      else if (AO_PRODUIT[k].etat === "mal") mal++;
    });
    return '<div class="ig-ao-lot">'
      + "<b>Faire produire plusieurs pièces</b>"
      + '<span class="cpt">' + n + " choisie(s) sur " + r.pieces.length
      + (faites ? " · " + faites + " produite(s)" : "")
      + (mal ? " · " + mal + " en échec" : "") + "</span>"
      + '<button type="button" class="btn btn-s" data-lot="tout">Tout choisir</button>'
      + '<button type="button" class="btn btn-s" data-lot="rien">Rien</button>'
      + '<button type="button" class="btn btn-s" data-lot="bloquantes">'
      + "Les bloquantes</button>"
      + '<label class="pousse"><span class="cpt">Format&nbsp;</span>'
      + '<select data-lot-fmt aria-label="Format des pièces produites">'
      + '<option value="docx"' + (AO_LOT_FMT === "docx" ? " selected" : "")
      + ">Word</option>"
      + '<option value="pdf"' + (AO_LOT_FMT === "pdf" ? " selected" : "")
      + ">PDF</option>"
      + '<option value="xlsx"' + (AO_LOT_FMT === "xlsx" ? " selected" : "")
      + ">Excel</option></select></label>"
      + '<button type="button" class="btn btn-p" data-lot="go"'
      + (n ? "" : " disabled") + ">Remplir les " + n + " pièce(s) choisie(s)"
      + "</button>"
      + '<p class="cpt" style="flex:1 1 100%" data-lot-msg role="status" '
      + 'aria-live="polite">Choisissez au clic sur une carte, ou dans la '
      + "liste ci-dessus. Les pièces choisies se remplissent EN MÊME TEMPS ; "
      + "chacune passe au vert dès que la sienne est prête.</p>"
      + "</div>";
  }

  /* CE QUE LA CARTE DIT DE SA PROPRE PRODUCTION. Le contour donne l'état d'un
     coup d'œil ; ce bloc donne la raison — et le lien, parce qu'un document
     produit qu'on ne peut pas prendre n'a servi à rien. */
  function aoLotEtatCarte(p) {
    var x = AO_PRODUIT[p.cle];
    if (!x) return "";
    var h = '<p class="ig-ao-et">';
    if (x.etat === "cours") h += "Production en cours…";
    else if (x.etat === "mal") h += "<b>Échec</b> — " + esc(x.texte || "");
    else {
      h += "<b>" + esc(x.titre || "Produite") + "</b> — " + esc(x.texte || "");
      if (x.url) {
        h += ' <a href="' + x.url + '" download="' + esc(x.nom || "piece")
          + '">⬇ ' + esc(x.nom || "prendre") + "</a>";
      }
      h += "</p>" + aoCasesVides(x.cases);
      return h;
    }
    return h + "</p>";
  }

  /* CE QUE LE FORMULAIRE SAIT ÉCRIRE ET QU'ON NE LUI A PAS DONNÉ.
     TROIS MANQUES QUI NE SE CORRIGENT PAS PAREIL, DONC TROIS GROUPES. Une
     donnée d'identité se cherche UNE FOIS sur un Kbis ou un avis INSEE et
     sert à tous les dossiers à venir ; une valeur non relevée se lit à la
     main dans la pièce déposée ; une saisie se DÉCIDE pour cette
     consultation et ne se trouve nulle part. Les mêler enverrait chercher
     dans un Kbis un montant qui se décide. */
  var AO_MANQUE_GROUPES = [
    ["fiche", "À porter une fois au dossier d'entreprise — ces cases se "
              + "rempliront ensuite sur TOUS vos dossiers"],
    ["consultation", "Non relevé dans les pièces déposées — à lire à la main, "
                     + "puis à saisir"],
    ["calcul", "Se déduirait d'une valeur d'identité absente"],
    ["saisie", "À décider pour CETTE consultation"],
  ];

  function aoCasesVides(cases) {
    if (!cases || !cases.length) return "";
    var h = '<div class="ig-ao-cv"><b>' + cases.length
      + " case(s) de ce formulaire restent vides.</b>";
    AO_MANQUE_GROUPES.forEach(function (g) {
      var l = cases.filter(function (c) { return c.source === g[0]; });
      if (!l.length) return;
      h += '<p class="ig-ao-cvg">' + esc(g[1]) + "</p><ul>";
      l.forEach(function (c) {
        h += "<li><b>" + esc(c.libelle) + "</b>"
          + (c.ou_trouver ? " — " + esc(c.ou_trouver) : "") + "</li>";
      });
      h += "</ul>";
    });
    return h + "</div>";
  }

  function aoLotMsg(t) {
    var m = document.querySelector("[data-lot-msg]");
    if (m) m.textContent = t;
  }

  /* LE REDESSIN N'EST PAS INTÉGRAL PENDANT UN LOT. Redessiner tout le bloc à
     chaque réponse ferait perdre les saisies en cours et ferait sauter la
     page sous les doigts. On ne touche donc qu'à LA carte concernée. */
  function aoLotRafraichirCarte(cle) {
    var c = document.querySelector('#ig-ao-rempli [data-doc="' + cle + '"]');
    if (!c) return;
    ["sel", "cours", "fait", "mal"].forEach(function (e) {
      c.classList.remove("ig-ao-cp-" + e);
    });
    if (AO_CHOISIES[cle]) c.classList.add("ig-ao-cp-sel");
    var x = AO_PRODUIT[cle];
    if (x) c.classList.add("ig-ao-cp-" + x.etat);
    c.setAttribute("aria-pressed", AO_CHOISIES[cle] ? "true" : "false");
    var vieux = c.querySelector(".ig-ao-et");
    if (vieux) vieux.remove();
    var h = aoLotEtatCarte({ cle: cle });
    if (h) c.insertAdjacentHTML("beforeend", h);
  }

  /* TOUT CHOISIR, une fois l'analyse revenue. Écrit à part pour être appelable
     ailleurs — et pour qu'une règle puisse l'exécuter sans rejouer l'analyse. */
  function aoToutChoisir() {
    var r = (AO_REMPLI && AO_REMPLI.pieces) || [];
    if (!r.length) return 0;
    r.forEach(function (p) { AO_CHOISIES[p.cle] = true; });
    r.forEach(function (p) { aoLotRafraichirCarte(p.cle); });
    aoLotCompter();
    return r.length;
  }

  function aoLotCompter() {
    var b = document.querySelector('[data-lot="go"]');
    var n = Object.keys(AO_CHOISIES).length;
    if (b) {
      b.disabled = !n;
      b.textContent = "Remplir les " + n + " pièce(s) choisie(s)";
    }
    var c = document.querySelector(".ig-ao-lot .cpt");
    if (c && AO_DERNIER) {
      var faites = 0, mal = 0;
      Object.keys(AO_PRODUIT).forEach(function (k) {
        if (AO_PRODUIT[k].etat === "fait") faites++;
        else if (AO_PRODUIT[k].etat === "mal") mal++;
      });
      c.textContent = n + " choisie(s) sur " + AO_DERNIER.pieces.length
        + (faites ? " · " + faites + " produite(s)" : "")
        + (mal ? " · " + mal + " en échec" : "");
    }
  }

  function aoLotBasculer(cle) {
    if (AO_CHOISIES[cle]) delete AO_CHOISIES[cle];
    else AO_CHOISIES[cle] = true;
    aoLotRafraichirCarte(cle);
    aoLotCompter();
  }

  function aoBrancherLot(r, z) {
    AO_DERNIER = r;
    z.querySelectorAll("#ig-ao-rempli [data-doc], .ig-ao-cd [data-doc]")
      .forEach(function (c) {
        var cle = c.dataset.doc;
        c.addEventListener("click", function (ev) {
          /* UN CLIC DANS UN CHAMP OU SUR UN LIEN N'EST PAS UN CHOIX. Sans
             cette réserve, saisir une valeur dans une carte la
             sélectionnerait, et prendre le document la désélectionnerait. */
          var t = ev.target;
          if (t.closest("input, textarea, select, a, button")) return;
          aoLotBasculer(cle);
        });
        c.addEventListener("keydown", function (ev) {
          if (ev.key !== "Enter" && ev.key !== " ") return;
          if (ev.target !== c) return;
          ev.preventDefault();
          aoLotBasculer(cle);
        });
      });
    z.querySelectorAll("[data-lot]").forEach(function (b) {
      b.addEventListener("click", function () {
        var q = b.dataset.lot;
        if (q === "tout") {
          r.pieces.forEach(function (p) { AO_CHOISIES[p.cle] = true; });
        } else if (q === "rien") {
          AO_CHOISIES = {};
        } else if (q === "bloquantes") {
          AO_CHOISIES = {};
          r.pieces.forEach(function (p) {
            if (p.bloquant) AO_CHOISIES[p.cle] = true;
          });
        } else if (q === "go") {
          aoLotRemplir(r);
          return;
        }
        r.pieces.forEach(function (p) { aoLotRafraichirCarte(p.cle); });
        aoLotCompter();
      });
    });
    var f = z.querySelector("[data-lot-fmt]");
    if (f) {
      f.addEventListener("change", function () { AO_LOT_FMT = f.value; });
    }
  }

  /* ── LE REMPLISSAGE SIMULTANÉ ─────────────────────────────────────────
     TOUTES LES CARTES PASSENT EN « EN COURS » D'UN COUP, puis chacune bascule
     pour SON PROPRE COMPTE dès que sa réponse arrive. C'est ce qui distingue
     un lot d'une file : on voit le dossier se remplir, on ne regarde pas une
     barre avancer.

     LE DOCUMENT RESTE DANS LA PAGE, il ne se télécharge pas tout seul. Vingt
     et un téléchargements simultanés sont bloqués par le navigateur, et celui
     qui les autorise noie le dossier de l'utilisateur. Chaque carte porte son
     lien ; « Tout le dossier (.zip) » reste là pour tout prendre d'un coup. */
  function aoLotRemplir(r) {
    var cles = r.pieces.map(function (p) { return p.cle; })
      .filter(function (c) { return AO_CHOISIES[c]; });
    if (!cles.length) return;
    var t0 = (window.performance && performance.now) ? performance.now() : 0;
    cles.forEach(function (c) {
      /* L'URL précédente est révoquée : garder vingt-trois objets vivants à
         chaque relance fait grossir la page sans qu'on le voie. */
      var v = AO_PRODUIT[c];
      if (v && v.url) { try { URL.revokeObjectURL(v.url); } catch (e) {} }
      AO_PRODUIT[c] = { etat: "cours" };
      aoLotRafraichirCarte(c);
    });
    aoLotCompter();
    aoLotMsg(cles.length + " pièce(s) lancées ensemble…");

    var i = 0, finies = 0;
    function suivante() {
      if (i >= cles.length) return Promise.resolve();
      var cle = cles[i++];
      return aoLotUne(cle).then(function () {
        finies++;
        aoLotRafraichirCarte(cle);
        aoLotCompter();
        aoLotMsg(finies + " / " + cles.length + " produite(s)…");
        return suivante();
      });
    }
    var front = [];
    for (var k = 0; k < Math.min(AO_LOT_FRONT, cles.length); k++) {
      front.push(suivante());
    }
    Promise.all(front).then(function () {
      var ms = t0 ? Math.round(performance.now() - t0) : 0;
      var mal = cles.filter(function (c) {
        return (AO_PRODUIT[c] || {}).etat === "mal";
      });
      aoLotMsg(cles.length + " pièce(s) produites"
        + (ms ? " en " + (ms / 1000).toFixed(1) + " s" : "")
        + (mal.length ? " · " + mal.length
           + " en échec, la carte dit pourquoi" : "")
        + ". Chaque carte porte son document ; « Tout le dossier (.zip) » les "
        + "prend tous.");
    });
  }

  function aoLotUne(cle) {
    var entete = null;
    return demander("/api/datacenter/marche/piece", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ piece: cle, fiche: AO_FICHE, analyse: AO_ANALYSE,
                             saisies: AO_SAISIES, format: AO_LOT_FMT }),
    }, DELAI_MOYEN).then(function (x) {
      if (!x.ok) {
        return x.json().then(function (j) {
          throw new Error((j && j.message) || "production refusée");
        }, function () { throw new Error("production refusée"); });
      }
      entete = x.headers.get("X-Piece");
      var cd = x.headers.get("Content-Disposition") || "";
      var m = /filename="?([^";]+)"?/.exec(cd);
      return x.blob().then(function (b) { return [b, m ? m[1] : cle]; });
    }).then(function (bn) {
      var d = null;
      try { d = JSON.parse(entete || "null"); } catch (e) { d = null; }
      var reste = (d && (d.reste || d.non_places)) || [];
      /* CE QU'ON DÉTIENT ET QUE LE FORMULAIRE N'OFFRE PAS D'ÉCRIRE. « 2
         valeur(s) portée(s) » sur un DC1 qui en tient cinq se lit comme un
         formulaire aussi rempli qu'il peut l'être. Les trois autres sont
         justes et sans case : à recopier, donc à dire ICI, sur la carte. */
      var main = (d && d.sans_ancre) || [];
      AO_PRODUIT[cle] = {
        etat: "fait",
        titre: (d && d.production_nom) || "Produite",
        texte: (d ? d.places + " valeur(s) portée(s)" : "document produit")
          + (main.length ? " · à recopier à la main : " + main.join(", ") : "")
          + (reste.length ? " · reste " + reste.slice(0, 3).join(", ")
             + (reste.length > 3 ? "…" : "") : ""),
        /* LES CASES OUVERTES ET VIDES, GARDÉES POUR ÊTRE MONTRÉES. Un DC2
           sortait avec sept valeurs portées et six cases vides — SIRET, RCS,
           NAF, les trois chiffres d'affaires — sans un mot. « 7 valeur(s)
           portée(s) » se lit comme « aussi rempli qu'il peut l'être ». */
        cases: (d && d.cases_vides) || [],
        url: URL.createObjectURL(bn[0]),
        nom: bn[1],
      };
    }).catch(function (e) {
      AO_PRODUIT[cle] = { etat: "mal", texte: e.message || "échec" };
    });
  }

  var AO_DERNIER = null;

  function aoRempliRendre(r) {
    var z = $("#ig-ao-rempli");
    if (!z) return;
    var e = r.etat;
    var h = '<h3 class="ig-tr-st">Les pièces des deux dossiers, remplies de '
      + "ce qui est déjà écrit ailleurs</h3>"
      /* CE QUE CE BLOC EST, ET CE QU'IL N'EST PAS. Il ne produit aucun
         formulaire : les DC1, DC2, DC4 et ATTRI1 ont leur version, leur
         format et leurs cases, et un fac-similé serait refusé — ou pire,
         accepté et faux. Ce report se pose À CÔTÉ d'eux, chaque valeur avec
         son origine, pour être recopié en le vérifiant. */
      + '<p class="ig-ao-cq">Les quatre formulaires de l\'État — DC1, DC2, '
      + "DC4, ATTRI1 — redemandent les mêmes informations. Ce report les "
      + "rassemble avec, pour chacune, D'OÙ ELLE VIENT.</p>";
    if (r.sans_dossier) {
      h += '<p class="ig-ao-a ig-ao-a-attention">Aucun dossier de consultation '
        + "n\'a encore été analysé : les rubriques qui viennent des pièces de "
        + "l\'acheteur — l\'acheteur lui-même, l\'objet, la référence, les lots "
        + "— restent vides. Déposez-les ci-dessus et elles se rempliront.</p>";
    }
    h += '<div class="ig-ao-bar">'
      + '<span class="ig-ao-cpt ok">' + e.remplies + " remplies</span>"
      + '<span class="ig-ao-cpt att">' + (e.a_saisir + e.non_trouvees)
      + " à compléter</span>"
      + '<span class="ig-ao-cpt dec">' + e.a_declarer + " à déclarer</span>"
      + (e.invalides ? '<span class="ig-ao-cpt mal">' + e.invalides
         + " à corriger</span>" : "")
      /* LE DÉCOMPTE PORTE SUR CE QUI EST MESURABLE, et il le dit. « 1 / 14 »
         laisserait croire que treize pièces manquent alors que neuf ne se
         remplissent pas ici — elles s'écrivent ou s'obtiennent. */
      + '<span class="ig-ao-cpt">' + e.pieces_completes + " / " + e.mesurables
      + " pièces remplissables sans manque</span>"
      + (e.pieces_a_signer ? '<span class="ig-ao-cpt dec">'
         + e.pieces_a_signer + " n'attendent plus qu'une signature</span>" : "")
      + '<span class="ig-ao-cpt">' + (e.pieces - e.mesurables)
      + " à écrire ou à obtenir</span>"
      + "</div>";
    if (e.bloquantes_incompletes.length) {
      h += '<p class="ig-ao-a ig-ao-a-bloquante">Pièces bloquantes encore '
        + "incomplètes : " + esc(e.bloquantes_incompletes.join(", ")) + ".</p>";
    }
    /* CE QUE CE MODULE NE SAIT PAS FAIRE ET QUI REND LA CANDIDATURE
       IRRECEVABLE. Les taire parce qu'il ne sait pas les produire serait la
       pire des omissions : ce sont elles qui ont un délai. */
    if ((e.bloquantes_a_produire || []).length) {
      h += '<p class="ig-ao-a ig-ao-a-bloquante">Bloquantes que ce cadre ne '
        + "remplit pas — "
        + e.bloquantes_a_produire.map(function (x) {
            return esc(x.nom) + " (" + esc(x.voie_nom.toLowerCase())
              + (x.delai ? ", " + esc(x.delai) : "") + ")";
          }).join(" · ") + ".</p>";
    }
    /* CE QUE VOUS AFFIRMEZ TENIR, DIT À PART. Une bloquante affirmée fournie a
       quitté la liste ci-dessus ; la répéter ici — comme « affirmée, non
       vérifiée » — évite qu'un relecteur la croie constatée par l'outil. */
    if ((e.bloquantes_fournies || []).length) {
      h += '<p class="ig-ao-a ig-ao-a-fournie">Bloquantes affirmées fournies '
        + "hors outil — " + e.bloquantes_fournies.map(esc).join(" · ")
        + ". <b>Votre affirmation, non vérifiée par l'outil.</b></p>";
    }
    h += aoMenuDocs(r, AO_DOC);
    h += aoLotBarre(r);
    h += '<div class="ig-ao-cd">';
    r.pieces.forEach(function (p) {
      var prod = AO_PRODUIT[p.cle];
      h += '<div class="ig-ao-cp' + (p.bloquant ? " ig-ao-cpb" : "")
        + (p.complet ? " ig-ao-cp-ok" : "")
        + (p.fournie ? " ig-ao-cp-fournie" : "")
        + (AO_CHOISIES[p.cle] ? " ig-ao-cp-sel" : "")
        + (prod ? " ig-ao-cp-" + prod.etat : "")
        + '" data-doc="' + esc(p.cle)
        /* LA CARTE EST UN INTERRUPTEUR, et elle le dit à qui ne la voit pas.
           Un `div` cliquable sans rôle ni état n'existe pas pour un lecteur
           d'écran : on choisirait à la souris et jamais au clavier. */
        + '" role="button" tabindex="0" aria-pressed="'
        + (AO_CHOISIES[p.cle] ? "true" : "false")
        + '" data-fam="' + esc(p.famille) + '">'
        /* LA FAMILLE D'INFOBULLES SUIT LE DOSSIER. Le glossaire tient
           `piece_candidature` et `piece_offre` séparés : demander la mauvaise
           n'affiche rien, et n'affiche rien SANS ERREUR. La clé vient donc du
           module, elle ne se devine pas ici. */
        + '<div class="ig-ao-cph"><b' + info(p.glossaire + ":" + p.cle) + ">"
        + esc(p.nom) + "</b>"
        + '<span class="ig-ao-cn">' + esc(p.nature_nom) + "</span>"
        + (p.bloquant ? '<span class="ig-ao-bl">bloquante</span>' : "")
        + '<span class="ig-ao-vo ig-ao-vo-' + esc(p.voie) + '">'
        + esc(p.voie_nom) + "</span>"
        + aoProduira(p)
        + "</div>";
      /* UNE PIÈCE SANS OBJET LE DIT, ET DIT POURQUOI. Muette, elle
         ressemblerait à une pièce oubliée — et ses vingt-trois rubriques
         vides, à autant de manques. */
      if (p.sans_objet) {
        h += '<p class="ig-ao-a ig-ao-a-attention">Sans objet — '
          + esc(p.sans_objet_aide) + "</p>";
      }
      /* UNE PIÈCE QUE CE MODULE NE REMPLIT PAS DOIT QUAND MÊME DIRE CE QU'ELLE
         CONTIENT. Sans cela, le menu la nommerait et le lecteur ne trouverait
         rien derrière — ce qui est pire que de ne pas l'avoir nommée. */
      if (!p.mesurable) {
        h += '<p class="ig-ao-cq"><i>' + esc(p.voie_nom) + "</i> — "
          + esc(p.voie_aide) + "</p>"
          + '<p class="ig-ao-cq"><i>Produite par</i> — ' + esc(p.produit_par)
          + '</p><ul class="ig-ao-cc">';
        (p.contient || []).forEach(function (c) {
          h += "<li>" + esc(c) + "</li>";
        });
        h += "</ul>";
        if (p.delai) {
          h += '<p class="ig-ao-dl"><b>Délai d\'obtention</b> — '
            + esc(p.delai) + "</p>";
        }
        /* LE GESTE « JE L'AI FOURNIE », SUR LES SEULES PIÈCES QUE CE MODULE NE
           REMPLIT PAS. Il ne coche rien à votre place : c'est VOUS qui affirmez
           avoir obtenu ou écrit la pièce hors de l'outil, et la carte le dit —
           « affirmé par vous, non vérifié ». Réservé aux bloquantes : ce sont
           les seules dont l'affirmation lève un blocage. */
        if (p.bloquant) {
          h += '<div class="ig-ao-fo' + (p.fournie ? " ig-ao-fo-on" : "") + '">';
          if (p.fournie) {
            h += '<span class="ig-ao-fo-m">✓ Fournie — <b>affirmé par vous</b>,'
              + " non vérifié par l'outil.</span>"
              + '<button type="button" class="btn btn-s" data-fournie="'
              + esc(p.cle) + '" data-on="1">Annuler</button>';
          } else {
            h += '<span class="ig-ao-fo-q">Elle ne se remplit pas ici. Une fois '
              + "obtenue ou écrite hors de l'outil, marquez-la pour qu'elle "
              + "sorte des blocages.</span>"
              + '<button type="button" class="btn btn-s" data-fournie="'
              + esc(p.cle) + '">J\'ai fourni cette pièce</button>';
          }
          h += "</div>";
        }
      }
      h += '<dl class="ig-ao-rb">';
      p.rubriques.forEach(function (l) {
        var cl = AO_ETAT_CLASSE[l.statut] || "att";
        h += '<dt class="' + cl + '">' + esc(l.libelle)
          + '<span class="ig-ao-st ' + cl + '">' + esc(l.statut_nom)
          + "</span></dt><dd>";
        if (l.source === "saisie") {
          h += '<input type="text" class="ig-ao-si" data-saisie="'
            + esc(p.cle + "." + l.cle) + '" value="' + esc(l.valeur || "")
            + '" placeholder="à saisir pour cette consultation">';
        } else if (l.valeur) {
          h += '<span class="ig-ao-vv">' + esc(l.valeur) + "</span>";
        }
        if (l.origine) {
          /* UNE VALEUR TIRÉE D'UN FICHIER NON IDENTIFIÉ NE SE LIT PAS COMME
             LES AUTRES. L'origine est un texte de 10,5 px en gris : sur une
             ligne marquée « Rempli », personne ne la lira avant de signer.
             La classe la sort du gris. */
          h += '<span class="ig-ao-og'
            + (l.a_confirmer ? " ig-ao-og-conf" : "") + '">'
            + esc(l.origine) + "</span>";
        }
        if (l.citation) {
          h += '<blockquote class="ig-ao-c">' + esc(l.citation.texte)
            + "<cite>" + esc(l.citation.fichier) + "</cite></blockquote>";
        }
        (l.divergences || []).forEach(function (d) {
          h += '<p class="ig-ao-div"><b>' + esc(d.sigle || d.fichier)
            + "</b> dit : " + esc(d.valeur) + "</p>";
        });
        if (l.texte) {
          /* CE QU'ELLE ENGAGE EST DIT AVEC ELLE. Une déclaration d'absence
             d'interdiction de soumissionner est un délit si elle est fausse ;
             l'engagement d'un acte d'engagement n'affirme aucun fait et lie
             au prix, à la durée et aux pièces visées par renvoi. Servir le
             même avertissement sur les deux dirait une chose fausse. */
          h += '<blockquote class="ig-ao-dec">'
            + '<span class="ig-ao-cn">' + esc(l.engage_nom) + "</span>"
            + esc(l.texte) + "</blockquote>";
        }
        if (l.message) h += '<p class="ig-ao-w">' + esc(l.message) + "</p>";
        if (l.aide) h += '<p class="ig-ao-w">' + esc(l.aide) + "</p>";
        h += "</dd>";
      });
      h += "</dl>"
        + '<p class="ig-ao-pg"><i>Le piège</i> — ' + esc(p.piege) + "</p>"
        + aoLotEtatCarte(p) + "</div>";
    });
    h += "</div>"
      + '<div class="actions" style="margin-top:14px;gap:10px;flex-wrap:wrap">'
      + '<button type="button" class="btn btn-s" data-ao-exp="docx">'
      + "Emporter le dossier préparé (Word)</button>"
      + '<button type="button" class="btn btn-s" data-ao-exp="pdf">'
      + "PDF</button>"
      + '<button type="button" class="btn btn-s" data-ao-exp="xlsx">'
      + "Excel</button>"
      /* TOUT LE DOSSIER EN UN GESTE. Répondre à une consultation demandait
         cinq téléchargements — le report, puis les quatre formulaires — et
         autant d'occasions d'en oublier un. Le choix de format ne porte que
         sur le REPORT : les formulaires officiels restent en Word, parce que
         ce qui sort est le fichier du ministère et qu'un fac-similé serait
         refusé. L'archive le dit dans son bordereau. */
      + '<label class="ig-ao-zip"><span>Tout le dossier&nbsp;:</span>'
      + '<select data-ao-zip-fmt aria-label="Format du report dans l\'archive">'
      + '<option value="docx">Word</option>'
      + '<option value="pdf">PDF</option>'
      + '<option value="xlsx">Excel</option></select>'
      + '<button type="button" class="btn btn-s" data-ao-zip>'
      + "⬇ Tout le dossier (.zip)</button></label>"
      + aoFormulairesBoutons() + "</div>"
      + '<p class="ig-icpe-res">' + esc(r.note) + "</p>";
    z.innerHTML = h;
    aoBrancherMenu(r);
    aoBrancherLot(r, z);
    z.querySelectorAll("[data-ao-exp]").forEach(function (b) {
      b.addEventListener("click", function () { aoExporter(b.dataset.aoExp, b); });
    });
    z.querySelectorAll("[data-ao-zip]").forEach(function (b) {
      b.addEventListener("click", function () {
        var sel = z.querySelector("[data-ao-zip-fmt]");
        aoDossierComplet(sel ? sel.value : "docx", b);
      });
    });
    z.querySelectorAll("[data-ao-form]").forEach(function (b) {
      b.addEventListener("click", function () {
        aoFormulaireRemplir(b.dataset.aoForm, b);
      });
    });
    z.querySelectorAll("[data-saisie]").forEach(function (i) {
      i.addEventListener("input", function () {
        AO_SAISIES[i.dataset.saisie] = i.value;
        aoFicheEnregistrer();
        aoRemplir();
      });
    });
  }


  /* ── LE PROJET : CONSERVER LE DOSSIER, ET ASSUMER LES DÉCLARATIONS ─────
     RATTACHER UN PROJET EST UNE DÉCISION, PAS UN RÉGLAGE. Tant qu'aucun
     projet n'est choisi, la fiche vit dans ce navigateur et les pièces
     repartent avec la réponse : rien n'est conservé. Rattacher change cela,
     et le bloc dit quoi AVANT de le proposer — durée, chiffrement,
     effacement. Un service qui se met à conserver sans le dire est le défaut
     qu'on veut éviter, pas une commodité.

     ASSUMER UNE DÉCLARATION N'ÉCRIT RIEN DANS LE FORMULAIRE. Ce qui se
     conserve est QUI a affirmé QUOI, sur quel texte, avec quelles preuves
     valides ce jour-là. Les six cases restent vides — le document produit est
     identique, octet pour octet, avant et après. L'écran le répète parce
     qu'un lecteur attend naturellement l'inverse. */
  var AO_PROJET = null;         /* l'identifiant rattaché, ou null */
  var AO_PROJET_ETAT = null;    /* la dernière réponse du serveur */
  var AO_PROJETS = null;        /* la liste des projets du compte */

  function aoProjetCharger() {
    try { AO_PROJET = localStorage.getItem("ao-projet-v1") || null; }
    catch (e) { AO_PROJET = null; }
  }
  function aoProjetRetenir(id) {
    AO_PROJET = id || null;
    try {
      if (id) localStorage.setItem("ao-projet-v1", id);
      else localStorage.removeItem("ao-projet-v1");
    } catch (e) { /* stockage refusé : le choix vaut pour cette visite */ }
  }

  function aoProjetMsg(t) {
    var m = $("#ig-cons-msg");
    if (m) m.textContent = t || "";
  }

  /* L'ÉTAT VIENT DU SERVEUR, JAMAIS D'UNE MÉMOIRE LOCALE. Les preuves
     périment et les textes changent : un état gardé ici vieillirait en
     silence, et l'écran annoncerait « prouvée » pour une attestation expirée
     la semaine dernière. */
  function aoProjetEtat() {
    if (!AO_PROJET) { aoProjetRendre(); return Promise.resolve(null); }
    return demander("/api/datacenter/marche/projet/dossier?projet="
                    + encodeURIComponent(AO_PROJET),
                    { credentials: "same-origin" })
      .then(function (r) { return r.json().then(function (j) { return [r.status, j]; }); })
      .then(function (xj) {
        if (xj[0] === 404) {          /* projet effacé ailleurs : on se détache */
          aoProjetRetenir(null);
          AO_PROJET_ETAT = null;
          aoProjetMsg("Ce projet n'existe plus. Le dossier n'est plus rattaché.");
        } else if (xj[1] && xj[1].ok) {
          AO_PROJET_ETAT = xj[1];
          /* LE COFFRE COMBLE, IL N'ÉCRASE PAS — et c'est posé ici, pas dans
             `aoProjetReprendre`, qui sort tôt dès qu'une analyse est en cours.
             Le texte conservé serait alors resté inaccessible précisément
             dans le cas le plus courant : on analyse, puis on regarde le
             projet. */
          aoTextesPoser(aoTextesDuCoffre(xj[1].dossier), false);
          aoProjetReprendre();
        }
        aoProjetRendre();
        return AO_PROJET_ETAT;
      })
      .catch(function () { aoProjetRendre(); return null; });
  }

  /* ── LE DOSSIER CONSERVÉ REPREND LA MAIN ──────────────────────────────
     CE QUI SE PASSAIT SANS CELA. Le dossier de consultation était déposé,
     analysé, conservé chiffré — et à la visite suivante l'écran repartait
     vide. On avait un dossier en base et rien sous les yeux : il fallait tout
     redéposer pour retrouver ce qu'on avait déjà.

     L'ANALYSE N'EST PAS REFAITE ICI. Elle a été relevée AU DÉPÔT, avec la
     version du releveur, et conservée telle quelle : la refaire ferait varier
     le résultat quand les motifs évoluent, et deux lectures du même dossier ne
     diraient plus la même chose.

     ON NE PIÉTINE JAMAIS UNE SAISIE EN COURS. La fiche locale, si elle porte
     déjà quelque chose, l'emporte sur celle du coffre — c'est la plus
     récente, et l'écraser ferait disparaître sous les doigts ce qu'on vient
     de taper. */
  /* CE QUE L'ÉCRAN DIT DE LA REPRISE — écrit à part pour être MESURABLE.
     La date passait par `String(ms).slice(0, 10)`, qui rend les dix premiers
     chiffres de l'horodatage : « relevées le 1788728142 », mesuré à l'écran.
     Elle passe désormais par `aoJour`, comme partout ailleurs. Sortir la
     phrase de la fonction qui touche le DOM permet à une règle de l'exécuter
     sur un horodatage connu, au lieu de constater qu'un mot y figure. */
  function aoRepriseMsg(d) {
    return "Dossier conservé repris : "
      + ((d.analyse && d.analyse.pieces) || []).length
      + " pièce(s) identifiée(s), relevées le "
      + aoJour(d.maj_le || d.cree_le) + ". Rien n'a été redéposé.";
  }

  function aoProjetReprendre() {
    var d = (AO_PROJET_ETAT || {}).dossier;
    if (!d || AO_ANALYSE) return;
    if (!d.analyse || !(d.analyse.pieces || []).length) return;
    AO_ANALYSE = d.analyse;
    AO_DOCS = (d.pieces || []).map(function (x) {
      return { nom: x.nom, texte: "" };   /* le texte reste au coffre */
    });
    if (d.fiche && !Object.keys(AO_FICHE || {}).length) AO_FICHE = d.fiche;
    aoRendre(AO_ANALYSE);
    /* L'ORDRE COMPTE : `aoCandidature` VIDE la ligne de message en entrant.
       Annoncer la reprise avant elle l'aurait effacée avant d'être lue. */
    aoCandidature();
    var msg = $("#ig-ao-msg");
    if (msg) msg.textContent = aoRepriseMsg(d);
  }

  /* Le texte des pièces du coffre, par nom de fichier. Écrit à part pour
     qu'une règle puisse l'exécuter sur un dossier connu : `aoProjetEtat` ne
     s'éprouve qu'avec une requête. */
  function aoTextesDuCoffre(d) {
    var out = {};
    ((d || {}).pieces || []).forEach(function (p) {
      if (p && p.nom && typeof p.texte === "string" && p.texte) {
        out[p.nom] = p.texte;
      }
    });
    return out;
  }

  function aoProjetsCharger() {
    return demander("/api/datacenter/projets", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) { AO_PROJETS = (j && j.ok) ? (j.projets || []) : []; })
      .catch(function () { AO_PROJETS = []; });
  }

  /* LES TAILLES PASSENT PAR `fr`, COMME TOUS LES NOMBRES DE CE SITE. Un
     `toFixed(1)` rendait « 5.0 Mo » — le point décimal anglais, au milieu
     d'une page où tout le reste porte la virgule. Le formateur commun décide
     du barème une seule fois, et un entier y reste un entier : « 799 Ko »,
     pas « 799,0 Ko ». */
  function aoOctets(n) {
    n = Number(n) || 0;
    return n < 1024 ? fr(n) + " o"
      : n < 1048576 ? fr(n / 1024) + " Ko"
      : fr(n / 1048576) + " Mo";
  }
  function aoJour(ms) {
    if (!ms) return "—";
    var d = new Date(Number(ms));
    return isNaN(d.getTime()) ? "—" : d.toLocaleDateString("fr-FR");
  }

  /* ── LE BLOC « PAS ENCORE RATTACHÉ » ─────────────────────────────────── */
  function aoProjetInvite() {
    var h = '<div class="ig-cons"><h4>Conserver ce dossier dans un projet</h4>'
      + "<p>Pour l'instant, <b>rien n'est conservé</b>&nbsp;: la fiche reste "
      + "dans ce navigateur et les pièces repartent avec la réponse. Les "
      + "redéposer et les retaper à chaque session est le prix de ce choix.</p>"
      + '<div class="ig-cons-av">Rattacher un projet <b>change cela</b>&nbsp;: '
      + "le texte des pièces, les relevés et la fiche sont conservés "
      + "<b>chiffrés</b>, pendant <b>12 mois à compter de la dernière "
      + "activité</b>, et vous pouvez les effacer à tout moment. Ils restent "
      + "visibles de vous et des collègues invités sur CE projet.</div>";
    if (!AO_DOCS || !AO_DOCS.length) {
      h += "<p>Analysez d'abord un dossier de consultation&nbsp;: c'est ce "
        + "qui sera conservé.</p></div>";
      return h;
    }
    if (!AO_PROJETS || !AO_PROJETS.length) {
      h += "<p>Aucun projet n'est ouvert sur ce compte. Créez-en un depuis "
        + "vos projets, puis revenez ici.</p></div>";
      return h;
    }
    h += '<div class="ig-cons-f"><select id="ig-cons-sel">';
    AO_PROJETS.forEach(function (p) {
      h += '<option value="' + esc(p.id) + '">' + esc(p.nom)
        + (p.client ? " — " + esc(p.client) : "") + "</option>";
    });
    h += "</select>"
      + '<button type="button" class="btn btn-s" id="ig-cons-go">'
      + "Conserver dans ce projet</button></div>"
      + '<p class="note" id="ig-cons-msg" style="margin-top:9px"></p></div>';
    return h;
  }

  /* ── LES SIX DÉCLARATIONS ────────────────────────────────────────────── */
  function aoDeclaration(l, textes) {
    var t = textes[l.cle] || {};
    var h = '<div class="ig-cons-d"><b>' + esc(l.libelle) + "</b>"
      + '<span class="ig-cons-nat'
      + (l.engage === "penal" ? " ig-cons-nat-penal" : "") + '">'
      + esc(l.engage_nom) + "</span>"
      + '<p class="ig-cons-txt">' + esc(t.texte || "") + "</p>";

    if (l.couverture === "prouvee") {
      h += '<p class="ig-cons-pr"><b>Preuves à jour.</b> ' + esc(l.message) + "</p>";
    } else if (l.couverture === "sans_preuve_interne") {
      h += '<p class="ig-cons-pr"><b>Aucune preuve interne ne la soutient.</b> '
        + esc(l.motif_sans_preuve) + "</p>";
    } else {
      h += '<p class="ig-cons-pr"><b>Preuve incomplète.</b> Il manque&nbsp;: '
        + (l.manquantes || []).map(function (m) {
            return esc(m.nom) + " (" + esc(m.etat) + ")";
          }).join(", ") + ".</p>";
    }

    if (l.affirmee) {
      h += '<p class="ig-cons-ok">Assumée par <b>' + esc(l.par || "—")
        + "</b> le " + esc(aoJour(l.le)) + ".</p>";
      (l.a_revoir || []).forEach(function (r) {
        h += '<p class="ig-cons-rev">À revoir&nbsp;: '
          + (r === "texte_modifie"
             ? "le texte de la pièce a changé depuis. Ce qui a été assumé "
               + "n'est plus la rédaction du formulaire."
             : "la preuve qui la soutenait a expiré. L'affirmation reste vraie "
               + "de son jour&nbsp;; elle ne dit plus rien d'aujourd'hui.")
          + "</p>";
      });
    }
    if (l.couverture === "incomplete") {
      h += '<p class="ig-cons-pr">Obtenez la pièce manquante avant d\'assumer '
        + "cette déclaration. Elle ne peut pas l'être sans.</p></div>";
      return h;
    }
    h += '<div class="ig-cons-f">'
      + '<input type="text" data-cons-nom="' + esc(l.cle)
      + '" placeholder="Nom de qui assume" maxlength="200">'
      + '<label><input type="checkbox" data-cons-lu="' + esc(l.cle) + '">'
      + "J'ai lu le texte ci-dessus et je l'assume.</label>";
    if (l.couverture === "sans_preuve_interne") {
      h += '<label><input type="checkbox" data-cons-rec="' + esc(l.cle) + '">'
        + "Je reconnais qu'aucune attestation de l'entreprise ne soutient "
        + "cette déclaration.</label>";
    }
    h += '<button type="button" class="btn btn-s" data-cons-aff="' + esc(l.cle)
      + '">' + (l.affirmee ? "Assumer à nouveau" : "Assumer") + "</button>"
      + "</div></div>";
    return h;
  }

  function aoProjetRendre() {
    var z = $("#ig-ao-projet");
    if (!z) return;
    if (!AO_PROJET || !AO_PROJET_ETAT) { z.innerHTML = aoProjetInvite(); }
    else {
      var d = AO_PROJET_ETAT.dossier;
      var dec = AO_PROJET_ETAT.declarations || { lignes: [] };
      var textes = {};
      (AO_PROJET_ETAT.textes || []).forEach(function (t) { textes[t.cle] = t; });
      var h = '<div class="ig-cons"><h4>Dossier conservé</h4>';
      if (!d) {
        h += "<p>Ce projet ne porte encore aucune pièce. Analysez un dossier "
          + "de consultation, puis conservez-le ici.</p>";
      } else {
        h += "<p><b>" + (d.pieces || []).length + " pièce(s)</b> conservées "
          + "chiffrées. Dernier dépôt le <b>" + esc(aoJour(d.maj_le))
          + "</b>, effacement automatique le <b>" + esc(aoJour(d.purge_le))
          + "</b>. Un dépôt AJOUTE&nbsp;: vous pouvez les charger une par une, "
          + "et une pièce redéposée sous le même nom remplace la sienne. "
          + "<b>Ce qui est conservé est le texte extrait</b>, pas le fichier "
          + "d'origine&nbsp;: « Lire » ouvre ce texte, avec les passages "
          + "relevés surlignés.</p><ul class=\"ig-cons-l\">";
        (d.pieces || []).forEach(function (x) {
          /* « 85 o » À CÔTÉ DE « RC.pdf » SE LIT COMME LA TAILLE DU PDF.
             C'est celle du TEXTE EXTRAIT — le fichier n'est pas conservé. Le
             mot manquait, et il change ce que le chiffre veut dire. */
          h += '<li><span class="n">' + esc(x.nom) + "</span>"
            + '<span class="o">' + esc(aoOctets(x.octets)) + " de texte · "
            + esc(String(x.empreinte || "").slice(0, 12)) + "</span>"
            + aoTexteBouton(x.nom)
            /* RETIRER UNE PIÈCE SANS PERDRE LE DOSSIER. Sans ce geste, la
               seule façon de corriger un dépôt fautif serait de tout effacer
               puis de tout redéposer — c'est-à-dire de perdre au passage ce
               qu'on ne retrouverait pas. */
            + '<button type="button" class="ig-cons-x" data-retirer="'
            + esc(x.nom) + '" title="Retirer cette pièce du dossier" '
            + 'aria-label="Retirer ' + esc(x.nom) + ' du dossier">✕</button>'
            + "</li>";
        });
        h += "</ul>"
          + '<div class="ig-cons-f">'
          + '<button type="button" class="btn btn-s" id="ig-cons-maj">'
          + "Ajouter les pièces analysées au dossier</button>"
          + '<button type="button" class="btn btn-s" id="ig-cons-off">'
          + "Effacer ce dossier</button></div>";
      }
      h += '<p class="note" id="ig-cons-msg" style="margin-top:9px"></p></div>'
        + '<div class="ig-cons"><h4>Les six déclarations</h4>'
        + "<p>Elles ne se pré-remplissent pas. Ce qui est conservé ici est "
        + "<b>qui</b> a affirmé <b>quoi</b>, sur quel texte, avec quelles "
        + "preuves valides ce jour-là.</p>";
      (dec.lignes || []).forEach(function (l) {
        h += aoDeclaration(l, textes);
      });
      /* « OCTET POUR OCTET » ÉTAIT FAUX, ET LA MESURE L'A MONTRÉ. Un .docx
         est une archive zip où python-docx écrit l'heure courante : deux
         documents rigoureusement identiques produits à trois secondes
         d'écart n'ont pas les mêmes octets. Ce qui est identique est le
         CONTENU, et c'est cela que la règle mesure — l'écran dit donc la
         même chose qu'elle. */
      h += '<p class="ig-cons-jamais"><b>Assumer ici n\'écrit RIEN dans le '
        + "formulaire.</b> Les six cases des DC1, DC2, DC4 et ATTRI1 restent "
        + "vides&nbsp;: le contenu du fichier produit est identique avant et "
        + "après. La signature reste un geste de la main.</p></div>";
      z.innerHTML = h;
    }
    aoProjetBrancher(z);
  }

  function aoProjetBrancher(z) {
    var go = $("#ig-cons-go", z);
    if (go) go.addEventListener("click", function () {
      var sel = $("#ig-cons-sel", z);
      aoProjetRetenir(sel ? sel.value : null);
      aoProjetDeposer();
    });
    var maj = $("#ig-cons-maj", z);
    if (maj) maj.addEventListener("click", aoProjetDeposer);
    var off = $("#ig-cons-off", z);
    if (off) off.addEventListener("click", aoProjetOublier);
    z.querySelectorAll("[data-retirer]").forEach(function (b) {
      b.addEventListener("click", function () {
        aoProjetRetirer(b.dataset.retirer, b);
      });
    });
    aoTexteBrancherListe(z);
    z.querySelectorAll("[data-cons-aff]").forEach(function (b) {
      b.addEventListener("click", function () { aoAffirmer(b.dataset.consAff, z); });
    });
  }

  function aoProjetDeposer() {
    if (!AO_PROJET) return;
    if (!AO_DOCS || !AO_DOCS.length) {
      aoProjetMsg("Analysez d'abord un dossier de consultation.");
      return;
    }
    aoProjetMsg("Conservation…");
    demander("/api/datacenter/marche/projet/dossier", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ projet: AO_PROJET, pieces: AO_DOCS,
                             fiche: AO_FICHE }),
    /* LE MÊME DÉLAI QUE L'ANALYSE, POUR LE MÊME TRAVAIL. Le dépôt transmet
       les mêmes octets, les repasse à l'antivirus, en réextrait le texte et
       refait le relevé sur le dossier ENTIER. Lui laisser un budget moyen
       quand l'analyse en demande un long, c'est couper au dernier geste ce
       qu'on a laissé passer au premier. */
    }, DELAI_LONG)
      .then(function (r) { return r.json().then(function (j) { return [r.status, j]; }); })
      .then(function (xj) {
        var j = xj[1];
        if (!j || !j.ok) {
          /* LE REFUS EST DIT AVEC SA RAISON. Un « indisponible » nu enverrait
             chercher une panne là où il y a une clé non configurée. */
          aoProjetMsg((j && j.message) || "La conservation a échoué.");
          return;
        }
        /* CE QUI N'A PAS PU ÊTRE LU — OU QUI A ÉTÉ ÉCOURTÉ — EST DIT ICI
           AUSSI. Un dépôt de six pièces dont deux sont écartées se lisait
           comme un dépôt de six.

           APRÈS `aoProjetEtat`, ET C'EST L'ORDRE QUI COMPTE : cette fonction
           reconstruit tout le bloc, `#ig-cons-msg` compris. Poser le message
           avant elle revenait à l'écrire sur un élément qu'elle allait
           remplacer — mesuré en navigateur, le message était vide alors que la
           pièce avait bel et bien été écourtée. */
        var ig = j.ignores || [];
        return aoProjetEtat().then(function () {
          aoProjetMsg(ig.length
            ? ig.map(function (x) { return x.fichier + " — " + x.pourquoi; })
                .join(" · ")
            : "");
        });
      })
      .catch(function (e) {
        aoProjetMsg(aoPanne(e, (AO_DOCS || []).reduce(function (n, d) {
          return n + (d.contenu || "").length * 3 / 4; }, 0)));
      });
  }

  /* RETIRER UNE PIÈCE, ET REFAIRE LE RELEVÉ SUR CE QUI RESTE. C'est le
     serveur qui refait le relevé : le faire ici donnerait deux comptes du même
     dossier, et c'est celui qu'on oublie de corriger qui resterait affiché. */
  function aoProjetRetirer(nom, bouton) {
    if (!AO_PROJET || !nom) return;
    if (bouton) bouton.disabled = true;
    aoProjetMsg("Retrait de « " + nom + " »…");
    demander("/api/datacenter/marche/projet/dossier", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ projet: AO_PROJET, retirer: nom }),
    }, DELAI_MOYEN)
      .then(function (r) { return r.json().then(function (j) { return [r.status, j]; }); })
      .then(function (xj) {
        var j = xj[1];
        if (!j || !j.ok) {
          aoProjetMsg((j && j.message) || "Le retrait a échoué.");
          if (bouton) bouton.disabled = false;
          return;
        }
        /* L'ANALYSE À L'ÉCRAN SUIT LE DOSSIER : la garder ferait remplir les
           rubriques depuis une pièce qu'on vient de retirer. */
        AO_ANALYSE = null;
        aoProjetMsg("");
        return aoProjetEtat();
      })
      .catch(function () {
        aoProjetMsg("Le retrait a échoué.");
        if (bouton) bouton.disabled = false;
      });
  }

  function aoProjetOublier() {
    if (!AO_PROJET) return;
    aoProjetMsg("Effacement…");
    demander("/api/datacenter/marche/projet/oubli", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ projet: AO_PROJET }),
    })
      .then(function (r) { return r.json(); })
      .then(function () { aoProjetRetenir(null); AO_PROJET_ETAT = null;
                          aoProjetRendre(); })
      .catch(function () { aoProjetMsg("L'effacement a échoué."); });
  }

  function aoAffirmer(cle, z) {
    var nom = $('[data-cons-nom="' + cle + '"]', z);
    var lu = $('[data-cons-lu="' + cle + '"]', z);
    var rec = $('[data-cons-rec="' + cle + '"]', z);
    if (!nom || !nom.value.trim()) {
      aoProjetMsg("Une déclaration porte le nom de qui l'assume."); return;
    }
    /* LA CASE « J'AI LU » EST TENUE ICI, ET LA PREUVE AU SERVEUR. Elle ne
       remplace aucun contrôle : elle empêche seulement le clic distrait. */
    if (!lu || !lu.checked) {
      aoProjetMsg("Lisez le texte, puis cochez que vous l'assumez."); return;
    }
    var textes = {};
    (AO_PROJET_ETAT.textes || []).forEach(function (t) { textes[t.cle] = t; });
    aoProjetMsg("Enregistrement…");
    demander("/api/datacenter/marche/projet/affirmation", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ projet: AO_PROJET, declaration: cle,
                             par: nom.value.trim(),
                             texte_vu: (textes[cle] || {}).texte || "",
                             reconnait_sans_preuve: !!(rec && rec.checked) }),
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) { aoProjetMsg((j && j.message) || "Refusé."); return; }
        aoProjetMsg("");
        return aoProjetEtat();
      })
      .catch(function () { aoProjetMsg("L'enregistrement a échoué."); });
  }


  function démarrer() {
    Promise.all([
      /* Le 401 est levé par `demander` lui-même, bannière comprise : le
         vérifier encore ici serait du code mort. */
      demander("/api/datacenter/referentiel", { credentials: "same-origin" })
        .then(function (r) { return r.json(); }),
      demander("/api/datacenter/ingenierie", { credentials: "same-origin" })
        .then(function (r) { return r.json(); }),
      /* L'ÉTAT DE L'ART, pour les profils de serveur. Ces chiffres viennent de
         livres blancs de fournisseurs et n'entrent dans AUCUN calcul — le
         moteur tient ses constantes de normes. Ils servent uniquement à
         proposer un nombre de serveurs dans le formulaire, en disant chaque
         fois de quel profil il vient. Leur absence ne doit donc rien casser :
         on retombe sur un objet vide et le champ redevient un nombre libre. */
      demander("/api/datacenter/etat-art", { credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .catch(function () { return { ok: false }; }),
    ])
      .then(function (rs) {
        if (!rs[0].ok || !rs[1].ok) throw new Error("ref");
        REF = rs[0];
        CADRE = rs[1].referentiel;
        ART = (rs[2] && rs[2].ok && rs[2].etat) || {};
        tipBrancher();
        bâtirFormulaire();
        bâtirIdentification();
        bâtirDisponibilite();
        bâtirOnglets();
        rendreCorrespondances();
        brancherGuide();
        /* L'URL est appliquée AVANT le premier rafraîchissement : appliquée
           après, la frise se dessinerait d'abord sur la filière par défaut,
           puis sauterait — le lecteur verrait la page se contredire. */
        PIECE_VISEE = appliquerURL();
        reprendreProfil();
        pjCharger();
        depotEtat();
        depotFormulaire();
        /* Les trois prolongements : le criblage ICPE, la phase travaux et
           l'appel d'offres. Leurs formulaires se dessinent d'emblée — un
           bouton sans formulaire au-dessus n'invite personne —, mais aucun
           ne calcule tant qu'on ne le lui demande pas. */
        progFormulaire(CADRE.programme_champs);
        icpeFormulaire(CADRE.icpe_champs);
        icpeBareme();
        reseauFormulaire(CADRE.reseau_champs);
        travauxFormulaire();
        /* L'ORDRE COMPTE : `aoInterne` décide si les commandes du §14 sont
           dessinées du tout. Les dessiner d'abord ferait apparaître un
           formulaire une fraction de seconde avant de le retirer. */
        aoInterne().then(function (ouvert) {
          if (!ouvert) return;
          aoDocuments();
          aoFicheCharger();
        });
        /* LE PROJET RATTACHÉ SE RETROUVE À L'OUVERTURE, et son état est
           redemandé au serveur. Le garder localement le ferait vieillir en
           silence : une preuve expirée la semaine dernière s'afficherait
           encore « à jour ». */
        aoProjetCharger();
        if (AO_PROJET) aoProjetsCharger().then(aoProjetEtat);
        densiteEchelle();
        densiteFormulaire();
        densitePratiques();
        aoRemplir(true);
        rafraichir();
        /* Le lanceur du parcours guidé bat à l'ouverture : c'est le seul
           geste utile quand on ne connaît pas encore la page. Différé d'une
           seconde — un battement qui commence pendant que la page se dessine
           passe inaperçu, et le lecteur n'a encore rien lu. */
        setTimeout(function () {
          battre("#ig-lanceur-b", "ig-bat", "lanceur");
        }, 1000);
      })
      .catch(function (e) {
        $("#ig-form").innerHTML = '<p class="note">'
          + (String(e.message) === "auth"
            ? "Connectez-vous pour accéder au cadre d'ingénierie."
            : "Référentiel indisponible. Réessayez dans un instant.")
          + "</p>";
      });

    var b;
    if ((b = $("#ig-docx"))) b.addEventListener("click", function () { exporter("docx"); });
    if ((b = $("#ig-pdf"))) b.addEventListener("click", function () { exporter("pdf"); });
    if ((b = $("#ig-xlsx"))) b.addEventListener("click", function () { exporter("xlsx"); });
    if ((b = $("#ig-prog-add"))) b.addEventListener("click", progAjouter);
    if ((b = $("#ig-prog-go"))) b.addEventListener("click", progConsolider);
    if ((b = $("#ig-icpe-go"))) b.addEventListener("click", icpeCribler);
    if ((b = $("#ig-res-go"))) b.addEventListener("click", reseauChiffrer);
    if ((b = $("#ig-den-go"))) b.addEventListener("click", densiteEprouver);
    if ((b = $("#ig-ao-go"))) b.addEventListener("click", aoAnalyser);
    if ((b = $("#ig-ao-cand"))) b.addEventListener("click", aoCandidature);
    if ((b = $("#ig-aop-go"))) {
      b.addEventListener("click", function () { aoParcours(this); });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", démarrer);
  } else {
    démarrer();
  }
})();

/* ══════════════════════════════════════════════════════════════════════════
   LE PRIX DE LA MAÎTRISE D'ŒUVRE — treize missions, cinq groupes de phases

   TROIS PARTIS PRIS, ET CHACUN RÉPOND À UN PIÈGE :

   1. LA MISSION CHOISIE PLUS HAUT COMMANDE LES PHASES. Une conception seule
      s'arrête à la consultation : lui proposer l'assistance aux contrats ou le
      suivi de chantier lui ferait payer ce qu'elle n'a pas confié. Et pour une
      AMO, un audit ou une ingénierie EPC, le barème REFUSE — un chiffre faux
      et crédible est la pire des deux combinaisons.

   2. LE BARÈME GROUPE CE QUE LA LOI MOP SÉPARE. « APS-PC » couvre l'esquisse
      ET l'avant-projet ; « EXE » couvre le visa, la direction et la réception.
      Le relevé ne dit pas comment le montant se divise à l'intérieur d'un
      groupe : on affiche ce que chacun recouvre, et on ne propose pas de
      détacher un élément — ce serait fabriquer un chiffre.

   3. LE PARTAGE CLOS-COUVERT / TECHNIQUE PÈSE PLUS QUE N'IMPORTE QUEL TAUX.
      Sur un centre de données, la technique fait le gros des travaux, et les
      taux y sont inversés. Il est donc demandé, avec son hypothèse par défaut
      affichée comme telle.
   ══════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";
  var REF = null, PH = null;
  var $ = function (s) { return document.querySelector(s); };
  function esc(x) { return String(x == null ? "" : x)
    .replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  /* `toLocaleString` SUPPRIME LES ZÉROS DE FIN : 1,10 s'affichait « 1,1 », ce
     qui descend sous le plancher de deux décimales. */
  function nb(x) { return fr(x); }
  function fo(a) { return (!a || a[0] == null) ? "—" : nb(a[0]) + " – " + nb(a[1]); }
  function saisi(id) {
    var e = document.getElementById(id);
    if (!e) return undefined;
    var t = String(e.value == null ? "" : e.value).trim();
    return t === "" ? undefined : Number(t.replace(",", "."));
  }
  function mission() {
    var e = document.getElementById("ig-mission");
    return (e && e.value) || "moe";
  }

  /* ── CE QUI ARRIVE DE SENTINEL ────────────────────────────────────────
     L'étude d'enveloppe se mène sur conseilprev ; ce module-ci ne calcule pas
     l'investissement et le dit. Son chiffrage de MOE attend donc deux
     grandeurs qu'il faudrait autrement retaper — et retaper la part du lot
     technique est le piège : laissée vide, elle retombe sur l'hypothèse à
     70 % du barème, qui déplace les honoraires plus que n'importe quel taux.

     LES VALEURS REÇUES SONT AFFICHÉES ET MODIFIABLES, jamais imposées : le
     lecteur doit voir ce qui a été repris et pouvoir le corriger. Et leur
     ORIGINE est écrite — un montant pré-rempli sans provenance se lit comme
     un calcul de cette page, alors qu'il vient de l'autre site. */
  var CLE_ENV = "cp.moe.enveloppe.v1";
  /* AU-DELA DE DEUX MOIS, ON NE PRE-REMPLIT PLUS. Une enveloppe vieillit : les
     couts unitaires bougent, le projet change de gabarit. Un montant ancien
     re-injecte en silence est exactement la facon dont un chiffre perime entre
     dans un document remis — et personne ne verifie un champ deja rempli. On
     l'ecarte donc, et ON LE DIT, plutot que de le taire ou de l'imposer. */
  var PEREMPTION_JOURS = 60;

  function _valides(t, p, pays) {
    if (!/^[\d.]+(-[\d.]+)?$/.test(t)) t = "";
    if (!/^[\d.]+$/.test(p)) p = "";
    if (!/^[A-Z]{2}$/.test(pays)) pays = "";
    return { trav: t, pt: p, pays: pays };
  }

  function _lireURL() {
    var q = new URLSearchParams(window.location.search);
    var v = _valides((q.get("travaux_meur") || "").trim(),
                     (q.get("part_technique") || "").trim(),
                     (q.get("pays") || "").trim().toUpperCase());
    return (v.trav || v.pt || v.pays) ? v : null;
  }

  /* LA MEMOIRE VIT DANS LE NAVIGATEUR DU CLIENT, ET NULLE PART AILLEURS.
     C'est un MONTANT : le conserver sur nos serveurs en ferait une donnee de
     plus a proteger, a conserver et a effacer, pour un confort que le poste du
     client rend deja. Le bandeau dit qu'elle existe et offre de l'oublier. */
  function _lireMemoire() {
    try {
      var b = window.localStorage.getItem(CLE_ENV);
      if (!b) return null;
      var o = JSON.parse(b);
      var v = _valides(o.trav || "", o.pt || "", o.pays || "");
      if (!v.trav && !v.pt) return null;
      v.quand = Number(o.quand) || 0;
      v.jours = v.quand ? Math.floor((Date.now() - v.quand) / 86400000) : null;
      v.memoire = true;
      return v;
    } catch (e) { return null; }
  }

  function _memoriser(v) {
    try {
      window.localStorage.setItem(CLE_ENV, JSON.stringify(
        { trav: v.trav, pt: v.pt, pays: v.pays, quand: Date.now() }));
    } catch (e) { /* navigation privee : le lien continue de fonctionner */ }
  }

  function oublierEnveloppe() {
    try { window.localStorage.removeItem(CLE_ENV); } catch (e) {}
  }

  /* L'ADRESSE L'EMPORTE SUR LA MEMOIRE : elle vient de l'etude qu'on est en
     train de mener, la memoire d'une precedente. */
  function recu() {
    var u = _lireURL();
    if (u) { _memoriser(u); u.frais = true; return u; }
    var m = _lireMemoire();
    if (!m) return null;
    if (m.jours !== null && m.jours > PEREMPTION_JOURS) {
      m.perime = true;
      m.trav = ""; m.pt = "";      /* on n'ecrit rien, mais on l'annonce */
    }
    return m;
  }

  /* TROIS PROVENANCES, ET ELLES NE SE VALENT PAS. Un montant pre-rempli sans
     origine visible se lit comme un calcul de CETTE page ; un montant memorise
     se lit comme le calcul du jour. Chacune est donc nommee, et la plus fragile
     — la memoire — porte sa date. */
  function bandeauRecu(r) {
    if (r.perime) {
      var z0 = document.getElementById("ig-moe-form");
      if (z0) z0.insertAdjacentHTML("beforebegin",
        '<div class="moe-recu moe-recu-vieux"><b>Une enveloppe mémorisée a été '
        + 'écartée : elle date de ' + r.jours + ' jours.</b> Au-delà de '
        + PEREMPTION_JOURS + ' jours, les coûts unitaires et le programme ont '
        + 'trop bougé pour qu’un report se fasse en silence — un chiffre périmé '
        + 'pré-rempli finit dans un document remis sans que personne ne le '
        + 'revérifie. <b>Relancez l’étude d’enveloppe</b> sur conseilprev, ou '
        + 'saisissez le montant à la main. '
        + '<button type="button" class="moe-oubli" data-moe-oubli>Oublier cette '
        + 'valeur</button></div>');
      return;
    }
    var lignes = [];
    if (r.trav) lignes.push("montant des travaux <b>" + esc(r.trav.replace("-", " – "))
                            + " M€</b>");
    if (r.pt) lignes.push("part du lot technique <b>" + esc(r.pt) + " %</b>");
    var quand = r.frais
      ? "Repris à l’instant de l’étude d’enveloppe"
      : ("Repris d’une étude d’enveloppe mémorisée sur cet appareil"
         + (r.jours === 0 ? " aujourd’hui"
            : r.jours ? " il y a " + r.jours + " jour" + (r.jours > 1 ? "s" : "")
            : ""));
    var h = '<div class="moe-recu"><b>' + quand
      + (r.pays ? " — " + esc(r.pays) : "") + ".</b> "
      + (lignes.length ? lignes.join(", ") + ". " : "")
      + "Ces valeurs viennent de <b>conseilprev</b>, pas de cette page : "
      + "vérifiez-les et corrigez-les si votre étude a bougé."
      + (r.pays ? " Le pays est rappelé pour mémoire — <b>le barème "
                  + "d’honoraires ne varie pas d’un pays à l’autre</b>." : "")
      + (r.memoire ? ' <button type="button" class="moe-oubli" data-moe-oubli>'
                     + 'Oublier cette valeur</button>' : "")
      + "</div>";
    var z = document.getElementById("ig-moe-form");
    if (z) z.insertAdjacentHTML("beforebegin", h);
  }

  /* C'EST UN MONTANT : on doit pouvoir le retirer de son appareil, et le geste
     doit se voir. Par délégation — le bandeau est écrit après coup. */
  document.addEventListener("click", function (ev) {
    var b = ev.target && ev.target.closest
      ? ev.target.closest("[data-moe-oubli]") : null;
    if (!b) return;
    oublierEnveloppe();
    var bloc = b.closest(".moe-recu");
    if (bloc) bloc.innerHTML = "<b>Valeur oubliée.</b> Plus rien n’est "
      + "mémorisé sur cet appareil ; les champs restent tels quels et vous "
      + "pouvez les vider.";
  });

  /* ── REPRENDRE LE CHIFFRAGE DES TRAVAUX (section 7) ─────────────────────
     LE DÉFAUT QUE CELA CORRIGE. Cette section demandait un montant de travaux
     en texte libre pendant que la section 7, sur la même page, l'établissait
     poste par poste. Deux gestes, deux chiffres, et rien pour les relier : le
     montant retapé est celui qui se trompe, et il se trompait en silence.

     UNE MAINTENANCE NE SE REPREND PAS. Son total est ANNUEL ; des honoraires
     de maîtrise d'œuvre assis dessus ne veulent rien dire. Le bouton n'est
     alors pas proposé, et il DIT pourquoi plutôt que de disparaître — un
     bouton absent se lit comme une panne.

     CE QUI N'EST PAS REPRIS, ET POURQUOI : la part du lot technique. Elle se
     CALCULE dans le pont, en bas de la section 7, depuis les familles du
     chiffrage. La recopier ici depuis le navigateur dupliquerait un calcul du
     serveur — et deux calculs de la même grandeur finissent toujours par
     diverger. Le bandeau renvoie donc au pont plutôt que de deviner. */
  var TRAVAUX = null;

  function _meur(euros) {
    /* Le barème parle en M€, le chiffrage en €. Deux décimales : au-delà, on
       afficherait une précision que le chiffrage n'a pas. */
    return Math.round((Number(euros) || 0) / 10000) / 100;
  }

  function offrirReprise() {
    var zone = document.getElementById("ig-moe-reprise");
    if (!zone || !TRAVAUX) return;
    var nom = TRAVAUX.operation_nom || "le chiffrage des travaux";
    if (TRAVAUX.annuel) {
      zone.innerHTML = '<div class="moe-recu moe-recu-vieux"><b>Le chiffrage '
        + "de la section 7 porte sur « " + esc(nom) + " » : son total est "
        + "ANNUEL.</b> Il ne se reprend pas ici — des honoraires de maîtrise "
        + "d’œuvre s’asseyent sur un investissement, pas sur une dépense "
        + "d’exploitation, et l’addition des deux ne voudrait rien dire.</div>";
      return;
    }
    var m = _meur(TRAVAUX.total_avec_provision);
    if (!m) { zone.innerHTML = ""; return; }
    var reste = TRAVAUX.postes_non_chiffres
      ? (" " + TRAVAUX.postes_non_chiffres + " poste(s) sur "
         + TRAVAUX.postes_total + " y sont encore sans prix : le montant "
         + "repris les ignore, il ne les estime pas.")
      : "";
    zone.innerHTML = '<div class="moe-recu"><b>La section 7 a chiffré « '
      + esc(nom) + " » : " + esc(String(m).replace(".", ",")) + " M€</b>"
      + " (provision comprise)." + esc(reste)
      + ' <button type="button" class="moe-oubli" data-moe-reprendre>'
      + "Reprendre ce montant</button>"
      + "<br><span class=\"dc-aide\">La part du lot technique, elle, ne se "
      + "reprend pas : elle se <b>calcule</b> dans « la maîtrise d’œuvre qui "
      + "va avec », au bas de la section 7. Ici, le barème retombe sur son "
      + "hypothèse tant que vous ne la saisissez pas.</span></div>";
  }

  /* Par délégation : le bandeau est écrit après coup, et le bouton n'existe
     pas au moment où cet écouteur est posé. */
  document.addEventListener("click", function (ev) {
    var b = ev.target && ev.target.closest
      ? ev.target.closest("[data-moe-reprendre]") : null;
    if (!b || !TRAVAUX) return;
    var champ = document.getElementById("ig-moe-trav");
    if (!champ) return;
    champ.value = String(_meur(TRAVAUX.total_avec_provision)).replace(".", ",");
    /* Le champ accepte « 600 » ou « 600-750 » et lit le point ; la virgule
       française doit donc repartir en point avant le calcul. On écrit la
       virgule pour l'œil et on normalise à la lecture, comme le reste du
       formulaire. */
    champ.value = champ.value.replace(",", ".");
    champ.dispatchEvent(new Event("input", { bubbles: true }));
    var bloc = b.closest(".moe-recu");
    if (bloc) bloc.innerHTML = "<b>Montant repris de la section 7.</b> "
      + "Vérifiez-le : c’est votre chiffrage, pas une donnée de ce module — "
      + "et il vaut ce que valent les prix unitaires que vous y avez posés.";
    try { champ.focus({ preventScroll: true }); } catch (e) { champ.focus(); }
  });

  document.addEventListener("ig-chiffrage", function (ev) {
    var d = ev && ev.detail;
    if (!d || d.source !== "travaux") return;
    TRAVAUX = d;
    offrirReprise();
  });

  function champs() {
    /* LA SEULE CASE QUI BLOQUE. Sans elle, `chiffrer()` refuse avant même
       d'interroger le serveur — voir plus bas. La part du lot technique a un
       défaut publié (le plancher affiché dans son propre champ) : elle reste
       facultative, et c'est pour cela qu'elle vient après. */
    $("#ig-moe-form").innerHTML =
        '<label class="dc-champ" for="ig-moe-trav"><span class="dc-lab">'
      + 'Montant des travaux (M€)'
      + ' <b class="dc-req" title="Champ nécessaire">*</b></span>'
      + '<input type="text" id="ig-moe-trav" placeholder="ex. 600 ou 600-750">'
      + '<span class="dc-aide">Le montant sur lequel portent les honoraires. '
      + 'Ce module ne le calcule pas : reportez celui de l’étude d’enveloppe, '
      + 'ou le vôtre. Une fourchette est acceptée.</span></label>'
      + '<label class="dc-champ" for="ig-moe-pt"><span class="dc-lab">'
      + 'Part du lot technique (%)</span>'
      + '<input type="text" id="ig-moe-pt" placeholder="défaut '
      + Math.round((REF.part_technique_defaut || 0.7) * 100) + '">'
      + '<span class="dc-aide">Électricité, froid, salles. Sur un centre de '
      + 'données, ce partage pèse plus lourd que n’importe quel taux du '
      + 'barème : les taux y sont inversés par rapport au clos-couvert.</span></label>';
  }

  function phases() {
    var p = (REF.portee_mission || {})[mission()];
    var z = $("#ig-moe-phases");
    if (!p || !p.couvre) {
      /* LE REFUS EST UNE RÉPONSE, et il vaut mieux que n'importe quel nombre. */
      z.innerHTML = '<p class="dc-refus">' + esc((p && p.dit)
        || "Ce barème ne couvre pas cette mission.") + "</p>";
      PH = [];
      return;
    }
    PH = p.phases.slice();
    z.innerHTML = '<p class="note" style="margin:0 0 8px">' + esc(p.dit) + "</p>"
      + REF.phases.filter(function (f) { return p.phases.indexOf(f.cle) >= 0; })
        .map(function (f) {
          var mop = (REF.phases_mop || {})[f.cle] || {};
          return '<button type="button" class="on" data-ph="' + esc(f.cle)
            + '" title="' + esc(f.titre + " — " + f.produit
                + (mop.note ? "\n\n" + mop.note : "")) + '">'
            + esc(f.nom)
            + '<span class="moe-mop">' + esc((mop.mop || []).join(" + ")) + "</span>"
            + "</button>";
        }).join("");
    z.querySelectorAll("[data-ph]").forEach(function (b) {
      b.addEventListener("click", function () {
        var c = b.getAttribute("data-ph"), i = PH.indexOf(c);
        if (i >= 0) { PH.splice(i, 1); b.classList.remove("on"); }
        else { PH.push(c); b.classList.add("on"); }
      });
    });
  }

  function rendre(j) {
    var ph = REF.phases.filter(function (f) {
      return j.phases_retenues.indexOf(f.cle) >= 0; });
    var h = '<p class="moe-tot">' + fo(j.total_meur) + " M€ "
      + '<span class="note">soit ' + fo(j.taux_effectif_pct) + " % des "
      + fo(j.travaux_meur) + " M€ de travaux</span></p>"
      + '<p class="note">' + esc(j.assiettes.note) + "</p>"
      + '<div style="overflow-x:auto"><table class="moe-tab"><thead><tr><th>Mission</th>'
      + '<th title="clos-couvert / technique">Taux</th>'
      + ph.map(function (f) {
          var mop = (REF.phases_mop || {})[f.cle] || {};
          return "<th>" + esc(f.nom) + '<span class="moe-mop">'
            + esc((mop.mop || []).join(" + ")) + "</span></th>"; }).join("")
      + "<th>Total</th></tr></thead><tbody>"
      /* UN TAUX ABSENT N'EST PAS UN TAUX NUL. Trois missions — économie de la
         construction, sécurité incendie, coordination SSI — n'ont pas de taux
         au relevé de 2018. Le module publie 0,0 par commodité de calcul et
         signale l'état par `etat` ; rendu tel quel, on lisait « 0,0 / 0,0 % »
         et « 0 – 0 », et une mission retenue passait pour gratuite. */
      + j.missions.map(function (l) {
          var ouvert = l.etat === "taux_a_saisir";
          var cls = l.obligation ? "loi" + (l.impose ? " impose" : "") : "";
          if (ouvert) cls += (cls ? " " : "") + "ouv";
          var titre = l.role + (ouvert && l.hors_releve
            ? " — TAUX NON RELEVÉ : " + l.hors_releve.pourquoi : "");
          return "<tr" + (cls ? ' class="' + cls + '"' : "")
            + '><td title="' + esc(titre) + '">' + esc(l.nom) + "</td><td>"
            + (ouvert ? '<span class="moe-asaisir">taux à saisir</span>'
                : (l.taux_sc * 100).toFixed(1).replace(".", ",") + " / "
                  + (l.taux_mep * 100).toFixed(1).replace(".", ",") + " %")
            + "</td>"
            + ph.map(function (f) {
                return "<td>" + (ouvert ? "—" : fo(l.phases[f.cle].montant_meur))
                  + "</td>"; }).join("")
            + "<td><b>" + (ouvert ? "—" : fo(l.montant_meur))
            + "</b></td></tr>"; }).join("")
      + "</tbody><tfoot><tr><td><b>Total</b></td><td></td>"
      + ph.map(function (f) { return "<td>" + fo(j.par_phase[f.cle]) + "</td>"; }).join("")
      + "<td><b>" + fo(j.total_meur) + "</b></td></tr></tfoot></table></div>";
    /* CE QUI RESTE OUVERT EST PUBLIÉ, PAS DISSOUS. Un total qui tairait trois
       missions retenues serait exact et trompeur : le lecteur croirait avoir
       chiffré ce qu'il a coché. */
    if (j.missions_ouvertes && j.missions_ouvertes.length) {
      h += '<div class="moe-perdu moe-ouvertes"><b>'
        + j.missions_ouvertes.length + " mission(s) retenue(s) n'entrent pas "
        + "dans ce total.</b> " + esc(j.lecture_ouvertes) + "<ul>"
        + j.missions_ouvertes.map(function (m) {
            return "<li><b>" + esc(m.nom) + "</b> — "
              + esc(m.hors_releve ? m.hors_releve.pourquoi : "")
              + (m.hors_releve && m.hors_releve.ou_chercher
                 ? "<br><i>Où le trouver :</i> " + esc(m.hors_releve.ou_chercher)
                 : "") + "</li>"; }).join("")
        + "</ul></div>";
    }
    if (j.imposees && j.imposees.length) {
      h += '<p class="moe-perdu"><b>⚖ Deux missions ne se décochent pas.</b> '
        + j.imposees.map(function (i) {
            return esc(i.nom) + " — " + esc(i.obligation.texte) + " ("
              + esc(i.obligation.reference) + ")"; }).join(" ") + "</p>";
    }
    if (j.consequences && j.consequences.length) {
      h += '<div class="moe-perdu"><b>Ce que vous ne prenez pas — et ce que '
        + "cela laisse à votre charge.</b><ul>"
        + j.consequences.map(function (c) {
            return "<li><b>" + esc(c.nom) + "</b> — " + esc(c.titre) + ".<br>"
              + "<i>Produit :</i> " + esc(c.produit) + "<br>"
              + "<i>Sans elle :</i> " + esc(c.sans) + "</li>"; }).join("")
        + "</ul></div>";
    }
    h += '<p class="note" style="margin-top:10px">' + esc(j.source.origine) + " "
      + esc(j.source.reserve) + " " + esc(j.source.anonymisation) + "</p>";
    $("#ig-moe-out").innerHTML = h;
    /* Le fil des gestes ne lit pas dans ce module : il attend d'être prévenu. */
    document.dispatchEvent(new CustomEvent("ig-chiffrage"));
  }

  function chiffrer() {
    var t = saisi("ig-moe-trav");
    var brut = (document.getElementById("ig-moe-trav") || {}).value || "";
    var m = /^\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*$/.exec(brut);
    var trav = m ? [Number(m[1].replace(",", ".")), Number(m[2].replace(",", "."))]
                 : (t === undefined ? null : [t, t]);
    if (!trav) {
      $("#ig-moe-msg").textContent = "Indiquez le montant des travaux : ce "
        + "module chiffre l’énergie, l’eau et le carbone, pas l’investissement.";
      return;
    }
    var pt = saisi("ig-moe-pt");
    $("#ig-moe-msg").textContent = "chiffrage en cours…";
    demander("/api/datacenter/moe", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mission: mission(), travaux_meur: trav,
                             part_technique: pt === undefined ? null : pt / 100,
                             phases: PH })
    }, DELAI_MOYEN).then(function (r) {
      return r.json();
    }).then(function (j) {
      if (!j.ok) {
        $("#ig-moe-msg").textContent = j.message || "chiffrage indisponible";
        $("#ig-moe-out").innerHTML = "";
        return;
      }
      $("#ig-moe-msg").textContent = "Mission : " + (j.portee.dit || "");
      rendre(j);
      /* LE TABLEAU DE RÉPARTITION NE S'OFFRE QU'APRÈS UN CALCUL RÉUSSI : un
         bouton toujours présent promettrait une pièce que rien n'alimente. */
      offrirRepartition({ mission: mission(), travaux_meur: trav,
                          part_technique: pt === undefined ? null : pt / 100,
                          phases: PH });
    }).catch(function (e) {
      /* Session éteinte : la bannière partagée (sessionEteinte(), déclenchée
         par demander()) l'a déjà dit — pas la peine de le répéter ici, ni de
         parler d'un « chiffrage indisponible » alors que le barème va bien,
         c'est la session qui ne l'est plus. */
      if (e && e.name === "SessionEteinte") return;
      $("#ig-moe-msg").textContent = messageDelai(e, "chiffrage indisponible");
      $("#ig-moe-out").innerHTML = "";
    });
  }

  /* LE TABLEAU DE RÉPARTITION DES HONORAIRES, en pièce de marché.
     Il était jusqu'ici recopié à la main depuis l'écran vers un classeur ;
     c'est le moment où un chiffre juste devient faux. Le classeur est
     construit par le serveur DEPUIS LE MÊME CALCUL que ce qui est affiché. */
  function offrirRepartition(charge) {
    var hote = document.getElementById("ig-moe-out");
    if (!hote) return;
    var anc = document.getElementById("ig-moe-rep");
    if (anc) anc.remove();
    var d = document.createElement("div");
    d.id = "ig-moe-rep";
    d.style.cssText = "margin-top:14px;display:flex;align-items:center;"
      + "gap:12px;flex-wrap:wrap";
    var b = document.createElement("button");
    b.type = "button";
    b.className = "btn";
    b.textContent = "Télécharger le tableau de répartition (.xlsx)";
    var note = document.createElement("span");
    note.className = "muted";
    note.style.fontSize = "12px";
    note.textContent = "Phases MOP en lignes, cotraitants en colonnes — "
      + "rempli depuis ce calcul.";
    d.appendChild(b); d.appendChild(note);
    hote.appendChild(d);

    b.addEventListener("click", function () {
      b.disabled = true;
      var libelle = b.textContent;
      b.textContent = "préparation…";
      demander("/api/datacenter/moe/repartition?format=xlsx", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(charge)
      }, DELAI_MOYEN).then(function (r) {
        if (!r.ok) throw new Error("http-" + r.status);
        return r.blob();
      }).then(function (blob) {
        var u = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = u;
        a.download = "repartition-honoraires-moe.xlsx";
        document.body.appendChild(a);
        a.click();
        a.remove();
        /* L'ADRESSE OBJET SE LIBÈRE, sinon le classeur reste en mémoire du
           navigateur jusqu'à la fermeture de l'onglet. */
        setTimeout(function () { URL.revokeObjectURL(u); }, 2000);
        b.textContent = libelle;
        b.disabled = false;
      }).catch(function (e) {
        /* ON DIT L'ÉCHEC PLUTÔT QUE DE RENDRE LE BOUTON À SON ÉTAT INITIAL :
           un bouton qui redevient cliquable sans rien avoir produit laisse
           croire à un clic manqué. La session éteinte, elle, a déjà sa
           bannière partagée — pas la peine de la répéter sur le bouton. */
        b.textContent = (e && e.name === "SessionEteinte")
          ? libelle
          : messageDelai(e, "téléchargement indisponible");
        b.disabled = false;
      });
    });
  }

  function demarrer() {
    if (!document.getElementById("ig-moe-go")) return;
    document.getElementById("ig-moe-go").addEventListener("click", chiffrer);
    demander("/api/datacenter/moe", {}, DELAI_COURT)
      .then(function (r) { return r.json(); })
      .then(function (j) {
        /* Un barème qui ne charge pas doit LE DIRE : un bloc muet, formulaire
           vide, se lit comme une section morte — et personne ne recharge une
           page qu'il croit cassée. */
        if (!j || !j.ok) {
          $("#ig-moe-msg").textContent = "Le barème n’a pas pu être chargé. "
            + "Rechargez la page ; si cela persiste, reconnectez-vous.";
          return;
        }
        REF = j; champs(); phases();
        /* Le pré-remplissage vient APRÈS champs() : les champs n'existent pas
           avant, et écrire dedans plus tôt ne ferait rien — en silence. */
        var r = recu();
        if (r) {
          /* Une valeur perimee n'ecrit RIEN dans les champs — `recu()` les a
             vides — mais elle s'annonce quand meme : un report silencieusement
             abandonne se lit comme un lien qui n'a pas marche. */
          if (r.trav) document.getElementById("ig-moe-trav").value = r.trav;
          if (r.pt) document.getElementById("ig-moe-pt").value = r.pt;
          bandeauRecu(r);
        }
        /* UN CHIFFRAGE A PU ARRIVER AVANT LE BARÈME. Les deux sections
           chargent en parallèle, et rien ne garantit l'ordre : sans ce
           rappel, un lecteur rapide qui chiffre la section 7 pendant que le
           barème arrive ne verrait jamais l'offre de reprise. */
        offrirReprise();
        /* LA MISSION COMMANDE LES PHASES : changer l'une refait l'autre. Sans
           cela, un client passé en conception seule garderait à l'écran des
           phases qu'il ne confie plus.

           PAR DÉLÉGATION, et c'est le point : le sélecteur de mission est
           construit par la page APRÈS le chargement de son propre référentiel.
           Mon premier jet faisait `getElementById("ig-mission")` au démarrage —
           il obtenait `null`, n'attachait rien, et le bloc restait figé sur la
           maîtrise d'œuvre complète quoi qu'on choisisse. Un écouteur posé sur
           le document survit à un élément qui n'existe pas encore. */
        document.addEventListener("change", function (ev) {
          var t = ev.target;
          if (!t || t.id !== "ig-mission") return;
          phases();
          $("#ig-moe-out").innerHTML = "";
          $("#ig-moe-msg").textContent = "";
        });
      }).catch(function (e) {
        /* AVANT, CE CATCH ÉTAIT VIDE : un délai dépassé ou une panne réseau
           laissaient le formulaire muet, sans qu'aucun des deux messages
           écrits pour ce module — celui-ci, ou celui du "!j.ok" ci-dessus —
           ne sorte jamais, puisqu'une requête suspendue ne rejette pas non
           plus sans le délai posé par demander(). */
        if (e && e.name === "SessionEteinte") return;
        $("#ig-moe-msg").textContent = messageDelai(e,
          "Le barème n’a pas pu être chargé. Rechargez la page ; si cela "
          + "persiste, reconnectez-vous.");
      });
  }
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", demarrer);
  else demarrer();
})();
