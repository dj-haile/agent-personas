# Handoff: Adopt Code Mode for Chief-of-Staff Gather and Synthesize Phases

**Created:** 2026-08-21
**Status:** Ready to implement
**Sources:** Source 120 (Vercel AI SDK Code Mode), Source 119 (Morrell object-capability pattern) in playbook
**Persona affected:** Chief-of-Staff (F1) — `personas/chief-of-staff.md`

## Why this change

The Chief-of-Staff's Phase 2 (gather) and Phase 3 (synthesize) are multi-system data joins. A typical daily-brief wakeup reads from Slack, Linear/Jira, GitHub, PagerDuty, and calendar, then cross-references and filters the results — deduplicating a PagerDuty alert that already appeared as a Slack thread, matching a PR to its Linear ticket, ranking items by urgency across systems.

With sequential structured tool calls, every read is a separate round trip. The model has to hold intermediate results in its context window, re-describe filtering logic in natural language between calls, and can't do the kind of in-memory joins that a few lines of code handle trivially. This is exactly the workload Code Mode was designed for: multi-step data retrieval with intermediate computation. Vercel's benchmarks show higher accuracy on these workflows because the model can lean on its code-writing prior instead of reasoning through data transformations in prose.

Phase 4 (side effects) does **not** change. Structured tool calls with simulate-and-queue stay exactly as specified — Code Mode is for reads and computation, not for actions that affect external state.

## What Code Mode is

Code Mode (`mode: "code"` in the Vercel AI SDK) lets the LLM write JavaScript that calls typed tool functions, instead of emitting one structured tool call at a time. The generated code runs in a V8 isolate sandbox — no ambient network access, no filesystem, no globals except the typed functions you expose. The model writes a short script, the sandbox executes it, and the result comes back.

The key property: the model's code-writing training prior is stronger than its sequential-tool-call prior for workflows involving loops, filters, joins, and conditional logic. Instead of describing "now call Slack, then for each message that mentions a ticket, call Linear to get the status," the model writes:

```javascript
const threads = await slack_getThreads({ channel: "engineering", since: yesterday });
const ticketIds = threads.flatMap(t => extractTicketIds(t.text));
const tickets = await Promise.all(ticketIds.map(id => linear_getIssue({ id })));
const blocked = tickets.filter(t => t.state === "blocked");
```

That's fewer round trips, explicit data flow, and the sandbox prevents anything the code shouldn't do.

## What changes

### Phase 2 — Gather with attribution (now Code Mode)

**Before:** The model emits sequential tool calls — `slack.getMessages`, wait, `linear.getIssues`, wait, `github.getPRs`, wait — holding each result in context and reasoning about what to fetch next in natural language.

**After:** The model writes a JavaScript script that calls all the typed tool functions it needs, performs in-memory joins and deduplication, and returns a structured intermediate result. The sandbox executes it in one pass.

The tool invocation mode for Phase 2 becomes `code` instead of `structured`. The harness passes the typed tool API into the V8 isolate; the model's code calls those functions; nothing else is reachable.

### Phase 3 — Synthesize (now Code Mode)

**Before:** The model receives the gathered data in its context and uses natural-language reasoning to triage, rank, and format the daily brief / meeting prep / mail classification.

**After:** The model writes a script that performs the classification and ranking logic — urgency scoring, deduplication, source-citation assembly — and returns the structured brief. For judgment-heavy synthesis (the "why this needs you" annotations, credibility notes on research), the script can call back into the model via a `synthesize()` helper exposed in the sandbox, so the model still handles the parts that need judgment while code handles the parts that need data manipulation.

### Phase 4 — Side effects (NO CHANGE)

Phase 4 stays on structured tool calls with simulate-and-queue. Every action in the side-effects table (`chief-of-staff.md` §Side Effects) continues to go through the existing approval posture:

- Deny-list actions → draft-and-stop (unchanged)
- Simulate-and-queue actions → structured tool calls with simulated results, queued for batch approval (unchanged)
- Autonomous sandbox actions → unchanged

**Why:** Code Mode's sandbox prevents side effects by design (no ambient network), but that's the wrong reason to use it for actions. The simulate-and-queue convention requires each action to carry a `state` field (`simulated` → `approved` → `executed`) and participate in the rejection cascade. Structured tool calls map 1:1 to actions in the queue. A code block that fires three tool calls in a loop would need its own bookkeeping to track which actions are simulated vs. real, and that bookkeeping would duplicate what the gatekeeper already does. Keep the separation clean: Code Mode for data, structured calls for effects.

## Typed tool API mapping

Every MCP tool the Chief-of-Staff currently uses maps to a typed function in the V8 sandbox. The function signatures are the capability references — narrow, typed, purpose-specific — not raw API endpoints (per Source 119's object-capability pattern).

```typescript
// Slack — read-only in sandbox
async function slack_getThreads(params: {
  channel: string;
  since: string;      // ISO date
  limit?: number;
}): Promise<SlackThread[]>

async function slack_getThread(params: {
  channel: string;
  threadTs: string;
}): Promise<SlackMessage[]>

// Linear / Jira — read-only in sandbox
async function linear_getIssues(params: {
  project?: string;
  assignee?: string;
  state?: string;
  since?: string;
}): Promise<LinearIssue[]>

async function linear_getIssue(params: {
  id: string;
}): Promise<LinearIssue>

// GitHub — read-only in sandbox
async function github_getPRs(params: {
  repo: string;
  state?: "open" | "closed" | "merged";
  author?: string;
  since?: string;
}): Promise<GitHubPR[]>

async function github_getPR(params: {
  repo: string;
  number: number;
}): Promise<GitHubPR>

async function github_getReviewComments(params: {
  repo: string;
  prNumber: number;
}): Promise<GitHubComment[]>

// PagerDuty — read-only in sandbox
async function pagerduty_getIncidents(params: {
  since?: string;
  urgency?: "high" | "low";
  status?: "triggered" | "acknowledged" | "resolved";
}): Promise<PagerDutyIncident[]>

// Calendar — read-only in sandbox
async function calendar_getEvents(params: {
  since: string;
  until: string;
}): Promise<CalendarEvent[]>

// Mail — read-only in sandbox
async function mail_getMessages(params: {
  since: string;
  folder?: string;
  limit?: number;
}): Promise<MailMessage[]>

// Synthesis helper — calls back into the model for judgment tasks
async function synthesize(params: {
  instruction: string;
  data: any;
}): Promise<string>
```

Each function is implemented by the harness as a bridge: the sandbox calls `slack_getThreads(...)`, the harness translates that to the actual MCP tool call (holding the credential via vault → arbiter → proxy, per the persona's credential architecture), executes it, and returns the result to the sandbox. The model's code never sees a credential, a network socket, or a raw API endpoint.

**Capability references compose with Code Mode.** Source 119's insight is that extension code should receive narrow typed functions, not API keys with filtering proxies. Code Mode is the authoring surface for code that calls those functions. The two patterns are complementary: capability references define the shape of what's available; Code Mode defines how the model uses them.

## Sandbox requirements

The V8 isolate for Phases 2 and 3 must enforce:

1. **No ambient network.** The only way to reach an external system is through the typed functions above. No `fetch`, no `XMLHttpRequest`, no socket APIs.
2. **No filesystem.** The code can't read or write files. Journal writes (Phase 5) happen after the sandbox returns, via structured tool calls.
3. **No globals except typed functions.** The sandbox exposes the function set above and standard JavaScript built-ins (Array, Map, Set, Date, JSON, Math, RegExp, Promise). Nothing else.
4. **Execution timeout.** Per-wakeup token/time bound already exists in the harness contract. The sandbox inherits it — a runaway loop doesn't outlive the wakeup budget.
5. **Return value is the only output.** The script must return a structured result (the gathered data for Phase 2, the formatted brief for Phase 3). Side-channel output (console.log, stderr) is captured for debugging but not acted on.

## TaskContract field additions

The Chief-of-Staff's harness task contract gains two fields:

```yaml
# Added to the wakeup task envelope
tool_invocation_mode: "code"        # "code" for Phases 2-3, "structured" for Phase 4
code_mode_sandbox:
  runtime: "v8-isolate"
  network: "none"
  filesystem: "none"
  timeout_ms: inherit_from_wakeup_budget
  exposed_functions:
    - slack_getThreads
    - slack_getThread
    - linear_getIssues
    - linear_getIssue
    - github_getPRs
    - github_getPR
    - github_getReviewComments
    - pagerduty_getIncidents
    - calendar_getEvents
    - mail_getMessages
    - synthesize
```

The harness switches `tool_invocation_mode` between phases within a single wakeup: `code` for Phases 2 and 3, `structured` for Phase 4. The agent doesn't choose its own mode — the harness sets it per phase.

## Harness portability

Code Mode originates from the Vercel AI SDK (`mode: "code"` on `generateText`), but the pattern is portable. Any harness that can:

1. Spin up a V8 isolate (or equivalent sandboxed JS runtime — Deno, workers, etc.)
2. Inject typed functions as the only callable API
3. Execute model-generated JavaScript and return the result

...implements Code Mode regardless of whether it uses the Vercel SDK. The sandbox contract above (no network, no filesystem, typed functions only, timeout) is the spec — the Vercel SDK is one implementation.

If the harness you're building on doesn't support `mode: "code"` natively, the implementation path is:

1. Prompt the model to emit a JavaScript code block instead of a tool call
2. Extract the code block from the response
3. Execute it in a V8 isolate with the typed functions injected as globals
4. Feed the result back as if it were a tool call response

This is roughly what the Vercel SDK does internally. The important part is the sandbox enforcement, not the SDK.

## Implementation order

1. **Define the typed function signatures** — the TypeScript interfaces above, plus return-type schemas for each MCP tool's response shape. Test each one by calling the real MCP tool and verifying the return type matches.
2. **Build the sandbox bridge** — a V8 isolate (or Deno worker, or Cloudflare Worker-style runtime) that exposes the typed functions and translates calls to MCP tool invocations through the existing credential architecture.
3. **Add `tool_invocation_mode` to the task envelope** — the harness sets `code` for Phase 2 and Phase 3, `structured` for Phase 4, within a single wakeup.
4. **Update the persona prompt for Code Mode phases** — tell the model it's in Code Mode, give it the function signatures, tell it to return a structured result. Keep the Phase 4 prompt unchanged (structured tool calls, simulate-and-queue).
5. **Write eval scenarios** — at least 3 scenarios exercising Code Mode gathers:
   - Daily brief across all 5 systems with deduplication
   - Meeting prep with cross-referenced tickets and PRs
   - Mail triage with classification into attention tiers
6. **Run evals against current structured-call baseline** — compare accuracy, token usage, and round trips. Code Mode should show fewer round trips and equivalent or better accuracy on the data-join scenarios.
7. **Verify Phase 4 isolation** — confirm that a Code Mode phase cannot emit a side-effect action. The sandbox should reject any call that isn't in the `exposed_functions` list. Specifically: no `slack_postMessage`, no `linear_updateIssue`, no `mail_send` — those stay in Phase 4's structured tool calls only.

## What this does NOT change

- **Credential architecture.** Vault → arbiter → proxy rewrite stays exactly as specified. The sandbox bridge is just another consumer of the arbiter-issued token — it makes the MCP call on behalf of the code, and the code never sees the credential.
- **Side-effect posture.** Every action in the `## Side Effects` table keeps its current approval mode. Simulate-and-queue is untouched. Deny-list actions are untouched.
- **Memory and journal.** Phase 5 journal writes happen after the sandbox returns, via structured tool calls. The Hygienist's audit pass is unchanged.
- **The persona's identity and operating principles.** Code Mode is an execution mechanism for data gathering. It doesn't change what the agent does, who it is, or how it presents its output. The daily brief still cites sources, still frames outputs as analysis, still stops at decisions that belong to the human.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Model generates code that calls functions not in the exposed set | Sandbox rejects the call at runtime — the function doesn't exist in the isolate. Eval scenario #7 above tests this explicitly. |
| Model-generated code contains an infinite loop | Sandbox inherits the wakeup timeout. The harness kills the isolate on budget expiry, same as it would kill a long-running structured-call chain. |
| Code Mode accuracy is worse than structured calls for this persona | The eval in step 6 catches this before deployment. If Code Mode loses on the Chief-of-Staff's specific workload, don't ship it — the structured-call path stays as the fallback. |
| Harness doesn't support V8 isolates natively | The portable implementation path (§Harness portability) works with any JS runtime that supports function injection. Deno and Cloudflare Workers are two alternatives. |
| Phase boundary leak — Code Mode code attempts a side effect | The exposed function set contains only read functions and `synthesize`. No write function exists in the sandbox. A side effect would require a function that doesn't exist — the sandbox errors, the wakeup continues in structured mode for Phase 4. |

## Cross-references

- `personas/chief-of-staff.md` — the full persona spec; Phases 2, 3, and 4 definitions
- `conventions/simulate-and-queue.md` — the side-effect convention Phase 4 implements (unchanged by this proposal)
- Playbook Source 120 (Vercel AI SDK Code Mode) — the pattern and its benchmarks
- Playbook Source 119 (Morrell object-capability) — capability references as the typed function shape
- Architecture handoff Pattern 7 — Code Mode subsection with `TaskContract` fields
