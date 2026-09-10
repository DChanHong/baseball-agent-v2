alter table public.rag_documents
  add column logical_document_id text null,
  add column revision_number integer null,
  add column is_active boolean not null default true,
  add column activated_at timestamptz not null default now(),
  add column deactivated_at timestamptz null,
  add column legacy_unreviewed boolean not null default false;

with ranked_stadium_documents as (
  select
    document_id,
    regexp_replace(document_id, '_[0-9]{8}$', '') as logical_document_id,
    row_number() over (
      partition by regexp_replace(document_id, '_[0-9]{8}$', '')
      order by as_of, created_at, document_id
    )::integer as revision_number,
    row_number() over (
      partition by regexp_replace(document_id, '_[0-9]{8}$', '')
      order by as_of desc, updated_at desc, document_id desc
    )::integer as current_rank
  from public.rag_documents
  where document_type in (
    'stadium_bag_policy',
    'stadium_facility_guide',
    'stadium_seat_guide',
    'stadium_ticketing_guide',
    'stadium_transport_guide',
    'stadium_food_guide',
    'stadium_entry_guide',
    'stadium_accessibility_guide'
  )
)
update public.rag_documents as documents
set
  logical_document_id = ranked.logical_document_id,
  revision_number = ranked.revision_number,
  is_active = ranked.current_rank = 1,
  activated_at = coalesce(documents.updated_at, documents.created_at, now()),
  deactivated_at = case
    when ranked.current_rank = 1 then null
    else coalesce(documents.updated_at, documents.created_at, now())
  end,
  legacy_unreviewed = true
from ranked_stadium_documents as ranked
where documents.document_id = ranked.document_id;

alter table public.rag_documents
  add constraint rag_documents_logical_document_id_not_blank_check
    check (
      logical_document_id is null
      or length(btrim(logical_document_id)) > 0
    ),
  add constraint rag_documents_revision_number_positive_check
    check (revision_number is null or revision_number > 0),
  add constraint rag_documents_revision_identity_check
    check (
      (logical_document_id is null and revision_number is null)
      or (logical_document_id is not null and revision_number is not null)
    ),
  add constraint rag_documents_activation_window_check
    check (
      (is_active and deactivated_at is null)
      or (not is_active and deactivated_at is not null)
    );

create unique index rag_documents_logical_revision_unique_idx
  on public.rag_documents (logical_document_id, revision_number)
  where logical_document_id is not null;

create unique index rag_documents_one_active_revision_idx
  on public.rag_documents (logical_document_id)
  where is_active and logical_document_id is not null;

create index rag_documents_active_stadium_type_idx
  on public.rag_documents (stadium_id, document_type)
  where is_active;

comment on column public.rag_documents.logical_document_id is
  'Stable identity shared by every revision of one RAG document.';

comment on column public.rag_documents.revision_number is
  'Monotonic revision number within one logical RAG document.';

comment on column public.rag_documents.is_active is
  'Whether this revision is currently eligible for retrieval.';

comment on column public.rag_documents.legacy_unreviewed is
  'Allows pre-pipeline stadium guide data to remain searchable until reviewed replacements are promoted.';

create table public.stadium_guide_sync_runs (
  run_id text primary key,
  scope jsonb not null default '{}'::jsonb,
  status text not null,
  source_count integer not null default 0,
  create_count integer not null default 0,
  update_count integer not null default 0,
  unchanged_count integer not null default 0,
  delete_candidate_count integer not null default 0,
  manual_required_count integer not null default 0,
  failure_count integer not null default 0,
  started_at timestamptz not null default now(),
  finished_at timestamptz null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint stadium_guide_sync_runs_run_id_not_blank_check
    check (length(btrim(run_id)) > 0),
  constraint stadium_guide_sync_runs_status_check
    check (status in ('running', 'completed', 'completed_with_failures', 'failed')),
  constraint stadium_guide_sync_runs_counts_check
    check (
      source_count >= 0
      and create_count >= 0
      and update_count >= 0
      and unchanged_count >= 0
      and delete_candidate_count >= 0
      and manual_required_count >= 0
      and failure_count >= 0
    )
);

create table public.stadium_guide_source_checks (
  check_id uuid primary key default gen_random_uuid(),
  run_id text not null references public.stadium_guide_sync_runs(run_id) on delete cascade,
  source_id text not null,
  source_url text not null,
  result_status text not null,
  raw_content_hash text null,
  normalized_text_hash text null,
  raw_file_path text null,
  http_status integer null,
  collector_type text not null,
  parser_name text null,
  consecutive_missing_count integer not null default 0,
  collected_at timestamptz not null default now(),
  error_code text null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),

  constraint stadium_guide_source_checks_source_id_not_blank_check
    check (length(btrim(source_id)) > 0),
  constraint stadium_guide_source_checks_source_url_not_blank_check
    check (length(btrim(source_url)) > 0),
  constraint stadium_guide_source_checks_result_status_check
    check (
      result_status in (
        'collected',
        'unchanged',
        'content_missing',
        'manual_required',
        'collection_failed'
      )
    ),
  constraint stadium_guide_source_checks_missing_count_check
    check (consecutive_missing_count >= 0),
  constraint stadium_guide_source_checks_http_status_check
    check (http_status is null or http_status between 100 and 599),
  constraint stadium_guide_source_checks_run_source_unique
    unique (run_id, source_id)
);

create table public.stadium_guide_change_candidates (
  candidate_id text primary key,
  run_id text not null references public.stadium_guide_sync_runs(run_id) on delete cascade,
  logical_document_id text not null,
  operation text not null,
  previous_revision_id text null references public.rag_documents(document_id) on delete set null,
  candidate_revision_id text null,
  previous_content_hash text null,
  candidate_content_hash text null,
  candidate_payload jsonb not null default '{}'::jsonb,
  diff_summary jsonb not null default '{}'::jsonb,
  source_ids text[] not null default '{}',
  status text not null default 'pending',
  reviewed_at timestamptz null,
  review_note text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint stadium_guide_candidates_candidate_id_not_blank_check
    check (length(btrim(candidate_id)) > 0),
  constraint stadium_guide_candidates_logical_id_not_blank_check
    check (length(btrim(logical_document_id)) > 0),
  constraint stadium_guide_candidates_operation_check
    check (operation in ('CREATE', 'UPDATE', 'DELETE_CANDIDATE', 'RE_EMBED')),
  constraint stadium_guide_candidates_status_check
    check (
      status in (
        'pending',
        'approved',
        'rejected',
        'applied_local',
        'evaluation_failed',
        'ready_for_production',
        'promoted'
      )
    ),
  constraint stadium_guide_candidates_review_state_check
    check (
      (status = 'pending' and reviewed_at is null)
      or (status <> 'pending' and reviewed_at is not null)
    )
);

create unique index stadium_guide_candidates_open_content_unique_idx
  on public.stadium_guide_change_candidates (
    logical_document_id,
    operation,
    coalesce(candidate_content_hash, '')
  )
  where status in ('pending', 'approved', 'applied_local', 'ready_for_production');

create index stadium_guide_candidates_status_created_idx
  on public.stadium_guide_change_candidates (status, created_at);

create table public.stadium_guide_deployments (
  deployment_id uuid primary key default gen_random_uuid(),
  candidate_id text not null,
  revision_id text not null references public.rag_documents(document_id) on delete restrict,
  target text not null,
  action text not null,
  evaluation_run_id text null,
  previous_active_revision_id text null,
  status text not null,
  error_code text null,
  deployed_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),

  constraint stadium_guide_deployments_candidate_id_not_blank_check
    check (length(btrim(candidate_id)) > 0),
  constraint stadium_guide_deployments_target_check
    check (target in ('local', 'production')),
  constraint stadium_guide_deployments_action_check
    check (action in ('promote', 'rollback', 'deactivate')),
  constraint stadium_guide_deployments_status_check
    check (status in ('running', 'completed', 'failed')),
  constraint stadium_guide_deployments_idempotency_unique
    unique (candidate_id, revision_id, target, action)
);

create index stadium_guide_source_checks_source_collected_idx
  on public.stadium_guide_source_checks (source_id, collected_at desc);

create index stadium_guide_deployments_revision_deployed_idx
  on public.stadium_guide_deployments (revision_id, deployed_at desc);

alter table public.stadium_guide_sync_runs enable row level security;
alter table public.stadium_guide_source_checks enable row level security;
alter table public.stadium_guide_change_candidates enable row level security;
alter table public.stadium_guide_deployments enable row level security;

create trigger set_stadium_guide_sync_runs_updated_at
before update on public.stadium_guide_sync_runs
for each row
execute function public.set_updated_at();

create trigger set_stadium_guide_change_candidates_updated_at
before update on public.stadium_guide_change_candidates
for each row
execute function public.set_updated_at();

comment on table public.stadium_guide_sync_runs is
  'Tracks one manually started stadium guide collection and classification run.';

comment on table public.stadium_guide_source_checks is
  'Stores source collection outcomes while raw response bodies remain in repository snapshots.';

comment on table public.stadium_guide_change_candidates is
  'Stores document-level changes awaiting explicit human review in the local workflow database.';

comment on table public.stadium_guide_deployments is
  'Records local application, production promotion, and rollback outcomes for approved revisions.';
