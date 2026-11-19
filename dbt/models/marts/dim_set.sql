with

sets as (

    select
        set_id,
        language_code,
        set_name,
        serie_id,
        serie_name,
        abbreviation_official,
        abbreviation_localized,
        card_count_official,
        card_count_total,
        symbol_url,
        logo_url,
        release_date,
        last_seen_on,
        is_current
    from {{ ref('stg_tcgdex__sets') }}
    where serie_id is distinct from 'tcgp'

)

select * from sets
