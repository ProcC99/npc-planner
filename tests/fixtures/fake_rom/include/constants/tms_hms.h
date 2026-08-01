#ifndef GUARD_CONSTANTS_TMS_HMS_H
#define GUARD_CONSTANTS_TMS_HMS_H

// Present for M1-T16 (teachable learnsets). M1-T10 does not read this file;
// it is added now so the fixture grows exactly once rather than twice.
#define FOREACH_TM(F) \
    F(FOCUS_PUNCH)    \
    F(DRAGON_CLAW)    \
    F(WATER_PULSE)    \
    F(CALM_MIND)      \
    F(ROAR)           \
    F(TOXIC)          \
    F(HAIL)           \
    F(BULK_UP)

#define FOREACH_HM(F) \
    F(CUT)            \
    F(FLY)            \
    F(SURF)

#endif // GUARD_CONSTANTS_TMS_HMS_H
