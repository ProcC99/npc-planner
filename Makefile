.PHONY: lint typecheck schema-check test-unit test-int hooks-check check gate fresh golden-update hooks review-bundle

# ---- Bundle review artifacts ----
review-bundle:
	bash scripts/review_bundle.sh

hooks-check:
	python3 scripts/check_hooks_installed.py

# ---- Rung 1: static ----
lint:
	python3 -m ruff check src tests scripts
	python3 -m ruff format --check src tests scripts

# ---- Rung 2: contract ----
typecheck:
	python3 -m mypy --strict src/npc_planner

# ---- Rung 2b: anti-drift ----
schema-check:
	python3 scripts/check_schema_manifest.py

# ---- Rung 3/4: tests ----
test-unit:
	python3 -m pytest tests/unit -q --maxfail=1

test-int:
	python3 -m pytest tests/integration -q --maxfail=1

# ---- The gate every commit must pass ----
check: hooks-check lint typecheck test-unit test-int schema-check
	@echo "check green"

# ---- Working-tree gate (Correction G) ----
gate:
	python3 scripts/check_hooks_installed.py
	python3 -m ruff format --check src tests scripts
	python3 -m ruff check src tests scripts
	python3 -m mypy --strict src/npc_planner
	python3 -m pytest tests/unit -q
	python3 -m pytest tests/integration -q
	python3 scripts/check_schema_manifest.py
	python3 -m pre_commit run --all-files

# ---- Reproducibility: build twice, compare hashes ----
fresh:
	@rm -f data/processed/planner.db
	@npc-planner data build --strict
	@sha256sum data/processed/planner.db | cut -d' ' -f1 > /tmp/npcp_a
	@rm -f data/processed/planner.db
	@npc-planner data build --strict
	@sha256sum data/processed/planner.db | cut -d' ' -f1 > /tmp/npcp_b
	@diff /tmp/npcp_a /tmp/npcp_b > /dev/null \
		&& echo "build reproducible" \
		|| (echo "BUILD NOT REPRODUCIBLE"; exit 1)

# ---- HUMAN APPROVAL REQUIRED ----
golden-update:
	@test "$(APPROVE)" = "yes" || (echo "Refusing. Run: make golden-update APPROVE=yes"; exit 1)
	python3 -m pytest tests/golden --snapshot-update
	@echo "Now review 'git diff tests/golden' line by line before committing."

hooks:
	python3 -m pre_commit install --install-hooks --hook-type pre-commit --hook-type commit-msg
