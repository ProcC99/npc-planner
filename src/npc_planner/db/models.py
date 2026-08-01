from typing import Literal

from pydantic import BaseModel, Field, field_validator

type SourceType = Literal[
    "official_baseline",
    "rom_extract",
    "hack_override",
    "explicit_custom",
    "inferred",
    "unknown",
]
type DamageClass = Literal["physical", "special", "status"]
type TargetMode = Literal[
    "selected",
    "both_foes",
    "all_others",
    "user",
    "user_side",
    "foe_side",
    "field",
    "random_foe",
    "ally",
    "user_or_ally",
    "scripted",
]
type CategorySource = Literal["gen3_type_based", "phys_spec_split", "custom_override"]
type AISafety = Literal[
    "safe_vanilla",
    "safe_improved",
    "requires_scripted",
    "unsafe",
    "unknown",
]
type LearnMethod = Literal["level_up", "tm", "hm", "tutor", "egg", "event", "custom"]
type TMKind = Literal["tm", "hm", "tutor"]
type GrindingExpectation = Literal["discouraged", "normal", "expected"]
type BanScope = Literal[
    "global",
    "npc",
    "player",
    "boss_only",
    "rematch_only",
    "postgame_only",
    "doubles_only",
    "singles_only",
]
type BattleFormat = Literal["single", "double", "multi", "scripted"]
type TrainerTier = Literal[
    "tutorial",
    "route",
    "rival",
    "mini_boss",
    "gym_leader",
    "villain_admin",
    "elite_four",
    "champion",
    "rematch",
    "optional_boss",
]
type DifficultyTarget = Literal[
    "intentionally_weak", "easy", "fair", "challenging", "difficult", "boss"
]
type AILevel = Literal["dumb", "vanilla", "improved", "scripted"]
type TeamVariant = Literal["easier", "standard", "harder"]
type IssueSeverity = Literal["error", "warning", "info"]
type AIRelevance = Literal["none", "passive", "reactive", "requires_scripting"]
type Availability = Literal[
    "regular",
    "hidden",
    "boss_only",
    "rematch_only",
    "custom",
    "unavailable",
]


class BuildInfoRow(BaseModel):
    build_id: str
    built_at: str
    tool_version: str
    baseline_version: str | None = None
    hack_name: str | None = None
    hack_version: str | None = None
    engine: str | None = None
    source_manifest: str


class ProvenanceRow(BaseModel):
    provenance_id: int | None = None
    entity_type: str
    entity_key: str
    field_path: str
    source_type: SourceType
    source_file: str | None = None
    source_version: str | None = None
    source_record: str | None = None
    value_hash: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    verification_status: str = "unknown"
    last_verified_at: str | None = None
    verified_by: str | None = None
    conflicts_with: str | None = None
    notes: str | None = None


class TypeRow(BaseModel):
    type_slug: str
    type_name: str
    rom_type_id: int | None = None
    enabled: int = 1
    is_custom: int = 0
    gen3_damage_class: Literal["physical", "special"] | None = None
    aliases: str | None = None
    implementation_status: str = "confirmed"
    verification_status: str = "confirmed"
    notes: str | None = None


class TypeMatchupRow(BaseModel):
    attacking_type: str
    defending_type: str
    multiplier: float
    chart_version: str = "hack_default"
    differs_from_baseline: int = 0
    verification_status: str = "baseline_only"

    @field_validator("multiplier")
    @classmethod
    def validate_multiplier(cls, v: float) -> float:
        allowed = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)
        if v not in allowed:
            raise ValueError(f"Multiplier must be one of {allowed}, got {v}")
        return v


class SpeciesRow(BaseModel):
    species_slug: str
    species_name: str
    natdex_no: int | None = None
    family_root: str | None = None
    is_custom: int = 0
    implementation_status: str = "baseline_only"
    verification_status: str = "baseline_only"
    notes: str | None = None


class FormRow(BaseModel):
    form_id: str
    species_slug: str
    form_name: str = "base"
    is_default: int = 1
    rom_species_id: int | None = None
    sprite_id: str | None = None
    engine_symbol: str | None = None
    type_1: str
    type_2: str | None = None
    base_hp: int
    base_atk: int
    base_def: int
    base_spa: int
    base_spd: int
    base_spe: int
    bst: int | None = None
    evolution_stage: int | None = None
    is_fully_evolved: int | None = None
    gender_ratio: str | None = None
    catch_rate: int | None = None
    exp_yield: int | None = None
    growth_rate: str | None = None
    implementation_status: str = "baseline_only"
    verification_status: str = "baseline_only"
    confidence: float = 0.3
    notes: str | None = None


class AbilityRow(BaseModel):
    ability_slug: str
    ability_name: str
    rom_ability_id: int | None = None
    engine_symbol: str | None = None
    description: str | None = None
    trigger_conditions: str | None = None
    battle_effects: str | None = None
    grants_type_immunity: str | None = None
    damage_modifiers: str | None = None
    stat_modifiers: str | None = None
    weather_interaction: str | None = None
    terrain_interaction: str | None = None
    status_interaction: str | None = None
    hazard_interaction: str | None = None
    switch_interaction: str | None = None
    recovery_interaction: str | None = None
    contact_interaction: str | None = None
    item_interaction: str | None = None
    move_interaction: str | None = None
    changes_type_matchups: int = 0
    changes_role_class: int = 0
    creates_team_synergy: int = 0
    requires_advanced_ai: int = 0
    ai_relevance: AIRelevance | None = None
    is_custom: int = 0
    implementation_status: str = "baseline_only"
    verification_status: str = "baseline_only"
    confidence: float = 0.3
    notes: str | None = None


class AbilityTagRow(BaseModel):
    ability_slug: str
    tag: str


class FormAbilityRow(BaseModel):
    form_id: str
    slot: int
    ability_slug: str
    availability: Availability = "regular"
    implementation_status: str = "baseline_only"
    verification_status: str = "baseline_only"


class MoveRow(BaseModel):
    move_slug: str
    move_name: str
    rom_move_id: int | None = None
    engine_symbol: str | None = None
    type_slug: str
    power: int | None = None
    accuracy: int | None = None
    pp: int = 5
    priority: int = 0
    target_mode: TargetMode = "selected"
    damage_class: DamageClass
    category_source: CategorySource = "gen3_type_based"
    effect_id: str | None = None
    effect_params: str | None = None
    secondary_chance: int = 0
    recoil_pct: int = 0
    drain_pct: int = 0
    crit_stage: int = 0
    min_hits: int | None = None
    max_hits: int | None = None
    charge_turn: int = 0
    recharge_turn: int = 0
    flag_contact: int = 0
    flag_sound: int = 0
    flag_punch: int = 0
    flag_bite: int = 0
    flag_bullet: int = 0
    flag_slicing: int = 0
    flag_wind: int = 0
    flag_powder: int = 0
    protect_affected: int = 1
    bypasses_substitute: int = 0
    magic_coat_affected: int = 0
    snatch_affected: int = 0
    kings_rock_affected: int = 0
    ai_utility_class: str | None = None
    ai_safety: AISafety = "unknown"
    generation_source: str | None = None
    is_custom: int = 0
    implementation_status: str = "baseline_only"
    verification_status: str = "baseline_only"
    confidence: float = 0.3
    notes: str | None = None


class MoveTagRow(BaseModel):
    move_slug: str
    tag: str
    source: str = "inferred"


class LearnsetRow(BaseModel):
    learnset_id: int | None = None
    form_id: str
    move_slug: str
    method: LearnMethod
    level: int | None = None
    source_ref: str | None = None
    npc_only: int = 0
    implementation_status: str = "baseline_only"
    verification_status: str = "baseline_only"


class TMDefinitionRow(BaseModel):
    tm_code: str
    kind: TMKind
    move_slug: str
    player_available_stage: str | None = None
    npc_available_stage: str | None = None
    reusable: int = 0
    implementation_status: str = "baseline_only"
    verification_status: str = "baseline_only"


class EvolutionRow(BaseModel):
    evolution_id: int | None = None
    from_form_id: str
    to_form_id: str
    method: str
    level: int | None = None
    condition_param: str | None = None
    implementation_status: str = "baseline_only"
    verification_status: str = "baseline_only"


class ItemRow(BaseModel):
    item_slug: str
    item_name: str
    rom_item_id: int | None = None
    engine_symbol: str | None = None
    category: str | None = None
    effect_text: str | None = None
    battle_effect: str | None = None
    consumable: int = 0
    player_available_stage: str | None = None
    npc_available_stage: str | None = None
    boss_only: int = 0
    ai_usable: int = 1
    implementation_status: str = "baseline_only"
    verification_status: str = "baseline_only"
    confidence: float = 0.3


class EncounterRow(BaseModel):
    encounter_id: int | None = None
    form_id: str
    location: str
    method: str
    min_level: int | None = None
    max_level: int | None = None
    rate: float | None = None
    stage_id: str | None = None
    implementation_status: str = "baseline_only"
    verification_status: str = "baseline_only"


class ProgressionStageRow(BaseModel):
    stage_id: str
    ordinal: int
    label: str
    expected_player_level_min: int
    expected_player_level_max: int
    expected_party_size: int
    expected_species: str | None = None
    expected_move_pool: str | None = None
    available_tms: str | None = None
    available_tutors: str | None = None
    available_items: str | None = None
    healing_available: int = 1
    battle_items_allowed: int = 1
    grinding_expectation: GrindingExpectation = "normal"
    notes: str | None = None


class FormAvailabilityRow(BaseModel):
    form_id: str
    stage_id: str
    player_available: int = 0
    npc_available: int = 0
    min_level: int | None = None
    max_level: int | None = None
    boss_only: int = 0
    rematch_only: int = 0
    postgame_only: int = 0


class FormTagRow(BaseModel):
    form_id: str
    tag: str
    source: str = "inferred"


class RulesetRow(BaseModel):
    ruleset_id: str
    label: str
    extends: str | None = None
    config_json: str
    source_file: str | None = None
    checksum: str | None = None


class RulesetBanRow(BaseModel):
    ruleset_id: str
    entity_type: str
    entity_key: str
    scope: BanScope = "global"
    reason: str | None = None


class TrainerSpecRow(BaseModel):
    trainer_id: str
    name: str
    trainer_class: str | None = None
    location: str | None = None
    story_role: str | None = None
    battle_format: BattleFormat = "single"
    trainer_tier: TrainerTier
    stage_id: str | None = None
    ruleset_id: str | None = None
    difficulty_target: DifficultyTarget
    ai_level: AILevel = "vanilla"
    ai_flags: str | None = None
    team_size_min: int = 1
    team_size_max: int = 6
    level_min: int
    level_max: int
    rematch_stage: int = 0
    battle_lesson: str | None = None
    theme_tags: str | None = None
    constraints_json: str | None = None
    export_symbol: str | None = None
    party_id: int | None = None
    source_file: str | None = None


class GeneratedTeamRow(BaseModel):
    team_id: str
    trainer_id: str
    ruleset_id: str
    variant: TeamVariant
    build_id: str
    seed: int
    archetype: str | None = None
    team_score: float | None = None
    score_breakdown: str | None = None
    difficulty_band: str | None = None
    difficulty_score: float | None = None
    counterplay_score: float | None = None
    counterplay_json: str | None = None
    legality_json: str | None = None
    warnings_json: str | None = None
    rationale_md: str | None = None
    created_at: str


class GeneratedTeamMemberRow(BaseModel):
    team_member_id: int | None = None
    team_id: str
    slot: int
    form_id: str
    level: int
    ability_slug: str | None = None
    item_slug: str | None = None
    nature: str | None = None
    ivs: str | None = None
    evs: str | None = None
    assigned_role: str | None = None
    pokemon_score: float | None = None
    score_breakdown: str | None = None
    is_ace: int = 0


class GeneratedMovesetRow(BaseModel):
    team_member_id: int
    move_slot: int = Field(ge=1, le=4)
    move_slug: str
    learn_method: str
    learn_level: int | None = None
    role_purpose: str | None = None


class ValidationIssueRow(BaseModel):
    issue_id: int | None = None
    build_id: str
    severity: IssueSeverity
    code: str
    entity_type: str | None = None
    entity_key: str | None = None
    field_path: str | None = None
    ruleset_id: str | None = None
    stage_id: str | None = None
    trainer_id: str | None = None
    message: str
    suggestion: str | None = None
    detected_at: str
