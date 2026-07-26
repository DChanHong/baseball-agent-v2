create table public.chat_conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid null references auth.users(id) on delete set null,
  guest_id uuid null,
  title varchar(200) null,
  status varchar(20) not null default 'active',
  agent_type varchar(50) not null default 'baseball_general',
  summary text null,
  metadata jsonb not null default '{}'::jsonb,
  last_message_at timestamptz null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz null,

  constraint chat_conversations_status_check
    check (status in ('active', 'archived', 'deleted')),
  constraint chat_conversations_metadata_object_check
    check (jsonb_typeof(metadata) = 'object'),
  constraint chat_conversations_deleted_state_check
    check (
      (status = 'deleted' and deleted_at is not null)
      or
      (status <> 'deleted' and deleted_at is null)
    )
);

comment on table public.chat_conversations is
  'Stores chat conversation rooms for authenticated users or browser guests.';

comment on column public.chat_conversations.user_id is
  'Nullable owner reference. Linked to auth.users after login is introduced.';

comment on column public.chat_conversations.guest_id is
  'Browser-generated UUID used to identify a guest before login.';

comment on column public.chat_conversations.summary is
  'Condensed summary of older messages used as conversation context.';

alter table public.chat_conversations enable row level security;
