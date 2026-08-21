---
name: owners-analyzer
description: >
  Analyze OWNERS files in a repository to find membership, other owners, and inclusion status of target OWNERS files (e.g. media/OWNERS).
---

# OWNERS Analyzer

This skill provides a tool to find, analyze, and categorize `OWNERS` files in a Chromium or Git repository where a specific developer is a member, and checks if a target `OWNERS` file (e.g. `media/OWNERS`) is also a member (either explicitly included or implicitly inherited).

## When to activate

Activate this skill when the user:
- Asks to find `OWNERS` files where they are a member but another group or file (like `media/OWNERS`) is not.
- Asks to count the number of other owners in their owned files.
- Needs to perform bulk analysis of `OWNERS` file permissions or inheritance hierarchies.

## Prerequisites & Tools Used

- **Python 3:** The script `owners_analyzer.py` is written in Python and requires no external dependencies beyond the Python Standard Library.
- **Git:** Utilizes `git config` and `git grep` for fast repository-level scanning and configuration auto-detection.

## Workflow

To run the analysis:

1. Locate the script: `owners_analyzer.py` inside this skill folder.
2. Run it using Python 3:
   ```bash
   python3 owners_analyzer.py [options]
   ```

### Command Line Options

- `--email <email>`: Specify the owner's email address to search for. If omitted, it will automatically query `git config user.email` in the repository.
- `--check-inclusion <path>`: Specify the relative path of the `OWNERS` file whose inclusion you want to verify (default: `media/OWNERS`).
- `--repo-root <path>`: Specify the path to the Git repository root (defaults to automatically detecting the git repository of the current working directory).
- `--output <path>`: Path to write a beautiful, formatted Markdown report. If omitted, the report is printed directly to standard output.

### Examples

- **Standard analysis for yourself checking `media/OWNERS` (output to stdout):**
  ```bash
  python3 owners_analyzer.py
  ```

- **Generate a report file for a specific email, checking `chromeos/printing/OWNERS`:**
  ```bash
  python3 owners_analyzer.py --email other_user@chromium.org --check-inclusion chromeos/printing/OWNERS --output /path/to/report.md
  ```
