## v0.6.0 (2026-11-17)

### Nouveautés

- staging dbt des sets datés et des nouvelles cartes

### Documentation

- regles métiers readme

## v0.5.0 (2026-11-17)

### Nouveautés

- sets collectés à chaque exécution

## v0.4.0 (2026-11-17)

### Nouveautés

- publier sets et nouvelles cartes dans la Release catalogue
- fiche et prix des nouvelles cartes le jour même
- **collect**: snapshot des sets avec date de sortie les jours du catalogue
- modèle stg_tcgdex__sets et analyse des changements du catalogue
- modèle stg_tcgdex__cards, une ligne par carte et par langue
- source dbt du catalogue et échantillon versionné pour inv ci
- tâche inv rebuild, base reconstruite depuis les Releases sans écraser l'ancienne en cas d'échec
- téléchargement des snapshots des Releases avec contrôle SHA-256
- inventaire des snapshots Parquet des Releases à rapatrier
- tâche inv dbt, lancée par inv ci, inv finish et inv release

### Corrections

- versionner l'échantillon Parquet lu par inv ci
- CI sans copie de .env.example, la variable GitHub suffit

### Réécritures

- renommer les colonnes de staging qui sont des mots-clés SQL

### Documentation

- Any toléré pour le JSON d'API non typé
- staging dbt et échantillon dans CONTRIBUTING, DBT-01 livré
- échantillon dbt, fiches corrigées par TCGdex
- spec et plan DBT-01, staging du catalogue
- inv rebuild dans CONTRIBUTING, STO-02 livré
- plan STO-02, reconstruction de la base
- projet dbt et inv dbt dans CONTRIBUTING
- journal du 16 novembre, CI-01 livré et FND-02 planifié

### Tests

- tests unitaires et contrats dbt sur le staging du catalogue

### Maintenance

- standard SQL vérifié par sqlfluff au commit, inv sql-fmt
- standard SQL vérifié par sqlfluff au commit, inv sql-fmt
- ignorer l'aperçu local des snapshots
- squelette dbt-duckdb (projet, profil DuckDB, couches)

## v0.3.1 (2026-11-16)

### Corrections

- variable TCGDEX_USER_AGENT passée aux contrôles de la CI

### Documentation

- CI, inv finish et protection des branches dans CONTRIBUTING et le README

### Maintenance

- ruleset de protection de develop et main
- inv release ouvre la pull request develop vers main avec le changelog
- tâche inv finish, contrôles, push et pull request vers develop
- workflow CI sur les pull requests, actionlint et zizmor au commit

## v0.3.0 (2026-11-15)

### Nouveautés

- lecture des lots de la roadmap et des jours travaillés pour le suivi

### Corrections

- suivi sans exécutions en cours, erreurs de gh visibles, couverture datée

### Réécritures

- temps de travail retiré des estimations du suivi

### Documentation

- corrections de la revue du dossier de veille
- veille technique et revue de veille à chaque porte
- veille légale, licences des modèles et conditions des services
- dossier de veille, sources et quotas revérifiés
- GOV-05 planifié, entrées P0-DEC et GOV-04 remises dans le journal
- bilan Green IT et lien vers la gouvernance dans le README
- calendrier révisé à chaque porte, dates des portes 1 à 3 validées
- plan gouvernance
- porte 0 franchie, neuf tests tranchés
- porte 0, durées réelles de novembre et replis vérifiés
- T9 passé, embeddings sur CPU en 15 minutes au plus sur un runner
- EMB-T9 revu, mesure sur runner seul et repli par indexation étalée
- COL-T2 passé, couverture française et variantes tranchées
- scan japonais par lecture du code et du numéro, limites notées
- avertissement, données et licence dans le README
- T5 passé, STO-03 clos
- manifeste quotidien décrit dans le README

### Maintenance

- licence MIT

## v0.2.1 (2026-11-09)

### Corrections

- résumé écrit après le catalogue, une collecte coupée ne perd plus le catalogue
- sélection des prix sans langue demandée ne lève plus d'erreur

### Réécritures

- table du catalogue déplacée dans snapshot.py, run.py réduit à l'orchestration
- sélection des produits à interroger déplacée dans prices.py
- latest_catalogue et bilan d'étape par défaut sortis de run.py

### Performances

- le jour du catalogue, prix tirés de ses fiches sans seconde passe sur l'API
- prix lisibles depuis les fiches du catalogue sans nouvel appel à l'API

### Documentation

- collecte du lundi en une seule passe, résumé après chaque étape
- collecte déclenchée par cron-job.org

### Maintenance

- schémas Mermaid gardés en local, hors git

## v0.2.0 (2026-10-30)

### Nouveautés

- tâche inv release. Commitizen et hook commit-msg

### Réécritures

- version lue dans pyproject.toml par importlib.metadata

### Documentation

- cycle de release et préfixes de commit dans CONTRIBUTING
- contrôles avant pull request, specs et plans locaux
- contrôles locaux et branches feature dans CONTRIBUTING

### Maintenance

- okflint pour les specs et plans (inv okflint)
- markdownlint et prettier au commit

## v0.1.0 (2026-10-30)

### Nouveautés

- manifeste quotidien sans prix (fichiers, Release, SHA-256, taille du dépôt)
- résumé Markdown de la collecte
- snapshots Parquet et commande inv collect (COL-02)
- client TCGdex COL-01 et cadrage des flux
- socle Python FND-01 (logs, beartype, langues)

### Corrections

- retire les vrais prix des fixtures TCGdex

### Réécritures

- résumé de collecte typé, doublons retirés et docstrings relues

### Documentation

- surveillance de la collecte dans le README
- note COL-T4, tcgdex/price-history écarté
- retour aux prix quotidiens
- retour aux prix quotidiens
- ORC-01 vérifié et collecte hebdomadaire

### Maintenance

- hooks pre-push retirés, blocage reporté à la CI GitHub
- hooks pre-commit et pre-push
- fins de ligne LF
- specs et plans gardés en local
- initial project structure from cruft template
