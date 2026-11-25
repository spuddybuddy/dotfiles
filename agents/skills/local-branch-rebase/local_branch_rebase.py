#!/usr/bin/env python3
"""Rebase a local Git branch onto a local tracking branch and sync .git/config."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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
DEFAULT_UPSTREAM = "main"

TRACKING_CONFIG_KEYS = [
    "remote",
    "merge",
    "base",
    "base-upstream",
]

GERRIT_CONFIG_KEYS = [
    "gerritissue",
    "gerritserver",
    "gerritpatchset",
    "gerritsquashhash",
    "last-upload-hash",
]

ALL_REPORTED_KEYS = TRACKING_CONFIG_KEYS + GERRIT_CONFIG_KEYS


@dataclass
class BranchConfigSnapshot:
    values: Dict[str, Optional[str]] = field(default_factory=dict)

    def get(self, key: str) -> Optional[str]:
        return self.values.get(key)


@dataclass
class RebaseResult:
    repo_root: str
    branch: str
    upstream: str
    switched_from: Optional[str]
    old_head: str
    new_head: str
    upstream_sha: str
    used_onto_base: Optional[str]
    before_config: BranchConfigSnapshot
    after_config: BranchConfigSnapshot
    gerrit_synced: bool = False
    gerrit_sync_note: Optional[str] = None
    dry_run: bool = False
    map_branches_output: Optional[str] = None


def normalize_host(host: str) -> str:
    """Ensure host has https:// scheme and no trailing slash."""
    host = host.strip()
    if not host.startswith("http://") and not host.startswith("https://"):
        host = f"https://{host}"
    return host.rstrip("/")


def normalize_local_branch(name: str) -> str:
    """Normalize 'refs/heads/foo' or 'foo' to the bare local branch name 'foo'."""
    name = name.strip()
    if name.startswith("refs/heads/"):
        return name[len("refs/heads/") :]
    return name


def run_git(
    args: List[str],
    cwd: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a git subcommand and return the CompletedProcess."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=check,
    )


def get_repo_root(cwd: str) -> str:
    res = run_git(["rev-parse", "--show-toplevel"], cwd=cwd, check=False)
    if res.returncode != 0:
        raise RuntimeError(f"Not inside a git repository: {cwd}")
    return res.stdout.strip()


def get_current_branch(repo_root: str) -> Optional[str]:
    res = run_git(["symbolic-ref", "--short", "-q", "HEAD"], cwd=repo_root, check=False)
    if res.returncode != 0:
        return None
    branch = res.stdout.strip()
    return branch or None


def local_branch_exists(repo_root: str, branch: str) -> bool:
    res = run_git(
        ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=repo_root,
        check=False,
    )
    return res.returncode == 0


def rev_parse(repo_root: str, rev: str) -> Optional[str]:
    res = run_git(["rev-parse", "--verify", f"{rev}^{{commit}}"], cwd=repo_root, check=False)
    if res.returncode != 0:
        return None
    return res.stdout.strip()


def is_ancestor(repo_root: str, ancestor: str, descendant: str) -> bool:
    res = run_git(
        ["merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        check=False,
    )
    return res.returncode == 0


def has_uncommitted_tracked_changes(repo_root: str) -> List[str]:
    """Check tracked working-tree/index changes, ignoring dirty submodules."""
    res = run_git(
        [
            "status",
            "--porcelain",
            "--untracked-files=no",
            "--ignore-submodules=all",
        ],
        cwd=repo_root,
        check=True,
    )
    return [line for line in res.stdout.splitlines() if line.strip()]


def is_rebase_in_progress(repo_root: str) -> bool:
    git_dir_res = run_git(["rev-parse", "--git-dir"], cwd=repo_root, check=True)
    git_dir = git_dir_res.stdout.strip()
    if not os.path.isabs(git_dir):
        git_dir = os.path.join(repo_root, git_dir)
    return os.path.isdir(os.path.join(git_dir, "rebase-merge")) or os.path.isdir(
        os.path.join(git_dir, "rebase-apply")
    )


def get_branch_config_value(repo_root: str, branch: str, key: str) -> Optional[str]:
    res = run_git(
        ["config", "--get", f"branch.{branch}.{key}"],
        cwd=repo_root,
        check=False,
    )
    if res.returncode != 0:
        return None
    return res.stdout.strip()


def set_branch_config_value(repo_root: str, branch: str, key: str, value: str) -> None:
    run_git(["config", f"branch.{branch}.{key}", value], cwd=repo_root, check=True)


def read_branch_config_snapshot(repo_root: str, branch: str) -> BranchConfigSnapshot:
    snapshot = BranchConfigSnapshot()
    for key in ALL_REPORTED_KEYS:
        snapshot.values[key] = get_branch_config_value(repo_root, branch, key)
    return snapshot


def query_gerrit_current_revision(
    host: str, cl_number: str
) -> Tuple[Optional[int], Optional[str]]:
    """Query Gerrit for the latest patchset number and revision SHA of a CL."""
    gerrit_client = shutil.which("gerrit_client.py")
    if not gerrit_client and DEPOT_TOOLS_DIR:
        candidate = os.path.join(DEPOT_TOOLS_DIR, "gerrit_client.py")
        if os.path.isfile(candidate):
            gerrit_client = candidate
    if not gerrit_client:
        return None, None

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
            "rawapi",
            "--host",
            host,
            f"--json_file={tmp_json}",
            "--path",
            f"changes/{cl_number}?o=CURRENT_REVISION",
        ]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if res.returncode != 0 or not os.path.exists(tmp_json) or os.path.getsize(tmp_json) == 0:
            return None, None
        with open(tmp_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        change = data[0] if isinstance(data, list) and data else data
        if isinstance(change, dict):
            curr_rev = change.get("current_revision")
            revisions = change.get("revisions", {})
            if curr_rev and isinstance(revisions, dict) and curr_rev in revisions:
                ps_num = revisions[curr_rev].get("_number")
                if ps_num is not None:
                    return int(ps_num), str(curr_rev)
    finally:
        if os.path.exists(tmp_json):
            try:
                os.remove(tmp_json)
            except OSError:
                pass
    return None, None


def run_map_branches(repo_root: str) -> Optional[str]:
    """Run git map-branches if depot_tools provides it."""
    env = os.environ.copy()
    if DEPOT_TOOLS_DIR and DEPOT_TOOLS_DIR not in env.get("PATH", ""):
        env["PATH"] = f"{DEPOT_TOOLS_DIR}:{env.get('PATH', '')}"
    res = subprocess.run(
        ["git", "map-branches"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=False,
    )
    if res.returncode != 0:
        return None
    return res.stdout.rstrip()


def rebase_and_update_branch(
    cwd: str = ".",
    branch: Optional[str] = None,
    upstream: str = DEFAULT_UPSTREAM,
    old_base: Optional[str] = None,
    use_config_onto: bool = True,
    update_config_only: bool = False,
    offline: bool = False,
    dry_run: bool = False,
) -> RebaseResult:
    """Rebase local `branch` onto local `upstream` and update .git/config."""
    repo_root = get_repo_root(cwd)

    if is_rebase_in_progress(repo_root) and not update_config_only:
        raise RuntimeError(
            "A git rebase is already in progress in this repository. "
            "Finish or abort it first (`git rebase --continue` or `git rebase --abort`), "
            "or run with `--update-config-only` after resolving conflicts."
        )

    current_branch = get_current_branch(repo_root)
    target_branch = normalize_local_branch(branch) if branch else current_branch
    if not target_branch:
        raise RuntimeError(
            "HEAD is currently detached; pass `--branch <local-branch>` explicitly."
        )

    target_upstream = normalize_local_branch(upstream)
    if target_branch == target_upstream:
        raise RuntimeError(
            f"Source branch '{target_branch}' and upstream branch '{target_upstream}' cannot be the same."
        )

    if not local_branch_exists(repo_root, target_branch):
        raise RuntimeError(f"Local branch '{target_branch}' does not exist in {repo_root}.")
    if not local_branch_exists(repo_root, target_upstream):
        raise RuntimeError(
            f"Local upstream branch '{target_upstream}' does not exist in {repo_root}. "
            f"(Expected refs/heads/{target_upstream}.)"
        )

    if not update_config_only:
        dirty = has_uncommitted_tracked_changes(repo_root)
        if dirty:
            preview = "\n  ".join(dirty[:10])
            raise RuntimeError(
                f"Working tree has uncommitted tracked changes (commit or stash first):\n  {preview}"
            )

    before_config = read_branch_config_snapshot(repo_root, target_branch)
    old_head = rev_parse(repo_root, f"refs/heads/{target_branch}") or ""
    upstream_sha = rev_parse(repo_root, f"refs/heads/{target_upstream}") or ""

    # Determine whether an explicit or stacked non-ancestor old base should be passed to --onto
    resolved_onto_base: Optional[str] = None
    if old_base:
        parsed_old = rev_parse(repo_root, old_base)
        if not parsed_old:
            raise RuntimeError(f"Could not resolve `--old-base` commit: {old_base}")
        if is_ancestor(repo_root, parsed_old, f"refs/heads/{target_branch}"):
            resolved_onto_base = parsed_old
    elif use_config_onto:
        cfg_base = before_config.get("base")
        if cfg_base:
            parsed_cfg_base = rev_parse(repo_root, cfg_base)
            # Only use `--onto <upstream> <cfg_base>` automatically when unstacking from
            # a parent commit that is NOT already an ancestor of `<upstream>`. When
            # `<cfg_base>` is already an ancestor of `<upstream>` (e.g. rebasing along
            # `main` or `lkgr`), plain `git rebase <upstream>` is used directly.
            if (
                parsed_cfg_base
                and is_ancestor(repo_root, parsed_cfg_base, f"refs/heads/{target_branch}")
                and not is_ancestor(
                    repo_root, parsed_cfg_base, f"refs/heads/{target_upstream}"
                )
            ):
                resolved_onto_base = parsed_cfg_base

    switched_from: Optional[str] = None
    if current_branch != target_branch:
        switched_from = current_branch or "(detached HEAD)"

    planned_config = BranchConfigSnapshot(values=dict(before_config.values))
    planned_config.values["remote"] = "."
    planned_config.values["merge"] = f"refs/heads/{target_upstream}"
    planned_config.values["base"] = upstream_sha
    planned_config.values["base-upstream"] = f"refs/heads/{target_upstream}"

    cl_issue = before_config.get("gerritissue")
    gerrit_synced = False
    gerrit_sync_note: Optional[str] = None
    if cl_issue:
        host = normalize_host(before_config.get("gerritserver") or DEFAULT_HOST)
        planned_config.values["gerritserver"] = host
        if not offline:
            ps_num, ps_sha = query_gerrit_current_revision(host, cl_issue)
            if ps_num is not None and ps_sha:
                planned_config.values["gerritpatchset"] = str(ps_num)
                planned_config.values["gerritsquashhash"] = ps_sha
                gerrit_synced = True
                gerrit_sync_note = (
                    f"Synced CL {cl_issue} patchset {ps_num} ({ps_sha[:12]}) from Gerrit"
                )
            else:
                gerrit_sync_note = (
                    f"Preserved existing Gerrit config for CL {cl_issue} "
                    f"(could not query remote revision)"
                )
        else:
            gerrit_sync_note = (
                f"Preserved existing Gerrit config for CL {cl_issue} (`--offline`)"
            )

    if dry_run:
        return RebaseResult(
            repo_root=repo_root,
            branch=target_branch,
            upstream=target_upstream,
            switched_from=switched_from,
            old_head=old_head,
            new_head="(dry-run: unchanged)",
            upstream_sha=upstream_sha,
            used_onto_base=resolved_onto_base,
            before_config=before_config,
            after_config=planned_config,
            gerrit_synced=gerrit_synced,
            gerrit_sync_note=gerrit_sync_note,
            dry_run=True,
            map_branches_output=None,
        )

    if current_branch != target_branch:
        checkout_res = run_git(["checkout", target_branch], cwd=repo_root, check=False)
        if checkout_res.returncode != 0:
            err = checkout_res.stderr.strip() or checkout_res.stdout.strip()
            raise RuntimeError(f"Failed to switch to branch '{target_branch}': {err}")

    # Set upstream tracking before rebasing (`remote = .`, `merge = refs/heads/<upstream>`),
    # matching: `git branch --set-upstream-to=<upstream>`
    set_upstream_res = run_git(
        ["branch", f"--set-upstream-to={target_upstream}", target_branch],
        cwd=repo_root,
        check=False,
    )
    if set_upstream_res.returncode != 0:
        err = set_upstream_res.stderr.strip() or set_upstream_res.stdout.strip()
        raise RuntimeError(
            f"Failed to set upstream of '{target_branch}' to '{target_upstream}': {err}"
        )

    if not update_config_only:
        if resolved_onto_base:
            rebase_cmd = [
                "rebase",
                "--onto",
                target_upstream,
                resolved_onto_base,
                target_branch,
            ]
        else:
            rebase_cmd = ["rebase", target_upstream]

        rebase_res = run_git(rebase_cmd, cwd=repo_root, check=False)
        if rebase_res.returncode != 0:
            conflicts_res = run_git(
                ["diff", "--name-only", "--diff-filter=U"], cwd=repo_root, check=False
            )
            conflicts = [
                c.strip() for c in conflicts_res.stdout.splitlines() if c.strip()
            ]
            conflict_list = (
                "\n  - " + "\n  - ".join(conflicts)
                if conflicts
                else "\n  " + (rebase_res.stderr.strip() or rebase_res.stdout.strip())
            )
            script_path = os.path.abspath(__file__)
            raise RuntimeError(
                f"Rebase of '{target_branch}' onto '{target_upstream}' stopped due to conflicts:"
                f"{conflict_list}\n\n"
                f"After resolving conflicts and running `git rebase --continue`, finish updating `.git/config` with:\n"
                f"  python3 {script_path} --branch {target_branch} --upstream {target_upstream} --update-config-only"
            )

    # Write all updated branch tracking and Gerrit config fields into .git/config
    for key in ALL_REPORTED_KEYS:
        val = planned_config.get(key)
        if val is not None:
            set_branch_config_value(repo_root, target_branch, key, val)

    after_config = read_branch_config_snapshot(repo_root, target_branch)
    new_head = rev_parse(repo_root, f"refs/heads/{target_branch}") or ""
    map_out = run_map_branches(repo_root)

    return RebaseResult(
        repo_root=repo_root,
        branch=target_branch,
        upstream=target_upstream,
        switched_from=switched_from,
        old_head=old_head,
        new_head=new_head,
        upstream_sha=upstream_sha,
        used_onto_base=resolved_onto_base,
        before_config=before_config,
        after_config=after_config,
        gerrit_synced=gerrit_synced,
        gerrit_sync_note=gerrit_sync_note,
        dry_run=False,
        map_branches_output=map_out,
    )


def format_result_markdown(result: RebaseResult) -> str:
    mode_prefix = "[DRY RUN] " if result.dry_run else ""
    lines = [
        f"## {mode_prefix}Rebased `{result.branch}` onto `{result.upstream}`",
        "",
        f"- **Repository**: `{result.repo_root}`",
        f"- **Branch**: `{result.branch}`"
        + (
            f" (switched from `{result.switched_from}`)"
            if result.switched_from
            else " (already checked out)"
        ),
        f"- **New Upstream Tracking Branch**: `{result.upstream}` (`refs/heads/{result.upstream}` @ `{result.upstream_sha[:12]}`)",
        f"- **HEAD**: `{result.old_head[:12]}` -> `{result.new_head[:12] if not result.dry_run else result.new_head}`",
    ]
    if result.used_onto_base:
        lines.append(
            f"- **Transplanted Commits From Base**: `{result.used_onto_base[:12]}..{result.old_head[:12]}`"
        )
    if result.gerrit_sync_note:
        lines.append(f"- **Gerrit Metadata**: {result.gerrit_sync_note}")

    last_upload = result.after_config.get("last-upload-hash")
    if last_upload and not result.dry_run and last_upload != result.new_head:
        lines.append(
            f"- **Upload Status**: Local `HEAD` (`{result.new_head[:12]}`) differs from `last-upload-hash` (`{last_upload[:12]}`) — run `git cl upload` when ready to publish the rebased patchset."
        )

    lines.extend(
        [
            "",
            "### `.git/config` Entries (`[branch \"" + result.branch + "\"]`)",
            "",
            "| Config Key | Previous Value | Updated Value |",
            "| :--- | :--- | :--- |",
        ]
    )

    for key in ALL_REPORTED_KEYS:
        before_val = result.before_config.get(key)
        after_val = result.after_config.get(key)
        if before_val is None and after_val is None:
            continue
        b_disp = f"`{before_val}`" if before_val is not None else "*(unset)*"
        a_disp = f"`{after_val}`" if after_val is not None else "*(unset)*"
        lines.append(f"| `branch.{result.branch}.{key}` | {b_disp} | {a_disp} |")

    if result.map_branches_output:
        lines.extend(
            [
                "",
                "### `git map-branches`",
                "",
                "```text",
                result.map_branches_output,
                "```",
            ]
        )

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rebase a local Git branch onto a local tracking branch (default: main, "
            "or lkgr / another local branch) and update depot_tools & Gerrit keys in .git/config."
        )
    )
    parser.add_argument(
        "upstream_pos",
        nargs="?",
        default=None,
        metavar="UPSTREAM",
        help="New local upstream branch to rebase onto and track (default: main, or e.g. lkgr or another local branch).",
    )
    parser.add_argument(
        "-u",
        "--upstream",
        dest="upstream_flag",
        default=None,
        help="New local upstream branch to rebase onto and track (default: main).",
    )
    parser.add_argument(
        "-b",
        "--branch",
        default=None,
        help="Local branch to rebase (default: current checked-out branch). Automatically switches to it if needed.",
    )
    parser.add_argument(
        "-C",
        "--repo",
        default=".",
        help="Path to the Git repository (default: current directory).",
    )
    parser.add_argument(
        "--old-base",
        default=None,
        help="Explicit old base commit/ref for `git rebase --onto <upstream> <old-base> <branch>`.",
    )
    parser.add_argument(
        "--no-onto",
        action="store_true",
        help="Do not automatically use `branch.<branch>.base` as `--onto` cut point; run plain `git rebase <upstream>`.",
    )
    parser.add_argument(
        "--update-config-only",
        action="store_true",
        help="Only update `.git/config` tracking and Gerrit metadata without running `git rebase`.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip querying Gerrit for updated patchset/revision hashes (preserves existing Gerrit entries).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned rebase and `.git/config` updates without making changes.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    upstream = args.upstream_flag or args.upstream_pos or DEFAULT_UPSTREAM

    try:
        result = rebase_and_update_branch(
            cwd=args.repo,
            branch=args.branch,
            upstream=upstream,
            old_base=args.old_base,
            use_config_onto=not args.no_onto,
            update_config_only=args.update_config_only,
            offline=args.offline,
            dry_run=args.dry_run,
        )
        print(format_result_markdown(result))
        return 0
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
