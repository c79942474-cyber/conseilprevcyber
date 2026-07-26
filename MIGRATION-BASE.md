# Migration de la base : Neon → PostgreSQL Render

Procédure de bascule de la base applicative vers la base PostgreSQL déclarée
dans `render.yaml` (`conseilprevcyber-db`, région Frankfurt, PostgreSQL 16).

**Pourquoi.** La base Neon de l'offre gratuite plafonne à 512 Mo. Une fois ce
plafond atteint, PostgreSQL refuse **toute écriture** : les pages continuent de
s'afficher (lectures) mais plus aucun document ne se charge — sur tous les blocs
et quel que soit le format. Message caractéristique, visible via
« 🩺 Tester le chargement » :

```
could not extend file because project size limit (512 MB) has been exceeded
HINT: ... internally by neon.max_cluster_size
```

**Ce que la migration déplace.** Sept modules partagent `DATABASE_URL` : base de
connaissance (documents, fragments, fichiers d'origine), comptes, clients RGPD
et leurs pièces jointes, historique des livrables, cockpit, veille, automation.
La bascule doit donc emporter **toute** la base, pas seulement les documents.

Procédure entièrement vérifiée en local sur PostgreSQL 16 + pgvector, avec des
documents réels : restauration sans erreur, 735 fragments et 3 documents
retrouvés à l'identique, connexion admin, recherche, téléchargement des fichiers
d'origine et **nouveau chargement** tous fonctionnels sur la base d'arrivée.

---

## 0. Avant de commencer

- **Ne supprimez pas la base Neon** tant que la nouvelle n'est pas validée.
  L'export ci-dessous est en lecture seule : il fonctionne même si la base est
  saturée (les écritures sont bloquées, pas les lectures).
- Prévoyez `pg_dump` / `pg_restore` **version 16** (même version majeure que les
  bases). `pg_dump --version` doit afficher `16.x`.
- Notez que le plan Render `basic-256mb` désigne la **mémoire vive**, pas le
  disque : vérifiez la taille de stockage allouée dans le tableau de bord de la
  base et augmentez-la si nécessaire (elle est ajustable après coup).

Ordre de grandeur utile pour dimensionner : chaque fragment coûte ~4 Ko
d'embedding ; un document comme `DNV-OS-D301` (333 fragments) pèse donc ~1,3 Mo
d'index, auxquels s'ajoute le fichier d'origine s'il est conservé en base.

---

## 1. Créer la base PostgreSQL Render

La base est **déjà déclarée** dans `render.yaml` :

```yaml
databases:
  - name: conseilprevcyber-db
    databaseName: conseilprevcyber
    user: conseilprevcyber
    region: frankfurt          # MÊME région que le service web
    plan: basic-256mb
    postgresMajorVersion: "16"
    ipAllowList: []            # aucune connexion externe
```

Dans le tableau de bord Render : **Blueprints → Sync** (ou créez la base à la
main avec ces mêmes réglages). Attendez le statut **Available**.

> `ipAllowList: []` interdit toute connexion externe. Pour l'import depuis votre
> poste (étape 3), ajoutez **temporairement** votre adresse IP dans
> *Access Control*, puis **retirez-la** aussitôt l'import terminé.

## 2. Exporter l'ancienne base (Neon)

Récupérez l'URL de connexion Neon (tableau de bord Neon → *Connection string*),
puis :

```bash
pg_dump "postgresql://…VOTRE_URL_NEON…?sslmode=require" \
  --no-owner --no-privileges -Fc -f migration.dump
```

Vérifiez que le fichier n'est pas vide :

```bash
ls -lh migration.dump
pg_restore -l migration.dump | head
```

Le dump contient l'extension `vector` : rien à préparer sur la base d'arrivée.

## 3. Importer dans la base Render

Récupérez l'**External Database URL** de la base Render (nécessaire depuis votre
poste ; l'URL *interne* n'est joignable que depuis Render).

```bash
pg_restore --no-owner --no-privileges \
  -d "postgresql://…URL_EXTERNE_RENDER…" migration.dump
```

`pg_restore` doit se terminer **sans erreur**. Contrôlez immédiatement :

```bash
psql "postgresql://…URL_EXTERNE_RENDER…" -c "
  SELECT 'documents', count(*) FROM rag_documents
  UNION ALL SELECT 'fragments', count(*) FROM rag_chunks
  UNION ALL SELECT 'fichiers',  count(*) FROM rag_blobs
  UNION ALL SELECT 'clients',   count(*) FROM clients
  UNION ALL SELECT 'comptes',   count(*) FROM users;"
```

Les compteurs doivent être **identiques** à ceux de l'ancienne base (même
requête sur l'URL Neon).

## 4. Basculer le service sur la nouvelle base

Le blueprint alimente déjà `DATABASE_URL` depuis la base Render :

```yaml
      - key: DATABASE_URL
        fromDatabase:
          name: conseilprevcyber-db
          property: connectionString
```

Si le service pointe aujourd'hui vers Neon, c'est qu'une valeur `DATABASE_URL`
a été saisie **à la main** dans *Environment* : elle prend le pas sur le
blueprint. Dans le tableau de bord du service web :

1. *Environment* → **supprimez** la variable `DATABASE_URL` saisie manuellement
   (ou remplacez sa valeur par l'**Internal Database URL** de la base Render) ;
2. **Manual Deploy → Deploy latest commit**.

> Utilisez l'URL **interne** pour le service (même région, connexion privée,
> plus rapide et non exposée). L'URL **externe** ne sert qu'à l'import.

## 5. Vérifier

Sur `/admin/base-connaissance` :

1. **🩺 Tester le chargement** → toutes les étapes doivent être au vert, et la
   version affichée doit correspondre au dernier déploiement.
2. **📊 Espace disque** → l'occupation doit repartir d'un niveau confortable.
3. Chargez un document : il doit s'enregistrer normalement.
4. Vérifiez que vos documents, clients et comptes sont bien présents.

## 6. Après validation

- Retirez votre IP de l'*Access Control* de la base Render (étape 1).
- Conservez `migration.dump` hors ligne quelques jours (sauvegarde de repli).
- Ne supprimez la base Neon qu'une fois tout validé.

---

## En cas de problème

| Symptôme | Cause probable | Correctif |
|---|---|---|
| `pg_dump: server version mismatch` | `pg_dump` plus ancien que la base | Installer les outils client PostgreSQL 16 |
| Connexion refusée à l'import | `ipAllowList` vide | Ajouter temporairement votre IP dans *Access Control* |
| `type "vector" does not exist` | Extension absente sur la cible | `CREATE EXTENSION IF NOT EXISTS vector;` puis relancer l'import |
| L'app démarre mais la base paraît vide | Le service pointe encore sur Neon | Vérifier `DATABASE_URL` dans *Environment*, puis redéployer |
| Le chargement échoue encore | Le nouveau déploiement n'est pas en ligne | Comparer la version affichée par « 🩺 Tester le chargement » |

## Prévenir une nouvelle saturation

- **📊 Espace disque** dans l'admin : surveiller l'occupation et libérer le
  superflu (résidus de chargements interrompus, bulletins de veille, fichiers
  d'origine — les documents restent cherchables).
- **💾 Sauvegarder** : exporter régulièrement la base de connaissance hors ligne.
- Les fichiers d'origine sont le poste le plus lourd et ne servent qu'au bouton
  « télécharger l'original » : les purger libère beaucoup sans rien perdre
  d'exploitable.
