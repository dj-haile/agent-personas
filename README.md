# agent-personas

A catalog of **26 reusable agent personas for an engineering organization** — each a complete, dispatchable spec grounded in a curated research corpus on AI-agent engineering, with verified citations, eval suites, and ready-made Claude Code agent definitions.

**Start with the catalog → [`org-agent-personas-catalog.md`](org-agent-personas-catalog.md)** — 26 personas across seven lifecycle groups (Shape & Discover · Plan & Build · Verify & Review · Secure & Govern · Operate & Improve · Leadership & Org · Product & Design), plus anti-personas the research warns against and a recommended rollout order.

## Layout

| Path | What it is |
|---|---|
| `org-agent-personas-catalog.md` | The catalog — every persona's job, who uses it, its research basis, and its constraints |
| `personas/` | A full spec file per persona: 8-field agent contract, phased workflow, hard rules, anti-rationalization table, report format |
| `evals/` | Gate-opening eval suites (5 scenarios each) for the wired personas — dispatch fresh, grade outcomes |
| `claude-agents/` | Claude Code agent definitions — `cp claude-agents/*.md .claude/agents/` in your project to activate |
| `reference/` | Vendored canonical implementations (currently: the eval-review-agent house template) |
| `conventions/` | Cross-cutting conventions persona specs reference (currently: the simulate-and-queue gatekeeper pattern, and Code Mode for read phases) |
| `coverage-and-gap-audit.md` | The verification audit: corrections applied to the catalog, plus tiered candidate personas not yet specced |
| `SOURCES.md` | Provenance map — what every citation shorthand ("playbook §N", "scout-reading 05", …) refers to |

## How to use a persona

1. Find it in the catalog; open its spec in `personas/`.
2. Dispatch it **fresh** (seeded specialist, clean context): use the spec as the agent's instructions, honoring its contract — tools, stopping condition, evidence standard, budget, model tier. The one deliberate exception to fresh dispatch is the Chief-of-Staff (F1), which is long-lived and ships with a Memory Hygienist companion.
3. Before trusting a new or edited persona on real work, run its eval (or write one: 3–5 scenarios opens the gate; grow toward 20–50). The research this catalog is built on is emphatic that unevaluated agents don't work.

## Conventions

All paths are relative to this repo's root. Specs follow one house template (see any file in `personas/`). Design principles that recur throughout: seeded specialists over standing agents; governance lives in the harness, never the persona; research documents, planning recommends; verification is the bottleneck — grade against the spec; assume prompt injection succeeds and contain blast radius; side-effect actions declare their approval mode.

## Provenance

Every number and claim in the catalog was verified against its source documents (July 2026 audit — see `coverage-and-gap-audit.md`). The research corpus itself lives in a private companion repo; `SOURCES.md` maps every citation to its origin so the trail survives. The persona specs are freestanding — nothing here requires external files to operate.
