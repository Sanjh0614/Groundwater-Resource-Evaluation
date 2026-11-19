-- Run this once in Supabase -> SQL Editor
create table if not exists readings (
  id             bigint generated always as identity primary key,
  device_id      text not null default 'node-1',
  water_level_cm double precision not null,
  voltage        double precision,
  recorded_at    timestamptz not null default now()
);

create index if not exists readings_device_time_idx
  on readings (device_id, recorded_at desc);

-- Only the backend (service-role key) touches this table
alter table readings enable row level security;
