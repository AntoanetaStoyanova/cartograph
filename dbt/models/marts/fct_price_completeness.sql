with

catalog as (

    select distinct cardmarket_product_id
    from {{ ref('dim_card') }}
    where is_current and cardmarket_product_id is not null

),

priced as (

    select
        prices.price_date,
        count(distinct prices.cardmarket_product_id) as priced_products
    from {{ ref('fct_price_snapshot') }} as prices
    inner join catalog
        on prices.cardmarket_product_id = catalog.cardmarket_product_id
    where prices.trend_price is not null
    group by prices.price_date

),

snapshot_dates as (

    select distinct price_date
    from {{ ref('fct_price_snapshot') }}

),

status as (

    select
        snapshot_dates.price_date,
        (select count(*) from catalog) as catalog_products,
        coalesce(priced.priced_products, 0) as priced_products
    from snapshot_dates
    left join priced
        on snapshot_dates.price_date = priced.price_date

),

final as (

    select
        price_date,
        catalog_products,
        priced_products,
        (
            priced_products / nullif(catalog_products, 0)
        )::decimal(5, 4) as completeness
    from status

)

select * from final
