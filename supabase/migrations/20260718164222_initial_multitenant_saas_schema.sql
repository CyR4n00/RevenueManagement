-- Customer-isolated SaaS schema.  Platform services write with a server-side
-- database/service key; browser clients only receive the publishable key.
create table public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(trim(name)) between 1 and 160),
  stripe_customer_id text unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.organization_members (
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('owner', 'admin', 'member')),
  created_at timestamptz not null default now(),
  primary key (organization_id, user_id)
);
create index organization_members_user_id_organization_id_idx
  on public.organization_members(user_id, organization_id);

create table public.ota_sources (
  key text primary key check (key in ('booking', 'airbnb', 'jalan', 'rakuten')),
  name text not null,
  domains text[] not null,
  collection_status text not null check (collection_status in ('pending', 'approved', 'disabled')),
  approval_reference text,
  actor_environment_key text not null,
  updated_at timestamptz not null default now()
);

insert into public.ota_sources (key, name, domains, collection_status, actor_environment_key)
values
  ('booking', 'Booking.com', array['booking.com'], 'pending', 'APIFY_ACTOR_BOOKING'),
  ('airbnb', 'Airbnb', array['airbnb.com'], 'pending', 'APIFY_ACTOR_AIRBNB'),
  ('jalan', 'じゃらんnet', array['jalan.net'], 'pending', 'APIFY_ACTOR_JALAN'),
  ('rakuten', '楽天トラベル', array['travel.rakuten.co.jp'], 'pending', 'APIFY_ACTOR_RAKUTEN')
on conflict (key) do nothing;

create table public.facilities (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  name text not null check (char_length(trim(name)) between 1 and 160),
  address text,
  base_price integer not null check (base_price between 0 and 1000000),
  min_price integer not null check (min_price between 0 and 1000000),
  max_price integer not null check (max_price between min_price and 1000000),
  onboarding_completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index facilities_organization_id_idx on public.facilities(organization_id);

create table public.competitors (
  id uuid primary key default gen_random_uuid(),
  facility_id uuid not null references public.facilities(id) on delete cascade,
  ota_source_key text not null references public.ota_sources(key),
  name text,
  url text not null check (url like 'https://%'),
  canonical_url text not null check (canonical_url like 'https://%'),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (facility_id, canonical_url)
);
create index competitors_facility_id_idx on public.competitors(facility_id);

create table public.competitor_prices (
  id bigint generated always as identity primary key,
  competitor_id uuid not null references public.competitors(id) on delete cascade,
  stay_date date not null,
  price_jpy integer check (price_jpy is null or price_jpy between 0 and 1000000),
  is_fully_booked boolean not null default false,
  collected_at timestamptz not null default now(),
  collection_source text not null check (collection_source in ('apify', 'simulation')),
  unique (competitor_id, stay_date),
  check (is_fully_booked or price_jpy is not null)
);
create index competitor_prices_competitor_id_stay_date_idx
  on public.competitor_prices(competitor_id, stay_date desc);

create table public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null unique references public.organizations(id) on delete cascade,
  stripe_customer_id text unique,
  stripe_subscription_id text unique,
  stripe_price_id text,
  status text not null default 'inactive',
  current_period_end timestamptz,
  updated_at timestamptz not null default now()
);

alter table public.organizations enable row level security;
alter table public.organization_members enable row level security;
alter table public.ota_sources enable row level security;
alter table public.facilities enable row level security;
alter table public.competitors enable row level security;
alter table public.competitor_prices enable row level security;
alter table public.subscriptions enable row level security;

create policy "members_can_read_own_membership"
  on public.organization_members for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "members_can_read_own_organizations"
  on public.organizations for select to authenticated
  using (exists (
    select 1 from public.organization_members m
    where m.organization_id = organizations.id and m.user_id = (select auth.uid())
  ));

create policy "authenticated_can_read_ota_sources"
  on public.ota_sources for select to authenticated using (true);

create policy "members_can_read_own_facilities"
  on public.facilities for select to authenticated
  using (exists (
    select 1 from public.organization_members m
    where m.organization_id = facilities.organization_id and m.user_id = (select auth.uid())
  ));

create policy "members_can_read_own_competitors"
  on public.competitors for select to authenticated
  using (exists (
    select 1 from public.facilities f
    join public.organization_members m on m.organization_id = f.organization_id
    where f.id = competitors.facility_id and m.user_id = (select auth.uid())
  ));

create policy "members_can_read_own_prices"
  on public.competitor_prices for select to authenticated
  using (exists (
    select 1 from public.competitors c
    join public.facilities f on f.id = c.facility_id
    join public.organization_members m on m.organization_id = f.organization_id
    where c.id = competitor_prices.competitor_id and m.user_id = (select auth.uid())
  ));

create policy "members_can_read_own_subscription"
  on public.subscriptions for select to authenticated
  using (exists (
    select 1 from public.organization_members m
    where m.organization_id = subscriptions.organization_id and m.user_id = (select auth.uid())
  ));

comment on table public.ota_sources is 'Platform-managed OTA collection permission register. Only approved sources may be collected in production.';
comment on table public.competitor_prices is 'Daily lowest available rate or sold-out state collected through an approved provider.';
