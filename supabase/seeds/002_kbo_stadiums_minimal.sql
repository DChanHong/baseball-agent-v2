insert into public.kbo_stadiums (
  id,
  name_ko,
  short_name,
  aliases,
  city,
  home_team_id,
  is_active
)
values
  ('JAMSIL', '서울종합운동장 야구장', '잠실', array['잠실', '잠실야구장', '서울종합운동장', '서울종합운동장 야구장'], '서울', null, true),
  ('GOCHEOK', '고척스카이돔', '고척', array['고척', '고척돔', '고척스카이돔'], '서울', 'KIWOOM', true),
  ('MUNHAK', '인천 SSG 랜더스필드', '문학', array['문학', '문학야구장', '랜더스필드', '인천 SSG 랜더스필드'], '인천', 'SSG', true),
  ('GWANGJU', '광주-기아 챔피언스 필드', '광주', array['광주', '광주기아챔피언스필드', '광주-기아 챔피언스 필드'], '광주', 'KIA', true),
  ('DAEGU', '대구 삼성 라이온즈 파크', '대구', array['대구', '대구야구장', '라이온즈파크', '대구 삼성 라이온즈 파크'], '대구', 'SAMSUNG', true),
  ('SAJIK', '부산 사직 야구장', '사직', array['사직', '사직야구장', '부산 사직 야구장'], '부산', 'LOTTE', true),
  ('CHANGWON', '창원 NC 파크', '창원', array['창원', '창원NC파크', '창원 NC 파크'], '창원', 'NC', true),
  ('DAEJEON', '대전 한화생명 볼파크', '대전', array['대전', '대전야구장', '한화생명볼파크', '대전 한화생명 볼파크'], '대전', 'HANWHA', true),
  ('SUWON', '수원 KT 위즈파크', '수원', array['수원', '수원야구장', '위즈파크', '수원 KT 위즈파크'], '수원', 'KT', true),
  ('POHANG', '포항 야구장', '포항', array['포항', '포항야구장'], '포항', null, true)
on conflict (id) do update
set
  name_ko = excluded.name_ko,
  short_name = excluded.short_name,
  aliases = excluded.aliases,
  city = excluded.city,
  home_team_id = excluded.home_team_id,
  is_active = excluded.is_active;
