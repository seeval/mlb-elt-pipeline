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
        sum(t.pitching_runs)                as series_runs_allowed,
        sum(t.pitching_earned_runs)         as series_earned_runs,
        sum(t.pitching_hits)                as series_hits_allowed,
        sum(t.pitching_home_runs)           as series_home_runs_allowed,
        sum(t.pitching_walks)               as series_walks,
        sum(t.pitching_strikeouts)          as series_strikeouts,
        sum(t.pitching_hit_by_pitch)        as series_hit_by_pitch,
        sum(t.pitching_innings_pitched)     as series_innings_pitched,
        sum(t.pitching_number_of_pitches)   as series_pitches_thrown,
        sum(t.pitching_batters_faced)       as series_batters_faced,
        sum(t.pitching_outs)                as series_outs,
        sum(t.pitching_strikes)             as series_strikes,
        sum(t.pitching_balls)               as series_balls,

        -- rate stats recomputed from counting stats
        safe_divide(
            sum(t.pitching_earned_runs) * 9,
            sum(t.pitching_innings_pitched)
        )                                   as series_era,

        safe_divide(
            sum(t.pitching_hits) + sum(t.pitching_walks),
            sum(t.pitching_innings_pitched)
        )                                   as series_whip,

        safe_divide(
            sum(t.pitching_strikeouts) * 9,
            sum(t.pitching_innings_pitched)
        )                                   as series_k_per_9,

        safe_divide(
            sum(t.pitching_walks) * 9,
            sum(t.pitching_innings_pitched)
        )                                   as series_bb_per_9

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
