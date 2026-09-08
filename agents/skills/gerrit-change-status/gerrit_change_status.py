#!/usr/bin/env python3
"""Queries and summarizes Gerrit CL status across local repositories."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# Re-exec under Python >= 3.11 if available (satisfies depot_tools type hint and StrEnum requirements)
if sys.version_info < (3, 11):
    for candidate in [
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/opt/homebrew/opt/python@3.14/bin/python3",
        "/opt/homebrew/opt/python@3.13/bin/python3",
        "/opt/homebrew/opt/python@3.12/bin/python3",
        "/opt/homebrew/opt/python@3.11/bin/python3",
    ]:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            os.execv(candidate, [candidate] + sys.argv)

# Locate depot_tools for gerrit_util and gerrit_client
DEPOT_TOOLS_CANDIDATES = [
    os.environ.get("DEPOT_TOOLS", ""),
    os.path.expanduser("~/depot_tools"),
    "/opt/depot_tools",
    "/usr/local/depot_tools",
]

DEPOT_TOOLS_DIR: Optional[str] = None
for candidate_dir in DEPOT_TOOLS_CANDIDATES:
    if candidate_dir and os.path.isdir(candidate_dir):
        DEPOT_TOOLS_DIR = candidate_dir
        if candidate_dir not in sys.path:
            sys.path.insert(0, candidate_dir)
        break

try:
    import gerrit_util
except Exception:
    gerrit_util = None


def prettify_repo_path(repo_path: str) -> str:
    """Abbreviate user's home directory to ~ for clean display."""
    if not repo_path:
        return ""
    home = os.path.expanduser("~")
    if repo_path.startswith(home):
        return "~" + repo_path[len(home):]
    return repo_path


def format_repo_branch(repo_path: str, branch: str, delimiter: str = " : ") -> str:
    """Combine repository path and branch name using the specified delimiter."""
    pretty_repo = prettify_repo_path(repo_path)
    if pretty_repo and branch:
        return f"{pretty_repo}{delimiter}{branch}"
    elif branch:
        return branch
    elif pretty_repo:
        return pretty_repo
    return "-"


def find_git_repos(paths: List[str]) -> List[str]:
    """Find all git repository roots in given paths and immediate subdirectories."""
    repos: List[str] = []
    for path in paths:
        expanded = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(expanded):
            continue
        if os.path.isdir(os.path.join(expanded, ".git")):
            repos.append(expanded)
        # Also check immediate subdirectories (handles gclient checkouts with subrepos like ~/chrome/infra/build)
        try:
            for entry in sorted(os.listdir(expanded)):
                if entry.startswith("."):
                    continue
                sub = os.path.join(expanded, entry)
                if os.path.isdir(sub) and os.path.isdir(os.path.join(sub, ".git")):
                    repos.append(sub)
        except OSError:
            pass
    return sorted(list(set(repos)))


def get_repo_cls(repo_path: str) -> List[Tuple[str, str, str]]:
    """Return list of (cl_id, repo_path, branch_name) for branches configured with gerritissue."""
    results: List[Tuple[str, str, str]] = []
    try:
        out = subprocess.check_output(
            ["git", "config", "--get-regexp", r"^branch\..*\.gerritissue$"],
            cwd=repo_path,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        for line in out.strip().splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2:
                key, cl_id = parts
                branch_name = key[len("branch."):-len(".gerritissue")]
                results.append((cl_id.strip(), repo_path, branch_name))
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return results


def call_gerrit_client_fallback(
    host: str, command: str, args: List[str]
) -> Optional[Any]:
    """Fallback to calling gerrit_client.py when gerrit_util is not directly importable."""
    gerrit_client = shutil.which("gerrit_client.py")
    if not gerrit_client and DEPOT_TOOLS_DIR:
        candidate = os.path.join(DEPOT_TOOLS_DIR, "gerrit_client.py")
        if os.path.isfile(candidate):
            gerrit_client = candidate

    if not gerrit_client:
        return None

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
        tmp_json = tmp_file.name

    try:
        cmd = [
            "vpython3" if shutil.which("vpython3") else sys.executable,
            gerrit_client,
            command,
            "--host",
            host,
            f"--json_file={tmp_json}",
        ] + args
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if os.path.exists(tmp_json) and os.path.getsize(tmp_json) > 0:
            with open(tmp_json, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    finally:
        if os.path.exists(tmp_json):
            try:
                os.remove(tmp_json)
            except OSError:
                pass
    return None


def query_cl_detail(host: str, cl_id: str) -> Optional[Dict[str, Any]]:
    """Query Gerrit for change details, labels, requirements, and revisions."""
    netloc = host.replace("https://", "").replace("http://", "").rstrip("/")
    if gerrit_util:
        try:
            return gerrit_util.GetChangeDetail(
                netloc,
                cl_id,
                o_params=[
                    "DETAILED_LABELS",
                    "CURRENT_REVISION",
                    "MESSAGES",
                    "SUBMITTABLE",
                    "SUBMIT_REQUIREMENTS",
                ],
            )
        except Exception:
            pass

    # Fallback to gerrit_client.py
    data = call_gerrit_client_fallback(
        host,
        "changes",
        [
            "--query",
            f"change:{cl_id}",
            "-o",
            "DETAILED_LABELS",
            "-o",
            "CURRENT_REVISION",
            "-o",
            "SUBMITTABLE",
            "-o",
            "SUBMIT_REQUIREMENTS",
        ],
    )
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    return None


def query_cl_comments(host: str, cl_id: str) -> Dict[str, Any]:
    """Query Gerrit for comments on a change."""
    netloc = host.replace("https://", "").replace("http://", "").rstrip("/")
    if gerrit_util:
        try:
            return gerrit_util.CallGerritApi(netloc, f"changes/{cl_id}/comments")
        except Exception:
            pass

    # Fallback to gerrit_client.py
    data = call_gerrit_client_fallback(host, "comments", ["--change", cl_id])
    if isinstance(data, dict):
        return data
    return {}


def extract_unresolved_comments(comments_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Find all unresolved comment threads in a CL."""
    unresolved_threads: List[Dict[str, Any]] = []

    for filename, comment_list in comments_data.items():
        if not isinstance(comment_list, list):
            continue

        # Build thread graph: child -> parent
        child_to_parent: Dict[str, str] = {}
        by_id: Dict[str, Dict[str, Any]] = {}
        for c in comment_list:
            cid = c.get("id")
            if cid:
                by_id[cid] = c
                parent = c.get("in_reply_to")
                if parent:
                    child_to_parent[cid] = parent

        # Identify leaf comments in each thread (comments that have no replies)
        parents = set(child_to_parent.values())
        leaf_comments = [c for c in comment_list if c.get("id") not in parents]

        for leaf in leaf_comments:
            if leaf.get("unresolved", False):
                author = leaf.get("author", {})
                author_name = author.get("name") or author.get("email") or "Unknown"
                line = leaf.get("line")
                location = f"{filename}:{line}" if line else filename
                unresolved_threads.append(
                    {
                        "filename": filename,
                        "line": line,
                        "location": location,
                        "author": author_name,
                        "email": author.get("email", ""),
                        "message": leaf.get("message", "").strip(),
                        "date": leaf.get("updated", ""),
                    }
                )

    return unresolved_threads


def format_cr_votes(detail: Dict[str, Any]) -> str:
    """Format Code-Review label votes."""
    labels = detail.get("labels", {})
    cr_label = labels.get("Code-Review", {})
    all_votes = cr_label.get("all", [])

    positive: List[str] = []
    negative: List[str] = []

    for vote in all_votes:
        val = vote.get("value", 0)
        name = vote.get("name") or vote.get("email")
        if not name:
            name = f"Account {vote.get('_account_id')}"
        if val > 0:
            positive.append(f"+{val} ({name})")
        elif val < 0:
            negative.append(f"{val} ({name})")

    parts = []
    for p in positive:
        parts.append(f"**+1** ({p.split('(')[1] if '(' in p else p}")
    for n in negative:
        parts.append(f"**-1** ({n.split('(')[1] if '(' in n else n}")

    if not parts:
        return "*None*"
    return "<br>".join(parts)


def format_submittable(detail: Dict[str, Any]) -> Tuple[bool, str]:
    """Determine if CL is submittable and return (is_submittable, formatted_string)."""
    submittable = detail.get("submittable", False)

    # Check submit requirements if present
    reqs = detail.get("submit_requirements", [])
    if reqs:
        all_passed = True
        for req in reqs:
            status = req.get("status")
            if status not in ("SATISFIED", "NOT_APPLICABLE", "OVERRIDDEN", "FORCED"):
                all_passed = False
                break
        submittable = submittable or all_passed

    badge = "**YES**" if submittable else "**NO**"
    return submittable, badge


def determine_status_next_step(
    detail: Dict[str, Any],
    unresolved_comments: List[Dict[str, Any]],
    submittable: bool,
) -> str:
    """Generate concise next step guidance for the CL."""
    status = detail.get("status", "NEW")
    if status == "MERGED":
        return "Merged."
    if status == "ABANDONED":
        return "Abandoned."

    if submittable:
        return "Ready to land on CQ."

    if unresolved_comments:
        count = len(unresolved_comments)
        return f"{count} unresolved comment{'s' if count > 1 else ''} to address."

    reqs = detail.get("submit_requirements", [])
    reviewers = detail.get("reviewers", {}).get("REVIEWER", [])
    cr_all = detail.get("labels", {}).get("Code-Review", {}).get("all", [])
    voted_ids = {v.get("_account_id") for v in cr_all if v.get("value", 0) > 0}
    pending_reviewers = [r for r in reviewers if r.get("_account_id") not in voted_ids]

    for req in reqs:
        req_name = req.get("name")
        req_status = req.get("status")
        if req_status not in ("SATISFIED", "NOT_APPLICABLE", "OVERRIDDEN", "FORCED"):
            if req_name == "Code-Owners":
                return "Needs Code-Owners approval (+1)."
            if req_name == "Code-Review":
                if pending_reviewers:
                    names = [r.get("name") or r.get("email") or str(r.get("_account_id")) for r in pending_reviewers]
                    return f"Awaiting review from {', '.join(names[:2])}."
                return "Needs reviewers assigned."
            if req_name == "Review-Enforcement":
                return "Requires two approvals per Review-Enforcement."
            if req_name == "No-Unresolved-Comments":
                return "Unresolved comments block submit."
            return f"Requirement '{req_name}' is {req_status}."

    if pending_reviewers:
        names = [r.get("name") or r.get("email") or str(r.get("_account_id")) for r in pending_reviewers]
        return f"Awaiting review from {', '.join(names[:2])}."

    return "Awaiting review or tryjob completion."


def build_markdown_report(
    cl_records: List[Dict[str, Any]], delimiter: str = " : "
) -> str:
    """Generate comprehensive markdown report matching skill standards."""
    lines: List[str] = []

    # Column delimiter for header
    delim_display = delimiter.strip()
    header_delim = f" {delim_display} " if delim_display else " : "

    # 1. Summary Table
    lines.append("### Overall Summary\n")
    lines.append(
        f"| CL | Repository{header_delim}Branch | Subject | CR Votes | Submittable? | Status / Next Step |"
    )
    lines.append("|---|---|---|---|:---:|---|")

    total_unresolved = 0
    for item in cl_records:
        cl_id = item["cl_id"]
        cl_url = f"https://crrev.com/c/{cl_id}"
        repo_branch_str = format_repo_branch(item["repo_path"], item["branch"], delimiter)
        subject = item.get("subject", "").replace("|", "\\|")
        cr_votes = item.get("cr_votes_formatted", "*None*")
        submittable_badge = item.get("submittable_badge", "**NO**")
        next_step = item.get("next_step", "").replace("|", "\\|")
        total_unresolved += len(item.get("unresolved_comments", []))

        lines.append(
            f"| [{cl_id}]({cl_url}) | `{repo_branch_str}` | {subject} | {cr_votes} | {submittable_badge} | {next_step} |"
        )

    lines.append("\n---\n")

    # 2. Unresolved Comments Table (if any)
    lines.append("### Unresolved Comments\n")
    if total_unresolved == 0:
        lines.append("No open unresolved comments found across queried CLs.\n")
    else:
        lines.append(
            f"| # | CL | Repository{header_delim}Branch | Location | Reviewer | Comment Excerpt |"
        )
        lines.append("|---|---|---|---|---|---|")
        idx = 1
        for item in cl_records:
            cl_id = item["cl_id"]
            cl_url = f"https://crrev.com/c/{cl_id}"
            repo_branch_str = format_repo_branch(item["repo_path"], item["branch"], delimiter)
            for comment in item.get("unresolved_comments", []):
                loc = comment.get("location", "")
                author = comment.get("author", "")
                msg = comment.get("message", "").splitlines()[0] if comment.get("message") else ""
                if len(msg) > 80:
                    msg = msg[:77] + "..."
                msg = msg.replace("|", "\\|")
                lines.append(
                    f"| {idx} | [{cl_id}]({cl_url}) | `{repo_branch_str}` | `{loc}` | {author} | {msg} |"
                )
                idx += 1
        lines.append("")

    return "\n".join(lines)


def build_text_report(
    cl_records: List[Dict[str, Any]], delimiter: str = " : "
) -> str:
    """Generate plain text summary for console output."""
    lines: List[str] = []
    for item in cl_records:
        cl_id = item["cl_id"]
        repo_branch = format_repo_branch(item["repo_path"], item["branch"], delimiter)
        subject = item.get("subject", "")
        submittable = "YES" if item.get("submittable") else "NO"
        next_step = item.get("next_step", "")
        lines.append(f"CL {cl_id} [{repo_branch}]: {subject}")
        lines.append(f"  Submittable: {submittable} | Status: {next_step}")
        if item.get("unresolved_comments"):
            lines.append(f"  Unresolved comments: {len(item['unresolved_comments'])}")
        lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query and summarize Gerrit CL status, reviews, and comments across local repositories."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=[],
        help="Repository directories or parent paths to scan for git branches with Gerrit CLs (default: current directory).",
    )
    parser.add_argument(
        "--cl",
        action="append",
        default=[],
        help="Explicit Gerrit CL number(s) to inspect directly (repeatable or comma-separated).",
    )
    parser.add_argument(
        "--delimiter",
        default=" : ",
        help="Delimiter string between repository path and branch name (default: ' : ').",
    )
    parser.add_argument(
        "--host",
        default="https://chromium-review.googlesource.com",
        help="Gerrit host URL (default: https://chromium-review.googlesource.com).",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "text", "json"],
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--output",
        help="File path to save the generated report to.",
    )
    parser.add_argument(
        "--include-merged",
        action="store_true",
        help="Include CLs that have already been MERGED or ABANDONED.",
    )
    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Skip querying comments API for faster execution.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    cl_targets: List[Tuple[str, str, str]] = []

    # 1. Discover CLs from repository paths
    scan_paths = args.paths if args.paths else ["."]
    discovered_repos = find_git_repos(scan_paths)
    for repo in discovered_repos:
        repo_cls = get_repo_cls(repo)
        cl_targets.extend(repo_cls)

    # 2. Add explicit CL numbers
    for cl_arg in args.cl:
        for token in cl_arg.replace(",", " ").split():
            token = token.strip()
            if token:
                cl_targets.append((token, "", ""))

    if not cl_targets:
        print("No Gerrit CLs found in scanned repositories or provided via --cl.", file=sys.stderr)
        return 1

    # Remove duplicates preserving order
    seen: set = set()
    unique_targets: List[Tuple[str, str, str]] = []
    for cl_id, repo, branch in cl_targets:
        if not (re.match(r"^\d+$", cl_id) or re.match(r"^I[0-9a-fA-F]+$", cl_id)):
            print(f"Warning: Skipping invalid CL identifier: {cl_id}", file=sys.stderr)
            continue
        if cl_id not in seen:
            seen.add(cl_id)
            unique_targets.append((cl_id, repo, branch))

    records: List[Dict[str, Any]] = []

    for cl_id, repo, branch in unique_targets:
        detail = query_cl_detail(args.host, cl_id)
        if not detail:
            print(f"Warning: Could not fetch details for CL {cl_id}", file=sys.stderr)
            continue

        status = detail.get("status", "NEW")
        if not args.include_merged and status in ("MERGED", "ABANDONED"):
            continue

        unresolved_comments: List[Dict[str, Any]] = []
        if not args.no_comments:
            comments_data = query_cl_comments(args.host, cl_id)
            unresolved_comments = extract_unresolved_comments(comments_data)

        submittable, submittable_badge = format_submittable(detail)
        cr_votes_formatted = format_cr_votes(detail)
        next_step = determine_status_next_step(detail, unresolved_comments, submittable)

        record = {
            "cl_id": cl_id,
            "repo_path": repo,
            "branch": branch,
            "repo_branch": format_repo_branch(repo, branch, args.delimiter),
            "subject": detail.get("subject", ""),
            "status": status,
            "submittable": submittable,
            "submittable_badge": submittable_badge,
            "cr_votes_formatted": cr_votes_formatted,
            "unresolved_comments": unresolved_comments,
            "next_step": next_step,
            "detail": detail,
        }
        records.append(record)

    if args.format == "json":
        output_str = json.dumps(records, indent=2)
    elif args.format == "text":
        output_str = build_text_report(records, delimiter=args.delimiter)
    else:
        output_str = build_markdown_report(records, delimiter=args.delimiter)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str + "\n")
        print(f"Report written to {args.output}")
    else:
        print(output_str)

    return 0


if __name__ == "__main__":
    sys.exit(main())
