/* Ingénierie de projet — IA Factory : l'étude de faisabilité chiffrée.
   ─────────────────────────────────────────────────────────────────────
   CE FICHIER NE CALCULE RIEN, NE PORTE AUCUN PRIX ET NE NOMME AUCUNE
   ENTREPRISE. Les postes, les quantités, les prix attendus, les ancrages, les
   secteurs, les phases, les jalons, les rôles du parcours et les sources
   viennent de /api/ia-factory ; le chiffrage et le planning viennent de
   /api/ia-factory/chiffrer. Une liste recopiée ici cesserait d'être vraie au
   premier poste ajouté au module, sans que rien ne le signale.

   Même discipline que les pages de centres de données : aucune requête sans
   délai, et le 401 reconnu à l'endroit unique par où passent toutes les
   requêtes. */

var DELAI_COURT = 12000;
var DELAI_MOYEN = 45000;
var SESSION_MORTE = false;

function sessionEteinte() {
  if (SESSION_MORTE) return;
  SESSION_MORTE = true;
  var b = document.createElement("div");
  b.className = "ig-session-alerte";
  b.setAttribute("role", "alert");
  b.innerHTML = "<b>Votre session n’est plus active.</b> C’est pour cela que plus rien "
    + "ne se charge ni ne se chiffre. "
    + '<a class="btn btn-s" href="/connexion?next=/ingenierie-ia-factory">Se reconnecter</a>'
    + " — vous reviendrez sur cette page.";
  var m = document.getElementById("main") || document.body;
  m.insertBefore(b, m.firstChild);
}

function messageDelai(ms) {
  return "Le serveur n’a pas répondu en " + Math.round(ms / 1000) + " s. Ce n’est pas "
    + "forcément une panne : il peut se réveiller. Réessayez dans un instant.";
}

/* L'UNIQUE PORTE. Délai borné, 401 traité une fois, erreurs rendues lisibles. */
function demander(url, options, delai) {
  var ctrl = ("AbortController" in window) ? new AbortController() : null;
  var opts = options || {};
  if (ctrl) opts.signal = ctrl.signal;
  var t = setTimeout(function () { if (ctrl) ctrl.abort(); }, delai || DELAI_COURT);
  return fetch(url, opts).then(function (r) {
    clearTimeout(t);
    if (r.status === 401) { sessionEteinte(); throw new Error("_401"); }
    return r.json().then(function (j) {
      if (!r.ok || (j && j.ok === false)) throw new Error((j && j.error) || ("HTTP " + r.status));
      return j;
    });
  }, function (e) {
    clearTimeout(t);
    if (e && e.name === "AbortError") throw new Error("_LENT:" + (delai || DELAI_COURT));
    throw e;
  });
}

(function () {
  var REF = null;
  var SECTEUR = "";
  var GUIDE_ROLE = null;
  var GUIDE_ETAPE = 0;

  function $(id) { return document.getElementById(id); }
  function esc(x) {
    return String(x == null ? "" : x).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  /* LA RÈGLE D'OR : on n'arrondit pas sous deux décimales. Un montant au
     centime près est une valeur exacte, et supprimer les centimes est un
     arrondi — sur un chiffrage à sept lots, sept arrondis au million font une
     erreur qu'aucune ligne ne montre. */
  function euro(n) {
    if (typeof window !== "undefined" && window.CPNombres)
      return window.CPNombres.euro(n);
    if (n == null) return "—";
    return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR",
      minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
  }
  function nombre(n, dec) {
    if (typeof window !== "undefined" && window.CPNombres)
      return window.CPNombres.fr(n, dec);
    if (n == null) return "—";
    return new Intl.NumberFormat("fr-FR", {
      minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
  }
  function exact(n) {
    return (typeof window !== "undefined" && window.CPNombres)
      ? window.CPNombres.exact(n) : nombre(n);
  }
  function fourchette(a) {
    var u = a.unite === "part" ? "" : (" " + a.unite);
    var f = function (v) { return a.unite === "part" ? nombre(v * 100, 0) + " %" : nombre(v, 2); };
    return (a.min === a.max ? f(a.min) : (f(a.min) + " – " + f(a.max))) + u;
  }
  function erreur(el, e) {
    if (!el) return;
    var m = (e && e.message) || "";
    if (m === "_401") return;
    el.innerHTML = '<p class="dc-refus">' + esc(m.indexOf("_LENT:") === 0
      ? messageDelai(+m.slice(6)) : ("Indisponible : " + (m || "erreur inconnue"))) + "</p>";
  }

  /* ══ LES DIX BLOCS : BLEU TANT QUE C'EST À FAIRE, VERT QUAND C'EST FAIT ══
     DEUX NATURES, DEUX FAÇONS DE VERDIR, et la page ne confond pas les deux.
     Un bloc « mesure » verdit sur un FAIT que le serveur constate, et il
     repasse au bleu si le fait cesse. Un bloc « lecture » ne peut être
     constate par personne : il porte une case, et son libellé dit « J'ai lu »
     — c'est une déclaration du lecteur, pas une vérification de la page. Faire
     verdir un bloc au défilement prétendrait mesurer une lecture ; ce serait
     faux, et faux de la pire façon : de façon crédible.

     LES DÉCLARATIONS DE LECTURE SURVIVENT AU RECHARGEMENT. Les perdre à chaque
     visite ferait recommencer un travail que personne ne refait ; le stockage
     est local au navigateur, et son échec (navigation privée, stockage refusé)
     ne doit rien casser — d'où les try/catch. */
  var CLE_LU = "iaf-lu-v1";
  var LU = {};
  function luCharger() {
    try { LU = JSON.parse(localStorage.getItem(CLE_LU) || "{}") || {}; } catch (e) { LU = {}; }
  }
  function luEnregistrer() {
    try { localStorage.setItem(CLE_LU, JSON.stringify(LU)); } catch (e) { /* sans effet */ }
  }

  function bandeau(sec, etat) {
    var lecture = sec.nature === "lecture";
    var ok = lecture ? !!LU[sec.id] : !!(etat && etat.valide);
    var h = '<div class="iaf-etat">'
      + '<span class="iaf-num" aria-hidden="true">' + sec.numero + "</span>"
      + '<span class="iaf-pastille">' + (ok ? "validé" : (lecture ? "à lire" : "à compléter")) + "</span>"
      + '<span class="iaf-critere">' + esc(sec.critere)
      + (etat && etat.dit ? " <b>" + esc(etat.dit) + "</b>" : "")
      + bulle(sec.aide, "À propos du bloc " + sec.numero) + "</span>";
    if (lecture) {
      h += '<label class="iaf-lu"><input type="checkbox" data-lu="' + esc(sec.id) + '"'
        + (ok ? " checked" : "") + "> J’ai lu ce bloc</label>";
    }
    return h + "</div>";
  }

  function peindreBlocs(etats) {
    if (!REF || !REF.sections) return;
    REF.sections.forEach(function (sec) {
      var z = $(sec.id);
      if (!z) return;
      var etat = etats ? etats[sec.id] : null;
      var ok = sec.nature === "lecture" ? !!LU[sec.id] : !!(etat && etat.valide);
      var b = z.querySelector(".iaf-etat");
      if (b) { b.outerHTML = bandeau(sec, etat); }
      else { z.insertAdjacentHTML("afterbegin", bandeau(sec, etat)); }
      if (ok) { z.classList.add("ok"); } else { z.classList.remove("ok"); }
    });
    document.querySelectorAll("[data-lu]").forEach(function (c) {
      c.addEventListener("change", function () {
        LU[c.dataset.lu] = c.checked;
        luEnregistrer();
        var z = $(c.dataset.lu);
        if (!z) return;
        if (c.checked) { z.classList.add("ok"); } else { z.classList.remove("ok"); }
        var p = z.querySelector(".iaf-pastille");
        if (p) p.textContent = c.checked ? "validé" : "à lire";
      });
    });
  }

  /* ── LE PARCOURS GUIDÉ ────────────────────────────────────────────────
     Les rôles viennent du serveur ; la page ne connaît ni leurs noms ni les
     sections qu'ils visent. Une seule section en relief à la fois : deux
     sections en relief ne désignent plus rien. */
  function surligner(ancre) {
    document.querySelectorAll(".iaf-vise").forEach(function (e) { e.classList.remove("iaf-vise"); });
    if (!ancre) return;
    var el = $(ancre);
    if (!el) return;
    el.classList.add("iaf-vise");
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function guideOuvrir(ouvert) {
    var z = $("iaf-guide"), b = $("iaf-guide-b");
    if (!z || !b) return;
    z.hidden = !ouvert;
    b.setAttribute("aria-expanded", ouvert ? "true" : "false");
    b.textContent = ouvert ? "Fermer le parcours" : "Ouvrir le parcours guidé";
    if (!ouvert) { surligner(null); GUIDE_ROLE = null; GUIDE_ETAPE = 0; }
  }
  function guideChoix() {
    return '<p class="iaf-g-q">Qui êtes-vous sur ce projet&nbsp;?</p><div class="iaf-g-liste" role="group" aria-label="Rôle">'
      + REF.parcours.map(function (r) {
          return '<button type="button" class="iaf-g-c" data-role="' + esc(r.id) + '">'
            + '<span class="nm">' + esc(r.nom) + "</span>"
            + '<span class="qs">' + esc(r.vient_pour) + "</span></button>";
        }).join("") + "</div>";
  }
  function guideEtape() {
    var r = REF.parcours.filter(function (x) { return x.id === GUIDE_ROLE; })[0];
    if (!r) return guideChoix();
    var e = r.etapes[GUIDE_ETAPE];
    return '<div class="iaf-g-etape"><p class="iaf-g-q">' + esc(r.nom)
      + ' <span class="iaf-g-n">étape ' + (GUIDE_ETAPE + 1) + " sur " + r.etapes.length + "</span></p>"
      + "<p><b>" + esc(e.faire) + "</b></p><p>" + esc(e.obtenir) + "</p>"
      + '<div class="iaf-g-nav">'
      + (GUIDE_ETAPE > 0 ? '<button type="button" class="iaf-g-b" data-pas="-1">← Précédente</button>' : "")
      + (GUIDE_ETAPE < r.etapes.length - 1
          ? '<button type="button" class="iaf-g-b" data-pas="1">Suivante →</button>'
          : '<button type="button" class="iaf-g-b" data-fin="1">Terminer</button>')
      + '<button type="button" class="iaf-g-b iaf-g-alt" data-retour="1">Changer de rôle</button>'
      + "</div></div>";
  }
  function guideRendre() {
    var z = $("iaf-guide");
    if (!z) return;
    z.innerHTML = GUIDE_ROLE ? guideEtape() : guideChoix();
    z.querySelectorAll("[data-role]").forEach(function (b) {
      b.addEventListener("click", function () {
        GUIDE_ROLE = b.dataset.role; GUIDE_ETAPE = 0; guideRendre(); guideViser();
      });
    });
    z.querySelectorAll("[data-pas]").forEach(function (b) {
      b.addEventListener("click", function () {
        GUIDE_ETAPE += (+b.dataset.pas); guideRendre(); guideViser();
      });
    });
    var fin = z.querySelector("[data-fin]");
    if (fin) fin.addEventListener("click", function () { guideOuvrir(false); });
    var ret = z.querySelector("[data-retour]");
    if (ret) ret.addEventListener("click", function () {
      GUIDE_ROLE = null; GUIDE_ETAPE = 0; surligner(null); guideRendre();
    });
  }
  function guideViser() {
    var r = REF.parcours.filter(function (x) { return x.id === GUIDE_ROLE; })[0];
    if (r && r.etapes[GUIDE_ETAPE]) surligner(r.etapes[GUIDE_ETAPE].section);
  }

  /* ── SAISIE : un champ par quantité et par prix, dérivés du référentiel ── */
  /* L'INFOBULLE, ÉCRITE DANS LE DOCUMENT ET NON FABRIQUÉE AU SURVOL.
     Un bouton focalisable, une bulle qui est un vrai <span> — donc lisible au
     clavier, par un lecteur d'écran (aria-describedby) et à l'impression. Une
     infobulle qui n'existe qu'au survol de la souris exclut ceux qui n'ont pas
     de souris, et perd le texte pour tout le reste. */
  var _bulle = 0;
  function bulle(texte, etiquette) {
    if (!texte) return "";
    var id = "iaf-b" + (++_bulle);
    return '<button type="button" class="iaf-info" aria-describedby="' + id + '"'
      + ' aria-label="' + esc(etiquette || "Explication") + '">i'
      + '<span class="iaf-bulle" role="tooltip" id="' + id + '">' + esc(texte) + "</span></button>";
  }

  /* LA LISTE DÉROULANTE N'EXISTE QUE LÀ OÙ LE MODULE EN DÉCLARE UNE, et le
     module n'en déclare que sur des énumérations STRUCTURELLES — un ou deux
     systèmes à unifier, un horizon en années, une fraction d'effectif. Jamais
     sur un prix ni sur une charge : proposer « 1,5 ETP par cas » installerait
     une norme inventée, ce que ce module refuse partout ailleurs.

     UN VRAI `select`, ET NON UN `datalist` — LA PREMIÈRE VERSION NE SE VOYAIT
     PAS. Sur un `<input type="number">`, aucun navigateur courant n'affiche
     d'indicateur de liste : les quatre listes étaient dans le document et
     l'utilisateur ne voyait RIEN. Une commande invisible n'est pas une
     commande, et ma règle était verte parce qu'elle vérifiait que le module
     DÉCLARE des choix, jamais qu'on en VOIE un.

     LA SAISIE LIBRE RESTE POSSIBLE, et c'est la condition pour qu'un `select`
     soit acceptable ici : la dernière option ouvre le champ numérique. Sans
     cette porte, la liste cesserait de suggérer pour contraindre — et le
     client ne pourrait plus dire sa valeur exacte. */
  var AUTRE = "__autre";
  /* L'option porte le LIBELLÉ ET LA VALEUR. Le libellé seul cacherait le
     nombre qui part au chiffrage — or le champ numérique est masqué dès qu'on
     choisit, et un client doit pouvoir vérifier que « un quart » vaut bien
     25 %. La valeur nue, elle, ne dit pas ce qu'elle signifie. */
  function optionLisible(v, unite) {
    return unite === "part" ? nombre(v * 100, 0) + " %" : nombre(v, 2) + " " + unite;
  }
  /* LES EXEMPLES ARRIVENT EN PARAMÈTRE, pas par une variable de portée. La
     fonction reste pure — on peut la rendre et lire ce qu'elle produit, ce que
     font les règles — et elle ne dépend pas de l'ordre dans lequel la page
     s'initialise. */
  function champs(dict, prefixe, exemples) {
    var h = "";
    Object.keys(dict).forEach(function (k) {
      var d = dict[k], choix = (d.choix && d.choix.length) ? d.choix : null;
      var tete = '<label class="iaf-champ"><span class="iaf-nom">' + esc(d.nom)
        + ' <small>(' + esc(d.unite) + ')</small>' + bulle(d.ou, "Où trouver « " + d.nom + " »")
        + "</span>";
      var ex = (exemples || {})[k] || [];
      var champ = '<input type="number" step="any" min="0" inputmode="decimal" data-cle="' + esc(k)
        + '" data-famille="' + prefixe + '" placeholder="non renseigné"'
        + (choix ? ' hidden' : "") + ">";
      var liste = "";
      if (choix) {
        liste = '<select class="iaf-choix" data-choix="' + esc(k) + '">'
          + '<option value="">— non renseigné —</option>'
          + choix.map(function (c) {
              return '<option value="' + esc(c[0]) + '">' + esc(c[1]) + " — "
                + esc(optionLisible(c[0], d.unite)) + "</option>";
            }).join("")
          + '<option value="' + AUTRE + '">Autre valeur…</option></select>';
      }
      /* LES EXEMPLES — une liste qui SUGGÈRE, pas une liste qui contraint.
         `choix` est un ensemble fermé (« un seul socle / deux / trois ou
         plus ») : le champ libre disparaît derrière lui. `exemples` est
         l'inverse — le champ reste visible et modifiable, la liste ne fait que
         le renseigner. Confondre les deux enfermerait le client dans nos
         ordres de grandeur, ce qui est exactement ce que ce module refuse.
         Rien n'est pré-sélectionné, et chaque option dit d'où elle vient. */
      var suggestions = "";
      if (!choix && ex.length) {
        suggestions = '<select class="iaf-choix iaf-exemples" data-exemple="' + esc(k) + '">'
          + '<option value="">— un exemple pour situer —</option>'
          + ex.map(function (e) {
              return '<option value="' + esc(e.valeur) + '" data-prov="' + esc(e.provenance) + '">'
                + esc(e.libelle) + " — " + esc(optionLisible(e.valeur, d.unite))
                + " (" + esc(_provCourt(e.provenance)) + ")</option>";
            }).join("")
          + "</select>";
      }
      h += tete + liste + suggestions + champ
        + '<span class="iaf-ou">' + esc(d.ou) + "</span></label>";
    });
    return h;
  }

  /* LE MOT COURT DE LA PROVENANCE, dans l'option elle-même. Le libellé complet
     vit dans le module (`provenances`) et s'affiche sous le formulaire : ici il
     tiendrait la ligne sur trois lignes. Un exemple sans provenance visible
     serait un chiffre du cabinet déguisé en donnée. */
  function _provCourt(p) {
    return p === "ancrage" ? "source du module"
         : p === "cabinet" ? "usage du cabinet, à remplacer"
         : "hypothèse de taille";
  }

  /* Le champ numérique reste le SEUL porteur de la valeur : `lire()` ne
     regarde que lui. La liste ne fait que le renseigner — deux porteurs
     dériveraient, et c'est celui qu'on oublie qui partirait au serveur. */
  function brancherExemples() {
    document.querySelectorAll("[data-exemple]").forEach(function (sel) {
      sel.addEventListener("change", function () {
        if (sel.value === "") return;
        var champ = sel.parentNode.querySelector("input[data-cle]");
        if (!champ) return;
        champ.value = sel.value;
        champ.dispatchEvent(new Event("input", { bubbles: true }));
        /* LA LISTE SE REMET SUR SON INTITULÉ. Laissée sur l'exemple choisi,
           elle affirmerait que la valeur du champ EST cet exemple — alors que
           le client vient peut-être de la corriger juste après. */
        sel.selectedIndex = 0;
      });
    });
  }

  function brancherChoix() {
    document.querySelectorAll("[data-choix]").forEach(function (sel) {
      sel.addEventListener("change", function () {
        var champ = sel.parentNode.querySelector("input[data-cle]");
        if (!champ) return;
        if (sel.value === AUTRE) {
          champ.hidden = false;
          champ.value = "";
          champ.focus();
        } else {
          champ.hidden = true;
          champ.value = sel.value;
        }
        champ.dispatchEvent(new Event("input", { bubbles: true }));
      });
    });
  }
  function lire(famille) {
    var out = {};
    document.querySelectorAll('input[data-famille="' + famille + '"]').forEach(function (i) {
      if (i.value !== "" && !isNaN(+i.value)) out[i.dataset.cle] = +i.value;
    });
    return out;
  }
  /* Les quantités dépendent du secteur : on redessine en CONSERVANT ce qui
     est déjà saisi — un champ vidé par un changement de secteur ferait perdre
     un travail que personne ne pense à refaire. */
  function redessinerQuantites() {
    var garde = lire("q");
    var dict = {};
    Object.keys(REF.quantites).forEach(function (k) { dict[k] = REF.quantites[k]; });
    Object.keys(REF.quantites_secteur).forEach(function (k) {
      var v = REF.quantites_secteur[k];
      if (SECTEUR && v.secteurs.indexOf(SECTEUR) >= 0) dict[k] = v;
    });
    $("iaf-q").innerHTML = champs(dict, "q", REF.exemples);
    document.querySelectorAll('input[data-famille="q"]').forEach(function (i) {
      if (garde[i.dataset.cle] == null) return;
      i.value = garde[i.dataset.cle];
      /* Une valeur reprise doit se retrouver DANS la liste si elle y figure,
         sinon la liste afficherait « non renseigné » sur un champ rempli. */
      var sel = i.parentNode.querySelector("[data-choix]");
      if (!sel) return;
      var connue = Array.prototype.some.call(sel.options, function (o) {
        return o.value !== "" && o.value !== AUTRE && +o.value === +i.value;
      });
      if (connue) { sel.value = String(+i.value); i.hidden = true; }
      else { sel.value = AUTRE; i.hidden = false; }
    });
    brancherChoix();
    brancherExemples();
  }

  /* ── LES SECTEURS ─────────────────────────────────────────────────────── */
  function rendreSecteurs() {
    var h = '<div class="iaf-sect-choix" role="group" aria-label="Secteur">'
      + Object.keys(REF.secteurs).map(function (k) {
          return '<button type="button" class="iaf-sect-b' + (SECTEUR === k ? " on" : "")
            + '" data-secteur="' + esc(k) + '">' + esc(REF.secteurs[k].nom) + "</button>";
        }).join("") + "</div>";
    if (!SECTEUR) {
      h += '<p class="dc-refus">Aucun secteur choisi : les postes, les jalons et les cas d’usage '
        + "propres au secteur ne sont pas dans l’étude, qui est de ce fait incomplète.</p>";
      return h;
    }
    var s = REF.secteurs[SECTEUR];
    h += "<p>" + esc(s.resume) + "</p>"
      + '<p class="iaf-autorites"><b>Autorités&nbsp;:</b> ' + esc(s.autorites) + "</p>"
      + "<h3>Les textes qui s’appliquent</h3><ul class=\"iaf-textes\">"
      + s.textes.map(function (t) {
          var src = REF.sources[t] || {};
          return "<li>" + (src.url
              ? '<a href="' + esc(src.url) + '" target="_blank" rel="noopener noreferrer">' + esc(src.titre) + "</a>"
              : esc(src.titre))
            + ' <span class="iaf-src">' + esc(src.editeur) + ", " + esc(src.annee)
            + " · " + esc(src.nature) + "</span></li>";
        }).join("") + "</ul>"
      + "<h3>Les cas d’usage typiques, et la case où la question se pose</h3>"
      + '<table class="moe-tab"><thead><tr><th>Cas d’usage</th><th>Classe</th><th>Pourquoi</th></tr></thead><tbody>'
      + s.cas_usage.map(function (c) {
          return "<tr><td>" + esc(c.nom) + '</td><td><span class="iaf-classe c-' + esc(c.classe)
            + '">' + esc(c.classe.replace(/_/g, " ")) + "</span><br><small>"
            + esc(REF.classes_cas[c.classe] || "") + "</small></td><td>" + esc(c.pourquoi) + "</td></tr>";
        }).join("") + "</tbody></table>"
      + '<p class="iaf-ou">La classe n’est PAS une qualification juridique : c’est la case où la '
      + "question se pose. La qualification se fait dossier par dossier.</p>"
      + '<p class="moe-recu"><b>Propre à ce secteur&nbsp;:</b> ' + esc(s.propre) + "</p>";
    if (s.secteurs_annexe_I) {
      h += "<h3>Les secteurs visés</h3><p><b>Annexe I (hautement critiques)&nbsp;:</b> "
        + esc(s.secteurs_annexe_I.join(", ")) + ".<br><b>Annexe II (autres secteurs critiques)&nbsp;:</b> "
        + esc(s.secteurs_annexe_II.join(", ")) + ".</p>";
    }
    return h;
  }
  function brancherSecteurs() {
    document.querySelectorAll("[data-secteur]").forEach(function (b) {
      b.addEventListener("click", function () {
        SECTEUR = (SECTEUR === b.dataset.secteur) ? "" : b.dataset.secteur;
        $("iaf-secteur").innerHTML = rendreSecteurs();
        brancherSecteurs();
        redessinerQuantites();
        rafraichirBlocs();
      });
    });
  }

  /* ── ANCRAGES, PHASES, JALONS, LEVIERS, SOURCES ───────────────────────── */
  /* ── LES CAS COMPARABLES, EN LISTE DÉROULANTE ─────────────────────────
     POURQUOI UN MENU PLUTÔT QUE QUATRE ARTICLES EMPILÉS. Chaque cas porte de
     deux à six chiffres, chacun avec sa source ET ce qu'il ne dit pas : à la
     suite, cela fait un mur qu'on parcourt en diagonale. Or ces cas servent à
     SITUER, pas à caler — et on ne situe pas en lisant tout, on situe en
     comparant un cas à sa propre installation, un à la fois.

     LE NOMBRE DE CAS EST ÉCRIT DANS L'INTITULÉ. Un menu qui n'en montre qu'un
     par défaut ferait croire qu'il n'y en a qu'un ; le libellé dit combien il
     y en a, et la première option les rend tous à la suite pour qui veut les
     lire d'un bloc.

     ET LE COMPTE N'EST PAS ÉCRIT EN DUR : il vient de ce que le module rend.
     Un quatrième cas ajouté au module apparaîtrait dans le menu et le compte
     resterait faux si on l'avait figé ici. */
  var CMP_TOUS = "__tous";

  function _casCourt(nom) {
    /* « Cas A — grand groupe bancaire… » : l'intitulé complet ne tient pas
       dans une option sans la rendre illisible. On garde le repère et la
       nature, on coupe le développement. */
    var i = String(nom || "").indexOf(" : ");
    return i > 0 ? String(nom).slice(0, i) : String(nom || "");
  }

  function rendreComparables(cmp, sources, secteurs) {
    var h = '<label class="iaf-champ iaf-cmp-m"><span class="iaf-nom">'
      /* LE COMPTE VIENT DES DONNÉES, en chiffre et au même endroit que dans
         l'option : « Quatre cas documentés » au-dessus de « Les 4 cas » écrit
         le même nombre de deux façons dans la même commande. */
      + cmp.length + " cas documentés — en choisir un"
      + '</span><select class="iaf-choix" data-cmp>'
      + '<option value="' + CMP_TOUS + '">Les ' + cmp.length
      + " cas, à la suite</option>";
    /* RANGÉS PAR SECTEUR, et c'est la raison d'être de ce menu depuis qu'il
       n'y a plus qu'une seule activité dedans. Les quatre premiers cas
       venaient tous de la banque ; un assureur ou un hôpital lisait quatre
       banques sans savoir laquelle le concernait. L'ordre des groupes et
       leurs libellés viennent du MODULE (`secteurs_comparables`), pas d'une
       liste recopiée ici : un cinquième secteur ajouté au module apparaît
       sans qu'on touche à ce fichier. */
    (secteurs || []).forEach(function (sec) {
      var dedans = [];
      cmp.forEach(function (c, i) { if (c.secteur === sec.cle) dedans.push(i); });
      if (!dedans.length) return;
      h += '<optgroup label="' + esc(sec.nom) + " (" + dedans.length + ')">'
        /* CHOISIR UN SECTEUR ENTIER, comme le menu des sources permet de
           choisir une nature entière. Sans cela le groupe ne serait qu'un
           intertitre : on saurait dans quelle activité on est, sans pouvoir
           lire cette activité d'un bloc. */
        + '<option value="s:' + esc(sec.cle) + '">Tout ce groupe — '
        + esc(sec.nom) + " (" + dedans.length + ")</option>";
      dedans.forEach(function (i) {
        h += '<option value="c' + i + '"' + (i === 0 ? " selected" : "") + ">"
          + esc(_casCourt(cmp[i].organisation)) + "</option>";
      });
      h += "</optgroup>";
    });
    h += '</select><span class="iaf-ou">Ils servent à SITUER un ordre de '
      + "grandeur, pas à caler un chiffrage : chaque valeur porte sa source et "
      + "ce qu'elle ne dit pas.</span></label>";
    return h + cmp.map(function (c, i) {
      return '<article class="iaf-cmp" data-cas="c' + i + '" data-cmp-sec="'
        + esc(c.secteur) + '"'
        + (i === 0 ? "" : " hidden") + "><h4>" + esc(c.organisation) + "</h4><ul>"
        + c.chiffres.map(function (x) {
            var s = sources[x.source] || {};
            return "<li><b>" + esc(x.nom) + "</b> : " + esc(fourchette(x))
              + ' <span class="iaf-src">' + esc(s.editeur || x.source) + ", " + esc(s.annee || "")
              + "</span><br><small>Ne dit pas : " + esc(x.ne_dit_pas) + "</small></li>";
          }).join("")
        + '</ul><p class="iaf-lecon">' + esc(c.lecon) + "</p></article>";
    }).join("");
  }

  /* Le filtre MASQUE, il ne redessine pas : redessiner referait le menu et
     perdrait le choix au moment même où on vient de le poser. */
  function brancherPhases() {
    var sel = document.querySelector("#iaf-phases [data-phase]");
    if (!sel) return;
    sel.addEventListener("change", function () {
      var cle = sel.value;
      document.querySelectorAll("#iaf-phases [data-ph]").forEach(function (li) {
        li.hidden = !(cle === PH_TOUTES || li.dataset.ph === cle);
      });
    });
  }

  /* LE FILTRE DES JALONS EST BRANCHÉ SUR UN CONTENEUR, pas sur un
     identifiant : la table des jalons est rendue DEUX FOIS — dans la section 5
     au chargement, et dans le calendrier après le chiffrage. Un branchement
     posé sur le seul premier laisserait le second menu mort. */
  function brancherJalons(racine) {
    (racine || document).querySelectorAll("[data-jal]").forEach(function (sel) {
      if (sel.dataset.branche) return;
      sel.dataset.branche = "1";
      sel.addEventListener("change", function () {
        var cle = sel.value;
        var etat = cle.slice(0, 2) === "e:" ? cle.slice(2) : null;
        var tab = sel.closest("label").parentNode;
        tab.querySelectorAll("tr[data-jal-etat]").forEach(function (tr) {
          tr.hidden = !(cle === JAL_TOUS || tr.dataset.jalEtat === etat);
        });
      });
    });
  }

  function brancherComparables() {
    /* CHERCHÉ DANS SON CONTENEUR, PAS PAR `$()`. Une règle du dépôt vérifie que
       tout identifiant visé par `$()` existe DANS LA PAGE — parce qu'un
       identifiant renommé d'un seul côté ne lève rien et laisse une zone
       vide. Ce menu-ci n'est pas une ancre de la page : c'est le script qui le
       crée. Le viser par `$()` aurait fait passer pour une ancre manquante ce
       qui n'en est pas une, et surtout aurait affaibli une règle utile. */
    var sel = document.querySelector("#iaf-cmp [data-cmp]");
    if (!sel) return;
    sel.addEventListener("change", function () {
      var cle = sel.value;
      var sec = cle.slice(0, 2) === "s:" ? cle.slice(2) : null;
      document.querySelectorAll("#iaf-cmp [data-cas]").forEach(function (a) {
        a.hidden = !(cle === CMP_TOUS
          || (sec !== null && a.dataset.cmpSec === sec)
          || a.dataset.cas === cle);
      });
    });
  }
  var PH_TOUTES = "__toutes";

  /* CINQ PHASES EMPILÉES FONT UN MUR. Chacune porte son entrée, sa sortie, ses
     activités et ses livrables — de trois à sept lignes chacune : à la suite,
     on les parcourt en diagonale, et une phase parcourue en diagonale ne sert
     plus à décider.

     UNE SEULE EST OUVERTE AU CHARGEMENT, comme les cas comparables et à
     l'inverse des sources : une phase se LIT, les sources se COMPTENT. Et
     l'intitulé dit combien il y en a, sinon un menu qui n'en montre qu'une
     ferait croire qu'il n'y en a qu'une.

     LES OPTIONS SONT NUMÉROTÉES, et ce n'est pas un ornement : les phases sont
     une SÉQUENCE — la sortie de l'une est l'entrée de la suivante. Le numéro
     porte une information que le lecteur a besoin de lire. */
  function rendrePhases(ref) {
    var h = '<label class="iaf-champ iaf-cmp-m"><span class="iaf-nom">'
      + ref.phases.length + " phases, dans l'ordre du projet — en choisir une"
      + '</span><select class="iaf-choix" data-phase>'
      + '<option value="' + PH_TOUTES + '">Les ' + ref.phases.length
      + " phases, à la suite</option>"
      + ref.phases.map(function (p, i) {
          return '<option value="p' + i + '"' + (i === 0 ? " selected" : "") + ">"
            + (i + 1) + ". " + esc(p.nom) + " — " + p.mois_min + " à " + p.mois_max
            + " mois</option>";
        }).join("")
      + '</select><span class="iaf-ou">Les durées sont l\'usage du cabinet, à '
      + "±50 %. La sortie d'une phase est l'entrée de la suivante : l'ordre "
      + "porte autant que les durées.</span></label>";
    return h + '<ol class="iaf-phases">' + ref.phases.map(function (p, i) {
      return '<li data-ph="p' + i + '"' + (i === 0 ? "" : " hidden")
        + "><b>" + esc(p.nom) + "</b> — " + p.mois_min + " à " + p.mois_max + " mois"
        + '<span class="iaf-nature">usage du cabinet, ±50 %</span>'
        + '<div class="iaf-ph-g"><div><span class="iaf-ph-t">Entrée</span>' + esc(p.entree) + "</div>"
        + '<div><span class="iaf-ph-t">Sortie</span>' + esc(p.sortie) + "</div></div>"
        + '<span class="iaf-ph-t">Activités</span><ul>'
        + p.activites.map(function (a) { return "<li>" + esc(a) + "</li>"; }).join("") + "</ul>"
        + '<span class="iaf-ph-t">Livrables</span><ul>'
        + p.livrables.map(function (l) { return "<li>" + esc(l) + "</li>"; }).join("") + "</ul>"
        + "<em>Jalon : " + esc(p.jalon) + "</em></li>";
    }).join("") + "</ol>";
  }
  var JAL_TOUS = "__tous";

  /* L'ÉTAT D'UN JALON VIENT DU MODULE, pas d'une expression conditionnelle
     écrite ici. Elle y était, et `planning()` en calculait une seconde côté
     serveur : deux arithmétiques pour une même colonne. Voir `etat_jalon`. */
  function _nomEtatJalon(cle, etats) {
    var e = (etats || []).filter(function (x) { return x.cle === cle; })[0];
    /* PAS DE LIBELLÉ DE SECOURS ÉCRIT ICI. Un repli local redeviendrait le
       second exemplaire qu'on vient de retirer : si le module cesse de publier
       ses états, la colonne doit le MONTRER, pas le masquer. */
    return e ? e.nom : cle;
  }

  function _etatJalon(j) {
    if (j.passe) return "vigueur";
    if (j.avant_fin_projet === null || j.avant_fin_projet === undefined) return "attente";
    return j.avant_fin_projet ? "pendant" : "apres";
  }

  /* LES JALONS SE COMPTENT, ILS NE SE LISENT PAS UN À UN : tous restent
     visibles au chargement, et le menu sert à RÉDUIRE — c'est le choix fait
     pour les sources, à l'inverse des cas et des phases. Ce qu'un lecteur veut
     isoler ici est une question précise : « qu'est-ce qui me tombe dessus
     pendant le projet ? » L'état est donc l'axe, et les groupes ne montrent
     que les états RÉELLEMENT présents — un groupe vide promettrait un tri qui
     ne rend rien. */
  function rendreJalons(jal, sources, etats) {
    var h = "";
    var presents = (etats || []).filter(function (e) {
      return jal.some(function (j) { return _etatJalon(j) === e.cle; });
    });
    if (presents.length > 1) {
      h = '<label class="iaf-champ iaf-cmp-m"><span class="iaf-nom">'
        + jal.length + " jalons — en isoler un état"
        + '</span><select class="iaf-choix" data-jal>'
        + '<option value="' + JAL_TOUS + '">Les ' + jal.length
        + " jalons, à la suite</option>"
        + presents.map(function (e) {
            var n = jal.filter(function (j) { return _etatJalon(j) === e.cle; }).length;
            return '<option value="e:' + esc(e.cle) + '">' + esc(e.nom)
              + " (" + n + ")</option>";
          }).join("")
        + "</select></label>";
    }
    return h + '<table class="moe-tab iaf-jalons"><thead><tr><th>Date</th><th>Texte</th><th>Ce que cela porte</th><th>État</th></tr></thead><tbody>'
      + jal.map(function (j) {
          var s = sources[j.source] || {};
          return '<tr data-jal-etat="' + esc(_etatJalon(j)) + '"'
            + (j.passe ? ' class="passe"' : "") + "><td>" + esc(j.date) + "</td><td>"
            + esc(j.texte) + (s.url ? ' <a href="' + esc(s.url) + '" target="_blank" rel="noopener noreferrer">texte</a>' : "")
            + "</td><td>" + esc(j.porte) + "</td><td>"
            + esc(_nomEtatJalon(_etatJalon(j), etats)) + "</td></tr>";
        }).join("") + "</tbody></table>";
  }
  var LEV_TOUS = "__tous";

  /* CE QUI SOUTIENT UN LEVIER, calculé à UN SEUL endroit. Le rendu décidait
     déjà de la mention affichée par une cascade — ancrage, puis source, puis
     « convention du cabinet » ; le menu en aurait fait une seconde, et deux
     cascades pour un même verdict divergent. On lit donc le même résultat que
     celui qui s'affiche sous le levier. */
  function _soutienLevier(l, parCle, sources) {
    if (!l.ancrage) return "convention";
    return (parCle[l.ancrage] || sources[l.ancrage]) ? "ancre" : "convention";
  }

  /* CINQ LEVIERS EMPILÉS FONT UN MUR : chacun porte son propos, son public, sa
     mesure et son ancrage — quatre à cinq lignes. Un seul est ouvert au
     chargement, comme les phases et les cas : un levier se LIT.

     RANGÉS PAR CE QUI LES SOUTIENT, et c'est l'axe que le chapô de la page
     promettait déjà sans qu'on puisse trier dessus. C'est la seule question
     qui décide de ce qu'un levier vaut dans une discussion : est-ce que je peux
     le montrer, ou est-ce que je dois l'assumer ?

     LA MÊME FONCTION SERT LA SECTION 6 ET LA SECTION 7 — les leviers de
     conduite du changement et les principes de migration ont la même forme.
     L'intitulé arrive donc en paramètre : « 5 leviers » sur l'une, « 4
     principes » sur l'autre. Écrit en dur, il aurait menti sur l'une des deux. */
  function rendreLeviers(liste, sources, ancrages, soutiens, intitule, prefixe) {
    var parCle = {};
    ancrages.forEach(function (a) { parCle[a.cle] = a; });
    var quoi = prefixe || "lev";
    var etiquette = function (l) { return _soutienLevier(l, parCle, sources); };

    var h = "";
    var presents = (soutiens || []).filter(function (g) {
      return liste.some(function (l) { return etiquette(l) === g.cle; });
    });
    if (presents.length > 1) {
      h = '<label class="iaf-champ iaf-cmp-m"><span class="iaf-nom">'
        + liste.length + " " + esc(intitule || "éléments") + " — en choisir un"
        + '</span><select class="iaf-choix" data-lev="' + esc(quoi) + '">'
        + '<option value="' + LEV_TOUS + '">Les ' + liste.length + " "
        + esc(intitule || "éléments") + ", à la suite</option>";
      presents.forEach(function (g) {
        var dedans = [];
        liste.forEach(function (l, i) { if (etiquette(l) === g.cle) dedans.push(i); });
        h += '<optgroup label="' + esc(g.nom) + " (" + dedans.length + ')">'
          + '<option value="s:' + esc(g.cle) + '">Tout ce groupe — '
          + esc(g.nom) + " (" + dedans.length + ")</option>";
        dedans.forEach(function (i) {
          h += '<option value="l' + i + '"' + (i === 0 ? " selected" : "") + ">"
            + esc(liste[i].nom) + "</option>";
        });
        h += "</optgroup>";
      });
      h += "</select></label>";
    }

    return h + '<ul class="iaf-leviers">' + liste.map(function (l, i) {
      var a = l.ancrage ? (parCle[l.ancrage] || null) : null;
      var s = l.ancrage ? (sources[l.ancrage] || null) : null;
      var ref = a ? (esc(a.nom) + " : " + esc(fourchette(a)))
        : (s ? esc(s.editeur) + ", " + esc(s.annee) : "convention du cabinet, à discuter");
      return '<li data-lev-item="l' + i + '" data-lev-soutien="' + esc(etiquette(l)) + '"'
        + (i === 0 || !h ? "" : " hidden")
        + "><b>" + esc(l.nom) + "</b><br>" + esc(l.dit)
        + (l.publics ? '<br><span class="iaf-ph-t">Publics</span>' + esc(l.publics) : "")
        + (l.mesure ? '<br><span class="iaf-ph-t">Mesure</span>' + esc(l.mesure) : "")
        + (l.geste ? '<br><span class="iaf-ph-t">Geste</span>' + esc(l.geste) : "")
        + '<br><span class="iaf-src">Ancrage — ' + ref + "</span></li>";
    }).join("") + "</ul>";
  }

  /* BRANCHÉ SUR SON CONTENEUR, comme les jalons : deux sections emploient le
     même rendu, et un branchement posé sur un identifiant laisserait l'autre
     menu mort. */
  function brancherLeviers(racine) {
    (racine || document).querySelectorAll("[data-lev]").forEach(function (sel) {
      if (sel.dataset.branche) return;
      sel.dataset.branche = "1";
      sel.addEventListener("change", function () {
        var cle = sel.value;
        var grp = cle.slice(0, 2) === "s:" ? cle.slice(2) : null;
        var liste = sel.closest("label").parentNode;
        liste.querySelectorAll("[data-lev-item]").forEach(function (li) {
          li.hidden = !(cle === LEV_TOUS
            || (grp !== null && li.dataset.levSoutien === grp)
            || li.dataset.levItem === cle);
        });
      });
    });
  }
  /* ── LES SOURCES, EN LISTE DÉROULANTE ─────────────────────────────────
     TRENTE-SIX SOURCES À LA SUITE NE SE LISENT PAS, elles se survolent — et
     une liste qu'on survole ne sert plus à vérifier, qui est sa seule raison
     d'être. Le menu les range PAR NATURE, parce que c'est l'axe qui décide de
     ce qu'une source vaut : une autorité publique, un texte juridique, un
     analyste, un média et un fournisseur ne s'opposent pas de la même façon à
     une contradiction.

     ON PEUT CHOISIR UNE NATURE ENTIÈRE, et pas seulement une source. Avec
     trente-six entrées, filtrer une à une serait une commande sans usage :
     ce qu'on veut savoir, c'est « qu'est-ce qui vient d'une autorité ? ».

     LES COMPTES VIENNENT DE `couverture_sources()`, jamais du script : le
     module les calcule déjà, et deux comptages divergeraient. */
  var SRC_TOUTES = "__toutes";

  function rendreSources(sources, couv) {
    var parNature = {};
    Object.keys(sources).forEach(function (k) {
      var n = sources[k].nature || "autre";
      (parNature[n] = parNature[n] || []).push(k);
    });
    var natures = Object.keys(parNature).sort();

    var h = '<p class="iaf-couv">' + couv.total + " sources — " + couv.avec_adresse
      + " avec adresse, <b>" + couv.lues + " lue(s) depuis ce poste</b>. " + esc(couv.limite)
      + "</p>";
    h += '<label class="iaf-champ iaf-cmp-m"><span class="iaf-nom">'
      + couv.total + " sources, rangées par nature — en choisir une"
      + '</span><select class="iaf-choix" data-src>'
      + '<option value="' + SRC_TOUTES + '">Les ' + couv.total
      + " sources, à la suite</option>";
    natures.forEach(function (n) {
      h += '<optgroup label="' + esc(n) + " (" + parNature[n].length + ')">'
        + '<option value="n:' + esc(n) + '">Toutes celles de nature « '
        + esc(n) + " » (" + parNature[n].length + ")</option>";
      parNature[n].forEach(function (k) {
        h += '<option value="s:' + esc(k) + '">' + esc(sources[k].editeur)
          + ", " + esc(sources[k].annee) + "</option>";
      });
      h += "</optgroup>";
    });
    h += '</select><span class="iaf-ou">Une source qu\'on ne peut pas rouvrir '
      + "est une intention, pas une source : celles qui n'ont pas d'adresse le "
      + "disent, et portent leur réserve.</span></label>";

    h += '<ol class="iaf-sources">';
    natures.forEach(function (n) {
      parNature[n].forEach(function (k) {
        var s = sources[k];
        h += '<li data-src-cle="' + esc(k) + '" data-src-nat="' + esc(n) + '">'
          + (s.url
            ? '<a href="' + esc(s.url) + '" target="_blank" rel="noopener noreferrer">' + esc(s.titre) + "</a>"
            : '<span class="iaf-muet">' + esc(s.titre) + '</span> <span class="na-src-sans">sans adresse</span>')
          + " — <em>" + esc(s.editeur) + "</em>, " + esc(s.annee)
          + ' <span class="iaf-nature">' + esc(s.nature) + "</span>"
          + (s.reserve ? "<br><small>" + esc(s.reserve) + "</small>" : "") + "</li>";
      });
    });
    return h + "</ol>";
  }

  /* Le filtre MASQUE, il ne redessine pas : la numérotation de la liste suit
     ce qui reste visible, et redessiner perdrait le choix qu'on vient de
     poser. */
  function brancherSources() {
    var sel = document.querySelector("#iaf-sources [data-src]");
    if (!sel) return;
    sel.addEventListener("change", function () {
      var v = sel.value;
      document.querySelectorAll("#iaf-sources li[data-src-cle]").forEach(function (li) {
        li.hidden = !(v === SRC_TOUTES
          || (v.slice(0, 2) === "n:" && li.dataset.srcNat === v.slice(2))
          || (v.slice(0, 2) === "s:" && li.dataset.srcCle === v.slice(2)));
      });
    });
  }

  /* ── CHIFFRAGE ───────────────────────────────────────────────────────── */
  function rendreChiffrage(c, ref) {
    var titres = {};
    ref.groupes.forEach(function (g) { titres[g[0]] = g[1]; });
    var h = "";
    if (c.alertes && c.alertes.length) {
      h += '<div class="dc-refus"><ul>' + c.alertes.map(function (a) { return "<li>" + esc(a) + "</li>"; }).join("") + "</ul></div>";
    }
    h += '<table class="moe-tab"><thead><tr><th>Poste</th><th>Formule</th><th>Montant</th></tr></thead><tbody>';
    ref.groupes.forEach(function (g) {
      var lignes = c.lignes.filter(function (l) { return l.groupe === g[0]; });
      if (!lignes.length && g[0] !== "aleas") return;
      h += '<tr class="iaf-grp"><td colspan="3">' + esc(g[1]) + "</td></tr>";
      lignes.forEach(function (l) {
        h += "<tr" + (l.statut === "non_chiffre" ? ' class="ouv"' : "") + "><td>" + esc(l.nom)
          + (l.sectoriel ? ' <span class="iaf-classe">secteur</span>' : "")
          + (l.couvre ? "<br><small><b>Couvre :</b> " + esc(l.couvre) + "</small>" : "")
          + (l.exclut ? "<br><small><b>Exclut :</b> " + esc(l.exclut) + "</small>" : "")
          + (l.note ? "<br><small>" + esc(l.note) + "</small>" : "")
          + "</td><td><code>" + esc(l.formule) + "</code></td><td>"
          + (l.statut === "chiffre" ? euro(l.montant)
             : '<span class="moe-asaisir">non chiffré</span><br><small>manque : ' + esc(l.manque.join(", ")) + "</small>")
          + "</td></tr>";
      });
      if (g[0] === "aleas") {
        h += "<tr><td>Provision pour aléas</td><td><code>sous-total × taux saisi</code></td><td>"
          + (c.provision == null ? '<span class="moe-asaisir">non saisie</span>' : euro(c.provision)) + "</td></tr>";
      }
    });
    h += "</tbody></table>";
    h += '<p class="moe-tot">' + (c.total == null ? "Sous-total chiffré : " + euro(c.sous_total)
        : "Total : " + euro(c.total))
      + ' <span class="note">— ' + c.n_non_chiffres + " poste(s) sur " + c.n_postes + " non chiffré(s), soit "
      + nombre(c.part_non_chiffree * 100, 0) + " % de la structure</span></p>";
    return h;
  }
  function rendreDim(d) {
    if (!d.instruit) {
      return '<p class="dc-refus">' + esc(d.dit) + " Manque : " + esc(d.manque.join(", ")) + "</p>";
    }
    return "<p><b>Constructeurs de modèles</b> : " + nombre(d.roles.constructeurs.max, 1) + " ETP — "
      + esc(d.roles.constructeurs.dit) + "</p><p><b>Plateforme et data</b> : "
      + nombre(d.roles.plateforme.min, 1) + " à " + nombre(d.roles.plateforme.max, 1) + " ETP — "
      + esc(d.roles.plateforme.dit) + '</p><p class="moe-tot">Équipe centrale : '
      + nombre(d.total.min, 1) + " à " + nombre(d.total.max, 1) + " ETP"
      + ' <span class="note">— ' + esc(d.dit) + "</span></p>";
  }
  function rendrePlanning(pl) {
    var h = "<p>Début " + esc(pl.debut) + " · fin au plus tôt <b>" + esc(pl.fin_projet.tot)
      + "</b>, au plus tard <b>" + esc(pl.fin_projet.tard) + "</b>.</p>";
    if (pl.migration) {
      h += '<p class="moe-recu">Migration de cœur en parallèle : ' + pl.migration.mois_min + " à "
        + pl.migration.mois_max + " mois (fin au plus tard " + esc(pl.migration.fin_tard) + "). "
        + esc(pl.migration.dit) + "</p>";
    }
    h += '<table class="moe-tab"><thead><tr><th>Phase</th><th>Début (tôt)</th><th>Fin (tôt)</th><th>Fin (tard)</th></tr></thead><tbody>'
      + pl.phases.map(function (p) {
          return "<tr><td>" + esc(p.nom) + "</td><td>" + esc(p.debut_tot) + "</td><td>" + esc(p.fin_tot) + "</td><td>" + esc(p.fin_tard) + "</td></tr>";
        }).join("") + "</tbody></table>";
    h += "<h4>Jalons réglementaires, replacés dans ce calendrier</h4>"
      + rendreJalons(pl.jalons_reglementaires, REF.sources, REF.etats_jalon);
    return h;
  }

  /* On ne demande pas au serveur à chaque frappe : une temporisation courte
     suffit à ce que l'état suive la saisie sans la marteler. */
  var _tempo = null;
  function rafraichirBlocs() {
    clearTimeout(_tempo);
    _tempo = setTimeout(function () {
      var corps = { quantites: lire("q"), prix: lire("p"), secteur: SECTEUR || null };
      demander("/api/ia-factory/chiffrer", { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) }, DELAI_MOYEN)
        .then(function (j) { peindreBlocs(j.blocs); }, function () { /* l'état reste tel quel */ });
    }, 500);
  }

  /* L'AVERTISSEMENT QUI TIENT LA PROMESSE DU MODULE. « Ce module ne porte
     aucun prix : il chiffre les vôtres » cesse d'être vrai à la seconde où un
     client exporte une étude bâtie sur nos ordres de grandeur sans le savoir.
     Le compte vient du SERVEUR — le recalculer ici donnerait un second
     comptage, et c'est le plus visible qui serait cru. */
  function rendreValeursDexemple(liste) {
    var aRemplacer = (liste || []).filter(function (x) { return x.a_remplacer; });
    if (!aRemplacer.length) return "";
    return '<div class="iaf-alerte" role="status"><b>'
      + aRemplacer.length + " valeur(s) sont encore un ordre de grandeur du "
      + "cabinet</b> — ce chiffrage n'est pas encore le vôtre. À remplacer par "
      + "vos devis, votre grille RH et vos marchés en cours :<ul>"
      + aRemplacer.map(function (x) {
          return "<li><b>" + esc(x.nom) + "</b> — " + esc(optionLisible(x.valeur, x.unite))
            + " <small>(" + esc(x.libelle) + ")</small></li>";
        }).join("")
      + "</ul></div>";
  }

  function chiffrer() {
    var out = $("iaf-out"), dim = $("iaf-dim"), pla = $("iaf-planning");
    out.innerHTML = "<p>Chiffrage en cours…</p>";
    var prov = $("iaf-provision").value;
    var corps = { quantites: lire("q"), prix: lire("p"), secteur: SECTEUR || null,
      provision_pct: prov === "" ? null : (+prov) / 100, debut: $("iaf-debut").value || null };
    demander("/api/ia-factory/chiffrer", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) }, DELAI_MOYEN)
      .then(function (j) {
        /* CE QUI EST RESTÉ UN EXEMPLE, AVANT LES TOTAUX ET NON APRÈS.
           Placé sous le tableau, l'avertissement arriverait après que le
           lecteur a retenu le montant — et un montant retenu ne se corrige
           plus. */
        out.innerHTML = rendreValeursDexemple(j.valeurs_dexemple)
          + rendreChiffrage(j.chiffrage, REF);
        dim.innerHTML = rendreDim(j.chiffrage.dimensionnement);
        pla.innerHTML = rendrePlanning(j.planning);
        brancherJalons(pla);
        peindreBlocs(j.blocs);
      }, function (e) { erreur(out, e); });
  }

  function init() {
    demander("/api/ia-factory", null, DELAI_COURT).then(function (j) {
      REF = j.referentiel;
      $("iaf-secteur").innerHTML = rendreSecteurs();
      brancherSecteurs();
      redessinerQuantites();
      $("iaf-p").innerHTML = champs(REF.prix, "p", REF.exemples);
      brancherExemples();
      $("iaf-cmp").innerHTML = rendreComparables(REF.comparables, REF.sources,
        REF.secteurs_comparables);
      brancherComparables();
      $("iaf-phases").innerHTML = rendrePhases(REF);
      brancherPhases();
      /* `avant_fin_projet` RESTE INCONNU ICI, et c'est la correction. Il était
         forcé à `true` : la colonne « État » annonçait donc « tombe pendant le
         projet » pour des dates que personne n'avait comparées à une fin de
         projet — il n'y en avait pas encore. Laissé nul, l'état devient
         « à venir — replacé au chiffrage », qui est ce qui est vrai. */
      $("iaf-jalons").innerHTML = rendreJalons(REF.jalons_reglementaires.map(function (x) {
        return Object.assign({}, x, {
          passe: x.date <= new Date().toISOString().slice(0, 10),
          avant_fin_projet: null });
      }), REF.sources, REF.etats_jalon);
      brancherJalons();
      $("iaf-changement").innerHTML = rendreLeviers(REF.leviers_changement, REF.sources,
        REF.ancrages, REF.soutiens_levier, "leviers", "chg");
      brancherLeviers($("iaf-changement"));
      $("iaf-migration").innerHTML = rendreLeviers(REF.principes_migration, REF.sources,
        REF.ancrages, REF.soutiens_levier, "principes", "mig");
      brancherLeviers($("iaf-migration"));
      $("iaf-sources").innerHTML = rendreSources(REF.sources, REF.couverture_sources);
      brancherSources();
      $("iaf-limite").textContent = REF.limite;
      $("iaf-go").addEventListener("click", chiffrer);
      $("iaf-debut").value = new Date().toISOString().slice(0, 10);
      luCharger();
      peindreBlocs(null);
      /* Le secteur et la saisie changent l'état des blocs sans qu'on chiffre :
         on redemande au serveur, qui reste seul juge des critères. */
      document.addEventListener("input", function (e) {
        if (e.target && e.target.dataset && e.target.dataset.famille) rafraichirBlocs();
      });
      guideRendre();
      $("iaf-guide-b").addEventListener("click", function () {
        guideOuvrir($("iaf-guide").hidden);
      });
    }, function (e) { erreur($("iaf-q"), e); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
