-- Sur la vraie base seulement : le catalogue de l'échantillon est partiel, ses prix fictifs.
{{ config(tags = ['donnees_reelles']) }}

select
    price_date,
    priced_products,
    catalog_products,
    completeness
from {{ ref('fct_price_completeness') }}
where
    price_date = (select max(price_date) from {{ ref('fct_price_completeness') }})
    and (completeness is null or completeness < {{ var('min_completeness') }})
