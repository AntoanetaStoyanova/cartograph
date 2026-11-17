{% macro is_new_cards(filename) -%}
    regexp_matches({{ filename }}, '(^|/)new-cards-[^/]*$')
{%- endmacro %}
