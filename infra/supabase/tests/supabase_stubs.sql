-- Minimal stand-ins for the parts of Supabase the migrations use, so they apply to plain Postgres.
-- Safe to run more than once: roles are cluster-wide and may already exist.

do $$
begin
  create role anon nologin;
exception when duplicate_object then null;
end $$;

do $$
begin
  create role authenticated nologin;
exception when duplicate_object then null;
end $$;

create schema if not exists auth;
create table if not exists auth.users (id uuid primary key, email text);

-- Supabase reads the caller's JWT claims from this setting; tests set it with set_config().
create or replace function auth.jwt() returns jsonb language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claims', true), ''), '{}')::jsonb
$$;
create or replace function auth.uid() returns uuid language sql stable as $$
  select nullif(auth.jwt() ->> 'sub', '')::uuid
$$;
grant usage on schema auth to anon, authenticated;

create schema if not exists storage;
create table if not exists storage.buckets (id text primary key, name text, public boolean);
create table if not exists storage.objects (id bigserial primary key, bucket_id text, name text);
alter table storage.objects enable row level security;

grant usage on schema public, storage to anon, authenticated;
-- Supabase grants table access to its API roles and relies on RLS to restrict rows.
alter default privileges in schema public grant all on tables to anon, authenticated;
alter default privileges in schema public grant all on sequences to anon, authenticated;
