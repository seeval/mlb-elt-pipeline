with batting as (

    select * from {{ ref('stg_mlb__player_batting_stats') }}

),

series_map as (

    select * from {{ ref('int_game_series_map') }}

),

teams as (

    select * from {{ ref('dim_teams') }}

),

joined as (

    select
        b.player_id,
        b.player_name,
        b.team_id,
        dt.team_name,
        dt.team_abbreviation,
        dt.league,
        dt.division,
        s.series_id,
        s.series_start_date,
        s.home_team_id,
        s.away_team_id,

        sum(b.game_at_bats)             as series_at_bats,
        sum(b.game_hits)                as series_hits,
        sum(b.game_doubles)             as series_doubles,
        sum(b.game_triples)             as series_triples,
        sum(b.game_home_runs)           as series_home_runs,
        sum(b.game_rbi)                 as series_rbi,
        sum(b.game_walks)               as series_walks,
        sum(b.game_strikeouts)          as series_strikeouts,
        sum(b.game_hit_by_pitch)        as series_hit_by_pitch,
        sum(b.game_plate_appearances)   as series_plate_appearances,
        sum(b.game_stolen_bases)        as series_stolen_bases,
        sum(b.game_caught_stealing)     as series_caught_stealing,
        sum(b.game_left_on_base)        as series_left_on_base,
        count(distinct b.game_pk)       as games_played_in_series,

        safe_divide(
            sum(b.game_hits),
            sum(b.game_at_bats)
        )                               as series_avg,

        safe_divide(
            sum(b.game_hits)
                + sum(b.game_walks)
                + sum(b.game_hit_by_pitch),
            sum(b.game_plate_appearances)
        )                               as series_obp,

        safe_divide(
            sum(b.game_hits)
                + sum(b.game_doubles)
                + (2 * sum(b.game_triples))
                + (3 * sum(b.game_home_runs)),
            sum(b.game_at_bats)
        )                               as series_slg,
        
        
        -- OPS = OBP + SLG, recomputed from counting stats
        safe_divide(
            sum(b.game_hits)
                + sum(b.game_walks)
                + sum(b.game_hit_by_pitch),
            sum(b.game_plate_appearances)
        )
        +
        safe_divide(
            sum(b.game_hits)
                + sum(b.game_doubles)
                + (2 * sum(b.game_triples))
                + (3 * sum(b.game_home_runs)),
            sum(b.game_at_bats)
        )                               as series_ops,


        max(b.season_games_played)      as season_games_played,
        max(b.season_hits)              as season_hits,
        max(b.season_home_runs)         as season_home_runs,
        max(b.season_rbi)               as season_rbi,
        max(b.season_avg)               as season_avg,
        max(b.season_obp)               as season_obp,
        max(b.season_slg)               as season_slg,
        max(b.season_ops)               as season_ops

    from batting b
    inner join series_map s
        on b.game_pk = s.game_pk
    left join teams dt
        on b.team_id = dt.team_id

    group by
        b.player_id,
        b.player_name,
        b.team_id,
        dt.team_name,
        dt.team_abbreviation,
        dt.league,
        dt.division,
        s.series_id,
        s.series_start_date,
        s.home_team_id,
        s.away_team_id

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['player_id', 'series_id']) }}
                                            as batter_series_id,
        *
    from joined

)

select * from final
