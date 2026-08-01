PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ─────────── build metadata ───────────
CREATE TABLE build_info (
  build_id        TEXT PRIMARY KEY,
  built_at        TEXT NOT NULL,
  tool_version    TEXT NOT NULL,
  baseline_version TEXT,
  hack_name       TEXT,
  hack_version    TEXT,
  engine          TEXT,          -- pokeemerald | pokefirered | cfru | custom
  source_manifest TEXT NOT NULL  -- JSON {path: sha1}
);

-- ─────────── provenance ───────────
CREATE TABLE provenance (
  provenance_id       INTEGER PRIMARY KEY,
  entity_type         TEXT NOT NULL,
  entity_key          TEXT NOT NULL,
  field_path          TEXT NOT NULL,
  source_type         TEXT NOT NULL
     CHECK (source_type IN ('official_baseline','rom_extract','hack_override',
                            'explicit_custom','inferred','unknown')),
  source_file         TEXT, source_version TEXT, source_record TEXT,
  value_hash          TEXT,
  confidence          REAL NOT NULL DEFAULT 0.0 CHECK (confidence BETWEEN 0 AND 1),
  verification_status TEXT NOT NULL DEFAULT 'unknown',
  last_verified_at    TEXT, verified_by TEXT,
  conflicts_with      TEXT, notes TEXT
);
CREATE INDEX ix_prov_entity ON provenance(entity_type, entity_key);
CREATE INDEX ix_prov_conf   ON provenance(confidence);

-- ─────────── types ───────────
CREATE TABLE types (
  type_slug   TEXT PRIMARY KEY,
  type_name   TEXT NOT NULL,
  rom_type_id INTEGER,
  enabled     INTEGER NOT NULL DEFAULT 1,
  is_custom   INTEGER NOT NULL DEFAULT 0,
  gen3_damage_class TEXT CHECK (gen3_damage_class IN ('physical','special')),
  aliases     TEXT,                       -- JSON array
  implementation_status TEXT NOT NULL DEFAULT 'confirmed',
  verification_status   TEXT NOT NULL DEFAULT 'confirmed',
  notes TEXT
);

CREATE TABLE type_matchups (
  attacking_type TEXT NOT NULL REFERENCES types(type_slug),
  defending_type TEXT NOT NULL REFERENCES types(type_slug),
  multiplier     REAL NOT NULL CHECK (multiplier IN (0,0.25,0.5,1,2,4)),
  chart_version  TEXT NOT NULL DEFAULT 'hack_default',
  differs_from_baseline INTEGER NOT NULL DEFAULT 0,
  verification_status TEXT NOT NULL DEFAULT 'baseline_only',
  PRIMARY KEY (chart_version, attacking_type, defending_type)
);

-- ─────────── species / forms ───────────
CREATE TABLE species (
  species_slug   TEXT PRIMARY KEY,
  species_name   TEXT NOT NULL,
  natdex_no      INTEGER,
  family_root    TEXT,                    -- slug of base form of family
  is_custom      INTEGER NOT NULL DEFAULT 0,
  implementation_status TEXT NOT NULL DEFAULT 'baseline_only',
  verification_status   TEXT NOT NULL DEFAULT 'baseline_only',
  notes TEXT
);

CREATE TABLE forms (
  form_id        TEXT PRIMARY KEY,        -- 'charizard' | 'charizard--mega-x'
  species_slug   TEXT NOT NULL REFERENCES species(species_slug) ON DELETE CASCADE,
  form_name      TEXT NOT NULL DEFAULT 'base',
  is_default     INTEGER NOT NULL DEFAULT 1,
  rom_species_id INTEGER,
  sprite_id      TEXT,
  engine_symbol  TEXT,                    -- e.g. SPECIES_CHARIZARD
  type_1         TEXT NOT NULL REFERENCES types(type_slug),
  type_2         TEXT REFERENCES types(type_slug),
  base_hp        INTEGER NOT NULL, base_atk INTEGER NOT NULL,
  base_def       INTEGER NOT NULL, base_spa INTEGER NOT NULL,
  base_spd       INTEGER NOT NULL, base_spe INTEGER NOT NULL,
  bst            INTEGER GENERATED ALWAYS AS
                   (base_hp+base_atk+base_def+base_spa+base_spd+base_spe) STORED,
  evolution_stage INTEGER,                -- 0 baby, 1 base, 2 mid, 3 final
  is_fully_evolved INTEGER,
  gender_ratio   TEXT, catch_rate INTEGER, exp_yield INTEGER, growth_rate TEXT,
  implementation_status TEXT NOT NULL DEFAULT 'baseline_only',
  verification_status   TEXT NOT NULL DEFAULT 'baseline_only',
  confidence     REAL NOT NULL DEFAULT 0.3,
  notes TEXT
);
CREATE INDEX ix_forms_types ON forms(type_1, type_2);
CREATE INDEX ix_forms_spe   ON forms(base_spe);

-- ─────────── abilities ───────────
CREATE TABLE abilities (
  ability_slug  TEXT PRIMARY KEY,
  ability_name  TEXT NOT NULL,
  rom_ability_id INTEGER, engine_symbol TEXT,
  description   TEXT,
  trigger_conditions TEXT,                -- JSON array
  battle_effects     TEXT,                -- JSON structured effect list
  grants_type_immunity TEXT,              -- JSON array of type_slug
  damage_modifiers   TEXT,                -- JSON
  stat_modifiers     TEXT,                -- JSON
  weather_interaction TEXT, terrain_interaction TEXT,
  status_interaction  TEXT, hazard_interaction  TEXT,
  switch_interaction  TEXT, recovery_interaction TEXT,
  contact_interaction TEXT, item_interaction     TEXT,
  move_interaction    TEXT,
  changes_type_matchups INTEGER NOT NULL DEFAULT 0,
  changes_role_class    INTEGER NOT NULL DEFAULT 0,
  creates_team_synergy  INTEGER NOT NULL DEFAULT 0,
  requires_advanced_ai  INTEGER NOT NULL DEFAULT 0,
  ai_relevance   TEXT CHECK (ai_relevance IN ('none','passive','reactive','requires_scripting')),
  is_custom      INTEGER NOT NULL DEFAULT 0,
  implementation_status TEXT NOT NULL DEFAULT 'baseline_only',
  verification_status   TEXT NOT NULL DEFAULT 'baseline_only',
  confidence REAL NOT NULL DEFAULT 0.3,
  notes TEXT
);

CREATE TABLE ability_tags (
  ability_slug TEXT NOT NULL REFERENCES abilities(ability_slug) ON DELETE CASCADE,
  tag TEXT NOT NULL,
  PRIMARY KEY (ability_slug, tag)
);

CREATE TABLE form_abilities (
  form_id     TEXT NOT NULL REFERENCES forms(form_id) ON DELETE CASCADE,
  slot        INTEGER NOT NULL,           -- 1,2 regular; 3 hidden; 4+ custom
  ability_slug TEXT NOT NULL REFERENCES abilities(ability_slug),
  availability TEXT NOT NULL DEFAULT 'regular'
     CHECK (availability IN ('regular','hidden','boss_only','rematch_only','custom','unavailable')),
  implementation_status TEXT NOT NULL DEFAULT 'baseline_only',
  verification_status   TEXT NOT NULL DEFAULT 'baseline_only',
  PRIMARY KEY (form_id, slot)
);

-- ─────────── moves ───────────
CREATE TABLE moves (
  move_slug   TEXT PRIMARY KEY,
  move_name   TEXT NOT NULL,
  rom_move_id INTEGER, engine_symbol TEXT,
  type_slug   TEXT NOT NULL REFERENCES types(type_slug),
  power       INTEGER, accuracy INTEGER, pp INTEGER NOT NULL DEFAULT 5,
  priority    INTEGER NOT NULL DEFAULT 0,
  target_mode TEXT NOT NULL DEFAULT 'selected'
     CHECK (target_mode IN ('selected','both_foes','all_others','user','user_side',
                            'foe_side','field','random_foe','ally','user_or_ally','scripted')),
  damage_class TEXT NOT NULL CHECK (damage_class IN ('physical','special','status')),
  category_source TEXT NOT NULL DEFAULT 'gen3_type_based'
     CHECK (category_source IN ('gen3_type_based','phys_spec_split','custom_override')),
  effect_id     TEXT, effect_params TEXT,          -- JSON
  secondary_chance INTEGER NOT NULL DEFAULT 0,
  recoil_pct    INTEGER NOT NULL DEFAULT 0,
  drain_pct     INTEGER NOT NULL DEFAULT 0,
  crit_stage    INTEGER NOT NULL DEFAULT 0,
  min_hits      INTEGER, max_hits INTEGER,
  charge_turn   INTEGER NOT NULL DEFAULT 0,
  recharge_turn INTEGER NOT NULL DEFAULT 0,
  flag_contact  INTEGER NOT NULL DEFAULT 0, flag_sound INTEGER NOT NULL DEFAULT 0,
  flag_punch    INTEGER NOT NULL DEFAULT 0, flag_bite  INTEGER NOT NULL DEFAULT 0,
  flag_bullet   INTEGER NOT NULL DEFAULT 0, flag_slicing INTEGER NOT NULL DEFAULT 0,
  flag_wind     INTEGER NOT NULL DEFAULT 0, flag_powder INTEGER NOT NULL DEFAULT 0,
  protect_affected  INTEGER NOT NULL DEFAULT 1,
  bypasses_substitute INTEGER NOT NULL DEFAULT 0,
  magic_coat_affected INTEGER NOT NULL DEFAULT 0,
  snatch_affected     INTEGER NOT NULL DEFAULT 0,
  kings_rock_affected INTEGER NOT NULL DEFAULT 0,
  ai_utility_class TEXT,       -- damage|status|setup|recovery|hazard|pivot|phaze|weather|screen|trap|gimmick
  ai_safety TEXT NOT NULL DEFAULT 'unknown'
     CHECK (ai_safety IN ('safe_vanilla','safe_improved','requires_scripted','unsafe','unknown')),
  generation_source TEXT,      -- gen1..gen9 | custom
  is_custom  INTEGER NOT NULL DEFAULT 0,
  implementation_status TEXT NOT NULL DEFAULT 'baseline_only',
  verification_status   TEXT NOT NULL DEFAULT 'baseline_only',
  confidence REAL NOT NULL DEFAULT 0.3,
  notes TEXT
);
CREATE INDEX ix_moves_type ON moves(type_slug);
CREATE INDEX ix_moves_ai   ON moves(ai_safety);

CREATE TABLE move_tags (
  move_slug TEXT NOT NULL REFERENCES moves(move_slug) ON DELETE CASCADE,
  tag TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'inferred',
  PRIMARY KEY (move_slug, tag)
);

-- ─────────── learnsets ───────────
CREATE TABLE learnsets (
  learnset_id INTEGER PRIMARY KEY,
  form_id   TEXT NOT NULL REFERENCES forms(form_id) ON DELETE CASCADE,
  move_slug TEXT NOT NULL REFERENCES moves(move_slug),
  method    TEXT NOT NULL CHECK (method IN ('level_up','tm','hm','tutor','egg','event','custom')),
  level     INTEGER,                 -- level_up only
  source_ref TEXT,                   -- TM12 / tutor_id / event name
  npc_only  INTEGER NOT NULL DEFAULT 0,
  implementation_status TEXT NOT NULL DEFAULT 'baseline_only',
  verification_status   TEXT NOT NULL DEFAULT 'baseline_only'
);
CREATE UNIQUE INDEX uq_learnsets ON learnsets(form_id, move_slug, method, COALESCE(level,-1), COALESCE(source_ref,''));
CREATE INDEX ix_learn_form ON learnsets(form_id, method, level);
CREATE INDEX ix_learn_move ON learnsets(move_slug);

CREATE TABLE tm_definitions (
  tm_code TEXT PRIMARY KEY,          -- TM01 / HM03 / TUTOR_ROCK_SLIDE
  kind    TEXT NOT NULL CHECK (kind IN ('tm','hm','tutor')),
  move_slug TEXT NOT NULL REFERENCES moves(move_slug),
  player_available_stage TEXT,       -- FK-ish to progression_stages.stage_id
  npc_available_stage    TEXT,
  reusable INTEGER NOT NULL DEFAULT 0,
  implementation_status TEXT NOT NULL DEFAULT 'baseline_only',
  verification_status   TEXT NOT NULL DEFAULT 'baseline_only'
);

-- ─────────── evolutions ───────────
CREATE TABLE evolutions (
  evolution_id INTEGER PRIMARY KEY,
  from_form_id TEXT NOT NULL REFERENCES forms(form_id) ON DELETE CASCADE,
  to_form_id   TEXT NOT NULL REFERENCES forms(form_id),
  method       TEXT NOT NULL,        -- level_up|item|trade|friendship|move_known|custom
  level        INTEGER,
  condition_param TEXT,
  implementation_status TEXT NOT NULL DEFAULT 'baseline_only',
  verification_status   TEXT NOT NULL DEFAULT 'baseline_only'
);

-- ─────────── items ───────────
CREATE TABLE items (
  item_slug TEXT PRIMARY KEY,
  item_name TEXT NOT NULL, rom_item_id INTEGER, engine_symbol TEXT,
  category  TEXT,          -- held|berry|battle|key|ball
  effect_text TEXT, battle_effect TEXT,   -- JSON
  consumable INTEGER NOT NULL DEFAULT 0,
  player_available_stage TEXT, npc_available_stage TEXT,
  boss_only INTEGER NOT NULL DEFAULT 0,
  ai_usable INTEGER NOT NULL DEFAULT 1,
  implementation_status TEXT NOT NULL DEFAULT 'baseline_only',
  verification_status   TEXT NOT NULL DEFAULT 'baseline_only',
  confidence REAL NOT NULL DEFAULT 0.3
);

-- ─────────── encounters & availability ───────────
CREATE TABLE encounters (
  encounter_id INTEGER PRIMARY KEY,
  form_id  TEXT NOT NULL REFERENCES forms(form_id) ON DELETE CASCADE,
  location TEXT NOT NULL, method TEXT NOT NULL,   -- grass|surf|fish|gift|static|trade|egg
  min_level INTEGER, max_level INTEGER, rate REAL,
  stage_id TEXT,
  implementation_status TEXT NOT NULL DEFAULT 'baseline_only',
  verification_status   TEXT NOT NULL DEFAULT 'baseline_only'
);

CREATE TABLE progression_stages (
  stage_id   TEXT PRIMARY KEY,       -- 'pre_gym1','post_gym3','midgame','e4','postgame'
  ordinal    INTEGER NOT NULL UNIQUE,
  label      TEXT NOT NULL,
  expected_player_level_min INTEGER NOT NULL,
  expected_player_level_max INTEGER NOT NULL,
  expected_party_size INTEGER NOT NULL,
  expected_species    TEXT,   -- JSON array of form_id realistically obtainable
  expected_move_pool  TEXT,   -- JSON array of move_slug
  available_tms       TEXT,   -- JSON array of tm_code
  available_tutors    TEXT,
  available_items     TEXT,
  healing_available   INTEGER NOT NULL DEFAULT 1,
  battle_items_allowed INTEGER NOT NULL DEFAULT 1,
  grinding_expectation TEXT NOT NULL DEFAULT 'normal'
     CHECK (grinding_expectation IN ('discouraged','normal','expected')),
  notes TEXT
);

CREATE TABLE form_availability (
  form_id  TEXT NOT NULL REFERENCES forms(form_id) ON DELETE CASCADE,
  stage_id TEXT NOT NULL REFERENCES progression_stages(stage_id),
  player_available INTEGER NOT NULL DEFAULT 0,
  npc_available    INTEGER NOT NULL DEFAULT 0,
  min_level INTEGER, max_level INTEGER,
  boss_only    INTEGER NOT NULL DEFAULT 0,
  rematch_only INTEGER NOT NULL DEFAULT 0,
  postgame_only INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (form_id, stage_id)
);

-- ─────────── tags ───────────
CREATE TABLE form_tags (
  form_id TEXT NOT NULL REFERENCES forms(form_id) ON DELETE CASCADE,
  tag TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'inferred',
  PRIMARY KEY (form_id, tag)
);

-- ─────────── rulesets ───────────
CREATE TABLE rulesets (
  ruleset_id TEXT PRIMARY KEY,
  label TEXT NOT NULL, extends TEXT REFERENCES rulesets(ruleset_id),
  config_json TEXT NOT NULL,        -- full resolved ruleset document
  source_file TEXT, checksum TEXT
);

CREATE TABLE ruleset_bans (
  ruleset_id TEXT NOT NULL REFERENCES rulesets(ruleset_id) ON DELETE CASCADE,
  entity_type TEXT NOT NULL,        -- species|form|move|ability|item|type|tag
  entity_key  TEXT NOT NULL,
  scope TEXT NOT NULL DEFAULT 'global'
     CHECK (scope IN ('global','npc','player','boss_only','rematch_only',
                      'postgame_only','doubles_only','singles_only')),
  reason TEXT,
  PRIMARY KEY (ruleset_id, entity_type, entity_key, scope)
);

-- ─────────── trainer specs ───────────
CREATE TABLE trainer_specs (
  trainer_id TEXT PRIMARY KEY,
  name TEXT NOT NULL, trainer_class TEXT, location TEXT, story_role TEXT,
  battle_format TEXT NOT NULL DEFAULT 'single'
     CHECK (battle_format IN ('single','double','multi','scripted')),
  trainer_tier TEXT NOT NULL
     CHECK (trainer_tier IN ('tutorial','route','rival','mini_boss','gym_leader',
                             'villain_admin','elite_four','champion','rematch','optional_boss')),
  stage_id TEXT REFERENCES progression_stages(stage_id),
  ruleset_id TEXT REFERENCES rulesets(ruleset_id),
  difficulty_target TEXT NOT NULL
     CHECK (difficulty_target IN ('intentionally_weak','easy','fair','challenging',
                                  'difficult','boss')),
  ai_level TEXT NOT NULL DEFAULT 'vanilla'
     CHECK (ai_level IN ('dumb','vanilla','improved','scripted')),
  ai_flags TEXT,                 -- JSON array of engine AI script flags
  team_size_min INTEGER NOT NULL DEFAULT 1,
  team_size_max INTEGER NOT NULL DEFAULT 6,
  level_min INTEGER NOT NULL, level_max INTEGER NOT NULL,
  rematch_stage INTEGER NOT NULL DEFAULT 0,
  battle_lesson TEXT,
  theme_tags TEXT,               -- JSON array
  constraints_json TEXT,         -- required/forbidden species/types/moves/abilities
  export_symbol TEXT,            -- TRAINER_GYM_04
  party_id INTEGER,
  source_file TEXT
);

-- ─────────── generated output ───────────
CREATE TABLE generated_teams (
  team_id TEXT PRIMARY KEY,
  trainer_id TEXT NOT NULL REFERENCES trainer_specs(trainer_id),
  ruleset_id TEXT NOT NULL REFERENCES rulesets(ruleset_id),
  variant TEXT NOT NULL CHECK (variant IN ('easier','standard','harder')),
  build_id TEXT NOT NULL, seed INTEGER NOT NULL,
  archetype TEXT,
  team_score REAL, score_breakdown TEXT,       -- JSON
  difficulty_band TEXT, difficulty_score REAL,
  counterplay_score REAL, counterplay_json TEXT,
  legality_json TEXT, warnings_json TEXT,
  rationale_md TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE generated_team_members (
  team_member_id INTEGER PRIMARY KEY,
  team_id TEXT NOT NULL REFERENCES generated_teams(team_id) ON DELETE CASCADE,
  slot INTEGER NOT NULL,
  form_id TEXT NOT NULL REFERENCES forms(form_id),
  level INTEGER NOT NULL,
  ability_slug TEXT REFERENCES abilities(ability_slug),
  item_slug TEXT REFERENCES items(item_slug),
  nature TEXT, ivs TEXT, evs TEXT,
  assigned_role TEXT,
  pokemon_score REAL, score_breakdown TEXT,
  is_ace INTEGER NOT NULL DEFAULT 0,
  UNIQUE (team_id, slot)
);

CREATE TABLE generated_movesets (
  team_member_id INTEGER NOT NULL REFERENCES generated_team_members(team_member_id) ON DELETE CASCADE,
  move_slot INTEGER NOT NULL CHECK (move_slot BETWEEN 1 AND 4),
  move_slug TEXT NOT NULL REFERENCES moves(move_slug),
  learn_method TEXT NOT NULL, learn_level INTEGER,
  role_purpose TEXT,          -- stab|coverage|utility|setup|filler
  PRIMARY KEY (team_member_id, move_slot)
);

-- ─────────── validation ───────────
CREATE TABLE validation_issues (
  issue_id INTEGER PRIMARY KEY,
  build_id TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('error','warning','info')),
  code TEXT NOT NULL,
  entity_type TEXT, entity_key TEXT, field_path TEXT,
  ruleset_id TEXT, stage_id TEXT, trainer_id TEXT,
  message TEXT NOT NULL, suggestion TEXT,
  detected_at TEXT NOT NULL
);
CREATE INDEX ix_issue_sev ON validation_issues(severity, code);
