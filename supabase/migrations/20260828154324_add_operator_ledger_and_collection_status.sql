alter table public.competitor_collection_runs
  add column completed_at timestamptz,
  add column status text not null default 'started'
    check (status in ('started', 'succeeded', 'failed')),
  add column records_collected integer not null default 0
    check (records_collected >= 0),
  add column error_message text;

create index competitor_collection_runs_status_started_at_idx
  on public.competitor_collection_runs(status, started_at desc);

create table public.payment_ledger (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  customer_name text not null check (char_length(trim(customer_name)) between 1 and 160),
  billing_month date not null,
  paid_at date,
  amount_jpy integer not null check (amount_jpy between 1 and 10000000),
  service_end date not null,
  status text not null default 'paid' check (status in ('paid', 'unpaid', 'canceled')),
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index payment_ledger_organization_billing_month_idx
  on public.payment_ledger(organization_id, billing_month desc);

alter table public.payment_ledger enable row level security;

comment on table public.payment_ledger is
  'Server-only bank-transfer ledger. No browser Data API policy is granted; operators use authenticated backend endpoints.';
