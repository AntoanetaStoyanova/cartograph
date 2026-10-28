# Plan — COL-02 Snapshots Parquet

*Rédigé le : 28 octobre 2026*
*Référence : [lot-col-02-snapshots.md](../specs/lot-col-02-snapshots.md)*

## Objectif

`inv collect` écrit les snapshots Parquet du jour (prix, catalogue sur demande), le brut gzip et un résumé sans prix, de façon idempotente.

## Prérequis

- [COL-01 Client TCGdex](lot-col-01-client-tcgdex.md) terminé.
- Fixtures sans vrais prix (corrigées le 28 octobre 2026, commit de correction à faire).

## Étape 1 — Fondations d'écriture

- [ ] `uv add pyarrow`.
- [ ] `.gitignore` : `data/`.
- [ ] `config` : `DATA_DIR = <racine>/data`, `SNAPSHOT_COMPRESSION = "zstd"` ; section `Attributes` complétée.
- [ ] `bin/collect/snapshot.py` :
  - `snapshot_paths(data_dir: Path, day: date) -> SnapshotPaths` (dataclass figée : `cards`, `prices`, `raw_cards`, `raw_prices`, `summary`) ;
  - `write_parquet(table: pa.Table, path: Path, sort_by: Sequence[str]) -> int` : tri, zstd, fichier temporaire puis `os.replace`, renvoie la taille en octets ;
  - `write_json_gz(obj: Any, path: Path) -> int` : même écriture atomique.
- [ ] Tests `tests/test_collect_snapshot.py` :
  - `test_snapshot_paths_are_dated()`
  - `test_write_parquet_sorts_and_compresses()` (métadonnées : codec zstd, ordre des lignes)
  - `test_write_parquet_replaces_existing_file()`
  - `test_write_parquet_leaves_no_temporary_file()`
  - `test_write_json_gz_round_trip()`

## Étape 2 — Table des prix

- [ ] `snapshot.py` : `PRICE_SCHEMA` (`pa.schema`, voir la spec) et `price_table(records: Sequence[dict[str, Any]]) -> pa.Table` :
  - champs `cardmarket` mappés (`avg-holo` → `cm_avg_holo`…), absents → nul ;
  - `cm_updated` et `fetched_at` convertis en timestamp UTC ;
  - `tcgplayer` sérialisé en JSON s'il n'est pas nul ;
  - noms des champs Cardmarket inconnus journalisés une fois (jamais les valeurs).
- [ ] Tests `tests/test_collect_snapshot.py` :
  - `test_price_table_matches_schema()`
  - `test_price_table_maps_holo_fields()`
  - `test_price_table_missing_fields_are_null()` (`pricing` nul, `cardmarket` nul, champ absent)
  - `test_price_table_logs_unknown_field_names_only()`
  - `test_price_table_empty_records()`

## Étape 3 — Table du catalogue sans prix

- [ ] `snapshot.py` :
  - `strip_prices(card: dict[str, Any]) -> dict[str, Any]` : copie sans aucune clé `pricing`, à toute profondeur ;
  - `CARD_SCHEMA` et `card_table(cards: Sequence[dict[str, Any]], language: str, fetched_at: datetime) -> pa.Table` : colonnes clés, `id_product` lu avant le retrait des prix, `raw_json` = fiche sans prix.
- [ ] Tests :
  - `test_strip_prices_removes_nested_pricing()` (`variants_detailed[].pricing`)
  - `test_strip_prices_does_not_modify_input()`
  - `test_card_table_matches_schema()`
  - `test_card_table_contains_no_price()` (aucune valeur de prix des fixtures dans la table sérialisée)
  - `test_card_table_keeps_id_product()`

## Étape 4 — Enchaînement de la collecte

- [ ] `prices.py` : déduplication commune extraite (`_dedupe(rows: Iterable[tuple[str, str, int | None]])`) ; `price_targets` inchangé pour l'appelant ; `price_targets_from_table(table: pa.Table) -> list[PriceTarget]`.
- [ ] `bin/collect/run.py` :
  - dataclass `StepReport` (statut, nombres, identifiants en échec, fichiers écrits) ;
  - `latest_catalogue(snapshots_dir: Path) -> Path | None` ;
  - `collect(client, data_dir, day, catalogue: bool, prices: bool, languages: Sequence[str]) -> dict[str, Any]` : catalogue tout ou rien, prix avec le catalogue du jour ou le plus récent, brut gzip, résumé écrit, renvoie le résumé.
- [ ] Tests `tests/test_collect_run.py` (client sur fixtures, `tmp_path`) :
  - `test_price_targets_from_table_matches_price_targets()`
  - `test_collect_with_catalogue_writes_all_files()`
  - `test_collect_prices_uses_latest_catalogue()`
  - `test_collect_prices_without_catalogue_fails()`
  - `test_collect_failed_language_writes_no_catalogue_but_prices()`
  - `test_collect_same_day_replaces_files()`
  - `test_collect_summary_contains_no_price()`

## Étape 5 — Ligne de commande et `inv collect`

- [ ] `run.py` : `main(argv: Sequence[str] | None = None) -> int` (`argparse` : `--catalogue`, `--no-prices`, `--languages`, `--data-dir`), `setup_logging`, date UTC du jour, `TcgdexClient` en `with`, code de sortie 0 / 1 ; `if __name__ == "__main__": sys.exit(main())`.
- [ ] `tasks/__init__.py` : tâche `collect(c, catalogue=False, prices=True, languages="", data_dir="")` qui lance `uv run python -m cartograph.bin.collect.run …` sans importer `cartograph`.
- [ ] Tests :
  - `test_main_parses_options()` (`collect` remplacé par un double)
  - `test_main_returns_one_when_a_step_fails()`
  - `test_main_rejects_unknown_language()`
- [ ] Docstrings NumPy de `snapshot` et `run` ; README : section « Collecte » (`inv collect`, `--catalogue`, dossier `data/`, brut avec prix jamais publié).

## Critères de fin

- [ ] `uv run inv ci` passe, couverture ≥ 88 %.
- [ ] Une collecte réelle `inv collect --catalogue --languages fr` lancée une fois en local (durée et tailles notées pour COL-T3).
- [ ] Critères d'acceptation de la [spec](../specs/lot-col-02-snapshots.md) cochés.
- [ ] COL-02 coché dans [roadmap-lots.md](roadmap-lots.md).
