---
type: reference
statut: en cours
redige_le: 2026-11-19
---

# Règles métier

*Rédigé le 19 novembre 2026. Tenu à jour par chaque lot qui ajoute, change ou retire une règle ; relu et validé par Antoaneta à la clôture de DBT-06.*

Ce document liste les règles appliquées par la collecte et par la base dbt : ce que fait Cartograph de ses données, où c'est écrit dans le code, et quel test le garantit.

## Mode d'emploi

Une table par famille. Chaque ligne a cinq colonnes :

- **ID** : `R-<FAMILLE>-<nn>`, jamais réutilisé, même pour une règle retirée ; le préfixe `R-` distingue la règle du lot (`R-COL-05` est une règle, `COL-05` le lot de collecte du même numéro) ;
- **Règle** : une phrase, lisible sans ouvrir le code ;
- **Appliquée dans** : le module, la fonction, le modèle dbt ou le workflow qui l'applique ;
- **Garantie par** : le nom exact du test (pytest `tests/<fichier>.py::<test>`, test unitaire, générique ou singulier dbt), ou « aucun » ;
- **Origine** : le lot qui l'a introduite, et « décision d'Antoaneta » quand c'est un choix de sa part.

Chaque règle a été vérifiée dans le code, pas recopiée des specs. Aucun prix réel n'apparaît ici, seulement des règles et des comptes.

Une règle abandonnée quitte sa famille et passe dans « Règles retirées », avec sa date et ce qui la remplace. Une règle de la section « À venir » remonte dans sa famille quand son lot est livré.

## COL — Collecte

Code dans `src/cartograph/bin/collect/`, tests dans `tests/test_collect_*.py`. Le workflow `Collecte` est dans le dépôt `cartograph-data`.

| ID | Règle | Appliquée dans | Garantie par | Origine |
| -- | ----- | -------------- | ------------ | ------- |
| R-COL-01 | La collecte est lancée chaque jour à 03:17 UTC par cron-job.org, qui déclenche le workflow `Collecte` ; le cron de GitHub Actions n'est pas utilisé. | cron-job.org, workflow `Collecte` de `cartograph-data` | aucun (surveillance healthchecks.io) | ORC-01, ORC-02 |
| R-COL-02 | La collecte complète du catalogue (toutes les fiches) ne se lance qu'à la main, pour un amorçage ou une réparation. | `run.main` (`--catalogue`), paramètre `catalogue` du workflow | `tests/test_collect_run.py::test_main_defaults` | COL-05, décision d'Antoaneta |
| R-COL-03 | Trois langues sont collectées : `fr`, `en`, `ja` ; toute autre langue est refusée. | `config.LANGUAGES`, `run._languages` | `tests/test_collect_run.py::test_main_rejects_invalid_options`, `tests/test_collect_catalogue.py::test_fetch_catalogue_rejects_unknown_language` | FND-01 |
| R-COL-04 | Ordre des étapes : catalogue complet s'il est demandé, sets, nouvelles cartes, prix, puis mise à jour du catalogue. | `run.collect` | `tests/test_collect_run.py::test_collect_without_catalogue_collects_sets_first`, `tests/test_collect_run.py::test_collect_with_catalogue_writes_all_files` | COL-04, COL-05 |
| R-COL-05 | Le jour d'un fichier est la date UTC du début de la collecte, et toutes les heures sont en UTC. | `run.collect`, `snapshot.snapshot_paths` | `tests/test_collect_run.py::test_collect_day_is_utc_date_of_start`, `tests/test_collect_run.py::test_collect_uses_utc_timestamps` | COL-02 |
| R-COL-06 | Le catalogue du jour (`cards-*`) est celui de la veille mis à jour avec les fiches reçues avec les prix, les nouvelles cartes et une rotation de 1 000 fiches. | `run._update_catalogue`, `incremental.merge_catalogue` | `tests/test_collect_run.py::test_collect_daily_writes_catalogue_and_changes`, `tests/test_collect_run.py::test_collect_two_daily_runs_chain_catalogues` | COL-05 |
| R-COL-07 | Le catalogue de la veille est le `cards-*` le plus récent antérieur au jour ; un `new-cards-*` n'en est jamais un. | `snapshot.latest_catalogue` | `tests/test_collect_snapshot.py::test_latest_catalogue_before_day_skips_same_day`, `tests/test_collect_new_cards.py::test_latest_catalogue_ignores_new_cards` | COL-04, COL-05 |
| R-COL-08 | La rotation relit les fiches lues il y a le plus longtemps, hors cartes interrogées pour les prix et hors cartes disparues. | `incremental.rotation_ids`, `config.ROTATION_SIZE` | `tests/test_collect_incremental.py::test_rotation_ids_oldest_first_without_targets_and_removed`, `tests/test_collect_run.py::test_collect_daily_rotation_reads_oldest_cards_outside_prices` | COL-05 |
| R-COL-09 | Une fiche est modifiée si son empreinte change : SHA-256 de la fiche triée, sans prix ni champ `updated`. | `snapshot.card_fingerprint`, `incremental.changed_cards` | `tests/test_collect_snapshot.py::test_card_fingerprint_ignores_updated_and_pricing`, `tests/test_collect_incremental.py::test_changed_cards_separates_changed_and_identical` | COL-05 |
| R-COL-10 | Une carte absente des listes de l'API reçoit la date de sa disparition (`removed_on`) et reste au catalogue ; si elle revient, `removed_on` est effacé. Une liste vide ne retire rien. | `catalogue.listing_diff`, `incremental.apply_listing` | `tests/test_collect_incremental.py::test_apply_listing_sets_and_clears_removed_on`, `tests/test_collect_run.py::test_collect_full_catalogue_marks_removed_then_reappeared_card`, `tests/test_collect_catalogue.py::test_listing_diff_empty_listing_removes_nothing` | COL-05 |
| R-COL-11 | Une fiche en échec garde sa ligne du catalogue de la veille. | `incremental.merge_catalogue`, `run._collect_catalogue` | `tests/test_collect_run.py::test_collect_daily_failed_price_card_keeps_previous_row`, `tests/test_collect_run.py::test_collect_catalogue_day_failed_card_keeps_previous_row` | COL-05 |
| R-COL-12 | Les changements du jour (carte nouvelle, modifiée, disparue, revenue) sont écrits dans `card-changes-*`. | `incremental.card_changes_table` | `tests/test_collect_incremental.py::test_card_changes_table_lists_each_change` | COL-05 |
| R-COL-13 | Nouvelles cartes : les listes de l'API sont comparées au catalogue de la veille, seules les fiches absentes sont téléchargées et leurs prix sont lus dans ces fiches ; `new-cards-*` n'est écrit que s'il y en a. | `run._collect_new_cards`, `prices.new_card_targets` | `tests/test_collect_run.py::test_collect_new_card_has_card_and_price`, `tests/test_collect_run.py::test_collect_without_new_card_writes_no_file`, `tests/test_collect_run.py::test_collect_new_card_with_known_product_is_not_doubled` | COL-04 |
| R-COL-14 | Les prix sont demandés une fois par produit Cardmarket : la première carte trouvée dans l'ordre `fr`, `en`, `ja` représente le produit ; une carte sans identifiant produit est ignorée et comptée ; une carte disparue n'est pas interrogée. | `prices.price_targets_from_catalogue` | `tests/test_collect_prices.py::test_price_targets_deduplicates_european_products`, `tests/test_collect_prices.py::test_price_targets_skips_cards_without_id_product`, `tests/test_collect_prices.py::test_price_targets_from_catalogue_ignores_removed_cards` | COL-01 |
| R-COL-15 | Le jour d'une collecte complète, les prix sont lus dans les fiches du catalogue, sans second appel à l'API. | `prices.prices_from_cards`, `run.collect` | `tests/test_collect_run.py::test_collect_with_catalogue_requests_each_card_once`, `tests/test_collect_prices.py::test_prices_from_cards_matches_fetch_prices` | Optimisation de la collecte (9 novembre 2026) |
| R-COL-16 | La collecte complète est tout ou rien : si une langue échoue, aucun `cards-*` n'est écrit, et les prix partent du dernier catalogue. | `run._collect_catalogue` | `tests/test_collect_run.py::test_collect_failed_language_writes_no_catalogue_but_prices` | COL-02 |
| R-COL-17 | Un échec des sets ou des nouvelles cartes ne bloque ni le catalogue ni les prix. | `run.collect` | `tests/test_collect_run.py::test_collect_failed_sets_keep_catalogue_and_prices`, `tests/test_collect_run.py::test_collect_failed_sets_keep_new_cards_and_prices`, `tests/test_collect_run.py::test_collect_failed_card_list_keeps_prices` | COL-04 |
| R-COL-18 | Après 20 échecs d'affilée, l'API est jugée en panne et l'étape s'arrête ; les prix et les fiches reçus avant l'arrêt sont écrits, et l'étape est en échec. | `batch.py`, `config.MAX_CONSECUTIVE_FAILURES` | `tests/test_collect_failures.py::test_fetch_prices_stops_after_consecutive_failures`, `tests/test_collect_run.py::test_collect_prices_stopped_by_outage_writes_prices_received`, `tests/test_collect_run.py::test_main_rotation_stopped_by_outage_writes_catalogue` | COL-01, audit du 18 novembre 2026 |
| R-COL-19 | Une réponse de l'API de forme inattendue fait échouer l'étape sans perdre le brut ; seul le type de l'erreur est noté, jamais son message, qui peut contenir un prix. | `run._write_table` | `tests/test_collect_run.py::test_collect_bad_price_keeps_raw_prices_and_leaks_nothing`, `tests/test_collect_run.py::test_collect_bad_card_keeps_raw_catalogue` | COL-02 |
| R-COL-20 | Le résumé est écrit après chaque étape, les étapes restantes marquées en échec : une collecte coupée publie quand même ce qui est écrit. | `run.collect` (`checkpoint`) | `tests/test_collect_run.py::test_collect_writes_summary_after_each_step`, `tests/test_collect_run.py::test_collect_interrupted_prices_keep_catalogue_summary` | Optimisation de la collecte (9 novembre 2026) |
| R-COL-21 | Le code de sortie vaut 1 si une étape demandée échoue, 0 sinon. | `run.main` | `tests/test_collect_run.py::test_main_returns_one_when_a_step_fails`, `tests/test_collect_run.py::test_main_returns_one_when_new_cards_fail` | COL-02 |
| R-COL-22 | Relancer le même jour remplace les fichiers du jour sans jamais laisser de fichier à moitié écrit, et repart du catalogue de la veille. | `snapshot.write_parquet` (écriture atomique), `snapshot.latest_catalogue` | `tests/test_collect_run.py::test_collect_same_day_replaces_files`, `tests/test_collect_snapshot.py::test_write_atomic_failure_keeps_previous_file`, `tests/test_collect_run.py::test_collect_same_day_rerun_starts_from_previous_catalogue` | COL-02, COL-05 |
| R-COL-23 | Les prix sont privés : `prices-*` et les réponses brutes vont dans le dépôt privé `cartograph-prices` ; `cards-*`, `sets-*`, `new-cards-*` et `card-changes-*` ne contiennent aucun prix et sont publics (Release `catalogue` de `cartograph-data`). | `snapshot.catalogue_table`, `manifest._release`, workflow `Collecte` | `tests/test_collect_snapshot.py::test_card_table_contains_no_price`, `tests/test_collect_run.py::test_collect_daily_catalogue_leaks_no_price`, `tests/test_collect_manifest.py::test_new_cards_parquet_is_public_and_raw_is_private`, `tests/test_collect_manifest.py::test_catalogue_parquet_goes_to_public_release` | COL-T8, décision d'Antoaneta |
| R-COL-24 | Le résumé, le bilan d'exécution et le manifeste ne contiennent aucun prix. | `run._write_summary`, `report.py`, `manifest.build_manifest` | `tests/test_collect_run.py::test_collect_summary_contains_no_price`, `tests/test_collect_report.py::test_real_summary_contains_no_price`, `tests/test_collect_manifest.py::test_real_summary_contains_no_price` | SUR-01, STO-01 |
| R-COL-25 | Un manifeste est commité chaque jour dans `cartograph-data`, même si la collecte échoue : statut des étapes, lignes, octets et SHA-256 de chaque fichier envoyé. | `manifest.build_manifest`, workflow `Collecte` | `tests/test_collect_manifest.py::test_successful_collection_lists_files_with_release_and_sha256`, `tests/test_collect_manifest.py::test_no_summary_gives_empty_steps_and_files` | STO-01 |
| R-COL-26 | La Release `catalogue` ne garde que le `cards-*` le plus récent et ceux des lundis. | workflow `Collecte` de `cartograph-data` | aucun | COL-05 |

## CAT — Catalogue

Modèles dans `dbt/models/`, macros dans `dbt/macros/`. Un test unitaire dbt est nommé par son `name` dans le `.yml` du modèle ; un test générique par `<modèle>.<colonne>` et son type ; l'unicité d'une clé à plusieurs colonnes est testée sur leur concaténation (`a || '|' || b`).

| ID | Règle | Appliquée dans | Garantie par | Origine |
| -- | ----- | -------------- | ------------ | ------- |
| R-CAT-01 | La date d'un snapshot est tirée du nom du fichier (`cards-AAAA-MM-JJ.parquet`), pas de son contenu. | macro `snapshot_date` | test unitaire `stg_tcgdex__cards_keeps_latest_version`, `stg_tcgdex__cardmarket_prices_unpivots_finishes` | DBT-01 |
| R-CAT-02 | Une carte a une seule ligne par langue, dans sa version la plus récente ; le même jour, le catalogue l'emporte sur `new-cards`. | `stg_tcgdex__cards` | `unique` sur `card_id \|\| '\|' \|\| language_code` de `stg_tcgdex__cards` ; test unitaire `stg_tcgdex__cards_keeps_latest_version` | DBT-01, COL-04 |
| R-CAT-03 | Une carte est courante si elle figure sans `removed_on` dans le dernier catalogue, ou dans un `new-cards` plus récent que lui. | `stg_tcgdex__cards` (`is_current`), macro `is_new_cards` | tests unitaires `stg_tcgdex__cards_counts_new_cards`, `stg_tcgdex__cards_reads_removed_on` | DBT-01, COL-04, COL-05 |
| R-CAT-04 | Une carte retirée de TCGdex reste dans la base, non courante, avec sa date de retrait et la date du dernier fichier où elle était présente (`last_seen_on`). | `stg_tcgdex__cards`, `dim_card` | test unitaire `stg_tcgdex__cards_reads_removed_on`, `dim_card_excludes_pocket_and_maps_rarity` | DBT-01, COL-05 |
| R-CAT-05 | La catégorie est ramenée à `pokemon`, `trainer` ou `energy`, quelle que soit la langue ; une autre valeur arrête le build. | `stg_tcgdex__cards` | `stg_tcgdex__cards.category` `accepted_values` ; test unitaire `stg_tcgdex__cards_keeps_latest_version` | DBT-01 |
| R-CAT-06 | Seules les langues `fr`, `en` et `ja` sont acceptées dans la base. | `stg_tcgdex__cards`, `stg_tcgdex__sets` | `stg_tcgdex__cards.language_code` et `stg_tcgdex__sets.language_code` `accepted_values` | DBT-01 |
| R-CAT-07 | Un set a une seule ligne par langue, tirée du dernier fichier `sets-*` où il figure ; il est courant s'il figure dans le dernier. | `stg_tcgdex__sets` | `unique` sur `set_id \|\| '\|' \|\| language_code` de `stg_tcgdex__sets` ; test unitaire `stg_tcgdex__sets_keeps_latest_version` | DBT-01, COL-04 |
| R-CAT-08 | TCG Pocket (jeu numérique, sans prix) est écarté : un set classé dans la série `tcgp` dans une langue l'est dans toutes, avec ses cartes et ses produits. | macro `not_pocket_set`, `dim_set`, `dim_card`, `int_cardmarket_products` | tests unitaires `dim_set_excludes_pocket`, `dim_card_excludes_pocket_and_maps_rarity` | DBT-04 |
| R-CAT-09 | Une carte doit avoir son set dans sa langue ; seule exception, les 9 cartes `pl4-AR*` en `fr`, qui ont un prix mais pas de set chez TCGdex, sont gardées sans set. | `dim_card` | test singulier `assert_card_set_exists` | DBT-04 |

## PRX — Prix

| ID | Règle | Appliquée dans | Garantie par | Origine |
| -- | ----- | -------------- | ------------ | ------- |
| R-PRX-01 | Le prix appartient au produit Cardmarket, pas à la carte : plusieurs cartes (une par langue, parfois plusieurs dans une langue) partagent un produit et son prix. | `stg_tcgdex__cardmarket_prices`, `fct_price_snapshot` (sans `card_id`) | `unique` sur `cardmarket_product_id \|\| '\|' \|\| finish \|\| '\|' \|\| price_date` de `stg_tcgdex__cardmarket_prices` et de `fct_price_snapshot` | COL-01, DBT-02 |
| R-PRX-02 | Cardmarket et TCGplayer ont chacun leur modèle, avec leurs finitions et leur devise ; ils ne sont pas mélangés. | `stg_tcgdex__cardmarket_prices`, `stg_tcgdex__tcgplayer_prices` | `stg_tcgdex__cardmarket_prices.currency_code` `accepted_values` (`EUR`), `stg_tcgdex__tcgplayer_prices.currency_code` `accepted_values` (`USD`) | DBT-02 |
| R-PRX-03 | Cardmarket a deux finitions : `base`, et `reverse_holo` pour le reverse ; le « holo » des colonnes TCGdex (`cm_*_holo`) est le reverse de Cardmarket, pas une carte holo. | `stg_tcgdex__cardmarket_prices` | `stg_tcgdex__cardmarket_prices.finish` et `fct_price_snapshot.finish` `accepted_values` ; test unitaire `stg_tcgdex__cardmarket_prices_unpivots_finishes` | DBT-02 |
| R-PRX-04 | Un prix à `0` est lu comme absent. | `stg_tcgdex__cardmarket_prices`, `stg_tcgdex__tcgplayer_prices` (`nullif`) | tests unitaires `stg_tcgdex__cardmarket_prices_unpivots_finishes`, `stg_tcgdex__tcgplayer_prices_unpivots_finishes` | DBT-02 |
| R-PRX-05 | Une finition sans aucun prix ne donne pas de ligne. | `stg_tcgdex__cardmarket_prices`, `stg_tcgdex__tcgplayer_prices` | tests unitaires `stg_tcgdex__cardmarket_prices_unpivots_finishes`, `stg_tcgdex__tcgplayer_prices_unpivots_finishes` | DBT-02 |
| R-PRX-06 | Une finition TCGplayer inconnue, un JSON TCGplayer invalide ou une date hors ISO 8601 arrêtent le build plutôt que de produire une valeur fausse. | `stg_tcgdex__tcgplayer_prices` | `stg_tcgdex__tcgplayer_prices.finish` `accepted_values` pour la finition ; aucun pour le JSON et la date (conversions du modèle) | DBT-02 |
| R-PRX-07 | TCGplayer sert au lien vers la page du produit (`tcgplayer_product_id`), pas au prix de référence. | `stg_tcgdex__tcgplayer_prices` | aucun | DBT-02 |
| R-PRX-08 | Aucun filtre sur les variantes déclarées d'une carte (`variants`) : une finition a une ligne dès qu'elle a un prix. | `stg_tcgdex__cardmarket_prices` | aucun | DBT-02 |
| R-PRX-09 | Tout produit de l'historique des prix est connu du catalogue (hors Pocket). | `fct_price_snapshot` | `fct_price_snapshot.cardmarket_product_id` `relationships` vers `int_cardmarket_products` (erreur) | DBT-04 |
| R-PRX-10 | Un produit est ambigu quand, dans une langue, ses cartes courantes ont plusieurs noms ou plusieurs codes de rareté : son prix n'a pas de carte sûre. Des noms différents entre langues ou une carte retirée ne le rendent pas ambigu. | `int_cardmarket_products`, repris dans `dim_card` | test unitaire `int_cardmarket_products_flags_ambiguity` ; test singulier `assert_no_ambiguous_product` (avertissement) | DBT-04 |
| R-PRX-11 | L'ambiguïté n'est évaluée que pour un produit qui a une carte courante (`has_current_card`) ; sinon elle vaut faux sans avoir été évaluée. | `int_cardmarket_products` | test unitaire `int_cardmarket_products_flags_ambiguity` | DBT-04 |
| R-PRX-12 | Un produit pouvant porter plusieurs cartes, tout agrégat de prix compte des produits distincts, pas des cartes. | description de `dim_card` et `fct_price_snapshot` | aucun | DBT-04 |

## RAR — Rareté

La correspondance des raretés est le seed `dbt/seeds/rarity_levels.csv`, relu à la main.

| ID | Règle | Appliquée dans | Garantie par | Origine |
| -- | ----- | -------------- | ------------ | ------- |
| R-RAR-01 | Chaque nom de rareté collecté, quelle que soit sa langue ou son écriture, reçoit un code commun aux langues (nom anglais en `snake_case`, ex. `Commune` et `Common` → `common`) ; la rareté brute reste dans `dim_card`. | seed `rarity_levels`, `int_rarity_mapping`, `dim_card` | `rarity_levels.rarity` et `int_rarity_mapping.rarity` `unique` ; test unitaire `int_rarity_mapping_one_row_per_collected_name` | DBT-03 |
| R-RAR-02 | Les raretés sont rangées sur une échelle de 8 niveaux, de 1 (`common`) à 8 ; un code n'a qu'un niveau. L'échelle est provisoire : DBT-06 la revoit sur les prix. | seed `rarity_levels` | `rarity_levels.rarity_level` `accepted_values` ; test singulier `assert_rarity_code_single_level` | DBT-03 |
| R-RAR-03 | Trois codes sont hors échelle, sans niveau : `none`, `promo` et `pocket` ; tous les autres en ont un. | seed `rarity_levels` | test singulier `assert_rarity_level_empty_iff_off_scale` | DBT-03 |
| R-RAR-04 | Une rareté vide est lue comme `None` et reçoit le code `none`. | `int_rarity_mapping`, `dim_card` (jointure sur `coalesce(rarity, 'None')`) | tests unitaires `int_rarity_mapping_one_row_per_collected_name`, `dim_card_excludes_pocket_and_maps_rarity` | DBT-03, DBT-04 |
| R-RAR-05 | Un nom de rareté collecté absent du seed arrête le build : il faut l'ajouter au seed avec son code et son niveau. | `int_rarity_mapping` | `int_rarity_mapping.rarity_code` `not_null` (erreur), `dim_card.rarity_code` `not_null` ; test unitaire `int_rarity_mapping_one_row_per_collected_name` | DBT-03 |

## HIS — Historique

| ID | Règle | Appliquée dans | Garantie par | Origine |
| -- | ----- | -------------- | ------------ | ------- |
| R-HIS-01 | L'historique des prix n'est jamais effacé : chaque build ajoute à `fct_price_snapshot` toutes les dates du staging absentes de la table, donc les jours manqués après un arrêt et un fichier plus ancien arrivé après coup ; une date déjà chargée n'est pas relue. | `fct_price_snapshot` (incrémentale par ajout) | tests unitaires `fct_price_snapshot_first_load`, `fct_price_snapshot_catches_up_missed_days`, `fct_price_snapshot_loads_late_dates` | DBT-04 |
| R-HIS-02 | Un fichier `prices-*` remplacé pour une date déjà chargée n'est pris en compte qu'après `dbt build --full-refresh --select fct_price_snapshot` ou `inv rebuild`. | `fct_price_snapshot` (description), `tasks.rebuild` | aucun | DBT-04 |
| R-HIS-03 | Un changement de colonnes de `fct_price_snapshot` arrête le build au lieu de modifier la table existante. | `fct_price_snapshot` (`on_schema_change = 'fail'`) | contrat du modèle (`contract.enforced`) | DBT-04 |
| R-HIS-04 | La base se reconstruit depuis les Releases : seuls les snapshots absents ou dont le SHA-256 a changé sont téléchargés, et un fichier dont le SHA-256 ne correspond pas est refusé. | `bin.rebuild` (`sync`, `download`) | `tests/test_rebuild.py::test_sync_downloads_only_missing_or_changed`, `tests/test_rebuild.py::test_download_rejects_wrong_sha` | STO-02 |
| R-HIS-05 | `inv rebuild` construit une base vide à part et ne remplace `data/cartograph.duckdb` que si le build réussit ; un téléchargement en échec arrête la tâche avant dbt. | `tasks.rebuild` | `tests/test_tasks_rebuild.py::test_rebuild_starts_from_empty_database`, `tests/test_tasks_rebuild.py::test_rebuild_replaces_database_on_success`, `tests/test_tasks_rebuild.py::test_rebuild_keeps_database_when_dbt_fails`, `tests/test_tasks_rebuild.py::test_rebuild_stops_before_dbt_when_download_fails` | STO-02 |

## QUA — Qualité et alertes

| ID | Règle | Appliquée dans | Garantie par | Origine |
| -- | ----- | -------------- | ------------ | ------- |
| R-QUA-01 | Un test dbt est bloquant par défaut : s'il échoue, `dbt build` est en échec et les modèles qui en dépendent ne sont pas construits. | `.yml` des modèles, `dbt/tests/` | aucun (comportement de dbt) | DBT-01 |
| R-QUA-02 | Seul test en avertissement, les produits ambigus sont signalés sans bloquer le build : ce sont des erreurs de correspondance connues de TCGdex. | test singulier `assert_no_ambiguous_product` (`severity = 'warn'`) | test singulier `assert_no_ambiguous_product` | DBT-04 |
| R-QUA-03 | Chaque modèle déclare ses colonnes et leurs types ; une colonne en trop, absente ou d'un autre type arrête le build. Les types du seed `rarity_levels` sont fixés. | `contract: enforced: true` de chaque modèle, `dbt_project.yml` (`+column_types`) | contrat de chaque modèle (`contract.enforced`) | DBT-01 à DBT-04 |
| R-QUA-04 | Les données publiques de test n'ont que des prix fictifs : réponses d'API enregistrées (`4000 + n + 0.37`) et échantillon `dbt/sample/snapshots/` (`0` ou `4000 + n + 0.37`). | `tests/fixtures/`, `dbt/sample/snapshots/` | `tests/test_fixtures_prices.py::test_fixture_prices_are_fictitious`, `tests/test_fixtures_prices.py::test_sample_prices_are_fictitious`, `tests/test_fixtures_prices.py::test_sample_with_real_price_is_detected` | DBT-02, audit du 18 novembre 2026 |
| R-QUA-05 | `inv ci` construit et teste dbt sur l'échantillon, dans une base séparée (`data/cartograph.sample.duckdb`), jamais sur la vraie base ; la CI GitHub le lance sur chaque pull request. | `tasks.ci`, `tasks.dbt` (`--sample`), workflow `CI` | `tests/test_tasks_dbt.py::test_ci_runs_dbt_on_sample`, `tests/test_tasks_dbt.py::test_dbt_sample_uses_sample_snapshots_and_database` | DBT-01, CI-01 |

## À venir

Règles décidées pour des lots non livrés (roadmap). Chacune reçoit son identifiant et remonte dans sa famille à la livraison de son lot.

| Lot | Famille | Règle |
| --- | ------- | ----- |
| DBT-05 | PRX | La marge d'une carte de la collection se calcule sur le `trend_price` Cardmarket de la finition possédée : normale et holo → `base`, reverse → `reverse_holo`. |
| DBT-06 | PRX | Les prix de référence et les tendances comptent des produits distincts. |
| DBT-06 | PRX | Un produit ambigu est exclu ou marqué, après filtre sur les produits qui ont une carte courante (`has_current_card`). |
| DBT-06 | RAR | L'échelle de `rarity_levels` est revue sur les prix (niveaux 4 et 5, 6 et 7 inversés ; produits à deux niveaux selon la langue), ainsi que la clé du repli par rareté (code ou niveau). |
| R-QUA-01 | QUA | Un prix négatif arrête le build. |
| R-QUA-01 | QUA | La complétude et la couverture (au moins 98 %, trous acceptés) se comptent en produits distincts. |
| R-QUA-01 | QUA | Des données trop anciennes sont signalées (fraîcheur). |
| R-QUA-02 | QUA | `dbt build` et ses tests tournent après chaque collecte ; leur échec fait échouer l'exécution. |

## Règles retirées

| ID | Règle | Retirée le | Remplacée par |
| -- | ----- | ---------- | ------------- |
| — | Collecte complète du catalogue chaque lundi (paramètre `catalogue: auto`), les autres jours seulement les nouvelles cartes et les prix. | COL-05 (novembre 2026) | R-COL-02, R-COL-06 : catalogue de la veille mis à jour chaque jour, collecte complète à la main seulement |

## Règles sans test

Relevées depuis la colonne `Garantie par`.

- **Collecte** : R-COL-01 (déclenchement par cron-job.org, surveillé par healthchecks.io), R-COL-26 (rétention de la Release `catalogue`), toutes deux dans le workflow de `cartograph-data`.
- **dbt**, à reprendre par le lot QUA-01 : R-PRX-06 (JSON TCGplayer invalide, date hors ISO 8601), R-PRX-07 (TCGplayer pour le lien seulement), R-PRX-08 (aucun filtre sur `variants`), R-PRX-12 (agrégats en produits distincts), R-HIS-02 (`--full-refresh` après un fichier de prix remplacé).
- R-QUA-01 décrit le comportement de dbt lui-même : rien à tester.
