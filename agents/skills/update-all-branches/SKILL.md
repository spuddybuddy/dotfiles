---
name: update-all-branches
description: >
  Update a git / Chromium checkout and all of its local branches: fetch and update main/lkgr
  (plus `gclient sync -D` in gclient checkouts) with arborist.py, delete local branches whose
  Gerrit CL is merged or abandoned, squash multi-commit branches, rebase every remaining branch
  onto its parent branch (or main), resolve merge conflicts, and verify each rebased branch.
---

# Update All Branches

Brings a whole checkout up to date in one session. The order of the steps matters, so follow
them in sequence:

1. Update the base branches (`main`, `lkgr`, …) and dependencies with `arborist.py -u`.
2. Capture a **plan** (parents, fork points, CL status) with `branch_plan.py` *before* changing
   any branch.
3. Delete branches whose CL is `MERGED` or `ABANDONED`.
4. For each remaining branch, parents first: squash it if it has 2+ commits, rebase it onto its
   parent (or `main` if the parent was deleted), resolve any conflicts, and verify it.
5. Restore the original branch and report.

## When to Activate

Activate when the user asks to update / refresh / sync their checkout and all local branches,
rebase all branches, clean up landed or abandoned CL branches, or "run arborist".

For rebasing a **single** branch, use the `local-branch-rebase` skill instead (this skill uses
it internally).

## Tools

| Tool | Purpose |
| :--- | :--- |
| [arborist.py](file:///Users/mfoltz/github/spuddybuddy/dotfiles/bin/arborist.py) | Fetches and updates base branches; runs `gclient sync -D` in gclient checkouts after `main` and `lkgr` are updated. |
| [branch_plan.py](file:///Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/update-all-branches/branch_plan.py) | Read-only. Lists local branches parents-first with parent, fork point, commits, Gerrit CL status and the planned action (`delete` / `rebase` / `skip`). |
| [local_branch_rebase.py](file:///Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills/local-branch-rebase/local_branch_rebase.py) | Rebases one branch onto a local upstream and syncs `.git/config` tracking and Gerrit keys (see the `local-branch-rebase` skill). |

Below, `$SKILLS` means `/Users/mfoltz/github/spuddybuddy/dotfiles/agents/skills`. Run every
command from the **root of the git repository** (for Chromium, the `src/` directory).

## Workflow

### 0. Preconditions

- `git status --porcelain --untracked-files=no --ignore-submodules=all` must be empty. If it is
  not, stop and ask the user whether to commit, stash, or abort. Never discard changes.
- No rebase can be in progress (`.git/rebase-merge` or `.git/rebase-apply`). If one is, ask the
  user how to proceed.
- Record the current branch as `ORIGINAL_BRANCH`.

### 1. Update base branches and dependencies

```bash
python3 /Users/mfoltz/github/spuddybuddy/dotfiles/bin/arborist.py -u
```

- In a Chromium checkout this fetches `main`/`lkgr` and then runs `gclient sync -D`, which can
  take many minutes. Run it in the background with a long timeout and wait for it to finish.
- If the repo has an `upstream` remote (a GitHub fork), arborist asks interactive questions.
  Ask the user for the answers, or answer the defaults (`Y`) by sending input to the task.
- If arborist fails (fetch error, `gclient sync` error), show the user the error and stop.

### 2. Capture the plan (before changing anything)

```bash
python3 $SKILLS/update-all-branches/branch_plan.py --output .git/update-all-branches-plan.json
```

Use this plan for the **whole session** and don't recompute it partway through.
Deleting or rewriting a parent branch changes the history the child branches are measured
against. So each branch's `fork_point` and `head` must come from this snapshot. Each entry
contains:

- `branch`, `parent`, `action` (`delete` | `rebase` | `skip`), `new_parent`
- `head`: the branch tip before any change
- `fork_point`: the commit the branch's own commits start from (`fork_point..head` are its commits)
- `commit_count`, `commits`, `gerritissue`, `cl_status`, `unuploaded_changes`, `notes`

Show the user the text summary (it is printed to stdout). Proceed without waiting for
confirmation, except in the cases listed in step 3.

If Gerrit could not be queried (the CL status is `?` / a "could not fetch status" note), treat
the branch as open: rebase it and never delete it.

### 3. Safety backups, then delete closed-CL branches

First, back up **every** branch in the plan so any branch can be recovered:

```bash
git update-ref refs/backup/update-all-branches/<branch> <head>   # for each plan entry
```

Then **always confirm with the user before deleting any branch**:

- List every entry with `action == "delete"`: branch name, CL number and status (`MERGED` /
  `ABANDONED`), CL subject, and any child branches that will be reparented onto `main`.
- Flag entries where `unuploaded_changes` is true: those local commits were never uploaded to
  the CL.
- Ask the user which of these branches to delete (all, none, or a subset). Wait for the answer;
  never delete a branch without explicit confirmation.

Delete only the confirmed branches:

- If the branch is currently checked out, `git checkout <default_base>` first.
- `git branch -D <branch>`

Child branches of a deleted branch already have `new_parent` set to `main` in the plan. If the
user chooses to **keep** a branch the plan marked for deletion, treat it as a normal `rebase`
entry onto its original `parent` (or `main` if that parent is deleted). Its children then keep
it as their `new_parent`, with the same `--old-base` fork points from the plan.

### 4. Squash, rebase, and verify each remaining branch (plan order)

Process the `action == "rebase"` entries **in plan order** (parents before children). For each
branch `B` with parent `P = new_parent`, `F = fork_point`, `OLD = head`:

#### 4a. Squash (only if `commit_count >= 2`)

```bash
git checkout B
git log --format='%B%n----' --reverse F..B   # read all commit messages
git reset --soft F
git commit -F <message-file>
```

Write the squashed message yourself (no interactive editor):
- Use the first commit's subject and body as the basis. Fold in any important details from the
  later commits, but leave out "fix typo", "address comments" and similar.
- Keep at most **one** `Change-Id:` footer. If the commits have one, keep the one that matches
  the CL. Never invent a new Change-Id. Keep the other footers (`Bug:`, `Fixed:`, etc.).
- The tree must not change: `git diff OLD B` must be empty after the squash.

#### 4b. Rebase

```bash
python3 $SKILLS/local-branch-rebase/local_branch_rebase.py --branch B --upstream P --old-base F
```

Always pass `--old-base F` from the plan. This transplants exactly `F..B` onto `P`, which is
correct even when `P` was squashed or rebased earlier in this session, or when the old parent
landed and was deleted.

#### 4c. Resolve conflicts (if the rebase stops)

1. List the conflicting files: `git diff --name-only --diff-filter=U`.
2. For each file, work out what each side intended:
   - this branch's change: `git show OLD -- <file>` or `git diff F OLD -- <file>`
   - upstream changes since the fork: `git log --oneline F..P -- <file>` and `git log -p F..P -- <file>`

   Then edit the file to keep **both** intents. Never just pick "ours" or "theirs" to make the
   conflict go away.
3. Make sure no conflict markers remain (`git diff --check`), then `git add <file>`.
4. `GIT_EDITOR=true git rebase --continue`, and repeat until the rebase finishes.
5. Finish syncing `.git/config`:
   ```bash
   python3 $SKILLS/local-branch-rebase/local_branch_rebase.py --branch B --upstream P --update-config-only
   ```
6. Record that `B` needed conflict resolution, and which files were involved, for the
   verification step and the final report.

**Hand off to the user** if you are stuck. Examples: you can't tell what the correct
resolution is, the code was substantially restructured or deleted upstream, a resolution fails
to compile and you can't fix it, or the same conflict keeps coming back. In that case:
- Leave the rebase in progress. Don't abort it and don't guess.
- Don't process any more branches (a rebase in progress blocks the repository).
- Tell the user which branch and files are affected, what you found out about each side, which
  branches are still pending, and how to resume. After `git rebase --continue`, run
  `local_branch_rebase.py ... --update-config-only`, then ask the agent to continue the
  remaining branches using the saved plan in `.git/update-all-branches-plan.json`.

#### 4d. Verify the rebased branch

Run these checks for every rebased branch:

1. **Patch preserved.** Compare the branch's change before and after:
   ```bash
   diff <(git diff F OLD) <(git diff P B)
   ```
   Differences should only be hunk offsets and context, plus the conflict resolutions you made.
   Anything else (a hunk lost or duplicated, or a parent's changes leaking into the child) is a
   bug: investigate, and fix it or restore from the backup ref.
2. **Clean commit structure.** `git log --oneline P..B` shows exactly one commit (or the
   original count if it was not squashed), and `git diff --check P B` reports no conflict
   markers or whitespace errors.
3. **Compile** (Chromium, when conflicts were resolved in `B` or upstream changed the same files
   since `F`). Compile only the touched source files in the user's build directory:
   ```bash
   autoninja -C out/release ../../path/to/file.cc^ ../../path/to/other.cc^
   ```
   Use `out/release` as the build directory by default, unless the user specifies another. If
   `out/release` does not exist, ask the user once which build directory to use, or whether to
   skip compiling. Fix
   compile errors you introduced while resolving conflicts (amend the commit, then run
   `--update-config-only` again). Hand off to the user if the errors are unrelated or you can't
   fix them.

### 5. Finish

1. Check out `ORIGINAL_BRANCH` if it still exists, otherwise the default base branch.
2. Show `git map-branches` (or `git branch -vv`).
3. Report a table with one row per branch: action taken (deleted / squashed / rebased /
   skipped / handed off), new parent, conflicts resolved, and verification results. Note
   branches whose HEAD now differs from `last-upload-hash`; the user may want to run
   `git cl upload` on them (don't upload automatically).
4. Tell the user how to recover or clean up the backups:
   ```bash
   git for-each-ref refs/backup/update-all-branches/                          # list
   git branch -f <branch> refs/backup/update-all-branches/<branch>             # restore one
   git for-each-ref --format='delete %(refname)' refs/backup/update-all-branches/ | git update-ref --stdin   # remove all
   ```
5. Delete `.git/update-all-branches-plan.json` once every branch has been processed.

## Rules

- Never push, upload (`git cl upload`), or land anything.
- Never delete a branch without the user's explicit confirmation in this session.
- Never delete a branch whose CL status is unknown or still open.
- Never use `git reset --hard`, `git checkout -- .`, or `git clean` on user work. The only
  reset allowed is `git reset --soft F` for squashing.
- Keep the backup refs until the user removes them.
