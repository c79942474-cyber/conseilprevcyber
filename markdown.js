/* Rendu Markdown léger — titres, gras, italique, code, listes, tableaux, hr.

   POURQUOI UN FICHIER À PART. Le même rendu sert à deux endroits : la console
   d'administration des livrables, et la lecture d'une pièce d'ingénierie. Il
   était écrit dans la console ; le recopier ailleurs aurait donné deux
   moteurs de rendu qui divergent au premier tableau mal aligné, et le même
   document se lirait différemment selon la page qui l'affiche.

   CE QU'IL FAIT, ET CE QU'IL NE FAIT PAS. Il rend ce que nos documents
   contiennent réellement — c'est un générateur maison, pas du Markdown venu
   d'ailleurs. Pas de HTML brut : tout passe par l'échappement, y compris à
   l'intérieur des tableaux. Un document reste un texte à lire, jamais du code
   à exécuter.

   Exposé en global (window.CPMarkdown) plutôt qu'en module : les pages qui
   l'utilisent sont des scripts classiques, et un module imposerait un
   chargement différé qui ferait clignoter le document au premier affichage. */
(function (global) {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function inline(s) {
    return esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
      /* Les liens ne s'ouvrent qu'en http(s) et jamais dans l'onglet courant :
         un document rédigé ailleurs ne doit pas pouvoir remplacer la page. */
      .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g,
               '<a href="$2" target="_blank" rel="noopener">$1</a>');
  }

  function versHtml(md) {
    var lignes = String(md || "").replace(/\r/g, "").split("\n");
    var out = [], i = 0;

    function liste(tag, items) {
      if (items.length) {
        out.push("<" + tag + ">" + items.map(function (x) {
          return "<li>" + inline(x) + "</li>";
        }).join("") + "</" + tag + ">");
      }
    }

    while (i < lignes.length) {
      var ln = lignes[i];
      if (/^\s*$/.test(ln)) { i++; continue; }

      var h = ln.match(/^(#{1,6})\s+(.*)$/);
      if (h) {
        var lvl = Math.min(h[1].length, 3);
        out.push("<h" + lvl + ">" + inline(h[2]) + "</h" + lvl + ">");
        i++;
        continue;
      }
      if (/^\s*([-*_])\1{2,}\s*$/.test(ln)) { out.push("<hr>"); i++; continue; }

      /* Tableau : ligne d'en-tête PUIS ligne de séparation. Sans exiger les
         deux, une simple phrase contenant une barre verticale se retrouvait
         rendue en tableau d'une colonne. */
      if (/^\s*\|.*\|\s*$/.test(ln) && i + 1 < lignes.length
          && /^\s*\|?[\s:|-]+\|?\s*$/.test(lignes[i + 1])
          && lignes[i + 1].indexOf("-") >= 0) {
        var tete = ln.trim().replace(/^\||\|$/g, "").split("|")
          .map(function (c) { return c.trim(); });
        i += 2;
        var rangs = [];
        while (i < lignes.length && /^\s*\|.*\|\s*$/.test(lignes[i])) {
          rangs.push(lignes[i].trim().replace(/^\||\|$/g, "").split("|")
            .map(function (c) { return c.trim(); }));
          i++;
        }
        /* Enveloppe défilante : un tableau large ne doit pas élargir la page —
           sinon c'est tout le document qui défile de côté. */
        var t = '<div class="tblx"><table><thead><tr>'
          + tete.map(function (c) { return "<th>" + inline(c) + "</th>"; }).join("")
          + "</tr></thead><tbody>";
        t += rangs.map(function (r) {
          return "<tr>" + r.map(function (c) {
            return "<td>" + inline(c) + "</td>";
          }).join("") + "</tr>";
        }).join("");
        out.push(t + "</tbody></table></div>");
        continue;
      }

      if (/^\s*[-*]\s+/.test(ln)) {
        var it = [];
        while (i < lignes.length && /^\s*[-*]\s+/.test(lignes[i])) {
          it.push(lignes[i].replace(/^\s*[-*]\s+/, ""));
          i++;
        }
        liste("ul", it);
        continue;
      }
      if (/^\s*\d+[.)]\s+/.test(ln)) {
        var it2 = [];
        while (i < lignes.length && /^\s*\d+[.)]\s+/.test(lignes[i])) {
          it2.push(lignes[i].replace(/^\s*\d+[.)]\s+/, ""));
          i++;
        }
        liste("ol", it2);
        continue;
      }

      /* Citation : nos documents s'en servent pour les extraits reproduits
         tels quels et pour l'avertissement de tête. Rendus en paragraphe, ils
         se confondaient avec le texte du rédacteur — c'est-à-dire qu'on ne
         voyait plus ce qui était cité. */
      if (/^\s*>\s?/.test(ln)) {
        var cite = [];
        while (i < lignes.length && /^\s*>\s?/.test(lignes[i])) {
          cite.push(lignes[i].replace(/^\s*>\s?/, ""));
          i++;
        }
        out.push("<blockquote>"
          + cite.filter(function (x) { return x.trim(); })
              .map(function (x) { return "<p>" + inline(x) + "</p>"; }).join("")
          + "</blockquote>");
        continue;
      }

      var para = [ln];
      i++;
      while (i < lignes.length && !/^\s*$/.test(lignes[i])
             && !/^(#{1,6}\s|\s*[-*]\s|\s*\d+[.)]\s|\s*\||\s*>)/.test(lignes[i])) {
        para.push(lignes[i]);
        i++;
      }
      out.push("<p>" + inline(para.join(" ")) + "</p>");
    }
    return out.join("\n");
  }

  /* Ce que pèse un document, en unités de lecteur. « 41 200 signes » ne dit
     rien ; « environ 12 pages » dit s'il se lit maintenant ou plus tard. */
  function mesurer(md) {
    var t = String(md || "");
    var signes = t.length;
    return {
      signes: signes,
      mots: (t.match(/\S+/g) || []).length,
      // 2 500 signes par page : l'ordre de grandeur d'une page A4 rédigée,
      // interlignes et titres compris.
      pages: Math.max(1, Math.round(signes / 2500)),
      chapitres: (t.match(/^##\s+/gm) || []).length,
      tableaux: (t.match(/^\|[^\n]*\|\s*$/gm) || []).length ? 1 : 0,
    };
  }

  global.CPMarkdown = { versHtml: versHtml, inline: inline, esc: esc,
                        mesurer: mesurer };
})(window);
