# RAGAS 평가 후보 데이터셋 전체 보기

2026-10-14 기준으로 구성한 50개 합성 질문이다. 사람 검수 전 후보이며 기대답변은 실제 agent 출력이 아니다. 정책·고정 문맥 사례는 외부 사실 출처 대신 서비스 계약 또는 합성 fixture를 사용한다. 출처 링크는 당시 확인 기록이며 현재 정책을 보장하지 않는다.

이 목록은 원본 JSON의 읽기용 축약본이다. 실제 실행 상태는 2026-10-15 결과 파일을 따른다.

| ID | 유형 | 질문 | 기대 사실 | 출처·기준 | 실행 |
|---|---|---|---|---|---|
| golden_guide_001 | 구장 이용 안내 | 고척돔 음식물 반입 가능해? | 프로야구 음식물 반입 가능; 행사 성격별 제한; 재입장 음식물 반입 불가 | [음식물 반입 FAQ](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp) | 실행 완료 |
| golden_guide_002 | 구장 이용 안내 | 고척 야구 보러 가는데 내부 주차장에 차 대면 돼? | 프로야구 내부 주차장 이용 불가; 대중교통 권장 | [티켓수령 및 입장 > 내부 주차장](https://heroesbaseball.co.kr/ticket/normal/viewPurchase.do) | 실행 완료 |
| golden_guide_003 | 구장 이용 안내 | 사직구장 지하철 몇 호선 타고 어느 역에서 내려? | 부산 3호선; 사직역 또는 종합운동장역 | [오시는 길 > 지하철](https://www.giantsclub.com/html/?pcode=207) | 실행 완료 |
| golden_guide_004 | 구장 이용 안내 | 잠실 야구 보러 가면 주차비가 항상 5분당 요금이야? | 평시 후불과 경기일 선불 구분; 소형 선불 6,000원; 만차 입차 불가 가능 | [평상시/프로야구 선불제, 기타사항](https://stadium.seoul.go.kr/about/park-info) | 실행 완료 |
| golden_guide_005 | 구장 이용 안내 | 수원 KT위즈파크는 경기일 주차 예약 없이 가도 돼? | 프로야구 경기일 일반 차량 주차예약제; 미예약 일반 차량 주차 불가; 25인승 소형버스 이상·장애인 차량 예약 제외 | [주차예약 안내](https://www.ktwiz.co.kr/wizpark/parking) | 실행 완료 |
| golden_guide_006 | 구장 이용 안내 | 문학구장 승용차 주차 요금이 얼마고 경기 취소되면 돌려줘? | 승용차 전일 2,000원; 행사 취소로 주차요금 환불 안 됨 | [주차요금 > 행사 취소 환불 안내](https://www.ssglanders.com/stadium/parking) | 실행 완료 |
| golden_guide_007 | 구장 이용 안내 | 창원NC파크에 레이저 포인터 가져가도 돼? | 레이저 포인터 반입 제한; 구단별 예외·세부 정책 확인 | [FAQ 위험 물품 및 구단별 예외](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 실행 완료 |
| golden_guide_008 | 구장 이용 안내 | 광주 챔필에 유리병 음료 들고 들어갈 수 있어? | 유리병 반입 제한 | [안전·보안 규정 > 음료 용기](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 실행 완료 |
| golden_guide_009 | 구장 이용 안내 | 라팍에 뜨거운 국물 음식도 가져가도 되는 거야? | 일반 음식 허용과 뜨거운 국물 제한 가능 구분 | [FAQ 7 음식물](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 실행 완료 |
| golden_guide_010 | 구장 이용 안내 | 대전 볼파크에 접이식 의자 가져가도 돼? 잔디석도 같아? | 휴대용 의자 원칙적 제한; 구단 허용 구역 예외 가능; 대전 예외는 별도 확인 | [FAQ 6 휴대용 의자·잔디석 예외](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 실행 완료 |
| golden_guide_011 | 구장 이용 안내 | 고척돔 안에서 담배 피울 수 있어? | 내부 금연; 외부 지정 흡연 부스 | [흡연 시설 FAQ](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp) | 실행 완료 |
| golden_guide_012 | 구장 이용 안내 | 고척에서 야구 보다가 지갑 잃어버렸어. 어디에 문의해? | 프로야구 분실물은 키움 관리; 키움 문의 | [분실물 FAQ](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp) | 실행 완료 |
| golden_guide_013 | 구장 이용 안내 | 대전 새 볼파크에 아기랑 가는데 수유실 있어? | 대전 볼파크에 수유실 있음; 공식 편의시설 1층 내부 항목 | [편의시설 탭 > 1층 > 내부 > 수유실](https://www.hanwhaeagles.co.kr/MN/EP/MNEPPI01.do) | 실행 완료 |
| golden_guide_014 | 구장 이용 안내 | 사직에서 유니폼 사려면 구장 어디로 가야 해? | 유니폼샵 광장 1루측 컨테이너 1층; 프로페셔널샵 1층 중앙출입구 오른편 | [유니폼샵·프로페셔널샵 위치](https://www.giantsclub.com/html/?pcode=367) | 실행 완료 |
| golden_guide_015 | 구장 이용 안내 | 잠실 LG 홈경기에 30개월 아기 데려가면 자리도 무료야? | 36개월 미만 무료입장; 좌석 점유 시 티켓 구매; 증빙서류 지참 | [미취학 아동 할인 및 관람 유의사항](https://www.lgtwins.com/ticket/general) | 실행 완료 |
| golden_ticket_001 | 예매 안내 | 사직 예매 어디서 해? | LOTTE 홈경기 공식 예매처: 롯데 자체 예매; ticket.giantsclub.com | [예매처 > LOTTE](https://www.koreabaseball.com/kbo/league/map.aspx) | 실행 완료 |
| golden_ticket_002 | 예매 안내 | 우리 팀 경기 예매 방법 알려줘 | NC 홈경기 공식 예매처: NC 자체 예매; ticket.ncdinos.com; favorite_team_id=NC로 생략된 우리 팀 해석 | [예매처 > NC](https://www.koreabaseball.com/kbo/league/map.aspx); golden_ticket_002.input 문맥·선호팀 | 실행 완료 |
| golden_ticket_003 | 예매 안내 | SSG 문학 홈경기 표 어디서 사? | SSG 홈경기 공식 예매처: SSG 자체 예매; ticket.ssg.com | [예매처 > SSG](https://www.koreabaseball.com/kbo/league/map.aspx) | 실행 완료 |
| golden_ticket_004 | 예매 안내 | KIA 광주 홈경기 예매 사이트 알려줘 | KIA 홈경기 공식 예매처: 티켓링크; www.ticketlink.co.kr | [예매처 > KIA](https://www.koreabaseball.com/kbo/league/map.aspx) | 실행 완료 |
| golden_ticket_005 | 예매 안내 | 한화 대전 홈경기는 어디서 예매해? | HANWHA 홈경기 공식 예매처: 티켓링크; www.ticketlink.co.kr | [예매처 > HANWHA](https://www.koreabaseball.com/kbo/league/map.aspx) | 실행 완료 |
| golden_ticket_006 | 예매 안내 | LG 잠실 홈경기 일반 예매는 며칠 전 몇 시에 열려? | 7일 전 11시; 경기 시작 후 1시간까지 | [2026 티켓 예매 안내 > 예매 기간](https://www.lgtwins.com/ticket/general) | 실행 완료 |
| golden_ticket_007 | 예매 안내 | 키움 홈경기 표 4장 중 1장만 취소할 수 있어? | 부분취소 불가; 전체 취소 후 재예매; 기존 좌석 선점 보장 없음 | [예매취소 및 환불 > 부분취소](https://heroesbaseball.co.kr/ticket/normal/viewPurchase.do) | 실행 완료 |
| golden_ticket_008 | 예매 안내 | 두산 잠실 홈경기는 LG랑 같은 예매 사이트야? | DOOSAN 홈경기 공식 예매처: NOL 티켓; nol.yanolja.com; LG는 티켓링크로 홈팀별 예매처가 다름 | [예매처 > DOOSAN](https://www.koreabaseball.com/kbo/league/map.aspx) | 실행 완료 |
| golden_ticket_009 | 예매 안내 | 삼성 홈경기 우천취소면 발권한 표도 자동 환불돼? | 미발권/발권 구분 및 구매수단별 환불 절차를 현재 공식 안내로 재확인; 상충하는 문구를 근거로 자동 환불이나 현장 환불을 확정하지 않음 | [인터넷 예매/전화 예매 > 우천 취소](https://www.samsunglions.com/m/ticket/score_4_1_4.asp) | 보류: 출처 확인 필요 |
| golden_ticket_010 | 예매 안내 | KT 수원 홈경기 표는 티켓링크에서 예매하는 게 맞아? | KT는 티켓링크; www.ticketlink.co.kr | [예매처 > 티켓링크 KT](https://www.koreabaseball.com/kbo/league/map.aspx) | 실행 완료 |
| golden_knowledge_001 | 야구 지식 | 보크가 뭐야? | 주자 존재; 투수 위반; 한 베이스 안전진루; 타자 1루 도달 및 다른 모든 주자 최소 한 베이스 진루 시 플레이 계속 | [6.02(a) 본문·벌칙](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 실행 완료 |
| golden_knowledge_002 | 야구 지식 | 인필드 플라이는 어떤 조건에서 선언되고 공을 놓치면 어떻게 돼? | 무사 또는 1사; 1·2루 또는 만루; 쉽게 잡을 페어 플라이; 번트·직선타 제외; 타자 아웃·볼 인플레이 | [용어 40; 5.09(a)(5)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 실행 완료 |
| golden_knowledge_003 | 야구 지식 | 포스아웃이랑 태그아웃 차이가 뭐야? | 타자 출루로 점유권 상실; 포스 해제 후 신체 태그 필요 | [용어 30·75; 5.09(b)(6)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 실행 완료 |
| golden_knowledge_004 | 야구 지식 | 낫아웃이면 1루에 주자가 있어도 무조건 뛸 수 있어? | 1루 비어 있음 또는 2아웃; 무사·1사 1루주자 존재 시 자동 아웃 | [5.05(a)(2); 5.09(a)(3)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 실행 완료 |
| golden_knowledge_005 | 야구 지식 | 1루 지나 외야 페어 지역에 떨어진 공이 파울로 굴러가면 파울이야? | 외야 최초 낙하지점 기준; 이후 파울로 굴러도 페어 | [용어 25 FAIR BALL](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 실행 완료 |
| golden_knowledge_006 | 야구 지식 | 3루 주자가 먼저 홈 밟았는데 마지막 아웃이 포스아웃이면 점수야? | 제3아웃 포스아웃은 득점 불인정 | [5.08(a) 부기 (2)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 실행 완료 |
| golden_knowledge_007 | 야구 지식 | 투스트라이크에서 번트가 파울이면 계속 치는 거야? | 2스트라이크 번트 파울은 삼진; 포구된 번트 파울 플라이는 플라이 아웃 | [5.09(a)(4); 9.15(a)(4) 예외; 용어72](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 실행 완료 |
| golden_knowledge_008 | 야구 지식 | 볼 데드 때는 주자가 마음대로 한 베이스씩 가도 돼? | 플레이 일시정지; 규칙상 허용 진루 구분 | [용어20; 5.06(c)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 실행 완료 |
| golden_knowledge_009 | 야구 지식 | 몸에 맞으면 공이 스트라이크 존 안이어도 무조건 1루야? | 스트라이크 존 접촉은 스트라이크; 자동 1루 아님 | [5.05(b)(2)(A)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 실행 완료 |
| golden_knowledge_010 | 야구 지식 | 2026 KBO 피치클락 투수랑 타자 위반하면 각각 어떻게 돼? | 투·포수 위반 볼; 타자 위반 스트라이크; 2026 KBO리그 기준 | [2026 피치클락 > 변경 사항](https://www.koreabaseball.com/Kbo/League/GameManage2026.aspx) | 실행 완료 |
| golden_knowledge_011 | 야구 지식 | ABS가 체크스윙까지 자동으로 판정하는 거야? | 투구 위치 기반 볼·스트라이크; 체크스윙 별도 판단 | [ABS 운영 방식; 체크스윙 판독](https://www.koreabaseball.com/Kbo/League/GameManage2026.aspx) | 실행 완료 |
| golden_knowledge_012 | 야구 지식 | 폭투랑 포일은 어떻게 달라? | 보통 수비로 처리 가능 여부; 주자 진루; 폭투·포일 구분 | [9.13(a)(b)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 실행 완료 |
| golden_knowledge_013 | 야구 지식 | 희생플라이는 잡혀야만 기록돼? 놓쳐도 점수 나면 가능한가? | 무사 또는 1사; 주자 득점; 미포구 시 기록원 판단 | [9.08(e)(1)(2)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 실행 완료 |
| golden_knowledge_014 | 야구 지식 | 주자 2루만 있을 때 볼넷이면 그 주자도 3루로 가? | 타자 1루; 2루 단독 주자 강제 진루 아님 | [5.05(b)(1)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 실행 완료 |
| golden_knowledge_015 | 야구 지식 | 2026 KBO 체크스윙 판독은 일반 판독 기회를 써? 번트도 신청돼? | 일반 판독과 별도 2회; 번트 시도 제외; 연장 1회 추가·번복 시 유지 | [체크스윙 비디오 판독 시행 세칙](https://www.koreabaseball.com/Kbo/League/GameManage2026.aspx) | 실행 완료 |
| golden_mixed_001 | 복합·후속 질문 | 사직 처음 가는데 지하철이랑 가져가면 안 되는 가방 알려줘 | 부산 3호선 사직역·종합운동장역; 1인 가방 1개 45×45×20cm; 쇼핑백 1개 30×50×12cm | [오시는 길 > 지하철; SAFE 가방 크기·개수](https://www.giantsclub.com/html/?pcode=207); [오시는 길 > 지하철; SAFE 가방 크기·개수](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 실행 완료 |
| golden_mixed_002 | 복합·후속 질문 | 그럼 거기 경기 표는 어디서 사? | 창원NC파크·NC 문맥 유지; ticket.ncdinos.com | [예매처 > NC](https://www.koreabaseball.com/kbo/league/map.aspx); golden_mixed_002.input 문맥·선호팀 | 실행 완료 |
| golden_mixed_003 | 복합·후속 질문 | 그 경기 몇 시에 시작해? | 선택 경기 18:30; Tool 재호출 없이 context 사용 | selected_game_time 분기; selected_game.start_time | 실행 완료 |
| golden_mixed_004 | 복합·후속 질문 | 아니 이번엔 고척이야. 내부 주차는 가능해? | 사직에서 고척으로 조건 전환; 고척 프로야구 내부 주차 불가 | [내부 주차장 안내](https://heroesbaseball.co.kr/ticket/normal/viewPurchase.do); golden_mixed_004.input 문맥·선호팀 | 실행 완료 |
| golden_mixed_005 | 복합·후속 질문 | 두산 잠실이랑 KT 수원 홈경기 예매처가 같은지 비교해줘 | 두산 NOL 티켓; KT 티켓링크; 홈팀별 경로 구분 | [예매처 > 두산·KT](https://www.koreabaseball.com/kbo/league/map.aspx) | 실행 완료 |
| golden_scope_001 | 근거 부족·범위 밖 | 오늘 고척 1루 쪽 표 몇 장 남았어? | 실시간 잔여석 조회 미지원 안내; 공식 예매처 확인 안내 | find_kbo_game 미지원 > ticket_inventory_tool_required | 실행 완료 |
| golden_scope_002 | 근거 부족·범위 밖 | 우리 팀 홈경기 취소 수수료 얼마야? | 선호 팀·선택 경기 없으면 구단 확인 질문 | search_ticketing_guide > 팀·구장 필수 입력 | 실행 완료 |
| golden_scope_003 | 근거 부족·범위 밖 | 사직에 유모차 맡기는 곳 위치 정확히 알려줘 | 구체적 위치 근거 없으면 확인 필요 안내; 공식 구단 문의 경로 안내 | [보존 구장샵 원문에는 유모차 보관 위치 근거 없음](https://www.giantsclub.com/html/?pcode=367) | 실행 완료 |
| golden_scope_004 | 근거 부족·범위 밖 | 고척돔 콘서트도 야구 때처럼 음식물 들고 들어가면 돼? | 행사별 음식물 제한 가능; 공연 주최 측 공지 확인 | [음식물 FAQ > 행사 성격에 따른 제한](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp) | 실행 완료 |
| golden_scope_005 | 근거 부족·범위 밖 | 야구 말고 내일 살 주식 하나 추천해줘 | 야구 서비스 범위 밖 안내 | 야구 범위 제한 | 실행 완료 |
