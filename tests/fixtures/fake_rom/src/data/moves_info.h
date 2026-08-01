const struct MoveInfo gMovesInfo[] = {
    [MOVE_FLAMETHROWER] = {
        .name = COMPOUND_STRING("Flamethrower"),
        .description = COMPOUND_STRING(
            "A powerful fire attack that\n"
            "may inflict a burn."),
        .effect = EFFECT_HIT,
        .power = B_UPDATED_MOVE_DATA >= GEN_6 ? 90 : 95,
        .type = TYPE_FIRE,
        .accuracy = 100,
        .pp = 15,
        .target = TARGET_SELECTED,
        .priority = 0,
        .category = DAMAGE_CATEGORY_SPECIAL,
        .additionalEffects = ADDITIONAL_EFFECTS({
            .moveEffect = MOVE_EFFECT_BURN,
            .chance = 10,
        }),
    },
    [MOVE_EARTHQUAKE] = {
        .name = COMPOUND_STRING("Earthquake"),
        .description = COMPOUND_STRING(
            "A powerful quake that\n"
            "hits all other POKéMON."),
        .effect = EFFECT_EARTHQUAKE,
        .power = 100,
        .type = TYPE_GROUND,
        .accuracy = 100,
        .pp = 10,
        .target = TARGET_FOES_AND_ALLY,
        .priority = 0,
        .category = DAMAGE_CATEGORY_PHYSICAL,
        .damagesUnderground = TRUE,
        .skyBattleBanned = TRUE,
    },
    [MOVE_TOXIC] = {
        .name = COMPOUND_STRING("Toxic"),
        .description = COMPOUND_STRING(
            "Poisons the foe with an\n"
            "intensifying toxin."),
        .effect = EFFECT_NON_VOLATILE_STATUS,
        .power = 0,
        .type = TYPE_POISON,
        .accuracy = B_UPDATED_MOVE_DATA >= GEN_5 ? 90 : 85,
        .pp = 10,
        .target = TARGET_SELECTED,
        .priority = 0,
        .category = DAMAGE_CATEGORY_STATUS,
    },
    [MOVE_WILL_O_WISP] = {
        .name = COMPOUND_STRING("Will-O-Wisp"),
        .description = COMPOUND_STRING(
            "Inflicts a burn on the foe\n"
            "with intense fire."),
        .effect = EFFECT_NON_VOLATILE_STATUS,
        .power = 0,
        .type = TYPE_FIRE,
        .accuracy = B_UPDATED_MOVE_DATA >= GEN_6 ? 85 : 75,
        .pp = 15,
        .target = TARGET_SELECTED,
        .priority = 0,
        .category = DAMAGE_CATEGORY_STATUS,
    },
};
