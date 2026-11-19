{% macro not_pocket_set(set_id) -%}
    not exists (
        select 1
        from {{ ref('stg_tcgdex__sets') }} as pocket_sets
        where pocket_sets.serie_id = 'tcgp' and pocket_sets.set_id = {{ set_id }}
    )
{%- endmacro %}
