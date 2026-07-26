# Changer de base de données — mode d'emploi

## Le problème en une phrase

La base actuelle (Neon, offre gratuite) a atteint son plafond de **512 Mo**.
PostgreSQL refuse alors **toute écriture** : les pages s'affichent encore, mais
plus aucun document ne peut être chargé. Il faut donc passer sur la base
PostgreSQL Render (~6 $/mois), déjà prévue dans `render.yaml`.

---

## Quelle méthode choisir ?

Deux méthodes. **La question à vous poser : qu'avez-vous besoin de récupérer ?**

| | **Méthode A — en clics** | **Méthode B — complète** |
|---|---|---|
| Ce qui est repris | Les **documents** de la base de connaissance (avec leurs fichiers d'origine, thèmes et visibilité) | **Tout** : documents + comptes utilisateurs + clients RGPD + historique des livrables + cockpit |
| Comment | 3 boutons dans l'admin | Ligne de commande (`pg_dump`) |
| Compétence requise | Aucune | Savoir ouvrir un terminal |
| Durée | ~10 min | ~30 min |
| À installer | Rien | Outils PostgreSQL (même version majeure que la base) |

### 👉 Notre recommandation

- **Si vos fiches clients et l'historique des livrables sont vides ou sans
  importance → Méthode A.** C'est le cas le plus courant, et de loin le plus
  simple. Vos documents sont repris à l'identique ; le compte administrateur
  est recréé automatiquement.
- **Si vous avez des fiches clients (RGPD) ou un historique de livrables à
  conserver → Méthode B.** C'est la seule qui reprend ces données.

> **Comment savoir ?** Ouvrez `/admin/clients` et `/admin/livrables` sur le site
> actuel. Si les listes sont vides ou ne contiennent que des essais : Méthode A.

Dans les deux cas, **rien n'est perdu** : on ne supprime la base Neon qu'à la
toute fin, une fois la nouvelle validée.

---

# MÉTHODE A — en clics (recommandée)

### Étape 1 — Sauvegarder les documents (site actuel)

1. Ouvrez **`/admin/base-connaissance`**.
2. Cliquez **💾 Sauvegarder**.
3. Un fichier `conseilprevcyber-rag-backup.json` se télécharge. **Gardez-le** :
   il contient tous vos documents avec leurs fichiers d'origine.

> Cela fonctionne même si la base est saturée : sauvegarder ne fait que *lire*.

### Étape 2 — Créer la nouvelle base (tableau de bord Render)

1. Render → **Blueprints** → **Sync** : la base `conseilprevcyber-db` est déjà
   décrite dans `render.yaml`, elle se crée toute seule.
   *(Ou : New + → PostgreSQL, région **Frankfurt**, version **16**, plan
   **basic-256mb**.)*
2. Attendez que son statut passe à **Available**.

> ⚠️ Le nom du plan, « 256mb », désigne la **mémoire**, pas l'espace disque.
> Vérifiez la taille de stockage sur la page de la base et augmentez-la si
> besoin — c'est modifiable après coup.

### Étape 3 — Brancher le site sur la nouvelle base

1. Render → votre service web **conseilprevcyber** → onglet **Environment**.
2. Cherchez la variable **`DATABASE_URL`** :
   - **si elle existe** (elle contient une adresse Neon) → **supprimez-la**.
     Le fichier `render.yaml` rebranchera automatiquement le site sur la base
     Render ;
   - *si elle n'existe pas*, il n'y a rien à faire.
3. Cliquez **Manual Deploy → Deploy latest commit** et attendez la fin du
   déploiement (~3 min).

### Étape 4 — Restaurer vos documents

1. Rechargez **`/admin/base-connaissance`** (**Ctrl+Maj+R**).
   La liste est **vide** : c'est normal, la base est neuve.
2. Connectez-vous si besoin : le compte administrateur est recréé
   automatiquement à partir de `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
3. Cliquez **⤴ Restaurer**, choisissez le fichier de l'étape 1, confirmez.
4. **Laissez la page ouverte.** Après la restauration, l'indexation démarre
   toute seule et vous voyez défiler
   « Indexation des documents restaurés… 3/12 ». Attendez le message
   **« Indexation terminée »**.

> ⚠️ Ne fermez pas l'onglet pendant l'indexation : un document non indexé reste
> invisible pour la recherche, l'assistant et les livrables. Si vous fermez trop
> tôt, ce n'est pas grave : un bouton **▶ Indexer N en attente** apparaît en haut
> de la liste des documents pour reprendre.

### Étape 5 — Vérifier

1. **🩺 Tester le chargement** → tout doit être au vert.
2. Chargez un document : il doit s'enregistrer.
3. **📊 Espace disque** → l'occupation repart bas.
4. Vérifiez que vos documents sont là, avec leurs thèmes.

**C'est fini.** Supprimez la base Neon seulement après quelques jours de recul.

---

# MÉTHODE B — complète (comptes, clients, livrables)

Nécessaire uniquement si vous devez conserver les comptes utilisateurs, les
fiches clients RGPD ou l'historique des livrables. Sept modules partagent la
base ; seule cette méthode les déplace tous.

### Prérequis

Les outils client PostgreSQL, dans une version **au moins égale à celle de la
base la plus récente** des deux. `pg_dump` refuse de lire une base plus récente
que lui ; en revanche, restaurer vers une base plus récente ne pose aucun
problème.

La version de chaque base est indiquée par « 🩺 Tester le chargement » (étape
« session ») ou sur sa page Render. La base Render en service tourne
actuellement en **PostgreSQL 18** : prévoyez donc les outils **18**.

- **macOS** : `brew install postgresql@18`
- **Windows** : installeur PostgreSQL 18 (cocher « Command Line Tools »)
- **Linux (Debian/Ubuntu)** : `sudo apt install postgresql-client-18`
  (dépôt officiel PGDG si le paquet est absent des dépôts de la distribution)

Contrôle : `pg_dump --version`.

### 1. Créer la base Render

Identique à l'**étape 2** de la méthode A.

Puis, sur la page de la base, section **Access Control**, ajoutez
**temporairement** votre adresse IP (sans quoi vous ne pourrez pas y écrire
depuis votre poste). Vous la retirerez à la fin.

### 2. Exporter l'ancienne base

Récupérez l'URL de connexion Neon (tableau de bord Neon → *Connection string*) :

```bash
pg_dump "postgresql://…VOTRE_URL_NEON…?sslmode=require" \
  --no-owner --no-privileges -Fc -f migration.dump
```

Vérifiez que le fichier existe et n'est pas vide : `ls -lh migration.dump`.

### 3. Importer dans la base Render

Récupérez l'**External Database URL** de la base Render (l'URL *interne* n'est
joignable que depuis Render) :

```bash
pg_restore --no-owner --no-privileges \
  -d "postgresql://…URL_EXTERNE_RENDER…" migration.dump
```

La commande doit se terminer **sans erreur**. Contrôlez :

```bash
psql "postgresql://…URL_EXTERNE_RENDER…" -c "
  SELECT 'documents', count(*) FROM rag_documents
  UNION ALL SELECT 'fragments', count(*) FROM rag_chunks
  UNION ALL SELECT 'fichiers',  count(*) FROM rag_blobs
  UNION ALL SELECT 'clients',   count(*) FROM clients
  UNION ALL SELECT 'comptes',   count(*) FROM users;"
```

Les chiffres doivent être **identiques** à ceux de l'ancienne base (même
commande sur l'URL Neon).

### 4. Brancher le site

Identique à l'**étape 3** de la méthode A.

### 5. Vérifier, puis nettoyer

Identique à l'**étape 5** de la méthode A. Ensuite :

- **retirez votre IP** de l'*Access Control* de la base Render ;
- conservez `migration.dump` hors ligne quelques jours ;
- ne supprimez la base Neon qu'une fois tout validé.

> Avec cette méthode, l'indexation est déjà faite : les documents arrivent en
> statut « prêt », rien à relancer.

---

## Si quelque chose bloque

| Ce que vous voyez | Cause | Que faire |
|---|---|---|
| La liste des documents est vide après la bascule | Normal en méthode A avant la restauration | Faites l'étape 4 |
| Le chargement échoue encore | Le nouveau déploiement n'est pas en ligne | « 🩺 Tester le chargement » affiche la version en ligne : comparez-la au dernier déploiement |
| « Session expirée » | Cookie de l'ancienne session | Déconnectez-vous, reconnectez-vous, **Ctrl+Maj+R** |
| Des documents restent en « indexation » | Onglet fermé trop tôt | Bouton **▶ Indexer N en attente** |
| `pg_dump: server version mismatch` | Outils trop anciens | Installer les outils PostgreSQL **16** |
| Connexion refusée à l'import | `ipAllowList` vide | Ajouter votre IP dans *Access Control* |
| L'app démarre mais la base semble vide | Le site pointe encore sur Neon | Vérifier `DATABASE_URL` dans *Environment*, redéployer |

## Pour ne plus jamais saturer

- **📊 Espace disque** dans l'admin : surveiller et libérer le superflu
  (résidus de chargements interrompus, bulletins de veille, fichiers d'origine —
  les documents restent cherchables).
- **💾 Sauvegarder** régulièrement, et conserver le fichier hors ligne.
- Ordre de grandeur : ~4 Ko par fragment, soit ~1,3 Mo pour un document de
  333 fragments, plus le fichier d'origine s'il est conservé en base.
