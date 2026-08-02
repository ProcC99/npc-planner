# Remote Publishing & Review Trace Protocol

This document defines the rules and operational procedures for remote repository publishing and automated review tracing.

## 1. Repository Accessibility
- **Public Visibility Required**: The remote repository (`https://github.com/ProcC99/npc-planner`) MUST remain public. A private repository breaks external reviewer access and defeats automated verification.

## 2. Authentication Scoping
- **Repo-Local Only**: Authentication is configured exclusively via `git config --local core.sshCommand`.
- **No Credentials in URLs**: Personal access tokens or embedded credentials in remote URLs are strictly prohibited.
- **No Global Mutations**: Global or user-level SSH configuration (`~/.ssh/*`, `~/.gitconfig`) must never be modified by automated agents.

## 3. Fixed Push Targets
- **Target Branches**: Only `main`, `milestone/*`, and tags may be pushed to `origin`.
- **Timing**: Pushes occur only immediately after a task or milestone merge, or as directed by task procedures.

## 4. Strict Non-Fast-Forward / Force Push Rules
- **Force Push Prohibited**: `--force`, `-f`, or `--force-with-lease` are strictly prohibited on `main` and `milestone/*`.
- **Push Rejection as Evidence**: If a push is rejected as non-fast-forward, the agent must STOP and report `PUSH_REJECTED_NON_FF` along with local and remote SHAs. Never rebase, amend, or reset to force a push. A rejected push is evidence, not an obstacle (§11.15).

## 5. Tagging Standard
- **Format**: Annotated tags named `done/<TASK_ID>` pointing directly to the commit SHA recorded in `docs/LEDGER.md`.
- **Immutability**: Tags must never be moved, deleted, or re-created once pushed.

## 6. Execution Report Format
- Every publishing action concludes with the standardized `PUSHED` status block containing verification counts for unit tests, integration tests, mypy coverage, acceptance suites, and audit results.

## 7. Working-Tree Boundary (Prime Directive)
- Agents MUST NOT create, modify, or chmod any file outside the repository working tree. If an operation appears to require out-of-tree changes, stop and report `OUT_OF_TREE_CHANGE_REQUIRED`.
