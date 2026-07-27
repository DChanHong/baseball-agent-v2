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
