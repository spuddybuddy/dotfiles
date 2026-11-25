#!/usr/bin/env python3
"""Compute a read-only plan for updating all local branches in a git repository.

For every local (non-base) branch, in parent-first order, reports:
  - its parent (upstream) branch and Gerrit CL status,
  - the fork point (the commit the branch's own changes start from),
  - the number of commits unique to the branch,
  - the planned action: `delete` (CL merged/abandoned) or `rebase` onto a new parent.

The fork points MUST be captured before any branch is deleted, squashed, or rebased,
because deleting/rewriting a parent branch makes it impossible to tell which commits
belong to the child. Save the JSON output and use it for the whole session.

This script never modifies the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

SKILLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILLS_DIR, "gerrit-change-status"))

BASE_BRANCHES = ["main", "master", "lkgr", "gh-pages"]
CLOSED_STATUSES = ("MERGED", "ABANDONED")
DEFAULT_HOST = "https://chromium-review.googlesource.com"


def git(args: List[str], cwd: str, check: bool = False) -> Optional[str]:
    res = subprocess.run(
        ["git"] + args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if res.returncode != 0:
        if check:
            raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
        return None
    return res.stdout.strip()


def rev_parse(repo: str, rev: Optional[str]) -> Optional[str]:
    if not rev:
        return None
    return git(["rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"], repo)


def is_ancestor(repo: str, ancestor: str, descendant: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=repo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def branch_config(repo: str) -> Dict[str, Dict[str, str]]:
    """Returns {branch: {key: value}} from all branch.<name>.<key> config entries."""
    out = git(["config", "--get-regexp", r"^branch\."], repo) or ""
    config: Dict[str, Dict[str, str]] = {}
    for line in out.splitlines():
        key, _, value = line.partition(" ")
        name, _, subkey = key[len("branch."):].rpartition(".")
        config.setdefault(name, {})[subkey] = value
    return config


def local_branches(repo: str) -> List[str]:
    out = git(["for-each-ref", "--format=%(refname:short)", "refs/heads/"], repo, check=True)
    return [b for b in (out or "").splitlines() if b]


def parent_of(name: str, cfg: Dict[str, str]) -> Optional[str]:
    """Returns the upstream branch name (local name, or base name for remote bases)."""
    merge = cfg.get("merge")
    if not merge:
        return None
    short = merge[len("refs/heads/"):] if merge.startswith("refs/heads/") else merge
    return short


def topo_sort(branches: List[str], parents: Dict[str, Optional[str]]) -> List[str]:
    branch_set = set(branches)
    result: List[str] = []
    visited: set = set()
    visiting: set = set()

    def visit(b: str) -> None:
        if b in visited or b in visiting:
            return
        visiting.add(b)
        p = parents.get(b)
        if p in branch_set:
            visit(p)
        visiting.discard(b)
        visited.add(b)
        result.append(b)

    for b in sorted(branches):
        visit(b)
    return result


def query_statuses(issues: Dict[str, str], hosts: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """Returns {cl_number: gerrit change detail}, grouped by Gerrit host."""
    try:
        from gerrit_change_status import query_cl_details_batch  # type: ignore
    except ImportError as exc:
        print(f"Warning: could not import gerrit_change_status: {exc}", file=sys.stderr)
        return {}
    by_host: Dict[str, List[str]] = {}
    for branch, issue in issues.items():
        by_host.setdefault(hosts.get(branch) or DEFAULT_HOST, []).append(issue)
    details: Dict[str, Dict[str, Any]] = {}
    for host, cl_ids in by_host.items():
        details.update(query_cl_details_batch(host, sorted(set(cl_ids))) or {})
    return details


def build_plan(repo: str, offline: bool) -> Dict[str, Any]:
    repo = git(["rev-parse", "--show-toplevel"], repo, check=True) or repo
    all_branches = local_branches(repo)
    present_bases = [b for b in BASE_BRANCHES if b in all_branches]
    default_base = "main" if "main" in present_bases else (present_bases[0] if present_bases else None)
    cfg = branch_config(repo)
    branches = [b for b in all_branches if b not in BASE_BRANCHES]

    parents = {b: parent_of(b, cfg.get(b, {})) for b in branches}
    order = topo_sort(branches, parents)

    issues = {b: cfg[b]["gerritissue"] for b in branches if cfg.get(b, {}).get("gerritissue")}
    hosts = {b: cfg[b].get("gerritserver", DEFAULT_HOST) for b in issues}
    details = {} if offline else query_statuses(issues, hosts)

    entries: List[Dict[str, Any]] = []
    deleted: set = set()
    for b in order:
        bcfg = cfg.get(b, {})
        head = rev_parse(repo, f"refs/heads/{b}")
        parent = parents[b]
        parent_is_local = parent in all_branches
        # Remote-tracking upstreams like origin/main map onto the local base branch.
        if parent and not parent_is_local:
            tail = parent.split("/")[-1]
            if tail in present_bases:
                parent, parent_is_local = tail, True

        # Fork point: prefer depot_tools' branch.<b>.base, else merge-base with the parent.
        fork_point, fork_source = None, None
        cfg_base = rev_parse(repo, bcfg.get("base"))
        if cfg_base and head and is_ancestor(repo, cfg_base, head):
            fork_point, fork_source = cfg_base, "branch.base"
        else:
            ref = parent if parent_is_local else default_base
            if ref:
                mb = git(["merge-base", f"refs/heads/{ref}", f"refs/heads/{b}"], repo)
                if mb:
                    fork_point, fork_source = mb, f"merge-base({ref})"

        commits: List[str] = []
        if fork_point:
            log = git(["log", "--format=%h %s", "--reverse", f"{fork_point}..refs/heads/{b}"], repo)
            commits = [c for c in (log or "").splitlines() if c]

        issue = issues.get(b)
        detail = details.get(issue, {}) if issue else {}
        status = detail.get("status") if detail else None
        last_upload = bcfg.get("last-upload-hash")
        unuploaded = bool(issue and last_upload and head and last_upload != head)

        notes: List[str] = []
        if status in CLOSED_STATUSES:
            action, new_parent = "delete", None
            deleted.add(b)
            if unuploaded:
                notes.append("HEAD differs from last-upload-hash: local changes were never uploaded; confirm before deleting")
        else:
            action = "rebase"
            if parent and parent_is_local and parent not in deleted:
                new_parent = parent
            else:
                new_parent = default_base
                if parent in deleted:
                    notes.append(f"parent '{parent}' will be deleted; reparenting onto {default_base}")
                elif not parent:
                    notes.append(f"no upstream configured; using {default_base}")
                else:
                    notes.append(f"upstream '{parent}' is not a local branch; using {default_base}")
            if issue and not offline and not detail:
                notes.append(f"could not fetch status for CL {issue}")
            if not fork_point:
                action = "skip"
                notes.append("could not determine fork point")
            elif not commits:
                notes.append("branch has no commits of its own")

        entries.append(
            {
                "branch": b,
                "parent": parent,
                "action": action,
                "new_parent": new_parent,
                "head": head,
                "fork_point": fork_point,
                "fork_source": fork_source,
                "commit_count": len(commits),
                "commits": commits,
                "gerritissue": issue,
                "cl_status": status,
                "cl_subject": detail.get("subject") if detail else None,
                "unuploaded_changes": unuploaded,
                "notes": notes,
            }
        )

    return {
        "repo_root": repo,
        "current_branch": git(["branch", "--show-current"], repo),
        "base_branches": present_bases,
        "default_base": default_base,
        "branches": entries,
    }


def format_text(plan: Dict[str, Any]) -> str:
    lines = [
        f"Repository: {plan['repo_root']}  (current branch: {plan['current_branch'] or 'detached'})",
        f"Base branches: {', '.join(plan['base_branches'])}",
        "",
    ]
    for e in plan["branches"]:
        cl = f"CL {e['gerritissue']} [{e['cl_status'] or '?'}]" if e["gerritissue"] else "no CL"
        if e["action"] == "delete":
            what = "DELETE"
        elif e["action"] == "rebase":
            what = f"REBASE onto {e['new_parent']}"
            if e["commit_count"] >= 2:
                what += f" (squash {e['commit_count']} commits first)"
        else:
            what = "SKIP"
        fork = (e["fork_point"] or "?")[:12]
        lines.append(f"- {e['branch']}: {what}; parent={e['parent']}; {cl}; fork={fork}; commits={e['commit_count']}")
        for n in e["notes"]:
            lines.append(f"    note: {n}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-C", "--repo", default=".", help="Path to the git repository (default: .)")
    parser.add_argument("--offline", action="store_true", help="Do not query Gerrit for CL status.")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    parser.add_argument("--output", help="Also write the JSON plan to this file.")
    args = parser.parse_args()

    try:
        plan = build_plan(args.repo, args.offline)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
            f.write("\n")
    print(json.dumps(plan, indent=2) if args.format == "json" else format_text(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
