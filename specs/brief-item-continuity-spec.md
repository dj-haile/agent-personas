# Spec: Brief-item continuity for the Chief-of-Staff daily brief

**Status:** Draft for review · **Author:** Spec Author persona · **Date:** 2026-08-30
**Governs work against:** `personas/chief-of-staff.md` v1.4 · `decisions/chief-of-staff-v0-readonly-deployment.md` (D1–D6 active)
**Placement note:** the persona's Output rule names `specs/<slug>-spec.md`; the dispatching task named `decisions/`. Filed in `decisions/` with the spec filename convention. It is a spec, not a decision record — plan and validation grade against it.

**Solution-neutral by construction.** This document states properties any design must have, and which candidate designs the stated constraints already eliminate. It does not select a file format, a data model, a matching algorithm, or a code path.

---

## 1. Problem statement

**Who has it.** One engineering leader (VP Engineering, new role starting 2026-08-31 or 2026-09-01 — see A11), running the Chief-of-Staff agent under the v0 read-only profile, reading one brief per morning across Slack, Linear, Gmail, Google Calendar and GitHub.

**The problem, stated precisely.** The agent already carries continuity — it has a journal, and journal entry `2026-08-28-16` is a same-day re-observation that explicitly corroborates four earlier entries. What it does not carry is an **open loop**. The journal records *claims about the world* ("the welcome message drew 12 reactions and no reply, 23 days on"), append-only, each with a TTL and a confidence score the agent is forbidden to update. A brief item is a different object: *a thing that is on the leader and is not finished yet*. It has a lifecycle, it changes state, and the change has to be recorded in place.

So the accurate framing is not "the agent has no memory." It is: **the agent has an immutable claim log and no mutable open-loop ledger, and the brief format has no section that carries anything forward.** The persona's report format (sections 1–6) is entirely present-tense. Nothing in the spec, the profile, the agent definition, or the journal schema names an item that persists across wakeups.

**Cost of not solving it.** Three costs, all observable today:

1. **Re-derivation without recognition.** Every morning the agent re-discovers the same open loops from raw sources and re-words them. The leader cannot tell a 40-day-old item from a new one, so age — the most useful signal for a "waiting on" item — is invisible.
2. **No completion signal.** Nothing records that the leader acted. An item he closed on Tuesday is presented again on Wednesday with the same urgency, which trains him to stop trusting the top section.
3. **Unbounded read cost by default.** The only continuity surface that exists is `journal.json`, read whole. On the observed write rate it becomes unaffordable to read daily within roughly two months (A8, AC-30).

**What the leader asked for, in his words:** "some things will be done and some will still be ongoing. This is how life works." He wants the agent aware of that, still able to answer what he asked for, and affordable to run daily.

### 1.1 The item taxonomy — the requester's two classes are refined into three

The requester proposed two classes: items backed by a system object with its own lifecycle, and items that exist only as the agent's judgment. Checked against the real corpus (`journal.json`, 27 entries; `trailmap-brief/trailmap.json`, 14 moves and 1 waiting chip), **the binary does not survive contact with the data.** The load-bearing axis is not "is there a system object" but **"is the closing act visible on a surface the agent already reads?"**

| Tier | Definition | Closure test | Examples from the live corpus |
|---|---|---|---|
| **A — object state** | A named object with its own lifecycle field. | Re-read the object; compare one field. | PR `deadlyvipers/dojo_rules#2163`, open since 2014-11-05 (journal 19); Linear DJ-1..DJ-4, all `Todo` (journal 05, 16). |
| **B — observable absence** | The claim is that something has *not* happened on a readable surface. No object, but there is a **query** whose result changes when the loop closes. | Re-run the recorded query; a non-empty result closes it. | "No reply to Theo Marsh's welcome, 23 days on" (journal 08) — closes when `dj-haile` posts in that thread. "No visible candidate referral in-channel" for Jordan Ellis (journal 14). "Give Lin Hao a date" (journal 07). "Connect work Slack/Gmail/Calendar" — closes when the connector binds. |
| **C — off-surface** | The closing act happens where the agent cannot read. | No observation will ever close it. Only the leader can. | "Ask security whether an AI agent may read Slack and mail" (`m_policy`). "Waiting on New employer IT — Datadog access" (`w_datadog`). A referral Ellis receives by DM or mail outside the connected surface. |

**Why the refinement matters, and what it costs to skip it.** The requester's class 2 collapses B and C. Both collapses fail:

- Treat all judgment items as C → every item needs a human hand-close. The leader will not maintain a to-do list by hand every morning; that is the thing the agent exists to remove. The feature degrades into stale noise within two weeks.
- Treat all judgment items as B → the agent reads silence as action and closes things that are still open, and reads a broken query as evidence of closure. Both failure modes are already documented at this deployment: journal 13 (Slack channel search returned 1 channel of 7; `#wins` was missed entirely by an earlier wakeup) and journal 21–22 (the GitHub token cannot read private-repo issues, and the repo list it returns is not the account's whole set).

**Tier B is the majority of the value and the whole of the risk.** It is also the tier the requester's framing has no separate name for.

### 1.2 What tier B requires that tier C does not

A tier-B item is only trackable if the **query that established the absence is stored with the item**, not just the prose conclusion. "Nobody replied" is not re-checkable. "`slack_read_thread` on `C014FKH7L4Q/p1785950299962259`, looking for a message from `U0BN18JH2DC`" is. The journal already gestures at this — entry 06 records `slack_read_channel on C079GJZPB7X, C0844KSMT0W, ...` — but as provenance for a past claim, not as a re-runnable closure test.

---

## 2. Desired outcome

Stated as the leader would check it, on an ordinary morning in month four:

- The brief opens with what needs him today, ranked exactly as ruthlessly as now, capped at five, and **not padded with old items just because they are old.**
- Anything carried over says so, with the date he first saw it and the date it was last checked — so a 40-day-old waiting item reads as 40 days old, not as news.
- Things he finished stop appearing. A short trailing window shows what closed since he last looked, then those disappear too.
- When the agent closes something on its own, it shows the evidence, and he can click it.
- When the agent cannot check something any more — a channel he removed, a repo the token lost — it says so instead of guessing.
- If he tells the agent "that one's done" or "that was never mine," it stays that way. It does not come back next week.
- The tracking never makes the morning run noticeably more expensive, and the cost does not grow as the months accumulate.

---

## 3. Acceptance criteria

Each criterion is independently testable, as a replay or single-wakeup check against the delivered brief and the item state the agent wrote.

### 3.1 Identity (AC-1 … AC-9)

**AC-1 — Identity survives re-wording.** *Given* an item first surfaced on day 1 as "Jordan Ellis asked for VP-infra referrals and none have been posted," *when* the brief on day 40 surfaces the same underlying loop with different wording, *then* the item carries the same identifier as on day 1. *Test:* two briefs against fixtures differing only in surface phrasing; assert identifier equality.

**AC-2 — Identity is never derived from a similarity judgment over brief prose.** *Given* two open items with near-identical labels and disjoint cited sources, *when* the agent processes a wakeup, *then* the two remain distinct and are never merged. *Test:* fixture with two near-identical labels and no shared source; assert two distinct identifiers survive ten simulated wakeups. *Rationale (not a mandated mechanism):* cross-item confusion is already observed within a **single** brief — journal entry 11 records the agent attaching Jordan Ellis's 15-day interval to Carl Brandt's separate ask. Any scheme that re-establishes identity by comparing regenerated prose inherits that failure and compounds it over months.

**AC-3 — Every item declares its anchor set.** *Given* any item in any state, *when* the leader inspects it, *then* it names zero or more **anchors** — the source references the persona's citation rule already produces (permalink, PR URL, issue key, thread timestamp, monitor ID) — and the anchor count is visible.

**AC-4 — Anchorless items are minted once and never re-minted.** *Given* a tier-C item with an empty anchor set, *when* the same loop is still open on any later wakeup, *then* no second item is created for it. *Test:* replay twenty wakeups against an unchanged fixture; assert total item count is stable and no identifier appears twice.

**AC-5 — Anchor overlap forces a decision, never a silent merge.** *Given* a newly derived loop whose anchor set intersects an existing open item's but is not identical, *when* the brief is produced, *then* the agent either matches it to the existing item or surfaces a **possible duplicate** naming both identifiers — never a silent new item. *Test:* fixture with partial anchor overlap; assert an explicit duplicate-candidate line naming two identifiers.

**AC-6 — Identifiers are visible to the leader.** *Given* any item rendered in a brief, *then* the identifier is present in the rendered text, in a form he can quote back in the next wakeup task.

**AC-7 — Labels do not change silently.** *Given* an item whose label the agent revises between wakeups, *then* the brief carries an explicit amendment line showing the prior label and the new one. *Test:* replay two wakeups with changed underlying facts; diff labels by identifier; assert every change has an amendment line.

**AC-8 — Identity assignment is not affected by ranking.** *Given* an item in "Needs you today" on day 1 and in cross-system synthesis on day 5, *then* the identifier is unchanged.

**AC-9 (negative) — No identifier is ever reused.** *Given* an item that reached a terminal state, *when* any later item is created, *then* its identifier differs from every identifier ever issued, including terminal ones.

### 3.2 State and transitions (AC-10 … AC-19)

States are named as **observable conditions the leader can see and check**, not as a storage schema.

| State | Means | Who may set it |
|---|---|---|
| `open` | Surfaced, not finished. | Agent (on first sighting) |
| `closed-observed` | The agent observed the closure evidence it declared in advance. | Agent |
| `closed-by-operator` | The leader said it is done. | Leader only |
| `dismissed` | The leader said it was never his, or not worth tracking. Never counted as a completion. | Leader only |
| `unverifiable` | The declared closure test can no longer be run (lost channel access, deleted thread, token scope change). | Agent |
| `dormant` | Open, unchanged, untouched by the leader for the dormancy interval. Leaves the wakeup read set; still retrievable. | Agent |
| `merged-into <id>` | Folded into another item after a confirmed duplicate. | Leader confirms; agent may only propose |

**AC-10 — Closure evidence is declared before it is used.** *Given* any item in `open`, *when* it is created, *then* it carries a closure test stated concretely enough that a second party can run it — tier A: the object and the field; tier B: the query and the result that counts as closure; tier C: an explicit "operator only."

**AC-11 — The agent closes only on its declared evidence.** *Given* an item whose declared closure test has not produced its closure result, *then* it does not move to `closed-observed` under any other reasoning. *Test:* fixture where the topic stops being mentioned anywhere but the closure test still returns "not closed"; assert the item stays `open`.

**AC-12 (negative) — Absence from a sweep is never closure.** *Given* an item whose anchoring surface is unreachable this wakeup — channel removed from the allowlist, repo outside the token's grant, thread deleted — *then* the item moves to `unverifiable` and the brief states why; it does **not** move to any closed state and does **not** silently remain `open` as if checked. *Test:* remove one channel from the readable set between two wakeups; assert `unverifiable` with a stated reason. *Why:* the two documented read-coverage failures at this deployment (journal 13; journal 21–22) both produce exactly the input this guards against.

**AC-13 — Operator state outranks agent state, permanently.** *Given* an item the leader set to `closed-by-operator` or `dismissed`, *then* the agent does not change that state, and does not create a new item for the same anchor set. *Test:* dismiss an item; replay thirty wakeups with the underlying condition still visibly true; assert no state change and no new item.

**AC-14 — New activity on a dismissed anchor is reported at most once, and creates nothing.** *Given* a `dismissed` item whose anchor shows new activity, *then* the brief mentions it once, labeled as activity on a dismissed item, and creates no open item; it is not mentioned again unless the leader reopens it. *Test:* replay three wakeups after new activity; assert exactly one mention.

**AC-15 — Reopening requires the leader.** *Given* any closed, dismissed or merged item, *when* the leader says to reopen it in a wakeup task, *then* it returns to `open` with the reopening date recorded. No other input produces a reopen.

**AC-16 — Dormancy is time-based, visible, and reversible.** *Given* an `open` item with no state change and no operator touch for the dormancy interval (default 21 days — A15/OQ-4), *then* it moves to `dormant`, leaves the brief body, and appears in the periodic dormancy digest with its first-seen date.

**AC-17 — Merge is proposed, not performed.** *Given* the agent judges two open items to be the same loop, *then* it renders a merge proposal naming both identifiers and both anchor sets, and both items remain separate until the leader confirms. *Test:* fixture with a true duplicate; assert two items still exist after the brief, plus a proposal line.

**AC-18 — Every transition carries its date and its cause.** *Given* any item that changed state, *then* the record names the date of the change and the evidence or operator instruction that caused it.

**AC-19 (negative) — The agent never scores an item's confidence and never extends its life.** *Given* any item, *when* the agent writes to it, *then* it writes no confidence value and no expiry extension. Item longevity is governed by the dormancy rule and the leader, never by an agent judgment about how much it believes the item.

### 3.3 What the leader sees — reconciling "disappear" with "recent completions" (AC-20 … AC-29)

The two requests are not in conflict once the visible-completion window is time-boxed. The leader's own tool already models this: Trailmap keeps done items on Today, struck through, until the day rolls over, and reports momentum as "N moves shipped this quarter · M this week."

**AC-20 — Carried items are marked as carried, with two dates.** *Given* an item first seen before today, *when* it appears in any brief section, *then* the line carries its first-seen date and its last-verified date, and does not read as a fresh observation. *Why:* the persona already requires the date behind every age. Continuity sharpens this — a label written on day 1 is re-rendered on day 40 with the authority of freshness unless the dates travel with it.

**AC-21 — A trailing closed window exists, then closures vanish.** *Given* items closed within the closed-window (default 7 days — A15/OQ-4), *then* they appear in a dedicated closed section with their closure evidence; items closed before that window appear nowhere in the brief body. *Test:* closures at 2 days and 30 days; assert the first appears, the second does not.

**AC-22 — Completion counts remain retrievable after items leave the brief.** *Given* items closed more than the closed-window ago, *when* the leader asks for progress over a period, *then* the agent reports those closures with identifiers and closure dates.

**AC-23 — Counts follow the persona's count rule.** *Given* the closed section or any carried-item list, *then* no quantity word precedes the list it counts; any count appears after the list and matches it exactly. *Why:* this is the persona's single most repeated graded defect — seven instances across 2026-08-28 and 2026-08-29, plus a count inside a parenthetical on 2026-08-30. New list-bearing sections are new instances of the same hazard.

**AC-24 (negative) — Age alone never promotes an item into "Needs you today."** *Given* an item open for 40 days meeting none of the agent definition's four escalation criteria (blocked on this specific person; degrading now and unowned; deadline inside 48 hours; quietly consequential), *then* it does not appear in "Needs you today." *Why:* this is the primary way the feature fails. Continuity that quietly converts the top section into a nag list destroys the ranking discipline that is the brief's whole value.

**AC-25 — "Needs you today" stays capped.** *Given* any brief with carried items present, *then* section 1 contains at most five items.

**AC-26 — Every carried item still cites a source.** A stored identifier is not a substitute for a citation.

**AC-27 — Unverifiable items are visible, not hidden.** *Given* items in `unverifiable`, *then* the brief lists them with the reason each check failed, so the leader can restore access or close them by hand.

**AC-28 — Age arithmetic in item lines is mechanically checkable.** *Given* any rendered elapsed time on a carried item, *when* checked against the two dates it derives from, *then* the arithmetic is correct; where the wakeup envelope states no timezone, the line says so. *Note:* the 2026-08-30 round-two run concluded this defect class does not respond to spec rules and needs a post-generation check in the harness. Continuity multiplies computed ages per brief, so this criterion depends on D-5 rather than on instruction holding.

**AC-29 (negative) — No item line asserts anything about the leader that its sources do not say.** No attendance, approval, ownership or receipt absent from the cited sources. *Why:* carried items are re-rendered many times from a label written once. One invented attribution on day 1 gets repeated for months.

### 3.4 Scale and read budget (AC-30 … AC-37)

**AC-30 — The wakeup read set is flat with respect to deployment age.** *Given* the deployment on day 180, *when* a wakeup runs, *then* the tracking state read is no greater than on day 14, assuming the open-item count is within cap. *Test:* simulate 180 days of item creation and closure at a measured rate; measure tokens read on day 14 and day 180; assert day 180 ≤ day 14 × 1.1. **This is the load-bearing scale criterion.**

**AC-31 — The wakeup read set is exactly definable, and everything else is excluded.** *Given* a wakeup, *then* the agent reads exactly: items in `open`, plus items closed within the closed-window. Items in `dormant`, `dismissed`, `merged-into`, and closures older than the window are not read. **This is the concrete rule requested in place of "archive old items."** Nothing is archived by age of the item; records leave the read set by **state**, and state changes by two time-based rules (dormancy at 21 days untouched; closures leaving at 7 days) plus operator action.

**AC-32 — A hard cap on open items exists and overflow surfaces rather than truncates.** *Given* the open-item count reaches the cap (default 40 — A15/OQ-4), *when* the next item would be created, *then* the brief surfaces the overflow to the leader as an item requiring his triage, and no existing item is silently dropped.

**AC-33 — The tracking read has a stated token budget.** *Given* any wakeup at any deployment age, *then* tracking state consumes no more than the per-wakeup budget (default ≤ 8,000 tokens — A15/OQ-4). *Derivation of the default:* a cap of 40 open items plus roughly ten recent closures, at a per-item record holding an identifier, a label, one or two anchors, a state, two dates, a tier and a closure test. 8,000 tokens is under 10% of what `journal.json` alone would cost per wakeup after one month at the observed write rate (A8).

**AC-34 — Net document load per wakeup increases by at most one file.** *Given* the design in operation, *then* documents loaded per dispatch exceed the current baseline (persona spec, deployment profile, agent definition, journal) by no more than one. *Why:* measured on this deployment, cache writes were 58% of spend across 27 runs on 2026-08-28 to 2026-08-29 ($41–55 total at Opus 5 rates), cache reads 34%, output 8%, uncached input under 1%. The eval run's own conclusion: "the expense is fresh agents loading governing documents and fixtures, not agents thinking." Document count per dispatch is the cost lever.

**AC-35 — The journal read is bounded too, or the saving is cancelled.** *Given* a wakeup, *then* the agent reads a bounded subset of the journal (the live, in-TTL set), not the whole file. *Test:* a journal with 300 entries of which 40 are live; assert the read is proportional to the live set, not the file. *Why:* the journal is read whole today. A bounded item store beside an unbounded journal read does not solve the cost problem; it adds to it.

**AC-36 (negative, structural) — No design adds a per-item, per-wakeup append.** *Given* an item open for 30 wakeups with no change, *then* the tracking state holds one record for it, not 30. **This criterion tests store structure rather than delivered behavior.** It is stated because the shape is the mechanism behind AC-30, and because the journal's append-only, no-self-update discipline already produces exactly this shape — entry `2026-08-28-16` is a separate entry re-observing entries 04, 05, 06 and 08 because the agent may not increment their observation counts. Correct for a claim log, catastrophic for an item ledger. Drop it if AC-30 can be measured directly on the real deployment.

**AC-37 — Growth is measured in week one and the defaults revisited.** *Given* seven consecutive real briefs, *then* item creation rate, closure rate by tier, and peak open-item count are reported, and the cap, dormancy interval and closed-window defaults are confirmed or changed against those numbers.

### 3.5 Wrong-item risk and correction (AC-40 … AC-46)

**AC-40 — Conflation is visible in the brief.** *Given* an item whose anchor set contains anchors from unrelated sources, *then* all its anchors render on the line, so a wrong merge is apparent without opening any file.

**AC-41 — Every correction channel is durable.** *Given* the leader states a correction in a wakeup task ("close CS-14," "CS-9 and CS-22 are the same," "CS-31 was never mine"), *then* it is recorded in tracking state and survives every later wakeup without restatement. *Test:* state once; replay ten wakeups; assert it still holds.

**AC-42 — Direct editing by the leader is supported and not clobbered.** *Given* the leader edits tracking state by hand between wakeups, *then* the next wakeup reads and honors it, and no agent-generated output overwrites it. *Why this is a criterion, not an assumption:* the current Trailmap export path fails exactly this. `brief-to-trailmap.py` writes `trailmap.json` wholesale from a generated source document, `move()` defaults `done` to `False`, and there is no read-merge step anywhere in the script. Any completion checked off in the app is reset on the next export.

**AC-43 — A wrong closure is correctable in one instruction.** *Given* an item the agent moved to `closed-observed` in error, *when* the leader says so in the next wakeup task, *then* it returns to `open`, the erroneous closure evidence is retained in its history, and the same evidence does not re-close it. *Test:* reopen; replay five wakeups with the same evidence present; assert it stays open.

**AC-44 — Resurrection is impossible without the leader.** Covered by AC-13 and AC-14; restated because it is the requester's named risk. The check: no sequence of agent-only wakeups moves an item out of `dismissed` or `closed-by-operator`.

**AC-45 — Duplicate creation is detectable by the leader in the brief.** *Given* two items that are in fact one loop, minted separately, *then* both identifiers and both anchor sets are visible in the same brief.

**AC-46 (negative) — The agent never asserts an item is closed without rendering the evidence.** A closure with no rendered, checkable citation does not ship.

### 3.6 Where state lives — constraints on any store (AC-50 … AC-55)

**The Planner selects the store. This section states properties it must have and records which candidates the properties eliminate.** AC-51, AC-52 and AC-54 test structure rather than delivered behavior; they are stated because the cost constraint (AC-30) and the visible-disappearance requirement (AC-16) make structure observable in the output.

**AC-50 — No connected system is written to.** *Given* the v0 profile, *when* tracking state is written, *then* the target is a local file. No Linear issue, Slack message, GitHub object, calendar event, or Gmail draft is created or modified. *Test:* the runbook's 5c smoke test, extended to tracking writes.

**AC-51 — State supports in-place transition.** Append-per-wakeup designs fail AC-36.

**AC-52 — Item lifetime is not governed by TTL decay.** *Given* an item open longer than any journal TTL, *when* the TTL sweep runs, *then* the item does not expire out of existence. Items age into `dormant` visibly (AC-16); they do not silently disappear.

**AC-53 — Tracking state is inspectable by the leader outside the agent.** *Given* the leader opens tracking state directly, *then* he can read every item's state, dates, anchors and closure test without running the agent.

**AC-54 — Concurrent human and agent writes cannot silently lose either side.** *Given* the leader edited tracking state while a wakeup was in flight, *then* neither write is silently lost; a conflict is surfaced.

**AC-55 (negative) — Tracking state does not leak the leader's private judgments into a shared workspace.** *Given* items whose labels hold judgments about named colleagues ("nobody has sent Ellis a referral"), *then* they are not stored in any multi-tenant or employer-visible system.

#### Candidate stores, and what the criteria do to them

| Candidate | Verdict | Why |
|---|---|---|
| **Linear (or the employer's tracker)** | **Eliminated by constraint, not judgment.** | Fails AC-50 outright — the agent has no write path, enforced by the tool allowlist in `claude-agents/chief-of-staff.md`, which omits `save_issue` and omits `ToolSearch`. Independently fails AC-55: personal open loops holding judgments about colleagues would sit in the company's shared tracker. Two disqualifiers, either sufficient. |
| **`journal.json`** | **Eliminated.** | Fails AC-51 (append-only claim log; the agent may not update entries in place — journal 16 and 18 both explicitly decline to, correctly). Fails AC-36 for the same reason. Fails AC-52 (journal entries expire by TTL; a live open loop must not). Fails AC-30 by arithmetic: 27 entries across 3 wakeups on 2026-08-28 is 9 per wakeup; `journal.json` holds those 27 entries in 357 lines, about 13 lines per entry; at one wakeup per day that is roughly 270 entries and 3,600 lines per month, and about 21,400 lines by month six. Read whole every morning, that is the "large file at every wakeup" the requester identified as expensive by construction. |
| **Trailmap's data file** | **Eliminated as the system of record. Retained as a view.** | Fails AC-53/AC-3: the schema validated by `brief-to-trailmap.py` has no field for a source link, a stable identifier across regeneration, a closure test, or any state beyond `done: bool` and a `since` date. Fails AC-42 today (wholesale rewrite, `done` defaults `False`, no read-merge). Fails AC-54: the app reloads on external edit and, on a collision, snapshots both versions and asks which wins — a real conflict path between agent writes and in-app edits. **What it is good at:** it already encodes aging thresholds (amber at 5 days, red at 10), a visible-item cap (top 3 open moves per initiative), a 7-day "this week" window, and a same-day trophy shelf. Right place to *see* items, wrong place to *keep* them. |
| **A local store the agent owns, separate from the journal** | **The only candidate the criteria leave standing.** | Satisfies AC-50 (local write is the one permitted write, logged `sandbox`), AC-51, AC-52, AC-53, and AC-30/31 given the cap and the state-based read set. Costs one additional file per dispatch, which AC-34 budgets for and AC-35 offsets by bounding the journal read. |

**Not specified here, deliberately:** the file's format, its path, its record shape, how identifiers are constructed, how the Trailmap view is regenerated from it, and how conflicts are surfaced.

### 3.7 Boundary with the Memory Hygienist (AC-60 … AC-65)

**Recommendation: items are a distinct artifact class from journal entries, governed by the Hygienist on the same schedule but under different rules.** The reasoning, since the requester asked for it rather than a verdict:

A journal entry is *the agent's claim about the world, with the agent's own confidence in it*. An item is *an open loop, with externally checkable evidence for its state*. The no-self-grading rule exists because a drifted agent that can adjust its own confidence can launder its beliefs clean. That hazard applies fully to confidence and fully to revival. It does **not** apply the same way to a state transition carrying checkable evidence — "this PR now reads merged, here is the link" is the opposite of ungraded self-promotion, because the leader verifies it in one click and AC-46 forces the evidence to be rendered.

But item state is not outside memory either. "This item is still open" is a claim carried across time, and it can go silently wrong. So the split:

**AC-60 — The agent may write item state transitions, and only with rendered evidence or an operator instruction.** Permitted agent transitions: `open` → `closed-observed` (declared evidence only), `open` → `unverifiable`, `open` → `dormant`, and *proposing* a merge.

**AC-61 (negative) — The agent may not write confidence on an item, extend an item's life, reopen an item, revive a dismissed item, or confirm its own merge proposal.** *Test:* inspect every agent-written change across a replay; assert none is any of those five.

**AC-62 — The Hygienist owns the item audit, on the same monthly schedule as the journal audit.** Item-side scope: duplicate and merge audit across the open set; items whose rendered evidence no longer supports their state; items stuck in `unverifiable`; cap-pressure and dormancy-rate reporting; escalation if the agent appears to have closed something on evidence that did not support closure. *Test:* run against a corpus with one wrongly closed item and one duplicate pair; assert both reported with reasons.

**AC-63 — One journal claim spawns at most one item, and most spawn none.** *Test:* against the existing 27-entry corpus, assert that entries 13, 20, 21 and 22 (method corrections and evidence ceilings) produce no item, while entries 07 and 08 each produce exactly one.

**AC-64 — The journal remains the system of record for claims; the item store never becomes a second claim log.** *Given* an item record, *then* it holds identity, anchors, tier, state, dates, closure test and a short label — not analysis, not confidence, not observation counts. *Why:* this is what keeps AC-33's budget achievable.

**AC-65 — Hygienist audit dependency is stated, not assumed.** *Given* profile deviation D5 (the monthly audit is operator-triggered in v0), *when* the audit has not run for more than one interval, *then* the brief says so once.

### 3.8 Staged delivery — what week one gets (AC-70 … AC-75)

The leader starts 2026-08-31 or 2026-09-01 (A11). The runbook already prescribes running the brief manually each morning for week one. Continuity must fit inside that week with no new infrastructure.

**AC-70 — Week one (stage 1) requires no automatic closure at all.** *Given* stage 1, *when* a brief runs, *then* items are minted with identifiers, anchors, tier, first-seen date and a stated closure test; they render as carried with their dates; and **closure comes only from the leader's instruction in the wakeup task.** No agent-observed closure is enabled. *Test:* stage-1 replay; assert zero `closed-observed` transitions. *Rationale:* stage 1's purpose is to collect the corpus that sets the numbers in A15 — tier mix, creation rate, closure rate, peak open count — before any automatic behavior is tuned against guesses.

**AC-71 — Stage 1 satisfies AC-1 … AC-9, AC-13, AC-20, AC-21, AC-26, AC-41, AC-50, AC-53.** Identity, operator-set state durability, carried-item rendering, the closed window, citations, corrections, no-write and inspectability all hold from day one. These are the criteria that are expensive to retrofit.

**AC-72 — Stage 2 (weeks 2–4) adds agent-observed closure for tiers A and B, dormancy, and the cap.** AC-10, AC-11, AC-12, AC-16, AC-27, AC-31, AC-32 hold. *Gate:* stage 2 does not begin until AC-37's week-one measurement exists.

**AC-73 — Stage 3 (from the first monthly audit) adds the Hygienist item audit.** AC-62 holds from the first Monday audit, per the runbook's calendar hold.

**AC-74 — Each stage is independently gradeable.** Criteria out of scope for a stage are marked deferred, not failed.

**AC-75 (negative) — No stage requires provisioning, IT tickets, a bot identity, or the harness queue.** *Why:* the leader's week one has no slack for that, and the profile's §6 migration is explicitly deferred.

---

## 4. Scope boundaries

### Explicitly in

- Item identity, state and lifecycle across briefs, for all three tiers.
- The read-set rule that bounds per-wakeup cost, and the states that implement it.
- Rendering rules for carried and recently-closed items, including two new list-bearing sections and the dates that must travel with them.
- Correction paths for wrong identity and wrong state, and their durability.
- The boundary between item state and journal memory, and the Hygienist's item-side scope.
- Constraints on any store, and elimination of candidates that violate them.
- Staging, with week-one scope explicitly bounded.

### Explicitly out

- **Any write to a connected system.** Not in this spec, not in any stage.
- **Choosing the store's format, path or record shape.** Planner's decision, judged against §3.6.
- **The identifier construction scheme and the matching algorithm.** Planner's, judged against §3.1.
- **Changes to Trailmap the application** — schema, renderer, storage contract. If the view needs fields Trailmap lacks, that is a finding to raise, not work this spec authorizes.
- **A notification or reminder system.** Trailmap already fires waiting-chip and due-date notifications.
- **A conversational "mark done" interface** beyond stating corrections in the wakeup task.
- **Re-ranking rules.** The four escalation criteria in the agent definition are unchanged; AC-24 forbids continuity from altering them.
- **Multi-user, shared or synced item state.** One leader, one machine.
- **Changes to journal entry semantics** — TTL, confidence, count-weighting and the no-self-grading rule are untouched.
- **The post-generation numeric validator** (recommended by the 2026-08-30 run, depended on by AC-28, specified elsewhere).
- **Retroactive item creation from the existing 27-entry journal corpus** — pending OQ-6.

---

## 5. Assumptions

| # | Assumption | Status | Evidence / owner |
|---|---|---|---|
| A1 | Brief items divide into three closure tiers, not two. | **Verified** | Classified every item in `trailmap-brief/trailmap.json` (14 moves, 1 waiting chip) and every claim in `journal.json` (27 entries). Tier B items — the welcome reply, the Ellis referral, the Lin Hao date, the connector tasks — have no system object but do have a re-runnable query. |
| A2 | Judgment items (tiers B and C) are the majority. | **Verified for the current corpus; needs re-confirmation at the real employer.** | None of the 14 current moves is backed by a live work-tracker object — Linear holds only four stock onboarding issues (journal 05, 16) and GitHub shows nothing blocked on the leader (journal 19). This is a week-zero artifact; tier A grows once the employer's systems connect. Owner: re-measure at AC-37. |
| A3 | An anchor already exists for most items at zero extra cost. | **Verified** | Persona hard rule ("every line cites its source or it doesn't ship"); every journal entry carries a `sources` array; the 2026-08-29 and 2026-08-30 blind grades both confirm source links held on every line. |
| A4 | Some items have no readable anchor at all. | **Verified** | `m_policy` and `w_datadog` in the current export. Neither has a source object. |
| A5 | The current Trailmap export regenerates wholesale and resets hand-marked completions. | **Verified** | `brief-to-trailmap.py`: `write()` serializes the whole doc; `move()` sets `done=False` by default; no read of the existing file anywhere in the script. |
| A6 | The agent cannot write to any connected system. | **Verified** | Profile §3–§4; the `tools:` list in `claude-agents/chief-of-staff.md` contains only read tools and omits `ToolSearch`. |
| A7 | The agent can write local files. | **Verified** | `Write` is in the tool list; the journal write is the profile's `sandbox` action state. |
| A8 | Reading the journal whole becomes unaffordable within roughly two months. | **Needs-confirmation** | Extrapolated from a single day: 27 entries across 3 wakeups on 2026-08-28 = 9 per wakeup; 357 file lines ÷ 27 entries ≈ 13 lines per entry; at 1 wakeup/day ≈ 270 entries and ≈ 3,600 lines per month. One day is not a rate. Owner: measure across week one (AC-37). |
| A9 | Per-wakeup cost is dominated by document loading, not reasoning. | **Verified** | 2026-08-29 eval run, Cost section: 27 runs, $41–55, cache writes 58%, cache reads 34%, output 8%, uncached input <1%. |
| A10 | The leader will state closures in the wakeup task during week one. | **Needs-confirmation** | The single behavioral assumption stage 1 rests on. If he will not, stage 1 produces an ever-growing open list and no closure signal. Owner: Dj. |
| A11 | The new role starts 2026-09-01. | **Needs-confirmation** | Journal entry `2026-08-28-02` says Monday 2026-08-31, sourced to the leader's own DM and corroborated by a `#general` welcome. The dispatching task says 2026-09-01. Low stakes, but the staging plan hangs on it. Owner: Dj. |
| A12 | Arithmetic in prose is an unresolved defect class that rules have not fixed. | **Verified** | 2026-08-28 (five unsupported specifics), 2026-08-29 (two count failures), 2026-08-30 (a wrong timestamp subtraction, a count in a parenthetical, a wrong day-count label). The 2026-08-30 run concludes it needs a mechanical check, not another rule. |
| A13 | Read coverage is unreliable in ways that will break tier-B closure checks. | **Verified** | Journal 13 (Slack channel search returned 1 of 7 channels; `#wins` missed by a prior wakeup), journal 21 (private-repo issues unreadable by the token), journal 22 (repo list is not the account's whole set). |
| A14 | The Hygienist audit is operator-triggered in v0. | **Verified** | Profile deviation D5; runbook step 4 (calendar hold, first Monday monthly). |
| A15 | The defaults (cap 40, dormancy 21 days, closed-window 7 days, budget 8,000 tokens) are starting points, not derived facts. | **Needs-confirmation** | Cap and window shapes are borrowed from Trailmap's own calibrated constants — chips amber at 5 days and red at 10, top-3 visible moves, a 7-day "this week" window. The specific values are guesses until AC-37. Owner: Dj. |
| A16 | Item state carrying rendered evidence is materially different from journal confidence, and does not violate the no-self-grading rule. | **Needs-confirmation — a judgment call the leader owns.** | Argued in §3.7. The counter-argument is real: "this item is still open" is a belief carried across time, and drift applies. AC-61 is written to make the conservative reading safe either way. Owner: Dj. |

---

## 6. Dependencies

| # | Depends on | Why | Blocking? |
|---|---|---|---|
| D-1 | The leader stating closures in the wakeup task (A10) | Stage 1 has no other closure path. | Blocking for stage 1 |
| D-2 | Week-one measurement of tier mix, creation rate, closure rate, peak open count (AC-37) | Sets the numbers in A15. Stage 2 is gated on it. | Blocking for stage 2 |
| D-3 | The wakeup task envelope carrying a slot for operator corrections | AC-41 needs a channel that exists. Envelope shape is set by the harness/runbook. | Blocking for AC-41 |
| D-4 | The Hygienist's monthly audit actually running (A14, profile D5) | AC-62, AC-65. Operator-triggered in v0. | Blocking for stage 3 |
| D-5 | The harness post-generation numeric validator recommended on 2026-08-30 | AC-28. The defect class does not respond to spec rules. | Non-blocking; degrades AC-28 to best-effort |
| D-6 | The eval suite gaining continuity scenarios | Nothing here is graded today. Minimum set: replay for identity stability, dropped-access for AC-12, resurrection for AC-13/AC-14, age-does-not-promote for AC-24. | Blocking for validation |
| D-7 | Connectors at the new employer | Tier A barely exists until the employer's trackers connect (A2). | Non-blocking; changes the tier mix, not the design |
| D-8 | Trailmap's schema, if used as the view | A view rendering an identifier, a first-seen date and a source link needs fields the current schema does not validate. | Non-blocking; raise as a finding |
| D-9 | The Trailmap export's write path (A5) | AC-42 fails today because the exporter regenerates wholesale. | Blocking for AC-42 |

---

## 7. Open questions

Ranked by how much a wrong answer costs.

**OQ-1 — Can tier-B closure be made reliable enough that the leader does not have to hand-close most items?** (Owner: Dj, informed by AC-37's week-one data.) If tier B cannot close itself reliably, nearly everything falls to the leader, and the feature becomes a to-do list needing daily human upkeep — the thing the agent exists to remove. The evidence cuts both ways: closure queries are cheap and concrete, but read coverage is demonstrably unreliable (A13), and a broken query looks identical to a closed loop unless AC-12 holds. **This determines whether the feature is worth building at all.**

**OQ-2 — Is item state "memory" under the no-self-grading rule?** (Owner: Dj.) §3.7 argues it is a distinct class and AC-60/AC-61 draw the line conservatively. If the leader decides it is memory in full, agent-observed closure is out entirely and the design collapses to stage 1 permanently — a coherent, cheaper, more conservative product that should be chosen deliberately rather than by default.

**OQ-3 — What happens when the leader stops answering?** (Owner: Dj.) Every correction path assumes he responds; some weeks he will not. Does an unanswered merge proposal expire? Does an item untouched for 60 days close itself, stay dormant forever, or get batch-presented for bulk dismissal? AC-16 handles dormancy; it does not handle the terminal case.

**OQ-4 — What are the real numbers for cap, dormancy interval, closed-window and token budget?** (Owner: Dj, after AC-37.) The defaults are borrowed from Trailmap's calibrated constants and from AC-33's arithmetic. They are guesses labeled as guesses.

**OQ-5 — Does the closed section belong in the brief body or somewhere else?** (Owner: Dj.) The leader has said both that resolved items should disappear and that seeing recent completions helps him track progress. AC-21 reconciles them with a 7-day window in the brief. The alternative — completions live only in the Trailmap view, never in the brief — is equally consistent with both statements and costs the brief nothing. Not resolvable without one week of real briefs.

**OQ-6 — Should the existing 27-entry journal corpus seed the first items?** (Owner: Dj.) Six or seven current entries describe live open loops. Seeding gives day one a real corpus to test against; not seeding gives a clean measurement of the true creation rate.

**OQ-7 — What is the retention policy on closed items?** (Owner: Dj.) AC-22 requires closures to stay retrievable after leaving the brief. Forever is a growing file that AC-30 does not cover, because AC-31 excludes it from the read set but nothing bounds its size on disk. One quarter matches Trailmap's momentum window; one year matches review cadence.

**OQ-8 — Do item labels holding judgments about named colleagues need a retention or review rule of their own?** (Owner: Dj.) AC-55 keeps them off shared systems. It does not address a local file accumulating months of "nobody has replied to X" about real coworkers at a new employer, re-rendered daily and never re-reviewed.

---

## Riskiest open question

**OQ-1 is the one that decides whether this is worth building.** The whole design rests on the claim that most judgment items are tier B — closable by re-running a recorded query — rather than tier C, which needs the leader to say so. If that claim holds, the agent closes most loops on its own, the brief stays honest with almost no upkeep, and the cost stays flat. If it does not hold, everything falls to the leader, and a system that needs daily human maintenance to stay accurate is exactly what the daily brief was built to replace: it will go stale in week three and quietly stop being read. The evidence available today is mixed. In favor: every tier-B item in the current corpus has a concrete, cheap closure query, and the brief already runs those same queries to build itself. Against: this deployment has already documented two ways a query silently stops seeing what it used to see — Slack channel discovery returned one channel out of seven on 2026-08-28, and the GitHub token cannot read private-repo issues at all — and a query that has stopped working returns what a closed loop returns. AC-12 is written to catch that case, but AC-12 is an untested requirement, not a measured fact. One week of real briefs at the new employer, counting how many items close by observation versus how many the leader closes by hand, settles it, and no amount of design work does. Stage 1 exists to produce that count, which is why it ships with automatic closure switched off.