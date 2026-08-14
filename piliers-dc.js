/* LES TROIS PILIERS CENTRES DE DONNÉES — un chemin, trois pages.
   ═══════════════════════════════════════════════════════════════════════════

   CE QU'IL RÉSOUT. Trois pages traitent le même projet sous trois angles : ce
   qu'on VISE, ce qu'on MESURE, ce qu'on ENGAGE. Elles se citaient de loin en
   loin — et pas toutes : /ingenierie-datacenter ne renvoyait pas une seule
   fois vers la stratégie. Rien ne disait dans quel ORDRE les prendre, ce que
   chacune attend de la précédente, ni où l'on en était. Trois outils voisins
   qu'on croit interchangeables, alors qu'ils s'enchaînent.

   L'ORDRE N'EST PAS UN GOÛT DE PRÉSENTATION :

     1. STRATÉGIE — ce qu'on vise. Elle décide quels enjeux comptent. Sans
        elle, on mesure tout au même titre et on ne priorise rien.
     2. MESURE — ce qu'on prouve. Énergie, eau, carbone, chiffrés ensemble.
        Elle a besoin de savoir ce qu'on vise pour dire ce qui manque.
     3. INGÉNIERIE — ce qu'on engage. À quelle phase un chiffre devient
        opposable, quelles pièces le portent, ce que coûte la maîtrise
        d'œuvre. Elle consomme les chiffres du pilier 2.

   ══ CE QUE CE BANDEAU N'INVENTE PAS ══

   IL NE TRANSPORTE QUE CE QUI EXISTE DÉJÀ. Le profil d'installation circule
   entre la mesure et l'ingénierie depuis `ProfilDC` — treize valeurs, les
   mêmes champs, le même référentiel. Ce bandeau le SIGNALE, il ne le refait
   pas.

   ET IL NE FABRIQUE PAS DE PASSAGE ENTRE LA STRATÉGIE ET LA MESURE. Le
   questionnaire de stratégie pose des questions QUALITATIVES — stress
   hydrique du bassin, proximité des habitations, maturité de l'organisation.
   La mesure attend des GRANDEURS — puissance installée, PUE cible, part
   évaporative. Traduire « stress hydrique élevé » en un nombre reviendrait à
   inventer une donnée et à la faire entrer dans un calcul, ce que tout ce
   site s'interdit. Ce qui passe d'un pilier à l'autre est donc une
   DÉSIGNATION, pas une valeur : la stratégie dit quels enjeux comptent, le
   bandeau dit où, sur le pilier suivant, ces enjeux se chiffrent.

   L'AVANCEMENT EST CONSTATÉ. « Fait » se lit sur ce qui est réellement en
   magasin, jamais sur une visite. Passer sur une page ne la remplit pas.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  /* Le résumé de la stratégie : un COMPTE, pas des réponses. Ce qui est noté
     reste sur sa page ; ce bandeau n'a besoin que de savoir s'il y a matière.
     sessionStorage, comme le profil : un projet en cours est une session de
     travail, pas une préférence — fermer l'onglet l'efface. */
  var CLE_STRAT = "cp_strategie_dc";

  var PILIERS = [
    {
      url: "/strategie-durable-datacenter",
      nom: "Stratégie",
      titre: "Stratégie durable",
      question: "Qu’est-ce qu’on vise, et quels enjeux comptent&nbsp;?",
      donne: "les enjeux retenus, et l’ordre dans lequel les traiter",
    },
    {
      url: "/datacenter",
      nom: "Mesure",
      titre: "Durabilité &amp; décarbonation",
      question: "Qu’est-ce qu’on prouve, et avec quelle incertitude&nbsp;?",
      donne: "le profil d’installation et les grandeurs calculées",
    },
    {
      url: "/ingenierie-datacenter",
      nom: "Ingénierie",
      titre: "Ingénierie de projet",
      question: "Qu’est-ce qu’on engage, et à quelle phase&nbsp;?",
      donne: "les pièces à produire et le prix de la maîtrise d’œuvre",
    },
  ];

  function ici() {
    var p = location.pathname.replace(/\/+$/, "") || "/";
    for (var i = 0; i < PILIERS.length; i++) {
      if (PILIERS[i].url === p) return i;
    }
    return -1;
  }

  /* ── CE QUI EST FAIT, LU EN MAGASIN ─────────────────────────────────── */

  function strategieFaite() {
    try {
      var b = window.sessionStorage.getItem(CLE_STRAT);
      if (!b) return null;
      var o = JSON.parse(b);
      return o && o.notes > 0 ? o : null;
    } catch (e) { return null; }
  }

  /* ON COMPTE LES CHAMPS DU PROFIL, PAS LES CLÉS DE SON ENVELOPPE. `lire()`
     rend `{champs, origine, quand}` : parcourir cet objet donnait toujours
     trois, quel que soit le nombre de valeurs réellement portées. Le bandeau
     annonçait donc « 3 valeurs » sur un profil qui en comptait sept — un
     chiffre faux, et faux dans le sens qui rassure. */
  function profilFait() {
    if (!window.ProfilDC || !window.ProfilDC.disponible) return null;
    try {
      var v = window.ProfilDC.lire();
      if (!v || !v.champs) return null;
      var n = 0;
      for (var k in v.champs) {
        if (String(v.champs[k]).trim() !== "") n++;
      }
      return n ? { champs: n } : null;
    } catch (e) { return null; }
  }

  function etat(i) {
    if (i === 0) return strategieFaite() ? "fait" : "vide";
    if (i === 1) return profilFait() ? "fait" : "vide";
    /* L'INGÉNIERIE NE SE DÉCLARE JAMAIS « FAITE ». Elle ne produit pas un
       jeu de valeurs qu'on retrouverait en magasin : elle rend un dossier de
       phase, qu'on emporte. Lui inventer un état « fait » ferait dire au
       bandeau une chose qu'il ne peut pas constater. */
    return "ouvert";
  }

  /* ── CE QUI PASSE AU PILIER SUIVANT, ET SEULEMENT S'IL Y A MATIÈRE ──── */
  function passage(i) {
    if (i === 0) {
      var s = strategieFaite();
      if (!s) return null;
      return "Vous avez noté <b>" + s.notes + " enjeu" + (s.notes > 1 ? "x" : "")
        + "</b> sur cette stratégie. La mesure ne les reprend pas comme des "
        + "valeurs — ce sont des jugements, pas des grandeurs — mais elle "
        + "chiffre ce qu’ils désignent&nbsp;: énergie, eau et carbone.";
    }
    if (i === 1) {
      var p = profilFait();
      if (!p) return null;
      return "Votre profil d’installation est retenu&nbsp;: <b>" + p.champs
        + " valeur" + (p.champs > 1 ? "s" : "") + "</b>. L’ingénierie le "
        + "reprend telle quelle — aucun champ n’est à ressaisir, et un champ "
        + "resté par défaut ici le reste là-bas.";
    }
    return null;
  }

  function carte(p, i, courant) {
    var e = etat(i);
    var actuel = i === courant;
    var b = actuel ? "div" : "a";
    return "<" + b + ' class="pdc-c' + (actuel ? " on" : "") + '"'
      + (actuel ? ' aria-current="page"' : ' href="' + p.url + '"')
      + "><span class=\"r\">" + (i + 1) + "</span>"
      + '<span class="t">' + p.titre + "</span>"
      + '<span class="q">' + p.question + "</span>"
      + '<span class="e ' + e + '">'
      + (e === "fait" ? "✓ renseigné"
        : e === "ouvert" ? "à parcourir" : "rien de saisi") + "</span>"
      + "</" + b + ">";
  }

  function rendre() {
    var z = document.getElementById("piliers");
    if (!z) return;
    var c = ici();
    if (c < 0) return;

    var h = '<nav class="pdc" aria-label="Les trois piliers centres de données">'
      + '<p class="pdc-t">Trois piliers, dans cet ordre&nbsp;: on décide ce '
      + 'qu’on vise, on le chiffre, puis on l’engage. Vous êtes sur le '
      + "pilier " + (c + 1) + ".</p>"
      + '<div class="pdc-l">';
    for (var i = 0; i < PILIERS.length; i++) {
      if (i) h += '<span class="pdc-fl" aria-hidden="true">→</span>';
      h += carte(PILIERS[i], i, c);
    }
    h += "</div>";

    /* CE QUI SE TRANSMET, DIT AU MOMENT OÙ IL SE TRANSMET. Affiché sur le
       pilier qui le PRODUIT, il vanterait une promesse ; affiché sur celui
       qui le REÇOIT, il constate. On le pose donc des deux côtés, mais avec
       deux phrases différentes — « voici ce que vous emportez » d'un côté,
       « voici ce qui a été repris » de l'autre. */
    var av = c > 0 ? passage(c - 1) : null;
    if (av) {
      h += '<p class="pdc-p recu"><b>Repris du pilier ' + c + "&nbsp;:</b> "
        + av + "</p>";
    }
    var ap = passage(c);
    if (ap && c < PILIERS.length - 1) {
      h += '<p class="pdc-p emporte"><b>Ce que vous emportez au pilier '
        + (c + 2) + "&nbsp;:</b> " + ap + "</p>";
    } else if (!ap && c < PILIERS.length - 1) {
      /* À QUELLE CONDITION LE REPORT AURA LIEU. Sans cette ligne, le lecteur
         qui a rempli tout le formulaire de mesure sans lancer le calcul lit
         « rien de saisi » et n'a aucun moyen de savoir ce qui manque : le
         profil n'est retenu qu'APRÈS un calcul réussi — un profil qui n'a rien
         produit ici n'a pas de raison d'être proposé ailleurs. La règle est
         bonne ; c'est de la taire qui ne l'était pas. */
      h += '<p class="pdc-p attente"><b>Rien à emporter pour l’instant.</b> '
        + (c === 0
            ? "Notez au moins un enjeu&nbsp;: le pilier suivant saura alors "
              + "quelles grandeurs vous regardez en premier."
            : "Le profil d’installation n’est retenu qu’une fois <b>l’étude "
              + "calculée</b> — renseigner le formulaire ne suffit pas, et "
              + "c’est voulu&nbsp;: un profil qui n’a rien produit ici n’a pas "
              + "à être proposé ailleurs.")
        + "</p>";
    }

    /* LE GESTE SUIVANT, UN SEUL. Trois liens à égalité ne disent pas par où
       continuer ; ce bouton dit ce qu'on va y faire, pas seulement où l'on
       va. Sur le dernier pilier, il ramène au premier — le chemin se
       reparcourt à chaque phase du projet, il ne se termine pas. */
    var suiv = PILIERS[(c + 1) % PILIERS.length];
    var boucle = c === PILIERS.length - 1;
    h += '<div class="pdc-go"><a class="pdc-b" href="' + suiv.url + '">'
      + (boucle ? "Revenir à la stratégie" : "Continuer vers&nbsp;: " + suiv.titre)
      + "</a><span>" + (boucle
        ? "Une phase franchie change ce qu’on vise&nbsp;: le chemin se "
          + "reparcourt, il ne se termine pas."
        : "Vous y trouverez&nbsp;: " + suiv.donne + ".") + "</span></div>";

    h += "</nav>";
    z.innerHTML = h;
  }

  function demarrer() {
    rendre();
    /* LE BANDEAU SUIT LA SAISIE. Le profil s'enregistre au fil du formulaire :
       sans cela, « rien de saisi » resterait affiché sous les yeux de
       quelqu'un qui vient précisément de tout remplir. */
    document.addEventListener("change", function () { rendre(); });
    /* Et il écoute le magasin lui-même : le profil s'écrit au retour du
       calcul, sans qu'aucune commande ne bouge. */
    document.addEventListener("profil-dc:ecrit", function () { rendre(); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }

  /* Exposé pour la page de stratégie — qui seule sait combien d'enjeux ont
     été notés — et pour la recette, qui doit lire ce que le bandeau a DÉDUIT
     plutôt que de le redéduire elle-même. */
  window.PiliersDC = {
    noterStrategie: function (n, total) {
      try {
        if (!n) { window.sessionStorage.removeItem(CLE_STRAT); }
        else {
          window.sessionStorage.setItem(CLE_STRAT,
            JSON.stringify({ notes: n, total: total || 0 }));
        }
      } catch (e) { /* mode privé : le bandeau dira simplement « rien de saisi » */ }
      rendre();
    },
    etat: etat, ici: ici, piliers: PILIERS, rendre: rendre,
  };
})();
