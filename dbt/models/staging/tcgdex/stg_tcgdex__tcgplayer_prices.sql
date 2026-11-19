with

source as (

    select
        id_product,
        tcgplayer_json::json as tcgplayer,
        {{ snapshot_date('filename') }} as price_date
    from {{ source('tcgdex', 'prices') }}
    where tcgplayer_json is not null

),

keyed as (

    select
        id_product,
        tcgplayer,
        price_date,
        unnest(json_keys(tcgplayer)) as finish
    from source

),

unpivoted as (

    select
        id_product,
        finish,
        price_date,
        tcgplayer -> finish as prices,
        tcgplayer ->> 'unit' as unit,
        tcgplayer ->> 'updated' as updated
    from keyed
    where finish not in ('unit', 'updated')

),

renamed as (

    select
        id_product as cardmarket_product_id,
        finish,
        price_date,
        nullif((prices ->> 'lowPrice')::decimal(10, 2), 0) as low_price,
        nullif((prices ->> 'midPrice')::decimal(10, 2), 0) as mid_price,
        nullif((prices ->> 'highPrice')::decimal(10, 2), 0) as high_price,
        nullif((prices ->> 'marketPrice')::decimal(10, 2), 0) as market_price,
        nullif((prices ->> 'directLowPrice')::decimal(10, 2), 0) as direct_low_price,
        unit as currency_code,
        updated::timestamptz as updated_at,
        (prices ->> 'productId')::bigint as tcgplayer_product_id
    from unpivoted

)

select * from renamed
where
    coalesce(low_price, mid_price, high_price, market_price, direct_low_price)
    is not null
