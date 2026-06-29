create table if not exists deal_records (
  id uuid primary key default gen_random_uuid(),
  counterparty_name text not null,
  commodity text not null,
  status text not null default 'draft',
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists ledger_entries (
  id uuid primary key default gen_random_uuid(),
  deal_id uuid not null references deal_records(id) on delete cascade,
  entry_type text not null,
  amount numeric(18,2) not null default 0,
  currency text not null default 'USD',
  created_at timestamptz not null default timezone('utc', now())
);
