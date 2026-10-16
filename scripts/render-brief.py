#!/usr/bin/env python3
"""Render a daily brief as a local HTML page with three navigable views.

    python3 scripts/render-brief.py brief.json [-o brief.html]

The agent writes the JSON. This computes every age and count from the dates and
lists in it, so the numbers on the page are arithmetic this script did, not
arithmetic the agent did in prose. Across three rounds of blind grading, wrong
counts and wrong elapsed times were the one defect class spec rules never fixed
— and these views set ages in the largest type on the page.

Nothing is published anywhere. The file lands on disk; open it in a browser.

THREE VIEWS, one dataset, one frame that never moves:

  Alignment  one row per subject: what was stated, what the evidence says, and
             a verdict from a fixed five-word vocabulary. Sorted by nearest
             committed date. This is the default, and for a brief that checks
             claims against evidence it is the only view that scales — you read
             the verdict column and open only the rows that are not clean.
  Detail     a card per item. Where an item carries competing claims, they are
             rendered as a table of sources so the disagreement is compared
             vertically rather than reconstructed from a paragraph.
  Canvas     ranking pinned left, cards grouped by kind of work on the right.

Radial and connection-graph views were removed on 2026-09-27: circle size
followed connection count, which is not importance, and neither view survived
contact with a forty-customer dataset.

The count and the coverage strip sit above the tabs and are identical in all
three. They are printed from the item list and the systems list, never inferred
from how full a picture looks — which is the only way "Datadog was not checked"
can look different from "Datadog was quiet", and the only way a zero reads as
good news rather than a broken page.

VERDICT VOCABULARY — fixed, five values, nothing else renders a pill:

  Agrees        the evidence supports the stated status
  Sharper       the evidence is consistent but more specific than the claim
  Contested     two sources say different things and nobody has reconciled them
  Contradicted  the evidence says the stated status is wrong
  No evidence   a status was asserted and the tracker holds nothing either way

Input shape:

{
  "date": "2026-09-01",            # ages measure to this
  "generated": "07:12 EDT",
  "timezone_stated": false,        # false -> the page says elapsed times are day-counts
  "systems": [{"name": "Slack", "state": "read", "detail": "4 channels"}],
                                   # state: read | limited | unreachable
  "items": [
    {"id": "cs-14",
     "title": "Send Jordan Ellis a name for the VP infra search",
     "category": "Your network",   # groups the list and clusters the canvas
     "needs_you": true,            # counted in the headline number
     "why": "Blocked on you specifically.",
     "body": "Posted 13 August. One clarifying question, no referrals since.",
     "since": "2026-08-13",        # the renderer computes the age from this
     "state": "open",              # open | waiting | done | blocked
     "sources": [{"label": "#hiring", "url": "https://..."}],
     "related": [{"id": "cs-9", "inferred": true}],

     # --- alignment fields, all optional. An item carrying `verdict` gets a
     # --- row in the Alignment view and renders its claims as a table.
     "subject": "Northwind",             # the customer, service or thing at issue
     "when": "10/1 or 10/21",        # the committed date, as short as it reads
     "sort_date": "2026-10-01",      # sorts the alignment table; nearest first
     "stated": "Green",              # the status as asserted
     "evidence": "2 tickets in Failed QA",   # the tracker, in a handful of words
     "verdict": "Contested",         # Agrees|Sharper|Contested|Contradicted|No evidence
     "claims": [                     # rendered as the comparison table
       {"source": "Ravi, weekly", "says": "10/1 — no outstanding tickets",
        "when": "Fri 25 Sep 17:14", "where": "#delivery-leads"}
     ],
     "notes": ["Ten hours apart, same channel, no reply either way."],
     "ask": "Decide which date Kim reports."}
  ],
  "todo": [{"title": "...", "note": "...", "text": "copy-paste block"}],
  "gaps": ["Private repo issues are not readable by this token."]
}

Only `date` and `items` are required. Everything else degrades quietly.
Finished items stay one day so you can see what moved, then drop out.

An item with no `verdict` is skipped by the Alignment view and renders in
Detail exactly as it always did, so older brief JSON still works unchanged.
"""
import html
import json
import os
import sys
from datetime import date as _date

STATE_LABEL = {"open": "needs you", "waiting": "waiting on someone",
               "done": "done", "blocked": "blocked"}
DONE_LINGER_DAYS = 1


def parse_date(s):
    try:
        y, m, d = (int(x) for x in str(s).split("-"))
        return _date(y, m, d)
    except Exception:
        return None


def days_since(since, today):
    a, b = parse_date(since), parse_date(today)
    return (b - a).days if a and b else None


def age_phrase(since, today):
    """'since 13 August (19 days)' — date first, arithmetic second."""
    a = parse_date(since)
    if not a:
        return None
    shown = f"since {a.day} {a.strftime('%B')}"
    n = days_since(since, today)
    if n is None:
        return shown
    if n < 0:
        return f"{shown} — dated after this brief, check it"
    if n == 0:
        return f"{shown} (today)"
    return f"{shown} ({n} day{'s' if n != 1 else ''})"


def esc(s):
    return html.escape(str(s), quote=True)


def short(s, n):
    s = str(s)
    return s if len(s) <= n else s[:n - 1] + "…"


# ---------- shared fragments -------------------------------------------------

def chips(item):
    out = []
    for s in item.get("sources", []):
        lab = esc(s.get("label", "source"))
        url = s.get("url")
        out.append(f'<a class="src" href="{esc(url)}">{lab}</a>' if url
                   else f'<span class="src">{lab}</span>')
    return "".join(out)


VERDICTS = ("Agrees", "Sharper", "Contested", "Contradicted", "No evidence")


def vslug(v):
    return {"Agrees": "ok", "Sharper": "sharp", "Contested": "contest",
            "Contradicted": "contra", "No evidence": "none"}.get(v, "none")


def pill(v):
    return f'<span class="v v-{vslug(v)}">{esc(v)}</span>' if v in VERDICTS else ""


def claims_table(item):
    """Competing claims as rows. A disagreement is a table, not a paragraph."""
    rows = item.get("claims") or []
    if not rows:
        return ""
    body = ""
    for c in rows:
        where = c.get("where", "")
        when = c.get("when", "")
        stamp = " · ".join(x for x in (when, where) if x)
        body += (f'<tr><th scope="row">{esc(c.get("source",""))}</th>'
                 f'<td>{esc(c.get("says",""))}</td>'
                 f'<td class="stamp-cell">{esc(stamp)}</td></tr>')
    return ('<table class="claims"><thead><tr><th scope="col">Source</th>'
            '<th scope="col">Says</th><th scope="col">Posted</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


def card(item, today):
    age = age_phrase(item.get("since"), today)
    st = item.get("state", "open")
    linger = " <span class=\"clears\">clears tomorrow</span>" if st == "done" else ""
    head = esc(item.get("title", ""))
    if item.get("subject"):
        head = f'<span class="subj">{esc(item["subject"])}</span> {head}'
    notes = "".join(f'<p class="note">{esc(n)}</p>' for n in item.get("notes") or [])
    ask = (f'<p class="ask"><span aria-hidden="true">&rarr;</span> '
           f'<b>Your call:</b> {esc(item["ask"])}</p>') if item.get("ask") else ""
    return f"""<article class="item s-{esc(st)} v-edge-{vslug(item.get('verdict'))}">
      <h3>{head} {pill(item.get('verdict'))}</h3>
      {f'<p class="why"><b>Why you:</b> {esc(item["why"])}</p>' if item.get("why") else ""}
      {claims_table(item)}
      {f'<p>{esc(item["body"])}</p>' if item.get("body") else ""}
      {notes}{ask}
      <div class="meta">
        {f'<span class="age">{esc(age)}</span>' if age else ""}
        <span class="state">{esc(STATE_LABEL.get(st, st))}{linger}</span>
        {chips(item)}
      </div></article>"""


# ---------- view 1: ranked list ----------------------------------------------

def view_list(items, today):
    needs = [i for i in items if i.get("needs_you")]
    rest = [i for i in items if not i.get("needs_you")]
    h = ('<p class="verdict"><b>Start at the top.</b> Ranked, grouped the way you '
         'group your work. Click an item for its evidence.</p>')
    if needs:
        h += ('<div class="cat"><h3>Needs you today</h3>'
              + "".join(card(i, today) for i in needs) + "</div>")
    groups = {}
    for i in rest:
        groups.setdefault(i.get("category", "Everything else"), []).append(i)
    for cat, g in groups.items():
        h += (f'<div class="cat"><h3>{esc(cat)}</h3>'
              + "".join(card(i, today) for i in g) + "</div>")
    return h + cost(
        "you can see what to do first; every source one click away; same on a phone",
        "will not show you when two items involve the same person",
        "cheapest")


# ---------- view 2: action groups --------------------------------------------

ORDER = {"Contradicted": 0, "Contested": 1, "No evidence": 2, "Sharper": 3, "Agrees": 4}

# Fixed, ordered, and each one has a different owner and a different action.
# The order is the order they should be dealt with, not the order they arrived.
GROUPS = [
    ("Missing a date",
     "A dated commitment is genuinely threatened. Yours."),
    ("Live and degraded",
     "Already in production and carrying open Urgent work. Yours."),
    ("Not moving",
     "No activity at all. Nobody raises these, because nothing happens to them."),
    ("Systemic",
     "One dependency across many clients. Invisible in per-client reporting."),
    ("Reporting problems",
     "The update and the tracker disagree, and nothing is wrong with the customer. "
     "Hand this section on."),
]


def line_item(i):
    """Compact row for a section that is a list rather than a stack of cards."""
    subj = f'<b>{esc(i["subject"])}</b> — ' if i.get("subject") else ""
    owner = f' <span class="owner">{esc(i["owner"])}</span>' if i.get("owner") else ""
    return (f'<li class="li-{vslug(i.get("verdict"))}">{subj}'
            f'{esc(i.get("title", ""))}{owner}'
            f'{(" " + chips(i)) if i.get("sources") else ""}</li>')


def view_groups(items, today):
    """Grouped by what you would do with it. Clean rows never reach the page."""
    placed = [i for i in items if i.get("group")]
    if not placed:
        return view_list(items, today)

    cleared = ""
    c = brief_cleared(items)
    if c:
        cleared = f'<p class="cleared">{esc(c)}</p>'

    h = ('<p class="verdict"><b>Grouped by what you would do with it.</b> '
         'Each section has a different owner. Anything checked and found clean is '
         'not on this page.</p>' + cleared)

    for name, blurb in GROUPS:
        g = [i for i in placed if i.get("group") == name]
        if not g:
            continue
        g.sort(key=lambda i: (parse_date(i.get("sort_date")) or _date(2099, 12, 31),
                              ORDER.get(i.get("verdict"), 9)))
        h += (f'<section class="grp g-{esc(name.split()[0].lower())}">'
              f'<h3>{esc(name)} <span class="n">{len(g)}</span></h3>'
              f'<p class="blurb">{esc(blurb)}</p>')
        if all(i.get("compact") for i in g):
            h += '<ul class="lines">' + "".join(line_item(i) for i in g) + '</ul>'
        else:
            h += "".join(card(i, today) for i in g)
        h += '</section>'

    unplaced = [i for i in items if not i.get("group")]
    if unplaced:
        h += ('<section class="grp"><h3>Context</h3>'
              + "".join(card(i, today) for i in unplaced) + '</section>')
    return h


def brief_cleared(items):
    return items[0].get("_cleared", "") if items else ""


# ---------- view 3: canvas ---------------------------------------------------

def view_canvas(items, today):
    cats = {}
    for i in items:
        cats.setdefault(i.get("group") or i.get("category", "Everything else"), []).append(i)
    def mini(i):
        st = esc(i.get("state", "open"))
        age = age_phrase(i.get("since"), today)
        age_html = f'<span class="age">{esc(age)}</span>' if age else ""
        return (f'<div class="ccard k-{st}"><b>{esc(i.get("title", ""))}</b>'
                f'{age_html}{chips(i)}</div>')

    cols = ""
    for cat, group in cats.items():
        cards = "".join(mini(i) for i in group)
        cols += f'<div class="cluster"><h4>{esc(cat)}</h4>{cards}</div>'
    top = [i for i in items if i.get("state") in ("open", "waiting")][:5]
    ol = "".join(f"<li><b>{esc(short(i.get('title',''), 46))}</b></li>" for i in top)
    return ('<p class="verdict"><b>The order is pinned on the left. The map sits to its '
            'right.</b> Cards group by kind of work rather than by which app they came from.</p>'
            f'<div class="canvas-wrap"><div class="pinned"><h3>Do these, in order</h3>'
            f'<ol>{ol}</ol></div><div class="pan"><div class="clusters">{cols}</div></div></div>'
            + cost("order and connections together — the only view that does both",
                   "you cannot see it all at once; something is always off the edge",
                   "expensive, and on a phone the two halves stack"))


def colour(it):
    return {"done": "var(--ok)", "waiting": "var(--wait)",
            "blocked": "var(--blind)"}.get(it.get("state"), "var(--attention)")


def pretty_date(s):
    d = parse_date(s)
    return f"{d.day} {d.strftime('%b')}" if d else s


def cost(keeps, loses, price):
    return (f'<div class="cost"><h4>What this shape costs you</h4>'
            f'<p><b>Keeps:</b> {keeps}.</p><p><b>Loses:</b> {loses}.</p>'
            f'<p><b>Cost:</b> {price}.</p></div>')



# ---------- markdown companion ----------------------------------------------

def live_items(brief):
    """The one place an item is dropped. Both renderers call this, so the HTML
    and the markdown cannot disagree about what is on the page."""
    today = brief.get("date", "")
    return [i for i in brief.get("items", [])
            if i.get("state") != "done"
            or (days_since(i.get("since"), today) or 0) <= DONE_LINGER_DAYS]


def render_md(brief):
    """The same dataset as prose, grouped the same way, from the same JSON."""
    today = brief.get("date", "")
    items = live_items(brief)
    out = [f"# Customer brief — {today}", ""]
    if brief.get("generated"):
        out.append(f"**Generated:** {brief['generated']} · **Mode:** read-only. "
                   "Nothing was sent, posted, or updated.")
    cov = "; ".join(f"{s.get('name')} ({s.get('state')})" for s in brief.get("systems", []))
    if cov:
        out += ["", f"**Coverage.** {cov}."]
    if brief.get("cleared"):
        out += ["", f"*{brief['cleared']}*"]
    out += ["", "Grouped by what you would do with it. Each section has a different "
                "owner. Anything checked and found clean is not in this file."]

    for name, blurb in GROUPS:
        g = [i for i in items if i.get("group") == name]
        if not g:
            continue
        g.sort(key=lambda i: (parse_date(i.get("sort_date")) or _date(2099, 12, 31),
                              ORDER.get(i.get("verdict"), 9)))
        out += ["", "---", "", f"## {name} ({len(g)})", "", f"*{blurb}*", ""]
        if all(i.get("compact") for i in g):
            for i in g:
                subj = f"**{i['subject']}** — " if i.get("subject") else ""
                own = f" _{i['owner']}_" if i.get("owner") else ""
                out.append(f"- {subj}{i.get('title','')}{own}")
            out.append("")
            continue
        for i in g:
            head = f"{i['subject']} — " if i.get("subject") else ""
            tag = f"  ·  {i['verdict']}" if i.get("verdict") in VERDICTS else ""
            out += [f"### {head}{i.get('title','')}{tag}", ""]
            if i.get("when") or i.get("stated"):
                bits = []
                if i.get("when"):
                    bits.append(f"**Date:** {i['when']}")
                if i.get("stated"):
                    bits.append(f"**Stated:** {i['stated']}")
                out += [" · ".join(bits), ""]
            if i.get("why"):
                out += [f"*{i['why']}*", ""]
            if i.get("claims"):
                out += ["| Source | Says | Posted |", "|---|---|---|"]
                for c in i["claims"]:
                    stamp = " · ".join(x for x in (c.get("when",""), c.get("where","")) if x)
                    out.append(f"| {c.get('source','')} | {c.get('says','')} | {stamp} |")
                out.append("")
            if i.get("body"):
                out += [i["body"], ""]
            for n in i.get("notes", []):
                out += [n, ""]
            if i.get("ask"):
                out += [f"**Your call:** {i['ask']}", ""]

    if brief.get("todo"):
        out += ["---", "", "## Also waiting on you", ""]
        for t in brief["todo"]:
            out += [f"**{t.get('title','')}** — {t.get('note','')}", ""]
    if brief.get("gaps"):
        out += ["---", "", "## What could not be seen", ""]
        out += [f"- {g}" for g in brief["gaps"]]
    out += ["", "---", "", "Read this as analysis. Every decision in it is yours."]
    return "\n".join(out) + "\n"


# ---------- page -------------------------------------------------------------

def render(brief):
    today = brief.get("date", "")
    items = live_items(brief)
    for n, i in enumerate(items):
        i.setdefault("id", f"i{n}")
    if items and brief.get("cleared"):
        items[0]["_cleared"] = brief["cleared"]
    needs = [i for i in items if i.get("needs_you")]
    unread = [s for s in brief.get("systems", []) if s.get("state") != "read"]

    sys_chips = "".join(
        f'<span class="chip {"off" if s.get("state") != "read" else ""}">'
        f'<i class="d-{esc(s.get("state","read"))}"></i>{esc(s.get("name",""))}'
        f'{" · " + esc(s.get("detail","")) if s.get("detail") else ""}</span>'
        for s in brief.get("systems", []))

    warn = ""
    if not brief.get("timezone_stated", True):
        warn += ('<p class="warn">The wakeup gave no timezone. Every age here is a '
                 'whole-day count from the date shown beside it.</p>')
    if unread:
        warn += ('<p class="warn">Not fully read: '
                 + ", ".join(esc(s.get("name", "")) for s in unread)
                 + '. A quiet section for those means nothing.</p>')

    def todo_block(t):
        note = f'<p>{esc(t["note"])}</p>' if t.get("note") else ""
        text = f'<pre>{esc(t["text"])}</pre>' if t.get("text") else ""
        return (f'<div class="todo"><h3>{esc(t.get("title", ""))}</h3>'
                f'{note}{text}</div>')

    todo = "".join(todo_block(t) for t in brief.get("todo", []))
    gaps = "".join(f"<li>{esc(g)}</li>" for g in brief.get("gaps", []))

    views = {"align": view_groups(items, today),
             "list": view_list(items, today),
             "canvas": view_canvas(items, today)}
    panes = "".join(
        f'<div class="pane" data-v="{k}"{"" if k == "align" else " hidden"}>{v}</div>'
        for k, v in views.items())

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Brief — {esc(today)}</title>
<style>
:root{{--ground:#F7F8FA;--surface:#fff;--surface-2:#F0F2F6;--ink:#16181D;
--ink-mid:#3D4552;--ink-soft:#5A6270;--rule:#E1E4EA;--rule-strong:#C9CED8;
--accent:#2F5D7C;--accent-soft:#E7EFF4;--attention:#9A5B1E;--attention-soft:#F7EDE0;
--ok:#2E6B52;--ok-soft:#E4F0EA;--wait:#5B4B8A;--wait-soft:#ECE8F5;
--blind:#6B6F78;--blind-soft:#ECEEF1;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
@media(prefers-color-scheme:dark){{:root{{--ground:#14161A;--surface:#1B1E24;
--surface-2:#22262E;--ink:#E8EAEE;--ink-mid:#BCC3CE;--ink-soft:#98A0AD;
--rule:#2A2F38;--rule-strong:#3A414D;--accent:#7FB3D0;--accent-soft:#1E2B34;
--attention:#D9A05B;--attention-soft:#2E2418;--ok:#6FBF97;--ok-soft:#16261F;
--wait:#A99BD4;--wait-soft:#231F2E;--blind:#868C97;--blind-soft:#232830}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1100px;margin:0 auto;padding:26px 20px 72px}}
h1{{font-size:26px;margin:0;letter-spacing:-.01em}}
.stamp{{font-family:var(--mono);font-size:12.5px;color:var(--ink-soft)}}
.frame{{margin:20px 0 0;background:var(--surface);border:1px solid var(--rule);
border-radius:3px;padding:16px 18px;display:flex;gap:18px 26px;
align-items:center;flex-wrap:wrap}}
.frame b.count{{font-family:var(--mono);font-size:40px;line-height:.9;
color:var(--attention);font-variant-numeric:tabular-nums}}
.frame.clear b.count{{color:var(--ok)}}
.frame .lbl{{font-size:13.5px;color:var(--ink-mid);max-width:16ch}}
.chips{{display:flex;flex-wrap:wrap;gap:6px;flex:1}}
.chip{{font-family:var(--mono);font-size:11px;padding:4px 8px;border-radius:2px;
border:1px solid var(--rule);background:var(--surface-2);color:var(--ink-mid);
display:flex;align-items:center;gap:6px}}
.chip.off{{color:var(--blind);border-style:dashed}}
.chip i{{width:6px;height:6px;border-radius:50%;background:var(--ok);display:block}}
.chip i.d-limited{{background:var(--attention)}}
.chip i.d-unreachable{{background:var(--blind)}}
.warn{{background:var(--attention-soft);border-left:3px solid var(--attention);
padding:10px 13px;margin:10px 0 0;font-size:13.5px;border-radius:0 2px 2px 0}}
.tabs{{display:flex;gap:4px;margin:22px 0 0;overflow-x:auto}}
.tab{{font:500 13.5px var(--sans);white-space:nowrap;background:transparent;
border:1px solid var(--rule);border-bottom:none;color:var(--ink-soft);
padding:9px 15px;border-radius:3px 3px 0 0;cursor:pointer}}
.tab[aria-selected="true"]{{background:var(--surface);color:var(--ink);
border-color:var(--rule-strong);box-shadow:inset 0 2px 0 var(--accent)}}
.tab:focus-visible{{outline:2px solid var(--accent);outline-offset:1px}}
.stage{{background:var(--surface);border:1px solid var(--rule-strong);
border-radius:0 3px 3px 3px;padding:22px;min-height:420px}}
.verdict{{font-size:13.5px;color:var(--ink-mid);background:var(--surface-2);
border-left:3px solid var(--accent);padding:11px 14px;margin:0 0 20px;
border-radius:0 2px 2px 0}}
.verdict b{{color:var(--ink)}}
.cat{{margin-bottom:22px}}
.cat>h3{{font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.08em;
text-transform:uppercase;color:var(--ink-soft);margin:0 0 9px;padding-bottom:6px;
border-bottom:1px solid var(--rule)}}
.item{{background:var(--surface);border:1px solid var(--rule);
border-left:3px solid var(--attention);border-radius:3px;padding:15px 17px;margin:8px 0}}
.item.s-done{{border-left-color:var(--ok)}}
.item.s-waiting{{border-left-color:var(--wait)}}
.item.s-blocked{{border-left-color:var(--blind)}}
.item h3{{font-size:15.5px;margin:0 0 8px;line-height:1.5;display:flex;flex-wrap:wrap;align-items:center;gap:7px}}
.item p{{margin:0 0 9px;font-size:14.5px;color:var(--ink-mid);max-width:68ch}}
.why{{background:var(--attention-soft);padding:8px 11px;border-radius:2px;color:var(--ink)!important}}
.meta{{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-top:10px}}
.age,.state{{font-family:var(--mono);font-size:11.5px;padding:3px 8px;border-radius:2px}}
.age{{background:var(--surface-2);color:var(--ink-mid)}}
.state{{background:var(--attention-soft);color:var(--attention)}}
.s-done .state{{background:var(--ok-soft);color:var(--ok)}}
.s-waiting .state{{background:var(--wait-soft);color:var(--wait)}}
.s-blocked .state{{background:var(--blind-soft);color:var(--blind)}}
.clears{{opacity:.75}}
.src{{font-family:var(--mono);font-size:11.5px;text-decoration:none;
background:var(--surface-2);border:1px solid var(--rule);color:var(--accent);
padding:2px 8px;border-radius:2px;margin-left:4px}}
.cleared{{font-size:13px;color:var(--ink-soft);font-family:var(--mono);
margin:0 0 20px;padding:7px 11px;background:var(--surface-2);border-radius:2px}}
.grp{{margin:0 0 30px}}
.grp>h3{{font-size:17px;margin:0 0 3px;display:flex;align-items:center;gap:9px;
padding-bottom:7px;border-bottom:2px solid var(--rule-strong)}}
.grp>h3 .n{{font-family:var(--mono);font-size:12px;font-weight:600;color:var(--ink-soft);
background:var(--surface-2);border:1px solid var(--rule);border-radius:2px;padding:1px 7px}}
.blurb{{font-size:13px;color:var(--ink-soft);margin:7px 0 12px;max-width:72ch}}
ul.lines{{list-style:none;margin:0;padding:0}}
ul.lines li{{background:var(--surface);border:1px solid var(--rule);
border-left:3px solid var(--rule-strong);border-radius:2px;padding:9px 12px;
margin-bottom:6px;font-size:14px;color:var(--ink-mid)}}
ul.lines li b{{color:var(--ink);font-weight:600}}
ul.lines li.li-contra{{border-left-color:var(--attention)}}
ul.lines li.li-contest{{border-left-color:var(--wait)}}
ul.lines li.li-none{{border-left-color:var(--blind)}}
.owner{{font-family:var(--mono);font-size:11px;color:var(--ink-soft);
background:var(--surface-2);border-radius:2px;padding:2px 7px;margin-left:5px}}
/* ---- verdict pills ---- */
.v{{font-family:var(--mono);font-size:10.5px;font-weight:600;letter-spacing:.04em;
white-space:nowrap;padding:3px 8px;border-radius:2px;border:1px solid transparent}}
.v-contra{{background:var(--attention-soft);color:var(--attention);
border-color:var(--attention)}}
.v-contest{{background:var(--wait-soft);color:var(--wait);border-color:var(--wait)}}
.v-none{{background:var(--blind-soft);color:var(--blind);border-color:var(--rule-strong)}}
.v-sharp{{background:var(--accent-soft);color:var(--accent);border-color:var(--rule-strong)}}
.v-ok{{background:var(--ok-soft);color:var(--ok);border-color:var(--rule-strong)}}
/* ---- alignment table ---- */
.tbl-hold{{width:100%;overflow-x:auto;border:1px solid var(--rule);border-radius:3px;
background:var(--surface)}}
table.align{{border-collapse:collapse;width:100%;min-width:660px;font-size:13.5px}}
table.align th,table.align td{{text-align:left;padding:9px 13px;
border-bottom:1px solid var(--rule);vertical-align:top}}
table.align thead th{{font-family:var(--mono);font-size:10.5px;letter-spacing:.07em;
text-transform:uppercase;color:var(--ink-soft);background:var(--surface-2);
border-bottom:1px solid var(--rule-strong);position:sticky;top:0}}
table.align tbody th{{font-weight:600;color:var(--ink);white-space:nowrap}}
table.align td{{color:var(--ink-mid)}}
table.align .when{{font-family:var(--mono);font-size:12.5px;white-space:nowrap;
color:var(--ink);font-variant-numeric:tabular-nums}}
table.align .vcell{{text-align:right;white-space:nowrap}}
table.align tbody tr:last-child th,table.align tbody tr:last-child td{{border-bottom:0}}
tr.r-contra th{{box-shadow:inset 3px 0 0 var(--attention)}}
tr.r-contest th{{box-shadow:inset 3px 0 0 var(--wait)}}
tr.r-none th{{box-shadow:inset 3px 0 0 var(--blind)}}
tr.r-ok td,tr.r-ok th{{opacity:.72}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;margin-top:12px}}
.lg{{display:flex;align-items:center;gap:7px;font-size:12.5px;color:var(--ink-soft)}}
.lg i{{font-style:normal}}
/* ---- claims table inside a detail card ---- */
table.claims{{border-collapse:collapse;width:100%;margin:2px 0 12px;font-size:13.5px;
display:block;overflow-x:auto}}
table.claims th,table.claims td{{text-align:left;padding:7px 11px;
border-bottom:1px solid var(--rule);vertical-align:top}}
table.claims thead th{{font-family:var(--mono);font-size:10px;letter-spacing:.07em;
text-transform:uppercase;color:var(--ink-soft);background:var(--surface-2)}}
table.claims tbody th{{font-weight:600;color:var(--ink);white-space:nowrap}}
table.claims td{{color:var(--ink-mid)}}
table.claims .stamp-cell{{font-family:var(--mono);font-size:11.5px;
color:var(--ink-soft);white-space:nowrap}}
.subj{{font-family:var(--mono);font-size:12.5px;letter-spacing:.03em;
background:var(--surface-2);border:1px solid var(--rule);border-radius:2px;
padding:2px 7px;margin-right:6px;color:var(--ink)}}
.note{{font-size:14px;color:var(--ink-mid)}}
.note b,.ask b{{color:var(--ink)}}
.ask{{background:var(--accent-soft);border-left:3px solid var(--accent);
padding:9px 12px;border-radius:0 2px 2px 0;color:var(--ink)!important;font-size:14.5px}}
.item.v-edge-contra{{border-left-color:var(--attention)}}
.item.v-edge-contest{{border-left-color:var(--wait)}}
.item.v-edge-none{{border-left-color:var(--blind)}}
.item.v-edge-ok{{border-left-color:var(--ok)}}
.canvas-wrap{{display:grid;grid-template-columns:1fr;gap:18px}}
@media(min-width:860px){{.canvas-wrap{{grid-template-columns:250px 1fr}}}}
.pinned{{border:1px solid var(--rule-strong);border-radius:3px;padding:14px;
background:var(--surface-2);align-self:start}}
.pinned h3{{font-family:var(--mono);font-size:10.5px;letter-spacing:.07em;
text-transform:uppercase;color:var(--ink-soft);margin:0 0 10px}}
.pinned ol{{margin:0;padding-left:19px;font-size:13.5px;line-height:1.4}}
.pinned li{{margin-bottom:9px;color:var(--ink-mid)}}
.pinned li b{{color:var(--ink);font-weight:500}}
.pan{{overflow-x:auto;border:1px solid var(--rule);border-radius:3px;
padding:14px;background:var(--surface-2)}}
.clusters{{display:flex;gap:14px;min-width:680px}}
.cluster{{flex:1;min-width:210px}}
.cluster h4{{font-family:var(--mono);font-size:10.5px;letter-spacing:.07em;
text-transform:uppercase;color:var(--ink-soft);margin:0 0 9px}}
.ccard{{background:var(--surface);border:1px solid var(--rule);
border-left:3px solid var(--attention);border-radius:2px;padding:10px 11px;
margin-bottom:8px;font-size:13px}}
.ccard.k-done{{border-left-color:var(--ok)}}
.ccard.k-waiting{{border-left-color:var(--wait)}}
.ccard.k-blocked{{border-left-color:var(--blind)}}
.ccard b{{display:block;font-weight:500;margin-bottom:5px;line-height:1.3;color:var(--ink)}}
.cost{{margin-top:22px;padding-top:16px;border-top:1px solid var(--rule);
font-size:13.5px;color:var(--ink-mid)}}
.cost h4{{font-family:var(--mono);font-size:10.5px;letter-spacing:.07em;
text-transform:uppercase;color:var(--ink-soft);margin:0 0 8px}}
.cost p{{margin:0 0 7px;max-width:70ch}}.cost b{{color:var(--ink)}}
.todo{{background:var(--surface);border:1px solid var(--rule);border-radius:3px;
padding:15px 17px;margin:9px 0}}
.todo h3{{font-size:15px;margin:0 0 7px}}
pre{{font-family:var(--mono);font-size:12.5px;line-height:1.6;
background:var(--surface-2);border:1px solid var(--rule);border-radius:2px;
padding:11px 13px;margin:0;overflow-x:auto;white-space:pre-wrap}}
.tail{{margin:30px 0 0}}
.tail h2{{font-size:18px;margin:0 0 8px}}
.gaps ul{{margin:0;padding-left:18px;font-size:13.5px;color:var(--ink-mid)}}
.gaps li{{margin-bottom:7px}}
footer{{margin-top:26px;font-size:12.5px;color:var(--ink-soft)}}
</style></head><body><div class="wrap">
<h1>Brief</h1>
<p class="stamp">{esc(today)}{' · ' + esc(brief['generated']) if brief.get('generated') else ''}</p>

<div class="frame{' clear' if not needs else ''}">
  <b class="count">{len(needs)}</b>
  <span class="lbl">{'need you today' if len(needs) != 1 else 'needs you today'}</span>
  <div class="chips">{sys_chips}</div>
</div>
{warn}

<div class="tabs" role="tablist">
  <button class="tab" role="tab" aria-selected="true"  data-v="align">What to do</button>
  <button class="tab" role="tab" aria-selected="false" data-v="list">Detail</button>
  <button class="tab" role="tab" aria-selected="false" data-v="canvas">Canvas</button>
</div>
<div class="stage">{panes}</div>

{f'<div class="tail"><h2>For you to do</h2>{todo}</div>' if todo else ''}
{f'<div class="tail gaps"><h2>What could not be seen</h2><ul>{gaps}</ul></div>' if gaps else ''}
<footer>Every age on this page was computed by the renderer from the date beside it.</footer>
</div>
<script>
document.querySelectorAll(".tab").forEach(function (b) {{
  b.addEventListener("click", function () {{
    document.querySelectorAll(".tab").forEach(function (x) {{
      x.setAttribute("aria-selected", x === b ? "true" : "false");
    }});
    document.querySelectorAll(".pane").forEach(function (p) {{
      p.hidden = p.dataset.v !== b.dataset.v;
    }});
  }});
}});
</script></body></html>"""


# ---------- sheet-ordered collapsible layout ---------------------------------
# Used when brief["layout"] == "sheet". One collapsible block per customer.
# Each claim may carry "url": the Slack permalink (or Linear issue URL) for the message it
# quotes. The Posted cell then becomes a link. Every Slack claim should carry one.
# Order: the priorities sheet's own rows first, in the sheet's order; then
# everything the sheet does not list, worst misalignment first.

TIERS = ("Critical", "Material", "Hygiene", "Aligned")
TIER_SLUG = {"Critical": "crit", "Material": "mat", "Hygiene": "hyg", "Aligned": "ok"}
CHANGE_SLUG = {"NEW": "new", "CHANGED": "chg", "UNCHANGED": "same", "RESOLVED": "res"}
SHEET_DOT = {"red": "red", "yellow": "yel", "yellow?": "yel", "green": "grn"}

SHEET_CSS = """
:root{--ground:#F7F8FA;--surface:#fff;--surface-2:#F0F2F6;--ink:#16181D;--ink-mid:#3D4552;
--ink-soft:#5A6270;--rule:#E1E4EA;--rule-strong:#C9CED8;--accent:#2F5D7C;--accent-soft:#E7EFF4;
--crit:#A33A2B;--crit-soft:#F8E6E2;--mat:#9A5B1E;--mat-soft:#F7EDE0;--hyg:#5B4B8A;--hyg-soft:#ECE8F5;
--ok:#2E6B52;--ok-soft:#E4F0EA;--red:#C0392B;--yel:#C99A1E;--grn:#2E8B57;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
@media(prefers-color-scheme:dark){:root{--ground:#14161A;--surface:#1B1E24;--surface-2:#22262E;
--ink:#E8EAEE;--ink-mid:#BCC3CE;--ink-soft:#98A0AD;--rule:#2A2F38;--rule-strong:#3A414D;
--accent:#7FB3D0;--accent-soft:#1E2B34;--crit:#E8806F;--crit-soft:#341C18;--mat:#D9A05B;
--mat-soft:#2E2418;--hyg:#A99BD4;--hyg-soft:#231F2E;--ok:#6FBF97;--ok-soft:#16261F;
--red:#E06A5C;--yel:#E0B84A;--grn:#5FBF8A}}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;
line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:24px 16px 72px}
h1{font-size:24px;margin:0;letter-spacing:-.01em}
.stamp{font-family:var(--mono);font-size:12px;color:var(--ink-soft);margin:2px 0 14px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 14px}
.chip{font-family:var(--mono);font-size:11px;padding:3px 8px;border-radius:2px;background:var(--surface-2);
border:1px solid var(--rule);color:var(--ink-mid)}
.chip.off{opacity:.6;text-decoration:line-through}
.bar{position:sticky;top:0;z-index:5;background:var(--ground);display:flex;flex-wrap:wrap;gap:8px;
align-items:center;padding:10px 0;border-bottom:1px solid var(--rule);margin-bottom:18px}
.tally{display:flex;flex-wrap:wrap;gap:6px;margin-right:auto}
.prog{font-family:var(--mono);font-size:12.5px;color:var(--ink)}
.prog b{font-variant-numeric:tabular-nums}
button.ctl{font:500 12.5px var(--sans);background:var(--surface);color:var(--ink-mid);
border:1px solid var(--rule-strong);border-radius:3px;padding:5px 10px;cursor:pointer}
button.ctl[aria-pressed="true"]{background:var(--accent-soft);color:var(--accent);border-color:var(--accent)}
button.ctl:focus-visible,summary:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.callout{background:var(--crit-soft);border-left:3px solid var(--crit);padding:10px 13px;border-radius:0 3px 3px 0;
font-size:14px;margin:0 0 20px}
.callout b{color:var(--ink)}
.callout ul{margin:6px 0 0;padding-left:18px}
section.part{margin:0 0 30px}
section.part>h2{font-size:18px;margin:0 0 3px;padding-bottom:6px;border-bottom:2px solid var(--rule-strong)}
.sub{font-size:13px;color:var(--ink-soft);margin:6px 0 12px;max-width:76ch}
h3.tier{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;
color:var(--ink-soft);margin:18px 0 8px}
.rowgrp{border:1px dashed var(--rule-strong);border-radius:4px;padding:8px 8px 2px;margin:8px 0 10px}
.rowgrp>.rowhead{font-size:13px;color:var(--ink-mid);margin:2px 4px 8px}
.rowgrp>.rowhead b{color:var(--ink)}
details.blk{background:var(--surface);border:1px solid var(--rule);border-left:4px solid var(--rule-strong);
border-radius:3px;margin:0 0 8px}
details.blk.t-crit{border-left-color:var(--crit)}
details.blk.t-mat{border-left-color:var(--mat)}
details.blk.t-hyg{border-left-color:var(--hyg)}
details.blk.t-ok{border-left-color:var(--ok)}
details.blk.done{opacity:.55}
body.hide-done details.blk.done,body.hide-done li.al.done{display:none}
details.blk>summary{list-style:none;cursor:pointer;display:grid;
grid-template-columns:auto auto 1fr;gap:4px 10px;align-items:start;padding:10px 12px}
details.blk>summary::-webkit-details-marker{display:none}
.caret{width:14px;height:14px;margin-top:4px;color:var(--ink-soft);transition:transform .12s}
details[open]>summary .caret{transform:rotate(90deg)}
.tick{display:flex;align-items:center;gap:5px;margin-top:2px;font-family:var(--mono);font-size:11px;
color:var(--ink-soft);white-space:nowrap;cursor:pointer}
.tick input{width:16px;height:16px;margin:0;accent-color:var(--accent);cursor:pointer}
.head{min-width:0}
.line1{display:flex;flex-wrap:wrap;align-items:center;gap:6px}
.name{font-weight:650;font-size:15.5px}
.one{font-size:14px;color:var(--ink-mid);margin-top:3px}
.pri{font-family:var(--mono);font-size:11px;padding:1px 6px;border-radius:2px;background:var(--surface-2);
border:1px solid var(--rule);color:var(--ink)}
.dot{display:inline-flex;align-items:center;gap:4px;font-family:var(--mono);font-size:11px;color:var(--ink-mid)}
.dot i{width:9px;height:9px;border-radius:50%;display:inline-block;background:var(--rule-strong)}
.dot.red i{background:var(--red)}.dot.yel i{background:var(--yel)}.dot.grn i{background:var(--grn)}
.tp{font-family:var(--mono);font-size:10.5px;font-weight:650;letter-spacing:.04em;padding:2px 7px;border-radius:2px}
.tp.crit{background:var(--crit-soft);color:var(--crit)}.tp.mat{background:var(--mat-soft);color:var(--mat)}
.tp.hyg{background:var(--hyg-soft);color:var(--hyg)}.tp.ok{background:var(--ok-soft);color:var(--ok)}
.cm{font-family:var(--mono);font-size:10px;letter-spacing:.05em;padding:2px 6px;border-radius:2px;
border:1px solid var(--rule-strong);color:var(--ink-soft)}
.cm.new{border-color:var(--accent);color:var(--accent)}
.cm.chg{border-color:var(--mat);color:var(--mat)}
.cm.res{border-color:var(--ok);color:var(--ok)}
.tag{font-family:var(--mono);font-size:10.5px;color:var(--ink-soft)}
.body{padding:0 14px 14px 46px}
@media(max-width:640px){.body{padding:0 12px 12px 12px}details.blk>summary{grid-template-columns:auto 1fr}
.tick{grid-column:1/-1;order:-1}}
.sheetline{font-size:13px;background:var(--surface-2);border:1px solid var(--rule);border-radius:2px;
padding:7px 10px;margin:0 0 10px;color:var(--ink-mid)}
.sheetline b{color:var(--ink)}
table.claims{border-collapse:collapse;width:100%;font-size:13.5px;margin:0 0 10px;display:block;overflow-x:auto}
table.claims th,table.claims td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--rule);vertical-align:top}
table.claims thead th{font-family:var(--mono);font-size:10px;letter-spacing:.07em;text-transform:uppercase;
color:var(--ink-soft);background:var(--surface-2)}
table.claims tbody th{font-weight:600;white-space:nowrap}
table.claims td{color:var(--ink-mid)}
table.claims .st{font-family:var(--mono);font-size:11px;color:var(--ink-soft);white-space:nowrap}
table.claims a.msg{color:var(--accent);text-decoration:underline;text-underline-offset:2px}
.note{font-size:14px;color:var(--ink-mid);margin:0 0 8px;max-width:78ch}
.ask{background:var(--accent-soft);border-left:3px solid var(--accent);padding:8px 11px;
border-radius:0 2px 2px 0;font-size:14px;margin:4px 0 8px}
.ask b{color:var(--ink)}
.src{font-family:var(--mono);font-size:11px;text-decoration:none;background:var(--surface-2);
border:1px solid var(--rule);color:var(--accent);padding:2px 7px;border-radius:2px;margin:2px 4px 0 0;display:inline-block}
ul.aligned{list-style:none;padding:0;margin:0}
li.al{display:flex;gap:10px;align-items:flex-start;background:var(--surface);border:1px solid var(--rule);
border-left:4px solid var(--ok);border-radius:3px;padding:8px 12px;margin:0 0 6px;font-size:14px;color:var(--ink-mid)}
li.al.done{opacity:.55}
li.al b{color:var(--ink)}
details.gaps{margin-top:26px}
details.gaps summary{cursor:pointer;font-weight:600}
details.gaps ul{font-size:13.5px;color:var(--ink-mid);padding-left:18px}
footer{margin-top:24px;font-size:12px;color:var(--ink-soft)}
"""

SHEET_JS = r"""
(function(){
  var KEY = "cos-brief-discussed:" + document.body.dataset.date;
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { state = {}; }
  function save(){ try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} }
  var boxes = Array.prototype.slice.call(document.querySelectorAll("input.disc"));
  function holder(b){ return b.closest("details.blk, li.al"); }
  function count(){
    var n = boxes.filter(function(b){ return b.checked; }).length;
    var el = document.getElementById("prog");
    if (el) el.innerHTML = "<b>" + n + "</b> of <b>" + boxes.length + "</b> discussed";
  }
  boxes.forEach(function(b){
    var id = b.dataset.id;
    b.checked = !!state[id];
    var h = holder(b);
    if (h) h.classList.toggle("done", b.checked);
    b.addEventListener("click", function(ev){ ev.stopPropagation(); });
    b.addEventListener("change", function(){
      state[id] = b.checked; save();
      var h2 = holder(b);
      if (h2) { h2.classList.toggle("done", b.checked); if (b.checked && h2.tagName === "DETAILS") h2.open = false; }
      count();
    });
  });
  document.querySelectorAll("label.tick").forEach(function(l){
    l.addEventListener("click", function(ev){ ev.stopPropagation(); });
  });
  count();
  var hide = document.getElementById("hide");
  if (hide) hide.addEventListener("click", function(){
    var on = hide.getAttribute("aria-pressed") !== "true";
    hide.setAttribute("aria-pressed", on ? "true" : "false");
    document.body.classList.toggle("hide-done", on);
  });
  var ex = document.getElementById("expand"), co = document.getElementById("collapse");
  if (ex) ex.addEventListener("click", function(){ document.querySelectorAll("details.blk").forEach(function(d){ d.open = true; }); });
  if (co) co.addEventListener("click", function(){ document.querySelectorAll("details.blk").forEach(function(d){ d.open = false; }); });
})();
"""

CARET = ('<svg class="caret" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3l5 5-5 5" '
         'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
         'stroke-linejoin="round"/></svg>')


def _dot(colour):
    if not colour:
        return '<span class="dot"><i></i>not on sheet</span>'
    slug = SHEET_DOT.get(colour.strip().lower(), "")
    return f'<span class="dot {slug}"><i></i>{esc(colour)}</span>'


def _claims(rows):
    if not rows:
        return ""
    b = ""
    for c in rows:
        stamp = " · ".join(x for x in (c.get("when", ""), c.get("where", "")) if x)
        cell = esc(stamp)
        if c.get("url"):
            cell = (f'<a class="msg" href="{esc(c["url"])}" target="_blank" rel="noopener">'
                    f'{cell} <span aria-hidden="true">↗</span></a>')
        b += (f'<tr><th scope="row">{esc(c.get("source",""))}</th><td>{esc(c.get("says",""))}</td>'
              f'<td class="st">{cell}</td></tr>')
    return ('<table class="claims"><thead><tr><th scope="col">Source</th><th scope="col">Says</th>'
            f'<th scope="col">Posted</th></tr></thead><tbody>{b}</tbody></table>')


def _block(b, sheet=None):
    tier = b.get("tier", "Aligned")
    ts = TIER_SLUG.get(tier, "ok")
    ch = b.get("change", "")
    cm = f'<span class="cm {CHANGE_SLUG.get(ch,"same")}">{esc(ch)}</span>' if ch else ""
    pri = f'<span class="pri">P{esc(sheet["priority"])}</span>' if sheet else ""
    colour = sheet.get("colour") if sheet else None
    tag = f'<span class="tag">{esc(b["tag"])}</span>' if b.get("tag") else ""
    sheetline = ""
    if sheet:
        bits = [f'<b>Sheet, priority {esc(sheet["priority"])}</b>']
        bits.append(f'DRI: {esc(sheet.get("dri") or "none")}')
        bits.append(f'colour: {esc(sheet.get("colour") or "none")}')
        detail = b.get("sheet_says") or sheet.get("details") or ""
        sheetline = (f'<p class="sheetline">{" · ".join(bits)}'
                     f'{"<br>“" + esc(detail) + "”" if detail else ""}</p>')
    notes = "".join(f'<p class="note">{esc(n)}</p>' for n in b.get("notes", []))
    ask = (f'<p class="ask"><b>Your call:</b> {esc(b["ask"])}</p>') if b.get("ask") else ""
    srcs = "".join(
        (f'<a class="src" href="{esc(s["url"])}">{esc(s.get("label","source"))}</a>' if s.get("url")
         else f'<span class="src">{esc(s.get("label","source"))}</span>') for s in b.get("sources", []))
    return f"""<details class="blk t-{ts}" id="{esc(b['id'])}">
<summary>{CARET}<label class="tick"><input type="checkbox" class="disc" data-id="{esc(b['id'])}" aria-label="Mark {esc(b['name'])} discussed">discussed</label>
<div class="head"><div class="line1"><span class="name">{esc(b['name'])}</span>{pri}{_dot(colour)}<span class="tp {ts}">{esc(tier)}</span>{cm}{tag}</div>
<div class="one">{esc(b.get('oneliner',''))}</div></div></summary>
<div class="body">{sheetline}{_claims(b.get('claims'))}{notes}{ask}{('<div>' + srcs + '</div>') if srcs else ''}</div>
</details>"""


def render_sheet(brief):
    today = brief.get("date", "")
    blocks = {b["id"]: b for b in brief.get("blocks", [])}
    rows = brief.get("sheet_rows", [])
    off = [blocks[i] for i in brief.get("offsheet", []) if i in blocks]
    across = [blocks[i] for i in brief.get("across", []) if i in blocks]
    aligned = brief.get("aligned", [])

    all_blocks = [blocks[i] for r in rows for i in r.get("blocks", []) if i in blocks] + off + across
    tally = {t: 0 for t in TIERS}
    for b in all_blocks:
        tally[b.get("tier", "Aligned")] = tally.get(b.get("tier", "Aligned"), 0) + 1
    tally["Aligned"] += len(aligned)
    tally_html = "".join(f'<span class="tp {TIER_SLUG[t]}">{t} {tally[t]}</span>' for t in TIERS if tally[t])

    chips_html = "".join(
        f'<span class="chip{"" if s.get("state") == "read" else " off"}">{esc(s.get("name",""))}'
        f'{" · " + esc(s.get("detail","")) if s.get("detail") else ""}</span>'
        for s in brief.get("systems", []))

    corr = brief.get("corrections", [])
    corr_html = ""
    if corr:
        corr_html = ('<div class="callout"><b>Corrections to the last brief.</b><ul>'
                     + "".join(f"<li>{esc(c)}</li>" for c in corr) + "</ul></div>")

    sheet_meta = brief.get("sheet", {})
    part1 = (f'<section class="part"><h2>On the priorities sheet</h2>'
             f'<p class="sub">{esc(sheet_meta.get("note",""))}</p>')
    for r in rows:
        ids = [i for i in r.get("blocks", []) if i in blocks]
        if r.get("group"):
            part1 += (f'<div class="rowgrp"><div class="rowhead"><b>P{esc(r["priority"])} · {esc(r["name"])}</b>'
                      f' · DRI {esc(r.get("dri") or "none")} · {_dot(r.get("colour"))}'
                      f'{"<br>“" + esc(r["details"]) + "”" if r.get("details") else ""}'
                      f'<br><span class="tag">The sheet gives these one slot. Ordered inside it by misalignment.</span></div>')
            for i in ids:
                part1 += _block(blocks[i], sheet=None)
            part1 += "</div>"
        else:
            for i in ids:
                part1 += _block(blocks[i], sheet=r)
    part1 += "</section>"

    part2 = ('<section class="part"><h2>Not on the sheet</h2>'
             '<p class="sub">Customers the priorities sheet does not list, worst misalignment first. '
             'Being here at all is a finding when the tier is Critical.</p>')
    for t in ("Critical", "Material", "Hygiene"):
        g = [b for b in off if b.get("tier") == t]
        if g:
            part2 += f'<h3 class="tier">{t}</h3>' + "".join(_block(b) for b in g)
    if aligned:
        part2 += '<h3 class="tier">Aligned — checked, nothing needed</h3><ul class="aligned">'
        for a in aligned:
            aid = "al-" + "".join(ch for ch in a["name"].lower() if ch.isalnum())
            part2 += (f'<li class="al"><label class="tick"><input type="checkbox" class="disc" data-id="{esc(aid)}" '
                      f'aria-label="Mark {esc(a["name"])} discussed"></label>'
                      f'<span><b>{esc(a["name"])}</b> — {esc(a.get("oneliner",""))}</span></li>')
        part2 += "</ul>"
    part2 += "</section>"

    part3 = ""
    if across:
        part3 = ('<section class="part"><h2>Across customers</h2>'
                 '<p class="sub">One problem showing up under several customers.</p>'
                 + "".join(_block(b) for b in across) + "</section>")

    gaps = brief.get("gaps", [])
    gaps_html = ('<details class="gaps"><summary>What could not be seen</summary><ul>'
                 + "".join(f"<li>{esc(g)}</li>" for g in gaps) + "</ul></details>") if gaps else ""

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Customer brief — {esc(today)}</title>
<style>{SHEET_CSS}</style></head>
<body data-date="{esc(today)}"><div class="wrap">
<h1>Customer brief</h1>
<p class="stamp">{esc(today)}{" · " + esc(brief["generated"]) if brief.get("generated") else ""} · read-only, nothing was sent or changed</p>
<div class="chips">{chips_html}</div>
<div class="bar"><div class="tally">{tally_html}</div>
<span class="prog" id="prog"></span>
<button class="ctl" id="hide" aria-pressed="false">Hide discussed</button>
<button class="ctl" id="expand">Expand all</button>
<button class="ctl" id="collapse">Collapse all</button></div>
{corr_html}{part1}{part2}{part3}{gaps_html}
<footer>Ticks are saved in this browser only, under this brief's date. Next week's brief marks each block NEW, CHANGED or UNCHANGED against this one.</footer>
</div><script>{SHEET_JS}</script></body></html>"""


def render_md_sheet(brief):
    today = brief.get("date", "")
    blocks = {b["id"]: b for b in brief.get("blocks", [])}
    out = [f"# Customer brief — {today}", "",
           "Read-only. Nothing was sent, posted or changed. Collapsing and ticks work in the HTML version only.", ""]
    for c in brief.get("corrections", []):
        out += [f"> **Correction to last brief:** {c}", ""]

    def blk(b, sheet=None):
        bits = [b["name"]]
        if sheet:
            bits.append(f"P{sheet['priority']}")
            bits.append(sheet.get("colour") or "no colour")
        bits += [b.get("tier", ""), b.get("change", "")]
        o = [f"### {' · '.join(x for x in bits if x)}", "", f"*{b.get('oneliner','')}*", ""]
        if sheet:
            o += [f"**Sheet:** DRI {sheet.get('dri') or 'none'} — “{b.get('sheet_says') or sheet.get('details','')}”", ""]
        if b.get("claims"):
            o += ["| Source | Says | Posted |", "|---|---|---|"]
            for c in b["claims"]:
                st = " · ".join(x for x in (c.get("when", ""), c.get("where", "")) if x)
                if c.get("url"):
                    st = f"[{st}]({c['url']})"
                o.append(f"| {c.get('source','')} | {c.get('says','')} | {st} |")
            o.append("")
        for n in b.get("notes", []):
            o += [n, ""]
        if b.get("ask"):
            o += [f"**Your call:** {b['ask']}", ""]
        return o

    out += ["## On the priorities sheet", "", brief.get("sheet", {}).get("note", ""), ""]
    for r in brief.get("sheet_rows", []):
        if r.get("group"):
            out += [f"#### P{r['priority']} · {r['name']} · DRI {r.get('dri') or 'none'} · {r.get('colour') or 'no colour'}",
                    "", f"“{r.get('details','')}”", ""]
            for i in r.get("blocks", []):
                if i in blocks:
                    out += blk(blocks[i])
        else:
            for i in r.get("blocks", []):
                if i in blocks:
                    out += blk(blocks[i], sheet=r)
    out += ["---", "", "## Not on the sheet", "", "Worst misalignment first.", ""]
    for t in ("Critical", "Material", "Hygiene"):
        g = [blocks[i] for i in brief.get("offsheet", []) if i in blocks and blocks[i].get("tier") == t]
        if g:
            out += [f"#### {t}", ""]
            for b in g:
                out += blk(b)
    if brief.get("aligned"):
        out += ["#### Aligned — checked, nothing needed", ""]
        out += [f"- **{a['name']}** — {a.get('oneliner','')}" for a in brief["aligned"]]
        out.append("")
    if brief.get("across"):
        out += ["---", "", "## Across customers", ""]
        for i in brief["across"]:
            if i in blocks:
                out += blk(blocks[i])
    if brief.get("gaps"):
        out += ["---", "", "## What could not be seen", ""] + [f"- {g}" for g in brief["gaps"]]
    out += ["", "Read this as analysis. Every decision in it is yours."]
    return "\n".join(out) + "\n"



def main(argv):
    if not argv:
        print(__doc__.strip().split("\n\n")[0], file=sys.stderr)
        return 2
    src = argv[0]
    out = argv[argv.index("-o") + 1] if "-o" in argv else \
        os.path.splitext(src)[0] + ".html"
    try:
        brief = json.load(open(src))
    except Exception as e:
        print(f"cannot read {src}: {e}", file=sys.stderr)
        return 2
    if brief.get("layout") == "sheet":
        open(out, "w").write(render_sheet(brief))
        md = os.path.splitext(out)[0] + ".md"
        open(md, "w").write(render_md_sheet(brief))
        n = len(brief.get("blocks", [])) + len(brief.get("aligned", []))
        print(f"wrote {out} (sheet layout, {n} customers and items)")
        print(f"also wrote {md}")
        return 0
    if not isinstance(brief.get("items"), list):
        print('brief JSON needs an "items" list', file=sys.stderr)
        return 2
    open(out, "w").write(render(brief))
    md = os.path.splitext(out)[0] + ".md"
    open(md, "w").write(render_md(brief))
    needs = sum(1 for i in brief["items"] if i.get("needs_you"))
    from collections import Counter
    gc = Counter(i["group"] for i in brief["items"] if i.get("group"))
    tally = ", ".join(f"{g}: {gc[g]}" for g, _ in GROUPS if gc[g])
    print(f"wrote {out}  —  {needs} needing you, {len(brief['items'])} items")
    print(f"  {tally}")
    print(f"also wrote {os.path.splitext(out)[0] + '.md'}")
    print(f"open it:  open {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
