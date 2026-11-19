select rarity_code
from {{ ref('rarity_levels') }}
group by rarity_code
having count(distinct coalesce(rarity_level, -1)) > 1
