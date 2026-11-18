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

## [2026-11-18] — Fixtures livrées, CI-03 développé

### Fait

- Session ouverte (`/workspace-init`).
- Plan fix-fixtures-prix-fictifs — Étape 1 : Fixtures et test. Prémisse fausse : le commit `51973c5` (28/10, sur `main`) a déjà remplacé tous les prix par des valeurs `4000 + n + 0.37`. Fixtures non modifiées ; décision : garder cet ensemble plutôt que `rang + 0.07` (consignée dans la spec). Créé `tests/test_fixtures_prices.py` (chaque `float` d'un `pricing` appartient à `{n + 0.37, n ≥ 4000}`, détection d'un prix hors ensemble, présence de prix). `inv ci` vert. Commit prévu : `test:` au lieu de `fix:`, sans v0.6.1.
- Plan fix-fixtures-prix-fictifs — Étape 2 : `CONTRIBUTING.md`. Règle des fixtures réécrite (structure gardée, prix fictifs `4000 + n + 0.37`) ; section « Invariants » avant « Règles générales » (contrat : `collect.run`, `report`, `manifest`, appelés par `cartograph-data/.github/workflows/collect.yml`). `inv ci` et `inv okflint` verts. Critères de fin et de la spec cochés ; reste la livraison.
- Branches `feature/ci-02` et `feature/dbt-01` : déjà supprimées (locale et `origin`).
- Plan fix-fixtures-prix-fictifs livré (PR #28 et #30 fusionnées dans `develop`) : plan et spec passés à `fait`.
- Plan ci-03-alerte-version-finish — Étape 1 : Alerte dans `inv finish`. `tasks/__init__.py` : `_bumps_version`, `_touches_code` (`CODE_PATHS`), `_confirm_without_bump` appelée après `_require_clean` (`git diff --name-only origin/develop...HEAD`, puis `git log` seulement si du code est touché) ; `tests/test_tasks_finish.py` (« n », Entrée, « N » arrêtent avant les contrôles, « o » continue, `feat` et doc seule sans question) ; `CONTRIBUTING.md` (alerte décrite). Plan et spec CI-03 passés à `en cours`.
- Plan ci-03-alerte-version-finish — Étape 2 : Nettoyage des branches. `tasks/__init__.py` : `PROTECTED_BRANCHES`, `_check_deletable`, `_merged_pr` (`gh pr list --state merged --json number --jq length`), `_delete_branch` (`git branch -D`, puis `git push origin --delete` seulement si `git ls-remote --heads` la trouve) ; tâches `delete-branch` (`--force`) et `clean-branches` (liste, o/N, `git fetch --prune` seulement après suppression). `tests/test_tasks_branches.py` ; `CONTRIBUTING.md` (fin de lot, `delete-branch-on-merge`). Constat : `pre-commit --all-files` ignore les fichiers non suivis, un nouveau fichier de test n'est vérifié par `inv ci` qu'une fois ajouté (`git add`).
- Plan ci-03-alerte-version-finish — Étape 3 : `inv clean`. `.clean` créé (12 motifs, `logs/` exclu) ; `tasks/__init__.py` : `CLEAN_FILE`, `PROTECTED_PATHS`, `_read_clean`, `_clean_targets(root, patterns, tracked)` (paramètre `tracked` ajouté au plan pour garder la fonction pure : `git ls-files` lu par la tâche), `_check_pattern` (hors dépôt, partie fixe dans un chemin protégé), `_check_target` (chemin protégé ou en contenant un, fichier suivi), parcours `os.walk` qui ne descend ni dans les chemins protégés ni dans un dossier retenu (un `**/__pycache__/` ignore `.venv/`) ; tâche `clean` appelée à la fin de `finish` (PR créée ou déjà ouverte) et de `release` ; `docs-clean` retiré. `tests/test_tasks_clean.py`, tests `finish` et `release` adaptés ; `CONTRIBUTING.md` (« Contrôles »). `inv clean` lancé sur le dépôt : seuls des chemins de `.clean` supprimés, puis `inv ci` vert (337 tests). Critères de la spec et de fin cochés ; reste la livraison. Décision d'Antoaneta : `delete-branch-on-merge` non activé (branches gardées sur GitHub jusqu'à `inv clean-branches`), consigné dans la spec et `CONTRIBUTING.md`.
- dbt Fusion évalué (discussion, sans code) : adaptateur DuckDB en bêta locale, `external_location` / `read_parquet` à risque, gain faible à 2 modèles. Lot DBT-T1 « Essai de dbt Fusion » (P2, après DBT-02, branche `spike/dbt-fusion` non fusionnée, note versée à GOV-05) ajouté à docs/plans/roadmap-lots.md ; `inv okflint` vert. Non commité.

### Reste à faire

- Antoaneta : livrer docs/plans/ci-03-alerte-version-finish.md — commit `feat: inv clean et fichier .clean` (avec `.clean`, déjà marqué par `git add -N`) ; `inv finish`, PR vers `develop`, `inv release`, PR vers `main` ; CI-03 ajouté et coché dans docs/plans/roadmap-lots.md ; `inv clean-branches` (`feature/col-04-*`, `feature/fixtures-prix-fictifs`) ; puis plan et spec à `fait`.
- Ensuite : DBT-02 (staging des prix) au standard SQL.
- Antoaneta : commit `docs:` séparé de la ligne DBT-T1 de docs/plans/roadmap-lots.md (hors CI-03).
- Décision d'Antoaneta : collecte complète du catalogue gardée le lundi (corrections de fiches, ex. 36 raretés provisoires de M6 corrigées par TCGdex le 12/11) et contrôle quotidien des nouvelles cartes dans COL-04 (3 listes `/<langue>/cards` comparées au dernier catalogue, seules les fiches nouvelles téléchargées, prix dès le jour même). Ordre proposé : DBT-01 → CI-02 → COL-04 → DBT-02 ; à vérifier dans la spec COL-04 : l'API ne donne-t-elle que le prix du jour (premiers jours d'un set irrattrapables) ?
- Corriger le logger de `cartograph.bin.collect.run` (`__name__` vaut `__main__` sous `-m`) : petit `fix` à part.
- `inv release` sur `develop` quand STO-02 est fusionné (v0.4.0 : FND-02 contient un `feat`), puis PR `develop` → `main`.
- Avant la porte 1 : relire dans un navigateur les conditions de Cardmarket et de TCGplayer (veille).
- Rapport de novembre à régénérer en fin de mois (`inv suivi --mois 2026-11 --force`, commentaire gardé), puis `statut: fait` ; mettre à jour les chiffres de `docs/gouvernance/green-it.md`. Chaque début de mois : `inv ci` puis `inv suivi`, commentaire.
- optimisation-collecte : l'exécution `42687236424` (9 novembre au soir, `catalogue=oui`, 2 h 04) peut cocher l'exécution manuelle attendue ; reste la PR et la release si pas encore faites (code déjà sur `main`).
- Antoaneta : `inv release` sur `develop` (sans effet sur la version : seulement `docs` et `chore`, rien à taguer ; PR directe `develop` → `main` possible), PR `develop` → `main`. Puis vérifier `gh repo view AntoanetaStoyanova/cartograph --json licenseInfo` = MIT, cocher la dernière case de docs/plans/lot-doc-01-readme-licence.md et passer plan et spec à `fait`.
- Antoaneta : commit de la doc, PR `feature/collecte-rapide` vers `develop`, `inv release`, PR vers `main` ; commit et `git envoyer` du README de `cartograph-data`.
- Antoaneta : exécution manuelle `catalogue=oui` avant le lundi 16 novembre ; relever la durée de « Collecter », vérifier catalogue publié, prix dans `data-2026-11`, manifeste ; comparer le SHA-256 du catalogue au manifeste (STO-01). Puis cocher les dernières cases de docs/plans/optimisation-collecte.md et passer plan et spec à `fait`.
- Antoaneta : rattrapage du 9 novembre, relance prix seuls (`-f catalogue=non`, environ 1 h 20), à confirmer.
- Clore docs/plans/lot-sto-01-manifeste.md : après l'exécution `catalogue=oui`, comparer le SHA-256 du catalogue (`gh release download catalogue`) au manifeste, cocher le dernier critère de la spec, passer plan et spec à `fait`.
- Porte 0 franchie le 15 novembre 2026 (P0-DEC) : neuf tests tranchés dans la spec maîtresse.
- Antoaneta : avant PRO-02, demander aux testeurs leur logiciel de caisse et un fichier d'import exemple.
- `cadrage-flux.md` : flux d'export pro (FX7 et FX8, écrans) à ajouter quand PRO-01 et PRO-02 seront planifiés.

### Références

- docs/plans/ci-03-alerte-version-finish.md, docs/specs/ci-03-alerte-version-finish.md
- docs/plans/fix-fixtures-prix-fictifs.md, docs/specs/fix-fixtures-prix-fictifs.md
- `tasks/__init__.py`, `tests/test_tasks_finish.py`, `tests/test_tasks_branches.py`, `tests/test_tasks_clean.py`, `.clean`, `CONTRIBUTING.md`
- docs/plans/roadmap-lots.md (DBT-T1)
