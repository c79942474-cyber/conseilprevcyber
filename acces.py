"""QUI VOIT QUOI — la politique d'accès du site, écrite une fois.

LA RÈGLE, telle qu'elle a été arrêtée :

  · les pages du menu latéral demandent un compte client — inscription,
    confirmation de l'adresse par le client lui-même, puis validation par
    l'administrateur, qui en est averti par courriel ;
  · ONZE pages restent en accès direct : services, secteurs, études de cas,
    veille cyber, ressources, FAQ, accueil, à propos, vos projets, contact —
    et « obtenir un accès », ajoutée le jour où l'on s'est aperçu qu'aucun
    visiteur ne pouvait trouver ce qu'il devait acheter ;
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
    # ONZIÈME PAGE OUVERTE, ET LA DÉCISION EST ÉCRITE ICI. Le site vendait un
    # accès sans jamais dire ce qu'il ouvrait ni ce qu'il coûtait : le seul
    # chemin vers la caisse passait par /connexion, donc supposait d'avoir
    # déjà un compte confirmé — ce qu'un acheteur n'a pas. Fermer la page qui
    # vend l'accès derrière l'accès ne protège rien et n'ouvre rien.
    "/acces": "Obtenir un accès",
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

    # ── L'OUVERTURE DU 2 SEPTEMBRE 2026 ────────────────────────────────────
    # LE SITE S'OUVRE, SAUF L'INGÉNIERIE DE PROJET DATA CENTER. Trente et une
    # pages passent en accès direct ; il en reste TROIS derrière le compte —
    # /strategie-durable-datacenter, /datacenter, /ingenierie-datacenter — et
    # ce sont désormais elles, et elles seules, que l'accès vendu ouvre.
    #
    # CE QUE CETTE DÉCISION COÛTE, ÉCRIT ICI PLUTÔT QUE DÉCOUVERT PLUS TARD :
    # ce qui était vendu trente-quatre pages en vaut trois. Les conditions de
    # vente, la page qui vend l'accès et le périmètre calculé doivent le dire
    # ensemble — un site qui vend ce qu'il vient de donner ne trompe pas
    # seulement l'acheteur, il rend la vente attaquable.
    #
    # LA LISTE RESTE BLANCHE, ET C'EST DÉLIBÉRÉ. L'inverser — « tout est
    # ouvert sauf… » — serait plus court de trente lignes et changerait le sens
    # de l'oubli : une page ajoutée sans décision serait OUVERTE. Ici elle
    # reste fermée. Au pire elle gêne un développement, jamais elle ne laisse
    # fuir — la même règle que pour les interfaces, et pour la même raison.
    # Expertise
    "/methodologie": "Méthodologie",
    # Conseil & transformation
    "/operating-model": "Operating Model & gouvernance",
    "/maturite-ot": "Assessment de maturité",
    "/feuille-de-route": "Feuille de route",
    "/continuite-ot": "Continuité & crise OT",
    "/gestion-des-changements": "Gestion des changements (MOC)",
    "/architecture-cible": "Architecture cible OT",
    "/formation": "Formation & compétences",
    "/gouvernance-ia": "Governance by Design IA",
    "/relecture-contrat": "Relecture de contrats assistée",
    # Référentiel IEC 62443
    "/referentiel": "Vue d’ensemble",
    "/analyse-de-risque": "Analyse de risque · 3-2",
    "/programme-securite": "Programme de sécurité · 2-1",
    "/exigences-systeme": "Exigences système · 3-3",
    "/exigences-composants": "Exigences composants · 4-2",
    "/exigences-prestataires": "Exigences prestataires · 2-4",
    "/developpement-securise": "Développement sécurisé · 4-1",
    "/technologies-securite": "Technologies · TR 3-1",
    "/gestion-correctifs": "Gestion des correctifs · 2-3",
    "/glossaire-62443": "Glossaire · 1-2",
    "/metriques-62443": "Métriques · 1-3",
    "/checklist-62443": "Liste de vérification",
    # Conformité & audit
    "/audit-conformite": "Audit 62443",
    "/diagnostic": "Diagnostic express",
    "/nis2": "NIS2",
    "/juridique": "Conseil juridique",
    # Plateforme
    "/demo": "Cockpit de supervision",
    "/tendances": "Tendances",
    "/connecter": "Connecter une source",
    "/guide-integration": "Guide d’intégration",
    "/assistant": "Assistant IA",
}

# ── Ouvert par nécessité, hors menu ────────────────────────────────────────
# Chaque entrée porte SA raison. Une liste d'exceptions sans motif finit par
# accueillir n'importe quoi : c'est le motif écrit qui rend une nouvelle
# exception coûteuse à ajouter, donc rare.
HORS_MENU_OUVERT = {
    "/connexion": "sans elle, aucun compte ne peut servir",
    "/inscription": "sans elle, aucun compte ne peut être demandé",
    "/mot-de-passe-oublie": "un mot de passe perdu enfermerait le client dehors",
    "/cgv": "obligation légale — des conditions de vente inaccessibles avant "
            "l'achat ne sont pas opposables à l'acheteur",
    "/mentions-legales": "obligation légale",
    "/politique-confidentialite": "obligation légale",
    "/conformite": "RGPD et AI Act : exiger un compte pour lire ses droits "
                   "serait contradictoire",
    "/health": "sonde de l'hébergeur",
    "/robots.txt": "lu par les moteurs, sans session",
    "/sitemap.xml": "lu par les moteurs, sans session",
    # LE FLUX SORTANT DE LA VEILLE. Il ne rend que ce que la page publique rend
    # déjà — titres, liens vers les sources, et notre classement. Le fermer
    # n'aurait rien protégé et l'aurait rendu inutile : un flux dont il faut un
    # compte n'est pas un flux.
    "/veille.xml": "flux de veille, lu par les agrégateurs sans session",
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
    "/api/acces/perimetre": "nourrit /acces, la page qui vend l'accès : elle "
                            "doit pouvoir dire ce qu'elle vend. Ce sont les "
                            "entrées du tiroir, que tout visiteur voit déjà",
    "/api/veille": "nourrit /veille, en accès direct",

    # ── LES INTERFACES DES PAGES OUVERTES LE 2 SEPTEMBRE 2026 ──────────────
    # OUVRIR UNE PAGE SANS OUVRIR CE QUI LA NOURRIT NE L'OUVRE PAS : elle
    # s'affiche vide, ses boutons répondent 401, et le visiteur conclut que le
    # site est cassé plutôt qu'il n'a pas le droit. C'est le défaut symétrique
    # de celui que ce fichier corrigeait — quatorze interfaces servaient en
    # clair le contenu de pages fermées ; ici il faut ouvrir en même temps,
    # sous peine d'une ouverture qui n'en est pas une.
    #
    # CE QUE CELA EXPOSE, DIT SANS DÉTOUR. Trois de ces familles appellent un
    # MODÈLE DE LANGAGE facturé à l'usage — l'assistant, la relecture de
    # contrats, l'analyse juridique. Les ouvrir, c'est accepter qu'un visiteur
    # anonyme dépense ce budget. Chacune porte déjà une limite par adresse IP
    # (vingt appels par dix minutes pour l'assistant, vingt-cinq pour la
    # relecture, douze pour l'analyse juridique) : la dépense est bornée par
    # visiteur, pas par le nombre de visiteurs. C'est un arbitrage assumé, pas
    # un oubli — et le premier endroit où regarder si la facture surprend.
    "/api/62443/checklist": "la liste de vérification 62443, page ouverte",
    "/api/62443/checklist/compter": "le décompte de cette même liste",
    "/api/62443/checklist/emporter": "l'export de cette même liste",
    "/api/62443/checklist/parcours": "le parcours guidé de cette même liste",
    "/api/maturite-ot/referentiel": "le référentiel de l'assessment de maturité",
    "/api/maturite-ot/evaluer": "le calcul de l'assessment de maturité",
    "/api/maturite-ot/emporter": "l'export de l'assessment de maturité",
    "/api/state": "l'état du cockpit — données SIMULÉES en mode démonstration",
    "/api/assets": "les actifs du cockpit — mêmes données simulées",
    "/api/trends": "les tendances, nourries du même modèle",
    "/api/stream": "le flux temps réel du cockpit",
    "/api/assistant/config": "dit à la page ce que l'assistant sait faire",
    "/api/chat": "l'assistant lui-même — MODÈLE FACTURÉ, borné à 20 appels "
                 "par IP et par dix minutes",
    "/api/juridique/config": "dit à la page ce que l'analyse juridique propose",
    "/api/juridique/corpus": "le corpus consultable de la page juridique",
    "/api/juridique/clausier": "le clausier de la page juridique",
    "/api/juridique/instances": "les instances suivies par la page juridique",
    "/api/juridique/jurisprudence": "la jurisprudence citée par la page",
    "/api/juridique/controverses": "les controverses citées par la page",
    "/api/juridique/contrat": "le contrat de travail de la page juridique",
    "/api/juridique/qualification": "la qualification juridique demandée",
    "/api/juridique/arbitrage": "l'arbitrage rendu par la page juridique",
    "/api/juridique/dossier-documents": "les pièces du dossier juridique",
    "/api/juridique/analyse": "l'analyse juridique — MODÈLE FACTURÉ, borné à "
                              "12 appels par IP et par dix minutes",
    "/api/juridique/export": "l'export de l'analyse juridique",
    "/api/playbook/config": "dit à la page ce que la relecture propose",
    "/api/playbook/analyse": "la relecture de contrat — MODÈLE FACTURÉ",
    "/api/playbook/comparer": "la comparaison de deux versions de contrat",
    "/api/playbook/chat": "l'échange sur un contrat — MODÈLE FACTURÉ, borné à "
                          "25 appels par IP et par dix minutes",
    "/api/playbook/export": "l'export de la relecture de contrat",
    "/api/conformite": "nourrit /conformite : obligation légale",
    "/api/contact": "le formulaire de contact doit marcher sans compte",
    # LA SONDE DE VIE, SOUS SON SECOND NOM. Journal de production du
    # 27 août : « GET /api/health 404 "Render/1.0" ». L'hébergeur sondait
    # ce chemin, le service ne servait que « /health », et se déclarait
    # donc lui-même en panne — trafic coupé alors qu'il allait bien.
    # Rien n'y est secret : elle dit qu'un processus répond, et l'état
    # des dépendances que la supervision doit pouvoir lire sans compte.
    "/api/health": "sonde de l'hébergeur — second nom du même point",
    # LE PAIEMENT S'ADRESSE À QUELQU'UN QUI N'EST PAS ENCORE ENTRÉ. Un compte
    # non approuvé ne peut pas se connecter : exiger une session pour payer
    # rendrait la caisse inatteignable par ceux-là mêmes à qui elle s'adresse.
    "/api/paiement/etat": "dit si le paiement est proposé — la page doit le "
                         "savoir AVANT d'afficher un bouton",
    "/api/paiement/checkout": "l'acheteur n'a pas encore d'accès — c'est ce "
                              "qu'il vient acheter",
    # OUVERTE, MAIS VIDE POUR QUI N'A RIEN PROUVÉ. Elle ne rend que l'adresse
    # que l'appelant a lui-même confirmée en ouvrant le lien reçu dans sa
    # boîte, gardée dans SA session ; à tout autre elle rend `null`. Exiger
    # une session de compte la rendrait inutile : celui qui vient payer n'a
    # pas encore d'accès, donc pas de session de compte.
    "/api/paiement/adresse-confirmee": "préremplit la caisse avec l'adresse que "
                                       "l'appelant a lui-même confirmée",
    # Stripe n'a pas de session, et n'en aura jamais. Ce point s'authentifie
    # par la SIGNATURE de ce qu'il reçoit, jamais par un cookie.
    "/api/stripe/webhook": "notification de paiement, authentifiée par sa "
                           "signature et non par une session",
}

# Protégées par un jeton d'en-tête plutôt que par une session : ce sont des
# échanges de serveur à serveur, sans navigateur ni cookie. Les soumettre à une
# session les casserait sans rien protéger de plus.
API_JETON = {
    "/api/ingest": "INGEST_TOKEN — télémétrie du cockpit",
    "/api/reset": "INGEST_TOKEN — remise à zéro du cockpit",
    "/api/maintenance/purge": "INGEST_TOKEN — élagage de l'historique",
    "/api/rag/ingest": "jeton d'ingestion documentaire",
    # RECHERCHE FÉDÉRÉE — CONSEILPREV interroge notre base pour rédiger ses
    # livrables. Serveur à serveur : aucun cookie, donc aucune session à
    # présenter, et c'est bien pourquoi elle est nommée ici plutôt que laissée
    # « direct ». Elle est réservée par RAG_PAIR_CLE et ne sert QUE des
    # documents publics — la clé dit qui peut demander, pas ce qui est servi.
    "/api/rag/search": "RAG_PAIR_CLE — recherche fédérée depuis CONSEILPREV",
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
        elif attendu == "admin" and reel != "admin":
            ecarts.append("%s est sous /api/admin/ mais protégée par « %s » : "
                          "un compte client ordinaire (ou tout visiteur, si "
                          "« direct ») l'atteindrait" % (chemin, reel))
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

    Les ONZE pages en accès direct ont été énumérées une par une. Une liste qui
    en perdrait une au fil d'une modification fermerait une page qui devait
    rester ouverte, et personne ne s'en apercevrait avant qu'un visiteur se
    heurte à un formulaire de connexion sur la page « Contact ».

    LA ONZIÈME A ÉTÉ AJOUTÉE ICI, ET NON CONTOURNÉE. Cette garde a refusé le
    démarrage tant que « /acces » n'était pas nommée : c'est ce refus qui fait
    qu'ouvrir une page reste une décision et non un effet de bord. La modifier
    est l'acte par lequel la décision est prise."""
    # DEUX DÉCISIONS, DEUX ENSEMBLES, ET L'HISTOIRE RESTE LISIBLE. Les fondre
    # en une seule liste ferait disparaître le fait qu'un jour onze pages
    # seulement étaient ouvertes, et pourquoi les trente et une autres l'ont
    # été ensuite.
    decision_onze = {"/services", "/secteurs", "/etudes-de-cas", "/veille",
                     "/ressources", "/faq", "/", "/about", "/vos-projets",
                     "/contact", "/acces"}
    # Le 2 septembre 2026 : le site s'ouvre, sauf l'ingénierie Data Center.
    decision_ouverture = {
    "/methodologie", "/operating-model", "/maturite-ot",
    "/feuille-de-route", "/continuite-ot", "/gestion-des-changements",
    "/architecture-cible", "/formation", "/gouvernance-ia",
    "/relecture-contrat", "/referentiel", "/analyse-de-risque",
    "/programme-securite", "/exigences-systeme", "/exigences-composants",
    "/exigences-prestataires", "/developpement-securise", "/technologies-securite",
    "/gestion-correctifs", "/glossaire-62443", "/metriques-62443",
    "/checklist-62443", "/audit-conformite", "/diagnostic",
    "/nis2", "/juridique", "/demo",
    "/tendances", "/connecter", "/guide-integration",
    "/assistant",
    }
    attendues = decision_onze | decision_ouverture
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
