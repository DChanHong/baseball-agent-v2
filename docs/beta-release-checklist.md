# Beta Release Checklist

> 지금까지 구현한 상태로 베타 오픈과 배포를 진행하기 위한 정비 체크리스트.
> 각 항목은 인터뷰하면서 하나씩 결정/처리한다.

## Database

- [x] 운영 DB에 migration 적용 절차 정리
- [x] 로컬 DB의 `rag_documents`, `rag_chunks`를 재임베딩 없이 운영 DB로 dump/restore
- [x] 로컬 DB의 `kbo_games` 운영 DB 이관
- [x] 운영 DB 기본 seed 데이터 확인: `kbo_teams`, `kbo_stadiums`
- [x] 운영 DB 이관 후 row count 검증

### 운영 DB migration 적용 절차

원칙:

- Supabase schema의 기준은 `supabase/migrations/*.sql`이다.
- 운영 DB schema는 Supabase Dashboard에서 직접 수정하지 않는다.
- 운영 DB에는 개발용 전체 seed를 자동 적용하지 않는다.
- `db reset`은 운영 DB에서 사용하지 않는다.
- 실제 원격 DB 변경 전에는 사용자 확인을 받고 진행한다.

적용 대상 migration:

1. `supabase/migrations/20260726040522_create_chat_conversations.sql`
2. `supabase/migrations/20260726040726_create_chat_messages.sql`
3. `supabase/migrations/20260726041011_create_chat_indexes.sql`
4. `supabase/migrations/20260727165538_create_kbo_schedule_tables.sql`
5. `supabase/migrations/20260729120000_expand_kbo_team_stadium_profiles.sql`
6. `supabase/migrations/20260730043500_enable_vector_extension.sql`
7. `supabase/migrations/20260730044000_create_rag_document_chunk_tables.sql`
8. `supabase/migrations/20260811090000_add_auth_user_profiles.sql`

권장 절차:

1. 운영 Supabase project ref와 운영 DB 접속 정보를 확인한다.
2. Supabase CLI 로그인 및 project link 상태를 확인한다.
3. 운영 반영 전 dry-run으로 적용될 migration을 확인한다.
4. dry-run 결과에 위 8개 migration만 포함되는지 확인한다.
5. 사용자 확인 후 운영 DB에 migration을 적용한다.
6. migration 적용 후 주요 table, extension, index 존재를 확인한다.
7. 기본 seed 대상인 `kbo_teams`, `kbo_stadiums`는 별도 단계에서 확인/적용한다.
8. `rag_documents`, `rag_chunks`, `kbo_games` 운영 데이터는 migration 이후 별도 dump/restore 단계에서 이관한다.

명령 후보:

```bash
supabase link --project-ref <production-project-ref>
supabase db push --dry-run
supabase db push
```

확인 쿼리 후보:

```sql
select extname from pg_extension where extname = 'vector';

select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'chat_conversations',
    'chat_messages',
    'kbo_teams',
    'kbo_stadiums',
    'kbo_games',
    'kbo_game_status_history',
    'rag_documents',
    'rag_chunks',
    'user_profiles'
  )
order by table_name;
```

## Frontend

- [x] 출처 패널 제거: 클라이언트 호출부 주석 처리로 비활성화
- [x] tool card 내부 출처 링크는 유지
- [x] 하단 채팅 입력창을 fixed floating composer로 변경
- [x] 채팅 입력창을 textarea 기준으로 정리
- [x] fixed composer에 맞춰 메시지 영역 하단 여백 조정

## Environment

- [ ] 운영 backend env 정리
- [ ] 운영 frontend env 정리
- [ ] 서브도메인 기준 CORS 설정 정리
- [ ] Google OAuth redirect URL 운영 도메인으로 추가
- [ ] Supabase Auth redirect URL 운영 도메인으로 추가
- [ ] `APP_DEBUG=false` 적용
- [ ] `API_RESPONSE_LOGGING_ENABLED=false` 적용
- [ ] `AUTH_COOKIE_SECURE=true` 적용

## Quality Gates

- [ ] 백엔드 ruff lint 실패 항목 정리
- [x] 프론트 build 재검증
- [ ] 백엔드 test 재검증

## Production Smoke Test

- [ ] 배포 후 `/health` 확인
- [ ] 배포 후 `/health/db` 확인
- [ ] 운영 로그인 플로우 확인
- [ ] 운영 채팅 1회 end-to-end 확인
- [ ] 운영 DB 이관 후 RAG 검색 smoke test
- [ ] 운영 일정 질문 smoke test
- [ ] 운영 구장 가이드 질문 smoke test
- [ ] 운영 야구 규칙 질문 smoke test
- [ ] 운영 날씨 질문 smoke test
