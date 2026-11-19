with

cards as (

    select
        card_id,
        language_code,
        local_id,
        card_name,
        set_id,
        category,
        rarity,
        pokemon_types,
        hp,
        evolution_stage,
        dex_ids,
        illustrator,
        regulation_mark,
        is_legal_standard,
        is_legal_expanded,
        image_url,
        cardmarket_product_id,
        updated_at,
        last_seen_on,
        removed_on,
        is_current
    from {{ ref('stg_tcgdex__cards') }} as cards
    where not exists (
        select 1
        from {{ ref('stg_tcgdex__sets') }} as pocket_sets
        where
            pocket_sets.serie_id = 'tcgp'
            and pocket_sets.set_id = cards.set_id
    )

),

joined as (

    select
        cards.card_id,
        cards.language_code,
        cards.local_id,
        cards.card_name,
        cards.set_id,
        cards.category,
        cards.rarity,
        cards.pokemon_types,
        cards.hp,
        cards.evolution_stage,
        cards.dex_ids,
        cards.illustrator,
        cards.regulation_mark,
        cards.is_legal_standard,
        cards.is_legal_expanded,
        cards.image_url,
        cards.cardmarket_product_id,
        cards.updated_at,
        cards.last_seen_on,
        cards.removed_on,
        cards.is_current,
        rarity_mapping.rarity_code,
        rarity_mapping.rarity_level,
        products.is_ambiguous_product
    from cards
    left join {{ ref('int_rarity_mapping') }} as rarity_mapping
        on coalesce(cards.rarity, 'None') = rarity_mapping.rarity
    left join {{ ref('int_cardmarket_products') }} as products
        on cards.cardmarket_product_id = products.cardmarket_product_id

)

select * from joined
