---
name: gerrit-comment-reply
description: >
  Query published Gerrit comments and post batch or single replies to comment threads, patchset-level comments, or review messages using depot_tools gerrit_client.py and vpython3.
---

# Gerrit Comment Reply

This skill enables agents and engineers to inspect published review comments on a Gerrit Change List (CL), trace comment threads, and post replies (marking threads resolved or unresolved) in batch or individually using `depot_tools`'s command-line tool `gerrit_client.py` and `vpython3`.

> [!IMPORTANT]
> **Draft Mode is the Default:**
> All comments and replies are created as **unpublished drafts** by default. No emails are sent and no public change history is updated until you either:
> 1. Review and click **"Send"** / **"Reply"** in the Gerrit Web UI, or
> 2. Run with `--publish-drafts` to publish all staged drafts from the CLI, or
> 3. Pass the `--publish` flag to publish immediately.

## When to activate

Activate this skill when the user:
- Asks to reply to, answer, or resolve review comments on a Gerrit CL (especially in batch).
- Wants to stage draft replies so they can review them in the Gerrit Web UI before publishing.
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

### 2. Batch Reply to Multiple Comments (Default: Drafts)

Replying in batch stages all comments as unpublished drafts without sending emails.

#### A. Quick "Done" or "Ack" for Multiple Threads

```bash
# Staged as drafts by default:
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --batch-done 3651ea3e_b9232d19 db80ab0c_d81ad2bc

python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --batch-ack 3651ea3e_b9232d19 db80ab0c_d81ad2bc

# Or publish immediately in a single review (bypassing draft mode):
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --batch-done 3651ea3e_b9232d19 db80ab0c_d81ad2bc \
  --publish
```

#### B. Batch Replies via JSON File

```bash
# Staged as drafts by default:
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --batch-file replies.json

# Or publish immediately with a top-level review message:
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --batch-file replies.json \
  -m "Uploaded patchset 2 addressing all review comments." \
  --publish
```

#### C. Batch Replies via Inline JSON String

```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --batch-json '[
    {"reply_to": "3651ea3e_b9232d19", "message": "Done, reverted year."},
    {"reply_to": "db80ab0c_d81ad2bc", "done": true}
  ]'
```

#### Supported Batch JSON Formats

**Format 1: Array of comment items:**
```json
[
  {
    "reply_to": "3651ea3e_b9232d19",
    "message": "Done, reverted copyright year to 2025.",
    "unresolved": false
  },
  {
    "reply_to": "db80ab0c_d81ad2bc",
    "done": true
  },
  {
    "reply_to": "b5385538_9a05c05c",
    "ack": true
  }
]
```

**Format 2: Object with top-level message and comments:**
```json
{
  "message": "Uploaded PS2 addressing review comments.",
  "comments": [
    {
      "reply_to": "3651ea3e_b9232d19",
      "message": "Done."
    }
  ]
}
```

**Format 3: Simple mapping of `{comment_id: message}`:**
```json
{
  "3651ea3e_b9232d19": "Done, updated.",
  "db80ab0c_d81ad2bc": "Ack"
}
```

> [!NOTE]
> Thread context (`line`, `range`, `side`) is automatically inherited from the parent comment or ancestor comments in the thread, ensuring replies attach directly to the comment thread at the line of code rather than appearing as file-level comments.

### 3. Reply to a Single Comment Thread (Default: Draft)

Reply to an individual comment thread by passing its comment ID (`--reply-to <ID>`):

```bash
# Reply as a draft (default):
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --cl 8358885 \
  --reply-to 3651ea3e_b9232d19 \
  -m "Done, reverted copyright year to 2025."

# Quick "Done" or "Ack" as a draft:
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py --reply-to 3651ea3e_b9232d19 --done
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py --reply-to 3651ea3e_b9232d19 --ack

# Publish immediately (bypassing draft mode):
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --reply-to 3651ea3e_b9232d19 \
  --done \
  --publish
```

### 4. Review and Publish Staged Drafts

Once comments are staged as drafts:
1. **In the Gerrit Web UI (Recommended):** Open the CL. All drafts will be displayed in place in yellow boxes. You can inspect or edit them, and click **"Send"** / **"Reply"** to publish them all together.
2. **Via CLI:** Publish all drafts across revisions with an optional top-level message:
   ```bash
   python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
     --publish-drafts \
     -m "Uploaded patchset 2 addressing all review feedback."
   ```

### 5. Post a Patchset-Level Comment

Post a comment to `/PATCHSET_LEVEL`:
```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --cl 8351276 \
  --patchset-comment \
  -m "Ran an led build to verify: https://ci.chromium.org/b/8671642108848646433"
```

### 6. Post a Top-Level Change Message

Post a top-level review message to the changelist (always published immediately as a review):
```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --cl 8351276 \
  --change-message \
  -m "PTAL, ready for review."
```

### 7. Dry Run Preview

Preview what drafts or reviews would be created without making any network calls:
```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-comment-reply/gerrit_comment_reply.py \
  --batch-done 3651ea3e_b9232d19 db80ab0c_d81ad2bc \
  --dry-run
```

## Command Line Options

- `--cl <CL_ID>`: Gerrit change number or Change-Id (defaults to detecting from current git branch).
- `--host <URL>`: Gerrit host URL (defaults to branch config or `https://chromium-review.googlesource.com`).
- `--revision <REV>`: Target revision ID or patchset number (default: `'current'`).
- `--list`: List all published comment threads on the change.
- `--unresolved-only`: Filter comment display to only unresolved threads.
- `--publish`: Immediately publish review comments instead of saving as drafts (bypasses draft mode).
- `--publish-drafts`: Publish all existing draft comments across revisions on the change.
- `--batch-done <ID> [<ID> ...]`: Reply "Done" and resolve multiple comment threads (saved as drafts by default).
- `--batch-ack <ID> [<ID> ...]`: Reply "Ack" and resolve multiple comment threads (saved as drafts by default).
- `--batch-file <FILE>`: Path to a JSON file containing batch comments (`'-'` for stdin).
- `--batch-json <JSON_STR>`: JSON string containing batch comments.
- `--reply-to <ID>`: ID of parent comment to reply to (automatically detects file and threads reply).
- `-m, --message <TEXT>`: Message body (or top-level review message when used with `--publish` or `--change-message`).
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

