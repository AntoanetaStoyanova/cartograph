select
    rarity,
    rarity_code,
    rarity_level
from {{ ref('rarity_levels') }}
where (rarity_level is null) != (rarity_code in ('none', 'promo', 'pocket'))
