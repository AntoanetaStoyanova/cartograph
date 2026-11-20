-- Sur la vraie base seulement : l'échantillon est figé, il serait périmé chaque jour.
{{ config(tags = ['donnees_reelles']) }}

select
    last_date,
    staleness_days
from {{ ref('fct_price_history_status') }}
where staleness_days is null or staleness_days > {{ var('max_staleness_days') }}
