# Contributing to cartograph

Standards de développement du projet. Ces règles s'appliquent à tout contributeur humain ou IA (Claude Code inclus).

---

## Type hints

Obligatoires partout — arguments, valeurs de retour, variables ambiguës.

```python
def process(data: list[str], limit: int = 10) -> dict[str, int]: ...
```

- `mypy --strict` doit passer sans erreur
- Pas de `Any` sauf cas justifié par un commentaire

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

- Si un contrôle corrige un fichier, le commit est refusé : relire la correction, `git add`, recommencer le commit.
- « Stashing unstaged files » : les modifications hors du commit sont mises de côté pendant les contrôles, puis remises.
- `git commit --no-verify` saute les contrôles pour un commit de travail ; ils restent dus avant la pull request.
- `tests/fixtures/` (réponses enregistrées de l'API) n'est jamais modifié.

Avant une pull request :

```bash
uv run inv ci          # pre-commit sur tous les fichiers, mypy, pytest
uv run inv okflint     # en-tête et liens des specs et plans locaux de docs/
```

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

---

## Git

- Branches : `feature/<sujet>` (développement, créée depuis `develop`), `develop` (qualité), `main` (production, jamais modifiée en local)
- Cycle :
  1. `feature/…` se pousse librement et rejoint `develop` par une pull request ;
  2. sur `develop` : `uv run inv release --dry-run` (version suivante et changelog, sans rien modifier), puis `uv run inv release` (pull, contrôles, `cz bump`, documentation, push avec le tag) ;
  3. `develop` rejoint `main` par une pull request.
- Pull requests fusionnées en **merge commit** uniquement : un squash réduirait le changelog à une ligne et, comme un rebase, laisserait le commit tagué hors de `main`
- Mettre une branche feature à jour après une release : `git fetch origin && git merge origin/develop`
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

## Règles générales

- Commenter le **pourquoi**, jamais le **quoi** (le code doit se lire seul)
- Pas de code mort commenté — git conserve l'historique
- Pas de `print()` en production — passer par `log/`
- Pas de gestion d'erreurs pour des cas impossibles — ne pas sur-défendre le code
- Pas d'abstraction prématurée — trois lignes similaires valent mieux qu'une abstraction inutile
