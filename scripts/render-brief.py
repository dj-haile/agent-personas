#!/usr/bin/env python3
"""Render a daily brief as a local HTML page with four navigable views.

    python3 scripts/render-brief.py brief.json [-o brief.html]

The agent writes the JSON. This computes every age and count from the dates and
lists in it, so the numbers on the page are arithmetic this script did, not
arithmetic the agent did in prose. Across three rounds of blind grading, wrong
counts and wrong elapsed times were the one defect class spec rules never fixed
— and these views set ages in the largest type on the page.

Nothing is published anywhere. The file lands on disk; open it in a browser.

FOUR VIEWS, one dataset, one frame that never moves:

  List    ranked, grouped by category, click to open. Keeps the ordering.
  Radial  today at the centre, everything branching out.
  Graph   items as circles, real connections as lines. Dashed = the agent
          worked the connection out rather than reading it somewhere.
  Canvas  ranking pinned left, cards grouped by kind of work on the right.

The count and the coverage strip sit above the tabs and are identical in all
four. They are printed from the item list and the systems list, never inferred
from how full a picture looks — which is the only way "Datadog was not checked"
can look different from "Datadog was quiet", and the only way a zero reads as
good news rather than a broken page.

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
     "related": [{"id": "cs-9", "inferred": true}]}
  ],
  "todo": [{"title": "...", "note": "...", "text": "copy-paste block"}],
  "gaps": ["Private repo issues are not readable by this token."]
}

Only `date` and `items` are required. Everything else degrades quietly.
Finished items stay one day so you can see what moved, then drop out.
"""
import html
import json
import math
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


def card(item, today):
    age = age_phrase(item.get("since"), today)
    st = item.get("state", "open")
    linger = " <span class=\"clears\">clears tomorrow</span>" if st == "done" else ""
    return f"""<article class="item s-{esc(st)}">
      <h3>{esc(item.get('title',''))}</h3>
      {f'<p class="why"><b>Why you:</b> {esc(item["why"])}</p>' if item.get("why") else ""}
      {f'<p>{esc(item["body"])}</p>' if item.get("body") else ""}
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


# ---------- view 2: radial ---------------------------------------------------

def view_radial(items, today):
    spokes = items[:8]
    cx, cy, R = 430, 250, 168
    edges = nodes = ""
    for k, it in enumerate(spokes):
        a = (-math.pi / 2) + (k * 2 * math.pi / max(1, len(spokes)))
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        col = colour(it)
        edges += (f'<line class="edge" x1="{cx}" y1="{cy}" x2="{x:.0f}" y2="{y:.0f}" '
                  f'stroke-width="{2.2 if it.get("needs_you") else 1}"/>')
        anch = "end" if math.cos(a) < -0.25 else "start" if math.cos(a) > 0.25 else "middle"
        dx = -14 if anch == "end" else 14 if anch == "start" else 0
        dy = (24 if math.sin(a) > 0 else -16) if anch == "middle" else 4
        n = days_since(it.get("since"), today)
        sub = f"{n} days" if n and n > 0 else ""
        nodes += (
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{9 if it.get("needs_you") else 6}" fill="{col}"/>'
            f'<text class="n-lbl" x="{x+dx:.0f}" y="{y+dy:.0f}" text-anchor="{anch}">'
            f'{esc(short(it.get("title",""), 34))}</text>'
            f'<text class="n-sub" x="{x+dx:.0f}" y="{y+dy+13:.0f}" text-anchor="{anch}">{esc(sub)}</text>')
    needs = sum(1 for i in items if i.get("needs_you"))
    return (f'<p class="verdict"><b>Today in the middle, everything branching out.</b> '
            f'Try reading these most urgent first. Nothing in the shape tells you which one that is.</p>'
            f'<div class="svg-hold"><svg viewBox="0 0 860 500" width="100%" height="500" '
            f'role="img" aria-label="Radial view of today\'s items">'
            f'<circle cx="{cx}" cy="{cy}" r="46" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>'
            f'<text class="hub-lbl" x="{cx}" y="{cy-2}" text-anchor="middle">{esc(pretty_date(today))}</text>'
            f'<text class="n-sub" x="{cx}" y="{cy+15}" text-anchor="middle">{needs} need you</text>'
            f'{edges}{nodes}</svg></div>'
            + cost("the whole day on one screen; you feel the size before reading",
                   "the order — nobody reads a wheel in a reliable direction",
                   "middling, and cramped on a phone"))


# ---------- view 3: connection graph -----------------------------------------

def view_graph(items, today):
    """Deterministic layout: one cluster per category, items spread inside it."""
    cats = {}
    for i in items:
        cats.setdefault(i.get("category", "Everything else"), []).append(i)
    pos, W, H = {}, 800, 440
    n_c = max(1, len(cats))
    for ci, (cat, group) in enumerate(cats.items()):
        ang = (2 * math.pi * ci / n_c) - math.pi / 2
        ccx, ccy = W / 2 + 210 * math.cos(ang), H / 2 + 130 * math.sin(ang)
        for gi, it in enumerate(group):
            a = 2 * math.pi * gi / max(1, len(group))
            r = 0 if len(group) == 1 else 58
            pos[it["id"]] = (ccx + r * math.cos(a), ccy + r * math.sin(a))
    deg = {i["id"]: 0 for i in items}
    edges = ""
    for it in items:
        for rel in it.get("related", []):
            if rel.get("id") in pos and it["id"] in pos:
                x1, y1 = pos[it["id"]]
                x2, y2 = pos[rel["id"]]
                cls = "edge inf" if rel.get("inferred") else "edge"
                edges += (f'<line class="{cls}" x1="{x1:.0f}" y1="{y1:.0f}" '
                          f'x2="{x2:.0f}" y2="{y2:.0f}" stroke-width="1.4"/>')
                deg[it["id"]] += 1
                deg[rel["id"]] = deg.get(rel["id"], 0) + 1
    nodes = ""
    for it in items:
        if it["id"] not in pos:
            continue
        x, y = pos[it["id"]]
        r = 7 + deg.get(it["id"], 0) * 2.4
        n = days_since(it.get("since"), today)
        nodes += (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}" fill="{colour(it)}" fill-opacity=".85"/>'
                  f'<text class="n-lbl" x="{x:.0f}" y="{y+r+14:.0f}" text-anchor="middle">'
                  f'{esc(short(it.get("title",""), 26))}</text>'
                  f'<text class="n-sub" x="{x:.0f}" y="{y+r+26:.0f}" text-anchor="middle">'
                  f'{esc(f"{n} days" if n and n > 0 else "")}</text>')
    return ('<p class="verdict"><b>Items as circles, real connections as lines.</b> '
            'Circles grow with how many connections they have, which is the flaw — '
            'connections are not importance. A dashed line means the agent worked '
            'the connection out rather than reading it somewhere.</p>'
            f'<div class="svg-hold"><svg viewBox="0 0 {W} {H}" width="100%" height="{H}" '
            f'role="img" aria-label="Graph of items and their connections">{edges}{nodes}</svg></div>'
            + cost("connections across everything, including ones nobody wrote down",
                   "priority — size follows connections, and it redraws every morning",
                   "most expensive, worst on a phone"))


# ---------- view 4: canvas ---------------------------------------------------

def view_canvas(items, today):
    cats = {}
    for i in items:
        cats.setdefault(i.get("category", "Everything else"), []).append(i)
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


# ---------- page -------------------------------------------------------------

def render(brief):
    today = brief.get("date", "")
    items = [i for i in brief.get("items", [])
             if i.get("state") != "done"
             or (days_since(i.get("since"), today) or 0) <= DONE_LINGER_DAYS]
    for n, i in enumerate(items):
        i.setdefault("id", f"i{n}")
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

    views = {"list": view_list(items, today), "radial": view_radial(items, today),
             "graph": view_graph(items, today), "canvas": view_canvas(items, today)}
    panes = "".join(
        f'<div class="pane" data-v="{k}"{"" if k == "list" else " hidden"}>{v}</div>'
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
.item h3{{font-size:15.5px;margin:0 0 8px;line-height:1.35}}
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
.svg-hold{{width:100%;overflow-x:auto;border:1px solid var(--rule);
border-radius:3px;background:var(--surface-2)}}
svg{{display:block;min-width:560px}}
.n-lbl{{font-family:var(--sans);font-size:11px;fill:var(--ink)}}
.n-sub{{font-family:var(--mono);font-size:9px;fill:var(--ink-soft)}}
.hub-lbl{{font-family:var(--sans);font-size:15px;font-weight:600;fill:var(--ink)}}
.edge{{stroke:var(--rule-strong);fill:none}}
.edge.inf{{stroke-dasharray:3 3}}
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
  <button class="tab" role="tab" aria-selected="true"  data-v="list">Ranked list</button>
  <button class="tab" role="tab" aria-selected="false" data-v="radial">Radial</button>
  <button class="tab" role="tab" aria-selected="false" data-v="graph">Connections</button>
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
    if not isinstance(brief.get("items"), list):
        print('brief JSON needs an "items" list', file=sys.stderr)
        return 2
    open(out, "w").write(render(brief))
    needs = sum(1 for i in brief["items"] if i.get("needs_you"))
    print(f"wrote {out}  —  {needs} needing you, {len(brief['items'])} items, 4 views")
    print(f"open it:  open {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
