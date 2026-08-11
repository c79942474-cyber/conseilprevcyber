"""QUI VOIT QUOI — la politique d'accès du site, écrite une fois.

LA RÈGLE, telle qu'elle a été arrêtée :

  · les pages du menu latéral demandent un compte client — inscription,
    confirmation de l'adresse par le client lui-même, puis validation par
    l'administrateur, qui en est averti par courriel ;
  · DIX pages restent en accès direct : services, secteurs, études de cas,
    veille cyber, ressources, FAQ, accueil, à propos, vos projets, contact ;
  · l'administrateur atteint tout le site, sans exception.

POURQUOI UNE LISTE, ET NON QUARANTE-TROIS DÉCORATEURS QU'ON RELIT UN PAR UN.
La protection était jusqu'ici posée route par route, et elle avait dérivé sans
que personne puisse le voir : /ressources et /vos-projets demandaient un compte
alors qu'ils devaient être ouverts, quatorze autres pages étaient ouvertes alors
qu'elles ne devaient pas l'être. Personne n'avait fauté — simplement, un état
réparti sur quarante-trois décorateurs ne se lit pas, donc ne se vérifie pas.
Ici, la politique tient sur un écran et se lit en entier.

CE QUI FAIT QUE CETTE LISTE NE MENT PAS. Déclarer une politique dans un fichier
que personne n'applique serait pire que pas de politique : on croirait le site
protégé. `verifier_application()` compare donc, AU DÉMARRAGE, la protection
RÉELLE de chaque route à ce qui est déclaré ici, et empêche l'application de
démarrer en cas d'écart. Une page ajoutée sans décision ne démarre pas non plus
— c'est voulu : un oubli doit se voir au premier lancement, pas au premier
visiteur qui lit ce qu'il n'aurait pas dû lire.

CE QUI RESTE OUVERT SANS ÊTRE DANS LE MENU, et pourquoi ce n'est pas un trou :
la connexion et l'inscription (les fermer rendrait impossible d'obtenir un
compte), les mentions légales, la politique de confidentialité et la page de
conformité (leur accès est une obligation légale, et les enfermer derrière un
compte reviendrait à exiger un compte pour lire ses propres droits), le point de
santé, le plan du site et les fichiers servis à toute page.
"""

# ── Ce qui reste en accès direct, dans les mots de la décision ─────────────
# La deuxième colonne n'est pas décorative : c'est elle qui permet de relire
# cette liste à voix haute devant la décision d'origine et de constater qu'elles
# disent la même chose.
DIRECT = {
    "/services": "Services",
    "/secteurs": "Secteurs",
    "/etudes-de-cas": "Études de cas",
    "/veille": "Veille cyber",
    "/ressources": "Ressources",
    "/faq": "FAQ",
    "/": "Accueil",
    "/about": "À propos",
    "/vos-projets": "Vos projets",
    "/contact": "Contact",
}

# ── Ouvert par nécessité, hors menu ────────────────────────────────────────
# Chaque entrée porte SA raison. Une liste d'exceptions sans motif finit par
# accueillir n'importe quoi : c'est le motif écrit qui rend une nouvelle
# exception coûteuse à ajouter, donc rare.
HORS_MENU_OUVERT = {
    "/connexion": "sans elle, aucun compte ne peut servir",
    "/inscription": "sans elle, aucun compte ne peut être demandé",
    "/mot-de-passe-oublie": "un mot de passe perdu enfermerait le client dehors",
    "/mentions-legales": "obligation légale",
    "/politique-confidentialite": "obligation légale",
    "/conformite": "RGPD et AI Act : exiger un compte pour lire ses droits "
                   "serait contradictoire",
    "/health": "sonde de l'hébergeur",
    "/robots.txt": "lu par les moteurs, sans session",
    "/sitemap.xml": "lu par les moteurs, sans session",
}

# Réservé à l'administrateur — inchangé, rappelé ici pour que la politique se
# lise en entier au même endroit.
PREFIXE_ADMIN = "/admin"


# ── LES INTERFACES DE PROGRAMMATION, ET POURQUOI ELLES DÉCIDENT DE TOUT ─────
#
# Fermer une page sans fermer l'interface qui la nourrit ne protège RIEN : la
# page renvoie vers le formulaire de connexion, et le même contenu se récupère
# en une ligne de commande sur l'adresse en /api. C'est le défaut qu'on
# trouvait ici : quatorze interfaces servaient en clair le calcul, l'état de
# l'art, les lacunes et l'assistant des pages qu'on venait de fermer.
#
# LA RÈGLE EST DONC INVERSÉE : toute interface est fermée, sauf celles listées
# ci-dessous avec leur motif. Une interface ajoutée sans décision est fermée
# par défaut — au pire elle gêne un développement, jamais elle ne laisse fuir.
API_OUVERTES = {
    "/api/auth/captcha": "l'anti-robot précède la création du compte",
    "/api/auth/register": "sans elle, aucun compte ne peut être demandé",
    "/api/auth/login": "sans elle, aucun compte ne peut servir",
    "/api/auth/logout": "se déconnecter ne doit jamais échouer",
    "/api/auth/me": "dit à la page si l'on est connecté — y compris « non »",
    "/api/auth/forgot": "un mot de passe perdu enfermerait le client dehors",
    "/api/auth/reset": "idem, second temps",
    "/api/acces": "dit quelles pages demandent un compte — c'est ce qui permet "
                  "de le SIGNALER avant le clic, et rien n'y est secret : le "
                  "visiteur l'apprendrait de toute façon en cliquant",
    "/api/veille": "nourrit /veille, en accès direct",
    "/api/conformite": "nourrit /conformite : obligation légale",
    "/api/contact": "le formulaire de contact doit marcher sans compte",
}

# Protégées par un jeton d'en-tête plutôt que par une session : ce sont des
# échanges de serveur à serveur, sans navigateur ni cookie. Les soumettre à une
# session les casserait sans rien protéger de plus.
API_JETON = {
    "/api/ingest": "INGEST_TOKEN — télémétrie du cockpit",
    "/api/reset": "INGEST_TOKEN — remise à zéro du cockpit",
    "/api/maintenance/purge": "INGEST_TOKEN — élagage de l'historique",
    "/api/rag/ingest": "jeton d'ingestion documentaire",
}


def api_statut(chemin):
    """Ce qu'une interface DOIT être : « direct », « jeton » ou « client »."""
    if chemin.startswith("/api/admin/"):
        return "admin"
    if chemin in API_OUVERTES:
        return "direct"
    if chemin in API_JETON:
        return "jeton"
    return "client"


def statut(chemin):
    """« direct », « client » ou « admin » — pour un chemin de page du site."""
    if chemin == PREFIXE_ADMIN or chemin.startswith(PREFIXE_ADMIN + "/"):
        return "admin"
    if chemin in DIRECT or chemin in HORS_MENU_OUVERT:
        return "direct"
    return "client"


def ouvert(chemin):
    return statut(chemin) == "direct"


def verifier_api(reelles):
    """Toute interface est fermée, sauf motif écrit. Rend les écarts, en clair.

    `reelles` : {chemin: "direct" | "client" | "admin"} relevé sur les
    décorateurs. Les interfaces à jeton se présentent comme « direct » — elles
    n'ont pas de décorateur de session — et c'est pour cela qu'elles doivent
    être nommées : sans la liste, on ne les distingue pas d'un oubli."""
    ecarts = []
    for chemin, reel in sorted(reelles.items()):
        attendu = api_statut(chemin)
        if attendu == "jeton":
            if reel != "direct":
                ecarts.append("%s : déclarée à jeton mais protégée par session "
                              "(« %s ») — le serveur appelant n'a pas de "
                              "cookie" % (chemin, reel))
        elif attendu == "client" and reel == "direct":
            ecarts.append("%s est ouverte : fermer la page sans fermer son "
                          "interface ne protège rien" % chemin)
        elif attendu == "direct" and reel != "direct":
            ecarts.append("%s est fermée alors qu'elle doit rester ouverte (%s)"
                          % (chemin, API_OUVERTES[chemin]))
    return ecarts


def verifier_application(reelles, menu):
    """Compare la protection RÉELLE des routes à la politique déclarée.

    `reelles` : {chemin: "direct" | "client" | "admin"}, relevé sur les
    décorateurs effectivement posés.
    `menu`    : les chemins que le menu latéral propose.

    Rend la liste des écarts, en clair. Vide = la politique est appliquée.

    POURQUOI LE MENU ENTRE ICI. La règle porte sur « les pages du menu
    latéral » : c'est donc le menu qui dit ce qui doit être décidé. Une entrée
    de menu sans route, ou une route de menu sans décision, sont l'une et
    l'autre des écarts — et la seconde est celle qui laisse passer.
    """
    ecarts = []

    for chemin in sorted(menu):
        if chemin not in reelles:
            ecarts.append("%s est au menu mais n'a pas de route" % chemin)
            continue
        attendu, reel = statut(chemin), reelles[chemin]
        if attendu != reel:
            ecarts.append("%s : la politique dit « %s », la route applique "
                          "« %s »" % (chemin, attendu, reel))

    for chemin, reel in sorted(reelles.items()):
        if chemin in menu:
            continue
        attendu = statut(chemin)
        # Hors menu, seul le SENS INVERSE est une faute : une page ouverte que
        # la politique voudrait fermée laisse lire ce qui ne doit pas l'être.
        # Une page fermée que la politique croit ouverte est un choix plus
        # strict, jamais une fuite — on le laisse passer plutôt que d'obliger à
        # inscrire ici chaque fichier servi.
        if attendu == "client" and reel == "direct":
            ecarts.append("%s est ouverte alors que la politique la ferme"
                          % chemin)

    return ecarts


def _verifier():
    """La politique doit dire ce que la décision disait — sinon, rien ne part.

    Les DIX pages en accès direct ont été énumérées une par une. Une liste qui
    en perdrait une au fil d'une modification fermerait une page qui devait
    rester ouverte, et personne ne s'en apercevrait avant qu'un visiteur se
    heurte à un formulaire de connexion sur la page « Contact »."""
    attendues = {"/services", "/secteurs", "/etudes-de-cas", "/veille",
                 "/ressources", "/faq", "/", "/about", "/vos-projets",
                 "/contact"}
    if set(DIRECT) != attendues:
        manquantes = sorted(attendues - set(DIRECT))
        ajoutees = sorted(set(DIRECT) - attendues)
        raise RuntimeError(
            "acces : l'accès direct ne correspond plus à la décision — "
            "manquantes %s, ajoutées %s" % (manquantes, ajoutees))
    if any(not lib.strip() for lib in DIRECT.values()):
        raise RuntimeError("acces : une page en accès direct sans libellé")
    if any(not motif.strip() for motif in HORS_MENU_OUVERT.values()):
        raise RuntimeError(
            "acces : une exception hors menu sans motif écrit — c'est le motif "
            "qui rend une exception coûteuse à ajouter, donc rare")
    for chemin in list(DIRECT) + list(HORS_MENU_OUVERT):
        if not chemin.startswith("/"):
            raise RuntimeError("acces : chemin mal formé — %r" % chemin)
    if set(DIRECT) & set(HORS_MENU_OUVERT):
        raise RuntimeError("acces : une page déclarée deux fois — %s"
                           % sorted(set(DIRECT) & set(HORS_MENU_OUVERT)))


_verifier()
