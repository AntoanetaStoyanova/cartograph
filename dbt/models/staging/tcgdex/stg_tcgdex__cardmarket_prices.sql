with

source as (

    select
        *,
        {{ snapshot_date('filename') }} as price_date
    from {{ source('tcgdex', 'prices') }}

),

unpivoted as (

    select
        id_product,
        'base' as finish,
        price_date,
        cm_low as low_price,
        cm_trend as trend_price,
        cm_avg as avg_price,
        cm_avg1 as avg1_price,
        cm_avg7 as avg7_price,
        cm_avg30 as avg30_price,
        cm_unit,
        cm_updated
    from source

    union all

    select
        id_product,
        'reverse_holo' as finish,
        price_date,
        cm_low_holo as low_price,
        cm_trend_holo as trend_price,
        cm_avg_holo as avg_price,
        cm_avg1_holo as avg1_price,
        cm_avg7_holo as avg7_price,
        cm_avg30_holo as avg30_price,
        cm_unit,
        cm_updated
    from source

),

renamed as (

    select
        id_product as cardmarket_product_id,
        finish,
        price_date,
        nullif(low_price::decimal(10, 2), 0) as low_price,
        nullif(trend_price::decimal(10, 2), 0) as trend_price,
        nullif(avg_price::decimal(10, 2), 0) as avg_price,
        nullif(avg1_price::decimal(10, 2), 0) as avg1_price,
        nullif(avg7_price::decimal(10, 2), 0) as avg7_price,
        nullif(avg30_price::decimal(10, 2), 0) as avg30_price,
        cm_unit as currency_code,
        cm_updated as updated_at
    from unpivoted

)

select * from renamed
where
    coalesce(
        low_price, trend_price, avg_price, avg1_price, avg7_price, avg30_price
    ) is not null
