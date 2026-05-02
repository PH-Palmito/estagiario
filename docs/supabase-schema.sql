create table if not exists public.axel_memory_states (
  key text primary key,
  category text not null default 'state',
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.axel_memory_states enable row level security;

drop policy if exists "axel_memory_states_select_anon" on public.axel_memory_states;
create policy "axel_memory_states_select_anon"
on public.axel_memory_states
for select
to anon
using (true);

drop policy if exists "axel_memory_states_insert_anon" on public.axel_memory_states;
create policy "axel_memory_states_insert_anon"
on public.axel_memory_states
for insert
to anon
with check (true);

drop policy if exists "axel_memory_states_update_anon" on public.axel_memory_states;
create policy "axel_memory_states_update_anon"
on public.axel_memory_states
for update
to anon
using (true)
with check (true);
