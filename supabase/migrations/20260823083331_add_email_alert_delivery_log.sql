create table public.notification_deliveries (
  id bigint generated always as identity primary key,
  organization_id uuid not null references public.organizations(id) on delete cascade,
  fingerprint text not null check (fingerprint ~ '^[0-9a-f]{64}$'),
  delivered_at timestamptz not null default now(),
  unique (organization_id, fingerprint)
);

create index notification_deliveries_organization_delivered_idx
  on public.notification_deliveries (organization_id, delivered_at desc);

alter table public.notification_deliveries enable row level security;

create policy "members_can_read_own_notification_deliveries"
  on public.notification_deliveries for select to authenticated
  using (exists (
    select 1 from public.organization_members m
    where m.organization_id = notification_deliveries.organization_id
      and m.user_id = (select auth.uid())
  ));

comment on table public.notification_deliveries is
  'Successful transactional alert batches. Fingerprints prevent duplicate email delivery.';
