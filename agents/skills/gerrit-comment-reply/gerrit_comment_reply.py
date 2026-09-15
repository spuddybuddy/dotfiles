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


def create_draft(
    host: str,
    cl_id: str,
    comment_input: Dict[str, Any],
    revision: str = "current",
) -> Dict[str, Any]:
    """Create an unpublished draft comment on a revision via gerrit_client.py rawapi."""
    path = f"changes/{cl_id}/revisions/{revision}/drafts"
    raw_args = [
        "--path",
        path,
        "--method",
        "PUT",
        "--body",
        json.dumps(comment_input),
    ]
    res = call_gerrit_client(host, "rawapi", raw_args)
    if isinstance(res, dict):
        return res
    raise RuntimeError("No response returned from gerrit_client.py rawapi when creating draft.")


def publish_drafts(
    host: str,
    cl_id: str,
    message: Optional[str] = None,
    revision: str = "current",
) -> Dict[str, Any]:
    """Publish all draft comments on a change via gerrit_client.py rawapi."""
    payload: Dict[str, Any] = {"drafts": "PUBLISH_ALL_REVISIONS"}
    if message:
        payload["message"] = message.strip()
    return post_review(host, cl_id, payload, revision=revision)


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


def get_comment_thread_context(
    comments_dict: Dict[str, Any], comment_id: str
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Dict[str, Any]]:
    """Locate comment, its file path, and inherited thread context.

    Returns (target_file, parent_comment, context_dict).
    context_dict contains inherited 'line', 'range', 'side', and 'patch_set'.
    If the comment itself is missing line/range/side (e.g. it was an earlier reply),
    walks up the in_reply_to chain to find them from ancestor comments in the thread.
    """
    target_file, parent_comment = find_comment_by_id(comments_dict, comment_id)
    if not parent_comment or not target_file:
        return None, None, {}

    context: Dict[str, Any] = {}
    for key in ("line", "range", "side", "patch_set"):
        if key in parent_comment:
            context[key] = parent_comment[key]

    # If line, range, or side are missing, walk up the thread to find them from ancestors
    if not all(k in context for k in ("line", "range", "side")):
        file_comments = comments_dict.get(target_file, [])
        if isinstance(file_comments, list):
            by_id = {
                c.get("id"): c
                for c in file_comments
                if isinstance(c, dict) and c.get("id")
            }
            visited = {comment_id}
            curr_id = parent_comment.get("in_reply_to")
            while curr_id and curr_id in by_id and curr_id not in visited:
                visited.add(curr_id)
                ancestor = by_id[curr_id]
                for key in ("line", "range", "side", "patch_set"):
                    if key not in context and key in ancestor:
                        context[key] = ancestor[key]
                if all(k in context for k in ("line", "range", "side")):
                    break
                curr_id = ancestor.get("in_reply_to")

    return target_file, parent_comment, context


def build_comment_object(
    item: Dict[str, Any],
    comments_dict: Dict[str, Any],
    cl_id: str,
    default_unresolved: bool = False,
    default_done: bool = False,
    default_ack: bool = False,
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """Builds (target_file, comment_obj, context) from a comment specification dict.

    Raises ValueError if item is invalid or comment cannot be found.
    """
    reply_to = item.get("reply_to") or item.get("in_reply_to") or item.get("id")
    target_file = item.get("file") or item.get("path")
    is_patchset = bool(
        item.get("patchset_comment")
        or item.get("patchset_level")
        or target_file == "/PATCHSET_LEVEL"
    )

    # Determine message and unresolved status
    if item.get("done") or (default_done and not item.get("message") and not item.get("comment")):
        message = "Done"
        unresolved = False
    elif item.get("ack") or (default_ack and not item.get("message") and not item.get("comment")):
        message = "Ack"
        unresolved = False
    else:
        message = item.get("message") or item.get("comment") or ""
        unresolved = item.get("unresolved", default_unresolved)

    if not message and not is_patchset and not reply_to:
        raise ValueError(f"Comment message is required: {item}")

    context: Dict[str, Any] = {}

    if reply_to:
        found_file, parent_comment, context = get_comment_thread_context(
            comments_dict, reply_to
        )
        if not found_file:
            if target_file:
                found_file = target_file
            else:
                raise ValueError(
                    f"Comment ID '{reply_to}' not found on CL {cl_id}. "
                    "Run with --list to view valid comment IDs."
                )
        target_file = found_file

        comment_obj: Dict[str, Any] = {
            "in_reply_to": reply_to,
            "message": message.strip(),
            "unresolved": unresolved,
        }
        line = item.get("line", context.get("line"))
        if line is not None:
            comment_obj["line"] = line
        range_obj = item.get("range", context.get("range"))
        if range_obj is not None:
            comment_obj["range"] = range_obj
        side = item.get("side", context.get("side"))
        if side is not None:
            comment_obj["side"] = side

        return target_file, comment_obj, context

    elif is_patchset:
        target_file = "/PATCHSET_LEVEL"
        comment_obj = {
            "message": message.strip(),
            "unresolved": unresolved,
        }
        return target_file, comment_obj, {}

    elif target_file:
        comment_obj = {
            "message": message.strip(),
            "unresolved": unresolved,
        }
        if "line" in item:
            comment_obj["line"] = item["line"]
        if "range" in item:
            comment_obj["range"] = item["range"]
        if "side" in item:
            comment_obj["side"] = item["side"]
        return target_file, comment_obj, {}

    else:
        raise ValueError(
            f"Invalid comment specification (must provide 'reply_to', 'file', or 'patchset_comment'): {item}"
        )


def parse_batch_input(
    raw_data: Any,
) -> Tuple[Optional[str], List[Dict[str, Any]], Dict[str, Any]]:
    """Parse batch JSON input into (top_level_message, comment_items, extra_review_fields)."""
    top_message: Optional[str] = None
    items: List[Dict[str, Any]] = []
    extra_fields: Dict[str, Any] = {}

    if isinstance(raw_data, list):
        items = raw_data
    elif isinstance(raw_data, dict):
        if "message" in raw_data and isinstance(raw_data["message"], str):
            top_message = raw_data["message"]
        for key in ("tag", "notify", "labels", "drafts", "ready"):
            if key in raw_data:
                extra_fields[key] = raw_data[key]

        if "comments" in raw_data:
            comments_val = raw_data["comments"]
            if isinstance(comments_val, list):
                items = comments_val
            elif isinstance(comments_val, dict):
                for file_path, c_list in comments_val.items():
                    if isinstance(c_list, list):
                        for c in c_list:
                            if isinstance(c, dict):
                                c_copy = dict(c)
                                c_copy.setdefault("file", file_path)
                                items.append(c_copy)
                    elif isinstance(c_list, dict):
                        c_copy = dict(c_list)
                        c_copy.setdefault("file", file_path)
                        items.append(c_copy)
        elif "replies" in raw_data:
            replies_val = raw_data["replies"]
            if isinstance(replies_val, list):
                items = replies_val
            elif isinstance(replies_val, dict):
                for cid, val in replies_val.items():
                    if isinstance(val, str):
                        items.append({"reply_to": cid, "message": val})
                    elif isinstance(val, dict):
                        c_copy = dict(val)
                        c_copy.setdefault("reply_to", cid)
                        items.append(c_copy)
        else:
            if any(
                k in raw_data
                for k in ("reply_to", "in_reply_to", "patchset_comment", "file", "path")
            ):
                items = [raw_data]
            else:
                for k, v in raw_data.items():
                    if k in ("message", "tag", "notify", "labels", "drafts", "ready"):
                        continue
                    if isinstance(v, str):
                        items.append({"reply_to": k, "message": v})
                    elif isinstance(v, dict):
                        c_copy = dict(v)
                        c_copy.setdefault("reply_to", k)
                        items.append(c_copy)
    else:
        raise ValueError(
            f"Batch input must be a JSON array or object, got {type(raw_data).__name__}"
        )

    return top_message, items, extra_fields


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

  # Reply to a single comment thread and mark it resolved (default):
  python3 gerrit_comment_reply.py --reply-to 3e2bf9a2_ac21bfa4 -m "Done, updated as suggested."

  # Quick "Done" or "Ack" for a single thread:
  python3 gerrit_comment_reply.py --reply-to 3e2bf9a2_ac21bfa4 --done
  python3 gerrit_comment_reply.py --reply-to 3e2bf9a2_ac21bfa4 --ack

  # Batch reply to multiple threads with "Done" in a SINGLE review (one email, one UI update):
  python3 gerrit_comment_reply.py --batch-done 3e2bf9a2_ac21bfa4 db80ab0c_d81ad2bc

  # Batch reply from a JSON file:
  python3 gerrit_comment_reply.py --batch-file replies.json

  # Batch reply from a JSON file with a top-level review message:
  python3 gerrit_comment_reply.py --batch-file replies.json -m "Uploaded PS2 with fixes."

  # Batch reply to multiple threads with "Done" as unpublished drafts (DEFAULT):
  python3 gerrit_comment_reply.py --batch-done 3e2bf9a2_ac21bfa4 db80ab0c_d81ad2bc

  # Batch reply from a JSON file as unpublished drafts (DEFAULT):
  python3 gerrit_comment_reply.py --batch-file replies.json

  # Immediately publish batch replies in a review (bypassing draft mode):
  python3 gerrit_comment_reply.py --batch-done 3e2bf9a2_ac21bfa4 db80ab0c_d81ad2bc --publish

  # Publish all existing draft comments across the change:
  python3 gerrit_comment_reply.py --publish-drafts -m "Uploaded PS2 with fixes."

  # Reply to a single thread as an unpublished draft (DEFAULT):
  python3 gerrit_comment_reply.py --reply-to 3e2bf9a2_ac21bfa4 -m "Done, updated as suggested."

  # Preview draft creation without executing:
  python3 gerrit_comment_reply.py --batch-done 3e2bf9a2_ac21bfa4 db80ab0c_d81ad2bc --dry-run
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
        help="Reply message content or top-level review message.",
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
        "--batch-file",
        help="Path to a JSON file containing batch comments ('-' for stdin).",
    )
    parser.add_argument(
        "--batch-json",
        help="JSON string containing batch comments.",
    )
    parser.add_argument(
        "--batch-done",
        nargs="+",
        metavar="ID",
        help="Reply 'Done' and resolve multiple comment threads (saved as drafts by default).",
    )
    parser.add_argument(
        "--batch-ack",
        nargs="+",
        metavar="ID",
        help="Reply 'Ack' and resolve multiple comment threads (saved as drafts by default).",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Immediately publish review comments in a review instead of saving as drafts.",
    )
    parser.add_argument(
        "--draft",
        dest="publish",
        action="store_false",
        default=False,
        help="Post comments as unpublished drafts without sending emails (default behavior).",
    )
    parser.add_argument(
        "--publish-drafts",
        action="store_true",
        help="Publish all existing draft comments across revisions on the change.",
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

    # Action: Publish drafts
    if args.publish_drafts:
        target_revision = args.revision
        top_message = args.message
        if args.message_file:
            if args.message_file == "-":
                top_message = sys.stdin.read()
            else:
                with open(args.message_file, "r", encoding="utf-8") as f:
                    top_message = f.read()

        if args.dry_run:
            print(f"[DRY-RUN] Publish all drafts for CL {cl_id} on {host} (Revision: {target_revision})")
            if top_message:
                print(f"[DRY-RUN] Top-level review message: {top_message.strip()}")
            return 0

        print(f"Publishing all draft comments for CL {cl_id} on {host}...")
        try:
            publish_drafts(host, cl_id, message=top_message, revision=target_revision)
            print(f"✅ Successfully published all draft comments on CL {cl_id}!")
            return 0
        except Exception as e:
            print(f"❌ Error publishing drafts: {e}", file=sys.stderr)
            return 1

    # Action: List comments
    is_list_action = args.list or (
        not args.reply_to
        and not args.message
        and not args.message_file
        and not args.done
        and not args.ack
        and not args.patchset_comment
        and not args.change_message
        and not args.batch_file
        and not args.batch_json
        and not args.batch_done
        and not args.batch_ack
        and not args.file
    )

    if is_list_action:
        print(f"Fetching comments for CL {cl_id} from {host}...")
        try:
            comments = query_comments(host, cl_id)
            display = format_threads_display(comments, unresolved_only=args.unresolved_only)
            print(display)
            return 0
        except Exception as e:
            print(f"❌ Error fetching comments: {e}", file=sys.stderr)
            return 1

    # Collect batch items or single item
    batch_raw: Optional[Any] = None
    if args.batch_file:
        if args.batch_file == "-":
            batch_raw = json.load(sys.stdin)
        else:
            with open(args.batch_file, "r", encoding="utf-8") as f:
                batch_raw = json.load(f)
    elif args.batch_json:
        batch_raw = json.loads(args.batch_json)
    elif args.batch_done:
        batch_raw = [{"reply_to": cid, "done": True} for cid in args.batch_done]
    elif args.batch_ack:
        batch_raw = [{"reply_to": cid, "ack": True} for cid in args.batch_ack]

    top_message: Optional[str] = None
    items: List[Dict[str, Any]] = []
    extra_fields: Dict[str, Any] = {}

    if batch_raw is not None:
        try:
            top_message, items, extra_fields = parse_batch_input(batch_raw)
        except ValueError as err:
            print(f"❌ Error parsing batch input: {err}", file=sys.stderr)
            return 1

        cli_message: Optional[str] = None
        if args.message:
            cli_message = args.message
        elif args.message_file:
            if args.message_file == "-":
                cli_message = sys.stdin.read()
            else:
                with open(args.message_file, "r", encoding="utf-8") as f:
                    cli_message = f.read()
        if cli_message:
            top_message = cli_message
    else:
        # Determine single message content
        single_message = args.message
        if args.done:
            single_message = "Done"
        elif args.ack:
            single_message = "Ack"
        elif args.message_file:
            if args.message_file == "-":
                single_message = sys.stdin.read()
            else:
                with open(args.message_file, "r", encoding="utf-8") as f:
                    single_message = f.read()

        if args.change_message:
            if not single_message:
                parser.error("Message is required for --change-message.")
            top_message = single_message
        elif args.reply_to:
            if not single_message and not args.done and not args.ack:
                parser.error(
                    "Reply message is required (use -m, --message, --message-file, --done, or --ack)."
                )
            items = [{
                "reply_to": args.reply_to,
                "message": single_message,
                "unresolved": args.unresolved,
                "done": args.done,
                "ack": args.ack,
                "file": args.file,
            }]
        elif args.patchset_comment:
            if not single_message:
                parser.error("Message is required for --patchset-comment.")
            items = [{
                "patchset_comment": True,
                "message": single_message,
                "unresolved": args.unresolved,
            }]
        elif args.file:
            if not single_message:
                parser.error("Message is required for --file comment.")
            single_item: Dict[str, Any] = {
                "file": args.file,
                "message": single_message,
                "unresolved": args.unresolved,
            }
            if args.line is not None:
                single_item["line"] = args.line
            items = [single_item]
        else:
            parser.error(
                "Please specify a comment action: --reply-to <ID>, --batch-file <FILE>, "
                "--batch-json <JSON>, --batch-done <IDs...>, --batch-ack <IDs...>, "
                "--patchset-comment, --change-message, or --file <PATH>."
            )

    # Fetch published comments if needed to resolve thread contexts
    comments_dict: Dict[str, Any] = {}
    needs_comments = any(
        (it.get("reply_to") or it.get("in_reply_to") or it.get("id"))
        for it in items
    )
    if needs_comments:
        print(f"Fetching comments for CL {cl_id} from {host}...")
        try:
            comments_dict = query_comments(host, cl_id)
        except Exception as e:
            print(f"❌ Error fetching comments: {e}", file=sys.stderr)
            return 1

    # Construct review payload
    payload: Dict[str, Any] = {"drafts": "KEEP"}
    payload.update(extra_fields)
    if top_message:
        payload["message"] = top_message.strip()

    comments_map: Dict[str, List[Dict[str, Any]]] = {}
    all_contexts: List[Dict[str, Any]] = []
    draft_entries: List[Tuple[str, Dict[str, Any], str]] = []

    for item in items:
        try:
            tgt_file, c_obj, ctx = build_comment_object(
                item,
                comments_dict,
                cl_id,
                default_unresolved=args.unresolved,
                default_done=args.done,
                default_ack=args.ack,
            )
        except ValueError as err:
            print(f"❌ Error in comment: {err}", file=sys.stderr)
            return 1
        comments_map.setdefault(tgt_file, []).append(c_obj)
        all_contexts.append(ctx)

        # For draft comments, target the parent comment's patchset if available
        d_rev = str(ctx.get("patch_set")) if (args.revision == "current" and ctx.get("patch_set")) else args.revision
        draft_input = dict(c_obj)
        draft_input["path"] = tgt_file
        draft_entries.append((tgt_file, draft_input, d_rev))

    if comments_map:
        payload["comments"] = comments_map

    num_comments = sum(len(c_list) for c_list in comments_map.values())
    if not comments_map and not top_message:
        print("No comments or message to post.", file=sys.stderr)
        return 1

    # Determine target revision
    target_revision = args.revision
    if args.revision == "current":
        patchsets = {
            ctx.get("patch_set")
            for ctx in all_contexts
            if ctx.get("patch_set")
        }
        if len(patchsets) == 1:
            target_revision = str(next(iter(patchsets)))

    # Draft mode is the default for comments unless --publish is explicitly specified.
    # Note: If the user only specified a top-level change message (no inline/file comments),
    # it is published as a review since Gerrit does not support draft change messages.
    is_draft_mode = (not args.publish) and bool(draft_entries)

    if is_draft_mode:
        if args.dry_run:
            print(f"[DRY-RUN] Target CL: {cl_id} on {host}")
            print(f"[DRY-RUN] Would create {len(draft_entries)} draft comment(s) (UNPUBLISHED):")
            for tgt_file, d_input, rev in draft_entries:
                print(f"  - PUT changes/{cl_id}/revisions/{rev}/drafts:")
                print(json.dumps(d_input, indent=4))
            return 0

        print(f"Creating {len(draft_entries)} draft comment(s) on CL {cl_id} on {host}...")
        created = 0
        for tgt_file, d_input, rev in draft_entries:
            try:
                create_draft(host, cl_id, d_input, revision=rev)
                created += 1
                loc = f"{tgt_file}:{d_input.get('line', '')}" if d_input.get("line") else tgt_file
                print(f"  ✓ Draft created at {loc}")
            except Exception as e:
                print(f"❌ Error creating draft for {tgt_file}: {e}", file=sys.stderr)
                return 1

        print(f"✅ Successfully created {created} draft comment(s) on CL {cl_id}!")
        print("💡 These comments are saved as drafts. You can review and edit them in the Gerrit Web UI,")
        print("   and click 'Reply' / 'Send' to publish them when ready (or use --publish-drafts).")
        return 0

    # Dry-run execution
    if args.dry_run:
        print(f"[DRY-RUN] Target CL: {cl_id} on {host} (Revision: {target_revision})")
        print(
            f"[DRY-RUN] Review includes {num_comments} comment(s) and "
            f"{1 if top_message else 0} top-level message."
        )
        print("[DRY-RUN] Review Payload:")
        print(json.dumps(payload, indent=2))
        return 0

    # Submit review
    print(
        f"Posting review with {num_comments} comment(s) to CL {cl_id} on {host} "
        f"(Revision: {target_revision})..."
    )
    try:
        post_review(host, cl_id, payload, revision=target_revision)
        if num_comments > 0:
            print(f"✅ Successfully posted review ({num_comments} comment(s))!")
        else:
            print(f"✅ Successfully posted change message to CL {cl_id}!")
        return 0
    except Exception as e:
        print(f"❌ Error posting review: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())


