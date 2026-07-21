-- Reserve every production Actor invocation before it is started. The unique
-- daily slot prevents a manual dashboard refresh from exceeding an OTA's
-- written collection-frequency limit.
create table public.competitor_collection_runs (
  id bigint generated always as identity primary key,
  competitor_id uuid not null references public.competitors(id) on delete cascade,
  collection_day date not null,
  slot smallint not null check (slot between 1 and 2),
  started_at timestamptz not null default now(),
  collection_source text not null check (collection_source in ('apify', 'simulation')),
  unique (competitor_id, collection_day, slot)
);

create index competitor_collection_runs_competitor_day_idx
  on public.competitor_collection_runs(competitor_id, collection_day desc);

alter table public.competitor_collection_runs enable row level security;

create policy "members_can_read_own_collection_runs"
  on public.competitor_collection_runs for select to authenticated
  using (exists (
    select 1 from public.competitors c
    join public.facilities f on f.id = c.facility_id
    join public.organization_members m on m.organization_id = f.organization_id
    where c.id = competitor_collection_runs.competitor_id
      and m.user_id = (select auth.uid())
  ));

comment on table public.competitor_collection_runs is
  'Server-reserved Apify collection slots. Production uses these records to enforce each OTA daily run limit.';
