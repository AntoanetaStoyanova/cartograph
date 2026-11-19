-- pl4 n'existe pas en fr chez TCGdex, mais ses 9 cartes AR ont un prix : gardées sans set.
select
    dim_card.card_id,
    dim_card.language_code,
    dim_card.set_id
from {{ ref('dim_card') }} as dim_card
where
    not exists (
        select 1
        from {{ ref('dim_set') }} as dim_set
        where
            dim_set.set_id = dim_card.set_id
            and dim_set.language_code = dim_card.language_code
    )
    and not (dim_card.set_id = 'pl4' and dim_card.language_code = 'fr')
