create table public.facility_rate_ranks (
  id uuid primary key default gen_random_uuid(),
  facility_id uuid not null references public.facilities(id) on delete cascade,
  label text not null check (label ~ '^[A-Z]$'),
  price_jpy integer not null check (price_jpy between 0 and 1000000),
  sort_order integer not null check (sort_order between 0 and 11),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (facility_id, label),
  unique (facility_id, sort_order)
);

create index facility_rate_ranks_facility_id_idx
  on public.facility_rate_ranks(facility_id);

insert into public.facility_rate_ranks (facility_id, label, price_jpy, sort_order)
select id, rank.label, rank.price_jpy, rank.sort_order
from public.facilities
cross join lateral (values
  ('A', max_price, 0),
  ('B', min_price + round((max_price - min_price) * 0.67)::integer, 1),
  ('C', min_price + round((max_price - min_price) * 0.34)::integer, 2),
  ('D', min_price, 3)
) as rank(label, price_jpy, sort_order)
on conflict do nothing;

alter table public.facility_rate_ranks enable row level security;

create policy "members_can_read_own_rate_ranks"
  on public.facility_rate_ranks for select to authenticated
  using (exists (
    select 1 from public.facilities f
    join public.organization_members m on m.organization_id = f.organization_id
    where f.id = facility_rate_ranks.facility_id
      and m.user_id = (select auth.uid())
  ));

comment on table public.facility_rate_ranks is
  'Facility-defined operational rate ladder. A is the highest price; labels continue sequentially for properties that need E, F, or more.';
