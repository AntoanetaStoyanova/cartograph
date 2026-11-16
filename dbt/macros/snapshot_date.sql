{% macro snapshot_date(filename) -%}
    regexp_extract({{ filename }}, 'cards-(\d{4}-\d{2}-\d{2})', 1)::date
{%- endmacro %}
