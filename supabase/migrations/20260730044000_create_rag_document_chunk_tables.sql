create table public.rag_documents (
  document_id text primary key,
  document_type text not null,
  stadium_id text null references public.kbo_stadiums(id) on delete cascade,
  team_id text null references public.kbo_teams(id) on delete set null,
  title text not null,
  as_of date not null,
  trust_level text not null,
  review_status text not null,
  source_ids text[] not null default '{}',
  source_urls text[] not null default '{}',
  content_hash text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint rag_documents_document_id_not_blank_check
    check (length(btrim(document_id)) > 0),
  constraint rag_documents_document_type_not_blank_check
    check (length(btrim(document_type)) > 0),
  constraint rag_documents_title_not_blank_check
    check (length(btrim(title)) > 0),
  constraint rag_documents_trust_level_check
    check (trust_level in ('official', 'verified', 'curated')),
  constraint rag_documents_review_status_check
    check (review_status in ('needs_review', 'approved', 'rejected'))
);

comment on table public.rag_documents is
  'Stores normalized source documents used to produce RAG chunks.';

comment on column public.rag_documents.source_ids is
  'Source registry identifiers from data/stadium_guide/sources.json.';

comment on column public.rag_documents.source_urls is
  'Resolved source URLs used for citation display and provenance.';

create table public.rag_chunks (
  chunk_id text primary key,
  document_id text not null references public.rag_documents(document_id) on delete cascade,
  chunk_index integer not null,
  stadium_id text null references public.kbo_stadiums(id) on delete cascade,
  team_id text null references public.kbo_teams(id) on delete set null,
  document_type text not null,
  title text not null,
  chunk_text text not null,
  content text not null,
  embedding extensions.vector(1536) null,
  embedding_model text not null,
  embedding_dimensions integer not null,
  as_of date not null,
  trust_level text not null,
  review_status text not null,
  source_ids text[] not null default '{}',
  source_urls text[] not null default '{}',
  content_hash text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint rag_chunks_chunk_id_not_blank_check
    check (length(btrim(chunk_id)) > 0),
  constraint rag_chunks_chunk_index_check
    check (chunk_index >= 0),
  constraint rag_chunks_document_type_not_blank_check
    check (length(btrim(document_type)) > 0),
  constraint rag_chunks_title_not_blank_check
    check (length(btrim(title)) > 0),
  constraint rag_chunks_chunk_text_not_blank_check
    check (length(btrim(chunk_text)) > 0),
  constraint rag_chunks_embedding_dimensions_check
    check (embedding_dimensions = 1536),
  constraint rag_chunks_trust_level_check
    check (trust_level in ('official', 'verified', 'curated')),
  constraint rag_chunks_review_status_check
    check (review_status in ('needs_review', 'approved', 'rejected')),
  constraint rag_chunks_document_chunk_index_key
    unique (document_id, chunk_index)
);

comment on table public.rag_chunks is
  'Stores searchable RAG chunks and their pgvector embeddings.';

comment on column public.rag_chunks.chunk_text is
  'Text sent to the embedding model. It can include title and metadata context.';

comment on column public.rag_chunks.content is
  'Normalized source content used as answer evidence.';

create index rag_documents_stadium_type_idx
  on public.rag_documents (stadium_id, document_type);

create index rag_documents_review_status_idx
  on public.rag_documents (review_status);

create index rag_chunks_stadium_type_review_idx
  on public.rag_chunks (stadium_id, document_type, review_status);

create index rag_chunks_team_idx
  on public.rag_chunks (team_id)
  where team_id is not null;

alter table public.rag_documents enable row level security;
alter table public.rag_chunks enable row level security;

create trigger set_rag_documents_updated_at
before update on public.rag_documents
for each row
execute function public.set_updated_at();
create trigger set_rag_chunks_updated_at
before update on public.rag_chunks
for each row
execute function public.set_updated_at();
