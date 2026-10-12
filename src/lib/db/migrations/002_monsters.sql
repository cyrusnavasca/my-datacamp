-- Monsters the learner owns, one row per line. Species, forms and art live in
-- src/lib/monsters/roster.ts; rows reference a line by its id. Level and form
-- are derived from xp (src/lib/monsters/level.ts). The partner, which gets
-- the XP from each finished exercise, is settings.partner.

create table if not exists monsters (
  line_id    text primary key,
  xp         integer not null default 0 check (xp >= 0),
  caught_at  text not null
);
