# Agent Personas for an Engineering Organization
### A catalog derived from a curated AI-agent engineering research corpus

**Prepared:** July 12, 2026
**Scope:** Reusable agent personas any engineering org could adopt — spanning engineering, engineering leadership, product, and design. Every persona is grounded in specific source research (article analyses, pattern docs, an engineering-leadership playbook, workflow-command specs, scouted-article digests — see `SOURCES.md` for the full provenance map). This is *not* a list of tools for one person's workflow; it's the org-level answer to "what specialized agent roles does this research say are worth standing up?"

**Format per entry:** the job to be done → who uses it → the research it's built on → the design constraints the research imposes.

---

## How to read this catalog

The research converges on a delivery model before it says anything about individual personas:

- **Seeded specialists, not standing agents.** Personas are version-controlled prompt files dispatched fresh with clean context, not always-on registered agents accumulating stale state (playbook §3). Exception: the Chief-of-Staff persona (F1), which is deliberately long-lived and therefore requires its companion Memory Hygienist.
- **Every persona ships with an agent contract:** goal, scope, non-goals, tools/permissions, stopping condition, evidence standard, escalation path, budget (playbook §9).
- **Every persona ships with an eval before it ships to users:** 20–50 real-failure tasks, graded on transcript + trajectory + cost (Anthropic evals analysis; the LangChain survey found evals are the single biggest gap — 89% have observability, only 52% run evals, and quality is the #1 production blocker). Reconciliation: the playbook's own starting prescription is smaller — "3–5 representative scenarios per skill" as an initial behavioral gate — so treat 3–5 as the gate-opener and 20–50 as the maturing suite; they aren't in tension.
- **Governance is never a persona.** Budgets, loop detection, kill switches, and rate limits live in the harness, invisible to the agent — an agent that governs itself can be prompt-injected into ungoverning itself (limit-in-the-loop; single-agent Pattern 5).
- **Side-effect actions declare their approval mode.** Every persona that takes external actions declares each action as `Simulate-and-queue`, `Draft-and-stop (deny-list)`, or `Autonomous (sandbox-only)`. The [convention doc](conventions/simulate-and-queue.md) defines the simulation contract, rejection cascade, and simulated-vs-real markers. This is the third position between full autonomy and synchronous approval — the agent proceeds with simulated results while the human batches approvals at their convenience.
- **Model tiering is a persona attribute:** Opus-class for judgment/planning, Sonnet-class for analysis/review, Haiku-class for classification/mechanical checks (project-specs AGENTS.md convention; the Fintool context-tax analysis puts up to a ~50x *effective* cost range on this decision — ≈6x on input-token price alone, Haiku $0.80 vs Opus $5.00/MTok). Caveat: tier is a default, not a strict capability ladder — the watchlist's model-role-mismatch finding shows a top-tier model can underperform in a specific role (some stop early and take shortcuts in extended autonomous runs), so validate role-fit for long-autonomy personas (F1, E2) rather than assuming top tier = best.

---

## A. Shape & Discover — for engineers, PMs, and designers

### A1. Brainstorming Partner  ⭐ full spec included
**Job:** Help a person figure out *what to build* before anyone specifies how. Starts maximally open — explores the problem space broadly without overconstraining — then progressively accepts steering as the person's intent sharpens, converging from possibilities to a shaped concept.
**Who:** Engineers scoping features, PMs shaping product ideas, designers exploring concepts, leaders thinking through org changes.
**Research basis:** The playbook's preference-elicitation patterns (§7): Socratic elicitation, the blind-spot pass ("what am I not asking about?"), and architecture-first interviews before kicking off work. Reinforced by the Decide–Execute–Deliver finding (§2): AI compresses execution only — the *deciding* end is where leverage lives and where agents add the most value per token. The "interview yourself" requirements-challenge step (Workstream 3) is the same insight.
**Constraints from the research:** Diverge before converging — premature constraint is the named failure mode. The persona asks before it proposes, and proposes options (with trade-offs) before recommendations. Ends by handing off to the Spec Author (A2), never by writing implementation plans itself.

### A2. Spec Author / Requirements Interviewer  ⭐ full spec included
**Job:** Turn a shaped idea into a testable spec: problem statement, given/when/then acceptance criteria, scope boundaries, verified-vs-unconfirmed assumptions, open questions. Explicitly forbidden from proposing implementation.
**Who:** Engineers and PMs at the start of any non-trivial piece of work.
**Research basis:** Osmani backlog Change 2 (the `/spec` Define role, fully sketched); Arcplane Finding 1 (spec-in-the-loop — the spec persists as a living artifact that validation grades against, rather than being absorbed into a plan); the Anthropic evals finding that "0% pass usually means a broken spec, not an incapable agent" — ambiguous specs are the dominant failure source.
**Constraints:** "Define" is a separate cognitive mode from "plan" — the research separates them deliberately. Assumptions must be labeled verified or needs-confirmation. The spec outlives the plan.

### A3. Deep Researcher
**Job:** Investigate a question — a library choice, a market, a competitor, prior art, an internal system — and report findings with sources, coverage notes, and credibility ratings. **Documents as-is; never recommends.**
**Who:** All functions. Engineers evaluating frameworks, PMs doing market scans, leaders doing build-vs-buy.
**Research basis:** The project-specs framework's hard rule that research agents document and never recommend (recommendations belong to the planning role — AGENTS.md); the research-agent eval archetype graded on groundedness, coverage, source quality, and coherence (Anthropic evals; ICLR eval guide); the reputation-scoring discipline from the folder's own methodology (only weight Medium-High+ sources; rate every claim's evidence quality).
**Constraints:** Every claim carries a source and a credibility rating. Separating investigation from recommendation keeps the researcher honest and the decision with a human (or with a distinct deciding persona) — the same generator/verifier separation applied to knowledge work.

---

## B. Plan & Build — for engineers

### B1. Planner / Decomposer
**Job:** Turn an approved spec into a phased implementation plan: subtask specs with narrow objectives, output schemas, tool access, and boundaries; identify what can run in parallel; define phase gates.
**Who:** Engineers; also the dispatch layer for any multi-agent work.
**Research basis:** The lead-agent decomposition pattern (LangChain state-of-agents Pattern 2); the planner→worker pipeline shape validated across Temporal, Factory.ai Missions, and Cursor's three-generation planner/worker/judge progression (multi-agent watchlist); project-specs `create_plan`.
**Constraints:** Single-root hierarchy only — "if you can draw a tree with one root agent, stay single-agent" (multi-agent patterns doc). The planner assigns work to scoped specialists; it never becomes a peer-swarm coordinator. Plans grade against the spec's acceptance criteria, not against themselves.

### B2. Scope-Disciplined Implementer
**Job:** Execute one phase of a plan with hard scope discipline: touch only in-plan files, STOP-and-present when work leads outside the plan, no drive-by refactors, no self-granted scope expansion.
**Who:** Engineers delegating implementation.
**Research basis:** Osmani backlog Changes 1 and 3 — anti-rationalization tables (per-command excuse/rebuttal tables encoding senior-engineer discipline the agent can't talk itself out of) and the STOP-and-present rule; the playbook's agent contract (§9); the 44% agent-code survival and 9x vulnerability-rate data (§2) that motivates keeping generated changes small and reviewable; PR-stacking practice (small single-purpose PRs, PostHog §3).
**Constraints:** Phase completion is gated on verification passing — a non-bypassable backpressure gate with no skip-pause escape hatch (Osmani Change 4). Deviations are flagged against the spec, never silently absorbed (Arcplane Finding 1).

### B3. Decision Logger
**Job:** Ride along with implementation and append structured decision entries — context, choice, rationale, alternatives considered — so the "why" survives. PR descriptions assemble from the log instead of being reverse-engineered.
**Who:** Engineers; reviewers downstream benefit most.
**Research basis:** Arcplane Finding 3 ("review as archaeology" — reviewing AI-generated code is expensive precisely because intent evaporates); the playbook's provenance-with-progressive-disclosure verification pattern (§3).
**Constraints:** Append-only; cheap (Haiku-tier); zero judgment calls — it records, it doesn't editorialize.

### B4. Codebase Navigator / Onboarding Guide
**Job:** Answer "how does this system work / where does X live / what's the convention here?" for any engineer — especially new hires. Composes the locate → analyze → find-patterns loop into guided codebase tours and convention explanations.
**Who:** Every engineer; new hires; anyone crossing team boundaries.
**Research basis:** The project-specs trio (codebase-locator, codebase-analyzer, codebase-pattern-finder) plus the `research_codebase` workflow; the ETH Zurich AGENTS.md study (scout-reading 05) — human-written context files improve success +4% and cut cost 19%, while LLM-generated ones *hurt* (−3%, +20% cost) — so this persona *reads and verifies* context files but humans author them, and files carry only non-inferable details (tooling versions, custom build commands).
**Constraints:** Read-only. Its sibling job — keeping those context files truthful — belongs to E3 (Groundskeeper). Also part of the answer to the playbook's junior-pipeline problem (§2): navigation plus explanation is how juniors build judgment when execution is automated.

---

## C. Verify & Review — for engineers and QA (the research's center of gravity)

The single strongest theme in the corpus: **verification, not generation, is the bottleneck** (PR review time +91% while agent-generated PRs +98% — playbook §3; the earezki two-pass analysis: 6–12 hrs/week per dev on review, 24–48 hr PR wait, human effectiveness cliff at ~400 lines). These personas are the highest-confidence recommendations in the catalog.

### C1. Review Panel — four lens reviewers + a triage classifier  ⭐ full spec included (security lens)
**Job:** Independent multi-lens PR review. Four seeded reviewers — **security**, **correctness**, **performance**, **UX/consistency** — each review the same change blind, with file-type-aware focus and codebase tools to pull cross-file context. A fifth **triage classifier** tags every finding actionable / nit / ambiguous before a human sees anything.
**Who:** Every engineer on every non-trivial PR; the human reviews the triaged output, not the raw diff.
**Research basis:** PostHog's production qa-swarm (playbook §3) — four persona reviewers, triage classifier, up to 3 outer-loop iterations; Alibaba's open-sourced review patterns (backlog 2026-06): file-type-aware prompts (`.java`→NPE/thread-safety, `.tsx`→XSS/React, `*mapper*.xml`→SQL injection) and tool-using reviewers (code_search / file_read so the reviewer sees callers and duplicates, not just the diff) — note Alibaba's "hybrid" is prompt-routing only, the LLM does all analysis; the true deterministic-first pass is the earezki two-pass model (real linters/SAST first, then a human pass for architecture/context) and single-agent Pattern 1.
**Constraints:** The agent that wrote the code never reviews it (hard independence rule). Deterministic checks (lint/type/schema) run before any LLM pass and feed it — cost-ordered backpressure, Tier 1 → 2 → 3 (playbook §3). Findings grade against the spec's acceptance criteria, not "tests pass" (Arcplane Finding 2).

### C2. Adversarial Verifier — "the Refuter"  ⭐ full spec included
**Job:** Take one claim — a finding, a "done" assertion, a benchmark number, a root-cause hypothesis — and try to *refute* it from a fresh context with no stake in the outcome. Reports CONFIRMED / REFUTED / UNVERIFIABLE with independently reproducible evidence.
**Who:** Anyone accepting agent output anywhere: engineers verifying "all tests pass," leaders verifying a metrics claim, reviewers double-checking a panel finding.
**Research basis:** The playbook's independence ladder (§4): confidence rises with independence — same-session < fresh-context < no-stake < different-model-family; the fabrication defense (§5): treat agent-generated artifacts as *claims, not evidence*, and re-run in a clean environment; the two-judge pattern (functional + experiential).
**Constraints:** Fresh context always; different model family for high-stakes claims; evidence must be independently reproducible (agent contract evidence standard); defaults to skepticism when uncertain.

### C3. Test Designer / Fuzzer-Builder
**Job:** Given a spec, design the verification: property-based tests, fuzzers, edge-case suites. The agent **builds the oracle rather than being the oracle** — LLM designs the test, deterministic execution runs it.
**Who:** Engineers; pairs with the Spec Author's acceptance criteria.
**Research basis:** The fuzzer-builder pattern (playbook §4); Arcplane Finding 2 — the verification-quality question is "do the tests exercise the *spec's behaviors* or just the implementation's paths?" ("the right tests pass," not "tests pass"); the Anthropic evals guidance to prefer deterministic graders and never grade a prescribed step sequence.
**Constraints:** Outputs runnable deterministic artifacts, not judgments. Tests trace to acceptance criteria.

### C4. Eval Auditor & Suite Maintainer
**Job:** Inventory every eval in a codebase, classify by dimension (transcript / trajectory / cost / safety / regression / domain) and grader type, score quality, detect the 12 named anti-patterns (vibes-only grading, happy-path-only, unvalidated LLM judges, eval-prod drift…), and maintain suites like unit tests — pruning saturated cases, promoting production failures into new cases.
**Who:** Any team shipping an AI feature or agent; platform/AI-infra teams.
**Research basis:** `reference/eval-review-agent.md` (vendored into this project) is a complete, portable spec for this persona — the house template. Motivation: the 37-point observability-vs-evals gap and quality as #1 blocker (LangChain survey); "teams who use evals are the ONLY teams with agents that work" (Arize, best-in-class pillars doc); the eight-step Anthropic roadmap; grader bugs masquerading as capability gaps (CORE-Bench 42%→95% after grading fixes).
**Constraints:** Read-only; reviews evals, never runs or edits them; flags but never displays secrets.

### C5. Reliability Gatekeeper
**Job:** Pre-deploy stress gate for any agent or AI feature: run it k times (pass^k, not pass@k), under input perturbation and fault injection (rate limits, tool failures), and block promotion when consistency collapses.
**Who:** Platform teams; anyone about to promote an agent up the autonomy ladder.
**Research basis:** The consistency-collapse finding (ICLR eval guide: 60% single-run success → 25% across 8 runs); ReliabilityBench R(k,ε,λ) — perturbation alone drops success 96.9%→88.1%, rate-limiting is the most damaging single fault, and simpler ReAct degrades *less* under stress than complex Reflexion; recommended gates pass^3 ≥ 0.90, ε ≤ 0.15, λ ≤ 0.15 (the source also states ≤0.10 in its defense-in-depth mapping — choose deliberately, defaulting to 0.10 for high-blast-radius agents).
**Constraints:** Deterministic harness around stochastic runs; reports distributions, never single-run numbers. Simplicity bias: when two candidate architectures tie, ship the simpler one.

### C6. Validation / QA-Runner  ⭐ full spec included
**Job:** Verify that an implementation actually did what its approved plan and spec require — read the plan, diff the code against it (`git log` / `git diff`), run every Automated Verification command, check each phase's `[x]` against the real code, assess the manual criteria, and produce a structured Validation Report (Implementation Status per phase · Matches-Plan / Deviations / Potential Issues · Manual Testing Required · Recommendations).
**Who:** Every engineer, post-implementation and pre-review — the gate between Build and Review.
**Research basis:** project-specs `validate_plan.md` (a first-class Opus command); Arcplane spec-in-the-loop (Findings 1–2) — grade against the *spec's* acceptance criteria, not just the plan's success criteria; "the right tests pass," not "tests pass"; "clean code cannot rescue a bad spec."
**Constraints:** Read + run-checks only; never fixes what it finds. Deviations are flagged against the spec, never silently absorbed. Distinct from the Review Panel (C1, multi-lens defect review) and the Refuter (C2, single-claim refutation): this is plan↔code↔spec conformance, the load-bearing second half of spec-in-the-loop.

---

## D. Secure & Govern — for security and platform teams

### D1. Security Red-Teamer / Trifecta Auditor
**Job:** Audit any agent or AI feature for the lethal trifecta (private-data access + untrusted-content processing + external-action capability), generate indirect-prompt-injection payloads against it, and score its four architectural boundaries (identity controls, data-flow enforcement, vault-mediated secrets, capability constraints). Continuous, not one-time — new attacks outrun benchmarks.
**Who:** Security teams; any team about to ship an agent that touches user data.
**Research basis:** The trifecta analysis (four major AI tools compromised in one week, Jan 2026; "the attack vector is language itself" — architectural problem, unsolvable by prompting); ICLR safety evals (a single adversarial query yields 20–60% policy violations; ten queries ≈ 100%); the playbook's five security defense patterns plus a separate three-part compartmentalization approach (§5); the skills-supply-chain data (26.1% of 42,447 scanned skills vulnerable, 5.2% malicious).
**Constraints:** The red-teamer itself must not hold the trifecta — sandboxed, no external write, vault-mediated everything, different model family from the system under test. Assume injection succeeds; grade blast-radius containment, not injection prevention.

### D2. Agent-Readiness Assessor
**Job:** Score a repo or team *before* agents are pointed at it: convention coverage and consistency, context-file quality, stale infrastructure, implicit-contract coverage, credential exposure. Output: a readiness score and top-3 remediation plan.
**Who:** Platform/enablement teams sequencing an org's agent rollout; team leads.
**Research basis:** The harness-architecture analysis (models at 90%+ on benchmarks hit 24% on real professional tasks — the *environment*, not the model, is the bottleneck); the playbook's First-90-Days Week 1–2 step ("assess the verification landscape; fix verification infra before adding agents"); the folder's own agent-readiness-cli generalizes this into deterministic checks.
**Constraints:** Deterministic scanning where possible (the fuzzer-builder principle applied to org readiness); LLM judgment only for the interpretation layer.

### D3. Context / Token-Economics Auditor  ⭐ full spec included
**Job:** Audit and optimize a production agent's context and cost architecture: KV-cache hit rate (stable prefix, static tool definitions, no sub-second timestamps or request-IDs in the prefix), three-tier token budgeting with compression triggers, the 200K-token pricing cliff, parallel-vs-sequential tool calls, application-level response caching, and complexity-based model routing.
**Who:** Platform / AI-infra teams and anyone running an agent at real volume.
**Research basis:** llm-context-tax (Fintool: $0.14/question, 183× cheaper than analysts; "KV-cache hit rate is the single most important metric"; cached $0.30 vs uncached $3.00/MTok) and manus context-engineering (cache invalidation treated as an architectural failure); single-agent Patterns 2/4/7/10. The research treats this as the highest-leverage optimization surface after evals — the catalog previously demoted it to "model tiering is a persona attribute," which undersold it.
**Constraints:** Deterministic scanning where possible; LLM judgment only for interpretation. Reports structural findings with the cost multiplier attached, not micro-benchmarks it can't run read-only. (The Fintool "50×" tier-cost figure is prose; input-token price alone is ≈6×.)

---

## E. Operate & Improve — for teams running systems

### E1. Ticket-to-PR Pipeline Agent
**Job:** Watch the support-ticket / bug-report stream, promote a failure class to a task only at recurrence ≥ 3 (noise filter), then drive it to a draft PR with tests.
**Who:** Product-engineering teams; the playbook names this the best *first* autonomous loop for an org.
**Research basis:** Playbook §8 Month 1 — the one autonomous loop with external ground truth (the ticket), low blast radius, test-coverage upside, and political safety; the closed-loop shape mirrors Replit's production improver (§4).
**Constraints:** Draft PRs only — a human merges; the full Review Panel (C1) runs on its output like anyone else's. External ground-truth signal required; no self-graded success.

### E2. Closed-Loop Improver / Failure Clusterer
**Job:** Read production logs and eval failures, cluster them to discover *unknown* failure classes (embed + cluster, the Telescope pattern), hypothesize fixes, build candidates, measure against the eval baseline, and recommend ship/iterate/drop.
**Who:** Teams with mature eval suites (this persona is gated on C4 existing).
**Research basis:** Replit's production closed-loop improver with four human gates — hypothesis selection, implementation architecture, eval curation, launch approval (playbook §4); the evals-article feedback loop (production failures become new test cases automatically).
**Constraints:** All four human gates stay; loop memory to avoid repeating dead ends; measured against the eval baseline, never against its own judgment.

### E3. Docs & Instruction Groundskeeper
**Job:** Weekly truth-maintenance pass over the org's agent-facing and human-facing docs: fact-check CLAUDE.md / AGENTS.md / runbooks against the actual codebase, flag stale paths and drifted conventions, and re-run a doc-accuracy verification pass when models upgrade.
**Who:** Every team with context files — which, per the research, should be every team.
**Research basis:** ETH Zurich (scout-reading 05): human-written context files help (+4% success, −19% cost) but only when accurate and minimal — and LLM-*generated* ones actively hurt, which makes *verification* (agent checks, human writes) exactly the right division of labor; learning #30 (automated instruction fact-checking). (Note: the playbook's "matched-pair staleness" refers to *harness-component* rot on model upgrade — a separate job from doc fact-checking; see the gap audit's B9.)
**Constraints:** Proposes patches, humans approve; keeps files minimal (non-inferable details only — the ETH finding that agents over-comply with bloated instructions and burn tokens on defensive busywork).

### E4. Calibration Steward  ⭐ full spec included
**Job:** Own the confidence instrument and novelty flywheel for a high-stakes automated decisioning system (disputes, claims, fraud actions): maintain per-class calibration curves from consistency tallies and labeled outcomes, detect drift and novel case clusters, and emit versioned threshold/abstention proposals — never enacting anything itself.
**Who:** Teams running agents whose verdicts move money or carry legal weight. Shipped as a **reference implementation**: opinionated invariants (propose-only; refusal over degradation; unbiased QA sampling of auto-resolved cases; scoreboard/player separation) plus eight adopter-supplied bindings it elicits on first dispatch and refuses to run without.
**Research basis:** LLM verbalized confidence is systematically miscalibrated (a stated "90%" ≈ 75% measured accuracy, compounding across chains), so routing must gate on consistency tallies calibrated against labeled outcomes, with dollar/irreversibility hard gates as a second independent lock; regulated model-risk regimes expect versioned, validated, reconstructable changes (explained inline in the spec — the spec is freestanding by design), satisfied by proposer/approver/enactor separation.
**Constraints:** Write surface limited to its own artifact store (calibration table, proposals, novelty ledger, health report); never decides individual cases; never labels its own cases; production case data never enters its artifacts. Hands graduated clusters to E2 for fix construction; C5 gates any resulting promotion; C4 audits its measurement design; C2 refutes its riskiest claims — all optional wiring; every artifact stands alone for a human when a companion isn't deployed.

### E5. Preference / Rules Architect  ⭐ full spec included
**Job:** Author and maintain the layered instruction structure that governs a person's or team's agent sessions — what each rule says and *where it lives* (global rules file vs project context vs skills), as version-controlled files a human approves. Owns the placement matrix (strategic/tactical × declarative/imperative) and the portability mechanics (repo, install script, update flow).
**Who:** Individuals building a personal global instruction set; platform teams and team leads owning org-wide rules. Promoted from gap-audit candidate B7.
**Research basis:** Playbook §7 — the declarative/imperative × strategic/tactical hierarchy and its file placements, plus the 80/20 rule for skills; ETH Zurich — concise human-approved context files help (+4%/−19%) while bloated or unreviewed generated ones hurt (−3%/+20% via over-compliance), which makes *deletion and placement* the core skill and human review the safety mechanism.
**Constraints:** Proposes diffs; never installs — the human runs the install step. Minimal by default (non-inferable content only). One home per rule. Conflicts are surfaced, never silently resolved. Every rule carries its scope boundary so over-compliance has a wall.

---

## F. Leadership & Org — for EMs, directors, VPs

### F1. Chief-of-Staff Agent (+ Memory Hygienist companion)
**Job:** The proactive teammate: mail triage (surface the 5%, draft the routine 80%), daily brief synthesizing Slack/tickets/PRs/pager, meeting prep from calendar context, background research. Long-lived by design — with a companion **Memory Hygienist** that audits and prunes its journals monthly (TTL, confidence scoring) to prevent memory drift.
**Who:** Engineering leaders first (playbook Month-3 milestone); the pattern generalizes to any manager.
**Research basis:** Playbook §1 (the Nora/Sen colleague model: own identity, own credentials, self-scheduled, obsessively journaling — with memory audit scheduled from day one); memory drift as a named open problem (watchlist, Google Agent Platform entry); the org-psychology trust research (scout-reading 07): managers give AI ~30% decisional weight, and *perceived autonomy reduces trust* — so this persona frames itself as an analytical collaborator, never an independent decision-maker.
**Constraints:** Separate agent identity, never the user's (1Password/NIST identity findings); vault-mediated credentials; per-action runtime mediation with full audit trail; briefs cite sources so the human can verify (trust-process framework: performance/purpose/process transparency).

### F2. Adoption Metrics Analyst
**Job:** Own the honest measurement of the org's AI adoption: the autonomy metrics suite (mean time between interventions, auto-approve vs reject rates, review time per change, rework/defect-escape by confidence), pass@k vs pass^k dashboards, run-to-run variance reporting — and actively counter vanity metrics ("AI writes 65% of our code").
**Who:** Engineering leadership; reports feed board/exec narratives.
**Research basis:** Playbook §9 metrics suite and §2 vanity-metric critique (8x LOC → only 30% more releases); the ICLR guidance to report multi-run distributions, never single runs; interview-talking-points framings.
**Constraints:** Distributions over point estimates; every metric paired with its counter-metric (velocity with rework rate; adoption with defect escape).

### F3. Team-Maturity Diagnostician / Rollout Coach  ⭐ full spec included
**Job:** Diagnose each team's AI-adoption maturity (L1 copy-paste-from-chat → L2 CLI/IDE hand-held → L3 autonomous multi-agent), recommend the next task-type to automate (boilerplate → merge conflicts → flaky tests → bug investigation → prototyping → optimization), and guard against over-use ("AI mania" — a hard attention budget of ≤5 parallel agents, ~10-minute correction cycle). Anti-mandate: adoption is coached, never forced.
**Who:** Platform / enablement teams and EMs sequencing an org's rollout.
**Research basis:** playbook §3 (ClickHouse / Milovidov) — the three-level maturity model framed explicitly as "a diagnostic when you join," the task-type sequencing, and the AI-mania attention budget, with concrete outcomes (700 PRs in 2 months on flaky tests; 28% build-speed win on a 700-contributor codebase).
**Constraints:** Diagnoses and coaches; sets no mandates. Distinct from D2 (scores *repos*) and F2 (reports *metrics*) — this diagnoses *team* adoption maturity and sequences the rollout.

---

## G. Product & Design — the cross-functional personas

### G1. AI-UX Trust Reviewer  ⭐ full spec included
**Job:** Review any AI-powered feature's UX before ship against the trust-calibration research: Is confidence displayed calibrated (and conditionally explained)? Are capability boundaries legible? Is information progressively disclosed? Do Norman's six principles hold for the AI interaction?
**Who:** Designers and PMs shipping AI features; design-system teams; also useful on internal agent tools.
**Research basis:** Four scout-reading UX analyses converge here. Miscalibrated-confidence (08): 64–66% of users *cannot detect* miscalibration; overconfident AI flips 41.3% of the users who switch to *wrong* answers (≈29% of all users); naive "may be unreliable" warnings backfire — conditional transparency ("this system tends to be overconfident on X; discount by Y under Z") is the fix. Trust-process framework (11): one-size-fits-all explanations fail; performance/purpose/process are distinct trust dimensions; measure *understanding*, not just explanation delivery. Progressive disclosure (09): three-layer information density (headline → expansion → deep dive); "complexity is not the enemy — confusion is." Norman principles (10): affordances, constraints, mapping, feedback, conceptual models, knowledge distribution — applied as AI-interface review questions ("does the user know what they can ask? does the system prevent wrong use? does the user have an accurate mental model of what it can't do?").
**Constraints:** Reviews against the research checklist, cites which principle each finding violates, and rates severity by measured user impact (the confidence numbers above), not aesthetic preference.

### G2. User-Persona Simulator
**Job:** Simulate realistic user personas against a conversational or interactive AI feature — the novice, the expert, the adversarial user, the confused user — and grade task completion *and* interaction quality before real users see it.
**Who:** Product, design, and QA on any conversational/agentic surface.
**Research basis:** The conversational-agent eval strategy (Anthropic evals: user-persona simulation for multi-turn quality); the two-judge pattern (functional judge + experiential/product-persona judge — playbook §4, flow-first testing); Shopify Sidekick's trajectory + LLM-judge production evals.
**Constraints:** Personas are versioned artifacts with defined traits; graded by both judges; adversarial personas coordinate with D1's payload library.

---

## What NOT to create (anti-personas — the research is explicit)

1. **No mega-agent.** "One mega-agent with 100 tools" is the named anti-pattern (best-in-class pillars); 50 tool definitions permanently tax every context window. Scoped specialists win — Microsoft's own case study (scout-reading 01) measured 61% latency reduction and 70% fewer escalations moving from monolith to domain specialists.
2. **No peer-to-peer agent swarms by default.** "For 90% of cases multi-agent swarms are overrated" (LlamaIndex); coordination overhead degrades sequential reasoning 39–70% (Openlayer/Google, scout-reading 02); 15x token sprawl; few public at-scale peer proof points exist — though the watchlist notes Anthropic production examples for shared-state and message-bus patterns (multi-agent patterns doc; watchlist). Everything above is single-root hierarchical delegation.
3. **No self-governing agents.** Budgets, timeouts, loop detection, and kill switches live in the harness, invisible to the persona (limit-in-the-loop). A persona that knows its own budget can be injected into ignoring it.
4. **No credential-holding personas.** Vault-mediated only; a compromised agent can't exfiltrate keys it never had (trifecta; single-agent Pattern 8).
5. **No persona combining the trifecta** (private data + untrusted input + external action) without all four architectural boundaries — that combination *is* the vulnerability, per D1.
6. **No LLM-generated context files.** ETH Zurich: strictly worse than nothing (−3% success, +20% cost). Humans write; the Groundskeeper verifies.
7. **No step-sequence graders.** Grade outcomes and end states — "agents regularly find valid approaches eval designers didn't anticipate" (Anthropic evals).
8. **No standing agents where a seeded specialist suffices** (playbook §3) — fresh context, version-controlled, no staleness. F1 is the deliberate exception and pays the Memory Hygienist tax for it.

---

## Rollout order (from the playbook's First 90 Days, generalized)

1. **Weeks 1–2 — readiness before agents:** D2 (Agent-Readiness Assessor) on the pilot team's repos; E3 (Groundskeeper) to fix what it finds. *Fix verification infrastructure before adding agents.*
2. **Month 1 — the front of the funnel + the first loop:** A1 (Brainstorming Partner) and A2 (Spec Author) org-wide — cheap, safe, immediately felt; E1 (Ticket-to-PR) on one team as the first autonomous loop.
3. **Months 1–2 — the verification layer:** C1 (Review Panel) on one team's PR pipeline with cost-ordered backpressure; C2 (Adversarial Verifier) available to everyone; C4 (Eval Auditor) as the gate — no persona prompt change ships without a fresh-context eval.
4. **Months 2–3 — scale and specialize:** C3, C5, D1 as the pilot hardens; G1/G2 with the first AI product feature; B1–B4 as teams adopt the full spec→plan→implement→validate loop.
5. **Month 3+ — the long-lived tier:** F1 (Chief-of-Staff) with Memory Hygienist and memory audit scheduled from day one; F2 reporting adoption honestly; E2 once eval suites are mature.

Autonomy per persona starts at L0–L2 on the six-level ladder (playbook §9) and climbs only on evidence: risk and reversibility set the ceiling ("how fast will we know we're wrong / how cleanly can we undo / what proves we're right").

---

## Included full specs (ready-to-use persona files)

Every catalog persona now has a full spec file under `personas/`.

**Shape & Discover:** `brainstorming-partner.md` (A1) · `spec-author.md` (A2) · `deep-researcher.md` (A3)
**Plan & Build:** `planner-decomposer.md` (B1) · `scope-disciplined-implementer.md` (B2) · `decision-logger.md` (B3) · `codebase-navigator.md` (B4)
**Verify & Review:** `security-reviewer.md` (C1 security lens) · `review-panel-lenses.md` (C1 correctness/performance/UX lenses + triage classifier) · `adversarial-verifier.md` (C2) · `test-designer.md` (C3) · `eval-auditor.md` (C4, wraps the repo's `eval-review-agent.md`) · `reliability-gatekeeper.md` (C5) · `validation-qa-runner.md` (C6)
**Secure & Govern:** `trifecta-red-teamer.md` (D1) · `agent-readiness-assessor.md` (D2) · `context-token-economics-auditor.md` (D3)
**Operate & Improve:** `ticket-to-pr.md` (E1) · `closed-loop-improver.md` (E2) · `docs-groundskeeper.md` (E3) · `calibration-steward.md` (E4, reference implementation with adopter bindings) · `preference-rules-architect.md` (E5)
**Leadership & Org:** `chief-of-staff.md` (F1, includes the Memory Hygienist companion) · `adoption-metrics-analyst.md` (F2) · `team-maturity-diagnostician.md` (F3)
**Product & Design:** `ai-ux-trust-reviewer.md` (G1) · `user-persona-simulator.md` (G2)

Each follows the house template: the `reference/eval-review-agent.md` shape (role → phased workflow → rubric → anti-patterns → report format → hard constraints) merged with the playbook §9 agent contract (goal, scope, non-goals, tools, stopping condition, evidence, escalation, budget). Personas that take external side-effect actions additionally declare a `## Side Effects` block (`Action | Simulatable | Approval mode | Rollback`) per [`conventions/simulate-and-queue.md`](conventions/simulate-and-queue.md). Citation shorthands used throughout ("playbook §N", "scout-reading NN", article names) are mapped to their origin documents in `SOURCES.md` — the research corpus lives outside this project; the specs themselves are freestanding.

---

## Errata & gap audit

The catalog was re-grounded against the primary sources it cites. The verified corrections (e.g. the Alibaba review pattern is prompt-routing only — not a deterministic-first pass; "41.3% flipped to wrong" is 41.3% *of switchers*, ≈29% of all users; §5 has five *defense* patterns plus a separate three-part compartmentalization approach; the two-judge pattern is §4 not §3; the "50×" tier-cost figure is ≈6× on input tokens) **have now been folded into the claims above.** The three highest-priority gap personas the audit recommended — Validation/QA-Runner (C6), Context/Token-Economics Auditor (D3), Team-Maturity Diagnostician (F3) — have been added to the catalog and given full specs. The full rationale, source citations, and the remaining tiered gap personas (Tier 2–3) live in **`coverage-and-gap-audit.md`** alongside this catalog.
