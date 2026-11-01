-- ArchiDB Blog: im Supabase Dashboard unter "SQL Editor" ausführen.
create table if not exists public.posts (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  slug text not null unique,
  summary text default '',
  body text default '',
  author text default 'Vladislav Sloboder',
  published boolean not null default false,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
 
create or replace function public.set_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end; $$ language plpgsql;
drop trigger if exists posts_updated on public.posts;
create trigger posts_updated before update on public.posts
  for each row execute function public.set_updated_at();
 
alter table public.posts enable row level security;
 
-- Besucher (anon): nur veröffentlichte Artikel lesen
drop policy if exists "public read published" on public.posts;
create policy "public read published" on public.posts
  for select to anon, authenticated using (published = true);
 
-- Admin: NUR diese E-Mail darf alles (hier ggf. anpassen!)
drop policy if exists "admin all" on public.posts;
create policy "admin all" on public.posts
  for all to authenticated
  using ((auth.jwt() ->> 'email') = 'info@archidb.de')
  with check ((auth.jwt() ->> 'email') = 'info@archidb.de');
 
grant select on public.posts to anon;
grant select, insert, update, delete on public.posts to authenticated;
