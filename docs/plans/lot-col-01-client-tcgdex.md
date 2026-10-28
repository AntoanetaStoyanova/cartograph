# Plan — COL-01 Client TCGdex

*Rédigé le : 27 octobre 2026*
*Référence : [lot-col-01-client-tcgdex.md](../specs/lot-col-01-client-tcgdex.md)*

## Objectif

Récupérer le catalogue de chaque langue et les prix une fois par produit Cardmarket, avec pauses et nouvelles tentatives, testé sur des réponses enregistrées.

## Prérequis

- [FND-01 Socle Python](lot-fnd-01-socle.md) terminé (`LANGUAGES`, `setup_logging`, beartype).
- [COL-T8](roadmap-lots.md) tranché : aucun prix dans les logs.

## Étape 1 — Client HTTP

- [x] `uv add httpx`.
- [x] `src/cartograph/config/__init__.py` : `TCGDEX_BASE_URL = "https://api.tcgdex.net/v2"`, `REQUEST_PAUSE_S = 0.1`, `REQUEST_TIMEOUT_S = 30.0`, `MAX_RETRIES = 4`, `RETRY_BACKOFF_S = 1.0` ; section `Attributes` de la docstring complétée.
- [x] `src/cartograph/bin/collect/__init__.py` : docstring NumPy du paquet.
- [x] `src/cartograph/bin/collect/client.py` :
  - exceptions `TcgdexError` et `CardNotFoundError(TcgdexError)` ;
  - `TcgdexClient(base_url=TCGDEX_BASE_URL, pause=REQUEST_PAUSE_S, max_retries=MAX_RETRIES, backoff=RETRY_BACKOFF_S, transport: httpx.BaseTransport | None = None, sleep: Callable[[float], None] = time.sleep)`, gestionnaire de contexte (`__enter__` / `__exit__` ferment le `httpx.Client`) ;
  - `get_json(path: str) -> Any` : pause avant chaque requête sauf la première, `User-Agent` du projet, nouvelles tentatives sur 429 / 500 / 502 / 503 / 504 / `httpx.TransportError`, `Retry-After` numérique respecté, 404 → `CardNotFoundError`, autre 4xx ou tentatives épuisées → `TcgdexError`.
- [x] Tests `tests/test_collect_client.py` (`httpx.MockTransport`, `sleep` enregistreur) :
  - `test_get_json_returns_payload()`
  - `test_get_json_sends_user_agent()`
  - `test_get_json_pauses_between_requests()`
  - `test_get_json_retries_then_succeeds()` (503 puis 200)
  - `test_get_json_retries_on_transport_error()`
  - `test_get_json_respects_retry_after()` (429 avec `Retry-After: 7`)
  - `test_get_json_raises_after_max_retries()`
  - `test_get_json_404_raises_card_not_found_without_retry()`
  - `test_get_json_other_4xx_raises_without_retry()`

## Étape 2 — Catalogue

- [x] Enregistrer les réponses dans `tests/fixtures/tcgdex/` (`curl` sur l'API, listes réduites à 3 cartes) :
  - `fr_cards.json`, `en_cards.json`, `ja_cards.json` (listes) ;
  - `fr_swsh3-136.json`, `en_swsh3-136.json` (même `idProduct`) ;
  - une fiche japonaise avec prix Cardmarket ;
  - une fiche avec `pricing` absent ou sans `cardmarket` (trouvée à l'enregistrement, sinon dérivée d'une fiche réelle et signalée comme telle dans le nom du fichier) : `ja_PMCG6-055.json` (`cardmarket: null`, réelle) ;
  - montants Cardmarket remplacés par des valeurs fictives `40xx.37` (dépôt public, T8) ; `idProduct`, `unit`, `updated` réels.
- [x] `tests/conftest.py` : helper qui charge une fixture et fabrique un `TcgdexClient` sur `MockTransport` routant `/{lang}/cards` et `/{lang}/cards/{id}` vers les fixtures (404 sinon), `sleep` sans attente.
- [x] `src/cartograph/bin/collect/catalogue.py` :
  - dataclass figée `FetchResult(items: list[dict[str, Any]], failed: list[str])` (ou dans `bin/collect/__init__.py` si partagée avec `prices`) ;
  - `list_card_ids(client: TcgdexClient, language: str) -> list[str]` ;
  - `fetch_catalogue(client: TcgdexClient, language: str, card_ids: Sequence[str] | None = None) -> FetchResult` : `ValueError` si `language` hors `LANGUAGES` ; identifiants encodés dans l'URL (cas `exu-%3F`).
- [x] Tests `tests/test_collect_catalogue.py` :
  - `test_list_card_ids_returns_ids()`
  - `test_fetch_catalogue_returns_full_cards()`
  - `test_fetch_catalogue_rejects_unknown_language()`
  - `test_fetch_catalogue_uses_given_card_ids()`

## Étape 3 — Prix par produit Cardmarket

- [x] `src/cartograph/bin/collect/prices.py` :
  - dataclass figée `PriceTarget(language: str, card_id: str, id_product: int)` ;
  - `price_targets(catalogues: Mapping[str, Sequence[dict[str, Any]]]) -> list[PriceTarget]` : parcours dans l'ordre de `LANGUAGES`, première carte par `idProduct`, cartes sans `idProduct` ignorées ;
  - `fetch_prices(client: TcgdexClient, targets: Sequence[PriceTarget], now: Callable[[], datetime] = ...) -> FetchResult` : un enregistrement `{"language", "card_id", "id_product", "fetched_at", "pricing"}` par cible.
- [x] Tests `tests/test_collect_prices.py` :
  - `test_price_targets_deduplicates_european_products()` (fr et en `swsh3-136` → une cible `fr`)
  - `test_price_targets_keeps_japanese_products()`
  - `test_price_targets_skips_cards_without_id_product()`
  - `test_fetch_prices_returns_one_record_per_target()`
  - `test_fetch_prices_sets_fetched_at_in_utc()`

## Étape 4 — Cas limites et logs

- [x] `fetch_catalogue` et `fetch_prices` : carte en `CardNotFoundError` ou `TcgdexError` → ajoutée à `failed`, avertissement journalisé, collecte poursuivie ; échec de `list_card_ids` propagé.
- [x] `config` : `MAX_CONSECUTIVE_FAILURES = 20` ; après autant de cartes en `TcgdexError` d'affilée (hors `CardNotFoundError`), `fetch_catalogue` et `fetch_prices` lèvent `TcgdexError` ; un succès remet le compteur à zéro.
- [x] Logs via `logging.getLogger(__name__)` : début, progression toutes les 1 000 cartes, totaux (récupérées, en échec, ignorées sans `idProduct`) ; aucune valeur de `pricing`.
- [x] Tests `tests/test_collect_failures.py` (+ `test_fetch_catalogue_logs_progress()`) :
  - `test_fetch_catalogue_records_failed_card_and_continues()`
  - `test_fetch_prices_records_failed_card_and_continues()`
  - `test_fetch_catalogue_with_empty_list_returns_nothing()`
  - `test_fetch_prices_logs_no_price()` (`caplog` : aucune valeur de prix des fixtures dans le texte)
  - `test_list_card_ids_propagates_error()`
  - `test_fetch_prices_stops_after_consecutive_failures()`
  - `test_fetch_catalogue_404s_do_not_stop_collection()`
  - `test_consecutive_failure_counter_resets_on_success()`
- [x] Docstrings NumPy de tout le paquet `bin.collect` relues ; exemple d'utilisation dans la docstring de `collect/__init__.py` (sans appel réseau exécuté en doctest).

## Critères de fin

- [x] `uv run inv ci` passe, couverture ≥ 88 %.
- [x] Critères d'acceptation de la [spec](../specs/lot-col-01-client-tcgdex.md) cochés.
- [x] COL-01 coché dans [roadmap-lots.md](roadmap-lots.md).
