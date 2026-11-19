# Journal — cartograph

> **Usage — Claude Code** : ce fichier trace l'avancement du projet session par session —
> ce qui a été fait et ce qu'il reste à faire. Contrairement à `CURRENT.md` (état du code
> au moment d'une review), ce journal suit les décisions, les documents créés et les étapes
> franchies. Ajoute une entrée en haut (sous ce bloc) à chaque session de travail
> significative. Ne supprime pas les entrées précédentes.
>
> Format d'une entrée :
>
> ## [YYYY-MM-DD] — <titre court de la session>
> ### Fait
> - ce qui a été fait
>
> ### Reste à faire
> - ce qu'il reste à faire
>
> ### Références
> - fichiers, specs, plans

---

## [2026-11-19] — Audit clos, v0.8.1, DBT-02 livré

### Fait

- Session ouverte (`/workspace-init`).
- Plan fix-audit-2026-11-18 — Étape 2 : Collecte. `FetchResult.error` : `fetch_each` renvoie le partiel au lieu de lever ; prix reçus avant une panne écrits (brut et Parquet, étape `failed`) ; rotation garde les fiches lues de la langue coupée ; catalogue complet, sets et nouvelles cartes restent tout ou rien. `Retry-After` négatif → 0, `nan` → backoff. Logger nommé dans `run.py` (testé par `runpy` en `__main__`). `new_cards` dans le checkpoint. Docstring de `inv collect`. `inv ci` et `inv okflint` verts.
- Plan fix-audit-2026-11-18 — Étape 3 : Tests et doc restants. Fixture `isolated_logs` dans `conftest.py` (`LOG_DIR` patché dans `config`, `__main__`, `rebuild`, `collect.run`, `suivi.run`, handlers fermés) : `test_suivi_run` n'écrit plus dans `logs/` du dépôt. Tests ajoutés : rotation coupée par une panne via `main`, carte disparue puis revenue en collecte complète, `--catalogue --no-prices`, ensemble exact des fiches de la rotation (`raw_path`, l'ancienne assertion `%253F` ne pouvait pas échouer), prix entiers dans les fixtures, échec du téléchargement dans `inv rebuild`, vrai `.clean` sur le dépôt, lignes Énergie et Émissions. `CONTRIBUTING.md:141` corrigé. Test `-m` : client remplacé par une sous-classe (une lambda fait échouer beartype sur les annotations). `inv ci` (389 tests, 99,4 %) et `inv okflint` verts.
- Vérifié : la collecte du 19/11 (run 44450348025, succès) a supprimé `cards-2026-11-18.parquet` de la Release `catalogue` (« Supprimé de catalogue » dans le log) ; restent les `cards-` des lundis 02, 09, 16/11 et `cards-2026-11-19`.
- fix-audit-2026-11-18 clos : critères de fin cochés, entrée de l'audit complétée dans `CURRENT.md`, plan et spec `statut: fait`.
- Retiré du « Reste à faire » : « Porte 0 franchie le 15/11 » (constat, déjà acquis).
- v0.8.1 livrée (PR #35 fusionnée, `inv release`).
- `docs/specs/dbt-02-staging-prix.md` et `docs/plans/dbt-02-staging-prix.md` créés. Décisions : un staging par marché (`stg_tcgdex__cardmarket_prices`, finitions `base` / `reverse_holo` ; `stg_tcgdex__tcgplayer_prices`, 7 finitions), grain produit Cardmarket × finition × date (`card_id` hors grain), `decimal(10, 2)` avec `nullif(…, 0)`, pas de ligne vide, aucun filtre sur `variants`, échantillon de prix fictifs (`4000 + n + 0.37`) versionné et couvert par le test de non-régression ; finitions de FX7 (normale, holo → `base`, reverse → `reverse_holo`) traduites en aval.
- Spec DBT-02 relue et corrigée : pas de filtre sur `variants` (retiré du hors périmètre, seules les valeurs douteuses vont à QUA-01) ; remplissage des colonnes `_holo` donné colonne par colonne (`cm_trend_holo` à 0 sur 12 284 lignes sur 30 278 le 18/11).
- Spec et plan DBT-02 : mesures suffixées `_price` (`low_price`, `trend_price`, `avg_price`… ; TCGplayer `mid_price`, `market_price`, `direct_low_price`…) ; correspondance des finitions de FX7 tranchée en DBT-05 (`fct_collection`, marge sur `trend_price` de la finition possédée), DBT-05 ajouté aux mises à jour de la roadmap.
- Plan dbt-02-staging-prix — Étape 1 : Source et échantillon fictif. Spec passée à `en cours`. `tests/test_fixtures_prices.py` : non-régression sur `dbt/sample/snapshots/prices-*.parquet` (`cm_*` et nombres de `tcgplayer_json` hors `productId` : `0` ou `n + 0.37`), cas négatifs Cardmarket, TCGplayer décimal et entier, présence de prix. `prices-2026-11-17.parquet` (20 produits) et `prices-2026-11-18.parquet` (191) générés depuis les `id_product` du catalogue du 16, recette DuckDB + pyarrow (cast à `PRICE_SCHEMA`, DuckDB écrit des colonnes non nullables) déterministe, dans `dbt/sample/README.md` avec le tableau des cas. Décision : la valeur TCGplayer entière de l'échantillon est `0` (un entier ≥ 4000 sortirait de l'ensemble fictif) ; l'entier non nul sera couvert par les tests unitaires de l'étape 3. Source `tcgdex.prices` dans `sources.yml`, description de la source mise à jour. `inv dbt --sample` vert.
- Plan dbt-02-staging-prix — Étape 2 : `stg_tcgdex__cardmarket_prices`. `.sql` (`source` → `unpivoted` en `union all` `base` / `reverse_holo` → `renamed`, lignes sans aucune mesure filtrées) et `.yml` (contrat, `data_type`, `unique` sur le grain, `not_null`, `accepted_values` sur `finish` et `currency_code`, test unitaire `stg_tcgdex__cardmarket_prices_unpivots_finishes`). Décision : `nullif` appliqué après le `decimal(10, 2)`, pour qu'un prix arrondi à 0,00 devienne vide. Échantillon : 20 + 191 lignes `base`, 13 + 127 `reverse_holo`. `inv ci` (395 tests, dbt 26/26) et `inv okflint` verts.
- Plan dbt-02-staging-prix — Étape 3 : `stg_tcgdex__tcgplayer_prices`. `.sql` (`source` en `json`, `keyed` par `unnest(json_keys(…))`, `unpivoted` hors `unit` et `updated`, `renamed` : mesures `->>` en `decimal(10, 2)` puis `nullif`, `updated_at` en `timestamptz`, `tcgplayer_product_id` en `bigint` ; lignes sans aucune mesure filtrées) et `.yml` (contrat, `accepted_values` sur les 7 finitions et `USD`, `not_null` sur le grain et `tcgplayer_product_id`, test unitaire `stg_tcgdex__tcgplayer_prices_unpivots_finishes` : entier `4000` lu en décimal, `0` vide, finition nulle et JSON vide sans ligne). Échantillon : 10 + 96 `normal`, 1 + 1 `reverse-holofoil`. `inv ci` (395 tests, dbt 35/35) et `inv okflint` verts.
- Plan dbt-02-staging-prix — Étape 4 : Vraies données et documentation. `inv rebuild` lancé par Antoaneta (23 fichiers `prices-`) ; tests des deux modèles 15/15 sur la vraie base ; contrôles par nombres notés dans la spec (section « Vérification sur les vrais prix ») : aucune mesure à 0, aucune ligne vide, 7 finitions TCGplayer présentes, 8 689 lignes `base` sans `trend_price` (pour DBT-06 et QUA-01). Mis à jour : roadmap (DBT-02 coché, DBT-04 limité à Cardmarket via `dim_card`, DBT-05 marge sur `trend_price`), spec maîtresse (lignes staging des prix et `fct_price_snapshot`), `cadrage-flux.md` (prix de référence confirmé, finitions de FX7), `CONTRIBUTING.md` (source, modèles, échantillon de prix fictifs, invariant), `README.md` (deux modèles de prix). Critères de la spec cochés sauf « CI sur GitHub », à vérifier sur la PR. `inv ci` et `inv okflint` verts.
- PR #37 (`feature/dbt-02` → `develop`) fusionnée, CI GitHub verte (run 44508257537) : dernier critère coché, plan et spec dbt-02-staging-prix `statut: fait`.

### Reste à faire

- Revue de DBT-02 (`/cr`), puis `inv finish` pour pousser les derniers ajouts de `feature/dbt-02` vers `develop`.
- Prochain lot de la chaîne Pipeline de données : DBT-03 (intermediate rareté), à planifier (`/workspace-plan`).
- Avant la porte 1 : relire dans un navigateur les conditions de Cardmarket et de TCGplayer (veille).
- Rapport de novembre à régénérer en fin de mois (`inv suivi --mois 2026-11 --force`, commentaire gardé), puis `statut: fait` ; mettre à jour les chiffres de `docs/gouvernance/green-it.md`. Chaque début de mois : `inv ci` puis `inv suivi`, commentaire.
- Antoaneta : avant PRO-02, demander aux testeurs leur logiciel de caisse et un fichier d'import exemple.
- `cadrage-flux.md` : flux d'export pro (FX7 et FX8, écrans) à ajouter quand PRO-01 et PRO-02 seront planifiés.

### Références

- ../docs/specs/dbt-02-staging-prix.md, ../docs/plans/dbt-02-staging-prix.md
- dbt/sample/snapshots/prices-2026-11-17.parquet, prices-2026-11-18.parquet, dbt/sample/README.md, dbt/models/staging/tcgdex/sources.yml, tests/test_fixtures_prices.py
- dbt/models/staging/tcgdex/stg_tcgdex__cardmarket_prices.sql, stg_tcgdex__cardmarket_prices.yml, stg_tcgdex__tcgplayer_prices.sql, stg_tcgdex__tcgplayer_prices.yml
- docs/plans/roadmap-lots.md, docs/specs/cadrage-flux.md, spec maîtresse, CONTRIBUTING.md, README.md
- docs/plans/fix-audit-2026-11-18.md, docs/specs/fix-audit-2026-11-18.md
- src/cartograph/bin/collect/ (`__init__`, `batch`, `client`, `run`, `prices`, `catalogue`, `sets`), tasks/__init__.py
- tests/test_collect_run.py, tests/test_collect_client.py, tests/test_collect_failures.py
- tests/conftest.py, test_main.py, test_rebuild.py, test_suivi_run.py, test_fixtures_prices.py, test_tasks_rebuild.py, test_tasks_clean.py, test_suivi_report.py, CONTRIBUTING.md
