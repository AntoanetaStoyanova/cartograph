-- En avertissement : erreurs de correspondance connues de TCGdex, signalées sans bloquer.
{{ config(severity = 'warn') }}

select
    cardmarket_product_id,
    card_count
from {{ ref('int_cardmarket_products') }}
where is_ambiguous_product
