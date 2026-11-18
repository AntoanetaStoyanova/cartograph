# Contributing to cartograph

Standards de développement du projet. Ces règles s'appliquent à tout contributeur humain ou IA (Claude Code inclus).

---

## Type hints

Obligatoires partout — arguments, valeurs de retour, variables ambiguës.

```python
def process(data: list[str], limit: int = 10) -> dict[str, int]: ...
```

- `mypy --strict` doit passer sans erreur
- Pas de `Any`, sauf pour du JSON externe non typé (réponses d'API : `dict[str, Any]`) ; tout autre usage est justifié par un commentaire

---

## Docstrings

Obligatoires sur tous les modules, classes et fonctions publiques. Format NumPy, résumé sur la ligne qui suit les guillemets, types repris de la signature :

```python
def fetch(url: str, timeout: int = 30) -> bytes:
    """
    Télécharge le contenu d'une URL.

    Parameters
    ----------
    url : str
        URL cible.
    timeout : int
        Délai max en secondes.

    Returns
    -------
    bytes
        Contenu brut de la réponse.

    Raises
    ------
    ValueError
        Si l'URL est invalide.
    """
```

Classes : section `Attributes` au même format. Doctests : section `Examples`.

Fonctions privées (`_nom`) : docstring courte en une ligne suffit.

---

## Style & formatage

Outil unique : **Ruff** (formatage + lint).

```bash
uv run ruff format .   # formate
uv run ruff check .    # lint
```

- Longueur de ligne : 88 caractères
- Guillemets doubles
- Imports triés automatiquement (isort via Ruff)

---

## Tests

```bash
uv run pytest          # lance tous les tests + coverage
```

- Couverture minimale : **88%** (bloquant en CI)
- Les doctests comptent (`--doctest-modules` activé)
- Un test = un comportement précis, pas une fonction
- Nommage : `test_<comportement>.py`, fonctions `test_<ce_qui_est_verifie>()`

---

## Contrôles

Une fois après le clonage :

```bash
uv sync
uv run inv hooks       # installe le hook pre-commit
```

À chaque `git commit`, pre-commit contrôle les fichiers du commit (`.pre-commit-config.yaml`) :

| Fichiers | Contrôles |
| --- | --- |
| Tous | fins de ligne LF, fin de fichier, espaces en fin de ligne, BOM, gros fichiers, casse des noms |
| Python | `ruff check`, `ruff format` |
| Markdown | markdownlint (`.markdownlint-cli2.yaml`) |
| YAML, JSON, TOML | validité ; prettier formate le YAML et le JSON |
| Workflows (`.github/workflows/`) | actionlint, zizmor (`--persona=pedantic`) |
| SQL de `dbt/models/` et `dbt/analyses/` | sqlfluff (`.sqlfluff`, voir « Standard SQL ») |

- Si un contrôle corrige un fichier, le commit est refusé : relire la correction, `git add`, recommencer le commit.
- « Stashing unstaged files » : les modifications hors du commit sont mises de côté pendant les contrôles, puis remises.
- `git commit --no-verify` saute les contrôles pour un commit de travail ; ils restent dus avant la pull request.
- Les réponses d'API enregistrées dans `tests/fixtures/` gardent leur structure ; leurs prix sont fictifs (`4000 + n + 0.37`, vérifié par `tests/test_fixtures_prices.py`).

Avant une pull request, depuis la branche `feature/…` :

```bash
uv run inv finish      # inv ci et inv okflint, push, puis pull request vers develop
```

`inv finish` refuse une autre branche qu'une `feature/…` et un arbre de travail non propre ; si la pull request existe déjà, il affiche son lien. Si la branche modifie `src/`, `tasks/`, `dbt/models/` ou `dbt/macros/` sans aucun commit `feat`, `fix`, `refactor` ou `perf` (seuls préfixes qui font monter la version), il affiche les commits et demande confirmation avant le push ; « n » ou Entrée arrête la tâche, le temps d'un `git commit --amend`. Les contrôles se lancent aussi seuls :

```bash
uv run inv ci          # pre-commit sur tous les fichiers, mypy, pytest, dbt build sur l'échantillon
uv run inv okflint     # en-tête et liens des specs et plans locaux de docs/
```

`uv run inv clean` supprime les fichiers générés (caches, couverture, `dbt/target/`, base échantillon, `docs/_build/`) déclarés dans `.clean`, à la racine : un motif glob par ligne, relatif à la racine, `/` final pour un dossier, `#` pour un commentaire. Pour nettoyer un nouveau fichier généré, ajouter son motif à `.clean` plutôt qu'écrire un `rm`. La tâche échoue sans rien supprimer si un motif touche un fichier suivi par Git, sort du dépôt ou atteint un chemin protégé (`.env`, `.venv/`, `.git/`, `data/snapshots/`, `data/raw/`, `data/cartograph.duckdb`, `docs/plans/`, `docs/specs/`). `inv finish` et `inv release` la lancent à la fin ; `inv ci` non, pour garder `htmlcov/` et `dbt/target/` après un échec.

Sur GitHub, le workflow `CI` (`.github/workflows/ci.yml`) lance `uv run inv ci` sur chaque pull request vers `develop` et `main` (environ une minute) ; un nouveau push sur la branche annule l'exécution en cours. La variable GitHub Actions `TCGDEX_USER_AGENT` du dépôt doit exister : `cartograph.config` l'exige à l'import.

Les specs et plans de `docs/` (locaux, non suivis par Git) commencent par un en-tête vérifié par okflint (`okf-base.yaml`) :

```yaml
---
type: plan             # spec, plan, note ou reference
statut: en cours       # brouillon, en cours, fait ou abandonné
redige_le: 2026-10-30
lot: CI-00             # facultatif
---
```

---

## Organisation du code

```text
src/cartograph/
├── __main__.py     # uniquement : from . import main; main()
├── bin/            # modules métier (fonctions), importés en cartograph.bin.<module>
├── config/         # constantes et paramètres
├── data/           # chargement / sauvegarde de données
├── log/            # configuration des logs (jamais print() en production)
└── notebook/       # utilitaires pour notebooks Jupyter
```

Les transformations dbt (dbt-duckdb) vivent dans `dbt/`, hors du paquet Python :

```text
dbt/
├── dbt_project.yml     # matérialisations par couche, variable snapshot_dir
├── profiles.yml        # profil DuckDB versionné, sans secret
├── sample/snapshots/   # échantillon du catalogue pour la CI (recette dans sample/README.md)
├── analyses/           # requêtes lancées à la demande, sans table créée
├── macros/             # fonctions Jinja partagées (snapshot_date, is_new_cards)
└── models/
    ├── staging/        # stg_<source>__<entité> : nettoyage des sources, en vue
    ├── intermediate/   # int_ : jointures et règles métier, en vue
    └── marts/          # fct_, dim_, mart_ : tables lues par l'application
```

Chaque modèle, analyse ou macro `<nom>.sql` a son fichier de propriétés `<nom>.yml` à côté (description, colonnes, tests) ; les sources sont déclarées dans `sources.yml`. Chaque colonne déclare son `data_type` ; les modèles ont un contrat (`contract: enforced: true`) : un type qui ne correspond plus fait échouer `dbt build`. Une règle de calcul (dernière version, `is_current`…) est couverte par un test unitaire dbt (`unit_tests:`, données en `format: sql`, car dbt-duckdb ne lit pas les colonnes d'une source externe). Les modèles de staging du catalogue (`staging/tcgdex/`) sont `stg_tcgdex__cards` (une ligne par carte et par langue, dernière version vue dans un catalogue complet ou un `new-cards`, `is_current` vrai si la carte est dans le dernier catalogue complet ou dans un `new-cards` postérieur) et `stg_tcgdex__sets` (une ligne par set et par langue, avec date de sortie et série, tirée des `sets-*.parquet`).

### Standard SQL

Le SQL de `dbt/models/` et `dbt/analyses/` suit le style de dbt Labs, vérifié par sqlfluff (`.sqlfluff`, dialecte `duckdb`) à chaque commit, donc dans `inv ci` :

- tout en minuscules (mots-clés, fonctions, types, noms) ; 4 espaces ; 88 caractères par ligne, comme Ruff ;
- un modèle enchaîne des CTE (`source`, `renamed`…) et finit par `select * from <dernière CTE>` ;
- alias toujours explicites avec `as`, y compris pour une sous-requête ; virgules en fin de ligne ;
- `group by` et `order by` par noms de colonnes, jamais par numéros ; dans un `order by` à plusieurs colonnes, le sens (`asc`, `desc`) est donné pour toutes ou pour aucune ;
- aucun nom de colonne n'est un mot-clé SQL (règle RF04) : `language_code`, `card_name`, `pokemon_types`, `evolution_stage` plutôt que `language`, `name`, `types`, `stage`. Les colonnes des Parquet gardent leur nom d'origine et sont renommées dans le staging ;
- l'ordre des colonnes d'un `select` suit leur sens (identité, description, images, dates), le même que dans le `.yml` : la règle ST06 (colonnes simples avant les calculs) est désactivée.

sqlfluff lit les balises `{{ }}` avec son lecteur `jinja` (fonctions de dbt simulées, macros chargées depuis `dbt/macros/`) : pas besoin de compiler le projet dbt, le contrôle prend une à deux secondes. Les macros ne sont pas contrôlées (`.sqlfluffignore`).

```bash
uv run inv sql-fmt     # corrige ce que sqlfluff sait corriger (mise en page, casse)
```

Le reste (alias manquant, `group by 1`, nom de colonne réservé) se corrige à la main ; relire les corrections avant `git add`.

```bash
uv run inv dbt                    # dbt build sur data/snapshots/
uv run inv dbt --sample           # dbt build sur l'échantillon, base data/cartograph.sample.duckdb
uv run inv dbt --args debug       # autre commande dbt (debug, docs generate…)
uv run inv dbt --args "show --select catalogue_changes"  # changements du catalogue par semaine
```

La source `tcgdex.cards` lit `*cards-*.parquet` (catalogues complets `cards-` et nouvelles cartes `new-cards-`, distingués par la macro `is_new_cards`) et la source `tcgdex.sets` lit `sets-*.parquet`, dans le dossier de la variable dbt `snapshot_dir` (`data/snapshots` par défaut) ; la date du snapshot vient de la fin du nom du fichier (macro `snapshot_date`). Chaque motif doit trouver au moins un fichier, sinon `read_parquet` échoue. `inv dbt --sample` la fait pointer vers `dbt/sample/snapshots/` et écrit dans `data/cartograph.sample.duckdb` : c'est ce que lancent `inv ci`, `inv finish` et `inv release`, sans `data/snapshots/` ni appel aux APIs, et sans toucher à `data/cartograph.duckdb`. L'échantillon ne contient que du catalogue public, jamais de prix ; si le schéma des snapshots change, le régénérer avec la recette de `dbt/sample/README.md`.

La base est `data/cartograph.duckdb` (jamais versionnée, reconstruite à la demande) ; la variable `CARTOGRAPH_DUCKDB` en désigne une autre. `dbt/target/` et `dbt/logs/` sont recréés à chaque commande et ignorés par Git.

Pour reconstruire la base depuis les données collectées :

```bash
uv run inv rebuild                  # snapshots des Releases, puis dbt build
uv run inv rebuild --skip-download  # dbt build sur les snapshots déjà présents
```

`inv rebuild` rapatrie dans `data/snapshots/` les `*.parquet` de la Release `catalogue` de `cartograph-data` et des Releases `data-AAAA-MM` de `cartograph-prices` (dépôt privé : la session `gh auth` doit y avoir accès). Les JSON bruts ne sont pas téléchargés. Un fichier n'est téléchargé que s'il manque ou si son SHA-256 diffère de celui de GitHub (collecte relancée le même jour), et son empreinte est recontrôlée après téléchargement ; une erreur arrête la commande avant dbt. Un Parquet local absent des Releases est gardé (sauvegarde) et signalé. dbt construit une base temporaire, `data/cartograph.rebuild.duckdb`, qui ne remplace `data/cartograph.duckdb` qu'en cas de succès : un échec laisse l'ancienne base intacte.

---

## Git

- Branches : `feature/<sujet>` (développement, créée depuis `develop`), `develop` (qualité), `main` (production, jamais modifiée en local)
- Cycle :
  1. `feature/…` se pousse librement et rejoint `develop` par une pull request, ouverte par `uv run inv finish` ;
  2. sur `develop` : `uv run inv release --dry-run` (version suivante et changelog, sans rien modifier), puis `uv run inv release` (pull, contrôles, `cz bump`, documentation, push avec le tag, puis pull request `develop` → `main` titrée `Release vX.Y.Z`, avec la section de la version dans `CHANGELOG.md`) ;
  3. la pull request `develop` → `main` est fusionnée une fois le check `ci` vert.
- Protection (ruleset `.github/rulesets/develop-main.json`, appliqué par `gh api --method POST repos/AntoanetaStoyanova/cartograph/rulesets --input …`) : sur `develop` et `main`, pull request obligatoire, check `ci` vert requis, merge commit seul, ni force-push ni suppression. Le rôle admin peut passer outre : c'est ce qui laisse `inv release` pousser sur `develop`. Ne jamais cocher « bypass rules » pour fusionner une pull request rouge.
- Pull requests fusionnées en **merge commit** uniquement : un squash réduirait le changelog à une ligne et, comme un rebase, laisserait le commit tagué hors de `main`
- Mettre une branche feature à jour après une release : `git fetch origin && git merge origin/develop`
- Fin de lot : `uv run inv clean-branches` liste les branches locales dont la pull request est fusionnée (`gh pr list --state merged`, qui reconnaît aussi un squash) et, après confirmation (o/N), les supprime en local puis sur `origin` si elles y sont encore, puis `git fetch --prune`. Une seule branche : `uv run inv delete-branch <nom>`, refusée sans pull request fusionnée sauf `--force`. `main`, `develop` et la branche courante ne sont jamais supprimées, même avec `--force`.
- Le réglage GitHub `delete-branch-on-merge` reste désactivé : une branche fusionnée reste sur `origin`, consultable, jusqu'à `inv clean-branches`. `develop` et `main` sont de toute façon protégées par le ruleset.
- Les specs et plans de `docs/` ne sont pas suivis par Git : `git clean -fdx` les effacerait, il est interdit
- Format des commits — **Conventional Commits**, vérifié par le hook `commit-msg`. Chaque message devient une ligne du `CHANGELOG.md` : l'écrire pour être relu.

| Préfixe | Usage | Version (0.x) | Changelog |
| --- | --- | --- | --- |
| `feat:` | nouvelle fonctionnalité | mineure | Nouveautés |
| `fix:` | correction de bug | correctif | Corrections |
| `refactor:` | réécriture sans changement de comportement | correctif | Réécritures |
| `perf:` | performance | correctif | Performances |
| `docs:` | documentation uniquement | aucune | Documentation |
| `test:` | ajout ou correction de tests | aucune | Tests |
| `chore:` | maintenance, dépendances, config | aucune | Maintenance |

- `!` après le type (`feat!:`) marque un changement cassant : mineure tant que la version est en 0.x
- Une release ne contenant que `docs`, `test` ou `chore` ne crée pas de version ; ces commits partent dans la suivante
- `bump:` est réservé au commit créé par `inv release`

---

## Invariants

- Aucun prix réel dans un fichier commité : les fixtures publiques n'ont que des prix fictifs.
- Aucun prix dans le résumé de collecte ni dans les logs : seulement identifiants, nombres et messages d'erreur, comme `run.py` et `client.py`.
- Les options de `cartograph.bin.collect.run`, `report` et `manifest`, et le format du résumé et du manifeste, sont un contrat avec le workflow `Collecte` de `cartograph-data` : vérifier les commandes de `../cartograph-data/.github/workflows/collect.yml` avant de les changer.

---

## Règles générales

- Commenter le **pourquoi**, jamais le **quoi** (le code doit se lire seul)
- Pas de code mort commenté — git conserve l'historique
- Pas de `print()` en production — passer par `log/`
- Pas de gestion d'erreurs pour des cas impossibles — ne pas sur-défendre le code
- Pas d'abstraction prématurée — trois lignes similaires valent mieux qu'une abstraction inutile
