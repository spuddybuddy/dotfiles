---
name: gerrit
description: >-
  Interact with Gerrit Code Review. View CL diffs, metadata, comments,
  post review comments, manage draft comments (list, view, update, delete),
  search for changes, manage reviewers/CCs, list or vote on labels,
  abandon, and submit changes.
  Use when working with Gerrit-hosted code reviews (Android, Chromium,
  Fuchsia, etc.) or whenever the user provides a Gerrit review URL (matching
  https://*-review.git.corp.google.com/* or https://*-review.googlesource.com/*)
  rather than Critique/Piper CLs or web browsing tools.
---

# Gerrit

Interact with Gerrit using the `gerrit` CLI. View full diffs, CL metadata,
comments, list files, search changes, manage reviewers, and post review
comments.

> [!IMPORTANT]
>
> **MANDATORY: Multi-Host Context** Unlike Critique, which is a central system,
> **Gerrit has multiple hosts**. To list, query, or interact with an issue or
> CL, you *must* know and provide the correct `--host` parameter. If the user
> request does not specify a host URL and you cannot determine it from the local
> git repository's remote origin URL, **you MUST STOP and ask the user for the
> correct Gerrit host URL before running any commands.** Do NOT attempt to run
> any `gerrit` commands without the `--host` flag.

> [!TIP]
>
> **Handling 404 (Not Found) Errors**: If a `gerrit` command fails with a 404
> Not Found error for a change on a public host (e.g.,
> `https://android-review.googlesource.com`), the change may reside on its
> internal/googleplex counterpart (e.g.,
> `https://googleplex-android-review.googlesource.com`). Check the Common Gerrit
> Hosts table and try querying the internal mirror before concluding the change
> does not exist.

## Identifying metadata

If inside a git repo:

*   Identify the host: Use `git --no-pager config --get remote.origin.url` as
    `host`.
*   Identify the change: Use `git --no-pager log -n1` and use the `Change-ID`
    tag in the commit message as `change`.

## CLI Usage

Prefer using the pre-built binary (available on all gLinux machines):

```bash
GERRIT=/google/bin/releases/gemini-agents-gerrit/gerrit
```

Alternatively, install via apt:

```bash
sudo glinux-add-repo -b gemini-agents-gerrit stable
sudo apt update && sudo apt install -y gemini-agents-gerrit
```

If you modify the CLI source code, build from source:

```bash
blaze build //learning/gemini/agents/clis/gerrit:gerrit
GERRIT=blaze-bin/learning/gemini/agents/clis/gerrit/gerrit
```

### View CL metadata

```bash
$GERRIT info --change=12345 --host=https://android-review.googlesource.com
```

> [!NOTE]
>
> When asked to show CL metadata or change info, execute `$GERRIT info` once
> and report the basic metadata directly to the user. Do NOT run `diff` or other
> commands when basic metadata is requested.

### View CL diff

```bash
$GERRIT diff --change=12345 --host=https://android-review.googlesource.com

# For a specific revision/patchset
$GERRIT diff --change=12345 --revision=2 --host=https://android-review.googlesource.com
```

> [!NOTE]
>
> When asked to show the code diff or commit message for a change, execute
> `$GERRIT diff` once. The command outputs the full unified diff and displays
> the commit message at the very top under `/COMMIT_MSG`. Report the relevant
> sections directly to the user without running additional inspection commands.

### List files in a change

```bash
$GERRIT files --change=12345 --host=https://android-review.googlesource.com
```

### View raw file content (Full Context)

```bash
$GERRIT cat --change=12345 --file="path/to/file.go" --host=https://android-review.googlesource.com
```

> [!NOTE] Returns the complete raw contents of the remote file. It automatically
> detects and avoids printing raw binary bytes to standard output.

### Fetch static analysis findings for a Gerrit change

Fetch static analysis findings (e.g. Lint, AyeAye) for a Gerrit change. By
default, only actionable findings for the latest patchset are shown.

-   `--change`: The numeric change ID or the full Change-Id string.
-   `--host`: The Gerrit host URL.
-   `--all`: (Optional) Include non-actionable findings.
-   `--patchset`: (Optional) Filter by a specific patchset number.

Example:

```bash
$GERRIT findings --change=12345 --host=https://android-review.googlesource.com
# For a specific patchset
$GERRIT findings --change=12345 --patchset=2 --host=https://android-review.googlesource.com
```

> [!NOTE]
>
> This command fetches actionable findings from the internal Findings API. It is
> useful for identifying lint errors or automated check failures associated with
> the change. When asked to show static analysis findings, execute
> `$GERRIT findings` once and report the results directly to the user without
> running additional file inspection commands.

### View all comments

```bash
$GERRIT comments list --change=12345 --host=https://android-review.googlesource.com
```

> [!NOTE]
>
> Output iterates flat components grouped by file paths sorted by line numbers,
> but natively indents descendants to render threaded conversation hierarchies
> recursively. When asked to show all comments on a change, execute `$GERRIT
> comments list` once and present the conversation threads directly to the user
> without running additional file inspection commands.

### Post a draft comment

```bash
$GERRIT comments post \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --file=path/to/file.py \
  --line=10 \
  --message="Consider refactoring this block"

# Ranged inline comment (spans specific characters)
$GERRIT comments post \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --file=path/to/file.py \
  --start-line=10 --start-char=5 \
  --end-line=15 --end-char=10 \
  --message="Consider refactoring this block"
```

NOTE: This will post a *draft* comment to the CL. It will not be visible to
other users until it is published.

### Reply to a comment

```bash
$GERRIT comments reply \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --comment-id=a1b2c3d4 \
  --message="Done."

# Reply and mark thread as resolved
$GERRIT comments reply \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --comment-id=a1b2c3d4 \
  --message="Fixed." \
  --resolve

# Reply and mark thread as unresolved
$GERRIT comments reply \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --comment-id=a1b2c3d4 \
  --message="Fixed." \
  --resolve=false
```

NOTE: This will post a *draft* reply to the CL. It will not be visible to other
users until it is published.

### Publish comments

```bash
$GERRIT comments publish --change=12345 --host=https://android-review.googlesource.com

# Publish and add a review message
$GERRIT comments publish \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --message="Looks good to me!" \
  --notify=true

# Publish comments and add a Code-Review +1 label
$GERRIT comments publish \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --message="LGTM" \
  --lgtm

# Publish comments and add a Code-Review -1 label if there's a major issue
$GERRIT comments publish \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --message="There are major issues." \
  --reject
```

> [!CAUTION]
>
> This is a write action which MUST be explicitly authorized by the user before
> execution.

### List draft comments

```bash
$GERRIT comments list --change=12345 --host=https://android-review.googlesource.com --drafts
```

> [!NOTE]
>
> Use the `--drafts` flag to list your unpublished draft comments instead of
> published comments. Draft comment IDs from this output can be used with the
> `get`, `update`, and `delete` commands below.

### View a draft comment

```bash
$GERRIT comments get \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --comment-id=<draft_id>

# For a specific revision
$GERRIT comments get \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --comment-id=<draft_id> \
  --revision=3
```

### Update a draft comment

```bash
$GERRIT comments update \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --comment-id=<draft_id> \
  --message="Updated comment text"
```

> [!NOTE]
>
> This is a write action which MUST be explicitly authorized by the user before
> execution.

### Delete a draft comment

```bash
$GERRIT comments delete \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --comment-id=<draft_id>

# For a specific revision
$GERRIT comments delete \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --comment-id=<draft_id> \
  --revision=3
```

> [!CAUTION]
>
> This is a destructive write action which MUST be explicitly authorized by the
> user before execution.

### List change messages

```bash
$GERRIT messages list --change=12345 --host=https://android-review.googlesource.com

# Filter by author
$GERRIT messages list --change=12345 --user=Prow_Bot_V2 --host=https://android-review.googlesource.com
```

### Post a change message

```bash
$GERRIT messages post --change=12345 --message="Great work!" --host=https://android-review.googlesource.com
```

### Manage Reviewers and CCs

```bash
$GERRIT reviewers add \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --reviewer=user1,user2 \
  --cc=user3 \
  --mdb=group1

# Add reviewers and mark a WIP/draft change as ready for review
$GERRIT reviewers add \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --reviewer=user1 \
  --ready

# Mark a change as ready for review without adding reviewers
$GERRIT reviewers add \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --ready

$GERRIT reviewers remove \
  --change=12345 \
  --host=https://android-review.googlesource.com \
  --reviewer=user1
```

## Reference Material

For more detailed information and advanced topics, refer to the following
reference files:

- **Common Gerrit Hosts**: [hosts.md](references/hosts.md) - A lookup table of
  common Gerrit host URLs (internal and external).
-   **Advanced CLI Operations**: [advanced_cli.md](references/advanced_cli.md) -
    Instructions and syntax for:
    - Managing the Attention Set (`$GERRIT attention`)
    - Querying and searching for CLs (`$GERRIT search`)
    -   Interacting with CRUAS AI-assisted code reviews (`$GERRIT review`,
        `$GERRIT conversations`, `$GERRIT capabilities`)
    - Managing labels and voting on changes (`$GERRIT labels`, `$GERRIT vote`)
    -   Submitting and abandoning CLs (`$GERRIT submit`, `$GERRIT abandon`)

## Reporting Issues

Report bugs or improvements for this skill at
[Agent Skill: gerrit](http://b/hotlists/8077994). See the `skill_issue` skill
for instructions on filing and triaging skill bugs.
