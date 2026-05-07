with source as (

    select * from {{ source('mlb_raw', 'raw_player_pitching_stats') }}

),

renamed as (

    select
        -- identifiers
        game_pk,
        game_date,
        team_id,
        team_side,
        player_id,
        player_name,

        -- game pitching stats
        g_innings_pitched   as game_innings_pitched,
        g_hits              as game_hits,
        g_runs              as game_runs,
        g_earned_runs       as game_earned_runs,
        g_walks             as game_walks,
        g_strikeouts        as game_strikeouts,
        g_home_runs         as game_home_runs,
        g_number_of_pitches as game_number_of_pitches,
        g_strikes           as game_strikes,
        g_balls             as game_balls,
        g_batters_faced     as game_batters_faced,
        g_outs              as game_outs,
        g_era               as game_era,
        g_whip              as game_whip,
        g_hit_by_pitch      as game_hit_by_pitch,
        g_wild_pitches      as game_wild_pitches,
        g_balks             as game_balks,

        -- season snapshot pitching stats
        s_games_played          as season_games_played,
        s_games_started         as season_games_started,
        s_wins                  as season_wins,
        s_losses                as season_losses,
        s_saves                 as season_saves,
        s_holds                 as season_holds,
        s_blown_saves           as season_blown_saves,
        s_innings_pitched       as season_innings_pitched,
        s_hits                  as season_hits,
        s_runs                  as season_runs,
        s_earned_runs           as season_earned_runs,
        s_walks                 as season_walks,
        s_strikeouts            as season_strikeouts,
        s_home_runs             as season_home_runs,
        s_era                   as season_era,
        s_whip                  as season_whip,
        s_strikeouts_per_9      as season_strikeouts_per_9,
        s_walks_per_9           as season_walks_per_9,
        s_hits_per_9            as season_hits_per_9,
        s_strikeout_walk_ratio  as season_strikeout_walk_ratio,
        s_inherited_runners     as season_inherited_runners,
        s_inherited_runners_scored as season_inherited_runners_scored

    from source

)

select * from renamed
