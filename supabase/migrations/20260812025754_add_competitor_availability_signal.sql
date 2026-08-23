alter table public.competitor_prices
  add column availability_status text not null default 'unknown'
    check (availability_status in ('available', 'limited', 'sold_out', 'unknown')),
  add column remaining_rooms integer
    check (remaining_rooms is null or remaining_rooms between 0 and 10000),
  add column availability_source text not null default 'inferred'
    check (availability_source in ('explicit_count', 'symbol', 'inferred', 'unknown'));

alter table public.competitor_price_observations
  add column availability_status text not null default 'unknown'
    check (availability_status in ('available', 'limited', 'sold_out', 'unknown')),
  add column remaining_rooms integer
    check (remaining_rooms is null or remaining_rooms between 0 and 10000),
  add column availability_source text not null default 'inferred'
    check (availability_source in ('explicit_count', 'symbol', 'inferred', 'unknown'));

update public.competitor_prices
set availability_status = case
  when is_fully_booked then 'sold_out'
  when price_jpy is not null then 'available'
  else 'unknown'
end;

update public.competitor_price_observations
set availability_status = case
  when is_fully_booked then 'sold_out'
  when price_jpy is not null then 'available'
  else 'unknown'
end;

comment on column public.competitor_prices.remaining_rooms is
  'Minimum room count explicitly displayed by the OTA for a visible offer; null when not shown.';
comment on column public.competitor_prices.availability_status is
  'OTA-facing availability signal, not the property''s actual occupancy rate.';
