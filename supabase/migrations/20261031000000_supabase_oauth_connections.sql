-- Supabase OAuth connections for XYOCK users.
-- Tokens are encrypted by the Edge Function and never exposed to browser clients.
create table if not exists public.supabase_oauth_states (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  state_hash text not null unique,
  code_verifier text not null,
  return_to text not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);

create index if not exists supabase_oauth_states_expires_at_idx
  on public.supabase_oauth_states (expires_at);

create table if not exists public.supabase_oauth_connections (
  user_id uuid primary key references auth.users(id) on delete cascade,
  access_token_ciphertext text not null,
  refresh_token_ciphertext text not null,
  token_expires_at timestamptz not null,
  scope text,
  connected_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.supabase_oauth_states enable row level security;
alter table public.supabase_oauth_connections enable row level security;

-- Intentionally no client policies: only the authenticated Edge Function service role accesses these tables.
