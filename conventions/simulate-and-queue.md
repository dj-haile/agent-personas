# Convention: Simulate-and-Queue

**Applies to:** any persona that takes external side-effect actions (Slack posts, PR/branch operations, ticket updates, meeting scheduling, doc/rule writes). Read-only or judgment-only personas (research, review, verification, audit, diagnostics) don't need this convention — they produce reports, not side effects.

**What it is:** a third approval posture between full autonomy and synchronous human approval. The agent executes its full workflow against **simulated** results for its side-effect actions, queues those actions for human review, and only performs the real action once a human approves. The human batches approvals instead of gating every action in real time.

**Provenance:** Source 84 (Cloudflare AAM) — the gatekeeper is one production implementation of AAM's Mediation Layer; the Trust Ratchet composes with this pattern (see [reference/gatekeeper-adapter.md](../reference/gatekeeper-adapter.md)). Source 87 (Cloudflare OS Gatekeepers) — the open-source reference implementation (Apache-2.0) this convention generalizes from. Motivating problem: Source 4 (Costa backpressure) names synchronous per-action approval "human as clipboard"; Source 5 (Osmani orchestration tax) names the same failure "human as GIL" — the human becomes the bottleneck the agent blocks on. Simulate-and-queue removes the agent from that blocking wait without removing the human from the decision.

---

## 1. The three-position decision rule

Every side-effect action a persona can take gets exactly one of three approval postures. This is a decision rule, not a preference — apply it action-by-action, not persona-by-persona (one persona can mix all three).

| Posture | When it applies | Mechanism |
|---|---|---|
| **Draft-and-stop** | Deny-list actions: never simulatable regardless of reversibility. External email, anything touching credentials, spending, or access grants. | Agent drafts, then blocks. Synchronous human approval is required before the action exists in any form. |
| **Simulate-and-queue** | Side-effect actions that are reversible or draftable. Opening a PR, posting to an internal Slack channel, scheduling a meeting, writing to a branch, updating a ticket status. | Agent receives a simulated success result, proceeds as if the action happened, and queues the real action for human batch review. |
| **Full autonomy** | Actions confined to the agent's own sandbox with no external observer. Writing to `thoughts/`, running tests in sandbox, reading the codebase. | No approval path at all — the harness doesn't gate it. |

**Decision test, in order:**
1. Is this action on the deny-list (credentials, spending, access, external communication)? → **draft-and-stop.** Stop here; do not evaluate the other two.
2. Does the action leave the agent's sandbox and affect state a human or another system observes? → **simulate-and-queue**, provided it is reversible or exists only as a draft until approved.
3. Otherwise (sandbox-confined, no external observer) → **full autonomy.**

The deny-list check runs first and is absolute: an action that is technically reversible (e.g., an email can theoretically be recalled) is still draft-and-stop if it is a deny-list category. Reversibility governs the choice *within* the simulate-and-queue bucket (which rollback to declare), not whether an action escapes the deny-list.

## 2. Simulation contract per action type

Each simulatable action type declares its contract: whether it's simulatable, the placeholder result the agent proceeds on, and its rollback. This is the base contract; personas may reference it directly rather than redefining action types locally.

```yaml
action_types:
  slack_post:
    simulatable: true
    simulated_result: "Message queued — will appear in #{channel} on approval"
    rollback: delete_message
  pr_open:
    simulatable: true
    simulated_result: "Draft PR #{number} queued — will open on approval"
    rollback: close_pr
  branch_write:
    simulatable: true
    simulated_result: "Commit queued on #{branch} — will push on approval"
    rollback: revert_branch
  ticket_update:
    simulatable: true
    simulated_result: "Status change to #{status} queued for #{ticket} — will apply on approval"
    rollback: revert_ticket_status
  email_send:
    simulatable: false  # deny-list — draft-and-stop
    fallback: synchronous_approval
  file_write_external:
    simulatable: true
    simulated_result: "Write queued for #{path}"
    rollback: revert_file
  credential_action:
    simulatable: false  # never simulate credential operations
    fallback: synchronous_approval
  meeting_schedule:
    simulatable: true
    simulated_result: "Meeting queued for #{time} with #{attendees}"
    rollback: cancel_meeting
```

`branch_write` and `ticket_update` extend the base set: the decision rule's own examples (§1) name "writing to a branch" and "updating a ticket status" as canonical simulate-and-queue actions, and both are distinct action types from `pr_open`/`file_write_external` (a branch commit is not a PR; a ticket status transition is an API call, not a file write) — declaring them separately keeps their rollback semantics (`revert_branch`, `revert_ticket_status`) from being papered over by an unrelated action type's rollback.

Any persona spec introducing a new external action type must add an entry here (or in a persona-local extension that inherits this contract) before shipping — an undeclared action type has no simulation posture and defaults to draft-and-stop.

## 3. The rejection cascade rule

Rejecting action N rolls back **every downstream action that depended on N's simulated result** — not just N itself. The agent is notified of the rejection and must re-plan from the last approved state; it does not attempt to patch the plan forward from a partially-invalidated one.

**Why this has to be automatic, not agent-judgment:** the agent's downstream actions were built on a placeholder (§4), not on ground truth. If action 3 assumed action 1's simulated PR number, and action 1 is rejected, action 3's assumption is now false — whether or not action 3 itself looks fine in isolation. The agent cannot be trusted to notice this on its own; the cascade has to walk the dependency graph mechanically. See [reference/gatekeeper-adapter.md](../reference/gatekeeper-adapter.md) for the concrete algorithm.

**The naive-implementation failure this rule exists to prevent:** an implementation that rejects action N but leaves N's *dependents* untouched leaks simulated state into real execution — the downstream actions execute for real against an assumption that was never approved. This is not a hypothetical edge case; it is the default outcome of any queue that tracks approval per-action without tracking the dependency edges between actions. The cascade is not an optional refinement — a queue without it is not simulate-and-queue, it's a queue with a bug.

## 4. The simulated-vs-real marker

Every action in the activity log carries a `state` field. This field is the only thing separating "the agent believes this happened" from "this actually happened," and both the agent's own reasoning and any downstream automation must key off it rather than off the action's mere presence in the log.

| State | Meaning |
|---|---|
| `simulated` | Action received a placeholder result from the simulation contract (§2). Not yet reviewed. The agent may plan and act as if it succeeded, but nothing external has happened. |
| `approved` | A human reviewed the simulated result and approved it. Queued for real execution; still not executed. |
| `executed` | The real action ran and its real result replaced the simulated one. This is the only state that means the effect is real. |
| `rejected` | A human reviewed the simulated result and declined it. Terminal for this action; triggers the cascade (§3) for its dependents. |
| `rolled_back` | The action was undone via its declared rollback (§2) — either because it was itself rejected after reaching `executed`, or because it was a dependent caught by a cascade from an upstream rejection. |
| `draft` | A **draft-and-stop** (deny-list) action was drafted and halted (§1). It is not in the queue and never enters it — a human must perform the action directly. This is the only legal state for a deny-list action in the log: it can never be `simulated`, `approved`, or `executed`, because those states mean "queued and pending" or "ran," and a deny-list action is neither. Terminal until the human acts outside the system. |

The first five states are the simulate-and-queue lifecycle; `draft` is the draft-and-stop marker (§1), added so every logged action — including a deny-list action that is drafted and never queued — has exactly one legal state. A deny-list action carrying any state other than `draft` is a contract violation.

**Why the distinction has to be load-bearing, not cosmetic:** an agent that treats `simulated` and `executed` as interchangeable will report work as done that hasn't happened, plan follow-on work against effects that don't exist yet, and — if the state field is dropped or ignored downstream — hand a human a queue that looks identical to an audit log of real actions. The state field is what keeps the agent's context honest about what's real; nothing about the log's shape enforces that on its own.

## 5. Canonical `## Side Effects` block

Any persona spec that takes external actions declares them in a `## Side Effects` section of its Agent Contract, using this table. This convention doc is the definition personas reference — the persona spec itself just fills in the rows.

| Column | Contents |
|---|---|
| **Action** | The external action, named at the same granularity as an action type in §2 (e.g., "Post to Slack," not "communicate with team"). |
| **Simulatable** | Yes / No, per §2's `simulatable` field for that action type. |
| **Approval mode** | One of the three postures from §1: `Simulate-and-queue`, `Draft-and-stop (deny-list)`, or `Autonomous (sandbox-only)`. |
| **Rollback** | The rollback mechanism from §2, or `N/A` for draft-and-stop and autonomous actions (nothing to roll back — draft-and-stop never executed; autonomous never left the sandbox). |

Example:

| Action | Simulatable | Approval mode | Rollback |
|---|---|---|---|
| Post to Slack | Yes | Simulate-and-queue | Delete message |
| Send external email | No | Draft-and-stop (deny-list) | N/A |
| Open draft PR | Yes | Simulate-and-queue | Close PR |

A persona with no external actions omits the section entirely rather than including it empty.

---

## Cross-references

- [reference/gatekeeper-adapter.md](../reference/gatekeeper-adapter.md) — the runtime-facing counterpart: the `GatekeeperAdapter` interface, the approval queue schema, the rejection cascade algorithm, and composition with the AAM Trust Ratchet.
- **Source 84 (Cloudflare AAM):** the gatekeeper generalized here is one production implementation of AAM's Mediation Layer; its Trust Ratchet overrides this queue on a ratchet event (detailed in the reference doc above).
- **Source 87 (Cloudflare OS Gatekeepers):** the open-source implementation (Apache-2.0) this convention is derived from.
- **Source 4 (Costa backpressure)** and **Source 5 (Osmani orchestration tax):** name the "human as clipboard" / "human as GIL" anti-pattern — synchronous per-action approval as a throughput bottleneck — that this convention exists to solve without removing human oversight.

**What this convention does not cover:** the runtime that implements it — the queue, the simulation engine, the cascade executor — is harness infrastructure, not a persona concern. See [reference/gatekeeper-adapter.md](../reference/gatekeeper-adapter.md) for the spec-level interface a harness implements; persona specs declare *posture* (this doc), not *mechanism*.
