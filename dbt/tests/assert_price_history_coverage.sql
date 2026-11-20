-- Sur la vraie base seulement : l'échantillon est figé, sa période n'a pas de sens.
{{ config(tags = ['donnees_reelles']) }}

select
    coverage,
    expected_days,
    covered_days
from {{ ref('fct_price_history_status') }}
where coverage is null or coverage < {{ var('min_coverage') }}
