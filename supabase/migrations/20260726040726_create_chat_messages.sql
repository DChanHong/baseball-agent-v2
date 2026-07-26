create table public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null
    references public.chat_conversations(id) on delete cascade,
  user_id uuid null
    references auth.users(id) on delete set null,
  role varchar(20) not null,
  content text not null,
  content_type varchar(20) not null default 'markdown',
  sequence_no integer not null,
  status varchar(20) not null default 'completed',
  parent_message_id uuid null
    references public.chat_messages(id) on delete set null,
  model_name varchar(100) null,
  prompt_tokens integer null,
  completion_tokens integer null,
  total_tokens integer null,
  latency_ms integer null,
  error_code varchar(100) null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint chat_messages_conversation_sequence_key
    unique (conversation_id, sequence_no),
  constraint chat_messages_role_check
    check (role in ('user', 'assistant', 'system', 'tool')),
  constraint chat_messages_content_type_check
    check (content_type in ('text', 'markdown', 'json', 'image', 'file')),
  constraint chat_messages_sequence_no_check
    check (sequence_no > 0),
  constraint chat_messages_status_check
    check (status in ('pending', 'streaming', 'completed', 'failed', 'cancelled')),
  constraint chat_messages_prompt_tokens_check
    check (prompt_tokens is null or prompt_tokens >= 0),
  constraint chat_messages_completion_tokens_check
    check (completion_tokens is null or completion_tokens >= 0),
  constraint chat_messages_total_tokens_check
    check (total_tokens is null or total_tokens >= 0),
  constraint chat_messages_latency_ms_check
    check (latency_ms is null or latency_ms >= 0),
  constraint chat_messages_metadata_object_check
    check (jsonb_typeof(metadata) = 'object')
);

comment on table public.chat_messages is
  'Stores ordered user, assistant, system, and tool messages in a conversation.';

comment on column public.chat_messages.sequence_no is
  'One-based message order unique within a conversation.';

comment on column public.chat_messages.parent_message_id is
  'Optional source message for regenerated or branched responses.';

alter table public.chat_messages enable row level security;
