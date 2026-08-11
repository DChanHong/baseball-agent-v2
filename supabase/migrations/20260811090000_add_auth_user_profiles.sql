create table public.user_profiles (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid not null unique
    references auth.users(id) on delete cascade,
  encrypted_email text null,
  nickname varchar(32) not null unique,
  favorite_team varchar(30) null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_login_at timestamptz null,

  constraint user_profiles_nickname_not_blank_check
    check (length(trim(nickname)) > 0),
  constraint user_profiles_favorite_team_check
    check (
      favorite_team is null
      or favorite_team in (
        'LG',
        'DOOSAN',
        'KIWOOM',
        'SSG',
        'KT',
        'KIA',
        'SAMSUNG',
        'LOTTE',
        'HANWHA',
        'NC'
      )
    )
);

comment on table public.user_profiles is
  'Stores application profile data for Supabase Auth users.';

comment on column public.user_profiles.auth_user_id is
  'Supabase Auth user id managed in auth.users.';

comment on column public.user_profiles.encrypted_email is
  'Optional encrypted email value. Plain email is not stored in app tables.';

comment on column public.user_profiles.nickname is
  'Random nickname assigned on first login and editable from my page.';

comment on column public.user_profiles.favorite_team is
  'Optional KBO favorite team selected by the user.';

alter table public.user_profiles enable row level security;

create index user_profiles_auth_user_id_idx
  on public.user_profiles (auth_user_id);

create index user_profiles_last_login_at_idx
  on public.user_profiles (last_login_at desc)
  where last_login_at is not null;

create trigger set_user_profiles_updated_at
before update on public.user_profiles
for each row
execute function public.set_updated_at();

alter table public.chat_conversations
  add column if not exists user_profile_id uuid null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'chat_conversations_user_profile_id_fkey'
  ) then
    alter table public.chat_conversations
      add constraint chat_conversations_user_profile_id_fkey
      foreign key (user_profile_id)
      references public.user_profiles(id)
      on delete set null;
  end if;
end;
$$;

comment on column public.chat_conversations.user_profile_id is
  'Application profile owner. Supersedes user_id after Auth migration.';

alter table public.chat_messages
  add column if not exists user_profile_id uuid null,
  add column if not exists deleted_at timestamptz null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'chat_messages_user_profile_id_fkey'
  ) then
    alter table public.chat_messages
      add constraint chat_messages_user_profile_id_fkey
      foreign key (user_profile_id)
      references public.user_profiles(id)
      on delete set null;
  end if;
end;
$$;

comment on column public.chat_messages.user_profile_id is
  'Application profile owner. Supersedes user_id after Auth migration.';

comment on column public.chat_messages.deleted_at is
  'NULL for visible messages, non-NULL after soft deletion.';

create index chat_conversations_user_profile_last_message_idx
  on public.chat_conversations (user_profile_id, last_message_at desc)
  where user_profile_id is not null and deleted_at is null;

create index chat_messages_user_profile_created_at_idx
  on public.chat_messages (user_profile_id, created_at desc)
  where user_profile_id is not null and deleted_at is null;

create index chat_messages_conversation_sequence_visible_idx
  on public.chat_messages (conversation_id, sequence_no)
  where deleted_at is null;
