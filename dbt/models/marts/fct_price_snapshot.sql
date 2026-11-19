{{
    config(
        materialized = 'incremental',
        incremental_strategy = 'append',
        on_schema_change = 'fail',
    )
}}

with

prices as (

    select
        cardmarket_product_id,
        finish,
        price_date,
        low_price,
        trend_price,
        avg_price,
        avg1_price,
        avg7_price,
        avg30_price,
        currency_code,
        updated_at
    from {{ ref('stg_tcgdex__cardmarket_prices') }}
    {% if is_incremental() %}
        where
            price_date > (
                select coalesce(max(loaded.price_date), '1900-01-01')
                from {{ this }} as loaded
            )
    {% endif %}

)

select * from prices
