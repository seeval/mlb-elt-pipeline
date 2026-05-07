with source as (

    select * from {{ source('mlb_raw', 'raw_player_batting_stats') }}

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
        batting_order,

        -- game batting stats
        g_at_bats           as game_at_bats,
        g_runs              as game_runs,
        g_hits              as game_hits,
        g_doubles           as game_doubles,
        g_triples           as game_triples,
        g_home_runs         as game_home_runs,
        g_rbi               as game_rbi,
        g_walks             as game_walks,
        g_strikeouts        as game_strikeouts,
        g_left_on_base      as game_left_on_base,
        g_avg               as game_avg,
        g_obp               as game_obp,
        g_slg               as game_slg,
        g_ops               as game_ops,
        g_plate_appearances as game_plate_appearances,
        g_stolen_bases      as game_stolen_bases,
        g_caught_stealing   as game_caught_stealing,
        g_hit_by_pitch      as game_hit_by_pitch,

        -- season snapshot batting stats
        s_games_played      as season_games_played,
        s_at_bats           as season_at_bats,
        s_hits              as season_hits,
        s_doubles           as season_doubles,
        s_triples           as season_triples,
        s_home_runs         as season_home_runs,
        s_rbi               as season_rbi,
        s_walks             as season_walks,
        s_strikeouts        as season_strikeouts,
        s_avg               as season_avg,
        s_obp               as season_obp,
        s_slg               as season_slg,
        s_ops               as season_ops,
        s_plate_appearances as season_plate_appearances,
        s_stolen_bases      as season_stolen_bases,
        s_babip             as season_babip

    from source

)

select * from renamed
