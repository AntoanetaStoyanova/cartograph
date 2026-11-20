# État du projet — cartograph

> **Usage — Claude Code** : ce fichier est ta mémoire vivante du projet.
> À chaque fois que l'utilisateur demande une review de code, ajoute une nouvelle entrée
> en haut du fichier (sous ce bloc), avec la date du jour, l'état réel du code,
> et les améliorations concrètes à faire. Ne supprime pas les entrées précédentes —
> elles servent à tracer l'évolution du projet dans le temps.
>
> Format d'une entrée :
>
> ## [YYYY-MM-DD] — <titre court décrivant l'état>
> ### État actuel
> ### Améliorations suggérées

---

## [2026-11-20] — Audit (tout le dépôt)

### État actuel

- audit-code : 1 confirmée, 0 écartée, 0 à vérifier (+5 INFO).
- audit-tests : 1 confirmée, 0 écartée, 0 à vérifier (+2 INFO).
- audit-doc : 1 confirmée (README.md:67 et R-COL-26 fusionnées), 0 écartée, 0 à vérifier (+8 INFO).
- Aucun CRITICAL. Tokens : code 117 581, tests 27 684, doc 296 798.
- Couverture partielle : `tests/` surtout par grep, `docs/gouvernance/{green-it,calendrier,veille}.md`, `suivi/` hors `run.py` et `actions.py` non lus.

### Améliorations suggérées

- [WARN] `src/cartograph/bin/collect/run.py:512` — `_collect_sets` écrit `sets-<jour>.parquet` et reste `ok` malgré des sets en échec ; le set absent garde sa ligne de la veille avec `is_current = false` (`stg_tcgdex__sets.sql:28`) → fusionner les fiches manquantes depuis le dernier `sets-*` ou passer l'étape en `failed`.
- [WARN] `tests/test_tasks_dbt.py:56` — seul `build` est testé avec `--exclude tag:donnees_reelles` ; retirer `test` de `TESTING_COMMANDS` (`tasks/__init__.py:70`) passe inaperçu → test paramétré sur `args="test"`.
- [WARN] `README.md:67`, `docs/gouvernance/regles-metier.md:58` (R-COL-26) — la doc laisse croire que toute la Release `catalogue` est purgée ; le workflow ne purge que `cards-*` (`cartograph-data/.github/workflows/collect.yml:193-205`) → « seuls les `cards-*` sont purgés ».

---

## [2026-11-18] — Audit (tout le dépôt)

### État actuel

- audit-code : 5 confirmées, 0 écartée, 1 à vérifier (+3 INFO).
- audit-tests : 11 confirmées, 0 écartée, 0 à vérifier (+10 INFO).
- audit-doc : 10 confirmées (dont 2 doublons du CRITICAL `is_current`), 0 écartée, 0 à vérifier (+8 INFO).
- Principal défaut : depuis COL-05, `removed_on` n'est lu ni par `stg_tcgdex__cards` ni par `catalogue_changes`, donc une carte retirée reste `is_current = true` et le compte `removed` reste à 0.

### Améliorations suggérées

- [CRITICAL] `stg_tcgdex__cards.sql:42-45` : déclarer `removed_on` (et `fingerprint`) dans `sources.yml`, calculer `is_current` avec `removed_on is null`, ajuster `last_seen_on`, ajouter un cas au test unitaire.
- [CRITICAL] `test_collect_run.py` : tester la rotation coupée par une panne (`catalogue: failed`, catalogue et card-changes écrits, `main` renvoie 1).
- [WARN] `catalogue_changes.sql:52` : compter les retraits via `removed_on` (doc `catalogue_changes.yml:6,25`).
- [WARN] `collect/run.py:85` : `logging.getLogger("cartograph.bin.collect.run")` (sous `-m`, `__name__` vaut `__main__`).
- [WARN] `collect/run.py:172` : ajouter `new_cards` aux étapes en attente du checkpoint.
- [WARN] `tasks/__init__.py:387-423` : `clean_branches` doit exclure une branche qui a avancé après la fusion (`headRefOid`).
- [WARN] Tests : `--catalogue --no-prices` ; carte disparue en collecte complète ; assertion `%253F` impossible à faire échouer (`test_collect_run.py:859`) ; `Retry-After` négatif ; prix entiers dans les fixtures (`test_fixtures_prices.py:27`, `conftest.py:62`) ; `LOG_DIR` non patché dans `test_suivi_run.py` ; handlers laissés par `test_rebuild.py` ; échec du téléchargement dans `inv rebuild` ; vrai `.clean` jamais passé à `_clean_targets` ; lignes Énergie et Émissions du rapport.
- [WARN] Doc : README:89 (« lundi ») ; CONTRIBUTING:141 (`__main__.py`), :164 (`is_current`), :189 (« par semaine ») ; `sources.yml:57,60` (`fetched_at`, `raw_json` sans prix) ; docstring de `inv collect` (`tasks/__init__.py:108`).

### Résultat (19/11)

- Corrigé sur `feature/fix-audit-2026-11-18` (v0.8.1) : toutes les trouvailles ci-dessus sauf `clean_branches`, écarté (commande manuelle, cas rare).
- `fix` dbt : `removed_on` lu, `is_current` et `catalogue_changes` justes avant et après COL-05 (`union_by_name`), échantillon aux deux schémas.
- `fix` collecte : prix reçus avant une panne écrits (étape `failed`), `Retry-After` négatif ou `nan` ignoré, logger nommé, `new_cards` dans le checkpoint.
- `test` : trouvailles de audit-tests couvertes, logs des tests isolés (fixture `isolated_logs`).
- `inv ci` : 389 tests, couverture 99,4 % ; `inv okflint` vert.

## [2026-10-27] — Initialisation du projet

### État actuel

- Projet généré depuis le template cruft
- Structure de base en place : `src/`, `tests/`, `config/`, `log/`, `data/`, `notebook/`
- Environnement Python 3.13 configuré avec uv
- Outils configurés : Ruff (lint + format), mypy (strict), pytest + coverage (seuil 88%)
- Aucune logique métier implémentée — projet vide prêt à démarrer
- Branche active : `develop`

### Améliorations suggérées

- Définir la logique métier dans `src/cartograph/`
- Écrire un premier test dans `tests/` pour valider le setup
- Configurer les logs dans `log/__init__.py` (ex. : `logging.basicConfig`)
- Documenter le cas d'usage principal dans `README.md`
