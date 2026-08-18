/* Ingénierie de projet — le calcul replacé dans la séquence.
   ─────────────────────────────────────────────────────────
   Comme datacenter.js, ce fichier ne calcule RIEN. L'aptitude d'une phase, la
   liste des manques et le verdict sont produits par ingenierie_dc.py. Recalculer
   ici un « il ne manque que deux champs » ferait exister deux jugements, et
   c'est celui de l'écran que le lecteur recopierait dans son planning.

   Le parti pris d'affichage : le premier point d'arrêt est LA seule information
   qui commande une action. Neuf phases affichées à plat se lisent comme neuf
   chantiers parallèles, ce qu'elles ne sont pas. */
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
  var DOSSIER = null;

  function $(s, r) { return (r || document).querySelector(s); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
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

  function fr(n) {
    if (n === null || n === undefined || n === "") return "—";
    var x = Number(n);
    if (!isFinite(x)) return String(n);
    var s = Math.abs(x) >= 100 ? x.toFixed(0)
          : Math.abs(x) >= 10 ? x.toFixed(1)
          : x.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
    return s.replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, " ");
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
        h += '<input id="' + id + '" data-champ="' + esc(c.id) + '" type="text" inputmode="decimal"'
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
    ["pue_cible", "intensite_reseau_g", "part_evaporative"].forEach(function (id) {
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
  var CHAMPS_CONTEXTUELS = ["pue_cible", "intensite_reseau_g", "part_evaporative"];

  function rendreSuggestions(c, prefixe) {
    var props = (c.suggestions || []).concat(
      suggestionsContextuelles(c.id, prefixe));
    if (!props.length && CHAMPS_CONTEXTUELS.indexOf(c.id) < 0) return "";
    var h = '<span class="ig-sug" data-sug="' + esc(c.id) + '">';
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
        + '<div class="ig-grille">'
        + liste.map(carteP).join("") + "</div></section>";
    }
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

  function etatGuidage() {
    /* Ce que la page VOIT. Chaque clé est un constat, jamais une supposition :
       une clé absente vaut « pas fait », et un guide qui supposerait l'étape
       accomplie ferait sauter la seule qui manquait. */
    var A = PLAN && PLAN.avancement;
    return {
      projet: !!PROJET,
      profil: !!(lireProfil() || {}).puissance_it_kw,
      phase: !!PHASE,
      disponibilite: !!(($("#ig-tier") || {}).value),
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
    var g = null;
    for (var i = 0; i < fil.gestes.length; i++) {
      var c = fil.gestes[i];
      if (etat[c.fait_si]) continue;
      var pret = true;
      for (var j = 0; j < c.exige.length; j++) {
        if (!etat[c.exige[j]]) { pret = false; break; }
      }
      if (pret) { g = c; break; }
    }
    GESTE = g;
    var faits = fil.gestes.filter(function (x) { return etat[x.fait_si]; });
    var n = fil.gestes.length;

    if (!g) {
      z.className = "ig-guid fin";
      z.innerHTML = '<div class="g-t"><span class="g-p">Parcours terminé</span>'
        + "<b>" + esc(fil.fin.titre) + "</b></div>"
        + '<p class="g-x">' + esc(fil.fin.texte) + "</p>"
        + '<p class="g-a"><span class="fx">✓</span>' + esc(fil.fin.apres) + "</p>";
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
      + '<span class="g-o">' + esc(g.fleche) + "</span>"
      + '<span class="g-r">' + faits.length + " / " + n
      + " étapes franchies</span></div>"
      + '<div class="g-jauge"><i style="width:'
      + Math.round(faits.length * 100 / n) + '%"></i></div>';

    var b = $("#ig-guid-go");
    if (b) b.addEventListener("click", function () { allerAuGeste(g); });
    designer(g);
  }

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
    [["#ig-pc-docx", "docx", "Word"], ["#ig-pc-pdf", "pdf", "PDF"]]
      .forEach(function (t) {
        var b = $(t[0]);
        if (!b) return;
        b.addEventListener("click", function () {
          var tous = [$("#ig-pc-docx"), $("#ig-pc-pdf")];
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
    ["#ig-docx", "#ig-pdf"].forEach(function (s) {
      var b = $(s);
      if (b) b.disabled = !actif;
    });
    /* Les exports viennent de devenir possibles : c'est l'instant où le
       battement a quelque chose à dire. Avant, il aurait désigné des boutons
       inactifs — une promesse que le clic n'aurait pas tenue. */
    if (actif) battre("#ig-docx, #ig-pdf", "ig-bat-doc", "export");
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
  var GUIDE = null, GUIDE_ETAPE = 0, GUIDE_ROLE = null, GUIDE_THEME = null;

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
      + '</div><p class="ig-g-q">Et qu\'est-ce qui vous amène&nbsp;?</p>'
      + '<div class="ig-g-liste th" role="group" aria-label="Thème">'
      + themes.map(function (t) {
          return '<button type="button" class="ig-g-c'
            + (GUIDE_THEME === t.id ? " on" : "") + '" data-theme="' + esc(t.id)
            + '" style="--c:' + esc(t.couleur || "var(--cyan)") + '">'
            + '<span class="ic" aria-hidden="true">' + esc(t.icone) + "</span>"
            + '<span class="nm">' + esc(t.nom) + "</span>"
            + '<span class="qs">' + esc(t.question) + "</span></button>";
        }).join("")
      + "</div>";
    /* Le bouton n'apparaît QUE lorsque les deux choix sont faits : un bouton
       présent mais inopérant se lit comme une panne. */
    h += GUIDE_ROLE && GUIDE_THEME
      ? '<div class="ig-g-go"><button type="button" class="ig-g-b" id="ig-g-go">'
        + "Commencer le parcours →</button></div>"
      : '<p class="ig-g-att">Choisissez un rôle et un thème pour commencer.</p>';
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
        GUIDE_THEME = b.getAttribute("data-theme"); guideRendreChoix();
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
    if (!z || !GUIDE_ROLE || !GUIDE_THEME) return;
    var p = lireProfil();
    p.role = GUIDE_ROLE; p.theme = GUIDE_THEME;
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
       filet de gauche, celle du thème sur la jauge. Le lecteur reconnaît son
       parcours d'un coup d'œil, sans relire l'en-tête. */
    var cr = (GUIDE.role && GUIDE.role.couleur) || "var(--cyan)";
    var ct = (GUIDE.theme && GUIDE.theme.couleur) || "var(--cyan)";
    var h = '<div class="ig-g-p" style="--cr:' + esc(cr) + ";--ct:" + esc(ct) + '">'
      + '<div class="ig-g-h"><span class="ig-g-rt">'
      + '<span aria-hidden="true">' + esc(GUIDE.role.icone) + "</span> "
      + esc(GUIDE.role.nom) + " · " + esc(GUIDE.theme.icone) + " "
      + esc(GUIDE.theme.nom) + "</span>"
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
      + " · section " + e.section + "</p>"
      + "<h3>" + esc(e.titre) + "</h3>"
      + '<p class="ig-g-f">' + esc(e.faire) + "</p>"
      + '<p class="ig-g-ga"><b>Ce que vous y gagnez.</b> ' + esc(e.gain) + "</p>";
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
      h += '<div class="ig-g-fin"><b>Le piège de ce thème.</b> '
        + esc(GUIDE.theme.piege) + "</div>"
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
    "#ig-docx", "#ig-pdf",
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
    var h = '<label class="dc-champ" for="ig-tier">'
      + '<span class="dc-lab">Niveau de disponibilité visé</span>'
      + '<select id="ig-tier"><option value="">— non arrêté —</option>';
    (d.niveaux_ordre || []).forEach(function (k) {
      h += '<option value="' + esc(k) + '">' + esc(d.niveaux[k].nom) + "</option>";
    });
    h += '</select><span class="dc-aide">Le niveau qualifie une TOPOLOGIE. '
      + "Ce cadre dit ce qu'il exige et compte ce qu'il installe&nbsp;; il ne "
      + "décerne aucune certification.</span></label>";
    h += '<label class="dc-champ" for="ig-schema">'
      + '<span class="dc-lab">Schéma de redondance</span>'
      + '<select id="ig-schema"><option value="">— déduit du niveau —</option>';
    (d.schemas_ordre || []).forEach(function (k) {
      h += '<option value="' + esc(k) + '">' + esc(d.schemas[k].nom) + "</option>";
    });
    h += '</select><span class="dc-aide">Laissez « déduit » pour prendre le '
      + "schéma que le niveau appelle, ou imposez le vôtre.</span></label>";
    h += '<label class="dc-champ" for="ig-nunites">'
      + '<span class="dc-lab">Unités nécessaires par chaîne '
      + '<span class="dc-unite">(hors réserve)</span></span>'
      + '<input id="ig-nunites" type="text" inputmode="numeric" placeholder="ex. 6">'
      + '<span class="dc-aide">Le nombre de groupes froid, de chaînes onduleur '
      + "ou de groupes électrogènes que la charge exige, réserve exclue.</span></label>";
    z.innerHTML = h;
    ["#ig-tier", "#ig-schema", "#ig-nunites"].forEach(function (s) {
      var e = $(s);
      if (e) e.addEventListener(s === "#ig-nunites" ? "input" : "change", dispoDemander);
    });
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
    if (r) {
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

  function démarrer() {
    Promise.all([
      /* Le 401 est levé par `demander` lui-même, bannière comprise : le
         vérifier encore ici serait du code mort. */
      demander("/api/datacenter/referentiel", { credentials: "same-origin" })
        .then(function (r) { return r.json(); }),
      demander("/api/datacenter/ingenierie", { credentials: "same-origin" })
        .then(function (r) { return r.json(); }),
    ])
      .then(function (rs) {
        if (!rs[0].ok || !rs[1].ok) throw new Error("ref");
        REF = rs[0];
        CADRE = rs[1].referentiel;
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
  function nb(x) { return (Math.round(x * 100) / 100).toLocaleString("fr-FR"); }
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

  function champs() {
    $("#ig-moe-form").innerHTML =
        '<label class="dc-champ" for="ig-moe-trav"><span class="dc-lab">'
      + 'Montant des travaux (M€)</span>'
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
      + j.missions.map(function (l) {
          return "<tr" + (l.obligation ? ' class="loi' + (l.impose ? " impose" : "") + '"' : "")
            + '><td title="' + esc(l.role) + '">' + esc(l.nom) + "</td><td>"
            + (l.taux_sc * 100).toFixed(1).replace(".", ",") + " / "
            + (l.taux_mep * 100).toFixed(1).replace(".", ",") + " %</td>"
            + ph.map(function (f) {
                return "<td>" + fo(l.phases[f.cle].montant_meur) + "</td>"; }).join("")
            + "<td><b>" + fo(l.montant_meur) + "</b></td></tr>"; }).join("")
      + "</tbody><tfoot><tr><td><b>Total</b></td><td></td>"
      + ph.map(function (f) { return "<td>" + fo(j.par_phase[f.cle]) + "</td>"; }).join("")
      + "<td><b>" + fo(j.total_meur) + "</b></td></tr></tfoot></table></div>";
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
    fetch("/api/datacenter/moe", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mission: mission(), travaux_meur: trav,
                             part_technique: pt === undefined ? null : pt / 100,
                             phases: PH })
    }).then(function (r) {
      /* Session éteinte : « chiffrage indisponible » enverrait chercher la
         panne du mauvais côté — le barème va très bien, c'est la session. */
      if (r.status === 401) {
        $("#ig-moe-msg").innerHTML = "Votre session n’est plus active. "
          + '<a href="/connexion?next=/ingenierie-datacenter">Reconnectez-vous</a> '
          + "pour chiffrer — vous reviendrez sur cette page.";
        $("#ig-moe-out").innerHTML = "";
        throw new Error("auth-dit");
      }
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
      if (e && e.message === "auth-dit") return;
      $("#ig-moe-msg").textContent = "chiffrage indisponible";
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
      fetch("/api/datacenter/moe/repartition?format=xlsx", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(charge)
      }).then(function (r) {
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
      }).catch(function () {
        /* ON DIT L'ÉCHEC PLUTÔT QUE DE RENDRE LE BOUTON À SON ÉTAT INITIAL :
           un bouton qui redevient cliquable sans rien avoir produit laisse
           croire à un clic manqué. */
        b.textContent = "téléchargement indisponible";
        b.disabled = false;
      });
    });
  }

  function demarrer() {
    if (!document.getElementById("ig-moe-go")) return;
    document.getElementById("ig-moe-go").addEventListener("click", chiffrer);
    fetch("/api/datacenter/moe").then(function (r) { return r.json(); })
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
      }).catch(function () {});
  }
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", demarrer);
  else demarrer();
})();
