#!/usr/bin/env python3
"""Find Jetski conversations whose transcripts mention a CL, bug, branch, or string.

Read-only: only reads transcript files under the Jetski brain directory and
(optionally) `git config` in local repositories. Never writes anything.

Usage:
  find_conversation.py QUERY [QUERY...] [--repo PATH ...] [--exclude ID ...]
                       [--full] [--include-subagents] [--limit N] [--json]

QUERY forms understood:
  7123456, crrev.com/c/7123456, chromium-review.googlesource.com/c/.../+/7123456
  b/123456789, crbug.com/123456789, issues.chromium.org/issues/123456789
  a local branch name (also expands to its Gerrit CL via git config)
  any other literal string (case-insensitive)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

BRAIN = os.path.expanduser("~/.gemini/jetski/brain")
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
# Matches the invoke_subagent tool output regardless of JSON escaping depth.
SUBAGENT_RE = re.compile(r'Created the following subagent:.{0,300}?conversationId'
                         r'[\\"\s:]+(' + UUID_RE.pattern + r')')
NUM_PATTERNS = [
    r"crrev\.com/c/(\d+)",
    r"googlesource\.com/c/.*?/\+/(\d+)",
    r"\bcl/(\d+)",
    r"\bb/(\d+)",
    r"crbug\.com/(?:\d+/)?(\d+)",
    r"issues\.chromium\.org/issues/(\d+)",
    r"issuetracker\.google\.com/issues/(\d+)",
    r"^(\d{5,})$",
]


def git_branch_cl(branch, repos):
  """Returns Gerrit CL numbers recorded for `branch` in any of `repos`."""
  cls = set()
  for repo in repos:
    try:
      out = subprocess.run(
          ["git", "-C", repo, "config", "--get", f"branch.{branch}.gerritissue"],
          capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
      continue
    if out.isdigit():
      cls.add(out)
  return cls


def build_terms(queries, repos):
  """Returns a list of (label, compiled_regex, lowercase_prefilter)."""
  terms = {}
  for q in queries:
    q = q.strip()
    num = None
    for pat in NUM_PATTERNS:
      m = re.search(pat, q)
      if m:
        num = m.group(1)
        break
    if num:
      terms[num] = (re.compile(r"(?<!\d)" + num + r"(?!\d)"), num)
      continue
    terms[q] = (re.compile(re.escape(q), re.IGNORECASE), q.lower())
    for cl in git_branch_cl(q, repos):
      terms[f"{cl} (CL for {q})"] = (re.compile(r"(?<!\d)" + cl + r"(?!\d)"), cl)
  return [(label, rx, pre) for label, (rx, pre) in terms.items()]


def clean_user_text(text):
  text = re.sub(r"</?USER_REQUEST>", "", text or "")
  text = re.sub(r"<ADDITIONAL_METADATA>.*?</ADDITIONAL_METADATA>", "", text,
                flags=re.S)
  return " ".join(text.split())


def scan(conv_id, path, terms):
  info = {"id": conv_id, "hits": 0, "terms": {}, "first_ts": None,
          "last_ts": None, "last_hit_ts": None, "first_user": None,
          "last_user": None, "steps": 0, "children": set()}
  with open(path, errors="replace") as f:
    for line in f:
      info["steps"] += 1
      low = line.lower()
      if "created the following subagent" in low:
        info["children"].update(SUBAGENT_RE.findall(line))
      matched = [label for label, rx, pre in terms
                 if pre in low and rx.search(line)]
      is_user = '"USER_INPUT"' in line
      if not (matched or is_user or info["first_ts"] is None):
        # Cheap path: still track last timestamp.
        m = re.search(r'"created_at":\s*"([^"]+)"', line)
        if m:
          info["last_ts"] = m.group(1)
        continue
      try:
        o = json.loads(line)
      except ValueError:
        continue
      ts = o.get("created_at")
      info["first_ts"] = info["first_ts"] or ts
      info["last_ts"] = ts or info["last_ts"]
      if is_user and o.get("type") == "USER_INPUT":
        text = clean_user_text(o.get("content"))
        if text:
          info["first_user"] = info["first_user"] or text
          info["last_user"] = text
      if matched:
        info["hits"] += 1
        info["last_hit_ts"] = ts or info["last_hit_ts"]
        for label in matched:
          info["terms"][label] = info["terms"].get(label, 0) + 1
  return info


def short(text, n=160):
  if not text:
    return ""
  return text if len(text) <= n else text[: n - 1] + "…"


def day(ts):
  if not ts:
    return "?"
  try:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime(
        "%Y-%m-%d %H:%M")
  except ValueError:
    return ts


def main():
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("queries", nargs="+")
  ap.add_argument("--repo", action="append", default=[],
                  help="Git repo(s) used to expand branch names to CL numbers "
                  "(default: current directory).")
  ap.add_argument("--exclude", action="append", default=[],
                  help="Conversation ID(s) to skip, e.g. the current one.")
  ap.add_argument("--full", action="store_true",
                  help="Search transcript_full.jsonl (untruncated, slower).")
  ap.add_argument("--include-subagents", action="store_true",
                  help="Also list subagent conversations.")
  ap.add_argument("--limit", type=int, default=10)
  ap.add_argument("--json", action="store_true")
  args = ap.parse_args()

  repos = args.repo or [os.getcwd()]
  terms = build_terms(args.queries, repos)
  if not os.path.isdir(BRAIN):
    sys.exit(f"No Jetski brain directory at {BRAIN}")

  ids = [d for d in os.listdir(BRAIN) if UUID_RE.fullmatch(d)]
  visible = len(ids)
  results, subagents = [], set()
  fname = "transcript_full.jsonl" if args.full else "transcript.jsonl"
  for cid in ids:
    path = os.path.join(BRAIN, cid, ".system_generated", "logs", fname)
    if not os.path.exists(path):
      continue
    info = scan(cid, path, terms)
    subagents |= info["children"]
    if info["hits"] and cid not in args.exclude:
      results.append(info)

  for r in results:
    r["subagent"] = r["id"] in subagents
    r["children"] = sorted(r["children"])
  if not args.include_subagents:
    results = [r for r in results if not r["subagent"]]
  results.sort(key=lambda r: (r["hits"], r["last_hit_ts"] or ""), reverse=True)
  results = results[: args.limit]

  if args.json:
    print(json.dumps({"terms": [t[0] for t in terms], "results": results},
                     indent=2, default=list))
    return

  print(f"Search terms: {', '.join(t[0] for t in terms)}")
  print(f"Scanned {visible} conversation directories in {BRAIN}.")
  if visible <= 2:
    print("WARNING: very few conversations visible; the sandbox probably hides "
          "other conversations. Re-run with BypassSandbox: true.")
  if not results:
    print("\nNo matching conversations.")
    return
  print()
  print("| # | Conversation | Hits | Active (local) | Started with | Last request |")
  print("|---|---|---|---|---|---|")
  for i, r in enumerate(results, 1):
    tag = " (subagent)" if r["subagent"] else ""
    print(f"| {i} | [{r['id'][:8]}](conversation://{r['id']}){tag} | {r['hits']} | "
          f"{day(r['first_ts'])} → {day(r['last_ts'])} | "
          f"{short(r['first_user'], 90).replace('|', '/')} | "
          f"{short(r['last_user'], 90).replace('|', '/')} |")
  print()
  for i, r in enumerate(results, 1):
    terms_s = ", ".join(f"{k}×{v}" for k, v in r["terms"].items())
    print(f"{i}. {r['id']}  steps={r['steps']}  matched: {terms_s}")


if __name__ == "__main__":
  main()
