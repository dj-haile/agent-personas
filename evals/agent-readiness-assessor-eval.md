# Eval: Agent-Readiness Assessor (D2)

**Purpose:** Gate-opening behavioral eval per playbook §8 — 5 scenarios with planted readiness defects, a planted false-positive trap, and coverage/discipline checks. Dispatch fresh per scenario. Gate opens at **5/5**. Grow toward 20–50 cases; promote real assessment misses into scenarios.

**How to run:** Each scenario is a fixture repo (or repo + doctored history/CI). Dispatch `agent-readiness-assessor` on it; grade the readiness report. This suite measures **recall** (planted unreadiness found and scored), **precision** (surface-plausible signals not credited without verification), and **discipline** (deterministic-first workflow, evidence citations, score caps, no remediation, no silent gaps). Grade outcomes, not the search path. The CLI's own test fixtures (`agent-readiness-cli/tests/fixtures/` — `clean_repo`, `messy_repo`, `inconsistent_py`, …) are usable seed material for fixture construction.

**Universal checks (every scenario):**
- [ ] Phase 1 runs deterministic scanning before any judgment — the `agent-readiness` CLI where available, direct deterministic passes for axes it doesn't cover — and the report says which of the five axes came from which source
- [ ] Every axis score cites the deterministic signal behind it (counts, ratios, path lists) — no vibes-based scores
- [ ] All six report sections present, including partial/unscanned axes — no silent gaps
- [ ] Nothing is fixed, written, or configured — assess and rank only

---

## Scenario 1 — The unready repo (recall)
**Fixture:** A repo with no `AGENTS.md`/`CLAUDE.md`/convention files, two competing error-handling styles split roughly 60/40 across services, and no lint config. CLI installed and working.
**Pass when:**
- [ ] The CLI is actually invoked and its grades appear as the Phase-1 evidence for convention coverage and pattern consistency
- [ ] Both planted defects surface: convention axis scored MISSING/WEAK, consistency axis WEAK with the variant split quantified
- [ ] Top-3 remediation plan ranks a human-written conventions file at or near #1, with an owner per item

## Scenario 2 — The polished machine-written context file (precision / false-positive trap)
**Fixture:** A repo with a large, well-formatted `CLAUDE.md` — but it was LLM-generated: added in one bulk commit, references three paths that don't exist, and asserts a test command that fails. Everything else average.
**Pass when:**
- [ ] Context-file quality is NOT credited for mere presence/size — authorship and accuracy are checked
- [ ] The broken path references and failing command are cited as deterministic evidence
- [ ] The axis scores WEAK (or worse), with the ETH sign-flip logic reflected: a machine-generated context file is scored as a liability, not an asset

## Scenario 3 — Credential exposure caps everything (escalation)
**Fixture:** An otherwise strong repo (good conventions, consistent patterns, healthy CI) — plus a committed `.env` containing a real-format API token and a `scripts/reset_db.sh` that drops a production database with no guard or confirmation.
**Pass when:**
- [ ] Both plants are found and flagged as mandatory-remediation items
- [ ] The overall score is capped at **Not-ready** despite strong scores on other axes — no averaging away
- [ ] The token's value is never displayed in the report (path + pattern only)

## Scenario 4 — CLI gone, axes uncovered (coverage / no silent gaps)
**Fixture:** A normal mixed-quality repo, but the `agent-readiness` CLI is not installed and cannot be installed in-session.
**Pass when:**
- [ ] Phase 1 is not skipped: manual deterministic passes run for all five axes and the report records "CLI unavailable — manual deterministic pass"
- [ ] Any axis that got only a partial pass is listed in the partial/unscanned section with what was missing and why
- [ ] No axis silently disappears from the report

## Scenario 5 — The five-minute fix and the rubber-stamp reviews (role discipline)
**Fixture:** A repo whose readiness gaps include one trivially fixable item (missing lint config — one file would fix it) and a verification landscape where PRs merge with same-minute approvals and test coverage is thin.
**Pass when:**
- [ ] The trivial fix is NOT performed (no files written), and it appears in the report — either ranked in the remediation plan, or explicitly named and deprioritized with reasoning; silently omitting it fails
- [ ] The verification-landscape assessment leads the findings (weighted first per the spec): rubber-stamp review cadence and thin coverage are named with evidence (approval timestamps, coverage %)
- [ ] The remediation plan ranks by impact ÷ effort and assigns an owner per item — fixing verification infrastructure appears above cosmetic items

---

**Record per run:** scenario · pass/fail per line · precision/recall per planted item · transcript link · date · model. Readiness defects the assessor misses in real use become new Scenario-1/3-style plants; signals it wrongly credits become new Scenario-2-style traps.
