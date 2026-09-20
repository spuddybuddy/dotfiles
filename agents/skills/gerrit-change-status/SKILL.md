---
name: gerrit-change-status
description: >
  Query and summarize Gerrit CL review status, submit requirements, approvals, and unresolved comment threads across local repositories.
---

# Gerrit Change Status

This skill discovers open Gerrit changes associated with local git branches across one or more repositories, queries their current status via Gerrit REST APIs, and presents a clear summary table of review votes, submit requirements, unresolved comment threads, and recommended next steps.

## When to activate

Activate this skill when the user:
- Asks to review the status or submittability of open Gerrit CLs across their working directories.
- Asks to check for open or unresolved reviewer comments on their CLs.
- Needs an overview of who has reviewed or approved their CLs (`Code-Review+1`, `Code-Owners`, `CQ`).
- Wants to scan multiple checkouts (e.g. `~/openscreen`, `~/chrome/infra`) to see which CLs are ready to land.

## Prerequisites & Tools Used

- **Python 3:** Uses Python 3 (automatically uses Python 3.11+ or `vpython3` if available).
- **Depot Tools:** Integrates with `depot_tools` (`gerrit_util` / `gerrit_client.py`) for authenticated Gerrit REST API access.
- **Git:** Reads local repository branch metadata via `git config --get-regexp "^branch\..*\.gerritissue$"`.

## Workflow

### 1. Run the status tool

Run `gerrit_change_status.py` pointing to one or more repositories or parent directories containing git repositories:

```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/gerrit-change-status/gerrit_change_status.py ~/openscreen ~/openscreen2 ~/chrome/infra
```

### 2. Command Line Options

- `paths...`: Positional arguments for repository paths or parent directories to scan (defaults to current working directory `.`).
- `--cl <CL_ID>`: Inspect specific Gerrit change list number(s) directly (repeatable or comma-separated).
- `--delimiter <STRING>`: Delimiter string between the repository path and the branch name (default: `" : "`, e.g. `~/openscreen/openscreen : fix-recipes`).
- `--host <URL>`: Gerrit host (default: `https://chromium-review.googlesource.com`).
- `--format <markdown|text|json>`: Output format (default: `markdown`).
- `--output <FILE>`: Save generated report to a file instead of stdout.
- `--include-merged`: Include CLs that are already `MERGED` or `ABANDONED`.
- `--no-comments`: Skip comment fetching for faster queries when only checking approval status.

### 3. Delimiter Customization

By default, repository paths and branch names are joined with a delimiter (`" : "`) for clarity in tables and terminal outputs:

```text
~/chrome/infra/build : openscreen-gn-args-list
~/openscreen/openscreen : fix-recipes
```

To use a custom delimiter, pass `--delimiter`:

```bash
# Slash delimiter
python3 gerrit_change_status.py --delimiter " // " ~/openscreen

# Colon delimiter without padding
python3 gerrit_change_status.py --delimiter ":" ~/openscreen
```

### 4. Summarization Process & Output Structure

The output includes:
1. **Overall Summary Table**:
   - **CL**: Clickable link to the Gerrit change (`https://crrev.com/c/<id>`).
   - **Repository : Branch**: Repository path and local branch name joined by the configured delimiter.
   - **Subject**: CL title / commit subject.
   - **CR Votes**: Formatted `Code-Review` votes and reviewer names.
   - **Submittable?**: `YES` or `NO` badge based on Gerrit submit requirements and submittability rules.
   - **Status / Next Step**: Concise actionable advice (e.g., ready to land on CQ, missing review, or unresolved comments).

2. **Unresolved Comments Section**:
   - Lists any open unresolved comment threads, including location (`file:line`), reviewer, and comment snippet.

3. **Submittability & Next Steps Breakdown**:
   - Detailed per-project or per-topic walkthrough of required actions to unblock landing.
