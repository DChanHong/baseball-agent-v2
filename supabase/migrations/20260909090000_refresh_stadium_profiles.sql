-- Verified stadium addresses and official links, 2026-09-09.
-- KBO team information lists offices inside each home stadium.
-- Keep this snapshot identical to supabase/seeds/stadium_profiles.sql.
-- Preserve coordinates, unrelated metadata, and existing dome classifications.
update public.kbo_stadiums
set
  region = stadium_profile_values.region,
  address = stadium_profile_values.address,
  is_dome = coalesce(public.kbo_stadiums.is_dome, stadium_profile_values.is_dome),
  official_url = stadium_profile_values.official_url,
  source_url = stadium_profile_values.source_url,
  as_of = date '2026-09-09',
  metadata = coalesce(public.kbo_stadiums.metadata, '{}'::jsonb) || stadium_profile_values.metadata || jsonb_build_object('address_verified_at', '2026-09-09', 'dome_status_note', '기존 2026-07-29 구장 분류 유지; 이번 갱신은 주소 및 공식 URL 확인')
from (
  values
    (
      'JAMSIL',
      '서울특별시',
      '서울특별시 송파구 올림픽로 25',
      false,
      'https://stadium.seoul.go.kr/',
      'https://www.koreabaseball.com/Kbo/League/TeamInfo.aspx',
      jsonb_build_object('source_note', 'LG 트윈스 및 두산 베어스 KBO 구단사무실 주소 기준', 'shared_home_team_ids', jsonb_build_array('LG', 'DOOSAN'))
    ),
    (
      'GOCHEOK',
      '서울특별시',
      '서울특별시 구로구 경인로 430',
      true,
      'https://www.sisul.or.kr/open_content/skydome/sitemap.jsp',
      'https://www.koreabaseball.com/Kbo/League/TeamInfo.aspx',
      jsonb_build_object('source_note', '키움 히어로즈 KBO 구단사무실 주소 기준')
    ),
    (
      'MUNHAK',
      '인천광역시',
      '인천광역시 미추홀구 매소홀로 618',
      false,
      'https://www.ssglanders.com/',
      'https://www.koreabaseball.com/Kbo/League/TeamInfo.aspx',
      jsonb_build_object('source_note', 'SSG 랜더스 KBO 구단사무실 주소 기준')
    ),
    (
      'GWANGJU',
      '광주광역시',
      '광주광역시 북구 서림로 10',
      false,
      'https://www.kiatigers.co.kr/',
      'https://www.koreabaseball.com/Kbo/League/TeamInfo.aspx',
      jsonb_build_object('source_note', 'KIA 타이거즈 KBO 구단사무실 주소 기준')
    ),
    (
      'DAEGU',
      '대구광역시',
      '대구광역시 수성구 야구전설로 1',
      false,
      'https://www.samsunglions.com/',
      'https://www.koreabaseball.com/Kbo/League/TeamInfo.aspx',
      jsonb_build_object('source_note', '삼성 라이온즈 KBO 구단사무실 주소 기준')
    ),
    (
      'SAJIK',
      '부산광역시',
      '부산광역시 동래구 사직로 45',
      false,
      'https://www.giantsclub.com/m/?pcode=499',
      'https://www.giantsclub.com/m/?pcode=499',
      jsonb_build_object('source_note', '롯데자이언츠 공식 사직구장 안내 주소 기준')
    ),
    (
      'CHANGWON',
      '경상남도',
      '경상남도 창원시 마산회원구 삼호로 63',
      false,
      'https://www.ncdinos.com/',
      'https://www.koreabaseball.com/Kbo/League/TeamInfo.aspx',
      jsonb_build_object('source_note', 'NC 다이노스 KBO 창원 사무실 주소 기준')
    ),
    (
      'DAEJEON',
      '대전광역시',
      '대전광역시 중구 대종로 373',
      false,
      'https://www.hanwhaeagles.co.kr/',
      'https://www.koreabaseball.com/Kbo/League/TeamInfo.aspx',
      jsonb_build_object('source_note', '한화 이글스 KBO 구단사무실 주소 기준')
    ),
    (
      'SUWON',
      '경기도',
      '경기도 수원시 장안구 경수대로 893',
      false,
      'https://www.ktwiz.co.kr/',
      'https://www.koreabaseball.com/Kbo/League/TeamInfo.aspx',
      jsonb_build_object('source_note', 'KT 위즈 KBO 구단사무실 주소 기준')
    ),
    (
      'POHANG',
      '경상북도',
      '경상북도 포항시 남구 희망대로 790',
      false,
      'https://www.phsisul.org/sisul_6/main.do',
      'https://www.phsisul.org/sisul_6/main.do',
      jsonb_build_object('source_note', '포항시시설관리공단 포항야구장 공식 안내 주소 기준')
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
