---
name: find-conversation
description: >-
  Find past Jetski conversations whose transcripts mention a string such as a
  Gerrit CL number, Buganizer/crbug issue, local branch name, or file name, then
  switch the user to the best match. Use when the user asks "which conversation
  was working on X", "find the chat about CL 123", "go back to the conversation
  for branch foo", or similar.
---

# Find Conversation

Searches every local Jetski conversation transcript, read-only, for one or more
identifiers, ranks the matches, and hands the user a link to switch to the
best match.

## When to activate

- The user wants to find or resume the conversation that worked on a CL, bug,
  branch, file, or other string.
- The user asks which agent or chat made a given change.

## Background

- Transcripts live at
  `~/.gemini/jetski/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`
  (truncated fields), with `transcript_full.jsonl` (untruncated) next to it.
- **The terminal sandbox only exposes the *current* conversation's brain
  directory.** Searching other conversations therefore needs
  `BypassSandbox: true`. The script is strictly read-only: it only reads
  transcript files and runs `git config --get`. Run the script by itself, with
  no chained commands, so the elevated command stays minimal.

## Workflow

### 1. Run the search script once

```bash
python3 ~/github/spuddybuddy/dotfiles/agents/skills/find-conversation/find_conversation.py \
  <QUERY> [<QUERY> ...] --repo <repo-root> --exclude <current-conversation-id>
```

- Run with `BypassSandbox: true`. If the output warns that only 1 or 2
  conversation directories were visible, the sandbox was still in effect.
- Always pass `--exclude <your own conversation ID>`; this conversation
  contains the query too.
- Pass `--repo` with the workspace root (e.g. `~/chrome/src`), so a branch
  name also expands to its Gerrit CL number (`branch.<name>.gerritissue`).
  Repeat `--repo` for multiple checkouts.
- Accepted query forms (several can be passed; results are OR-ed and ranked):
  - CL: `8804522`, `crrev.com/c/8804522`,
    `https://chromium-review.googlesource.com/c/chromium/src/+/8804522`
  - Bug: `b/572921901`, `crbug.com/572921901`,
    `issues.chromium.org/issues/572921901`
  - Branch: `webmcp-exploit-test-helpers`
  - Anything else is a case-insensitive literal (e.g. a file name or commit
    subject).
- Useful flags:
  - `--include-subagents`: also list subagent conversations (hidden by
    default; e.g. `/review-agent` runs).
  - `--full`: search the untruncated transcripts if nothing is found.
  - `--limit N` (default 10), `--json` for machine-readable output.

If the user gives a branch but you suspect the CL or bug is mentioned more
often, look up the CL with `git config branch.<name>.gerritissue` and the bug
from the commit message (`Bug:` / `Fixed:` lines in `git log -1 <branch>`), and
pass those as extra queries in the same invocation.

### 2. (Optional) Confirm the top match

If the top results are close in hit count, inspect the last few user requests
of the candidates to decide which one actually *worked on* the item, rather
than just mentioning it. Do this read-only, with `BypassSandbox: true`:

```bash
python3 -c "
import json
p='$HOME/.gemini/jetski/brain/<ID>/.system_generated/logs/transcript.jsonl'
us=[json.loads(l) for l in open(p) if '\"USER_INPUT\"' in l]
for o in us[-6:]: print(o['created_at'], (o.get('content') or '')[:300].replace(chr(10),' '))
"
```

`agentapi get-conversation-metadata <ID>` (also needs `BypassSandbox: true`)
returns the workspace, the branch the conversation was started on, and
`parentConversationId`.

### 3. Switch to the conversation

No API lets an agent change the user's active conversation, so give the user
a one-click way to switch:

1. A clickable conversation link (the UI renders it):
   `[<short id> – <topic>](conversation://<conversation-id>)`
2. Alternatives the user can run themselves:
   - Hub/IDE: Cmd/Ctrl+K conversation palette, and paste the ID.
   - Jetski CLI: `/resume` (alias `/switch`), or from a shell
     `jetski --conversation <conversation-id>`.

Present the result concisely:

- The best match as a `conversation://` link, with its active date range and a
  one-line summary of what it was doing (from its last user requests).
- Other matches (if any) in one short line each, noting whether they only
  mentioned the item in passing or were subagents.
- Don't paste the full script output unless the user asks for it.
