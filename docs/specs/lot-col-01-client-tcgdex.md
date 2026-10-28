# Spec — COL-01 Client TCGdex

*Rédigé le : 27 octobre 2026*

## Contexte

Premier lot de la collecte dans la [feuille de route](../plans/roadmap-lots.md) (F1, N3, N10 de la [spec maîtresse](Spécification%20du%20projet%20final%20M2%20plateforme%20de%20données%20Pokémon%20TCG%20(1).md)). Il dépend de [FND-01](lot-fnd-01-socle.md) : `LANGUAGES = ("fr", "en", "ja")`, `setup_logging` et beartype sont en place.

Constaté sur l'API TCGdex le 27 octobre 2026 :

- `GET /v2/{lang}/cards` renvoie toute la liste en un appel, avec seulement `id`, `localId`, `name` (22 155 cartes FR, 23 770 EN, 13 006 JA).
- `GET /v2/{lang}/cards/{id}` renvoie la fiche complète, dont `pricing.cardmarket` (`idProduct`, `unit`, `updated`, `avg`, `low`, `trend`, `avg1`, `avg7`, `avg30` et leurs versions `-holo`) et `pricing.tcgplayer` (souvent `null`, y compris en anglais sur les cartes testées).
- Le GraphQL n'expose pas `pricing` : les prix demandent un appel par carte.
- Carte inconnue : 404. Aucune limite de débit publiée ; en-têtes `cache-control: no-cache` et `etag`.
- Les identifiants de carte sont communs aux langues (`swsh3-136` en `fr` et en `en`) ; les cartes européennes d'un même produit partagent l'`idProduct` Cardmarket, les japonaises ont le leur.

## Objectif

Un client Python qui récupère le catalogue d'une langue et les prix une fois par produit Cardmarket, avec pauses et nouvelles tentatives, testé sans réseau sur des réponses enregistrées. Il renvoie du JSON brut en mémoire ; l'écriture des fichiers vient avec COL-02.

## Périmètre

- Dépendance `httpx`.
- Paramètres de l'API dans `cartograph.config`.
- Paquet `cartograph.bin.collect` :
  - `client` : appels HTTP, pause entre requêtes, nouvelles tentatives, erreurs typées ;
  - `catalogue` : liste des identifiants et fiches complètes d'une langue ;
  - `prices` : choix des cartes à interroger (une par `idProduct`) et récupération des prix.
- Réponses enregistrées dans `tests/fixtures/tcgdex/` et tests sans réseau.

## Hors périmètre

- Écriture Parquet ou JSON, tâche `inv collect`, idempotence sur disque (COL-02).
- Mesures de durée et de volume (COL-T3) ; exploration de `tcgdex/price-history` (COL-T4).
- Images (EMB-01), workflow planifié (ORC-01), stockage dans `cartograph-prices` (STO-01).
- Sets (`/v2/{lang}/sets`) : la fiche carte contient déjà `set` (id, nom) ; à ajouter si DBT-01 en a besoin.

## Décisions

| Sujet | Décision | Raison |
| --- | --- | --- |
| Bibliothèque HTTP | `httpx` (client synchrone) ; tests avec `httpx.MockTransport` | Délai d'attente par défaut, transport remplaçable en test sans dépendance de test en plus |
| Format renvoyé | JSON brut (`dict[str, Any]`), sans transformation | Le JSON brut est conservé (spec maîtresse) ; l'aplatissement en colonnes appartient à COL-02 et au staging dbt |
| Parallélisme | Appels séquentiels avec pause (`REQUEST_PAUSE_S = 0.1`) | N10 ; volume (~59 000 fiches par semaine, ~35 000 prix par jour) à mesurer en COL-T3 avant d'envisager du parallélisme |
| Nouvelles tentatives | 429, 500, 502, 503, 504 et erreurs réseau (`httpx.TransportError`) : jusqu'à `MAX_RETRIES = 4` nouvelles tentatives (5 appels au plus), attente exponentielle (`RETRY_BACKOFF_S * 2**n`), `Retry-After` respecté s'il est numérique, plafonné à `MAX_RETRY_AFTER_S = 60` ; redirections suivies ; réponse non JSON → `TcgdexError` (carte en échec, pas de plantage) | N3 ; erreurs temporaires seulement |
| Erreurs définitives | 404 → `CardNotFoundError` sans nouvelle tentative ; autre 4xx ou tentatives épuisées → `TcgdexError` | Ne pas insister sur une erreur qui ne changera pas |
| Échec d'une carte | La carte est notée dans `failed` et la collecte continue ; seule la liste d'identifiants en échec fait échouer la langue | Une carte en erreur ne doit pas perdre la journée ; les trous sont suivis par la surveillance (SUR-01) |
| API en panne | Après `MAX_CONSECUTIVE_FAILURES = 20` cartes en `TcgdexError` d'affilée (les 404 ne comptent pas), `fetch_catalogue` et `fetch_prices` s'arrêtent et lèvent `TcgdexError` | Sans arrêt, une panne complète coûterait 15 s d'attente par carte, soit des heures de workflow pour rien |
| Une requête par produit | `price_targets` parcourt les catalogues dans l'ordre de `LANGUAGES` et garde la première carte par `pricing.cardmarket.idProduct` | Prix identiques par `idProduct` (T1) ; les japonaises ont leurs propres `idProduct` et sont donc toutes gardées |
| Cartes sans `idProduct` | Ignorées pour les prix du jour, comptées dans les logs ; reprises au catalogue suivant si un `idProduct` apparaît | Pas de clé de déduplication ; TCGplayer seul n'a été vu sur aucune carte testée |
| Enregistrement de prix | `{"language", "card_id", "id_product", "fetched_at", "pricing"}`, `fetched_at` en UTC ISO 8601 | Garde la carte interrogée et l'heure de collecte, `pricing` brut |
| Horloge et attente | `sleep` et `now` injectables (défaut `time.sleep`, `datetime.now(UTC)`) | Tests rapides et déterministes |
| Identification | En-tête `User-Agent` lu dans `TCGDEX_USER_AGENT` (`.env` en local, variable GitHub Actions `vars.TCGDEX_USER_AGENT` dans les workflows) | Politesse envers une API gratuite |
| Logs | Progression (toutes les 1 000 cartes), totaux et identifiants en échec ; jamais de prix | Les journaux du dépôt public sont publics (T8) |
| Langue | `language` doit appartenir à `LANGUAGES`, sinon `ValueError` | Une langue mal saisie échoue avant tout appel |

## Critères d'acceptation

- [x] `TcgdexClient.get_json` réessaie après 429, 5xx et erreur réseau, respecte `Retry-After`, et lève `TcgdexError` une fois les tentatives épuisées.
- [x] Un 404 lève `CardNotFoundError` sans nouvelle tentative.
- [x] Une pause d'au moins `REQUEST_PAUSE_S` sépare deux requêtes.
- [x] `fetch_catalogue` renvoie les fiches d'une langue et la liste des cartes en échec ; une langue hors `LANGUAGES` lève `ValueError`.
- [x] `price_targets` garde une seule carte par `idProduct` européen, toutes les japonaises, et ignore les cartes sans `idProduct`.
- [x] `fetch_prices` renvoie un enregistrement par cible avec `fetched_at` en UTC.
- [x] La collecte s'arrête avec `TcgdexError` après `MAX_CONSECUTIVE_FAILURES` cartes en échec d'affilée.
- [x] Aucun prix n'apparaît dans les logs (test).
- [x] Les tests n'appellent pas le réseau.
- [x] `uv run inv ci` passe, couverture ≥ 88 %.
