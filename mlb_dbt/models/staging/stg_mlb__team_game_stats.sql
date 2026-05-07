with source as (

    select * from {{ source('mlb_raw', 'raw_team_game_stats') }}

),

renamed as (

    select
        -- identifiers
        game_pk,
        game_date,
        team_id,
        team_side,

        -- batting stats
        b_runs           as batting_runs,
        b_hits           as batting_hits,
        b_doubles        as batting_doubles,
        b_triples        as batting_triples,
        b_home_runs      as batting_home_runs,
        b_rbi            as batting_rbi,
        b_walks          as batting_walks,
        b_strikeouts     as batting_strikeouts,
        b_hit_by_pitch   as batting_hit_by_pitch,
        b_at_bats        as batting_at_bats,
        b_plate_appearances as batting_plate_appearances,
        b_left_on_base   as batting_left_on_base,
        b_stolen_bases   as batting_stolen_bases,
        b_caught_stealing as batting_caught_stealing,
        b_fly_outs       as batting_fly_outs,
        b_ground_outs    as batting_ground_outs,
        b_avg            as batting_avg,
        b_obp            as batting_obp,
        b_slg            as batting_slg,
        b_ops            as batting_ops,

        -- pitching stats
        p_runs           as pitching_runs,
        p_earned_runs    as pitching_earned_runs,
        p_hits           as pitching_hits,
        p_doubles        as pitching_doubles,
        p_triples        as pitching_triples,
        p_home_runs      as pitching_home_runs,
        p_walks          as pitching_walks,
        p_strikeouts     as pitching_strikeouts,
        p_hit_by_pitch   as pitching_hit_by_pitch,
        p_fly_outs       as pitching_fly_outs,
        p_ground_outs    as pitching_ground_outs,
        p_number_of_pitches as pitching_number_of_pitches,
        p_innings_pitched as pitching_innings_pitched,
        p_batters_faced  as pitching_batters_faced,
        p_outs           as pitching_outs,
        p_strikes        as pitching_strikes,
        p_balls          as pitching_balls,
        p_era            as pitching_era,
        p_whip           as pitching_whip

    from source

)

select * from renamed
