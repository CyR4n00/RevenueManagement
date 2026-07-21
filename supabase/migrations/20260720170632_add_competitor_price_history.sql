-- Keep each approved collection event so that price movement is calculated for
-- the same competitor and stay date, rather than comparing different dates.
create table public.competitor_price_observations (
  id bigint generated always as identity primary key,
  competitor_id uuid not null references public.competitors(id) on delete cascade,
  stay_date date not null,
  price_jpy integer check (price_jpy is null or price_jpy between 0 and 1000000),
  is_fully_booked boolean not null default false,
  collected_at timestamptz not null default now(),
  collection_source text not null check (collection_source in ('apify', 'simulation')),
  check (is_fully_booked or price_jpy is not null)
);

create index competitor_price_observations_competitor_stay_collected_idx
  on public.competitor_price_observations (competitor_id, stay_date, collected_at desc);

alter table public.competitor_price_observations enable row level security;

create policy "members_can_read_own_price_observations"
  on public.competitor_price_observations for select to authenticated
  using (exists (
    select 1
    from public.competitors c
    join public.facilities f on f.id = c.facility_id
    join public.organization_members m on m.organization_id = f.organization_id
    where c.id = competitor_price_observations.competitor_id
      and m.user_id = (select auth.uid())
  ));

comment on table public.competitor_price_observations is
  'Immutable approved-collection events used to calculate rate movement for the same stay date.';
