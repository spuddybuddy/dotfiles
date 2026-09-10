#!/usr/bin/env python3
"""CLI tool and agent skill to query and reply to Gerrit comments using gerrit_client.py."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# Locate depot_tools for gerrit_client.py and vpython3
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
        break

DEFAULT_HOST = "https://chromium-review.googlesource.com"


def normalize_host(host: str) -> str:
    """Ensure host has https:// scheme and no trailing slash."""
    host = host.strip()
    if not host.startswith("http://") and not host.startswith("https://"):
        host = f"https://{host}"
    return host.rstrip("/")


def detect_repo_cl_and_host(cwd: str = ".") -> Tuple[Optional[str], Optional[str]]:
    """Detect Gerrit change ID and host from current git branch config."""
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if not branch or branch == "HEAD":
            return None, None

        cl = subprocess.check_output(
            ["git", "config", f"branch.{branch}.gerritissue"],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()

        try:
            host = subprocess.check_output(
                ["git", "config", f"branch.{branch}.gerritserver"],
                cwd=cwd,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except subprocess.CalledProcessError:
            host = None

        return cl or None, host or None
    except Exception:
        return None, None


def call_gerrit_client(
    host: str, command: str, args: List[str]
) -> Optional[Any]:
    """Call gerrit_client.py using vpython3."""
    gerrit_client = shutil.which("gerrit_client.py")
    if not gerrit_client and DEPOT_TOOLS_DIR:
        candidate = os.path.join(DEPOT_TOOLS_DIR, "gerrit_client.py")
        if os.path.isfile(candidate):
            gerrit_client = candidate

    if not gerrit_client:
        raise RuntimeError(
            "Could not locate gerrit_client.py in PATH or depot_tools."
        )

    vpython = shutil.which("vpython3")
    if not vpython and DEPOT_TOOLS_DIR:
        candidate = os.path.join(DEPOT_TOOLS_DIR, "vpython3")
        if os.path.isfile(candidate):
            vpython = candidate
    py_exec = vpython if vpython else sys.executable

    host = normalize_host(host)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
        tmp_json = tmp_file.name

    try:
        cmd = [
            py_exec,
            gerrit_client,
            command,
            "--host",
            host,
            f"--json_file={tmp_json}",
        ] + args
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if os.path.exists(tmp_json) and os.path.getsize(tmp_json) > 0:
            with open(tmp_json, "r", encoding="utf-8") as f:
                return json.load(f)
        if res.returncode != 0:
            err_msg = res.stderr.strip() or res.stdout.strip()
            raise RuntimeError(f"gerrit_client.py failed ({res.returncode}): {err_msg}")
    finally:
        if os.path.exists(tmp_json):
            try:
                os.remove(tmp_json)
            except OSError:
                pass
    return None


def query_comments(host: str, cl_id: str) -> Dict[str, Any]:
    """Query Gerrit for published comments on a change via gerrit_client.py."""
    data = call_gerrit_client(host, "comments", ["--change", cl_id])
    if isinstance(data, dict):
        return data
    return {}


def post_review(
    host: str, cl_id: str, payload: Dict[str, Any], revision: str = "current"
) -> Dict[str, Any]:
    """Submit a review payload via gerrit_client.py rawapi."""
    path = f"changes/{cl_id}/revisions/{revision}/review"
    raw_args = [
        "--path",
        path,
        "--method",
        "POST",
        "--body",
        json.dumps(payload),
    ]
    res = call_gerrit_client(host, "rawapi", raw_args)
    if isinstance(res, dict):
        return res
    raise RuntimeError("No response returned from gerrit_client.py rawapi.")


def find_comment_by_id(
    comments_dict: Dict[str, Any], comment_id: str
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Locate comment and its file path by comment ID."""
    for filename, comment_list in comments_dict.items():
        if not isinstance(comment_list, list):
            continue
        for c in comment_list:
            if c.get("id") == comment_id:
                return filename, c
    return None, None


def group_comments_into_threads(
    comment_list: List[Dict[str, Any]],
) -> List[List[Dict[str, Any]]]:
    """Group flat list of comments into chronological threads."""
    by_id: Dict[str, Dict[str, Any]] = {}
    child_to_parent: Dict[str, str] = {}

    for c in comment_list:
        cid = c.get("id")
        if cid:
            by_id[cid] = c
            parent = c.get("in_reply_to")
            if parent:
                child_to_parent[cid] = parent

    def get_root(cid: str) -> str:
        visited = set()
        curr = cid
        while curr in child_to_parent:
            if curr in visited:
                break
            visited.add(curr)
            curr = child_to_parent[curr]
        return curr

    threads_by_root: Dict[str, List[Dict[str, Any]]] = {}
    for c in comment_list:
        cid = c.get("id")
        if not cid:
            continue
        root = get_root(cid)
        threads_by_root.setdefault(root, []).append(c)

    threads: List[List[Dict[str, Any]]] = []
    for root, thread in threads_by_root.items():
        thread.sort(key=lambda x: x.get("updated", ""))
        threads.append(thread)

    threads.sort(key=lambda th: th[0].get("updated", ""))
    return threads


def format_threads_display(
    comments_dict: Dict[str, Any], unresolved_only: bool = False
) -> str:
    """Format comments into a readable string showing threads and resolution status."""
    out_lines: List[str] = []
    total_threads = 0
    total_unresolved = 0

    for filename in sorted(comments_dict.keys()):
        comment_list = comments_dict.get(filename, [])
        if not isinstance(comment_list, list) or not comment_list:
            continue

        threads = group_comments_into_threads(comment_list)
        file_printed = False

        for thread in threads:
            total_threads += 1
            leaf = thread[-1]
            is_unresolved = leaf.get("unresolved", False)
            if is_unresolved:
                total_unresolved += 1

            if unresolved_only and not is_unresolved:
                continue

            if not file_printed:
                out_lines.append(f"\n📂 File: {filename}")
                file_printed = True

            root = thread[0]
            line_str = f":{root.get('line')}" if root.get("line") else " (patchset level)"
            status_str = "🔴 UNRESOLVED" if is_unresolved else "🟢 RESOLVED"
            out_lines.append(f"  ── Thread at {filename}{line_str} [{status_str}] ──")

            for idx, c in enumerate(thread):
                author = c.get("author", {})
                author_name = (
                    author.get("display_name")
                    or author.get("name")
                    or author.get("email")
                    or "Unknown"
                )
                cid = c.get("id", "")
                ps = c.get("patch_set", "?")
                updated = c.get("updated", "")[:19]
                indent = "     " if idx == 0 else "       ↳ "
                out_lines.append(f"{indent}[{cid}] {author_name} (PS{ps}, {updated}):")
                msg = c.get("message", "").strip()
                for msg_line in msg.splitlines():
                    out_lines.append(f"{indent}  {msg_line}")

    summary_str = f"Found {total_threads} thread(s) ({total_unresolved} unresolved)."
    if not out_lines:
        return f"No comments found matching filter. {summary_str}"

    return "\n".join(out_lines) + f"\n\n{summary_str}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query and reply to Gerrit comments using gerrit_client.py.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # List all comments on the current branch's CL:
  python3 gerrit_comment_reply.py --list

  # List only unresolved comments on CL 8351276:
  python3 gerrit_comment_reply.py --cl 8351276 --list --unresolved-only

  # Reply to a comment thread and mark it resolved (default):
  python3 gerrit_comment_reply.py --reply-to 3e2bf9a2_ac21bfa4 -m "Done, updated as suggested."

  # Quick "Done" or "Ack":
  python3 gerrit_comment_reply.py --reply-to 3e2bf9a2_ac21bfa4 --done
  python3 gerrit_comment_reply.py --reply-to 3e2bf9a2_ac21bfa4 --ack

  # Reply but keep unresolved:
  python3 gerrit_comment_reply.py --reply-to 3e2bf9a2_ac21bfa4 -m "Looking into this." --unresolved

  # Post a patchset-level comment:
  python3 gerrit_comment_reply.py --patchset-comment -m "Uploaded new patchset with fix."

  # Preview JSON payload without sending:
  python3 gerrit_comment_reply.py --reply-to 3e2bf9a2_ac21bfa4 -m "Testing" --dry-run
""",
    )

    parser.add_argument(
        "--cl",
        help="Gerrit change number or Change-Id (defaults to detecting from current git branch).",
    )
    parser.add_argument(
        "--host",
        help=f"Gerrit host URL (defaults to branch config or {DEFAULT_HOST}).",
    )
    parser.add_argument(
        "--revision",
        default="current",
        help="Revision ID or patchset number (default: 'current').",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all published comment threads on the change.",
    )
    parser.add_argument(
        "--unresolved-only",
        action="store_true",
        help="When listing comments, show only unresolved threads.",
    )
    parser.add_argument(
        "--reply-to",
        help="Comment ID to reply to. Automatically detects file and threads reply.",
    )
    parser.add_argument(
        "-m",
        "--message",
        help="Reply message content.",
    )
    parser.add_argument(
        "--message-file",
        help="File path to read reply message from ('-' for stdin).",
    )
    parser.add_argument(
        "--done",
        action="store_true",
        help="Convenience flag to reply with 'Done' and resolve thread.",
    )
    parser.add_argument(
        "--ack",
        action="store_true",
        help="Convenience flag to reply with 'Ack' and resolve thread.",
    )
    parser.add_argument(
        "--resolved",
        dest="unresolved",
        action="store_false",
        default=False,
        help="Mark comment as resolved (default).",
    )
    parser.add_argument(
        "--unresolved",
        dest="unresolved",
        action="store_true",
        help="Mark comment as unresolved.",
    )
    parser.add_argument(
        "--patchset-comment",
        action="store_true",
        help="Post comment to /PATCHSET_LEVEL.",
    )
    parser.add_argument(
        "--change-message",
        action="store_true",
        help="Post as a top-level review message on the change instead of an inline comment.",
    )
    parser.add_argument(
        "--file",
        help="Target file path (only required if not replying to an existing comment and not /PATCHSET_LEVEL).",
    )
    parser.add_argument(
        "--line",
        type=int,
        help="Line number for a new inline comment.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the API payload without executing the request.",
    )

    args = parser.parse_args()

    cl_id = args.cl
    host = args.host

    detected_cl, detected_host = detect_repo_cl_and_host()
    if not cl_id:
        cl_id = detected_cl

    if not host:
        host = detected_host or DEFAULT_HOST

    if not cl_id:
        parser.error(
            "Gerrit CL not specified and could not be detected from current branch. "
            "Please specify --cl <CHANGE_ID>."
        )

    host = normalize_host(host)

    # Action: List comments
    if args.list or (
        not args.reply_to
        and not args.message
        and not args.message_file
        and not args.done
        and not args.ack
        and not args.patchset_comment
        and not args.change_message
    ):
        print(f"Fetching comments for CL {cl_id} from {host}...")
        try:
            comments = query_comments(host, cl_id)
            display = format_threads_display(comments, unresolved_only=args.unresolved_only)
            print(display)
            return 0
        except Exception as e:
            print(f"❌ Error fetching comments: {e}", file=sys.stderr)
            return 1

    # Determine message content
    message = args.message
    if args.done:
        message = "Done"
    elif args.ack:
        message = "Ack"
    elif args.message_file:
        if args.message_file == "-":
            message = sys.stdin.read()
        else:
            with open(args.message_file, "r", encoding="utf-8") as f:
                message = f.read()

    if not message:
        parser.error(
            "Reply message is required (use -m, --message, --message-file, --done, or --ack)."
        )

    # Construct review payload
    payload: Dict[str, Any] = {"drafts": "KEEP"}

    if args.change_message:
        payload["message"] = message.strip()
    elif args.reply_to:
        print(f"Resolving parent comment {args.reply_to} on CL {cl_id}...")
        try:
            comments = query_comments(host, cl_id)
        except Exception as e:
            print(f"❌ Error fetching comments: {e}", file=sys.stderr)
            return 1

        target_file, parent_comment = find_comment_by_id(comments, args.reply_to)

        if not target_file:
            if args.file:
                target_file = args.file
            else:
                print(
                    f"Error: Comment ID '{args.reply_to}' not found on CL {cl_id}.",
                    file=sys.stderr,
                )
                print(
                    "Run with --list to view valid comment IDs.",
                    file=sys.stderr,
                )
                return 1

        comment_obj: Dict[str, Any] = {
            "in_reply_to": args.reply_to,
            "message": message.strip(),
            "unresolved": args.unresolved,
        }
        payload["comments"] = {target_file: [comment_obj]}
    elif args.patchset_comment:
        comment_obj = {
            "message": message.strip(),
            "unresolved": args.unresolved,
        }
        payload["comments"] = {"/PATCHSET_LEVEL": [comment_obj]}
    elif args.file:
        comment_obj = {
            "message": message.strip(),
            "unresolved": args.unresolved,
        }
        if args.line:
            comment_obj["line"] = args.line
        payload["comments"] = {args.file: [comment_obj]}
    else:
        parser.error(
            "Please specify a target for the message: --reply-to <ID>, "
            "--patchset-comment, --change-message, or --file <PATH>."
        )

    # Automatically target the parent comment's patchset when replying,
    # as Gerrit requires replies to be on the same patchset as the parent comment.
    target_revision = args.revision
    if args.reply_to and parent_comment and parent_comment.get("patch_set"):
        if args.revision == "current":
            target_revision = str(parent_comment["patch_set"])

    # Dry-run execution
    if args.dry_run:
        print(f"[DRY-RUN] Target CL: {cl_id} on {host} (Revision: {target_revision})")
        print("[DRY-RUN] Review Payload:")
        print(json.dumps(payload, indent=2))
        return 0

    # Submit review
    print(f"Posting review to CL {cl_id} on {host} (Revision: {target_revision})...")
    try:
        post_review(host, cl_id, payload, revision=target_revision)
        resolution_str = "unresolved" if args.unresolved else "resolved"
        print(f"✅ Reply successfully posted ({resolution_str})!")
        return 0
    except Exception as e:
        print(f"❌ Error posting reply: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
