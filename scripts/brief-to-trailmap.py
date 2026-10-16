#!/usr/bin/env python3
"""Turn chief-of-staff brief items into a Trailmap document.

Trailmap (github.com/dj-haile/trailmap) reads `trailmap.json` from its data
directory. `TRAILMAP_DATA_DIR` overrides that directory, so a generated file can
be pointed at without touching the live map:

    TRAILMAP_DATA_DIR=~/projects/cos-journal/trailmap-brief npm start

Mapping from the brief:

    brief category      -> goal
    grouping within it  -> initiative
    "for you to do"     -> move   (label starts with a verb)
    blocked on a person -> waiting chip (ages: amber at 5 days, red at 10)
    quick capture       -> loose end

The `since` on a waiting chip is the date the wait started, NOT today. Trailmap
colours the chip by that date, so a wrong one silently mis-ages the item.

Validation below mirrors validateDoc() in renderer/logic.js. Run it before
writing; a malformed file makes the app fall back to a snapshot.
"""
import json
import os
import re
import sys

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate(doc):
    """Same checks the app runs. Returns a list of problems; empty means good."""
    errs = []
    is_str = lambda v: isinstance(v, str)
    is_date = lambda v: is_str(v) and bool(DATE.match(v))

    def check_move(m, where):
        if not is_str(m.get("id")):        errs.append(f"{where} missing id")
        if not is_str(m.get("label")):     errs.append(f"{where} missing label")
        if not isinstance(m.get("done"), bool): errs.append(f"{where} missing done")
        for f in ("doneAt", "due"):
            if f in m and not is_date(m[f]):
                errs.append(f"{where} bad {f}")

    if not is_str(doc.get("title")):
        errs.append("title missing")
    for m_i, m in enumerate(doc.get("loose", [])):
        check_move(m, f"loose[{m_i}]")
    for t_i, t in enumerate(doc.get("today", [])):
        if not is_str(t.get("id")):     errs.append(f"today[{t_i}] missing id")
        if not is_str(t.get("moveId")): errs.append(f"today[{t_i}] missing moveId")
    if not isinstance(doc.get("goals"), list):
        return errs + ["goals is not an array"]
    for g_i, g in enumerate(doc["goals"]):
        if not is_str(g.get("id")):   errs.append(f"goal[{g_i}] missing id")
        if not is_str(g.get("name")): errs.append(f"goal[{g_i}] missing name")
        if "horizon" in g and g["horizon"] not in ("quarter", "half", "year"):
            errs.append(f"goal[{g_i}] bad horizon")
        for i_i, it in enumerate(g.get("inits", [])):
            at = f"goal[{g_i}].init[{i_i}]"
            if not is_str(it.get("id")):   errs.append(f"{at} missing id")
            if not is_str(it.get("name")): errs.append(f"{at} missing name")
            for m_i, m in enumerate(it.get("moves", [])):
                check_move(m, f"{at}.move[{m_i}]")
            for w_i, w in enumerate(it.get("waiting", [])):
                w_at = f"{at}.wait[{w_i}]"
                if not is_str(w.get("who")):  errs.append(f"{w_at} missing who")
                if not is_str(w.get("what")): errs.append(f"{w_at} missing what")
                if not is_date(w.get("since")): errs.append(f"{w_at} bad since")
    return errs


def move(mid, label, done=False, due=None):
    m = {"id": mid, "label": label, "done": done}
    if due:
        m["due"] = due
    return m


def wait(wid, who, what, since):
    return {"id": wid, "who": who, "what": what, "since": since,
            "lastNotifiedTier": 0}


def merge_onto_existing(doc, path):
    """Carry the user's own work forward. Without this, every export wipes it.

    Three things the person does in the app that a regenerated document would
    otherwise destroy:
      - checking a move off            -> keep `done` and `doneAt`
      - pinning moves to Today         -> keep the `today` list
      - quick-adding a loose end       -> keep `loose` entries we never emitted

    And one that needs a record rather than a comparison: clicking a waiting
    chip deletes it. A chip we generated, that is now missing from the file on
    disk, was cleared on purpose — re-adding it would resurrect something the
    person already handled. So the file carries `_generated`, a list of every id
    this script has ever emitted. Absent from disk but present there means
    cleared; absent from both means new.
    """
    if not os.path.exists(path):
        doc["_generated"] = sorted(_all_ids(doc))
        return doc
    with open(path) as fh:
        prev = json.load(fh)

    done_state, prev_ids = {}, set()
    for m in _walk_moves(prev):
        prev_ids.add(m["id"])
        if m.get("done"):
            done_state[m["id"]] = m.get("doneAt")
    for w in _walk_waiting(prev):
        prev_ids.add(w["id"])
    ever = set(prev.get("_generated", [])) | prev_ids

    for m in _walk_moves(doc):
        if m["id"] in done_state:
            m["done"] = True
            if done_state[m["id"]]:
                m["doneAt"] = done_state[m["id"]]

    # A chip we emitted before, gone from disk now, was cleared by the person.
    for it in _walk_inits(doc):
        it["waiting"] = [w for w in it["waiting"]
                         if not (w["id"] in ever and w["id"] not in prev_ids)]

    doc["today"] = prev.get("today", [])
    emitted = _all_ids(doc)
    doc["loose"] = [m for m in prev.get("loose", []) if m["id"] not in emitted]
    doc["_generated"] = sorted(ever | emitted)
    return doc


def _walk_inits(d):
    for g in d.get("goals", []):
        for it in g.get("inits", []):
            yield it


def _walk_moves(d):
    for it in _walk_inits(d):
        for m in it.get("moves", []):
            yield m
    for m in d.get("loose", []):
        yield m


def _walk_waiting(d):
    for it in _walk_inits(d):
        for w in it.get("waiting", []):
            yield w


def _all_ids(d):
    return {m["id"] for m in _walk_moves(d)} | {w["id"] for w in _walk_waiting(d)}


def write(doc, out_dir):
    errs = validate(doc)
    if errs:
        print("REFUSING TO WRITE — document is invalid:", file=sys.stderr)
        for e in errs:
            print("  -", e, file=sys.stderr)
        return 1
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "trailmap.json")
    doc = merge_onto_existing(doc, path)
    errs = validate(doc)          # merging brings back user data; re-check it
    if errs:
        print("REFUSING TO WRITE — merged document is invalid:", file=sys.stderr)
        for e in errs:
            print("  -", e, file=sys.stderr)
        return 1
    with open(path, "w") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")
    goals = len(doc["goals"])
    moves = sum(len(i.get("moves", [])) for g in doc["goals"] for i in g.get("inits", []))
    waits = sum(len(i.get("waiting", [])) for g in doc["goals"] for i in g.get("inits", []))
    print(f"wrote {path}")
    print(f"  {goals} goals, {moves} moves, {waits} waiting")
    return 0


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "brief-items.json"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "trailmap-brief")
    with open(src) as fh:
        sys.exit(write(json.load(fh), out))
