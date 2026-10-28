# Spec — FND-01 Socle Python

*Rédigé le : 27 octobre 2026*

## Contexte

Premier lot de la [feuille de route](../plans/roadmap-lots.md). Le projet sort du template cruft : la structure existe, mais l'environnement n'a été créé que sous Windows (`.venv` avec `Scripts/`, `uv` absent de WSL), alors que la [spec maîtresse](Spécification%20du%20projet%20final%20M2%20plateforme%20de%20données%20Pokémon%20TCG%20(1).md) fixe Ubuntu ou WSL comme environnement de référence (N8).

État constaté le 27 octobre 2026 :

- `.gitignore` ignore `uv.lock` (contraire à N2), `src/cartograph/log/` et `src/cartograph/config/` : deux modules de code ne sont pas versionnés.
- `[tool.setuptools.packages.find]` (`where = ["."]`, `include = ["src*"]`) publie le paquet sous le nom `src.cartograph`, alors que le code importe `cartograph` : à vérifier.
- `setup_logging` ajoute de nouveaux handlers à chaque appel et n'a ni docstring ni test ; `__main__.py` contient un bloc de commentaires ; beartype n'est pas installé.

## Objectif

Un socle sur lequel les lots suivants s'appuient sans retouche : environnement WSL reproductible, logs configurés, vérification des types à l'exécution, configuration des langues, et `uv run inv ci` vert.

## Périmètre

- `.venv` recréé sous WSL et `uv.lock` versionné (le poste lui-même est préparé par FND-00).
- Correction de `.gitignore` (et de la découverte du paquet si l'import échoue).
- Module `cartograph.log`, beartype, module `cartograph.config` avec la liste des langues.
- Point d'entrée `python -m cartograph` nettoyé.

## Hors périmètre

- Client TCGdex et collecte (COL-01, COL-02).
- dbt (FND-02) et CI GitHub (CI-01).
- Tâches invoke `collect`, `dbt`, `app` : chacune arrive avec le lot qui l'implémente (COL-02, FND-02, APP-01).

## Décisions

| Sujet | Décision | Raison |
| --- | --- | --- |
| Environnement | WSL seul (poste préparé par [FND-00](../plans/lot-fnd-00-poste.md)) ; le `.venv` Windows est supprimé et recréé par `uv sync` sous WSL | Environnement de référence de la spec ; un même `.venv` ne peut pas servir aux deux systèmes |
| `.gitignore` | Ne plus ignorer `uv.lock`, `src/cartograph/log/`, `src/cartograph/config/` ; ignorer `logs/` et `src/cartograph/log/*.log` (fichiers de log produits) | Versions figées (N2) et code versionné ; défaut du template à signaler dans `python-project-template` sans le modifier depuis ici |
| Découverte du paquet | Si `import cartograph` échoue, passer à `where = ["src"]` | Correction minimale ; le reste de la config du template est conservé |
| beartype | `beartype_this_package()` dans `cartograph/__init__.py` | Couvre tout le paquet sans décorer chaque fonction ; aucune fonction publique oubliée |
| Logs | `setup_logging` idempotent, console sur stderr, fichier optionnel ; `python -m cartograph` écrit dans `src/cartograph/log/<projet>_<AAAAMMJJ_HHMMSS>.log` (chemin construit par `get_chemin`, fichiers `.log` ignorés par Git) ; 10 fichiers au plus par logger (`max_files`), les plus anciens supprimés | Appels répétés sans doublons ; stdout libre pour les sorties de commandes ; trace de chaque lancement (demande d'Antoaneta, 27 octobre 2026). Remplacé le 28 octobre 2026 : `LOG_DIR = <racine>/logs` dans `config`, `get_chemin` supprimée (sorties hors du paquet) |
| Configuration | Constante `LANGUAGES` dans `cartograph/config/__init__.py`, pas de fichier TOML ni JSON | Un seul développeur, même config partout : mypy vérifie le type, pas de lecture ni de validation à l'exécution ; passage à un fichier le jour où un lot a besoin d'une config par environnement |
| Contenu de la config | Seulement `LANGUAGES` pour ce lot | Chaque lot ajoute ses propres paramètres (ex. correspondance langue → modèle avec le lot des modèles) |
| Validation | Un test vérifie que `LANGUAGES` est non vide et sans doublon | Une erreur d'édition est détectée en CI, sans code de validation à l'exécution |
| Docstrings | Format NumPy | `CONTRIBUTING.md` du projet et standards globaux |

## Critères d'acceptation

- [x] `uv sync` fonctionne sous WSL et `uv.lock` n'est plus ignoré.
- [x] `src/cartograph/log/` et `src/cartograph/config/` ne sont plus ignorés par Git.
- [x] `uv run python -c "import cartograph"` fonctionne.
- [x] Appeler une fonction du paquet avec un mauvais type lève une erreur beartype.
- [x] `setup_logging` appelé deux fois ne duplique pas les messages.
- [x] `LANGUAGES` vaut `("fr", "en", "ja")`, non vide et sans doublon (test).
- [x] `uv run python -m cartograph` journalise le démarrage et les langues configurées.
- [x] `uv run inv ci` passe, couverture ≥ 88 %.
