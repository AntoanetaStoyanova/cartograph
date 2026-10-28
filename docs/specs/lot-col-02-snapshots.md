# Spec — COL-02 Snapshots Parquet

*Rédigé le : 28 octobre 2026*

## Contexte

Deuxième lot de la collecte dans la [feuille de route](../plans/roadmap-lots.md) (F3, N3 de la [spec maîtresse](Spécification%20du%20projet%20final%20M2%20plateforme%20de%20données%20Pokémon%20TCG%20(1).md)). [COL-01](lot-col-01-client-tcgdex.md) renvoie en mémoire le JSON brut : `fetch_catalogue` (fiches complètes d'une langue) et `fetch_prices` (un enregistrement `{"language", "card_id", "id_product", "fetched_at", "pricing"}` par produit Cardmarket), chacun avec la liste des cartes en échec.

Le [cadrage des flux](cadrage-flux.md) prévoit un seul workflow quotidien : le jour du catalogue (ou sur paramètre), catalogue puis prix ; un échec du catalogue ne bloque pas les prix, collectés avec le catalogue précédent.

Constaté sur les fixtures le 28 octobre 2026 : la fiche complète contient des prix à deux endroits, `pricing` et `variants_detailed[].pricing`. Le catalogue est destiné à être publié (`cartograph-data`, T8) : il doit être écrit sans aucun prix.

## Objectif

Une commande `inv collect` qui écrit les snapshots datés du jour (`prices-AAAA-MM-JJ.parquet` chaque jour, `cards-AAAA-MM-JJ.parquet` le jour du catalogue), la réponse brute compressée et un résumé d'exécution sans prix, en remplaçant les fichiers du jour si on la relance.

## Périmètre

- Dépendance `pyarrow`.
- Chemins de sortie dans `cartograph.config`.
- Module `cartograph.bin.collect.snapshot` : schémas, conversion en tables, retrait des prix du catalogue, écriture atomique.
- Module `cartograph.bin.collect.run` : enchaînement catalogue → prix, lecture du dernier catalogue, résumé, code de sortie, point d'entrée en ligne de commande.
- Tâche `inv collect`.

## Hors périmètre

- Envoi vers les Releases et manifeste (STO-01), archivage mensuel du brut (STO-03), workflow planifié et choix du jour du catalogue (ORC-01).
- Mesures de taille et de durée (COL-T3), Parquet en delta.
- Embeddings des nouvelles cartes (EMB-03).
- Lecture dbt des snapshots (DBT-01) ; l'échantillon versionné pour la CI dbt est produit là-bas.

## Décisions

| Sujet | Décision | Raison |
| --- | --- | --- |
| Bibliothèque | `pyarrow` | Schéma explicite, zstd, tri ; lu directement par DuckDB et dbt ; une seule dépendance |
| Schéma des prix | Colonnes typées fixes : `language`, `card_id`, `id_product` (int64), `fetched_at` (timestamp UTC), `cm_updated` (timestamp UTC), `cm_unit`, `cm_avg`, `cm_low`, `cm_trend`, `cm_avg1`, `cm_avg7`, `cm_avg30` et leurs versions `_holo` (float64, nul si absent), `tcgplayer_json` (texte, nul si absent) | Prix stables et typés pour dbt ; TCGplayer presque toujours nul, gardé brut tant que sa forme n'est pas connue |
| Champs Cardmarket inconnus | Ignorés dans le Parquet, conservés dans le brut ; leurs noms (jamais leurs valeurs) journalisés une fois par exécution | Le schéma ne casse pas si l'API ajoute un champ ; l'ajout est visible |
| Schéma du catalogue | Colonnes clés : `language`, `card_id`, `local_id`, `name`, `set_id`, `set_name`, `rarity`, `category`, `illustrator`, `image`, `id_product` (int64, nul si absent), `updated` (timestamp UTC), `fetched_at`, plus `raw_json` (fiche complète sans prix) | dbt extrait les autres champs du JSON ; schéma robuste aux changements de l'API |
| Prix dans le catalogue | Toute clé `pricing`, à n'importe quelle profondeur (`pricing`, `variants_detailed[].pricing`), retirée avant l'écriture du catalogue ; `id_product` gardé (identifiant, pas un prix) | Le catalogue est publiable (T8) ; les prix ne le sont jamais |
| Tri et compression | Tri par `card_id` puis `language` ; zstd | Spec maîtresse ; lecture et compression meilleures |
| Date du snapshot | Date UTC du début de l'exécution | Un seul jour par exécution, même si elle passe minuit |
| Dossier de sortie | `DATA_DIR = <racine>/data`, ignoré par Git ; `snapshots/` (Parquet), `raw/` (JSON brut gzip), `runs/` (résumés) ; dossier modifiable par paramètre | Rien de local dans le dépôt ; le workflow choisira son dossier |
| Brut | `raw/cards-AAAA-MM-JJ.json.gz` et `raw/prices-AAAA-MM-JJ.json.gz` : réponses complètes, prix compris ; écrit avant la conversion en table : une réponse de forme inattendue fait échouer l'étape sans perdre la collecte (erreur notée par son type seul, son message pouvant contenir un prix) | F3 ; contient des prix, donc uniquement local ou dépôt privé (STO-03) |
| Idempotence | Écriture dans un fichier temporaire du même dossier puis `os.replace` ; relancer le même jour remplace les fichiers du jour | N3 ; un fichier n'est jamais à moitié écrit |
| Catalogue | Tout ou rien : si une langue échoue (liste indisponible ou arrêt après `MAX_CONSECUTIVE_FAILURES`), aucun `cards-*.parquet` n'est écrit ; les cartes isolées en échec n'empêchent pas l'écriture | Un catalogue incomplet ferait disparaître des cartes des prix suivants |
| Catalogue des prix | Le catalogue du jour s'il vient d'être écrit, sinon le `cards-*.parquet` le plus récent du dossier ; aucun catalogue → prix en échec ; langues demandées absentes du catalogue notées (`missing_languages`) et journalisées, échec si aucune n'y figure | Échec du catalogue non bloquant (cadrage) ; les cibles se déduisent des colonnes `language`, `card_id`, `id_product` |
| Cibles depuis le Parquet | `price_targets` refactorisé autour d'une déduplication commune, utilisable depuis les fiches (COL-01) ou depuis les lignes du catalogue | Une seule règle « première carte par `idProduct` dans l'ordre de `LANGUAGES` » |
| Résumé | `runs/collect-AAAA-MM-JJ.json` : date, début, fin, et par étape statut (`ok`, `failed`, `skipped`), nombres (récupérées, en échec, ignorées sans `idProduct`), identifiants en échec, fichiers écrits (nom, lignes, octets), catalogue utilisé pour les prix ; aucun prix | Base du manifeste (STO-01) et du résumé d'exécution (SUR-01) |
| Code de sortie | 0 si chaque étape demandée est `ok` (cartes isolées en échec comprises), 1 sinon | Le workflow échoue et alerte (SUR-01) ; un trou de quelques cartes est suivi par la surveillance |
| Interface | `python -m cartograph.bin.collect.run [--catalogue] [--no-prices] [--languages fr,en] [--data-dir PATH]` ; `inv collect` avec les mêmes options | Le workflow (ORC-01) choisit le jour du catalogue et passe `--catalogue` ; aucun calendrier dans le code ; `run.py` est l'orchestrateur (pas de `__main__.py` dans `bin/`, voir CONTRIBUTING) |
| Import dans `tasks` | `inv collect` lance la commande avec `c.run`, sans importer `cartograph` | Les autres tâches (`lint`, `ci`) ne dépendent pas de `.env` |

## Critères d'acceptation

- [x] `inv collect --catalogue` écrit `cards-`, `prices-` (Parquet zstd triés), les deux bruts gzip et le résumé du jour.
- [x] `inv collect` sans `--catalogue` utilise le `cards-*.parquet` le plus récent ; sans aucun catalogue, l'étape prix est `failed` et le code de sortie vaut 1.
- [x] Relancer le même jour remplace les fichiers du jour, sans doublon.
- [x] Le Parquet du catalogue et le résumé ne contiennent aucun prix (test sur les valeurs des fixtures).
- [x] Les types des colonnes de prix sont ceux du schéma (test), quels que soient les champs absents.
- [x] Une langue en échec n'écrit aucun catalogue, les prix tournent avec le catalogue précédent et le code de sortie vaut 1.
- [x] Les tests n'appellent pas le réseau.
- [x] `uv run inv ci` passe, couverture ≥ 88 %.
