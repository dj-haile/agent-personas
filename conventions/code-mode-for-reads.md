# Convention: Code Mode for Reads

**Applies to:** any persona whose workflow includes a multi-system read phase — gathering from several sources, then joining, deduplicating, filtering, or ranking the results before synthesis. The motivating case is the Chief-of-Staff (F1), Phases 2–3 ([../personas/chief-of-staff.md](../personas/chief-of-staff.md)). Personas whose reads are single calls, and all side-effect phases of every persona, are out of scope (§1).

**What it is:** an execution mechanism the *harness* may select for a read phase: instead of the model emitting structured tool calls one at a time, the harness exposes the persona's read tools as narrow typed functions inside a sandboxed JavaScript runtime, and the model writes a short script that calls them, computes over the results in memory, and returns a structured result. The persona's posture, phases, evidence standard, and approval modes do not change — only how reads execute. This doc is the contract any implementation must satisfy; it ships no runtime.

**Provenance:** Source 120 (Code Mode — Vercel AI SDK, pattern by Varda & Pai/Cloudflare): models are more accurate on multi-step tool workflows expressed as code than as chained structured calls, because the code-writing training prior is vastly larger than the tool-call-schema prior. Source 119 (Morrell object-capability): untrusted or model-authored code should receive narrow typed function references, never credentials or ambient I/O — the typed function *is* the capability. The two compose: 119 is the shape of the tool surface, 120 is the authoring surface that uses it. Security caveat carried from Source 120: the sandbox becomes the security perimeter (Check Point, "When Agentic Glue Melts," 2026 — misconfiguration classes: ambient fetch, host FS mounts, shared isolates). See `SOURCES.md` for the full provenance trail. Proposal history: `decisions/chief-of-staff-code-mode-handoff.md` and its plan-skeptic review; this convention resolves that review's design objections at the spec level.

---

## 1. When Code Mode applies — and the hard boundary

**Applies when** a phase performs **three or more chained reads with dependencies** — transform, filter, join, dedup, retry — per Source 120's threshold. Single-call reads gain nothing and pay the sandbox cost; they stay structured.

**Never applies to side effects.** A phase governed by [simulate-and-queue.md](simulate-and-queue.md) or draft-and-stop always runs structured tool calls. The reason is bookkeeping, not sandbox safety: the queue's contract requires each action to map 1:1 to a queue entry carrying a `state` field and participating in the rejection cascade. A script that fires N actions in a loop would need its own action-tracking shadow of the gatekeeper. The separation is absolute: **Code Mode for data, structured calls for effects.**

**The harness selects the mode, per phase, per wakeup.** The agent never chooses, requests, or negotiates its own execution mode — mode selection is governance, and governance lives in the harness (catalog-wide principle). A persona prompt that lets the model pick its mode is non-compliant.

**Structured mode is the permanent default and fallback.** `tool_invocation_mode` defaults to `structured`; `code` is opt-in per phase. Adopting Code Mode for a persona must not delete or degrade its structured path — the structured prompt and flow remain runnable at all times, so reverting is a flag flip, not a rebuild.

## 2. The capability surface

The sandbox exposes **only narrow typed read functions** (Source 119 shape): a name, typed parameters, a typed return. Nothing else is callable.

- **No write function may exist in the sandbox.** Not denied — absent. A side effect from inside a Code Mode phase must require a function that does not exist. (Sandbox-confined writes with no external observer — e.g. a scratch buffer — are not "writes" in this sense; the line is the same one simulate-and-queue §1 draws: does the effect leave the sandbox?)
- **Every exposed function must trace to the persona's declared read scope** — a row already marked `Autonomous (sandbox-only)` reads in its `## Side Effects` table, or systems named in its Scope. The sandbox must not widen a persona's reach silently; if a persona needs a new read source, amend the persona spec first, then the function list.
- **The credential posture is inherited, not invented.** Each function is implemented by a harness-side bridge that holds the credential per the persona's *current* credential posture — target architecture (vault → arbiter → proxy) where it exists, or the persona's documented v1 posture (e.g. F1's keychain-held bot token) where it doesn't. This convention works under either and **does not presuppose infrastructure the persona's own spec says is unbuilt**. In every case the model's code sees typed functions only: no credential, no endpoint, no socket.
- The typed signatures are also the token-efficiency win (Source 119): a TypeScript signature is smaller and more familiar to the model than an OpenAPI JSON schema. Function docs stay minimal — signature plus one line.

## 3. Sandbox contract

Any conforming runtime (V8 isolate, Deno worker, comparable) must enforce:

1. **No ambient network.** No `fetch`, no sockets. External reach exists only through the exposed functions.
2. **No filesystem.** Journal writes happen after the sandbox returns, in the persona's normal journal phase.
3. **No globals beyond the exposed functions and standard JS built-ins** (Array, Map, Set, Date, JSON, Math, RegExp, Promise).
4. **No shared isolates.** One isolate per invocation (Check Point misconfiguration class).
5. **Timeout and token accounting inherit the wakeup budget** — and the concrete limits are **harness-internal, never placed in agent-visible prompt or envelope content**. Personas that forbid self-governed budgets (F1 hard rule: "a persona that knows its own limits can be talked out of them") stay compliant: the model is told it is in Code Mode and given the function signatures and return contract — not the limit values, not the sandbox config.
6. **The return value is the only acted-on output.** `console.log`/stderr are captured for debugging only. What the return value must contain is §4 — "only output" is a channel rule, not permission to return less.

## 4. The return contract: deliverable + observations + attribution

A Code Mode phase must return a structured result with **two mandatory parts**:

- **The deliverable payload** — the gathered dataset (gather phase) or the synthesized output (synthesize phase).
- **The observation record** — the raw material the persona's journal phase needs: items considered per system, every merge/dedup decision (which items merged, on what key), occurrence counts per signal, and what was filtered out with a reason class. Long-lived personas weight journal confidence by observation count (F1's Hygienist contract); a sandbox that returns only the finished brief starves the journal and silently corrupts confidence scoring downstream. **Returning the deliverable without the observation record is a contract violation**, not an optimization.

**Attribution is a field in every item type, at every stage.** Each item in each return type carries its source link(s). A merge or dedup **preserves the union of its inputs' links** — deduplicating a PagerDuty incident against its Slack thread yields one item with both links. The persona evidence rule ("every line cites its source or it doesn't ship") binds the intermediate data, not just the final brief — a link dropped in the sandbox cannot be re-cited later. Typed return schemas without a source-link field are non-conforming.

## 5. Untrusted content and generated code

Assume injection succeeds; design for blast-radius containment (catalog-wide principle). Code Mode adds one genuinely new surface: gathered attacker-writable content (Slack, mail, tickets, PR text) is in the model's context **when it writes the next script**, so hostile text can try to steer executable code — suppress an incident from the brief, re-rank an attacker's item upward — not just prose.

- **Containment first:** §2 and §3 cap the blast radius at *corrupted output*. No write functions, no network, no filesystem means an injected script cannot act, exfiltrate, or persist — the worst case is a wrong brief.
- **Content is data, never control flow.** Generated code must treat fetched content as values to filter, join, and quote — never as instructions that change what the code does. Ranking and filtering criteria come from the persona's task, not from imperative text found inside gathered items.
- **Corrupted output is the residual risk, so it is what the eval must catch.** A conforming adoption includes eval scenarios with planted injection in the gathered content, graded on outcome: the planted instruction appears in the output quoted-with-attribution (or not at all), the item it tried to suppress is still present, the priority it demanded is not granted (see `evals/chief-of-staff-eval.md`, Scenario 4).

## 6. The `synthesize()` helper — bounded, declared, separated

A synthesize phase may optionally expose `synthesize({instruction, data})` — a call back into a model for judgment tasks (why-this-needs-you annotations, credibility notes) while code handles the data manipulation. It is a **model call, not a read**, and is governed accordingly:

1. **Declared or absent.** A persona exposing `synthesize()` declares it in its spec (which phase, what for). Undeclared means not exposed — mirroring simulate-and-queue §2: an undeclared capability has no posture and defaults to unavailable.
2. **Harness-enforced call cap per wakeup.** The declaration names the cap (F1 default: 10). The cap is enforced by the bridge, invisible to the model (§3.5), and nested tokens count against the wakeup budget — a parallel fan-out can exhaust a token budget well inside a time budget, so the cap is on calls and tokens, not time.
3. **Depth 1.** The nested call has no tools and no `synthesize()` of its own.
4. **Tier declared.** Default: the persona's own tier. A cheaper tier is a per-persona decision recorded in the declaration.
5. **Instruction/data separation.** `instruction` must derive from the persona's task; `data` is passed as a distinct field and handled as quoted material inside the nested call — untrusted content never becomes the instruction. The nested call runs under the persona's hard rules (the harness injects the same rule set); attribution obligations (§4) apply to its output.

## 7. Failure, fallback, and the adoption gate

- **On script failure** (throw, timeout, non-conforming return): the phase produces nothing — there is no partial result to trust. The harness re-runs the phase in **structured mode** (same wakeup if budget allows, else next wakeup). Never re-prompt the model to "fix the script" with the failure in context during the same wakeup: a failing script plus injected content is an iteration loop an attacker can steer.
- **The adoption gate, per persona:** (1) the persona has an eval suite that passes at gate in **structured mode** — this is the baseline, and without it "Code Mode is better" is unfalsifiable; (2) the same scenarios, mechanism-agnostic and outcome-graded, run in code mode with **non-inferior results**; (3) a negative scenario confirms a script calling any function outside the exposed set fails with **no external effect**. Only then may the harness flip a phase to `code` — and §1's fallback rule means flipping back stays a flag flip.

## 8. Portability

This document is the contract; no SDK is the contract. Vercel AI SDK `mode: "code"` is one conforming implementation; a V8 isolate, Deno worker, or equivalent wired by hand is another, provided §§2–7 hold. Persona specs reference **this convention only** — never an SDK, runtime, or vendor — so the harness under a persona can be replaced without touching the persona. The runtime itself (isolate pool, bridge, schema generation) is harness infrastructure and lives outside this repo, per the repo's spec-only boundary.

---

## Cross-references

- [simulate-and-queue.md](simulate-and-queue.md) — the side-effect convention Code Mode explicitly defers to; §1's hard boundary exists to keep that contract intact.
- [../reference/gatekeeper-adapter.md](../reference/gatekeeper-adapter.md) — the queue/cascade runtime interface that structured Phase 4 calls feed.
- [../personas/chief-of-staff.md](../personas/chief-of-staff.md) — first adopting persona (Phases 2–3); its Appendix's v1 credential posture is the §2 "inherited posture" example.
- [../evals/chief-of-staff-eval.md](../evals/chief-of-staff-eval.md) — the baseline suite the §7 gate requires; Scenario 4 is the §5 injection check.
- `decisions/chief-of-staff-code-mode-handoff.md` — the originating proposal; superseded on design points by this convention where they differ (return contract, `synthesize()` bounds, fallback rule).
- **Source 119, Source 120** — see `SOURCES.md` for origin documents and the applied scout reports.

**What this convention does not cover:** the runtime that implements it — the isolate, the typed-function bridge, schema generation from tool definitions, and harness wiring are infrastructure concerns for a harness repo. Persona specs declare that a phase *may run under this convention*; they never describe sandbox mechanics.
