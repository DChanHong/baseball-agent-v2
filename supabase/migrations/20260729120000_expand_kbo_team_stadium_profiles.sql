alter table public.kbo_teams
  add column if not exists region text null,
  add column if not exists office_address text null,
  add column if not exists founded_year integer null,
  add column if not exists official_url text null,
  add column if not exists ticket_provider text null,
  add column if not exists ticket_url text null,
  add column if not exists source_url text null,
  add column if not exists as_of date null,
  add column if not exists metadata jsonb not null default '{}'::jsonb;

alter table public.kbo_stadiums
  add column if not exists region text null,
  add column if not exists address text null,
  add column if not exists latitude numeric(9, 6) null,
  add column if not exists longitude numeric(9, 6) null,
  add column if not exists is_dome boolean null,
  add column if not exists official_url text null,
  add column if not exists source_url text null,
  add column if not exists as_of date null,
  add column if not exists metadata jsonb not null default '{}'::jsonb;

alter table public.kbo_teams
  add constraint kbo_teams_founded_year_check
  check (founded_year is null or founded_year between 1982 and 2100);

alter table public.kbo_stadiums
  add constraint kbo_stadiums_latitude_check
  check (latitude is null or latitude between -90 and 90);

alter table public.kbo_stadiums
  add constraint kbo_stadiums_longitude_check
  check (longitude is null or longitude between -180 and 180);

comment on column public.kbo_teams.region is
  'KBO official 연고지역 value used for team profile answers.';

comment on column public.kbo_teams.office_address is
  'KBO official 구단사무실 address as of the profile source date.';

comment on column public.kbo_teams.founded_year is
  'KBO official 창단년도.';

comment on column public.kbo_teams.official_url is
  'Team official homepage URL.';

comment on column public.kbo_teams.ticket_provider is
  'Primary ticket provider from the KBO ticket guide. Values are descriptive, not an enum.';

comment on column public.kbo_teams.ticket_url is
  'Primary ticket URL from KBO ticket guide or official team ticket site.';

comment on column public.kbo_teams.source_url is
  'Primary official source URL for structured team profile fields.';

comment on column public.kbo_teams.metadata is
  'Volatile or less frequently queried team profile fields such as owner, executives, manager, and championship history.';

comment on column public.kbo_stadiums.region is
  'Broad administrative region for stadium profile answers.';

comment on column public.kbo_stadiums.address is
  'Official or team-profile-backed stadium address.';

comment on column public.kbo_stadiums.is_dome is
  'Whether the stadium is a dome. Useful for deterministic weather-related routing.';

comment on column public.kbo_stadiums.source_url is
  'Primary official source URL for structured stadium profile fields.';

comment on column public.kbo_stadiums.metadata is
  'Less stable or source-specific stadium profile fields that should not be promoted to columns yet.';

update public.kbo_teams
set
  region = team_profile_values.region,
  office_address = team_profile_values.office_address,
  founded_year = team_profile_values.founded_year,
  official_url = team_profile_values.official_url,
  ticket_provider = team_profile_values.ticket_provider,
  ticket_url = team_profile_values.ticket_url,
  source_url = 'https://www.koreabaseball.com/kbo/league/teaminfo.aspx',
  as_of = date '2026-07-29',
  metadata = team_profile_values.metadata
from (
  values
    (
      'LG',
      '서울특별시',
      '서울특별시 송파구 올림픽로 25 잠실야구장 내(우05500)',
      1990,
      'https://www.lgtwins.com',
      'ticketlink',
      'https://www.ticketlink.co.kr',
      jsonb_build_object(
        'owner', '구광모',
        'owner_representative', '구본능',
        'ceo', '김인석',
        'general_manager', '차명석',
        'manager', '염경엽',
        'championship_count', 4,
        'championship_years', jsonb_build_array(1990, 1994, 2023, 2025),
        'ticket_source_url', 'https://www.koreabaseball.com/kbo/league/map.aspx'
      )
    ),
    (
      'DOOSAN',
      '서울특별시',
      '서울특별시 송파구 올림픽로 25 잠실야구장 내(우05500)',
      1982,
      'https://www.doosanbears.com',
      'interpark',
      'https://ticket.interpark.com',
      jsonb_build_object(
        'owner', '박정원',
        'owner_representative', '고영섭',
        'ceo', '고영섭',
        'general_manager', '김태룡',
        'manager', '김원형',
        'championship_count', 6,
        'championship_years', jsonb_build_array(1982, 1995, 2001, 2015, 2016, 2019),
        'championship_note', 'OB 베어스 우승 기록 포함',
        'ticket_source_url', 'https://www.koreabaseball.com/kbo/league/map.aspx'
      )
    ),
    (
      'KIWOOM',
      '서울특별시',
      '서울특별시 구로구 경인로 430 고척스카이돔 내(우08275)',
      2008,
      'https://www.heroesbaseball.co.kr',
      'interpark',
      'https://ticket.interpark.com',
      jsonb_build_object(
        'owner', '위재민',
        'ceo', '위재민',
        'general_manager', '허승필',
        'manager', '설종진',
        'championship_count', 0,
        'championship_years', jsonb_build_array(),
        'ticket_source_url', 'https://www.koreabaseball.com/kbo/league/map.aspx'
      )
    ),
    (
      'SSG',
      '인천광역시',
      '인천광역시 미추홀구 매소홀로 618 인천SSG랜더스필드 내(우22234)',
      2021,
      'https://www.ssglanders.com',
      'team_site',
      'https://ticket.ssg.com',
      jsonb_build_object(
        'owner', '정용진',
        'ceo', '김재섭',
        'general_manager', '김재현',
        'manager', '이숭용',
        'championship_count', 5,
        'championship_years', jsonb_build_array(2007, 2008, 2010, 2018, 2022),
        'championship_note', 'SK 와이번스 우승 기록 포함',
        'ticket_source_url', 'https://www.koreabaseball.com/kbo/league/map.aspx'
      )
    ),
    (
      'KIA',
      '광주광역시',
      '광주광역시 북구 서림로 10 광주-기아 챔피언스 필드 내 2층(우61255)',
      2001,
      'https://www.kiatigers.co.kr',
      'ticketlink',
      'https://www.ticketlink.co.kr',
      jsonb_build_object(
        'owner', '송호성',
        'ceo', '김민수',
        'general_manager', '심재학',
        'manager', '이범호',
        'championship_count', 12,
        'championship_years', jsonb_build_array(1983, 1986, 1987, 1988, 1989, 1991, 1993, 1996, 1997, 2009, 2017, 2024),
        'championship_note', '해태 타이거즈 우승 기록 포함',
        'ticket_source_url', 'https://www.koreabaseball.com/kbo/league/map.aspx'
      )
    ),
    (
      'SAMSUNG',
      '대구광역시',
      '대구광역시 수성구 야구전설로 1 대구삼성라이온즈파크 내(우42250)',
      1982,
      'https://www.samsunglions.com',
      'ticketlink',
      'https://www.ticketlink.co.kr',
      jsonb_build_object(
        'owner', '유정근',
        'ceo', '유정근',
        'general_manager', '이종열',
        'manager', '박진만',
        'championship_count', 8,
        'championship_years', jsonb_build_array(1985, 2002, 2005, 2006, 2011, 2012, 2013, 2014),
        'ticket_source_url', 'https://www.koreabaseball.com/kbo/league/map.aspx'
      )
    ),
    (
      'LOTTE',
      '부산광역시',
      '부산광역시 동래구 사직로 45 사직야구장 내(우47874)',
      1982,
      'https://www.giantsclub.com',
      'team_site',
      'https://ticket.giantsclub.com',
      jsonb_build_object(
        'owner', '신동빈',
        'ceo', '이강훈',
        'general_manager', '박준혁',
        'manager', '김태형',
        'championship_count', 2,
        'championship_years', jsonb_build_array(1984, 1992),
        'ticket_source_url', 'https://www.koreabaseball.com/kbo/league/map.aspx'
      )
    ),
    (
      'NC',
      '창원시',
      '분당 사무실 경기도 성남시 분당구 대왕판교로 644번길 12 엔씨소프트 판교 R&D센터 C동 12층(우13494); 창원 사무실 경상남도 창원시 마산회원구 삼호로 63 창원NC파크 내(우51323)',
      2011,
      'https://www.ncdinos.com',
      'team_site',
      'https://ticket.ncdinos.com',
      jsonb_build_object(
        'owner', '김택진',
        'ceo', '이진만',
        'general_manager', '임선남',
        'manager', '이호준',
        'championship_count', 1,
        'championship_years', jsonb_build_array(2020),
        'ticket_source_url', 'https://www.koreabaseball.com/kbo/league/map.aspx'
      )
    ),
    (
      'HANWHA',
      '대전광역시',
      '대전광역시 중구 대종로 373 한화이글스(우35021)',
      1986,
      'https://www.hanwhaeagles.co.kr',
      'ticketlink',
      'https://www.ticketlink.co.kr',
      jsonb_build_object(
        'owner', '김승연',
        'owner_representative', '박종태',
        'ceo', '박종태',
        'general_manager', '손혁',
        'manager', '김경문',
        'championship_count', 1,
        'championship_years', jsonb_build_array(1999),
        'ticket_source_url', 'https://www.koreabaseball.com/kbo/league/map.aspx'
      )
    ),
    (
      'KT',
      '수원시',
      '경기도 수원시 장안구 경수대로 893 수원 케이티 위즈 파크 내(우16308)',
      2013,
      'https://www.ktwiz.co.kr',
      'ticketlink',
      'https://www.ticketlink.co.kr',
      jsonb_build_object(
        'owner', '박윤영',
        'ceo', '이선주',
        'general_manager', '나도현',
        'manager', '이강철',
        'championship_count', 1,
        'championship_years', jsonb_build_array(2021),
        'ticket_source_url', 'https://www.koreabaseball.com/kbo/league/map.aspx'
      )
    )
) as team_profile_values(
  id,
  region,
  office_address,
  founded_year,
  official_url,
  ticket_provider,
  ticket_url,
  metadata
)
where public.kbo_teams.id = team_profile_values.id;

update public.kbo_stadiums
set
  region = stadium_profile_values.region,
  address = stadium_profile_values.address,
  latitude = null,
  longitude = null,
  is_dome = stadium_profile_values.is_dome,
  official_url = stadium_profile_values.official_url,
  source_url = stadium_profile_values.source_url,
  as_of = date '2026-07-29',
  metadata = stadium_profile_values.metadata
from (
  values
    (
      'JAMSIL',
      '서울특별시',
      '서울특별시 송파구 올림픽로 25',
      false,
      null,
      'https://www.koreabaseball.com/kbo/league/teaminfo.aspx',
      jsonb_build_object('source_note', 'LG 트윈스 및 두산 베어스 KBO 구단사무실 주소 기준', 'shared_home_team_ids', jsonb_build_array('LG', 'DOOSAN'))
    ),
    (
      'GOCHEOK',
      '서울특별시',
      '서울특별시 구로구 경인로 430',
      true,
      null,
      'https://www.koreabaseball.com/kbo/league/teaminfo.aspx',
      jsonb_build_object('source_note', '키움 히어로즈 KBO 구단사무실 주소 기준')
    ),
    (
      'MUNHAK',
      '인천광역시',
      '인천광역시 미추홀구 매소홀로 618',
      false,
      null,
      'https://www.koreabaseball.com/kbo/league/teaminfo.aspx',
      jsonb_build_object('source_note', 'SSG 랜더스 KBO 구단사무실 주소 기준')
    ),
    (
      'GWANGJU',
      '광주광역시',
      '광주광역시 북구 서림로 10',
      false,
      null,
      'https://www.koreabaseball.com/kbo/league/teaminfo.aspx',
      jsonb_build_object('source_note', 'KIA 타이거즈 KBO 구단사무실 주소 기준')
    ),
    (
      'DAEGU',
      '대구광역시',
      '대구광역시 수성구 야구전설로 1',
      false,
      null,
      'https://www.koreabaseball.com/kbo/league/teaminfo.aspx',
      jsonb_build_object('source_note', '삼성 라이온즈 KBO 구단사무실 주소 기준')
    ),
    (
      'SAJIK',
      '부산광역시',
      '부산광역시 동래구 사직로 45',
      false,
      null,
      'https://www.koreabaseball.com/kbo/league/teaminfo.aspx',
      jsonb_build_object('source_note', '롯데 자이언츠 KBO 구단사무실 주소 기준')
    ),
    (
      'CHANGWON',
      '경상남도',
      '경상남도 창원시 마산회원구 삼호로 63',
      false,
      null,
      'https://www.koreabaseball.com/kbo/league/teaminfo.aspx',
      jsonb_build_object('source_note', 'NC 다이노스 KBO 창원 사무실 주소 기준')
    ),
    (
      'DAEJEON',
      '대전광역시',
      '대전광역시 중구 대종로 373',
      false,
      null,
      'https://www.koreabaseball.com/kbo/league/teaminfo.aspx',
      jsonb_build_object('source_note', '한화 이글스 KBO 구단사무실 주소 기준')
    ),
    (
      'SUWON',
      '경기도',
      '경기도 수원시 장안구 경수대로 893',
      false,
      null,
      'https://www.koreabaseball.com/kbo/league/teaminfo.aspx',
      jsonb_build_object('source_note', 'KT 위즈 KBO 구단사무실 주소 기준')
    ),
    (
      'POHANG',
      '경상북도',
      null,
      false,
      null,
      null,
      jsonb_build_object('source_note', '보조 구장. 공식 주소 출처 확정 후 보강 필요')
    )
) as stadium_profile_values(
  id,
  region,
  address,
  is_dome,
  official_url,
  source_url,
  metadata
)
where public.kbo_stadiums.id = stadium_profile_values.id;

create index if not exists kbo_teams_region_idx
  on public.kbo_teams (region)
  where region is not null;

create index if not exists kbo_teams_founded_year_idx
  on public.kbo_teams (founded_year)
  where founded_year is not null;

create index if not exists kbo_teams_ticket_provider_idx
  on public.kbo_teams (ticket_provider)
  where ticket_provider is not null;

create index if not exists kbo_stadiums_region_idx
  on public.kbo_stadiums (region)
  where region is not null;

create index if not exists kbo_stadiums_is_dome_idx
  on public.kbo_stadiums (is_dome)
  where is_dome is not null;
