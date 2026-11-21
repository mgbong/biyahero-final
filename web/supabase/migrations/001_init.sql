-- BIYAHERO Phase 1 — core schema (Naga City)
-- Run in Supabase SQL editor (or via supabase db push).
-- Requires PostGIS.

create extension if not exists postgis;
create extension if not exists pgcrypto;

create type public.verification_status as enum (
  'verified',
  'pending_verification',
  'potentially_outdated'
);

create type public.transport_type as enum (
  'jeepney',
  'tricycle',
  'bus',
  'walk_link'
);

create type public.plan_criterion as enum (
  'cheapest',
  'fastest',
  'fewest_transfers',
  'shortest_walk'
);

create table public.stops (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  geom geography(Point, 4326) not null,
  landmark_notes text,
  verification_status public.verification_status not null
    default 'pending_verification',
  last_verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.routes (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  code text unique,
  transport_type public.transport_type not null,
  geom geography(LineString, 4326),
  verification_status public.verification_status not null
    default 'pending_verification',
  last_verified_at timestamptz,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.route_stops (
  route_id uuid not null references public.routes (id) on delete cascade,
  stop_id uuid not null references public.stops (id) on delete restrict,
  sequence int not null check (sequence >= 1),
  primary key (route_id, sequence),
  unique (route_id, stop_id)
);

create table public.transfers (
  id uuid primary key default gen_random_uuid(),
  from_stop_id uuid not null references public.stops (id) on delete cascade,
  to_stop_id uuid not null references public.stops (id) on delete cascade,
  walking_distance_m numeric(10, 2) not null check (walking_distance_m >= 0),
  estimated_walk_seconds int check (estimated_walk_seconds is null or estimated_walk_seconds >= 0),
  check (from_stop_id <> to_stop_id)
);

create table public.fare_rules (
  id uuid primary key default gen_random_uuid(),
  transport_type public.transport_type not null,
  base_fare numeric(10, 2) not null check (base_fare >= 0),
  per_km_rate numeric(10, 4) not null check (per_km_rate >= 0),
  min_fare numeric(10, 2) check (min_fare is null or min_fare >= 0),
  currency text not null default 'PHP',
  active boolean not null default true,
  effective_from timestamptz,
  effective_to timestamptz,
  check (
    effective_to is null
    or effective_from is null
    or effective_to > effective_from
  )
);

-- Discounts are NEVER hardcoded in app code — only active rows apply.
create table public.discount_rules (
  id uuid primary key default gen_random_uuid(),
  type text not null,
  percent numeric(5, 2) not null check (percent >= 0 and percent <= 100),
  requires_validation boolean not null default true,
  active boolean not null default false,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.disruptions (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text not null,
  disruption_kind text,
  affected_route_ids uuid[] not null default '{}',
  affected_stop_ids uuid[] not null default '{}',
  starts_at timestamptz not null,
  ends_at timestamptz,
  verified boolean not null default false,
  created_by uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (ends_at is null or ends_at > starts_at)
);

create table public.search_logs (
  id uuid primary key default gen_random_uuid(),
  origin_label text,
  dest_label text,
  origin_geom geography(Point, 4326),
  dest_geom geography(Point, 4326),
  criterion public.plan_criterion,
  result_count int,
  created_at timestamptz not null default now()
);

create table public.feedback (
  id uuid primary key default gen_random_uuid(),
  message text not null,
  rating int check (rating is null or (rating between 1 and 5)),
  route_id uuid references public.routes (id) on delete set null,
  created_at timestamptz not null default now()
);

create table public.issue_reports (
  id uuid primary key default gen_random_uuid(),
  category text not null,
  description text not null,
  route_id uuid references public.routes (id) on delete set null,
  stop_id uuid references public.stops (id) on delete set null,
  status text not null default 'open',
  created_at timestamptz not null default now()
);

-- Reserved for later phases (no UI yet)
create table public.saved_routes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  title text,
  itinerary_json jsonb not null,
  created_at timestamptz not null default now()
);

create table public.recent_searches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  origin_label text,
  dest_label text,
  created_at timestamptz not null default now()
);

create index stops_geom_gix on public.stops using gist (geom);
create index routes_geom_gix on public.routes using gist (geom);
create index route_stops_route_seq_idx on public.route_stops (route_id, sequence);
create index transfers_from_idx on public.transfers (from_stop_id);
create index transfers_to_idx on public.transfers (to_stop_id);
create index fare_rules_type_active_idx on public.fare_rules (transport_type, active);
create index discount_rules_active_idx on public.discount_rules (active) where active = true;
create index disruptions_verified_active_idx
  on public.disruptions (starts_at, ends_at)
  where verified = true;
create index search_logs_created_idx on public.search_logs (created_at desc);

comment on table public.discount_rules is
  'Admin-editable discounts. App must only apply rows where active = true.';
comment on column public.disruptions.verified is
  'Only verified = true disruptions surface to commuters.';
