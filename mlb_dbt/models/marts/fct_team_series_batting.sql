with team_stats as (

    select * from {{ ref('stg_mlb__team_game_stats') }}

),

series_map as (

    select * from {{ ref('int_game_series_map') }}

),

joined as (

    select
        t.team_id,
        t.team_side,
        s.series_id,
        s.series_start_date,
        s.home_team_id,
        s.away_team_id,
        count(distinct t.game_pk)           as games_in_series,

        -- counting stats
        sum(t.batting_runs)                 as series_runs,
        sum(t.batting_hits)                 as series_hits,
        sum(t.batting_doubles)              as series_doubles,
        sum(t.batting_triples)              as series_triples,
        sum(t.batting_home_runs)            as series_home_runs,
        sum(t.batting_rbi)                  as series_rbi,
        sum(t.batting_walks)                as series_walks,
        sum(t.batting_strikeouts)           as series_strikeouts,
        sum(t.batting_hit_by_pitch)         as series_hit_by_pitch,
        sum(t.batting_at_bats)              as series_at_bats,
        sum(t.batting_plate_appearances)    as series_plate_appearances,
        sum(t.batting_left_on_base)         as series_left_on_base,
        sum(t.batting_stolen_bases)         as series_stolen_bases,
        sum(t.batting_caught_stealing)      as series_caught_stealing,

        -- rate stats recomputed from counting stats
        safe_divide(
            sum(t.batting_hits),
            sum(t.batting_at_bats)
        )                                   as series_avg,

        safe_divide(
            sum(t.batting_hits)
                + sum(t.batting_walks)
                + sum(t.batting_hit_by_pitch),
            sum(t.batting_plate_appearances)
        )                                   as series_obp,

        safe_divide(
            sum(t.batting_hits)
                + sum(t.batting_doubles)
                + (2 * sum(t.batting_triples))
                + (3 * sum(t.batting_home_runs)),
            sum(t.batting_at_bats)
        )                                   as series_slg

    from team_stats t
    inner join series_map s
        on t.game_pk = s.game_pk

    group by
        t.team_id,
        t.team_side,
        s.series_id,
        s.series_start_date,
        s.home_team_id,
        s.away_team_id

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['team_id', 'series_id']) }}
                                            as team_series_id,
        *
    from joined

)

select * from final
