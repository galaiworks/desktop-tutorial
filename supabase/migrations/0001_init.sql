-- NUMEN 初期スキーマ（要件定義書 §7 データ設計）
-- 方針: 本名は保持しない。生年月日そのものも保存せず、算出済みのライフパスのみを持つ（§13-4）。

create extension if not exists "pgcrypto";

-- 匿名ユーザー（将来のLINE連携・マッチング用。MVPでは任意）
create table if not exists public.users (
  id           uuid primary key default gen_random_uuid(),
  line_user_id text unique,
  created_at   timestamptz not null default now()
);

-- 診断結果
create table if not exists public.diagnoses (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid references public.users (id) on delete set null,
  life_path  smallint not null check (life_path in (1,2,3,4,5,6,7,8,9,11,22,33)),
  big5       jsonb    not null,
  lens       text     check (lens in ('romance','business')),
  created_at timestamptz not null default now()
);
create index if not exists diagnoses_created_at_idx on public.diagnoses (created_at desc);
create index if not exists diagnoses_life_path_idx  on public.diagnoses (life_path);

-- 相性算出の記録（フェーズ2のマッチング推薦の素地）
create table if not exists public.matches (
  id                uuid primary key default gen_random_uuid(),
  self_id           uuid references public.users (id) on delete set null,
  target_id         uuid references public.users (id) on delete set null,
  self_life_path    smallint not null,
  target_life_path  smallint not null,
  lens              text not null check (lens in ('romance','business')),
  score             smallint not null check (score between 0 and 100),
  created_at        timestamptz not null default now()
);
create index if not exists matches_created_at_idx on public.matches (created_at desc);

-- 診断結果とLINE友だちの紐付けトークン（§5.7 の引き継ぎ）
create table if not exists public.line_links (
  token        text primary key,
  diagnosis_id uuid references public.diagnoses (id) on delete cascade,
  line_user_id text,
  consumed_at  timestamptz,
  created_at   timestamptz not null default now(),
  expires_at   timestamptz not null default (now() + interval '30 days')
);

-- RLS: 既定で全拒否。書き込みはサーバ（service role）経由のみとし、
-- 匿名クライアントから診断データを読めないようにする。
alter table public.users      enable row level security;
alter table public.diagnoses  enable row level security;
alter table public.matches    enable row level security;
alter table public.line_links enable row level security;
-- ポリシーを一つも作らない = anon / authenticated からは読み書き不可。
-- service_role キーは RLS をバイパスするため、サーバ側の書き込みのみ通る。
