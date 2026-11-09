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

## Collecte

```bash
uv run inv collect                            # prix du jour, avec le dernier catalogue
uv run inv collect --catalogue                # catalogue puis prix
uv run inv collect --catalogue --no-prices    # catalogue seul
uv run inv collect --languages fr,ja --data-dir /tmp/cartograph
```

Les sorties vont dans `data/` (ignoré par Git), un fichier par jour, remplacé si on relance le même jour :

- `data/snapshots/` : `cards-AAAA-MM-JJ.parquet` (catalogue, sans aucun prix) et `prices-AAAA-MM-JJ.parquet` ;
- `data/raw/` : réponses brutes de l'API en JSON gzip, **prix compris : jamais publiées** ;
- `data/runs/` : résumé `collect-AAAA-MM-JJ.json` (statut, nombres, fichiers écrits, sans prix).

Le code de sortie vaut 1 si une étape demandée échoue. Les logs vont dans `logs/`.

## Collecte automatique

Le workflow `Collecte` du dépôt public [`cartograph-data`](https://github.com/AntoanetaStoyanova/cartograph-data) installe ce dépôt depuis `main` et lance la collecte. Il est déclenché chaque jour à 03:17 UTC par [cron-job.org](https://cron-job.org), qui appelle l'API GitHub `workflow_dispatch` : le cron de GitHub Actions ne garantit pas ses déclenchements. À chaque exécution :

- prix chaque jour (1 h à 1 h 30), avec le dernier catalogue publié ; le lundi (paramètre `catalogue` à `auto`), catalogue seul (2 h 30 à 3 h 15 selon les erreurs 503 de TCGdex), les prix étant lus dans ses fiches sans nouvel appel à l'API ;
- résumé écrit après le catalogue puis à la fin : une exécution coupée pendant les prix publie quand même le catalogue ;
- catalogue publié dans la Release `catalogue` de `cartograph-data` ;
- prix et brut envoyés dans la Release `data-AAAA-MM` du dépôt privé `cartograph-prices` (secret `PRICES_TOKEN`) ;
- résumé et log gardés 7 jours en artefact, sans aucun prix.

Surveillance :

- bilan de chaque exécution dans sa page (*Summary*) : statut par étape, nombres, cartes en échec, fichiers écrits, durée, sans aucun prix ;
- [healthchecks.io](https://healthchecks.io) reçoit un signal au début et à la fin de chaque exécution, et envoie un e-mail si la collecte échoue ou si aucune collecte réussie n'arrive avant 08:17 UTC (collecte non lancée, exécution bloquée) ;
- GitHub envoie un e-mail quand une exécution échoue.
- cron-job.org envoie un e-mail quand son appel échoue ou que la tâche est désactivée.

Relance manuelle : onglet *Actions* de `cartograph-data`, `Collecte`, *Run workflow* (options `catalogue` : `auto` le lundi, `oui` ou `non` pour forcer ; `prices`, `languages`, `code_ref`). Un lundi, `auto` relance aussi le catalogue : choisir `non` pour les prix seuls. Relancer le même jour remplace les fichiers du jour. Une exécution sans `catalogue` reprend le dernier catalogue publié.

## Mettre à jour depuis le template

```bash
cruft update
```
