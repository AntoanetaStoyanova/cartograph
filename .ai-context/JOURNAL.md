# Journal — cartograph

> **Usage — Claude Code** : ce fichier trace l'avancement du projet session par session —
> ce qui a été fait et ce qu'il reste à faire. Contrairement à `CURRENT.md` (état du code
> au moment d'une review), ce journal suit les décisions, les documents créés et les étapes
> franchies. Ajoute une entrée en haut (sous ce bloc) à chaque session de travail
> significative. Ne supprime pas les entrées précédentes.
>
> Format d'une entrée :
>
> ## [YYYY-MM-DD] — <titre court de la session>
> ### Fait
> - ce qui a été fait
>
> ### Reste à faire
> - ce qu'il reste à faire
>
> ### Références
> - fichiers, specs, plans

---

## [2026-11-18] — CI-04 livré, COL-05 livré

### Fait

- Session ouverte (`/workspace-init`).
- Plan fix-fixtures-prix-fictifs — Étape 1 : Fixtures et test. Prémisse fausse : le commit `51973c5` (28/10, sur `main`) a déjà remplacé tous les prix par des valeurs `4000 + n + 0.37`. Fixtures non modifiées ; décision : garder cet ensemble plutôt que `rang + 0.07` (consignée dans la spec). Créé `tests/test_fixtures_prices.py` (chaque `float` d'un `pricing` appartient à `{n + 0.37, n ≥ 4000}`, détection d'un prix hors ensemble, présence de prix). `inv ci` vert. Commit prévu : `test:` au lieu de `fix:`, sans v0.6.1.
- Plan fix-fixtures-prix-fictifs — Étape 2 : `CONTRIBUTING.md`. Règle des fixtures réécrite (structure gardée, prix fictifs `4000 + n + 0.37`) ; section « Invariants » avant « Règles générales » (contrat : `collect.run`, `report`, `manifest`, appelés par `cartograph-data/.github/workflows/collect.yml`). `inv ci` et `inv okflint` verts. Critères de fin et de la spec cochés ; reste la livraison.
- Branches `feature/ci-02` et `feature/dbt-01` : déjà supprimées (locale et `origin`).
- Plan fix-fixtures-prix-fictifs livré (PR #28 et #30 fusionnées dans `develop`) : plan et spec passés à `fait`.
- Plan ci-04-alerte-version-finish — Étape 1 : Alerte dans `inv finish`. `tasks/__init__.py` : `_bumps_version`, `_touches_code` (`CODE_PATHS`), `_confirm_without_bump` appelée après `_require_clean` (`git diff --name-only origin/develop...HEAD`, puis `git log` seulement si du code est touché) ; `tests/test_tasks_finish.py` (« n », Entrée, « N » arrêtent avant les contrôles, « o » continue, `feat` et doc seule sans question) ; `CONTRIBUTING.md` (alerte décrite). Plan et spec passés à `en cours`.
- Plan ci-04-alerte-version-finish — Étape 2 : Nettoyage des branches. `tasks/__init__.py` : `PROTECTED_BRANCHES`, `_check_deletable`, `_merged_pr` (`gh pr list --state merged --json number --jq length`), `_delete_branch` (`git branch -D`, puis `git push origin --delete` seulement si `git ls-remote --heads` la trouve) ; tâches `delete-branch` (`--force`) et `clean-branches` (liste, o/N, `git fetch --prune` seulement après suppression). `tests/test_tasks_branches.py` ; `CONTRIBUTING.md` (fin de lot, `delete-branch-on-merge`). Constat : `pre-commit --all-files` ignore les fichiers non suivis, un nouveau fichier de test n'est vérifié par `inv ci` qu'une fois ajouté (`git add`).
- Plan ci-04-alerte-version-finish — Étape 3 : `inv clean`. `.clean` créé (12 motifs, `logs/` exclu) ; `tasks/__init__.py` : `CLEAN_FILE`, `PROTECTED_PATHS`, `_read_clean`, `_clean_targets(root, patterns, tracked)` (paramètre `tracked` ajouté au plan pour garder la fonction pure : `git ls-files` lu par la tâche), `_check_pattern` (hors dépôt, partie fixe dans un chemin protégé), `_check_target` (chemin protégé ou en contenant un, fichier suivi), parcours `os.walk` qui ne descend ni dans les chemins protégés ni dans un dossier retenu (un `**/__pycache__/` ignore `.venv/`) ; tâche `clean` appelée à la fin de `finish` (PR créée ou déjà ouverte) et de `release` ; `docs-clean` retiré. `tests/test_tasks_clean.py`, tests `finish` et `release` adaptés ; `CONTRIBUTING.md` (« Contrôles »). `inv clean` lancé sur le dépôt : seuls des chemins de `.clean` supprimés, puis `inv ci` vert (337 tests). Critères de la spec et de fin cochés ; reste la livraison. Décision d'Antoaneta : `delete-branch-on-merge` non activé (branches gardées sur GitHub jusqu'à `inv clean-branches`), consigné dans la spec et `CONTRIBUTING.md`.
- dbt Fusion évalué (discussion, sans code) : adaptateur DuckDB en bêta locale, `external_location` / `read_parquet` à risque, gain faible à 2 modèles. Lot DBT-T1 « Essai de dbt Fusion » (P2, après DBT-02, branche `spike/dbt-fusion` non fusionnée, note versée à GOV-05) ajouté à docs/plans/roadmap-lots.md ; `inv okflint` vert. Non commité.
- Plan ci-04-alerte-version-finish livré (PR #31 vers `develop`, v0.7.0, PR #32 vers `main`, branche supprimée par `inv delete-branch`). Lot renommé CI-03 → CI-04 : CI-03 désigne déjà « Sécurité des dépôts » dans la roadmap. Plan et spec renommés `ci-04-alerte-version-finish.md`, titres et `lot:` mis à jour, ligne CI-04 ajoutée et cochée dans docs/plans/roadmap-lots.md (après CI-03, ordre « Pipeline de données » : COL-04 → CI-04 → DBT-02). Plan et spec à `fait`. `inv okflint` vert.
- Constat : `docs/plans/` et `docs/specs/` sont ignorés par Git (`.gitignore:95`), le commit `docs:` de la ligne DBT-T1 est sans objet.
- Plan lot-doc-01-readme-licence clos : GitHub affiche MIT pour `cartograph` (`gh repo view --json licenseInfo`) ; plan et spec à `fait`.
- Plan optimisation-collecte clos (PR, release et exécution `catalogue=oui` faites, confirmé par Antoaneta) ; plan et spec à `fait`.
- Discussion collecte (catalogues du 9 et du 16/11, API) puis `docs/specs/collecte-incrementale.md` et `docs/plans/collecte-incrementale.md` créés (lot COL-05, 7 étapes). Décisions actées dans la spec : collecte complète du lundi supprimée (manuelle seulement), empreinte SHA-256 sans `pricing` ni `updated`, fiches des prix réutilisées, rotation de 1 000 fiches par jour, `removed_on` sans suppression, fiche en échec = ligne de la veille, cartes sans `idProduct` gardées sans prédiction, Release `catalogue` : dernier `cards-*` et ceux des lundis + `card-changes-*` quotidien.

- Plan collecte-incrementale — Étape 1 : Empreinte et schéma du catalogue. `snapshot.py` : `card_fingerprint` (SHA-256 du JSON trié sans `pricing` ni `updated`), `CARD_SCHEMA` + `fingerprint` et `removed_on` (avant `raw_json`), `card_table` les remplit, `read_catalogue` complète un catalogue antérieur depuis `raw_json`. `tests/test_collect_snapshot.py` (6 tests). Vérifié : 20 fiches de `cards-2026-11-16.parquet` sur 20 ont la même empreinte que l'API, 59 400 lignes complétées en 7 s ; DuckDB lit un mélange d'anciens et de nouveaux `cards-*` sans erreur (`union_by_name` plus tard, consigné dans la spec). Spec à `en cours`.
- Retiré du « Reste à faire » : la décision du catalogue complet du lundi (COL-04), remplacée par COL-05.
- Plan collecte-incrementale — Étape 2 : Listes : nouvelles, disparues, revenues. `catalogue.py` : `ListingDiff` et `listing_diff(client, languages, catalogue: pa.Table)` remplacent `new_card_ids` ; `run._collect_new_cards` lit le catalogue par `read_catalogue` et prend `diff.new`. Tests déplacés de `tests/test_collect_new_cards.py` vers `tests/test_collect_catalogue.py` (5 tests). Décision : une liste vide de l'API ne fait disparaître aucune carte (consignée dans la spec).
- Plan collecte-incrementale — Étape 3 : Fiches reçues avec les prix. `prices.py` : `PriceFetch` (`prices`, `cards` par langue) renvoyé par `fetch_prices` ; `run.py` n'en prend encore que `.prices` (fusion à l'Étape 5). Nouveau module `incremental.py` : `changed_cards(base, cards)` renvoie les fiches modifiées (ou absentes de la base) et les identifiants des fiches identiques, par langue (dictionnaires plutôt que listes, pour alimenter `catalogue_table`). Tests : `tests/test_collect_prices.py`, `tests/test_collect_failures.py` adaptés, `tests/test_collect_incremental.py` créé.
- Plan collecte-incrementale — Étape 4 : Rotation. `incremental.py` : `rotation_ids(base, price_targets, size)` (hors cibles de prix et disparues, tri `fetched_at` puis `card_id`, coupe à `size` toutes langues confondues) ; `config` : `ROTATION_SIZE = 1000` ; `run.py` : option `--rotation N` (`_rotation`, entier ≥ 0) passée à `collect(rotation=...)`, encore sans effet jusqu'à l'Étape 5. Tests : `tests/test_collect_incremental.py`, `tests/test_collect_run.py`.
- Plan collecte-incrementale — Étape 5 : Fusion et collecte quotidienne. `incremental.py` : `apply_listing`, `merge_catalogue`, `card_changes_table`, `count_changes` ; `snapshot.py` : `CHANGE_SCHEMA`, `SnapshotPaths.card_changes`, `latest_catalogue(before=day)` ; `catalogue.py` : `compare_listing` (partagé avec la collecte complète) ; `prices.py` : `price_targets_from_catalogue(table, ...)` ignore les cartes disparues ; `run.py` : étape `catalogue` quotidienne (`_update_catalogue`, `_write_catalogue`), collecte complète avec lignes de la veille pour les fiches en échec ; `__init__.py` : `StepSummary.changes` ; `report.py` : tableau « Changements du catalogue » ; `manifest.py` : `card-changes-*` public. Bug trouvé et corrigé en test : changements calculés contre le catalogue déjà marqué (pas de `removed`). Mesure sur `cards-2026-11-16.parquet` : 31 000 fiches comparées en 2,4 s, fusion 0,7 s, 0 fausse modification. Décisions consignées dans la spec (source antérieure au jour, `apply_listing` avant les prix, échecs de prix et de rotation, `read_at` unique).
- Plan collecte-incrementale — Étape 6 : Workflow de `cartograph-data`. `collect.yml` : `catalogue` = `non` (défaut) ou `oui`, plus de lundi automatique ; « Télécharger le dernier catalogue » sans condition, dernier `cards-*` antérieur au jour (`awk '$0 < limit'`) ; notes de la Release (`cards-*` quotidien avec `removed_on`, `card-changes-*`) ; nouvelle étape « Nettoyer les anciens catalogues » (non bloquante, après « Publier le catalogue » réussie : garde le plus récent, ceux des lundis et celui du jour). actionlint et zizmor verts ; logique vérifiée à blanc. Non commité.
- Plan collecte-incrementale — Étape 7 : Documentation (part de Claude). `README.md` de `cartograph` (état, collecte, collecte automatique, relance) et de `cartograph-data` (fichiers publiés, `card-changes-*`, rétention, paramètres, relance) ; `dbt/models/staging/tcgdex/sources.yml` (description) ; docs/plans/roadmap-lots.md : COL-05 ajouté et coché, COL-02 et COL-04 annotés, ordre « … CI-04 → COL-05 → DBT-02 ». `CONTRIBUTING.md` inchangé (invariant général).
- COL-05 livré (PR #33, v0.8.0 ; `cartograph-data` envoyé ; branche supprimée). Exécution manuelle du 18/11 (run 44314516180) : « Collecter » 1 h 37 (1 h 44 à 1 h 47 avant), rotation 1 000 fiches en 3 min, 10 `new` (les 10 fiches en échec du 16/11, récupérées), 0 `updated` sur 31 284 fiches lues, `cards-2026-11-18.parquet` 59 410 lignes et 10,1 Mo (+2 Mo pour `fingerprint`), aucun prix publié. Résultats dans la spec ; plan et spec à `fait`.
- Discussion échecs de collecte : 11 prix en échec en 11 jours (~1 par jour, manifestes du 8 au 18/11). Décision : pas de seconde passe pour l'instant (relevé du lendemain couvert par `cm_avg7`/`cm_avg30`) ; à reprendre si > 50 échecs par jour, ou par un test de couverture des prix en QUA-01.

### Reste à faire

- Vérifier le 19/11 que « Nettoyer les anciens catalogues » a supprimé `cards-2026-11-18.parquet` de la Release `catalogue` (seul critère vérifié à blanc).
- DBT-02 : `stg_tcgdex__cards` devra lire `removed_on` (`union_by_name = true`) : les `cards-*` quotidiens gardent les cartes disparues.
- Planifier DBT-02 (staging des prix) au standard SQL : `/workspace-plan dbt-02`.
- Corriger le logger de `cartograph.bin.collect.run` (`__name__` vaut `__main__` sous `-m`) : petit `fix` à part.
- Avant la porte 1 : relire dans un navigateur les conditions de Cardmarket et de TCGplayer (veille).
- Rapport de novembre à régénérer en fin de mois (`inv suivi --mois 2026-11 --force`, commentaire gardé), puis `statut: fait` ; mettre à jour les chiffres de `docs/gouvernance/green-it.md`. Chaque début de mois : `inv ci` puis `inv suivi`, commentaire.
- Clore docs/plans/lot-sto-01-manifeste.md : après l'exécution `catalogue=oui`, comparer le SHA-256 du catalogue (`gh release download catalogue`) au manifeste, cocher le dernier critère de la spec, passer plan et spec à `fait`.
- Porte 0 franchie le 15 novembre 2026 (P0-DEC) : neuf tests tranchés dans la spec maîtresse.
- Antoaneta : avant PRO-02, demander aux testeurs leur logiciel de caisse et un fichier d'import exemple.
- `cadrage-flux.md` : flux d'export pro (FX7 et FX8, écrans) à ajouter quand PRO-01 et PRO-02 seront planifiés.

### Références

- ../docs/specs/collecte-incrementale.md, ../docs/plans/collecte-incrementale.md
- `cartograph-data/.github/workflows/collect.yml`
- `src/cartograph/bin/collect/snapshot.py`, `catalogue.py`, `run.py`, `prices.py`, `incremental.py`, `report.py`, `manifest.py`, `tests/test_collect_snapshot.py`, `tests/test_collect_catalogue.py`, `tests/test_collect_incremental.py`
- docs/plans/ci-04-alerte-version-finish.md, docs/specs/ci-04-alerte-version-finish.md
- docs/plans/fix-fixtures-prix-fictifs.md, docs/specs/fix-fixtures-prix-fictifs.md
- `tasks/__init__.py`, `tests/test_tasks_finish.py`, `tests/test_tasks_branches.py`, `tests/test_tasks_clean.py`, `.clean`, `CONTRIBUTING.md`
- docs/plans/roadmap-lots.md (DBT-T1)
