-- Vue : la fraîcheur se calcule à chaque test, pas au dernier build.
{{ config(materialized = 'view') }}

with

bounds as (

    select
        min(price_date) as first_date,
        max(price_date) as last_date
    from {{ ref('fct_price_snapshot') }}

),

calendar as (

    select
        unnest(generate_series(first_date, last_date, interval 1 day))::date
            as calendar_date
    from bounds

),

days as (

    select
        calendar.calendar_date,
        exists(
            select 1
            from {{ ref('fct_price_snapshot') }} as prices
            where prices.price_date = calendar.calendar_date
        ) as is_loaded,
        exists(
            select 1
            from {{ ref('accepted_gaps') }} as gaps
            where gaps.gap_date = calendar.calendar_date
        ) as is_accepted_gap
    from calendar

),

counts as (

    select
        count(*) filter (where not is_accepted_gap or is_loaded) as expected_days,
        count(*) filter (where is_loaded) as covered_days,
        count(*) filter (where is_accepted_gap and not is_loaded) as accepted_gap_days
    from days

),

status as (

    select
        bounds.first_date,
        bounds.last_date,
        counts.expected_days,
        counts.covered_days,
        counts.accepted_gap_days,
        (
            counts.covered_days / nullif(counts.expected_days, 0)
        )::decimal(5, 4) as coverage,
        datediff(
            'day',
            bounds.last_date,
            coalesce(nullif('{{ var("reference_date", "") }}', '')::date, current_date)
        ) as staleness_days
    from bounds
    cross join counts

)

select * from status
