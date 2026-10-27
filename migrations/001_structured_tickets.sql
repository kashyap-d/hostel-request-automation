-- Safe to run more than once, on a fresh project or on the original tables.
-- Run it in the Supabase SQL editor.

create table if not exists studentinfo (
  reg_number   text primary key,
  name         text not null,
  hostel_block text
);

create table if not exists request (
  id                bigint generated always as identity primary key,
  reg_number        text not null references studentinfo (reg_number),
  student_name      text not null,
  problem_statement text not null,
  created_at        timestamptz not null default now()
);

-- Structured ticket fields. The checks mirror the Literal types in classifier.py.
alter table request
  add column if not exists category text
    check (category in ('electrical', 'plumbing', 'cleanliness', 'furniture', 'internet',
                        'mess_food', 'security', 'room_allocation', 'admission', 'other'));
alter table request
  add column if not exists urgency text check (urgency in ('low', 'medium', 'high'));
alter table request add column if not exists location text;
alter table request add column if not exists is_repeat boolean not null default false;

-- History lookups filter by student and sort by time.
create index if not exists request_reg_number_created_at_idx on request (reg_number, created_at desc);

-- The bot uses the service key, which bypasses RLS. Enabling RLS with no policies
-- means the public anon key cannot read or write students' complaints.
alter table studentinfo enable row level security;
alter table request enable row level security;
