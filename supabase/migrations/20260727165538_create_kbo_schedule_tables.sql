create table public.kbo_teams (
  id text primary key,
  name_ko text not null,
  name_en text null,
  short_name text not null,
  aliases text[] not null default '{}',
  home_stadium_id text null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint kbo_teams_id_not_blank_check
    check (length(btrim(id)) > 0),
  constraint kbo_teams_name_ko_not_blank_check
    check (length(btrim(name_ko)) > 0),
  constraint kbo_teams_short_name_not_blank_check
    check (length(btrim(short_name)) > 0)
);

comment on table public.kbo_teams is
  'Stores canonical KBO teams and aliases used for schedule lookup normalization.';

comment on column public.kbo_teams.id is
  'Stable service-owned team identifier such as LG, LOTTE, or DOOSAN.';

comment on column public.kbo_teams.aliases is
  'Korean, English, short, and user-entered team aliases used before querying games.';

alter table public.kbo_teams enable row level security;

create table public.kbo_stadiums (
  id text primary key,
  name_ko text not null,
  short_name text not null,
  aliases text[] not null default '{}',
  city text null,
  home_team_id text null references public.kbo_teams(id) on delete set null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint kbo_stadiums_id_not_blank_check
    check (length(btrim(id)) > 0),
  constraint kbo_stadiums_name_ko_not_blank_check
    check (length(btrim(name_ko)) > 0),
  constraint kbo_stadiums_short_name_not_blank_check
    check (length(btrim(short_name)) > 0)
);

comment on table public.kbo_stadiums is
  'Stores canonical KBO stadium names and aliases used by schedule and stadium tools.';

comment on column public.kbo_stadiums.home_team_id is
  'Primary home team for the stadium when one exists. Shared or neutral stadiums can be null.';

alter table public.kbo_stadiums enable row level security;

alter table public.kbo_teams
  add constraint kbo_teams_home_stadium_id_fkey
  foreign key (home_stadium_id)
  references public.kbo_stadiums(id)
  on delete set null;

create table public.kbo_games (
  id uuid primary key default gen_random_uuid(),
  season_year integer not null,
  source_game_id text null,
  internal_game_key text not null,
  game_date date not null,
  start_time time null,
  starts_at timestamptz null,
  away_team_id text not null references public.kbo_teams(id),
  home_team_id text not null references public.kbo_teams(id),
  stadium_id text not null references public.kbo_stadiums(id),
  away_team_name text not null,
  home_team_name text not null,
  stadium_name text not null,
  game_status text not null,
  status_reason text null,
  away_score integer null,
  home_score integer null,
  source_name text not null default 'KBO',
  source_url text not null,
  source_collected_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint kbo_games_internal_game_key_key
    unique (internal_game_key),
  constraint kbo_games_season_year_check
    check (season_year between 1982 and 2100),
  constraint kbo_games_internal_game_key_not_blank_check
    check (length(btrim(internal_game_key)) > 0),
  constraint kbo_games_team_match_check
    check (away_team_id <> home_team_id),
  constraint kbo_games_game_status_check
    check (game_status in (
      'scheduled',
      'in_progress',
      'completed',
      'cancelled',
      'postponed',
      'unknown'
    )),
  constraint kbo_games_away_score_check
    check (away_score is null or away_score >= 0),
  constraint kbo_games_home_score_check
    check (home_score is null or home_score >= 0),
  constraint kbo_games_score_status_check
    check (
      (game_status in ('completed', 'in_progress') and away_score is not null and home_score is not null)
      or
      (game_status not in ('completed', 'in_progress'))
    )
);

comment on table public.kbo_games is
  'Stores normalized KBO schedule rows used by find_kbo_game and later Agent tools.';

comment on column public.kbo_games.source_game_id is
  'KBO-provided game id when available. Some scheduled or cancelled games may not include it.';

comment on column public.kbo_games.internal_game_key is
  'Service-owned stable upsert key generated from date, teams, stadium, and optional sequence data.';

comment on column public.kbo_games.source_collected_at is
  'Timestamp when the source schedule response was collected. Used for freshness and stale-data warnings.';

alter table public.kbo_games enable row level security;

create table public.kbo_game_status_history (
  id uuid primary key default gen_random_uuid(),
  game_id uuid not null references public.kbo_games(id) on delete cascade,
  previous_status text null,
  new_status text not null,
  previous_reason text null,
  new_reason text null,
  previous_away_score integer null,
  previous_home_score integer null,
  new_away_score integer null,
  new_home_score integer null,
  changed_at timestamptz not null default now(),

  constraint kbo_game_status_history_new_status_check
    check (new_status in (
      'scheduled',
      'in_progress',
      'completed',
      'cancelled',
      'postponed',
      'unknown'
    )),
  constraint kbo_game_status_history_previous_status_check
    check (
      previous_status is null
      or previous_status in (
        'scheduled',
        'in_progress',
        'completed',
        'cancelled',
        'postponed',
        'unknown'
      )
    ),
  constraint kbo_game_status_history_previous_away_score_check
    check (previous_away_score is null or previous_away_score >= 0),
  constraint kbo_game_status_history_previous_home_score_check
    check (previous_home_score is null or previous_home_score >= 0),
  constraint kbo_game_status_history_new_away_score_check
    check (new_away_score is null or new_away_score >= 0),
  constraint kbo_game_status_history_new_home_score_check
    check (new_home_score is null or new_home_score >= 0)
);

comment on table public.kbo_game_status_history is
  'Stores status and score changes detected while syncing KBO schedule data.';

alter table public.kbo_game_status_history enable row level security;

create index kbo_teams_short_name_idx
  on public.kbo_teams (short_name);

create index kbo_teams_aliases_gin_idx
  on public.kbo_teams using gin (aliases);

create index kbo_stadiums_short_name_idx
  on public.kbo_stadiums (short_name);

create index kbo_stadiums_aliases_gin_idx
  on public.kbo_stadiums using gin (aliases);

create index kbo_stadiums_home_team_idx
  on public.kbo_stadiums (home_team_id)
  where home_team_id is not null;

create index kbo_games_date_idx
  on public.kbo_games (game_date);

create index kbo_games_home_team_date_idx
  on public.kbo_games (home_team_id, game_date);

create index kbo_games_away_team_date_idx
  on public.kbo_games (away_team_id, game_date);

create index kbo_games_stadium_date_idx
  on public.kbo_games (stadium_id, game_date);

create index kbo_games_status_starts_at_idx
  on public.kbo_games (game_status, starts_at);

create index kbo_games_source_game_id_idx
  on public.kbo_games (source_game_id)
  where source_game_id is not null;

create index kbo_game_status_history_game_changed_at_idx
  on public.kbo_game_status_history (game_id, changed_at desc);

create trigger set_kbo_teams_updated_at
before update on public.kbo_teams
for each row
execute function public.set_updated_at();

create trigger set_kbo_stadiums_updated_at
before update on public.kbo_stadiums
for each row
execute function public.set_updated_at();

create trigger set_kbo_games_updated_at
before update on public.kbo_games
for each row
execute function public.set_updated_at();
