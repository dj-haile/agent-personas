#!/usr/bin/env python3
"""Rebuild the chief-of-staff agent's `tools:` line for whatever machine you are on.

    python3 scripts/gen-agent-tools.py            # print the line
    python3 scripts/gen-agent-tools.py --write    # write it into the agent file

Why this exists. The tool list is the only thing enforcing read-only — Slack and
Linear grant write scopes, so leaving `slack_send_message` and `save_issue` out
of the list is what prevents the agent writing. But connector tools are named
with a per-machine id, so a list written on one machine names nothing on the
next. This turns that from a setup failure into a setup step.

The list below is the portable part: connector display names and tool names,
which are stable. Only the ids are looked up locally.

TWO FAILURE MODES THIS GUARDS AGAINST, both silent by default:

  A stale entry.   A tool the connector no longer offers is dropped from the
                   agent's list without complaint, and the agent loses a
                   capability without anyone being told. Reported here as WARN.

  A partial list.  Claude Code refuses to launch a subagent only when EVERY
                   entry fails. Since `Read, Grep, Glob, Write` always resolve,
                   an agent whose 48 connector entries all failed still starts —
                   and writes you a brief with no Slack, Linear, Gmail or
                   Calendar in it, saying nothing about the hole. That is worse
                   than a crash. `--check` exits non-zero if any connector is
                   missing, so a setup script can stop.

If you run the agent from a terminal Claude Code session rather than the desktop
app, connector tools are instead named `mcp__claude_ai_<Connector>__<tool>`,
which is already stable across machines and needs no generation. Confirm the
exact server spellings with /mcp before relying on that.
"""
import glob
import json
import os
import re
import sys

SESSIONS = os.path.expanduser(
    "~/Library/Application Support/Claude/local-agent-mode-sessions")
AGENT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "claude-agents", "chief-of-staff.md")

BUILTINS = ["Read", "Grep", "Glob", "Write"]

# Connector display name -> the read tools the agent is allowed. Anything absent
# here is denied, including every write tool these connectors expose.
WANT = {
    "Slack": [
        "slack_read_channel", "slack_read_thread", "slack_read_user_profile",
        "slack_read_canvas", "slack_read_file", "slack_list_channel_members",
        "slack_search_channels", "slack_search_public_and_private",
        "slack_search_users",
    ],
    "Google Calendar": ["list_calendars", "list_events", "get_event", "search_events"],
    "Gmail": ["search_threads", "get_thread", "get_message", "list_labels"],
    "Linear": [
        "list_issues", "get_issue", "get_issue_status", "list_issue_statuses",
        "list_comments", "list_projects", "get_project", "list_teams",
        "get_team", "list_users", "get_user", "list_cycles", "list_documents",
        "get_document", "list_diffs", "get_diff", "get_status_updates",
    ],
}

# Servers added with `claude mcp add` are named by the name you gave them, not
# by a generated id, so these are already portable. They only need the same
# server name on the new machine.
LITERAL = [
    "mcp__github__get_me", "mcp__github__list_pull_requests",
    "mcp__github__pull_request_read", "mcp__github__search_pull_requests",
    "mcp__github__list_issues", "mcp__github__issue_read",
    "mcp__github__search_issues", "mcp__github__list_commits",
    "mcp__github__list_branches", "mcp__github__search_repositories",
    "mcp__github__list_repository_collaborators", "mcp__github__get_file_contents",
    "mcp__github__get_teams", "mcp__github__get_team_members",
]


def local_connectors():
    """Connector inventory from the desktop app's newest session record."""
    files = [f for f in glob.glob(os.path.join(SESSIONS, "*", "*", "local_*.json"))
             if os.path.isfile(f)]
    if not files:
        return None, None
    newest = max(files, key=os.path.getmtime)
    servers = json.load(open(newest)).get("remoteMcpServersConfig", [])
    return newest, {s["name"]: s for s in servers}


def build():
    source, by_name = local_connectors()
    if by_name is None:
        return None, source, ["no desktop session record found — are you in a "
                              "terminal session? then the tools are already "
                              "portable and this script is not needed"]
    out, warn = list(BUILTINS), []
    for connector, tools in WANT.items():
        s = by_name.get(connector)
        if not s:
            warn.append(f"connector not connected: {connector} "
                        f"({len(tools)} tools unavailable)")
            continue
        offered = {t["name"] for t in s.get("tools", [])}
        for t in tools:
            if t in offered:
                out.append(f'mcp__{s["uuid"]}__{t}')
            else:
                warn.append(f"{connector}: no longer offers {t}")
    out += LITERAL
    return out, source, warn


def main(argv):
    tools, source, warn = build()
    if source:
        print(f"read connectors from: {source}", file=sys.stderr)
    for w in warn:
        print(f"WARN {w}", file=sys.stderr)
    if tools is None:
        return 2

    line = "tools: " + ", ".join(tools)
    connectors_missing = any(w.startswith("connector not connected") for w in warn)

    if "--check" in argv:
        print(f"{len(tools)} tools resolved", file=sys.stderr)
        return 1 if connectors_missing else 0

    if "--write" in argv:
        path = os.path.normpath(AGENT_FILE)
        text = open(path).read()
        new, n = re.subn(r"^tools: .+$", line, text, count=1, flags=re.M)
        if not n:
            print(f"no tools: line found in {path}", file=sys.stderr)
            return 2
        open(path, "w").write(new)
        print(f"wrote {len(tools)} tools into {path}", file=sys.stderr)
        print("copy it into place:  cp claude-agents/chief-of-staff.md "
              "~/.claude/agents/", file=sys.stderr)
        print("then RESTART Claude Code — agent definitions are cached per "
              "session.", file=sys.stderr)
        return 1 if connectors_missing else 0

    print(line)
    return 1 if connectors_missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
