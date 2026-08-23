-- NUMEN フェーズ2: マッチング用プロフィールとLIFF連携（要件定義書 §3.2 / §5.7）
-- 方針は 0001 と同じ: 本名・生年月日は保持せず、算出済みの数値のみを扱う。

-- マッチングに参加する人だけが載る、明示的オプトインのプロフィール
create table if not exists public.match_profiles (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid references public.users (id) on delete cascade,
  handle       text not null,                      -- 表示名（ニックネーム。本名を推奨しない）
  life_path    smallint not null check (life_path in (1,2,3,4,5,6,7,8,9,11,22,33)),
  big5         jsonb not null,
  lens         text not null default 'romance' check (lens in ('romance','business')),
  opted_in     boolean not null default false,     -- 明示的な同意がない限り推薦対象にしない
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists match_profiles_optin_idx on public.match_profiles (opted_in, lens);

-- LIFF（LINE内ミニアプリ）からの本人紐付け
alter table public.line_links
  add column if not exists life_path smallint,
  add column if not exists big5 jsonb,
  add column if not exists lens text;

-- RLS: 0001 と同様、ポリシーを作らず service role 経由のみに限定する。
alter table public.match_profiles enable row level security;

comment on table public.match_profiles is
  'マッチング用プロフィール。opted_in = true の行のみ推薦対象。退会時は行ごと削除する。';
