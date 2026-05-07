with games as (

    select
        game_pk,
        game_date,
        team_id,
        team_side,
        game_date as approx_series_start

    from {{ ref('stg_mlb__team_game_stats') }}
    where team_side = 'home'  -- one row per game, not two

),

home_away as (

    -- reconstruct home/away team IDs per game from team stats
    select
        home.game_pk,
        home.game_date,
        home.team_id                          as home_team_id,
        away.team_id                          as away_team_id

    from games home
    inner join {{ ref('stg_mlb__team_game_stats') }} away
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
