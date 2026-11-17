with

source as (

    select
        *,
        {{ snapshot_date('filename') }} as snapshot_date
    from {{ source('tcgdex', 'cards') }}

),

renamed as (

    select
        set_id,
        language as language_code,
        set_name,
        (raw_json -> 'set' -> 'cardCount' ->> 'official')::integer
            as card_count_official,
        (raw_json -> 'set' -> 'cardCount' ->> 'total')::integer as card_count_total,
        raw_json -> 'set' ->> 'symbol' as symbol_url,
        raw_json -> 'set' ->> 'logo' as logo_url,
        snapshot_date as last_seen_on,
        snapshot_date = max(snapshot_date) over () as is_current
    from source
    qualify row_number() over (
        partition by set_id, language order by snapshot_date desc, card_id asc
    ) = 1

)

select * from renamed
