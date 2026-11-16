with

source as (

    select
        *,
        {{ snapshot_date('filename') }} as snapshot_date
    from {{ source('tcgdex', 'cards') }}

),

renamed as (

    select
        card_id,
        language,
        local_id,
        name,
        set_id,
        case lower(category)
            when 'pokemon' then 'pokemon'
            when 'pokémon' then 'pokemon'
            when 'trainer' then 'trainer'
            when 'dresseur' then 'trainer'
            when 'energy' then 'energy'
            when 'énergie' then 'energy'
            else lower(category)
        end as category,
        rarity,
        from_json(raw_json -> 'types', '["VARCHAR"]') as types,
        (raw_json ->> 'hp')::integer as hp,
        raw_json ->> 'stage' as stage,
        from_json(raw_json -> 'dexId', '["INTEGER"]') as dex_ids,
        illustrator,
        raw_json ->> 'regulationMark' as regulation_mark,
        (raw_json -> 'legal' ->> 'standard')::boolean as is_legal_standard,
        (raw_json -> 'legal' ->> 'expanded')::boolean as is_legal_expanded,
        image as image_url,
        id_product as cardmarket_product_id,
        updated as updated_at,
        snapshot_date as last_seen_on,
        snapshot_date = max(snapshot_date) over () as is_current
    from source
    qualify row_number() over (
        partition by card_id, language order by snapshot_date desc
    ) = 1

)

select * from renamed
