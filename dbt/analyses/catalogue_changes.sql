with

source as (

    select
        language as language_code,
        card_id,
        removed_on,
        json_merge_patch(raw_json, '{"updated": null}') as card_json,
        {{ snapshot_date('filename') }} as snapshot_date
    from {{ source('tcgdex', 'cards') }}
    where not {{ is_new_cards('filename') }}

),

snapshots as (

    select
        snapshot_date,
        lag(snapshot_date) over (order by snapshot_date) as previous_date
    from (select distinct snapshot_date from source) as snapshot_dates

),

current_cards as (

    select
        source.*,
        snapshots.previous_date
    from source
    inner join snapshots on source.snapshot_date = snapshots.snapshot_date
    where snapshots.previous_date is not null

),

previous_cards as (

    select
        source.*,
        snapshots.snapshot_date as next_date
    from source
    inner join snapshots on source.snapshot_date = snapshots.previous_date

),

compared as (

    select
        coalesce(curr.snapshot_date, prev.next_date) as snapshot_date,
        coalesce(curr.previous_date, prev.snapshot_date) as previous_date,
        coalesce(curr.language_code, prev.language_code) as language_code,
        curr.removed_on is null
        and (prev.card_id is null or prev.removed_on is not null) as is_added,
        prev.removed_on is null
        and (curr.card_id is null or curr.removed_on is not null) as is_removed,
        prev.card_json <> curr.card_json as is_modified
    from current_cards as curr
    full outer join previous_cards as prev
        on
            curr.snapshot_date = prev.next_date
            and curr.card_id = prev.card_id
            and curr.language_code = prev.language_code

)

select
    snapshot_date,
    previous_date,
    language_code,
    count(*) filter (where is_added) as added,
    count(*) filter (where is_removed) as removed,
    count(*) filter (where is_modified) as modified
from compared
group by snapshot_date, previous_date, language_code
order by snapshot_date, language_code
