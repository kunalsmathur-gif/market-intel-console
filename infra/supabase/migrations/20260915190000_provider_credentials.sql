-- Provider credentials: a token the owner pastes into the web app's Settings page (e.g.
-- Upstox's daily access token — PRD §8.5 broker connect, §9.3 daily login) instead of an
-- environment variable that would need a redeploy every trading day.
--
-- The worker connects to Postgres directly and bypasses RLS (see the header of the init
-- migration), so it can read a secret only the owner is allowed to write. Like outbox,
-- raw_responses and allowed_users, this table has RLS enabled with zero policies: nothing
-- reaches it through PostgREST directly. The owner writes and reads status only through the
-- two security-definer functions below, which check is_owner() themselves; the raw token is
-- never selectable, so it can never be sent back to the browser.

create table public.provider_credentials (
  provider text primary key check (provider ~ '^[a-z0-9][a-z0-9_-]*$'),
  access_token text not null,
  expires_at timestamptz not null,
  updated_at timestamptz not null default now(),
  updated_by uuid not null references auth.users (id)
);

alter table public.provider_credentials enable row level security;

-- Owner-only upsert; the access token never round-trips back out of this function.
create function public.set_provider_credential(
  p_provider text, p_access_token text, p_expires_at timestamptz
) returns void
language plpgsql security definer set search_path = ''
as $$
begin
  if not public.is_owner() then
    raise exception using errcode = '42501', message = 'only the owner may set provider credentials';
  end if;
  insert into public.provider_credentials (provider, access_token, expires_at, updated_at, updated_by)
  values (p_provider, p_access_token, p_expires_at, now(), auth.uid())
  on conflict (provider) do update
    set access_token = excluded.access_token,
        expires_at = excluded.expires_at,
        updated_at = excluded.updated_at,
        updated_by = excluded.updated_by;
end;
$$;

-- Status only, never the token itself.
create function public.provider_credential_status(p_provider text)
returns table (expires_at timestamptz, updated_at timestamptz)
language sql stable security definer set search_path = ''
as $$
  select expires_at, updated_at
  from public.provider_credentials
  where provider = p_provider and (select public.is_owner())
$$;

