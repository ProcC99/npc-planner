#!/usr/bin/env bash
# scripts/review_bundle.sh
#
# Produce a single artifact containing everything needed to review a task
# without re-running anything. Invoked by `make review-bundle`.
#
# The point of this script is that it captures raw output. A summary written
# afterwards is a second-hand account; this is the primary record.
#
# Usage:
#   make review-bundle                  # diff against milestone/M1
#   BASE=main make review-bundle        # diff against something else
#   TASK=M1-T11 make review-bundle      # name the acceptance script to run

set -uo pipefail

BASE="${BASE:-milestone/M1}"
TASK="${TASK:-}"
OUT_DIR="${OUT_DIR:-build/review}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
NAME="review-${TASK:-head}-${STAMP}"
WORK="${OUT_DIR}/${NAME}"

mkdir -p "${WORK}"

echo "review bundle: ${NAME}"
echo "base: ${BASE}"

# ---------------------------------------------------------------- git ------

{
  echo "# branch"
  git rev-parse --abbrev-ref HEAD
  echo
  echo "# head"
  git log -1 --format='%H%n%s%n%an%n%aI'
  echo
  echo "# working tree"
  git status --short
  echo
  echo "# base"
  git rev-parse "${BASE}" 2>/dev/null || echo "base not resolvable: ${BASE}"
} > "${WORK}/00-git-state.txt" 2>&1

git log --oneline --stat "${BASE}..HEAD" \
  > "${WORK}/01-git-log.txt" 2>&1

# Full diff, not truncated. If this is large, that is itself review signal.
git diff "${BASE}...HEAD" \
  > "${WORK}/02-git-diff.patch" 2>&1

git diff --name-only "${BASE}...HEAD" \
  > "${WORK}/03-changed-files.txt" 2>&1

# ---------------------------------------------------------------- gate -----

echo "running make gate ..."
make gate > "${WORK}/04-make-gate.txt" 2>&1
GATE_RC=$?
echo "exit=${GATE_RC}" >> "${WORK}/04-make-gate.txt"

# The gate and the hooks must agree. Captured separately and immediately
# after, because a disagreement here has cost this project two whole tasks.
echo "running pre-commit run --all-files ..."
python3 -m pre_commit run --all-files > "${WORK}/05-pre-commit.txt" 2>&1
echo "exit=$?" >> "${WORK}/05-pre-commit.txt"

# ---------------------------------------------------------- acceptance -----

if [ -n "${TASK}" ] && [ -f "scripts/accept/${TASK}.sh" ]; then
  echo "running acceptance for ${TASK} ..."
  bash "scripts/accept/${TASK}.sh" > "${WORK}/06-acceptance.txt" 2>&1
  echo "exit=$?" >> "${WORK}/06-acceptance.txt"
else
  echo "no acceptance script run (TASK unset or missing)" \
    > "${WORK}/06-acceptance.txt"
fi

# --------------------------------------------------------------- audit -----

python3 scripts/audit_commits.py --range "${BASE}" \
  > "${WORK}/07-audit.txt" 2>&1
echo "exit=$?" >> "${WORK}/07-audit.txt"

cp docs/LEDGER.md "${WORK}/08-LEDGER.md" 2>/dev/null \
  || echo "docs/LEDGER.md missing" > "${WORK}/08-LEDGER.md"

# --------------------------------------------------------------- pack ------

ZIP="${OUT_DIR}/${NAME}.zip"
rm -f "${ZIP}"
( cd "${OUT_DIR}" && zip -qr "${NAME}.zip" "${NAME}" )

echo
echo "wrote ${ZIP}"
ls -l "${ZIP}"
echo
echo "contents:"
unzip -l "${ZIP}" | sed 's/^/  /'
