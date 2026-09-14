-- Citebell V0 schema (PRD §8.5 sign-in, §8.7 alerts, §8.8 storage, §8.11 runs).
--
-- Facts, claims, evidence and corrections are append-only: a change is a new row, never an edit.
-- The worker connects as the table owner and bypasses RLS. The web app signs in with Supabase
-- Auth and can only read, plus flag claims, and only if the email is on the owner allowlist.

-- ---------------------------------------------------------------------------
-- Types (mirrors packages/schemas/src/citebell_schemas/enums.py)
-- ---------------------------------------------------------------------------
create type public.report_type as enum ('morning', 'midday', 'eod', 'flows');
create type public.source_tier as enum ('T1', 'T2', 'T3', 'TX');
create type public.source_kind as enum ('rss', 'api', 'search', 'manual');
create type public.evidence_kind as enum ('feed', 'article');
create type public.claim_type as enum ('market_number', 'news_event', 'forecast', 'opinion');
create type public.badge as enum (
  'primary_data', 'news_reported', 'verified', 'attributed_view', 'single_source', 'withheld'
);
create type public.verdict as enum ('publish', 'withhold');
create type public.run_status as enum ('queued', 'running', 'published', 'partial', 'withheld', 'failed');
create type public.section_status as enum ('published', 'withheld');
create type public.alert_channel as enum ('telegram', 'email', 'push');
create type public.alert_kind as enum (
  'report_ready', 'report_late', 'section_withheld', 'correction', 'system_health'
);
create type public.outbox_status as enum ('pending', 'sent', 'failed');
create type public.nse_dataset as enum ('fii_dii', 'participant_oi', 'ban_list', 'bhavcopy');
create type public.upload_status as enum ('received', 'parsed', 'rejected');

-- ---------------------------------------------------------------------------
-- Owner allowlist (V0 is owner-only; public sign-up stays off in Supabase Auth settings)
-- ---------------------------------------------------------------------------
create table public.allowed_users (
  email text primary key check (email = lower(email)),
  added_at timestamptz not null default now()
);

-- When authenticator-app 2FA is switched on, also require (auth.jwt() ->> 'aal') = 'aal2' here.
create function public.is_owner() returns boolean
language sql stable security definer set search_path = ''
as $$
  select exists (
    select 1 from public.allowed_users
    where email = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;

create function public.forbid_mutation() returns trigger
language plpgsql set search_path = ''
as $$
begin
  raise exception '% is append-only: insert a new row instead of %', tg_table_name, tg_op;
end;
$$;

-- ---------------------------------------------------------------------------
-- Sources and collected material
-- ---------------------------------------------------------------------------
create table public.sources (
  id text primary key check (id ~ '^[a-z0-9][a-z0-9_-]*$'),
  name text not null,
  domain text not null,
  tier public.source_tier not null,
  kind public.source_kind not null,
  url text,
  active boolean not null default true,
  updated_at timestamptz not null default now()
);

-- API and feed responses only, never article pages. Kept 90 days for debugging and replays.
create table public.raw_responses (
  id bigint generated always as identity primary key,
  source_id text not null references public.sources (id),
  request_key text not null,
  fetched_at timestamptz not null default now(),
  http_status int,
  content_type text,
  body text,
  content_sha256 text not null,
  expires_at timestamptz not null default now() + interval '90 days'
);
create index raw_responses_lookup_idx on public.raw_responses (source_id, request_key, fetched_at desc);
create index raw_responses_expiry_idx on public.raw_responses (expires_at);

-- Headlines and links only: no article text.
create table public.articles (
  id bigint generated always as identity primary key,
  source_id text not null references public.sources (id),
  url text not null unique,
  title text not null,
  published_at timestamptz,
  fetched_at timestamptz not null default now(),
  fingerprint text, -- hash of the page text, not the text
  syndication_group text, -- wire copies share a group and count as one source
  archive_url text -- Wayback Machine capture
);
create index articles_published_idx on public.articles (published_at desc);

create table public.stories (
  id bigint generated always as identity primary key,
  title text not null,
  impact_tags text[] not null default '{}',
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now()
);

create table public.story_articles (
  story_id bigint not null references public.stories (id),
  article_id bigint not null references public.articles (id),
  added_at timestamptz not null default now(),
  primary key (story_id, article_id)
);
create index story_articles_article_idx on public.story_articles (article_id);

create table public.manual_uploads (
  id bigint generated always as identity primary key,
  dataset public.nse_dataset not null,
  trading_date date not null,
  storage_path text not null,
  file_sha256 text not null,
  received_via text not null default 'telegram',
  received_at timestamptz not null default now(),
  status public.upload_status not null default 'received',
  parsed_at timestamptz,
  error text,
  unique (dataset, trading_date, file_sha256)
);

-- ---------------------------------------------------------------------------
-- Runs: one row per (report, trading day, version); queued rows are the job queue
-- ---------------------------------------------------------------------------
create table public.report_runs (
  id bigint generated always as identity primary key,
  report_type public.report_type not null,
  trading_date date not null,
  version int not null default 1 check (version >= 1),
  status public.run_status not null default 'queued',
  deadline_at timestamptz not null,
  queued_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  attempts int not null default 0,
  error text,
  trace jsonb not null default '[]'::jsonb, -- step timings, models, tokens and cost
  cost_usd numeric(10, 4),
  unique (report_type, trading_date, version)
);
create index report_runs_queue_idx on public.report_runs (deadline_at) where status = 'queued';

-- ---------------------------------------------------------------------------
-- Facts, claims and evidence (append-only)
-- ---------------------------------------------------------------------------
create table public.market_facts (
  id bigint generated always as identity primary key,
  run_id bigint references public.report_runs (id),
  field text not null, -- e.g. nifty50.close
  value numeric not null,
  unit text not null,
  as_of timestamptz not null,
  recorded_at timestamptz not null default now(),
  source_id text not null references public.sources (id),
  cross_check jsonb not null default '{}'::jsonb
);
create index market_facts_field_idx on public.market_facts (field, as_of desc);

create table public.claims (
  id text primary key, -- assigned by the pipeline
  run_id bigint not null references public.report_runs (id),
  story_id bigint references public.stories (id),
  claim_type public.claim_type not null,
  text text not null,
  field text,
  unit text,
  value numeric,
  as_of timestamptz,
  attributed_to text,
  verdict public.verdict not null,
  badge public.badge not null,
  independent_sources int not null default 0,
  reasons text[] not null default '{}',
  recorded_at timestamptz not null default now(),
  check ((verdict = 'withhold') = (badge = 'withheld'))
);
create index claims_run_idx on public.claims (run_id);
create index claims_story_idx on public.claims (story_id);

create table public.claim_evidence (
  id bigint generated always as identity primary key,
  claim_id text not null references public.claims (id),
  kind public.evidence_kind not null,
  source_id text not null references public.sources (id),
  tier public.source_tier not null,
  article_id bigint references public.articles (id),
  url text,
  syndication_group text,
  published_at timestamptz,
  fetched_at timestamptz not null,
  http_status int,
  quote text check (
    quote is null or array_length(regexp_split_to_array(btrim(quote), '\s+'), 1) <= 25
  ),
  quote_found boolean not null default false,
  value numeric,
  as_of timestamptz,
  recorded_at timestamptz not null default now()
);
create index claim_evidence_claim_idx on public.claim_evidence (claim_id);

-- ---------------------------------------------------------------------------
-- Published reports
-- ---------------------------------------------------------------------------
create table public.reports (
  id bigint generated always as identity primary key,
  run_id bigint not null references public.report_runs (id),
  report_type public.report_type not null,
  trading_date date not null,
  version int not null check (version >= 1),
  title text not null,
  key_takeaway text,
  published_at timestamptz not null default now(),
  supersedes_id bigint references public.reports (id),
  change_summary text,
  pdf_path text, -- paths in the private "reports" storage bucket
  citation_pack_path text,
  unique (report_type, trading_date, version)
);
create index reports_latest_idx on public.reports (trading_date desc, published_at desc);

-- Sections go live as they pass; a late section shows why and when it will be retried.
create table public.report_sections (
  id bigint generated always as identity primary key,
  report_id bigint not null references public.reports (id),
  key text not null, -- e.g. global_opening_check
  position int not null,
  title text not null,
  status public.section_status not null,
  body jsonb, -- rendered blocks that reference claim ids
  withheld_reason text,
  retry_at timestamptz,
  updated_at timestamptz not null default now(),
  unique (report_id, key),
  check ((status = 'published') = (body is not null)),
  check (status = 'published' or withheld_reason is not null)
);

create table public.section_claims (
  section_id bigint not null references public.report_sections (id),
  claim_id text not null references public.claims (id),
  position int not null,
  primary key (section_id, claim_id)
);
create index section_claims_claim_idx on public.section_claims (claim_id);

create table public.corrections (
  id bigint generated always as identity primary key,
  claim_id text not null references public.claims (id),
  replacement_claim_id text references public.claims (id),
  report_id bigint not null references public.reports (id),
  reason text not null,
  issued_at timestamptz not null default now()
);
create index corrections_claim_idx on public.corrections (claim_id);

create table public.claim_flags (
  id bigint generated always as identity primary key,
  claim_id text not null references public.claims (id),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  note text check (char_length(note) <= 1000),
  status text not null default 'open' check (status in ('open', 'confirmed', 'dismissed')),
  created_at timestamptz not null default now()
);
create index claim_flags_claim_idx on public.claim_flags (claim_id);

-- ---------------------------------------------------------------------------
-- Alerts outbox: written in the same transaction as the publish, sent with retries, never twice
-- ---------------------------------------------------------------------------
create table public.outbox (
  id bigint generated always as identity primary key,
  channel public.alert_channel not null,
  kind public.alert_kind not null,
  dedupe_key text not null unique,
  payload jsonb not null,
  status public.outbox_status not null default 'pending',
  attempts int not null default 0,
  next_attempt_at timestamptz not null default now(),
  last_error text,
  created_at timestamptz not null default now(),
  sent_at timestamptz
);
create index outbox_pending_idx on public.outbox (next_attempt_at) where status = 'pending';

-- ---------------------------------------------------------------------------
-- Append-only guards
-- ---------------------------------------------------------------------------
create trigger market_facts_append_only before update or delete on public.market_facts
  for each row execute function public.forbid_mutation();
create trigger claims_append_only before update or delete on public.claims
  for each row execute function public.forbid_mutation();
create trigger claim_evidence_append_only before update or delete on public.claim_evidence
  for each row execute function public.forbid_mutation();
create trigger corrections_append_only before update or delete on public.corrections
  for each row execute function public.forbid_mutation();

-- ---------------------------------------------------------------------------
-- Row level security: on for every table; the owner may read, and may flag claims
-- ---------------------------------------------------------------------------
alter table public.allowed_users enable row level security;
alter table public.sources enable row level security;
alter table public.raw_responses enable row level security;
alter table public.articles enable row level security;
alter table public.stories enable row level security;
alter table public.story_articles enable row level security;
alter table public.manual_uploads enable row level security;
alter table public.report_runs enable row level security;
alter table public.market_facts enable row level security;
alter table public.claims enable row level security;
alter table public.claim_evidence enable row level security;
alter table public.reports enable row level security;
alter table public.report_sections enable row level security;
alter table public.section_claims enable row level security;
alter table public.corrections enable row level security;
alter table public.claim_flags enable row level security;
alter table public.outbox enable row level security;

create policy "owner reads sources" on public.sources
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads articles" on public.articles
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads stories" on public.stories
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads story articles" on public.story_articles
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads uploads" on public.manual_uploads
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads runs" on public.report_runs
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads market facts" on public.market_facts
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads claims" on public.claims
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads evidence" on public.claim_evidence
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads reports" on public.reports
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads sections" on public.report_sections
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads section claims" on public.section_claims
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads corrections" on public.corrections
  for select to authenticated using ((select public.is_owner()));
create policy "owner reads own flags" on public.claim_flags
  for select to authenticated using ((select public.is_owner()) and user_id = (select auth.uid()));
create policy "owner flags claims" on public.claim_flags
  for insert to authenticated with check ((select public.is_owner()) and user_id = (select auth.uid()));
-- allowed_users, raw_responses and outbox have no policies: only the worker touches them.

-- ---------------------------------------------------------------------------
-- Storage: report PDFs and citation packs, private, served through short-lived signed links
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public) values ('reports', 'reports', false);
-- NSE files sent to the Telegram bot; only the worker reads these.
insert into storage.buckets (id, name, public) values ('uploads', 'uploads', false);

create policy "owner reads report files" on storage.objects
  for select to authenticated using (bucket_id = 'reports' and (select public.is_owner()));
