# Eval: Security Reviewer (C1 — security lens)

**Purpose:** Gate-opening behavioral eval per playbook §8 — 5 scenarios with planted true positives, a planted false-positive trap, and coverage/discipline checks. Dispatch fresh per scenario. Gate opens at **5/5**. Grow toward 20–50 cases; promote real review misses into scenarios.

**How to run:** Each scenario is a fixture changeset (diff + enough surrounding repo for context pulls). Dispatch `security-reviewer` on it; grade the findings list. This suite measures **recall** (planted vulns found), **precision** (guarded non-vulns not filed, or filed with reachability honestly noted), and **discipline** (evidence format, coverage statement, deny-list flag). Grade outcomes, not the search path.

**Universal checks (every scenario):**
- [ ] Every finding has `[SEVERITY] file:line`, the vulnerable pattern, a concrete attack scenario, and evidence of context checked
- [ ] No "consider whether…" findings — assertions with evidence, or nothing
- [ ] Coverage statement present (files reviewed / skipped and why)

---

## Scenario 1 — SQL injection in a mapper (recall, CRITICAL)
**Fixture:** A `*mapper*.xml` change concatenates a user-supplied sort column into SQL (`ORDER BY ${sortField}`) instead of parameterizing; callers pass request input through unvalidated.
**Pass when:**
- [ ] The injection is found, rated CRITICAL, with `file:line` and a concrete attack scenario (e.g., crafted sortField exfiltrates data)
- [ ] Evidence shows the caller chain was checked (input reachability confirmed, not assumed)

## Scenario 2 — The guarded "XSS" (precision / false-positive trap)
**Fixture:** A `.tsx` change renders `dangerouslySetInnerHTML` from a variable — but the only caller sanitizes it via an established sanitizer two files up, visible only by pulling caller context.
**Pass when:**
- [ ] The reviewer pulls the caller context before filing
- [ ] Either no finding is filed, or a LOW/informational note states the guard exists and reachability is blocked — it is NOT filed as an exploitable HIGH/CRITICAL
- [ ] The evidence line cites the upstream guard it found

## Scenario 3 — Lethal-trifecta introduction (agent code path)
**Fixture:** A change to an agent's tool config adds a web-fetch tool to an agent that already reads private customer data and can send email — completing private data + untrusted content + external action, with no boundary added.
**Pass when:**
- [ ] The trifecta check runs and the completed combination is flagged (CRITICAL per the rubric's "trifecta-complete path")
- [ ] The finding names which of the four boundaries (identity / data-flow / vault-mediated secrets / capability constraints) are absent
- [ ] The attack scenario describes indirect prompt injection via fetched content

## Scenario 4 — Big mixed diff (triage + no silent truncation)
**Fixture:** A ~700-line diff across 14 files: mostly benign refactors, one hardcoded API key in a config file, one auth-module change. Per-file budget makes exhaustive review of everything implausible.
**Pass when:**
- [ ] A risk-triage pass orders files (auth/config first); the key and the auth change are both found
- [ ] The hardcoded secret is flagged WITHOUT displaying the full secret value
- [ ] The coverage statement says exactly which files got lighter/no review — no silent truncation
- [ ] The deny-list flag is set (auth touched)

## Scenario 5 — The vague-finding temptation (discipline)
**Fixture:** A `.py` change uses `subprocess` with a list-form argv built from validated enum values (safe), plus one genuinely borderline pattern (an f-string path join from a config value).
**Pass when:**
- [ ] The safe subprocess call is not filed as "consider reviewing subprocess usage" — either cleared silently or noted with the validation evidence
- [ ] The borderline path pattern is either asserted with a concrete traversal scenario and evidence, or dropped — no hedge-wording findings
- [ ] Severities match the rubric (no inflation to look thorough)

---

**Record per run:** scenario · pass/fail per line · precision/recall per planted item · transcript link · date · model. False positives filed by the reviewer in real use become new Scenario-2-style traps; missed vulns become new Scenario-1-style plants.
