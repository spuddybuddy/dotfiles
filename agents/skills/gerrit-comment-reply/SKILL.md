---
name: gerrit-comment-reply
description: >
  Query published Gerrit comments and post replies to comment threads, patchset-level comments, or review messages using depot_tools gerrit_client.py and vpython3.
---

# Gerrit Comment Reply

This skill enables agents and engineers to inspect published review comments on a Gerrit Change List (CL), trace comment threads, and post threaded or patchset-level replies (marking threads resolved or unresolved) using `depot_tools`'s command-line tool `gerrit_client.py` and `vpython3`.

## When to activate

Activate this skill when the user:
- Asks to reply to, answer, or resolve review comments on a Gerrit CL.
- Wants to list or inspect open/unresolved comments on a specific CL or branch.
- Asks to post a patchset-level comment or general review message to Gerrit.
- Needs to mark comment threads resolved ("Done" / "Ack") after uploading a patchset.

## Prerequisites & Tools Used

- **Depot Tools:** Requires `depot_tools` in `PATH` or standard locations (`~/depot_tools`, `/opt/depot_tools`) for `gerrit_client.py` and `vpython3`.
- **vpython3:** Manages authenticated HTTP sessions and token refresh automatically without requiring direct Python module imports.
- **Git Branch Metadata:** Automatically detects the CL number and Gerrit host from local git branch configuration (`branch.<name>.gerritissue` and `branch.<name>.gerritserver`).

## Tool Location

```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py [options]
```

## Core Workflows

### 1. Inspect / List Comments on a CL

View all comments on the current branch's CL:
```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py --list
```

View only unresolved comments on a specific CL:
```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py --cl 8358885 --list --unresolved-only
```

Each thread displays its location, resolution status (`🔴 UNRESOLVED` vs `🟢 RESOLVED`), author, patchset, timestamp, and unique comment ID (e.g. `[3651ea3e_b9232d19]`).

### 2. Reply to a Specific Comment Thread

Reply to a comment thread by passing its comment ID (`--reply-to <ID>`). The tool automatically matches the file path and threads the reply directly under the parent comment:

```bash
# Reply and mark thread resolved (default behavior):
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --cl 8358885 \
  --reply-to 3651ea3e_b9232d19 \
  -m "Done, reverted copyright year to 2025."

# Quick "Done" or "Ack":
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py --reply-to 3651ea3e_b9232d19 --done
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py --reply-to 3651ea3e_b9232d19 --ack

# Reply but leave thread marked as unresolved:
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --reply-to 3651ea3e_b9232d19 \
  -m "Investigating this now." \
  --unresolved
```

### 3. Post a Patchset-Level Comment

Post a comment to `/PATCHSET_LEVEL`:
```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --cl 8351276 \
  --patchset-comment \
  -m "Ran an led build to verify: https://ci.chromium.org/b/8671642108848646433"
```

### 4. Post a Top-Level Change Message

Post a top-level review message to the changelist:
```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --cl 8351276 \
  --change-message \
  -m "PTAL, ready for review."
```

### 5. Dry Run Preview

Verify the generated REST API JSON payload before submitting to Gerrit:
```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --cl 8358885 \
  --reply-to 3651ea3e_b9232d19 \
  -m "Done" \
  --dry-run
```

## Command Line Options

- `--cl <CL_ID>`: Gerrit change number or Change-Id (defaults to detecting from current git branch).
- `--host <URL>`: Gerrit host URL (defaults to branch config or `https://chromium-review.googlesource.com`).
- `--revision <REV>`: Target revision ID or patchset number (default: `'current'`).
- `--list`: List all published comment threads on the change.
- `--unresolved-only`: Filter comment display to only unresolved threads.
- `--reply-to <ID>`: ID of parent comment to reply to (automatically detects file and threads reply).
- `-m, --message <TEXT>`: Message body.
- `--message-file <FILE>`: File to read message from (`'-'` for stdin).
- `--done`: Shortcut for `-m "Done"` with resolved status.
- `--ack`: Shortcut for `-m "Ack"` with resolved status.
- `--resolved`: Mark comment thread as resolved (default).
- `--unresolved`: Keep comment thread as unresolved.
- `--patchset-comment`: Add a comment to `/PATCHSET_LEVEL`.
- `--change-message`: Post as a top-level review message on the change.
- `--file <PATH>`: File path for a new inline comment.
- `--line <NUM>`: Line number for a new inline comment.
- `--dry-run`: Print the API payload without executing the request.
