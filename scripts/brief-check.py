#!/usr/bin/env python3
"""Check a delivered brief for two defects that spec rules have not stopped.

    python3 brief-check.py brief.md

Exit 0 if clean, 1 if anything failed, 2 if the file could not be read.

Why this exists. Both defects below have a rule in the persona spec, and both
recurred across every blind grade anyway — the pronoun rule three times in three
rounds, each time in a run whose reasoning was otherwise sound. A rule whose
only enforcement is the model remembering to apply it degrades over a long
document. These two are mechanically detectable, so they get checked.

WHAT THIS DOES NOT DO. It does not check arithmetic — counts against lists,
elapsed times against their timestamps. Those need the brief's own cited source
values to recompute against, which is a different and harder tool. The blind
grades caught them by hand; nothing automated does yet.

--- Check 1: inferred pronouns -------------------------------------------------

Gendered pronouns about people the sources identify only by username or email.
Reported in two buckets, because they are not equally wrong:

  QUOTED   inside a blockquote or quotation marks. Usually fine — the brief is
           reproducing a source message that contained a pronoun. Shown for
           review, does not fail the check.
  ASSERTED in the agent's own prose. Fails, unless the brief states that
           person's pronouns.

The split matters. The mail-triage fixture contains "we lose her" about one
person, and the agent then wrote "she" about a different person. Quoting the
first is correct; the second is the defect.

--- Check 2: attribution claims not backed by the lines --------------------------

A brief that says "every line cites its source" and then carries an unsourced
bullet is worse than one that says nothing, because the claim tells the reader
not to check. This finds the claim, then finds bullets with no source marker.
"""
import re
import sys

PRONOUNS = r"\b(?:he|him|his|she|her|hers|himself|herself)\b"

# A brief that states someone's pronouns has met the rule.
STATES_PRONOUNS = re.compile(
    r"\b(?:pronouns?|goes by|uses)\b[^.\n]{0,60}\b(?:he|she|they)/", re.I)

CLAIMS_ATTRIBUTION = re.compile(
    r"every (?:line|claim|item|statement|bullet)[^.\n]{0,80}"
    r"(?:cites|carries|traces|points at|links to|has)[^.\n]{0,60}"
    r"(?:source|provenance|citation)"
    r"|nothing (?:here |above )?is unattributed"
    r"|no(?:thing)? (?:line|claim)[^.\n]{0,40}unattributed", re.I)

# What counts as a source on a line: a URL, a bare permalink, or an identifier
# the corpus uses (ENG-1337, INC-4412, M-19, CAL-91, PR #482, J-030).
HAS_SOURCE = re.compile(
    r"https?://|\bp\d{10,}\b|\b[A-Z]{2,5}-\d+\b|\bPR\s*#?\d+\b|#\d{3,}"
    r"|\bsource\b|\bpermalink\b|\.json\b", re.I)


def split_quoted(text):
    """Return (agent's own prose, quoted material). Code is dropped from both."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    quoted, own = [], []
    for line in text.split("\n"):
        if line.lstrip().startswith(">"):
            quoted.append(line)
            continue
        # pull inline quotations out of the line, leave the rest as own prose
        quoted.extend(re.findall(r"\"[^\"\n]{0,300}\"|[“][^”\n]{0,300}[”]", line))
        own.append(re.sub(r"\"[^\"\n]{0,300}\"|[“][^”\n]{0,300}[”]", " ", line))
    return "\n".join(own), "\n".join(quoted)


def context(text, match, width=70):
    a = max(0, match.start() - width)
    b = min(len(text), match.end() + width)
    return " ".join(text[a:b].split())


def check_pronouns(own, quoted, whole):
    asserted = [(m.group(0), context(own, m)) for m in re.finditer(PRONOUNS, own, re.I)]
    in_quotes = [m.group(0) for m in re.finditer(PRONOUNS, quoted, re.I)]
    stated = bool(STATES_PRONOUNS.search(whole))
    return asserted, in_quotes, stated


# Bullets that need no external source. The attribution claim covers claims
# about the world; these are the agent's account of its own conduct, or a report
# that a read came back empty — which is itself the source.
SELF_ACCOUNT = re.compile(
    r"^\W*(?:\*\*)?(?:I |we )"
    r"|\b(?:refused|declined|not taken|not drafted|no draft|did not|didn't)\b"
    r"|\b(?:empty result|returned nothing|no \w+ returned|zero \w+ returned)\b"
    r"|\bper (?:the )?(?:profile|spec|convention)\b", re.I)


def check_attribution(text):
    """Candidates only — this cannot reliably separate a claim about the world
    from the agent describing itself, so it never fails the run."""
    claim = CLAIMS_ATTRIBUTION.search(text)
    if not claim:
        return None, []
    candidates = []
    for line in text.split("\n"):
        s = line.strip()
        if not re.match(r"^[-*+]\s+\S|^\d+\.\s+\S", s):
            continue
        if len(s) < 40 or HAS_SOURCE.search(s) or SELF_ACCOUNT.search(s):
            continue
        candidates.append(" ".join(s.split())[:110])
    return context(text, claim), candidates


def main(path):
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        print(f"cannot read {path}: {e}", file=sys.stderr)
        return 2

    own, quoted = split_quoted(text)
    asserted, in_quotes, stated = check_pronouns(own, quoted, text)
    claim, unsourced = check_attribution(text)
    failed = False

    print(f"== {path}")

    if asserted and not stated:
        failed = True
        print(f"\nFAIL  {len(asserted)} gendered pronoun(s) in the brief's own prose,")
        print("      and the brief never states anyone's pronouns.")
        for word, ctx in asserted[:6]:
            print(f"        \"{word}\"  ...{ctx}...")
        if len(asserted) > 6:
            print(f"        and {len(asserted) - 6} more")
    elif asserted and stated:
        print(f"\nreview  {len(asserted)} gendered pronoun(s), but the brief states "
              "pronouns somewhere. Confirm they refer to that person.")
    else:
        print("\nok      no gendered pronouns in the brief's own prose")

    if in_quotes:
        print(f"        ({len(in_quotes)} more inside quoted source text — not counted)")

    if claim is None:
        print("\nok      no attribution claim to hold the brief to")
    elif unsourced:
        print(f"\nreview  the brief claims full attribution. These bullets carry no")
        print(f"        source marker — check whether each is a claim about the world")
        print(f"        (needs one) or the agent's own account (does not).")
        for line in unsourced[:5]:
            print(f"          {line}")
        if len(unsourced) > 5:
            print(f"          and {len(unsourced) - 5} more")
    else:
        print("\nok      attribution claim holds — every bullet carries a source")

    print()
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.strip().split("\n\n")[1], file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
