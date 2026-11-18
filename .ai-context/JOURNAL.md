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

## [2026-11-18] — Fixtures livrées, CI-04 livré

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

### Reste à faire

- Antoaneta : nouvelles informations sur la collecte, plan à rédiger avec elle avant DBT-02.
- Planifier DBT-02 (staging des prix) au standard SQL : `/workspace-plan dbt-02`.
- Décision d'Antoaneta : collecte complète du catalogue gardée le lundi (corrections de fiches, ex. 36 raretés provisoires de M6 corrigées par TCGdex le 12/11) et contrôle quotidien des nouvelles cartes dans COL-04 (3 listes `/<langue>/cards` comparées au dernier catalogue, seules les fiches nouvelles téléchargées, prix dès le jour même). Ordre proposé : DBT-01 → CI-02 → COL-04 → DBT-02 ; à vérifier dans la spec COL-04 : l'API ne donne-t-elle que le prix du jour (premiers jours d'un set irrattrapables) ?
- Corriger le logger de `cartograph.bin.collect.run` (`__name__` vaut `__main__` sous `-m`) : petit `fix` à part.
- Avant la porte 1 : relire dans un navigateur les conditions de Cardmarket et de TCGplayer (veille).
- Rapport de novembre à régénérer en fin de mois (`inv suivi --mois 2026-11 --force`, commentaire gardé), puis `statut: fait` ; mettre à jour les chiffres de `docs/gouvernance/green-it.md`. Chaque début de mois : `inv ci` puis `inv suivi`, commentaire.
- Clore docs/plans/lot-sto-01-manifeste.md : après l'exécution `catalogue=oui`, comparer le SHA-256 du catalogue (`gh release download catalogue`) au manifeste, cocher le dernier critère de la spec, passer plan et spec à `fait`.
- Porte 0 franchie le 15 novembre 2026 (P0-DEC) : neuf tests tranchés dans la spec maîtresse.
- Antoaneta : avant PRO-02, demander aux testeurs leur logiciel de caisse et un fichier d'import exemple.
- `cadrage-flux.md` : flux d'export pro (FX7 et FX8, écrans) à ajouter quand PRO-01 et PRO-02 seront planifiés.

### Références

- docs/plans/ci-04-alerte-version-finish.md, docs/specs/ci-04-alerte-version-finish.md
- docs/plans/fix-fixtures-prix-fictifs.md, docs/specs/fix-fixtures-prix-fictifs.md
- `tasks/__init__.py`, `tests/test_tasks_finish.py`, `tests/test_tasks_branches.py`, `tests/test_tasks_clean.py`, `.clean`, `CONTRIBUTING.md`
- docs/plans/roadmap-lots.md (DBT-T1)
