# Plan — ORC-01 Dépôt de données et workflow planifié

*Rédigé le : 28 octobre 2026*
*Référence : [lot-orc-01-workflow.md](../specs/lot-orc-01-workflow.md)*

## Objectif

Un workflow de `cartograph-data` collecte chaque semaine sans intervention, publie le catalogue et envoie prix et brut dans `cartograph-prices`.

## Prérequis

- COL-02 et la note COL-T3 commités, `develop` fusionné dans `main` de `cartograph`.
- Dépôt `cartograph` public (clone sans jeton depuis le workflow).

## Étape 1 — Dépôts et accès

- [x] Antoaneta, sur GitHub :
  - créer `cartograph-data` (public) et `cartograph-prices` (privé), sans fichier initial ;
  - jeton à grain fin limité à `cartograph-prices`, permission `Contents: Read and write`, expiration notée dans le journal ;
  - dans `cartograph-data` : secret `PRICES_TOKEN`, variable `TCGDEX_USER_AGENT` (même valeur que `.env`).
- [x] `../cartograph-data/README.md` : rôle du dépôt, lien vers `cartograph`, catalogue TCGdex sous licence MIT avec attribution, aucun prix publié (prix dans un dépôt privé), mention « ni produit ni soutenu par Nintendo ni The Pokémon Company ».
- [x] `../cartograph-data/.gitignore` : `data/`, `code/`, `logs/`.
- [x] `git init`, branche `main`, remote SSH ; premier push par Antoaneta (`e683c34`).
- [x] Vérification : `cartograph-data` public en ligne avec `main` à `e683c34` ; `cartograph-prices` privé (404 anonyme, accessible en SSH, vide) ; secret et variable déclarés par Antoaneta (non lisibles sans `gh`).

## Étape 2 — Workflow de collecte

- [x] `.github/workflows/collect.yml` :
  - `on.schedule` `17 3 * * *` ; `on.workflow_dispatch.inputs` : `catalogue` (booléen, `false`), `prices` (booléen, `true`), `languages` (texte, vide = toutes), `code_ref` (texte, `main`) ;
  - `permissions: {}` ; `concurrency: {group: collect, cancel-in-progress: false}` ;
  - job `collect` : `ubuntu-latest`, `timeout-minutes: 300`, `permissions: contents: write` ;
  - `actions/checkout` du dépôt `AntoanetaStoyanova/cartograph` à `code_ref` dans `code/`, `fetch-depth: 1`, `persist-credentials: false` ;
  - `astral-sh/setup-uv` avec cache (clé sur `code/uv.lock`), puis `uv sync --frozen --no-dev` dans `code/` ;
  - étape `plan` : calcule `catalogue` (paramètre, ou cron et lundi) et les options de `run` ; paramètres lus par `env:` ;
  - sans catalogue : télécharge le dernier `cards-*.parquet` de la Release `catalogue` dans `data/snapshots/` (`gh release view --json assets`, tri par nom) ;
  - `uv run --frozen python -m cartograph.bin.collect.run --data-dir "$GITHUB_WORKSPACE/data" …`, `TCGDEX_USER_AGENT` depuis `vars`.
- [x] Vérification : `uvx --from actionlint-py --with shellcheck-py bash -c 'actionlint'` (shellcheck compris) et `uvx zizmor --persona=pedantic` sans alerte ; corrections : nom du job, commentaire sur `contents: write`. Actions épinglées par SHA (zizmor l'exige pour `setup-uv`, qui n'a pas d'étiquette majeure). Logique bash simulée en local (lundi, paramètres, injection dans `languages` restée un seul argument, dernier catalogue) ; clone de `main` + `uv sync --frozen --no-dev` + `--help` testés.

## Étape 3 — Publication des sorties

- [x] Étapes après la collecte, avec `if: ${{ !cancelled() }}` (étape `summary` : date et statut lus dans `collect-*.json` avec `jq`, nombres affichés sans prix) :
  - catalogue : si `data/snapshots/cards-<date du résumé>.parquet` existe, créer la Release `catalogue` si absente puis `gh release upload --clobber` (`GITHUB_TOKEN`) ;
  - prix et brut : `GH_TOKEN=${{ secrets.PRICES_TOKEN }}`, créer `data-AAAA-MM` dans `cartograph-prices` si absente, envoyer `prices-*.parquet` et `raw/*.json.gz` avec `--clobber` ;
  - `actions/upload-artifact` : `data/runs/collect-*.json` et `code/logs/*.log`, `retention-days: 7`, jamais `data/raw/` ni `data/snapshots/`.
- [x] Le job échoue si la collecte a échoué, après les publications : `continue-on-error` sur la collecte, dernière étape en échec si `steps.collect.outcome == 'failure'` ; délai de 270 min sur l'étape de collecte pour laisser le temps de publier avant les 300 min du job.
- [x] Vérification : `actionlint` (avec shellcheck), `zizmor --persona=pedantic` sans alerte ; étapes de publication simulées en local sur les sorties du 28 octobre avec un faux `gh` (catalogue → `catalogue`, prix + deux bruts → `data-2026-10`) ; relecture : seuls le catalogue, le résumé et le log sont publics.

## Étape 4 — Exécutions manuelles et documentation

- [x] Antoaneta : premier commit dans `cartograph-prices` (`03ffe70`) (README « Add a README » sur GitHub) ; sans commit, `gh release create` échoue sur un dépôt vide.
- [x] Commit et push de `collect.yml` dans `cartograph-data` (`5c1ddef`, le cron démarre au push).
- [x] Exécution manuelle `catalogue: true` (toutes langues) : fichiers présents dans les deux Releases ; durées et débit relevés dans le résumé. (`40717195500`, 28 octobre 2026 : succès en 3 h 45 ; `cards-2026-10-28.parquet` dans `catalogue` ; `prices-2026-10-28.parquet`, `cards-2026-10-28.json.gz`, `prices-2026-10-28.json.gz` dans `data-2026-10` ; 0 échec, 120 HTTP 503 absorbés.)
- [x] Passage en hebdomadaire (décision du 29 octobre 2026) : `collect.yml` (crons lundi et mardi, job `check` qui saute le mardi si `cards-<lundi>.parquet` et `prices-<lundi>.parquet` sont publiés, catalogue à chaque exécution planifiée, `catalogue` coché par défaut en manuel, `cache-dependency-glob: uv.lock`) ; `actionlint` et `zizmor` sans alerte ; logique du `check` testée sur les vraies Releases (28 octobre → saut, 27 → collecte, Release absente → collecte) ; spec maîtresse, `cadrage-flux.md`, `col-t3-taille-duree.md`, spec ORC-01 et `README.md` mis à jour. Push de `cartograph-data` par Antoaneta.
- [x] Exécution manuelle `catalogue: false` : catalogue lu depuis la Release, prix envoyés. (`40841546156`, 29 octobre 2026, workflow hebdomadaire `d0e8206` : `check` 3 s, collecte 1 h 1 min ; `cards-2026-10-28.parquet` repris de la Release ; 29 314 produits en 1 h 0 min 45 s (8,0 req/s), 0 échec ; `prices-2026-10-29.parquet` et `prices-2026-10-29.json.gz` dans `data-2026-10` ; aucun prix dans les logs.) (Le cron du 29 octobre à 03:17 UTC ne s'est pas déclenché : aucune exécution à 08:00 UTC, workflow `active`.)
- [x] Relance le même jour : fichiers remplacés, aucun doublon dans les Releases. (`40857127038`, 29 octobre 2026 : `prices-2026-10-29.parquet` et `.json.gz` remplacés à 11:56 UTC, toujours 5 fichiers dans `data-2026-10` et 1 dans `catalogue` ; 29 314 produits en 1 h 32, 0 échec ; 503 : 28 puis 22 sur les deux exécutions sans catalogue.)
- [ ] Mardi 3 novembre : le rattrapage saute la collecte (fichiers du lundi 2 présents).
- [x] Contrôle : aucun prix dans les logs d'exécution ni dans l'artefact (recherche de `cm_`, `avg`, `trend`, valeurs décimales dans les logs téléchargés). (Log du job, log de collecte et résumé : aucune occurrence ; les décimales du log du job sont des numéros de version.)
- [x] `docs/specs/col-t3-taille-duree.md` : section « Machine GitHub » (débit, durées réelles, verdict confirmé ou revu).
- [x] `README.md` de `cartograph` : section « Collecte automatique » (dépôts, horaire, lundi catalogue, relance manuelle).
- [x] `docs/plans/roadmap-lots.md` : STO-01 réduit au manifeste ; STO-03 réduit à l'archive mensuelle du brut.
- [ ] `docs/plans/roadmap-lots.md` : ORC-01 coché (après le contrôle du mardi 3 novembre).

## Critères de fin

- [x] `uv run inv ci` passe dans `cartograph`
- [x] `actionlint` et `zizmor` passent sur `cartograph-data`
- [ ] Critères d'acceptation de la spec cochés
