with

source as (

    select
        *,
        {{ snapshot_date('filename') }} as snapshot_date
    from {{ source('tcgdex', 'sets') }}

),

renamed as (

    select
        set_id,
        language as language_code,
        name as set_name,
        serie_id,
        serie_name,
        abbreviation_official,
        abbreviation_localized,
        card_count_official::integer as card_count_official,
        card_count_total::integer as card_count_total,
        symbol as symbol_url,
        logo as logo_url,
        release_date,
        snapshot_date as last_seen_on,
        snapshot_date = max(snapshot_date) over () as is_current
    from source
    qualify row_number() over (
        partition by set_id, language order by snapshot_date desc
    ) = 1

)

select * from renamed
