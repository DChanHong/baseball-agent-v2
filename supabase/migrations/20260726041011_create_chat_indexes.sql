create index chat_conversations_user_last_message_idx
  on public.chat_conversations (user_id, last_message_at desc)
  where user_id is not null and deleted_at is null;

create index chat_conversations_guest_last_message_idx
  on public.chat_conversations (guest_id, last_message_at desc)
  where guest_id is not null and deleted_at is null;

create index chat_conversations_status_updated_at_idx
  on public.chat_conversations (status, updated_at desc)
  where deleted_at is null;

create index chat_messages_user_created_at_idx
  on public.chat_messages (user_id, created_at desc)
  where user_id is not null;

create index chat_messages_status_created_at_idx
  on public.chat_messages (status, created_at);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger set_chat_conversations_updated_at
before update on public.chat_conversations
for each row
execute function public.set_updated_at();

create trigger set_chat_messages_updated_at
before update on public.chat_messages
for each row
execute function public.set_updated_at();
