#!/usr/bin/env python3
"""
validate.py — Structural validation for the agent-personas catalog.

Checks that every persona spec honors the house template and that the
catalog's own claims stay true, so drift is caught at PR time instead of
when a dispatched persona misbehaves.

What it validates (ERRORS — fail the run):
  1. Header      — every persona opens with `# Persona:` and a header line
                   carrying **Version:**, **Model tier:**, **Lifecycle:**
  2. Model tier  — tier is semantic ("Sonnet-class", "Deterministic", ...),
                   never a literal versioned model ID (portability rule)
  3. Contract    — the 8-field Agent Contract is present and complete:
                   Goal, Scope, Non-goals, Tools/permissions,
                   Stopping condition, Evidence standard, Escalation, Budget
  4. Rebuttals   — an anti-rationalization table with >= 3 excuse/rebuttal rows
  5. Catalog     — every persona file is referenced in the catalog
  6. Stubs       — claude-agents/*.md frontmatter is complete, `model:` is an
                   alias (haiku|sonnet|opus|inherit) not a versioned ID, and
                   each stub maps to an existing persona spec
  7. Evals       — every evals/<name>-eval.md maps to an existing persona
  8. Links       — relative markdown links resolve to real files
  9. Track       — if a persona declares **Track:**, its value is one of
                   leadership | engineering-workflow | both
 10. License     — a LICENSE file exists at the repo root

What it reports (WARNINGS — printed, never fatal):
  - Catalog count claims (README / catalog prose) vs actual entry count
  - Personas missing a report/output/deliverable section
  - Eval coverage: personas with no eval suite (the catalog's own principle
    is that unevaluated agents don't work — the gap is printed every run)
  - Track coverage, once tracks are adopted

Requires: python3 only (stdlib — no dependencies).

Exit codes: 0 = all clear, 1 = one or more errors.
Usage: python3 scripts/validate.py [--quiet]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PERSONAS = ROOT / "personas"
STUBS = ROOT / "claude-agents"
EVALS = ROOT / "evals"
CATALOG = ROOT / "org-agent-personas-catalog.md"
README = ROOT / "README.md"

CONTRACT_FIELDS = [
    "Goal",
    "Scope",
    "Non-goals",
    "Tools/permissions",
    "Stopping condition",
    "Evidence standard",
    "Escalation",
    "Budget",
]

# Semantic tier vocabulary: at least one of these must appear in the
# **Model tier:** value. Mixed/split tiers ("Haiku-class for X, Opus-class
# for Y") and deterministic components are all legitimate.
TIER_TOKEN_PAT = re.compile(r"(Haiku|Sonnet|Opus)-class|Deterministic", re.IGNORECASE)

# Versioned model IDs are forbidden everywhere a tier or model is declared —
# they rot on every model release. Aliases (bare "sonnet") are allowed only
# in claude-agents/ stub frontmatter, where Claude Code requires them.
LITERAL_MODEL_ID_PAT = re.compile(
    r"\b(?:claude|gpt|gemini|grok|llama)[-_][a-z0-9][a-z0-9._-]*", re.IGNORECASE
)
STUB_MODEL_ALIASES = {"haiku", "sonnet", "opus", "inherit"}

VALID_TRACKS = {"leadership", "engineering-workflow", "both"}

CATALOG_ENTRY_PAT = re.compile(r"^### ([A-G]\d+)\.", re.MULTILINE)
COUNT_CLAIM_PAT = re.compile(r"\*\*(\d+) (?:reusable agent )?personas?\b|(\d+) personas across", re.IGNORECASE)

REPORT_SECTION_PAT = re.compile(r"^#{2,3} .*(report|output|deliverable)", re.IGNORECASE | re.MULTILINE)

MD_LINK_PAT = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")

errors = []
warnings = []


def err(path, msg):
    errors.append(f"  ERROR   {path}: {msg}")


def warn(path, msg):
    warnings.append(f"  warning {path}: {msg}")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def parse_stub_frontmatter(path: Path):
    """Stub frontmatter is flat `key: value` — parse without a YAML dep."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm


def check_personas(catalog_text: str):
    for path in sorted(PERSONAS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        p = rel(path)

        # 1. Header shape
        if not lines or not lines[0].startswith("# Persona:"):
            err(p, "first line must be a `# Persona: <name>` heading")
        header = next((l for l in lines[:6] if "**Version:**" in l), None)
        if header is None:
            err(p, "missing header line with **Version:** / **Model tier:** / **Lifecycle:**")
        else:
            if not re.search(r"\*\*Version:\*\*\s*\d+\.\d+", header):
                err(p, "**Version:** must be numeric (e.g. 1.0)")
            for field in ("**Model tier:**", "**Lifecycle:**"):
                if field not in header:
                    err(p, f"header line missing {field}")

            # 2. Semantic model tier
            tier_m = re.search(r"\*\*Model tier:\*\*\s*(.+?)(?:\s*·\s*\*\*|$)", header)
            if tier_m:
                tier = tier_m.group(1)
                if not TIER_TOKEN_PAT.search(tier):
                    err(p, f"model tier is not semantic (expected *-class or Deterministic): {tier!r}")
                if LITERAL_MODEL_ID_PAT.search(tier):
                    err(p, f"model tier contains a literal model ID: {tier!r}")

        # 3. Agent Contract
        if not re.search(r"^## Agent Contract", text, re.MULTILINE):
            err(p, "missing `## Agent Contract` section")
        else:
            missing = [f for f in CONTRACT_FIELDS if f"**{f}:**" not in text]
            if missing:
                err(p, f"Agent Contract missing field(s): {', '.join(missing)}")

        # 4. Anti-rationalization table
        anti = re.search(r"^#{2,3} .*anti-rationalization.*$", text, re.IGNORECASE | re.MULTILINE)
        if not anti:
            err(p, "missing anti-rationalization table section")
        else:
            after = text[anti.end():]
            nxt = re.search(r"^#{2,3} ", after, re.MULTILINE)
            section = after[: nxt.start()] if nxt else after
            data_rows = [
                l for l in section.splitlines()
                if l.strip().startswith("|") and not re.match(r"^\|[\s|:-]+\|?$", l.strip())
            ]
            # first pipe row is the table header
            if len(data_rows) - 1 < 3:
                err(p, f"anti-rationalization table has {max(len(data_rows) - 1, 0)} rows (need >= 3)")

        # 5. Referenced in the catalog
        if path.name not in catalog_text:
            err(p, "not referenced anywhere in org-agent-personas-catalog.md")

        # 9. Track field, if adopted
        track_m = re.search(r"\*\*Track:\*\*\s*([a-z-]+)", text)
        if track_m and track_m.group(1) not in VALID_TRACKS:
            err(p, f"**Track:** must be one of {sorted(VALID_TRACKS)}, got {track_m.group(1)!r}")

        # Advisory: report/output section
        if not REPORT_SECTION_PAT.search(text):
            warn(p, "no report/output/deliverable section found")


def check_stubs():
    for path in sorted(STUBS.glob("*.md")):
        p = rel(path)
        fm = parse_stub_frontmatter(path)
        if fm is None:
            err(p, "missing or malformed frontmatter block")
            continue
        for field in ("name", "description", "tools", "model"):
            if not fm.get(field):
                err(p, f"frontmatter missing `{field}`")
        model = fm.get("model", "")
        if model and model not in STUB_MODEL_ALIASES:
            err(p, f"`model:` must be an alias {sorted(STUB_MODEL_ALIASES)}, got {model!r} "
                   "(versioned IDs rot on every model release)")
        name = fm.get("name", "")
        if name and not (PERSONAS / f"{name}.md").exists():
            err(p, f"no persona spec personas/{name}.md for this stub")
        if name and name != path.stem:
            err(p, f"file stem {path.stem!r} != frontmatter name {name!r}")


def check_evals():
    for path in sorted(EVALS.glob("*.md")):
        p = rel(path)
        if not path.stem.endswith("-eval"):
            warn(p, "eval files are expected to be named <persona>-eval.md")
            continue
        persona = path.stem[: -len("-eval")]
        if not (PERSONAS / f"{persona}.md").exists():
            err(p, f"no persona spec personas/{persona}.md for this eval suite")


def check_catalog_counts(catalog_text: str):
    entries = set(CATALOG_ENTRY_PAT.findall(catalog_text))
    n_entries = len(entries)
    n_files = len(list(PERSONAS.glob("*.md")))
    for doc in (README, CATALOG):
        text = doc.read_text(encoding="utf-8")
        for m in COUNT_CLAIM_PAT.finditer(text):
            claimed = int(m.group(1) or m.group(2))
            if claimed not in (n_entries, n_files):
                line = text.count("\n", 0, m.start()) + 1
                warn(f"{rel(doc)}:{line}",
                     f"claims {claimed} personas, but the catalog has {n_entries} "
                     f"entries across {n_files} spec files")


def check_links():
    for path in [README, CATALOG, *sorted(PERSONAS.glob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        for m in MD_LINK_PAT.finditer(text):
            target = m.group(1)
            if re.match(r"^[a-z]+://|^mailto:", target):
                continue
            if not (path.parent / target).exists():
                err(rel(path), f"broken relative link: {target}")


def check_license():
    if not (ROOT / "LICENSE").exists():
        err("LICENSE", "no LICENSE file at repo root")


def report_coverage():
    personas = sorted(p.stem for p in PERSONAS.glob("*.md"))
    covered = sorted(
        p.stem[: -len("-eval")] for p in EVALS.glob("*-eval.md")
        if (PERSONAS / f"{p.stem[: -len('-eval')]}.md").exists()
    )
    uncovered = [p for p in personas if p not in covered]
    print(f"  eval coverage: {len(covered)}/{len(personas)} personas have an eval suite")
    if uncovered:
        print(f"  without evals: {', '.join(uncovered)}")
    tracked = [
        p.stem for p in PERSONAS.glob("*.md")
        if re.search(r"\*\*Track:\*\*", p.read_text(encoding="utf-8"))
    ]
    if tracked:
        print(f"  track coverage: {len(tracked)}/{len(personas)} personas declare a Track")


def main():
    quiet = "--quiet" in sys.argv
    catalog_text = CATALOG.read_text(encoding="utf-8")

    check_personas(catalog_text)
    check_stubs()
    check_evals()
    check_catalog_counts(catalog_text)
    check_links()
    check_license()

    if errors:
        print(f"FAIL — {len(errors)} error(s):")
        print("\n".join(errors))
    if warnings:
        print(f"{len(warnings)} warning(s):")
        print("\n".join(warnings))
    if not errors and not warnings:
        print("All checks passed.")
    if not quiet:
        report_coverage()
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
