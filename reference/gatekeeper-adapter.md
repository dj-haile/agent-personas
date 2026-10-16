# Gatekeeper Adapter — Simulate-and-Queue Reference Implementation

## Scope

This is a **spec-level reference**, not runnable infrastructure. It documents the interface, schema, and algorithm a harness must implement to support the [simulate-and-queue convention](../conventions/simulate-and-queue.md) — in the same relationship `reference/eval-review-agent.md` has to the Eval Auditor persona: a portable spec personas and harnesses can point at, not a library this repo ships. The queue, the simulation engine, and the cascade executor are harness concerns. **No persona spec implements this directly** — a persona declares its `## Side Effects` table (per the convention doc, §5) and calls `simulate`/`execute`/`rollback` as opaque harness-provided operations. If a persona spec starts reasoning about queue internals, dependency graphs, or ratchet state, that's a sign the boundary has been crossed.

---

## 1. The `GatekeeperAdapter` interface

Three operations. Every simulatable action type declared in the convention doc's contract (§2 there) routes through exactly these three — nothing else touches real side-effect systems.

```
simulate(request: ActionRequest) -> SimulatedResult
execute(request: ActionRequest) -> RealResult
rollback(request: ActionRequest) -> void
```

### `simulate(request) -> SimulatedResult`

- **Input:** an `ActionRequest` — action type (must match a key in the convention doc's `action_types` contract), parameters, and the `task_id` of any prior queue entries this request depends on.
- **Behavior:** does not touch the real system. Produces a placeholder result from the action type's `simulated_result` template (e.g., `"Draft PR #{number} queued — will open on approval"`), with template fields either interpolated from the request or left as provisional values (a simulated PR number, a simulated message timestamp) that the agent may reference in downstream reasoning.
- **Output:** a `SimulatedResult` — the interpolated placeholder plus enough structure for downstream requests to reference it (e.g., `{simulated_pr_number: 4821}`).
- **Precondition:** the action type must be `simulatable: true` in the contract. Calling `simulate` on a `simulatable: false` action type (email_send, credential_action) is a harness bug — those route to synchronous approval instead and never enter the queue as `simulated`.
- **Effect on state:** creates a new queue entry with `state: simulated` (per the convention doc's state vocabulary, §4).

### `execute(request) -> RealResult`

- **Input:** an `ActionRequest` whose corresponding queue entry is in `state: approved`.
- **Behavior:** performs the real action against the real system (opens the PR for real, posts the Slack message for real).
- **Output:** a `RealResult` — the actual system response (real PR number, real message timestamp), which replaces the simulated placeholder in the queue entry.
- **Precondition:** `state: approved`. Calling `execute` on anything else (`simulated`, `rejected`, `rolled_back`) is a harness bug — approval is the only gate between simulation and reality.
- **Effect on state:** transitions the entry to `state: executed`.

### `rollback(request) -> void`

- **Input:** an `ActionRequest` whose corresponding queue entry is in `state: executed` (or, for cascade purposes, any state that implies a real or believed-real effect exists).
- **Behavior:** invokes the action type's declared `rollback` mechanism (`close_pr`, `delete_message`, `revert_branch`, `revert_ticket_status`, `revert_file`, `cancel_meeting`). This is a real, effectful operation — it undoes a real action, not a simulated one.
- **Output:** none. Rollback is not expected to fail silently; a rollback failure is an escalation to the human, not a retry loop the harness resolves on its own.
- **Effect on state:** transitions the entry to `state: rolled_back`.

---

## 2. The approval queue schema

Every action, from `simulate` through its terminal state, is one row in the approval queue. A harness may store this however it likes (table, event log, document store) — the fields below are the contract.

| Field | Type | Description |
|---|---|---|
| `task_id` | string (unique) | Identifies this specific queued action. Referenced by other entries' `dependencies` and by the cascade algorithm (§3). |
| `agent_id` | string | Which persona/agent instance produced this action — the queue can hold entries from multiple concurrent agents. |
| `action` | object | `{type: <action_type key>, params: {...}}` — the action type must match a key in the convention doc's contract; `params` are the request's arguments (channel, PR title, branch name, etc.). |
| `simulated_result` | object \| null | The `SimulatedResult` from `simulate()`. Present from creation; overwritten by the `RealResult` once `execute()` runs (or left in place with a `real_result` field added — either representation is acceptable as long as the harness can distinguish which is which). |
| `dependencies` | array of `task_id` | Other queue entries this action's simulated result depended on. Empty for root actions. This is the edge set the cascade algorithm walks. |
| `human_decision` | enum \| null | `null` (undecided), `approved`, or `rejected`. Set once by a human; the queue does not let an agent set this field. |
| `state` | enum | One of `simulated`, `approved`, `executed`, `rejected`, `rolled_back` — per the convention doc's state vocabulary (§4). Derived from `human_decision` plus whether `execute`/`rollback` has run; not independently settable. |
| `timestamps` | object | `{simulated_at, decided_at, executed_at, rolled_back_at}` — each set once, when the corresponding transition happens; unset fields are `null`. |

`dependencies` is what makes the cascade possible — without it, a rejection can only invalidate the one row it targets, and the naive-implementation failure the convention doc warns about (§3 there) becomes the default behavior.

---

## 3. The rejection cascade algorithm

Concrete walk, run whenever a `human_decision: rejected` is recorded on a queue entry.

```
function reject(task_id, queue):
    entry = queue.get(task_id)
    if entry.state in ["rejected", "rolled_back"]:
        return   # terminal — already handled, directly or by an earlier cascade
    entry.human_decision = "rejected"
    entry.state = "rejected"

    # Build the dependent set: every entry whose `dependencies` includes
    # this task_id, transitively.
    to_cascade = topological_order(
        transitive_dependents(task_id, queue)
    )  # ordered so that an entry's dependents are processed
       # only after the entry itself has been marked

    for dep_entry in to_cascade:
        if dep_entry.state == "executed":
            rollback(dep_entry.action_request)   # real undo, per §1
        # simulated / approved entries have no real effect yet —
        # no system-level rollback call needed, only a state change
        dep_entry.state = "rolled_back"
        dep_entry.human_decision = "rejected"     # cascade-rejected, not human-decided directly
        notify_agent(dep_entry.agent_id, reason="upstream_rejection", cause=task_id)

    notify_agent(entry.agent_id, reason="rejected", cause=task_id)
    # The agent re-plans from the last approved state — it does not
    # attempt to salvage or patch forward the rolled-back branch of the plan.
```

**Ordering matters:** the walk must be topological over the dependency graph (upstream before downstream) so that an entry is never rolled back before the entry it depended on has been marked. A breadth-first or depth-first traversal that ignores edge direction can process a grandchild before its parent and momentarily leave the queue in an inconsistent state.

**Terminal states:** `executed` (without a later rollback) and `rolled_back` are the only terminal states an action can end in permanently. `rejected` is terminal for an action that never reached `executed` — nothing to roll back, it simply never happens. An action cannot re-enter `simulated` after reaching any of these; a retried action is a new `task_id` with a fresh dependency set (which may include the original, now-terminal entry as context, but is not the same row). The guard at the top of `reject()` enforces this: a call targeting an entry that is already `rejected` or `rolled_back` is a no-op, so a terminal state — and the `cause` recorded when it was assigned — is never overwritten by a later, redundant rejection.

**Distinguishing direct rejection from cascade rejection:** the algorithm above sets `human_decision: "rejected"` on cascaded entries even though no human reviewed them individually — this is intentional (a human should not have to separately reject every downstream action of something they already rejected), but the harness must record `cause` (the originating `task_id`) so an audit trail can distinguish "a human rejected this" from "this was cascaded from a rejection upstream." Collapsing that distinction in logs or reporting defeats the purpose of the audit trail.

---

## 4. Composition with the AAM Trust Ratchet (Source 84)

The Trust Ratchet is a separate mechanism from the approval queue — it tracks an agent's or session's trust level and can move it down (never back up within a session) on a triggering event (a policy violation, a detected injection, a human override of an autonomous action). Composition rule:

**A ratchet event during simulate-and-queue immediately moves every pending simulated action — for the affected agent — to `rejected`, regardless of dependency structure or individual review status. The ratchet overrides the queue.**

Concretely: a ratchet event is not a single `reject(task_id)` call. It is a bulk operation —

```
function on_ratchet_event(agent_id, queue):
    pending = queue.filter(agent_id=agent_id, state in ["simulated", "approved"])
    for entry in pending:
        reject(entry.task_id, queue)   # runs the full cascade from §3 on each
```

The sweep is order-independent because of `reject()`'s terminal-state guard (§3): if entry B in `pending` is a transitive dependent of entry A (also in `pending`), whichever is processed first cascades to the other, marking it `rolled_back` with its `cause` recorded — and the outer loop's later direct call on that entry is a no-op. Without the guard, the second call would overwrite the cascade-assigned `rolled_back` with a direct `rejected`, violating the terminal-state rule and making the final queue state depend on iteration order.

Why this has to be a queue-wide override rather than routed through normal per-action rejection: the ratchet fires because trust in the *agent*, not in any one action, has dropped. An agent whose trust has been ratcheted down cannot be trusted to have planned its still-pending queued actions correctly either — they were produced by the same compromised or misbehaving reasoning that triggered the ratchet. Reviewing them individually assumes the actions are independently trustworthy, which is exactly the assumption the ratchet event just invalidated. `approved`-but-not-yet-`executed` entries are included in the sweep for the same reason: approval was granted before the ratchet event, on the assumption the agent's context was sound at approval time.

This composition is why the queue's `state` field (§4 of the convention doc) and the cascade algorithm (§3 above) exist as agent-agnostic, harness-owned mechanisms rather than something a persona spec could reimplement per-persona — the ratchet needs one queue-wide sweep to be reliable, and that's only possible if every persona's queued actions live in the same schema and go through the same cascade path.

---

## Cross-references

- [conventions/simulate-and-queue.md](../conventions/simulate-and-queue.md) — the spec-facing convention: the three-position decision rule, the simulation contract per action type, the rejection cascade *rule* (this doc gives the algorithm), the `state` vocabulary, and the canonical `## Side Effects` block persona specs declare.
- **Source 84 (Cloudflare AAM):** origin of the Trust Ratchet and the Mediation Layer this adapter implements.
- **Source 87 (Cloudflare OS Gatekeepers):** the open-source (Apache-2.0) implementation this reference generalizes.

**What this does not cover:** the runtime that hosts this adapter — the actual queue storage, the simulation engine per external system (Slack API, GitHub API, ticket trackers), the scheduler that runs the cascade — is harness infrastructure. This doc specifies the interface and algorithm a harness implements; it is not itself that implementation.
