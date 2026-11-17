# cartograph

[![CI](https://github.com/AntoanetaStoyanova/cartograph/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/AntoanetaStoyanova/cartograph/actions/workflows/ci.yml)

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

## État du projet

- **En service** : collecte quotidienne des prix et des nouvelles cartes, collecte hebdomadaire du catalogue et des sets depuis [TCGdex](https://tcgdex.dev), en français, anglais et japonais (voir « Collecte » et « Collecte automatique »).
- **À venir** : base de données reconstruite en local avec dbt et DuckDB, identification d'une carte à partir d'une photo, modèle d'estimation du prix, application locale.
- **Pilotage** : calendrier, rapports de suivi mensuels (`inv suivi`) et bilan Green IT dans [`docs/gouvernance/`](docs/gouvernance/).

## Collecte

```bash
uv run inv collect                            # nouvelles cartes puis prix, avec le dernier catalogue
uv run inv collect --catalogue                # catalogue, sets puis prix
uv run inv collect --catalogue --no-prices    # catalogue et sets
uv run inv collect --languages fr,ja --data-dir /tmp/cartograph
```

Les sorties vont dans `data/` (ignoré par Git), un fichier par jour, remplacé si on relance le même jour :

- `data/snapshots/` : `cards-AAAA-MM-JJ.parquet` (catalogue), `sets-AAAA-MM-JJ.parquet` (sets avec date de sortie), `new-cards-AAAA-MM-JJ.parquet` (cartes absentes du dernier catalogue, seulement s'il y en a), tous trois sans aucun prix, et `prices-AAAA-MM-JJ.parquet` (prix du catalogue et des nouvelles cartes) ;
- `data/raw/` : réponses brutes de l'API en JSON gzip, **prix compris : jamais publiées** ;
- `data/runs/` : résumé `collect-AAAA-MM-JJ.json` (statut, nombres, fichiers écrits, sans prix).

Le code de sortie vaut 1 si une étape échoue. Un échec des sets ou des nouvelles cartes ne bloque ni le catalogue ni les prix. Les logs vont dans `logs/`.

## Collecte automatique

Le workflow `Collecte` du dépôt public [`cartograph-data`](https://github.com/AntoanetaStoyanova/cartograph-data) installe ce dépôt depuis `main` et lance la collecte. Il est déclenché chaque jour à 03:17 UTC par [cron-job.org](https://cron-job.org), qui appelle l'API GitHub `workflow_dispatch` : le cron de GitHub Actions ne garantit pas ses déclenchements. À chaque exécution :

- prix chaque jour (1 h à 1 h 30), avec le dernier catalogue publié : avant les prix, les listes de cartes de chaque langue sont comparées à ce catalogue et seules les fiches des cartes absentes sont téléchargées (`new_cards`), leurs prix tirés de ces fiches ;
- le lundi (paramètre `catalogue` à `auto`), catalogue (2 h 30 à 3 h 15 selon les erreurs 503 de TCGdex) puis sets (`/<langue>/sets`, avec date de sortie), les prix étant lus dans les fiches du catalogue sans nouvel appel à l'API ;
- résumé écrit après chaque étape suivie d'une autre, puis à la fin : une exécution coupée pendant les sets ou les prix publie quand même ce qui est écrit ;
- `cards-*`, `sets-*` et `new-cards-*.parquet` publiés dans la Release `catalogue` de `cartograph-data` ;
- prix et brut envoyés dans la Release `data-AAAA-MM` du dépôt privé `cartograph-prices` (secret `PRICES_TOKEN`) ;
- résumé et log gardés 7 jours en artefact, sans aucun prix ;
- manifeste `manifest/AAAA/AAAA-MM-JJ.json` commité dans `cartograph-data`, même si la collecte échoue : statut des étapes, fichiers envoyés (Release, lignes, octets, SHA-256) et taille du dépôt, sans aucun prix. Il est calculé avant les envois et donne la Release de chaque fichier ; `sha256sum` d'un fichier téléchargé doit redonner son `sha256`.

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

## Données et licences

- **Catalogue** : il provient de [TCGdex](https://github.com/tcgdex/cards-database), sous licence MIT, © TCGdex. Il est republié sans images dans la Release `catalogue` de [`cartograph-data`](https://github.com/AntoanetaStoyanova/cartograph-data).
- **Prix** : les prix Cardmarket et TCGplayer et les réponses brutes de l'API ne sont jamais publiés. Les prix TCGplayer appartiennent à TCGplayer, et ceux de Cardmarket relèvent du droit des bases de données. Ils sont conservés dans un dépôt privé, `cartograph-prices`. Seuls le catalogue, le manifeste et des résultats dérivés, sans prix par carte, sont publics.

## Avertissement

Ce projet n'est ni produit ni soutenu par Nintendo, The Pokémon Company, Creatures ou Game Freak. Pokémon et les noms associés sont des marques de leurs propriétaires.

## Licence

Le code est sous licence MIT (voir [`LICENSE`](LICENSE)). Les données collectées gardent la licence de leur source.
