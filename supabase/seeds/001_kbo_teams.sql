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
