with all_games as (

    select * from {{ ref('stg_mlb__team_game_stats') }}

),

-- A game_pk can appear under multiple game_dates if a game is
-- rescheduled or the API returns it on multiple days.
-- Keep only the most recent game_date per game_pk to avoid
-- fan-out in the self-join below.
deduped as (

    select *
    from all_games
    qualify row_number() over (
        partition by game_pk, team_side
        order by game_date desc
    ) = 1

),

games as (

    select
        game_pk,
        game_date,
        team_id,
        team_side

    from deduped
    where team_side = 'home'

),

home_away as (

    select
        home.game_pk,
        home.game_date,
        home.team_id                          as home_team_id,
        away.team_id                          as away_team_id

    from games home
    inner join deduped away
        on home.game_pk = away.game_pk
        and away.team_side = 'away'

),

series_spine as (

    -- assign series_start_date as the minimum game_date
    -- for the same home/away matchup within a 7-day window
    -- 7 days covers the longest possible series including travel days
    select
        game_pk,
        game_date,
        home_team_id,
        away_team_id,
        min(game_date) over (
            partition by home_team_id, away_team_id
            order by unix_date(game_date)
            range between 6 preceding and current row
        )                                     as series_start_date

    from home_away

),

with_series_id as (

    select
        game_pk,
        game_date,
        home_team_id,
        away_team_id,
        series_start_date,
        -- surrogate key: deterministic hash of the three series-defining fields
        {{ dbt_utils.generate_surrogate_key([
            'home_team_id',
            'away_team_id',
            'series_start_date'
        ]) }}                                 as series_id

    from series_spine

)

select * from with_series_id
