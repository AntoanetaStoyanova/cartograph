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

## [2026-11-18] — Fixtures livrées, CI-03 étape 1

### Fait

- Session ouverte (`/workspace-init`).
- Plan fix-fixtures-prix-fictifs — Étape 1 : Fixtures et test. Prémisse fausse : le commit `51973c5` (28/10, sur `main`) a déjà remplacé tous les prix par des valeurs `4000 + n + 0.37`. Fixtures non modifiées ; décision : garder cet ensemble plutôt que `rang + 0.07` (consignée dans la spec). Créé `tests/test_fixtures_prices.py` (chaque `float` d'un `pricing` appartient à `{n + 0.37, n ≥ 4000}`, détection d'un prix hors ensemble, présence de prix). `inv ci` vert. Commit prévu : `test:` au lieu de `fix:`, sans v0.6.1.
- Plan fix-fixtures-prix-fictifs — Étape 2 : `CONTRIBUTING.md`. Règle des fixtures réécrite (structure gardée, prix fictifs `4000 + n + 0.37`) ; section « Invariants » avant « Règles générales » (contrat : `collect.run`, `report`, `manifest`, appelés par `cartograph-data/.github/workflows/collect.yml`). `inv ci` et `inv okflint` verts. Critères de fin et de la spec cochés ; reste la livraison.
- Branches `feature/ci-02` et `feature/dbt-01` : déjà supprimées (locale et `origin`).
- Plan fix-fixtures-prix-fictifs livré (PR #28 et #30 fusionnées dans `develop`) : plan et spec passés à `fait`.
- Plan ci-03-alerte-version-finish — Étape 1 : Alerte dans `inv finish`. `tasks/__init__.py` : `_bumps_version`, `_touches_code` (`CODE_PATHS`), `_confirm_without_bump` appelée après `_require_clean` (`git diff --name-only origin/develop...HEAD`, puis `git log` seulement si du code est touché) ; `tests/test_tasks_finish.py` (« n », Entrée, « N » arrêtent avant les contrôles, « o » continue, `feat` et doc seule sans question) ; `CONTRIBUTING.md` (alerte décrite). Plan et spec CI-03 passés à `en cours`.

### Reste à faire

- Exécuter docs/plans/ci-03-alerte-version-finish.md — Étape 2 : Nettoyage des branches, puis Étape 3 : `inv clean` (motifs dans `.clean`, appelée à la fin de `finish` et `release`) ; les branches `feature/col-04-*` et `feature/fixtures-prix-fictifs` seront supprimées par `inv clean-branches` à la livraison.
- Ensuite : DBT-02 (staging des prix) au standard SQL.
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
- `tasks/__init__.py`, `tests/test_tasks_finish.py`, `CONTRIBUTING.md`

## [2026-11-17] — COL-04 terminé, plans fixtures et CI-03

### Fait

- Session ouverte (`/workspace-init`).
- `inv release` archive le journal : avant `cz bump`, toutes les entrées sauf la plus récente passent dans `.ai-context/LOG.md` sous `# vX.Y.Z — date`, commit `chore(journal): archive avant vX.Y.Z` ; `cz bump --get-next` arrête la tâche avant l'archive s'il n'y a rien à publier (`tasks/__init__.py`, `tests/test_tasks_release.py`).
- `inv suivi` compte les jours travaillés dans `JOURNAL.md` et `LOG.md` (`worked_days` prend une liste de fichiers, un fichier absent est ignoré).
- Entrées existantes déplacées dans `LOG.md` par version (v0.1.0, v0.2.1, v0.3.0, v0.3.1) ; à reporter dans `python-project-template` en fin de projet.
- Plan col-04-nouvelles-cartes-sets — Étape 1 : Étape `sets` de la collecte. `bin/collect/sets.py` (`list_set_ids`, `fetch_sets`, `set_path`), `snapshot.py` (`SET_SCHEMA`, `set_table`, `SnapshotPaths.sets`, `SET_SORT_BY`), `run.py` (`_collect_sets` après le catalogue, résumé écrit après chaque étape suivie d'une autre, `_write_table` prend le tri), `manifest.py` et `report.py` ; `catalogue.check_language` rendu public. Fixtures `tests/fixtures/tcgdex/*_sets*.json` enregistrées (listes et `cards` réduites à 2, `SM1+` pour l'encodage) ; `conftest.fixture_route` sert aussi `/sets`. Tests : `test_collect_sets.py`, `test_collect_run.py`, `test_collect_manifest.py`, `test_collect_report.py`. Décisions (colonnes, résumé intermédiaire) dans la spec, passée à `en cours`.
- Plan col-04-nouvelles-cartes-sets — Étape 2 : Étape `new_cards` de la collecte. `catalogue.new_card_ids`, `prices.new_card_targets`, `SnapshotPaths.new_cards` et `raw_new_cards`, `run._collect_new_cards` (prix des nouvelles fiches ajoutés à ceux du catalogue dans un seul `prices-*.parquet`, `_write_table` renvoie la table), `manifest.py` (`new-cards-*.parquet` public, brut privé), `report.py`. Tests : `test_collect_new_cards.py`, `test_collect_run.py` (nouvelle carte et prix, produit non doublé, sans nouveauté, liste en échec, conversion en échec, code de sortie 1, T8), manifeste, résumé. Décisions dans la spec : `new_cards` aussi quand le catalogue du jour échoue, langue absente du dernier catalogue ignorée.
- Plan col-04-nouvelles-cartes-sets — Étape 3 : Publication et validation sur GitHub (partie code et doc). `../cartograph-data/.github/workflows/collect.yml` : « Publier le catalogue » sans condition sur l'étape catalogue (sortie `catalogue` de « Lire le résumé » retirée), notes de la Release `catalogue` réécrites à chaque publication (`gh release edit`) pour `cards-`, `sets-`, `new-cards-` ; actionlint et zizmor verts. README de `cartograph` (« Collecte », « Collecte automatique ») et de `cartograph-data` (« Ce qui est publié », `steps` du manifeste) ; `docs/specs/cadrage-flux.md` (vue d'ensemble, FX1, FX2, séquence quotidienne).
- Ligne trop longue de `tasks/__init__.py` (docstring de l'archive du journal) raccourcie pour `inv ci`.
- Plan col-04-nouvelles-cartes-sets — Étape 3 (Antoaneta) : PR #21 `feature/col-04` → `develop`, `inv release` (v0.4.0), PR #22 vers `main` ; `collect.yml` et README de `cartograph-data` envoyés (`7133231`) ; branche `feature/col-04` supprimée, travail repris sur `feature/col-04-dbt` ; exécution manuelle `44063453596` (`catalogue=oui`) lancée à 10:17 UTC.
- Décision d'Antoaneta (option C) : sets collectés à chaque exécution, et non plus seulement les jours du catalogue. Une extension sortie en semaine a ainsi ses cartes (`new-cards`) et son set (date de sortie, série) le jour même ; environ 3 min par jour. Écartées : sets hebdomadaires (jusqu'à 6 jours sans date de sortie pour un nouveau set) et sets des seules nouvelles cartes (plus de code, fusion côté dbt). Nouvelle Étape 4 « Sets quotidiens » dans le plan, staging dbt décalé en Étape 5 ; décision dans la spec.
- Exécution `44063453596` (`catalogue=oui`) annulée par Antoaneta : la validation GitHub de l'étape 3 (sets, `new-cards`, manifestes) passe dans l'étape 4, par une exécution sans catalogue ; étape 4 publiée seule (`feature/col-04-sets`), dbt ensuite.
- Plan col-04-nouvelles-cartes-sets — Étape 4 : Sets quotidiens (partie code et doc). `run.py` : `_collect_sets` à chaque exécution, après le catalogue s'il est demandé, avant `new_cards` ; résumé réécrit après les sets (prix à `failed`). Tests `test_collect_run.py` : sets avant les listes de cartes un jour sans catalogue, sets en échec sans effet sur `new_cards` et les prix, résumé après les sets ; « aucune étape `sets` sans catalogue » retiré. Doc : `bin/collect/__init__.py`, README, `docs/specs/cadrage-flux.md` (FX1, séquence), README et notes de `collect.yml` de `cartograph-data`.
- Étape 4 publiée et validée (Antoaneta) : PR #23 `feature/col-04-sets` → `develop`, v0.5.0, PR #24 vers `main`, `cartograph-data` `1551241`. Exécution `44090970922` (`catalogue=non`, « Collecter » 1 h 47) : `sets-2026-11-17.parquet` (628 sets) et `new-cards-2026-11-17.parquet` (10 cartes) publiés dans la Release `catalogue`, prix `ok` (3 en échec), manifeste `413d47f`. Étapes 3 et 4 du plan cochées.
- Plan col-04-nouvelles-cartes-sets — Étape 5 : Staging dbt. Macros `snapshot_date` (fin de nom `-AAAA-MM-JJ.parquet`) et `is_new_cards` (nouvelle, avec son `.yml`) ; source `tcgdex.cards` sur `*cards-*.parquet`, nouvelle source `tcgdex.sets` ; `stg_tcgdex__cards` : `is_current` = `last_seen_on` ≥ dernier catalogue complet, catalogue prioritaire à date égale, test unitaire `stg_tcgdex__cards_counts_new_cards` ; `stg_tcgdex__sets` reconstruit sur `tcgdex.sets` (série, sigles, `release_date`), test unitaire réécrit ; `catalogue_changes` sans les `new-cards` ; échantillon `sets-` et `new-cards-2026-11-17.parquet` (`tk-xy-su-26` revenue), recette dans `dbt/sample/README.md` ; `CONTRIBUTING.md`, roadmap (COL-04 coché). Vraies données : 628 sets datés ; les 10 cartes de `new-cards-17` sont exactement les 10 « retirées » du 16 (absentes du catalogue du 16, rattrapées le lendemain) ; seule la carte `fr` retirée le 9 reste non courante. Décisions dans la spec. CI : 253 tests, 99,83 %, dbt 17/17.
- README : section « Base de données » (`inv rebuild`, règles de `stg_tcgdex__cards` et `stg_tcgdex__sets`, renvoi aux `.yml`) ; « État du projet » corrigé (sets quotidiens depuis v0.5.0, base locale en service).
- COL-04 clos : PR #25 fusionnée avec un commit `docs:` (le dbt n'aurait fait monter aucune version), rattrapée par un commit vide `feat: staging dbt des sets datés et des nouvelles cartes` (PR #26), v0.6.0, PR #27 vers `main` ; plan et spec passés à `fait`.
- Plans écrits : docs/plans/fix-fixtures-prix-fictifs.md (prix réels de `pricing.cardmarket` dans 9 fixtures de `tests/fixtures/tcgdex/` d'un dépôt public, contradiction avec `CONTRIBUTING.md` ; valeurs fictives `rang + 0.07`, test de non-régression, section « Invariants ») et docs/plans/ci-03-alerte-version-finish.md (alerte de `inv finish` sur du code sans commit `feat`/`fix`/`refactor`/`perf`, option A).
- CI-03 complété d'une étape 2 : `inv clean-branches` et `inv delete-branch <nom>` (PR fusionnée selon `gh`, suppression locale puis sur `origin` si présente, `git fetch --prune`) et réglage GitHub `delete-branch-on-merge`. Décision d'Antoaneta : `main` et `develop` jamais supprimées, même avec `--force` (dans la spec).

### Reste à faire

- Exécuter docs/plans/fix-fixtures-prix-fictifs.md — Étape 1 : Fixtures et test, sur `feature/fixtures-prix-fictifs` (créée depuis `develop` à jour, v0.6.0 ; prix réels dans 9 fixtures publiques ; aucun prix affiché).
- Puis Exécuter docs/plans/ci-03-alerte-version-finish.md — Étape 1 : Alerte dans `inv finish` (option A décidée le 17/11), puis Étape 2 : Nettoyage des branches ; les branches `feature/col-04-sets`, `feature/col-04-dbt` et `feature/col-04-changelog` seront supprimées par `inv clean-branches` à la livraison.
- Ensuite : DBT-02 (staging des prix) au standard SQL.
- Supprimer la branche `feature/ci-02` (locale et `origin`) si ce n'est pas fait.
- Supprimer la branche `feature/dbt-01` (locale et `origin`) si ce n'est pas fait.
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

- docs/plans/col-04-nouvelles-cartes-sets.md, docs/specs/col-04-nouvelles-cartes-sets.md
- src/cartograph/bin/collect/sets.py, catalogue.py, prices.py, snapshot.py, run.py, manifest.py, report.py
- tests/conftest.py, tests/test_collect_sets.py, tests/test_collect_new_cards.py, tests/test_collect_run.py, tests/fixtures/tcgdex/*_sets*.json
- ../cartograph-data/.github/workflows/collect.yml, ../cartograph-data/README.md, README.md, docs/specs/cadrage-flux.md
- dbt/macros/, dbt/models/staging/tcgdex/, dbt/analyses/catalogue_changes.*, dbt/sample/, CONTRIBUTING.md, docs/plans/roadmap-lots.md
- docs/plans/fix-fixtures-prix-fictifs.md, docs/specs/fix-fixtures-prix-fictifs.md, docs/plans/ci-03-alerte-version-finish.md, docs/specs/ci-03-alerte-version-finish.md
