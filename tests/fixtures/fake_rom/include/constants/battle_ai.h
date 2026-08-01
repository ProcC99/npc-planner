#ifndef GUARD_CONSTANTS_BATTLE_AI_H
#define GUARD_CONSTANTS_BATTLE_AI_H

// Shift expressions are deliberate. A reader that only handles decimal and hex
// literals will silently produce zeros here, which is worse than failing.
#define AI_FLAG_CHECK_BAD_MOVE          (1 << 0)
#define AI_FLAG_TRY_TO_FAINT            (1 << 1)
#define AI_FLAG_CHECK_VIABILITY         (1 << 2)
#define AI_FLAG_SETUP_FIRST_TURN        (1 << 3)
#define AI_FLAG_RISKY                   (1 << 4)
#define AI_FLAG_PREFER_STRONGEST_MOVE   (1 << 5)
#define AI_FLAG_PREFER_BATON_PASS       (1 << 6)
#define AI_FLAG_DOUBLE_BATTLE           (1 << 7)
#define AI_FLAG_HP_AWARE                (1 << 8)
#define AI_FLAG_NEGATE_UNAWARE          (1 << 9)
#define AI_FLAG_WILL_SUICIDE            (1 << 10)
#define AI_FLAG_HELP_PARTNER            (1 << 11)
#define AI_FLAG_OMNISCIENT              (1 << 12)
#define AI_FLAG_SMART_SWITCHING         (1 << 13)
#define AI_FLAG_ACE_POKEMON             (1 << 14)

// A composite defined in terms of other symbols, not a literal.
#define AI_FLAG_BASIC_TRAINER           (AI_FLAG_CHECK_BAD_MOVE | AI_FLAG_TRY_TO_FAINT | AI_FLAG_CHECK_VIABILITY)

// Deliberately not statically evaluable. This must surface as
// W_ROM_EXPR_UNEVALUATED, never as a silent 0 and never as an exception.
#define AI_FLAG_RUNTIME_TUNED           (gBattleTuning->aiMask & AI_FLAG_OMNISCIENT)

#endif // GUARD_CONSTANTS_BATTLE_AI_H
