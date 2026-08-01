const struct SpeciesInfo gSpeciesInfo[] = {
    [SPECIES_SKARMORY] = {
        .speciesName = _("Skarmory"),
        .natDexNum = NATIONAL_DEX_SKARMORY,
        .baseHP = 65,
        .baseAttack = 80,
        .baseDefense = 140,
        .baseSpAttack = 40,
        .baseSpDefense = 70,
        .baseSpeed = 70,
        .types = {TYPE_STEEL, TYPE_FLYING},
        .abilities = {ABILITY_KEEN_EYE, ABILITY_STURDY, ABILITY_WEAK_ARMOR},
    },
#if P_GEN_9_POKEMON == TRUE
    [SPECIES_GEN9_GUARD] = {
        .speciesName = _("Gen9Guard"),
        .natDexNum = 999,
        .baseHP = 100,
        .baseAttack = 100,
        .baseDefense = 100,
        .baseSpAttack = 100,
        .baseSpDefense = 100,
        .baseSpeed = 100,
        .types = {TYPE_NORMAL, TYPE_NORMAL},
        .abilities = {ABILITY_NONE, ABILITY_NONE, ABILITY_NONE},
    },
#endif
};
