with

cards as (

    select
        cards.cardmarket_product_id,
        cards.language_code,
        cards.card_name,
        cards.is_current,
        rarity_mapping.rarity_code
    from {{ ref('stg_tcgdex__cards') }} as cards
    left join {{ ref('int_rarity_mapping') }} as rarity_mapping
        on coalesce(cards.rarity, 'None') = rarity_mapping.rarity
    where
        cards.cardmarket_product_id is not null
        and not exists (
            select 1
            from {{ ref('stg_tcgdex__sets') }} as pocket_sets
            where
                pocket_sets.serie_id = 'tcgp'
                and pocket_sets.set_id = cards.set_id
        )

),

ambiguity_by_language as (

    select
        cardmarket_product_id,
        language_code,
        count(distinct card_name) > 1
        or count(distinct rarity_code) > 1 as is_ambiguous
    from cards
    where is_current
    group by cardmarket_product_id, language_code

),

ambiguity as (

    select
        cardmarket_product_id,
        bool_or(is_ambiguous) as is_ambiguous_product
    from ambiguity_by_language
    group by cardmarket_product_id

),

products as (

    select
        cards.cardmarket_product_id,
        bool_or(cards.is_current) as has_current_card,
        count(*) filter (where cards.is_current) as card_count
    from cards
    group by cards.cardmarket_product_id

),

final as (

    select
        products.cardmarket_product_id,
        products.has_current_card,
        products.card_count,
        coalesce(ambiguity.is_ambiguous_product, false) as is_ambiguous_product
    from products
    left join ambiguity
        on products.cardmarket_product_id = ambiguity.cardmarket_product_id

)

select * from final
