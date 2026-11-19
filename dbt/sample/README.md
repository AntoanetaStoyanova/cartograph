# Échantillon de snapshots

Extrait des snapshots publics du catalogue (Release `catalogue` de `cartograph-data`), lu par `inv dbt --sample` et donc par `inv ci`, sans `data/snapshots/` ni appel aux APIs, et de prix fictifs : les vrais prix sont privés et ce dépôt est public. Chaque prix des `prices-*` vaut `0` ou `n + 0.37` avec `n ≥ 4000` (`tests/test_fixtures_prices.py`).

| Contenu | Cas couvert |
| ------- | ----------- |
| `en` `tk-xy-su` (30 cartes le 9, 29 le 16) | `tk-xy-su-26` disparue le 16, revenue dans `new-cards` le 17 (courante) ; trois catégories |
| `fr` `hgss3` (91 cartes) | `local_id` non numérique (`THREE`) ; catégories en français |
| `ja` `SV2P` (99 cartes) | 28 raretés vides |
| Sets `en` `tk-xy-su`, `fr` `hgss3`, `ja` `SV2P`, `ja` `M6` (le 17) | source `tcgdex.sets`, date de sortie et série |
| `ja` `M6-077`, `M6-078` | fiche corrigée par TCGdex le 12 (rareté provisoire `Mega Hyper Rare` → `Illustration rare`) : le modèle doit garder la version du 16 |
| `cards-2026-11-18`, au schéma de COL-05 (`fingerprint`, `removed_on`) | lecture par nom avec les fichiers plus anciens ; `fr` `hgss3-1` marquée `removed_on` le 18 (non courante, vue pour la dernière fois le 16, comptée dans `removed`) ; `tk-xy-su-26` de retour (comptée dans `added`) |
| `prices-2026-11-17` (20 produits) et `prices-2026-11-18` (191), au schéma `snapshot.PRICE_SCHEMA` | source `tcgdex.prices` ; produits du catalogue du 16 (`rn` : rang par `id_product`), les 20 premiers présents les deux jours avec des valeurs différentes |
| Produit `rn = 1` | `cm_trend` et `cm_trend_holo` à `0` ; `tcgplayer_json` à trois finitions : `normal` (avec `directLowPrice` entier à `0`), `reverse-holofoil`, `holofoil` entièrement nulle |
| Produit `rn = 2` | toutes les `cm_*_holo` nulles sauf `cm_trend_holo` à `0` : pas de prix reverse |
| Produits `rn` multiples de 3 | aucune mesure `_holo` |
| Produits `rn` pairs | `tcgplayer_json` absent |

## Recette du catalogue

À rejouer depuis la racine du dépôt, après `uv run inv rebuild`, si le schéma des snapshots change :

```sql
copy (
    select * from 'data/snapshots/cards-2026-11-09.parquet'
    where (language, set_id) in (('en', 'tk-xy-su'), ('fr', 'hgss3'), ('ja', 'SV2P'))
       or card_id in ('M6-077', 'M6-078') and language = 'ja'
) to 'dbt/sample/snapshots/cards-2026-11-09.parquet' (format parquet, compression zstd);
copy (
    select * from 'data/snapshots/cards-2026-11-16.parquet'
    where (language, set_id) in (('en', 'tk-xy-su'), ('fr', 'hgss3'), ('ja', 'SV2P'))
       or card_id in ('M6-077', 'M6-078') and language = 'ja'
) to 'dbt/sample/snapshots/cards-2026-11-16.parquet' (format parquet, compression zstd);
copy (
    select * from 'data/snapshots/new-cards-2026-11-17.parquet'
    where (language, set_id) in (('en', 'tk-xy-su'), ('fr', 'hgss3'), ('ja', 'SV2P'))
       or card_id in ('M6-077', 'M6-078') and language = 'ja'
) to 'dbt/sample/snapshots/new-cards-2026-11-17.parquet' (format parquet, compression zstd);
copy (
    select * from 'data/snapshots/sets-2026-11-17.parquet'
    where (language, set_id) in (('en', 'tk-xy-su'), ('fr', 'hgss3'), ('ja', 'SV2P'), ('ja', 'M6'))
) to 'dbt/sample/snapshots/sets-2026-11-17.parquet' (format parquet, compression zstd);
```

Par exemple, la requête enregistrée dans `extract.sql` : `uv run python -c "import duckdb, sys; duckdb.sql(open(sys.argv[1]).read())" extract.sql`.

`cards-2026-11-18.parquet` n'est pas extrait des données : il réunit l'extrait du 16 et le `new-cards` du 17 (le second l'emporte), calcule `fingerprint` avec `card_fingerprint` sur `raw_json` et pose `removed_on = 2026-11-18` sur `fr` `hgss3-1`, à la main. Le réécrire au schéma `snapshot.CARD_SCHEMA` si ce schéma change.

## Recette des prix

Prix fictifs générés sans lire `data/` : relancer après tout changement de `snapshot.PRICE_SCHEMA` ou du catalogue du 16, depuis la racine du dépôt. Requête dans `prices.sql` :

```sql
create or replace macro fake(n) as round(n + 0.37, 2)::double;
create or replace temp table products as
select
    min(language) as language,
    min(card_id) as card_id,
    id_product,
    row_number() over (order by id_product) as rn
from 'dbt/sample/snapshots/cards-2026-11-16.parquet'
where id_product is not null
group by id_product;
create or replace temp table prices as
select
    p.language,
    p.card_id,
    p.id_product,
    d.day::timestamptz + interval 1 hour + p.rn * interval 1 second as fetched_at,
    d.day::timestamptz - interval 2 hour as cm_updated,
    'EUR' as cm_unit,
    4000 + p.rn * 100 + d.shift as n,
    p.rn,
    d.day
from products as p
cross join (
    select '2026-11-17'::date as day, 0 as shift
    union all select '2026-11-18'::date, 50
) as d
where d.day = '2026-11-18' or p.rn <= 20;
create or replace temp table rows as
select
    language,
    card_id,
    id_product,
    fetched_at,
    cm_updated,
    cm_unit,
    fake(n) as cm_avg,
    fake(n + 1) as cm_low,
    if(rn = 1, 0, fake(n + 2)) as cm_trend,
    fake(n + 3) as cm_avg1,
    fake(n + 4) as cm_avg7,
    fake(n + 5) as cm_avg30,
    if(rn % 3 = 0 or rn = 2, null, fake(n + 6)) as cm_avg_holo,
    if(rn % 3 = 0 or rn = 2, null, fake(n + 7)) as cm_low_holo,
    case when rn in (1, 2) then 0 when rn % 3 = 0 then null else fake(n + 8) end
        as cm_trend_holo,
    if(rn % 3 = 0 or rn = 2, null, fake(n + 9)) as cm_avg1_holo,
    if(rn % 3 = 0 or rn = 2, null, fake(n + 10)) as cm_avg7_holo,
    if(rn % 3 = 0 or rn = 2, null, fake(n + 11)) as cm_avg30_holo,
    case
        when rn = 1 then json_object(
            'holofoil', json_object(
                'directLowPrice', null, 'highPrice', null, 'lowPrice', null,
                'marketPrice', null, 'midPrice', null, 'productId', 100000 + rn
            ),
            'normal', json_object(
                'directLowPrice', 0, 'highPrice', fake(n + 12),
                'lowPrice', fake(n + 13), 'marketPrice', fake(n + 14),
                'midPrice', fake(n + 15), 'productId', 100000 + rn
            ),
            'reverse-holofoil', json_object(
                'directLowPrice', null, 'highPrice', fake(n + 16),
                'lowPrice', fake(n + 17), 'marketPrice', fake(n + 18),
                'midPrice', fake(n + 19), 'productId', 100000 + rn
            ),
            'unit', 'USD',
            'updated', strftime(day - 1, '%Y-%m-%d') || 'T22:16:26.345Z'
        )::varchar
        when rn % 2 = 1 then json_object(
            'normal', json_object(
                'directLowPrice', fake(n + 12), 'highPrice', fake(n + 13),
                'lowPrice', fake(n + 14), 'marketPrice', fake(n + 15),
                'midPrice', fake(n + 16), 'productId', 100000 + rn
            ),
            'unit', 'USD',
            'updated', strftime(day - 1, '%Y-%m-%d') || 'T22:16:26.345Z'
        )::varchar
    end as tcgplayer_json,
    day
from prices;
```

Écriture au schéma exact (DuckDB écrirait des colonnes non nullables), dans `write.py`, lancé par `uv run python write.py prices.sql` ; le résultat est identique d'une exécution à l'autre :

```python
import sys

import duckdb
import pyarrow.parquet as pq

from cartograph.bin.collect.snapshot import PRICE_SCHEMA

con = duckdb.connect()
con.sql("set timezone = 'UTC'")
for query in open(sys.argv[1], encoding="utf-8").read().split(";"):
    if query.strip():
        con.sql(query)
for day in ("2026-11-17", "2026-11-18"):
    table = con.sql(
        f"select * exclude (day) from rows where day = '{day}' order by card_id, language"
    ).to_arrow_table()
    pq.write_table(
        table.cast(PRICE_SCHEMA),
        f"dbt/sample/snapshots/prices-{day}.parquet",
        compression="zstd",
    )
```
