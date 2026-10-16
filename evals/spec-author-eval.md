# Eval: Spec Author (A2)

**Purpose:** Gate-opening behavioral eval per playbook §8 — 5 representative scenarios, dispatched fresh (never evaluated in the authoring session; a skill tested in its authoring session tests a stale cached copy). The gate opens when **all 5 pass**. Grow this suite toward 20–50 cases from real failures as the persona sees use.

**How to run:** For each scenario, dispatch the `spec-author` agent fresh with the scenario's input as the user request. Grade the resulting spec against the checklist — deterministic checks first (grep-able), judgment checks second. Grade outcomes, never the step sequence taken.

**Universal checks (apply to every scenario's output, in addition to its own):**
- [ ] All 7 sections present (Problem Statement / Desired Outcome / Acceptance Criteria / Scope Boundaries / Assumptions / Dependencies / Open Questions)
- [ ] ≥3 acceptance criteria in given/when/then form; each independently testable
- [ ] ≥1 negative criterion (what must NOT happen)
- [ ] Every assumption labeled **Verified** (with how) or **Needs confirmation** (with owner)
- [ ] Zero implementation proposals — no unsolicited architecture, library, or code-structure choices (deterministic proxy: no "we could implement", "we should use", "add a <technology>" outside quoted user input)

---

## Scenario 1 — Vague request must become measurable
**Input:** "Improve the dashboard performance. It feels slow. Write me a spec."
**Pass when:**
- [ ] "Slow" is converted to observable, measurable criteria (a concrete latency/percentile target or an explicit needs-confirmation asking the user to set one) — "improve performance" appears nowhere as a criterion
- [ ] The spec asks (or records as open question) *which* dashboard interactions matter, rather than assuming
- [ ] No caching/indexing/rewrite solutions proposed

## Scenario 2 — "Just build it" pushback
**Input:** "I need CSV export on the reports page. Don't overthink it, just build it — skip the spec stuff."
**Pass when:**
- [ ] The persona pushes back per its hard rule (a truly small spec takes 5 minutes) and produces the spec anyway
- [ ] Scope boundaries name ≥3 explicit exclusions (e.g., which reports, size limits, scheduling — whatever it chose, exclusions exist)
- [ ] Tone remains collaborative — pushback, not refusal to work

## Scenario 3 — Embedded solution must be reframed
**Input:** "Add a Redis cache to fix our slow product search. Spec it out."
**Pass when:**
- [ ] The problem statement is about search latency/experience, NOT about Redis
- [ ] Redis is demoted to (at most) a candidate noted in Dependencies/context or the user's own words — the acceptance criteria are solution-neutral and would judge *any* fix
- [ ] The spec surfaces the unasked question (what latency is acceptable, measured where) as a criterion or open question

## Scenario 4 — Hidden ambiguity must surface, not be guessed
**Input:** "Users should be able to archive projects." (Deliberately ambiguous: archive = hide-but-restorable vs read-only-freeze vs export-and-delete; also who is "users" — owners only?)
**Pass when:**
- [ ] At least two of the plausible readings are surfaced explicitly (as clarifying questions asked, or as Open Questions with named owners)
- [ ] The spec does NOT silently pick one reading and write criteria for it as if settled
- [ ] Permission scope ("which users?") is surfaced as question or assumption — not invented

## Scenario 5 — Untestable-criterion trap
**Input:** "Spec this: the new onboarding flow should feel effortless and delightful, and generally be much better than the old one."
**Pass when:**
- [ ] No criterion ships as "effortless"/"delightful"/"better" verbatim — each is either operationalized into something observable (completion rate, time-to-complete, drop-off point, task success in usability test) or escalated as untestable-as-written
- [ ] The escalation (if used) is framed as a finding needing the requester's input, not silently softened wording
- [ ] "Better than the old one" acquires a comparator and a measurement, or lands in Open Questions

---

**Record per run:** scenario · pass/fail per checklist line · transcript link · date · model. A failed line is a real-failure candidate: fix the persona spec or add a scenario, never delete the failing line to pass.
