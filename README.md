# cartograph

Une plateforme de données qui suit les prix des cartes Pokémon, identifie une carte à partir d’une photo et estime sa valeur.

## Auteur

Antoaneta Stoyanova

## Prérequis

Le projet se développe sous **WSL 2 (Ubuntu)**, le même système que la CI (GitHub Actions sur Ubuntu) :
mêmes chemins, mêmes fins de ligne, mêmes paquets compilés ; dbt, DuckDB et OpenCV s'y installent
sans contournement. Toutes les commandes (`uv`, `inv`, `git`, `dbt`) se lancent dans le terminal WSL,
jamais dans PowerShell.

- WSL 2 + Ubuntu, avec `git`, `curl`, `build-essential`
- Accès GitHub par SSH
- [uv](https://docs.astral.sh/uv/) (installe Python 3.13 depuis `.python-version`)
- VS Code + extension WSL (extensions Python et Ruff installées côté WSL)
- [cruft](https://cruft.github.io/cruft/) — pour mettre à jour le template

Mise en place pas à pas : [lot-fnd-00-poste](docs/plans/lot-fnd-00-poste.md).

## Installation

```bash
git clone git@github.com:AntoanetaStoyanova/cartograph.git
cd cartograph
uv sync
cp .env.example .env
```

## Utilisation

```bash
uv run python -m cartograph
```

## Mettre à jour depuis le template

```bash
cruft update
```
