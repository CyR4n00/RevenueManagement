alter table public.organizations
  add column notification_email text
    check (notification_email is null or (char_length(notification_email) <= 320 and position('@' in notification_email) > 1)),
  add column email_notifications_enabled boolean not null default true;

update public.organizations as organization
set notification_email = account.email
from public.organization_members as membership
join auth.users as account on account.id = membership.user_id
where membership.organization_id = organization.id
  and membership.role = 'owner'
  and organization.notification_email is null;

comment on column public.organizations.notification_email is
  'Verified Supabase Auth email copied at account setup and used as the default alert recipient.';
