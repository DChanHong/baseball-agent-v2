insert into public.kbo_teams (
  id,
  name_ko,
  name_en,
  short_name,
  aliases,
  home_stadium_id,
  is_active
)
values
  ('LG', 'LG 트윈스', 'LG Twins', 'LG', array['LG', '엘지', 'LG 트윈스', '엘지 트윈스'], null, true),
  ('DOOSAN', '두산 베어스', 'Doosan Bears', '두산', array['두산', '두산 베어스'], null, true),
  ('KIWOOM', '키움 히어로즈', 'Kiwoom Heroes', '키움', array['키움', '키움 히어로즈'], null, true),
  ('SSG', 'SSG 랜더스', 'SSG Landers', 'SSG', array['SSG', '쓱', 'SSG 랜더스', '쓱 랜더스'], null, true),
  ('KIA', 'KIA 타이거즈', 'KIA Tigers', 'KIA', array['KIA', '기아', 'KIA 타이거즈', '기아 타이거즈'], null, true),
  ('SAMSUNG', '삼성 라이온즈', 'Samsung Lions', '삼성', array['삼성', '삼성 라이온즈'], null, true),
  ('LOTTE', '롯데 자이언츠', 'Lotte Giants', '롯데', array['롯데', '롯데 자이언츠'], null, true),
  ('NC', 'NC 다이노스', 'NC Dinos', 'NC', array['NC', '엔씨', 'NC 다이노스', '엔씨 다이노스'], null, true),
  ('HANWHA', '한화 이글스', 'Hanwha Eagles', '한화', array['한화', '한화 이글스'], null, true),
  ('KT', 'KT 위즈', 'KT Wiz', 'KT', array['KT', '케이티', 'KT 위즈', '케이티 위즈'], null, true)
on conflict (id) do update
set
  name_ko = excluded.name_ko,
  name_en = excluded.name_en,
  short_name = excluded.short_name,
  aliases = excluded.aliases,
  is_active = excluded.is_active;

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

update public.kbo_teams
set home_stadium_id = case id
  when 'LG' then 'JAMSIL'
  when 'DOOSAN' then 'JAMSIL'
  when 'KIWOOM' then 'GOCHEOK'
  when 'SSG' then 'MUNHAK'
  when 'KIA' then 'GWANGJU'
  when 'SAMSUNG' then 'DAEGU'
  when 'LOTTE' then 'SAJIK'
  when 'NC' then 'CHANGWON'
  when 'HANWHA' then 'DAEJEON'
  when 'KT' then 'SUWON'
  else home_stadium_id
end
where id in (
  'LG',
  'DOOSAN',
  'KIWOOM',
  'SSG',
  'KIA',
  'SAMSUNG',
  'LOTTE',
  'NC',
  'HANWHA',
  'KT'
);
