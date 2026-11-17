{% macro snapshot_date(filename) -%}
    regexp_extract({{ filename }}, '-(\d{4}-\d{2}-\d{2})\.parquet$', 1)::date
{%- endmacro %}
