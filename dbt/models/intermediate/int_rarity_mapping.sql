with

collected as (

    select distinct coalesce(rarity, 'None') as rarity
    from {{ ref('stg_tcgdex__cards') }}

),

mapped as (

    select
        collected.rarity,
        rarity_levels.rarity_code,
        rarity_levels.rarity_level
    from collected
    left join {{ ref('rarity_levels') }} as rarity_levels
        on collected.rarity = rarity_levels.rarity

)

select * from mapped
