# Stadium Guide Collection Summary

> 작성일: 2026-07-29  
> 범위: `data/stadium_guide` 로컬 JSON/RAG 후보 데이터  
> 원칙: 공식 출처가 확인되고 raw snapshot 또는 신뢰 가능한 공식 페이지 근거가 있는 문서만 유지한다.

## 현재 상태

현재 유지 중인 normalized 문서는 9개 구장, 45개 문서다.

```text
SAJIK   5 docs
GOCHEOK 5 docs
MUNHAK  5 docs
GWANGJU 5 docs
DAEGU   5 docs
SUWON   5 docs
DAEJEON 5 docs
JAMSIL  5 docs
CHANGWON 5 docs
```

공통 공식 출처:

| source_id | 용도 |
|---|---|
| `kbo_safe_campaign` | 전 구장 공통 반입/보안 정책 기준 |
| `kbo_ticket_map` | KBO 공식 구단별 예매처 매핑 |

## 구장별 수집 요약

### SAJIK

홈팀: `LOTTE`

수집 문서:

| document_type | 상태 | 주요 출처 |
|---|---|---|
| `stadium_bag_policy` | 수집 | KBO SAFE 캠페인 |
| `stadium_facility_guide` | 수집 | 롯데 사직야구장 안내, 구장샵 안내 |
| `stadium_seat_guide` | 수집 | 롯데 사직야구장 안내, 좌석안내, 요금안내 |
| `stadium_ticketing_guide` | 수집 | KBO 티켓 안내, 롯데 예매/수령, 요금/할인 안내 |
| `stadium_transport_guide` | 수집 | 롯데 사직야구장 안내, 구장샵 안내 |

메모:

- 현재 가장 완성도가 높은 vertical slice다.
- 사직구장 전용 반입 예외, 화장실/수유실/흡연구역/의무실 위치는 추가 수집 후보로 남긴다.

### GOCHEOK

홈팀: `KIWOOM`

수집 문서:

| document_type | 상태 | 주요 출처 |
|---|---|---|
| `stadium_bag_policy` | 수집 | 키움 일반티켓 안내, KBO SAFE 캠페인 |
| `stadium_facility_guide` | 수집 | 서울시설공단 고척스카이돔 |
| `stadium_seat_guide` | 수집 | 키움 일반티켓 안내 |
| `stadium_ticketing_guide` | 수집 | 키움 일반티켓/일일티켓 안내, KBO 티켓 안내 |
| `stadium_transport_guide` | 수집 | 키움 티켓 안내, 서울시설공단 고척스카이돔 |

메모:

- 주차 제한과 대중교통 권장 안내가 공식 출처에 명확하다.
- 돔 구장 특성상 날씨/우천 관련 문서를 나중에 별도로 만들기 좋다.

### MUNHAK

홈팀: `SSG`

수집 문서:

| document_type | 상태 | 주요 출처 |
|---|---|---|
| `stadium_bag_policy` | 수집 | KBO SAFE 캠페인 |
| `stadium_facility_guide` | 수집 | SSG 홈구장 안내 |
| `stadium_seat_guide` | 수집 | SSG 홈구장 안내, 단체관람 안내 |
| `stadium_ticketing_guide` | 수집 | SSG 단체관람 안내, 2026 티켓 예매 공지, KBO 티켓 안내 |
| `stadium_transport_guide` | 수집 | SSG 홈구장 안내, SSG 주차안내 |

메모:

- SSG 공식 홈구장 안내가 좌석, 매점, 화장실, GATE 정보를 제공한다.
- SSG 공식 홈구장 안내에서 오시는 길을 확인했고, 별도 공식 주차안내 페이지에서 주차장 형태, 요금, 총 주차대수를 보강했다.

### GWANGJU

홈팀: `KIA`

수집 문서:

| document_type | 상태 | 주요 출처 |
|---|---|---|
| `stadium_facility_guide` | 수집 | KIA 챔피언스필드 안내 |
| `stadium_ticketing_guide` | 수집 | KIA 입장권, 스마트티켓 공지, KBO 티켓 안내 |
| `stadium_transport_guide` | 수집 | KIA 챔피언스필드 안내 |
| `stadium_bag_policy` | 수집 | KBO SAFE 캠페인 |
| `stadium_seat_guide` | 수집 | KIA 챔피언스필드 안내, KIA 입장권 |

메모:

- 구장 안내와 교통 안내는 공식 출처가 좋다.
- 반입/안전 정책은 KBO SAFE 공통 기준으로 보강했으며, KIA 전용 예외는 추가 공식 출처 확인이 필요하다.
- 좌석 문서는 관람석 수와 공식 입장권 페이지 존재를 최소 근거로 만들었다. 좌석/요금 상세는 이미지 중심이라 추가 수동 검수가 필요하다.

### DAEGU

홈팀: `SAMSUNG`

수집 문서:

| document_type | 상태 | 주요 출처 |
|---|---|---|
| `stadium_seat_guide` | 수집 | 삼성 입장권 종류 |
| `stadium_ticketing_guide` | 수집 | 삼성 입장권 종류, 예매방법, 예매취소/환불, KBO 티켓 안내 |
| `stadium_bag_policy` | 수집 | KBO SAFE 캠페인 |
| `stadium_facility_guide` | 수집 | 삼성 2025 홈 개막전 라팍 시설 보강 공지 |
| `stadium_transport_guide` | 수집 | 삼성 공식 페이지 주소, 대구시 두드리소 대공원역 교통 답변 |

메모:

- 좌석/티켓/환불 정보는 공식 출처가 충분하다.
- 반입/안전 정책은 KBO SAFE 공통 기준으로 보강했으며, 삼성 라이온즈 파크 전용 예외는 추가 공식 출처 확인이 필요하다.
- 시설 문서는 공식 공지의 캠핑존, SKY 요기보 패밀리석, 파티플로어석, 식음 매장, 포토존 보강 내용을 기준으로 만들었다.
- 교통 문서는 대공원역과 도시철도 특별교통대책 근거만 최소 반영했다. 버스 노선, 출구 번호, 주차 가능 대수와 요금은 추가 공식 출처 확인이 필요하다.

### SUWON

홈팀: `KT`

수집 문서:

| document_type | 상태 | 주요 출처 |
|---|---|---|
| `stadium_facility_guide` | 수집 | kt wiz park 구장 소개, 구장 안내도 |
| `stadium_seat_guide` | 수집 | kt wiz park 구장 안내도, 2026 티켓정책 |
| `stadium_ticketing_guide` | 수집 | kt 일반티켓 예매, 2026 티켓정책, KBO 티켓 안내 |
| `stadium_transport_guide` | 수집 | kt wiz park 구장 소개, 주차예약 안내 |
| `stadium_bag_policy` | 수집 | KBO SAFE 캠페인 |

메모:

- 사전 주차 예약제가 공식 출처에 명확히 안내되어 있어 transport 문서 품질이 좋다.
- 구장 안내도와 티켓정책은 이미지 중심일 수 있어 좌석/요금 세부 구조화는 추가 검수 대상이다.
- 반입/안전 정책은 KBO SAFE 공통 기준으로 보강했으며, KT 위즈파크 전용 예외는 추가 공식 출처 확인이 필요하다.

### DAEJEON

홈팀: `HANWHA`

수집 문서:

| document_type | 상태 | 주요 출처 |
|---|---|---|
| `stadium_bag_policy` | 수집 | KBO SAFE 캠페인 |
| `stadium_facility_guide` | 수집 | 한화 공식 대전 한화생명 볼파크 안내, VISITKOREA 공식 관광정보 |
| `stadium_seat_guide` | 수집 | 한화 공식 대전 한화생명 볼파크 안내, 한화 티켓 안내 |
| `stadium_ticketing_guide` | 수집 | 한화 티켓 안내, KBO 티켓 안내 |
| `stadium_transport_guide` | 수집 | 한화 공식 대전 한화생명 볼파크 안내, VISITKOREA 공식 관광정보 |

메모:

- 한화 공식 페이지는 브라우저 기준으로 좌석, 시설, 주소, 대표 전화 정보를 확인했다.
- 한화 공식 페이지 raw fetch는 일부 `{}`
  또는 `{"user":null}` 수준으로만 저장되어, raw snapshot 단독 재현성은 약하다.
- 티켓/좌석 세부는 이미지와 동적 렌더링 중심이라 추가 수동 검수가 필요하다.
- 교통 문서는 주소와 주차 가능 여부까지만 최소 반영했다. 버스, 지하철, 주차 가능 대수, 요금은 추가 공식 출처 확인이 필요하다.

### JAMSIL

홈팀: `LG`, `DOOSAN`

수집 문서:

| document_type | 상태 | 주요 출처 |
|---|---|---|
| `stadium_bag_policy` | 수집 | KBO SAFE 캠페인, LG 트윈스 티켓 안내 |
| `stadium_facility_guide` | 수집 | 서울시 잠실야구장 시설현황, 서울시 주차 안내 |
| `stadium_seat_guide` | 수집 | 서울시 잠실야구장 시설현황, LG 트윈스 티켓 안내, NOL 두산베어스 |
| `stadium_ticketing_guide` | 수집 | LG 트윈스 티켓 안내, NOL 두산베어스, KBO 티켓 안내 |
| `stadium_transport_guide` | 수집 | 서울시 잠실야구장 시설현황, 서울시 주차 안내 |

메모:

- 잠실은 LG와 두산이 함께 쓰는 구장이라 티켓/좌석/응원석 답변은 홈팀 확인이 필수다.
- 서울시 공식 출처에서 좌석 수, 수용인원, 주차규모, 주차요금 정보를 확보했다.
- LG 공식 티켓 안내는 좌석 등급, 예매 기간, 예매 수수료, 예매 한도, 취소 조건, 일부 반입 유의사항이 텍스트로 확보되어 품질이 좋다.
- 두산은 NOL 스포츠 두산베어스 예매 페이지에서 잠실야구장 경기/예매 데이터를 확보했지만, 좌석/요금 상세는 동적 페이지 또는 이미지 검수가 더 필요하다.

### CHANGWON

홈팀: `NC`

수집 문서:

| document_type | 상태 | 주요 출처 |
|---|---|---|
| `stadium_bag_policy` | 수집 | KBO SAFE 캠페인, 창원시 재개장 안전점검 보도자료, NC 공식 공지 |
| `stadium_facility_guide` | 수집 | 창원관광 창원NC파크, 창원시 재개장 안전점검 보도자료, NC 공식 공지 |
| `stadium_seat_guide` | 수집 | 창원관광 창원NC파크, NC DINOS 공식 앱 |
| `stadium_ticketing_guide` | 수집 | NC DINOS 공식 앱, KBO 티켓 안내 |
| `stadium_transport_guide` | 수집 | 창원관광 창원NC파크, NC 공식 공지, 창원시 재개장 안전점검 보도자료 |

메모:

- 창원관광 공식 페이지에서 주소, 편의시설, 주차장 1,240면, 약 2만 명 수용, 일반석/프리미엄석/스카이박스 등 큰 범주 정보를 확인했다.
- NC 공식 앱 페이지에서 다이나믹 프라이싱 기반 자체 티켓 시스템, 스마트 티켓, 예매/발권/입장 기능을 확인했다.
- 창원시 공식 보도자료와 NC 공식 공지를 통해 2025년 안전점검/재개장 맥락을 함께 남겼다.
- 창원관광 raw HTML은 API 호출 구조라 상세 본문 단독 재현성이 약하다.
- 좌석 구역명, 좌석별 가격, 응원석/원정석, 버스/셔틀/주차요금은 추가 공식 검수가 필요하다.

## 아직 수집하지 못했거나 제외한 구장

현재 정규 홈구장 기준 초기 수집 대상은 모두 normalized 문서로 생성했다.

## 수집 대상 제외

### POHANG

홈팀: `SAMSUNG` 보조 구장

제외 이유:

- 정규 홈구장 중심 RAG 초기 수집 범위에서 보조 구장은 제외한다.
- 삼성 공식 티켓 페이지에 포항경기 요금표는 있으나, 포항야구장 자체 시설/교통/주차 공식 출처가 부족하다.
- 보조 구장이라 경기 편성 시점의 삼성 공지가 중요하다.

향후 검토 조건:

- 포항시 또는 포항시시설관리공단 포항야구장 전용 시설 안내
- 삼성 라이온즈 포항경기 운영 공지
- 포항경기 교통/주차/입장 안내

## 다음 작업 후보

1. 남긴 45개 normalized 문서를 RAG chunk 입력 포맷으로 변환한다.
2. 문서 schema를 정의한다.
3. `review_status`를 `needs_review`에서 `approved`로 바꾸는 검수 기준을 만든다.
4. 좌석/요금/게이트/교통처럼 구장별로 부족한 항목은 공식 출처를 추가 확보해 보강한다.
5. 블로그/커뮤니티 기반 초행자 팁은 별도 `curated` 문서로 분리하고, 공식 출처 기반 한계를 명시한다.
