# Coverage & Gap Audit — Org Agent-Personas Catalog

**Prepared:** July 12, 2026
**Method:** Every persona in `org-agent-personas-catalog.md` was re-grounded against the primary sources it cites — the 14 knowledge-base articles, the 3 pattern docs, the full VP-eng playbook, the project-specs workflow files, the `eval-review-agent.md` spec, the 11 scout-reading analyses, and the multi-agent watchlist — read directly (not via digests). This audit reports two things: **(A) corrections** to fold into the existing catalog so its claims are trustworthy, and **(B) coverage gaps** — jobs-to-be-done the research clearly supports that the catalog has no persona for, tiered by how strongly the evidence backs standing one up.

The headline: the catalog is substantially accurate. Almost every "§N" playbook citation resolves correctly, and the load-bearing numbers (44% agent-code survival, 9× vuln rate, +91%/+98% review-vs-PR, the six-level autonomy ladder, PostHog's qa-swarm, Replit's four gates, 26.1%/5.2% skills supply chain, the ETH context-file swings, the trust/UX figures) all check out against the source text. The issues below are precision fixes and genuine additive gaps — not a rewrite.

---

## Part A — Corrections to fold into the catalog

Ordered by how load-bearing the error is.

**A1. The Alibaba "deterministic checks run before any LLM pass" claim is an overreach (C1).**
The catalog's C1 basis line attributes cost-ordered, deterministic-first backpressure to Alibaba's open review patterns. The Alibaba source explicitly and repeatedly corrects exactly this: its "hybrid architecture" is *only* file-type prompt routing — deciding *which* review prompt to use — with the LLM doing all the actual analysis. There is no static analysis, no AST parsing, no linter/SAST output feeding the review. The true deterministic-first two-pass (run real linters/type-checkers/Semgrep first, feed findings to the LLM) is the **earezki two-pass model** and **single-agent Pattern 1**, not Alibaba. *Fix:* keep the design principle (it's sound and well-sourced), but re-attribute it to earezki/Pattern 1; describe Alibaba as the source of the file-type-aware *routing* and the tool-using reviewer, which it genuinely is.

**A2. "Overconfident AI flips 41.3% of users to the wrong answer" uses the wrong denominator (G1, and the §C intro).**
Source 08 says 41.3% *of the users who switch* move to incorrect advice, given a 69.6% switch rate under overconfidence — i.e. roughly **~29% of all users** actually flip to a wrong answer, not 41.3%. *Fix:* reword to "41.3% of the users who switch move to a wrong answer (≈29% of all users)."

**A3. "Five compartmentalization patterns (§5)" is a mislabel (D1).**
Playbook §5 contains **five security *defense* patterns** (separate data from instructions, capability allowlist, credential isolation, zone-based input handling, audit trail) *and a separate three-part compartmentalization approach* (main agent can't communicate externally; ephemeral subagents can but are container-isolated; no agent holds credentials directly). The catalog fuses the two into "five compartmentalization patterns." *Fix:* name them correctly. Note also that D1's "four architectural boundaries" (identity / data-flow / vault-mediated secrets / capability constraints) is a catalog *synthesis* — it is well-supported by single-agent Pattern 9 and trifecta Patterns 3–6, but it is not a named framework in the playbook; label it as synthesized.

**A4. The two-judge pattern is playbook §4, not §3 (G2).**
The functional-judge + experiential/product-persona-judge pattern lives in §4 "flow-first testing" (Klaassen), not §3. *Fix:* correct the citation. (C2 also invokes two-judge but assigns no section, so it's fine.)

**A5. E3's "matched-pair staleness audits (§3)" is repurposed.**
In the playbook, "matched-pair staleness" is about **harness components rotting when the model is upgraded** (e.g. compaction/checkpointing becoming dead weight) — not doc/CLAUDE.md fact-checking. E3's actual, correct basis is the **ETH Zurich context-file finding** (scout-reading 05). *Fix:* reground E3 on ETH; a model upgrade should *trigger* a doc re-verification pass, but that's re-checking doc accuracy, not auditing harness code. The harness-rot job is real but distinct — see gap B9.

**A6. The Fintool "50× cost range" between model tiers is softer than stated (F2, and the "How to read" model-tiering bullet).**
The source states "50×" in prose, but its own pricing table implies ~6.25× on input tokens (Haiku $0.80 vs Opus $5.00/MTok). The 50× likely folds in output-token or whole-workflow costs that aren't shown. *Fix:* don't present "50×" as a hard input-cost fact; say "up to ~50× effective, ≈6× on input-token price alone."

**A7. C5's reliability-gate thresholds are internally inconsistent in the source.**
ReliabilityBench states pass^3 ≥ 0.90, ε ≤ 0.15, λ ≤ 0.15 in two places but ε ≤ 0.10, λ ≤ 0.10 in its defense-in-depth mapping. *Fix:* present it as a deliberate team choice, defaulting to the stricter 0.10 for high-blast-radius agents. (Handled in the new C5 spec.)

**A8. The model-tiering "How to read" bullet overstates that tier = capability.**
The watchlist's model-role-mismatch finding directly challenges the clean Opus=judgment / Sonnet=analysis / Haiku=classification ladder: "the best model overall may perform worst in a specific agent role" — some top models stop early and take shortcuts in extended autonomous execution, and a lower-tier model can win a specific role. *Fix:* keep tiering as a default, but add the caveat that long-autonomy roles (F1, E2) must validate role-fit rather than assume top tier = best.

**A9. Anti-persona #2's "no at-scale peer proof point exists" is too absolute.**
The watchlist lists Anthropic-attributed *production* examples for the two most peer-like coordination patterns (shared-state research synthesis; message-bus security-ops triage). *Fix:* keep the recommendation (default to single-root hierarchy — still well-supported) but drop the absolutist proof claim. Note: the adjacent "15× token sprawl" figure *is* supported (it's in limit-in-the-loop), so that stays.

**A10. Minor reconciliation — "20–50 real-failure tasks."**
This is correctly attributed to the Anthropic evals analysis (it's real, from the eight-step roadmap). Worth a one-line note that the *playbook's* own starting prescription is smaller — "3–5 representative scenarios per skill" as an initial behavioral gate — so the two aren't in tension: 3–5 to open a gate, 20–50 for a maturing eval suite.

No correction changes a catalog *design principle* — single-root hierarchy, harness-owned governance, vault-mediated credentials, no step-sequence graders, deterministic-before-LLM, append-only logging, and assume-injection-succeeds are all positively supported by the sources.

---

## Part B — Coverage gaps (recommended new personas)

Tiered by evidence strength and how obvious the hole is. Each entry: the job, who uses it, the source, and why it's a *distinct* persona rather than a variant of one already in the catalog.

### Tier 1 — Add now (clear hole, strong single-source evidence, broad usefulness)

**B1. Validation / QA-Runner** — *the missing half of spec-in-the-loop.*
**Job:** verify that an implementation actually matches its approved plan *and* satisfies the spec's acceptance criteria — run every automated check, diff code against the plan, and produce a structured Validation Report (Implementation Status per phase, Matches-Plan / Deviations / Potential Issues, Manual Testing Required). **Who:** every engineer, post-implementation and pre-review. **Source:** project-specs `validate_plan.md` (a first-class Opus command) + Arcplane Findings 1–2. **Why distinct:** the catalog folds validation into C1 (Review Panel), C2 (Refuter), and C3 (Test Designer), but none of those is the "did the implementation conform to the approved plan and the spec" gate. It's the load-bearing second half of Arcplane's spec-in-the-loop thesis and it has no persona. This is the single most glaring omission.

**B2. Context / Token-Economics Auditor** — *the cost architecture nobody owns.*
**Job:** audit and optimize a production agent's context economics — KV-cache hit rate (stable prefix, static tool defs, no sub-second timestamps or request-IDs in the prefix), three-tier token budgeting with compression triggers, the 200K-token pricing cliff, parallel-vs-sequential tool calls, response caching, and complexity-based model routing. **Who:** platform/AI-infra teams and anyone running an agent at real volume. **Source:** two entire articles are about exactly this job — llm-context-tax (Fintool: $0.14/question, "KV-cache hit rate is the single most important metric") and manus context-engineering (10× cached/uncached; cache invalidation treated as an architectural failure). **Why distinct:** C4 audits *evals*, C5 audits *reliability under stress*, F2 measures *org adoption*, C1's performance lens reviews *PRs*. None audits an agent's *context/cost architecture* — which the research treats as the highest-leverage optimization surface after evals. The catalog currently demotes this to "model tiering is a persona attribute," which badly undersells it.

**B3. Team-Maturity Diagnostician / Rollout Coach** — *the org-adoption sequencer.*
**Job:** diagnose each team's current AI-adoption maturity (L1 copy-paste-from-chat → L2 CLI/IDE hand-held → L3 autonomous multi-agent), recommend the next task-type to automate (boilerplate → merge conflicts → flaky tests → bug investigation → prototyping → optimization), and guard against over-use ("AI mania" — a hard attention budget of ≤5 parallel agents, ~10-min correction cycle). **Who:** platform/enablement teams and EMs. **Source:** playbook §3 (ClickHouse/Milovidov) — the playbook's most detailed org-mechanics content, with concrete numbers (700 PRs in 2 months on flaky tests, 28% build-speed win). **Why distinct:** D2 scores *repos*, F2 reports *metrics*; nobody diagnoses *team* adoption maturity or coaches sequencing and restraint.

### Tier 2 — Strong candidates (distinct jobs, add for fuller lifecycle coverage)

**B4. Session-Handoff / Continuity persona.** Emit a structured handoff doc at session end (Summary, Progress checkboxes, Blockers, Files Modified, Next Steps, Open Questions) and restore context at session start. **Who:** multi-developer, multi-session teams. **Source:** workflow-patterns §3 (full schema included). **Why distinct:** not B3 Decision Logger (mid-implementation *why*) nor E3 Groundskeeper (doc truth) — this is inter-session/inter-person *state transfer* with its own artifact.

**B5. Debug / Parallel-Investigation persona.** Spawn parallel investigators (Log Analyzer, Git History, Database, Config) against a production issue and synthesize a hypothesis + remediation. **Who:** anyone doing root-cause analysis. **Source:** workflow-patterns §4. **Why distinct:** E1 (Ticket-to-PR) and E2 (Closed-Loop Improver) are throughput/improvement loops; this is an interactive fan-out-then-synthesize *diagnostic*.

**B6. Comprehension Verifier (quiz-before-merge).** Flip verification: the code verifies the *human's* understanding — generate an HTML change report plus a quiz the human must pass before merging a large agent diff. **Who:** any engineer merging big AI-generated changes. **Source:** playbook §7 technique #7. **Why distinct:** C1/C2 verify the *code/claims*, B3 logs *decisions* — none verifies the *reviewer's* understanding, which is the actual defense against rubber-stamping.

**B7. Preference / Rules Architect.** ✅ **PROMOTED (2026-08-02): now catalog persona E5 with a full spec (`personas/preference-rules-architect.md`) and eval suite.** Original scoping: author and maintain the org's declarative/imperative × strategic/tactical rules structure (strategic-declarative → CLAUDE.md/rules; strategic-imperative → mandatory skills; tactical → project context/skills, the critical 20%). **Who:** platform + team leads. **Source:** playbook §7. **Why distinct:** A1 *elicits* preferences and A2 *specs* a feature; neither owns the standing rules hierarchy that governs every agent session.

**B8. Context-Integrity / Drift & Poisoning Auditor.** Pre-ship audit for the failure modes that compound over a long session: context poisoning (one hallucinated goal referenced at every step), attention drift (tool choice drifting after 50+ turns), position bias, semantic loops — with poisoning-recovery and loop-detection tests. **Who:** platform teams shipping long-horizon or memory-carrying agents. **Source:** limit-in-the-loop (DeepMind poisoned-context; NoLiMa position bias 70–75% → 55–60%; "11 of 12 LLMs drop below 50% of short-context performance at 32k tokens"). **Why distinct:** C5 stresses *external* faults (rate limits, tool failures); this is the agent corrupting its *own* accumulated context. The Memory Hygienist is F1-specific and reactive; this is a general pre-ship audit.

### Tier 3 — Specialized / platform / conditional (add when the need arises)

**B9. Harness-Assumption Auditor** — audit scaffolding/harness code for rot on model upgrade (the *true* "matched-pair staleness"; see correction A5). Platform teams. Source: playbook §3.

**B10. Online-Experiment / Production-Trace Analyst** — run and interpret A/B experiments on prompt/tool/harness/model changes against real users, with trace-level analysis when aggregate metrics don't self-explain. Distinct from F2 (adoption metrics) and E2 (offline eval loop). Source: playbook §4. *(Scope note, added with E4: the Calibration Steward — `personas/calibration-steward.md` — now covers the monitoring/trace-analysis half of this job for high-stakes decisioning systems specifically. If B10 is ever stood up, scope it to general-purpose experimentation on agent changes; the decisioning-calibration lane belongs to E4, keeping one job per persona.)*

**B11. Agent Tool-Surface / Interface Designer** — a *design-time* reviewer choosing each capability's interface (direct API vs CLI vs MCP) and its destructive-action guardrail. Source: scout 03 (20,000× slower LLM DB code; an agent deleting 2.5 years of prod data). Note: this is design-time interface choice, not runtime governance (which stays in the harness per anti-persona #3).

**B12. Agent-Platform / Connector-Governance Architect** — own the MCP/connector *substrate*: transport scalability, capability discovery, gateway/proxy behavior, audit trails, SSO, config portability. Source: scout 04 + watchlist #10.

**B13. Ambient / Listener-Agent Operator** — stand up and govern long-lived agents on event streams (Pub/Sub, inbox, tables) with policy-in-gateway, not policy-in-prompt. Source: watchlist #10.

**B14. Stateful-Trajectory / Agentic Evaluator** — evaluate long agent trajectories by verifying *stateful side effects* against source-of-truth systems (not just final output), and handle judge-collapse on hard cases. A distinct fourth eval dimension beyond C4's suite-review. Source: watchlist #12.

**B15. Founder-Mode / Retroactive-Documentation persona** — for already-implemented work, backfill a ticket, retrospective plan, semantic commit, and PR description. The document-after-the-fact mode. Source: workflow-patterns §5.

**B16. Multi-Agent Coordination / Conflict-Detection Reviewer (conditional)** — *when* a system genuinely needs peer coordination, audit the coordination layer: semantic-contract coverage, single-writer ownership, event schema/idempotency, rule-based conflict detection. Source: agent-coordination-patterns + multi-agent best practices. Consistent with anti-persona #2's "only when you must" stance rather than contradicting it.

### Structural refinements (not new personas)

- **Split-tier note on B4 Codebase Navigator.** The corpus treats codebase-locator (Haiku), codebase-analyzer (Sonnet), and codebase-pattern-finder (Sonnet) as three separately-versioned agents on different tiers. The catalog collapses them into one persona; keep the persona, but the locator is really a cheap mechanical fan-out *primitive* that other personas dispatch — worth calling out so the tiering economics aren't lost. (Handled in the new B4 spec.)
- **PR-Describer.** Implied inside B3 (Decision Logger) but never named — `describe_pr` assembles the PR title/description/test-plan and pulls from the decision log. Mention it as B3's output surface rather than a standalone persona.

---

## Recommendation

Fold in all of Part A (they're integrity fixes, low effort, high trust value). For Part B, the three Tier-1 personas — **Validation/QA-Runner, Context/Token-Economics Auditor, Team-Maturity Diagnostician** — are the ones I'd add to the catalog and spec now; each fills a hole the research makes obvious and none overlaps an existing entry. Tier 2 is a strong "next five" for full lifecycle coverage. Tier 3 is a menu to pull from as specific needs surface, and B16 stays explicitly conditional to preserve the catalog's anti-swarm stance.
