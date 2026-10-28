# Plan — ORC-01 Dépôt de données et workflow planifié

*Rédigé le : 28 octobre 2026*
*Référence : [lot-orc-01-workflow.md](../specs/lot-orc-01-workflow.md)*

## Objectif

Un workflow de `cartograph-data` collecte chaque jour sans intervention, publie le catalogue et envoie prix et brut dans `cartograph-prices`.

## Prérequis

- COL-02 et la note COL-T3 commités, `develop` fusionné dans `main` de `cartograph`.
- Dépôt `cartograph` public (clone sans jeton depuis le workflow).

## Étape 1 — Dépôts et accès

- [ ] Antoaneta, sur GitHub :
  - créer `cartograph-data` (public) et `cartograph-prices` (privé), sans fichier initial ;
  - jeton à grain fin limité à `cartograph-prices`, permission `Contents: Read and write`, expiration notée dans le journal ;
  - dans `cartograph-data` : secret `PRICES_TOKEN`, variable `TCGDEX_USER_AGENT` (même valeur que `.env`).
- [ ] `../cartograph-data/README.md` : rôle du dépôt, lien vers `cartograph`, catalogue TCGdex sous licence MIT avec attribution, aucun prix publié (prix dans un dépôt privé), mention « ni produit ni soutenu par Nintendo ni The Pokémon Company ».
- [ ] `../cartograph-data/.gitignore` : `data/`, `code/`, `logs/`.
- [ ] `git init`, branche `main`, remote SSH ; premier push par Antoaneta.
- [ ] Vérification : `README.md` visible sur GitHub, secret et variable listés dans les réglages.

## Étape 2 — Workflow de collecte

- [ ] `.github/workflows/collect.yml` :
  - `on.schedule` `17 3 * * *` ; `on.workflow_dispatch.inputs` : `catalogue` (booléen, `false`), `prices` (booléen, `true`), `languages` (texte, vide = toutes), `code_ref` (texte, `main`) ;
  - `permissions: {}` ; `concurrency: {group: collect, cancel-in-progress: false}` ;
  - job `collect` : `ubuntu-latest`, `timeout-minutes: 300`, `permissions: contents: write` ;
  - `actions/checkout` du dépôt `AntoanetaStoyanova/cartograph` à `code_ref` dans `code/`, `fetch-depth: 1`, `persist-credentials: false` ;
  - `astral-sh/setup-uv` avec cache (clé sur `code/uv.lock`), puis `uv sync --frozen --no-dev` dans `code/` ;
  - étape `plan` : calcule `catalogue` (paramètre, ou cron et lundi) et les options de `run` ; paramètres lus par `env:` ;
  - sans catalogue : télécharge le dernier `cards-*.parquet` de la Release `catalogue` dans `data/snapshots/` (`gh release view --json assets`, tri par nom) ;
  - `uv run --frozen python -m cartograph.bin.collect.run --data-dir "$GITHUB_WORKSPACE/data" …`, `TCGDEX_USER_AGENT` depuis `vars`.
- [ ] Vérification : `uvx --from actionlint-py actionlint` et `uvx zizmor .github/workflows/collect.yml` sans alerte haute ; corrections notées.

## Étape 3 — Publication des sorties

- [ ] Étapes après la collecte, avec `if: ${{ !cancelled() }}` :
  - catalogue : si `data/snapshots/cards-<date du résumé>.parquet` existe, créer la Release `catalogue` si absente puis `gh release upload --clobber` (`GITHUB_TOKEN`) ;
  - prix et brut : `GH_TOKEN=${{ secrets.PRICES_TOKEN }}`, créer `data-AAAA-MM` dans `cartograph-prices` si absente, envoyer `prices-*.parquet` et `raw/*.json.gz` avec `--clobber` ;
  - `actions/upload-artifact` : `data/runs/collect-*.json` et `code/logs/*.log`, `retention-days: 7`, jamais `data/raw/` ni `data/snapshots/`.
- [ ] Le job échoue si la collecte a échoué, après les publications (code de sortie conservé dans une sortie d'étape).
- [ ] Vérification : `actionlint`, `zizmor` ; relecture que seuls le catalogue, le résumé et le log sont publics.

## Étape 4 — Exécutions manuelles et documentation

- [ ] Exécution manuelle `catalogue: true` (toutes langues) : fichiers présents dans les deux Releases ; durées et débit relevés dans le résumé.
- [ ] Exécution manuelle `catalogue: false` : catalogue lu depuis la Release, prix envoyés.
- [ ] Relance le même jour : fichiers remplacés, aucun doublon dans les Releases.
- [ ] Contrôle : aucun prix dans les logs d'exécution ni dans l'artefact (recherche de `cm_`, `avg`, `trend`, valeurs décimales dans les logs téléchargés).
- [ ] `docs/specs/col-t3-taille-duree.md` : section « Machine GitHub » (débit, durées réelles, verdict confirmé ou revu).
- [ ] `README.md` de `cartograph` : section « Collecte automatique » (dépôts, horaire, lundi catalogue, relance manuelle).
- [ ] `docs/plans/roadmap-lots.md` : ORC-01 coché ; STO-01 réduit au manifeste ; STO-03 réduit à l'archive mensuelle du brut.

## Critères de fin

- [ ] `uv run inv ci` passe dans `cartograph`
- [ ] `actionlint` et `zizmor` passent sur `cartograph-data`
- [ ] Critères d'acceptation de la spec cochés
