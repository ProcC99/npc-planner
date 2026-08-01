const struct MoveInfo gMovesInfo[] = {
    [MOVE_FLAMETHROWER] = {
        .name = _("Flamethrower"),
        .type = TYPE_FIRE,
        .power = 95,
        .accuracy = 100,
        .pp = 15,
        .target = MOVE_TARGET_SELECTED,
        .split = SPLIT_SPECIAL,
    },
    [MOVE_EARTHQUAKE] = {
        .name = _("Earthquake"),
        .type = TYPE_GROUND,
        .power = 100,
        .accuracy = 100,
        .pp = 10,
        .target = MOVE_TARGET_FOES_AND_ALLY,
        .split = SPLIT_PHYSICAL,
    },
};
