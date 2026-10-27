# Plan — FND-01 Socle Python

*Rédigé le : 27 octobre 2026*
*Référence : [lot-fnd-01-socle.md](../specs/lot-fnd-01-socle.md)*

## Objectif

Environnement WSL reproductible, logs, beartype et configuration des langues, avec `uv run inv ci` vert.

## Prérequis

- [FND-00 Poste de travail](lot-fnd-00-poste.md) terminé : WSL, Git, SSH, uv et VS Code prêts.

## Étape 1 — Environnement WSL et fichiers ignorés

- [x] Supprimer le `.venv` Windows, lancer `uv sync` sous WSL (Python 3.13).
- [x] Guider le choix de l'interpréteur dans VS Code (« Python: Select Interpreter » → `.venv/bin/python`), exécuté par Antoaneta.
- [x] `.gitignore` : retirer les lignes `uv.lock`, `src/cartograph/log/`, `src/cartograph/config/` ; ajouter `logs/`.
- [x] Vérifier `uv run python -c "import cartograph"` ; en cas d'échec, `pyproject.toml` → `[tool.setuptools.packages.find] where = ["src"]` et retirer `include`.
- [x] Noter dans le journal le défaut de `.gitignore` à corriger dans `python-project-template`.
- [x] Tests : `git check-ignore` ne renvoie plus rien pour `uv.lock` et les deux modules ; `uv run inv check` passe.

## Étape 2 — Module de logs

- [x] `src/cartograph/log/__init__.py` : `setup_logging(name: str, log_dir: Path | None = None, level: int = logging.INFO) -> logging.Logger`, idempotent (ne rajoute pas de handler s'il est déjà configuré), console sur stderr, fichier horodaté seulement si `log_dir` est fourni ; docstrings NumPy, lignes ≤ 88.
- [x] Tests `tests/test_log.py` :
  - `test_setup_logging_sets_level()`
  - `test_setup_logging_twice_does_not_duplicate_handlers()`
  - `test_setup_logging_writes_file_when_log_dir_given()` (`tmp_path`)
  - `test_setup_logging_without_log_dir_creates_no_file()`

## Étape 3 — beartype

- [x] `uv add beartype`.
- [x] `src/cartograph/__init__.py` : appeler `beartype_this_package()` ; corriger la docstring du module (double point final).
- [x] Tests `tests/test_beartype.py` : `test_wrong_argument_type_raises()` — `setup_logging(123)` lève `BeartypeCallHintParamViolation`.

## Étape 4 — Configuration des langues

- [x] `src/cartograph/config/__init__.py` : constante `LANGUAGES: tuple[str, ...] = ("fr", "en", "ja")` ; docstring NumPy du module.
- [x] Tests `tests/test_config.py` : `test_languages_are_non_empty_and_unique()`.

## Étape 5 — Point d'entrée

- [x] `src/cartograph/__main__.py` : retirer le bloc de commentaires ; `main()` journalise le démarrage et les langues de `LANGUAGES` ; docstring NumPy.
- [x] Mettre à jour la ligne FND-01 de `docs/plans/roadmap-lots.md` (tâches invoke reportées à COL-02, FND-02, APP-01).
- [x] `main()` écrit aussi ses logs dans `src/cartograph/log/cartograph_<AAAAMMJJ_HHMMSS>.log` (`get_chemin`) ; `.gitignore` : `src/cartograph/log/*.log`.
- [x] Tests `tests/test_main.py` : `test_main_logs_start_and_languages()` (`caplog`), `test_main_writes_log_file()`, `test_get_chemin_points_to_package_folder()`.
- [x] Rotation : `setup_logging(..., max_files=10)` supprime les plus anciens `<name>_*.log` ; 4 tests dans `tests/test_log.py`.
- [x] `inv lint` en vérification seule (`ruff check --no-fix`).

## Critères de fin

- [x] `uv run inv ci` passe (couverture ≥ 88 %, doctests compris).
- [x] `uv run python -m cartograph` affiche le démarrage et les langues `fr`, `en`, `ja`.
- [x] Tous les critères d'acceptation de la spec sont cochés.
- [x] FND-01 coché dans `docs/plans/roadmap-lots.md`.
