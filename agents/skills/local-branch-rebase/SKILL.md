---
name: local-branch-rebase
description: >
  Rebase a local git branch onto a specified local upstream tracking branch (default: main, or lkgr or another local branch) and update tracking and Gerrit metadata in .git/config so depot_tools and git map-branches stay accurate.
---

# Local Branch Rebase

This skill rebases a local branch onto a specified local tracking branch (`main` by default, or `lkgr` or any other local branch such as a stacked parent CL branch) and synchronizes all branch tracking and Gerrit entries in `.git/config`.

## Why This Matters in Chromium / `depot_tools`

When branches are created with plain `git checkout -b <branch>` or rebased manually onto a different local branch (`main`, `lkgr`, or another local branch), `.git/config` drifts out of sync with `depot_tools`:
- `branch.<branch>.remote` may be unset instead of `.`
- `branch.<branch>.merge` and `branch.<branch>.base-upstream` may point to the wrong upstream (or be missing) instead of `refs/heads/<upstream>`
- `branch.<branch>.base` remains pinned to the stale pre-rebase upstream commit SHA instead of the new `git rev-parse refs/heads/<upstream>` commit SHA
- If `branch.<branch>.base` already recorded an earlier stacked parent branch commit, plain `git rebase <new_upstream>` can accidentally replay commits from the old parent branch instead of transplanting only `<base>..<branch>`
- Associated Gerrit CL keys (`gerritserver`, `gerritpatchset`, `gerritsquashhash`, `last-upload-hash`) may be out of date with Gerrit

## When to Activate

Activate this skill when the user:
- Asks to rebase a local branch or CL onto `main` (default), `lkgr`, or another local branch.
- Wants to reparent / unstack / move a local branch from one upstream branch to another local branch (`main`, `lkgr`, or a stacked parent branch).
- Asks to update or fix `.git/config` tracking/base/Gerrit hashes for a local branch after or alongside a rebase.

## Tool Location

[local_branch_rebase.py](file:///Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/local-branch-rebase/local_branch_rebase.py)

## Workflow

### 1. Rebase onto Default `main` (Current Branch)

When the user asks to rebase the current branch without specifying a different upstream branch, `main` is used by default:

```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/local-branch-rebase/local_branch_rebase.py
```

### 2. Rebase onto `lkgr` or Another Local Branch

Pass the target local upstream branch (`lkgr`, `main`, or another local branch name) either positionally or with `--upstream`:

```bash
# Rebase onto local lkgr:
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/local-branch-rebase/local_branch_rebase.py lkgr

# Rebase onto another local branch (e.g., stacking onto a parent CL branch):
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/local-branch-rebase/local_branch_rebase.py parent-feature-branch
```

### 3. Switch to a Specific Branch First, Then Rebase onto Upstream

If you are not currently on the target feature branch, pass `--branch <branch>` — the script automatically checks out `<branch>` first (ignoring dirty submodule pointers), rebases it onto `<upstream>`, and updates `.git/config`:

```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/local-branch-rebase/local_branch_rebase.py \
  --branch webmcp-executetool-domexceptions \
  --upstream main
```

### 4. Finish Updating `.git/config` After Resolving Rebase Conflicts

If a rebase stops with merge conflicts, resolve the conflicts, run `git rebase --continue`, and then run with `--update-config-only` to write the updated tracking and Gerrit keys into `.git/config`:

```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/local-branch-rebase/local_branch_rebase.py \
  --upstream main \
  --update-config-only
```

## What Steps and `.git/config` Entries Are Executed

Following the Chromium local branch tracking pattern:

1. **Checkout & Set Local Upstream Tracking**:
   ```bash
   git checkout <branch>
   git branch --set-upstream-to=<upstream> <branch>
   ```
   Sets `branch.<branch>.remote = .` and `branch.<branch>.merge = refs/heads/<upstream>`.

2. **Rebase onto `<upstream>`**:
   - Standard case: `git rebase <upstream>`
   - Unstacking from an unmerged parent feature branch (`branch.<branch>.base` not an ancestor of `<upstream>`): `git rebase --onto <upstream> <old_base> <branch>`

3. **Synchronize `.git/config` Entries (`[branch "<branch>"]`)**:
   - `branch.<branch>.remote` $\rightarrow$ `.`
   - `branch.<branch>.merge` $\rightarrow$ `refs/heads/<upstream>`
   - `branch.<branch>.base` $\rightarrow$ `$(git rev-parse <upstream>)`
   - `branch.<branch>.base-upstream` $\rightarrow$ `refs/heads/<upstream>`
   - If `branch.<branch>.gerritissue` exists:
     - Ensures `branch.<branch>.gerritserver` is set (`https://chromium-review.googlesource.com`).
     - Queries Gerrit (`vpython3 ~/depot_tools/gerrit_client.py rawapi --host <host> --path "changes/<cl>?o=CURRENT_REVISION"`) to keep `branch.<branch>.gerritpatchset` and `branch.<branch>.gerritsquashhash` synced with the CL's current server revision.
     - Preserves `branch.<branch>.last-upload-hash` and reports if local `HEAD` now differs so `git cl upload` can be run when ready.

4. **Verify Branch Hierarchy**:
   Runs `git map-branches` and prints the full before/after table of `branch.<branch>.*` config keys.

## Command Line Options

- `UPSTREAM` / `-u, --upstream <BRANCH>`: Local tracking branch to rebase onto (`main` by default; e.g. `main`, `lkgr`, or another local branch).
- `-b, --branch <BRANCH>`: Local branch to rebase (defaults to current checked-out branch; automatically checks out `<BRANCH>` if on another branch).
- `-C, --repo <PATH>`: Path to Git repository (default: `.`).
- `--old-base <COMMIT>`: Explicit old base commit for `git rebase --onto <upstream> <old-base> <branch>` (defaults to `branch.<branch>.base` if valid and an ancestor of `<branch>`).
- `--no-onto`: Run plain `git rebase refs/heads/<upstream>` without using `branch.<branch>.base` as `--onto`.
- `--update-config-only`: Only update `.git/config` tracking and Gerrit metadata without running `git rebase`.
- `--offline`: Skip querying Gerrit REST API for patchset/revision hashes.
- `--dry-run`: Preview planned rebase and `.git/config` changes without mutating git refs or config.
