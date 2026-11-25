#!/usr/bin/env python3

import argparse
import subprocess
import sys
import os

class RunCommandError(Exception):
  """Exception raised when running a command."""
  pass


def run_command(command, cwd=None):
  """Runs a shell command, prints output, and returns True on success."""
  try:
    print(f"Running: {' '.join(command)}", flush=True)
    # Stream output in real-time
    with subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
      for line in proc.stdout:
        print(line, end='', flush=True)
        
      proc.wait()
      if proc.returncode != 0:
        raise RunCommandError(f"Error: Command failed with exit code {proc.returncode}: {' '.join(command)}")

  except RunCommandError:
    raise
  except FileNotFoundError as e:
    raise RunCommandError(f"Command not found: {command[0]}") from e
  except Exception as e:
    raise RunCommandError(f"An unexpected error occurred: {e}") from e


def is_working_tree_clean(cwd=None):
  """Checks if there are uncommitted (staged or unstaged) changes in the working tree."""
  result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, cwd=cwd)
  return result.returncode == 0 and not result.stdout.strip()


def is_valid_git_repo(cwd=None):
  """Checks if the directory is a valid git repository with at least one configured remote."""
  result = subprocess.run(['git', 'remote'], capture_output=True, text=True, cwd=cwd)
  return result.returncode == 0 and bool(result.stdout.strip())


def remote_branch_exists(branch, remote='origin', cwd=None):
  """Checks if a remote tracking branch exists."""
  result = subprocess.run(
      ['git', 'show-ref', '--verify', '--quiet', f'refs/remotes/{remote}/{branch}'],
      cwd=cwd)
  return result.returncode == 0


def has_upstream_remote(cwd=None):
  """Checks if a remote named 'upstream' is configured in the repository."""
  result = subprocess.run(['git', 'remote'], capture_output=True, text=True, cwd=cwd)
  return result.returncode == 0 and 'upstream' in result.stdout.split()


CANDIDATE_BASE_BRANCHES = ['main', 'master', 'lkgr', 'gh-pages']


def probe_remote_base_branches(remote, cwd=None):
  """Queries remote server for existing candidate base branches without downloading objects."""
  cmd = ['git', 'ls-remote', '--heads', remote] + CANDIDATE_BASE_BRANCHES
  result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
  if result.returncode != 0:
    return []
  found = []
  for line in result.stdout.splitlines():
    parts = line.strip().split()
    if len(parts) >= 2:
      ref = parts[1]  # e.g. refs/heads/main
      for branch in CANDIDATE_BASE_BRANCHES:
        if ref == f'refs/heads/{branch}':
          found.append(branch)
  return found


def optimized_fetch(remote, branches=None, cwd=None):
  """Fetches only target base branches with --no-tags and memory optimizations."""
  if branches is None:
    branches = probe_remote_base_branches(remote, cwd=cwd)

  fetch_cmd = [
      'git',
      '-c', 'core.deltaBaseCacheLimit=2g',
      'fetch',
      '--no-tags',
      '--no-recurse-submodules',
      remote,
  ]
  if branches:
    print(f"\n--- Fetching updates for {', '.join(branches)} from {remote} ---")
    fetch_cmd.extend([f'+refs/heads/{b}:refs/remotes/{remote}/{b}' for b in branches])
  else:
    print(f"\n--- Fetching updates from {remote} ---")

  run_command(fetch_cmd, cwd=cwd)
  return True


def get_current_branch(cwd=None):
  """Gets the current git branch name."""
  result = subprocess.run(['git', 'branch', '--show-current'], check=True, cwd=cwd, text=True, capture_output=True)
  return result.stdout.strip()


def branch_exists(branch_name, cwd=None):
  """Checks if a local git branch exists."""
  result = subprocess.run(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch_name}'], cwd=cwd)
  return result.returncode == 0


def ensure_base_branches(cwd=None):
  """Ensures local tracking branches exist and track origin for any candidate base branches."""
  for branch in CANDIDATE_BASE_BRANCHES:
    if not branch_exists(branch, cwd=cwd):
      if remote_branch_exists(branch, remote='origin', cwd=cwd):
        print(f"Creating local tracking branch '{branch}' tracking origin/{branch}...")
        try:
          run_command(['git', 'branch', '--track', branch, f'origin/{branch}'], cwd=cwd)
        except RunCommandError as e:
          print(f"Warning: Could not create local tracking branch '{branch}': {e}", file=sys.stderr)
      elif remote_branch_exists(branch, remote='upstream', cwd=cwd):
        print(f"Creating local branch '{branch}' from upstream/{branch}...")
        try:
          run_command(['git', 'branch', branch, f'upstream/{branch}'], cwd=cwd)
        except RunCommandError as e:
          print(f"Warning: Could not create local branch '{branch}': {e}", file=sys.stderr)
    elif has_upstream_remote(cwd=cwd) and remote_branch_exists(branch, remote='origin', cwd=cwd):
      # If branch exists but mistakenly tracks upstream instead of origin, correct it
      current_upstream = get_upstream_branch(branch, cwd=cwd)
      if current_upstream == f'upstream/{branch}':
        print(f"Correcting tracking remote for local branch '{branch}' to origin/{branch}...")
        try:
          run_command(['git', 'branch', '-u', f'origin/{branch}', branch], cwd=cwd)
        except RunCommandError as e:
          print(f"Warning: Could not update tracking remote for '{branch}': {e}", file=sys.stderr)


def update_branch(branch, remote='origin', cwd=None):
  print(f"\n--- Updating '{branch}' branch from {remote}/{branch} ---")
  ensure_base_branches(cwd=cwd)

  if get_current_branch(cwd=cwd) != branch:
    print(f"Checking out '{branch}'...")
    run_command(['git', 'checkout', branch], cwd=cwd)

  print(f"Rebasing '{branch}' with {remote}/{branch}...")
  run_command(['git', 'rebase', f'{remote}/{branch}'], cwd=cwd)


def get_upstream_branch(branch, cwd=None):
  """Gets the upstream tracking branch for a given local branch."""
  result = subprocess.run(['git', 'for-each-ref', '--format=%(upstream:short)', f'refs/heads/{branch}'], cwd=cwd, text=True, capture_output=True)
  return result.stdout.strip()


def get_git_dir(cwd=None):
  """Gets the absolute path to the .git directory (supports git worktrees)."""
  result = subprocess.run(['git', 'rev-parse', '--git-dir'], capture_output=True, text=True, cwd=cwd)
  if result.returncode == 0:
    git_dir = result.stdout.strip()
    if not os.path.isabs(git_dir):
      git_dir = os.path.join(cwd or os.getcwd(), git_dir)
    return git_dir
  return os.path.join(cwd or os.getcwd(), '.git')


def find_gclient_root(cwd=None):
  """Returns the directory containing a .gclient file at or above cwd, or None.

  A Chromium-style checkout managed by gclient has a .gclient file in a parent
  of the git repository root (e.g. ~/chromium/.gclient with the repo in ~/chromium/src).
  """
  path = os.path.abspath(cwd or os.getcwd())
  while True:
    if os.path.isfile(os.path.join(path, '.gclient')):
      return path
    parent = os.path.dirname(path)
    if parent == path:
      return None
    path = parent


def gclient_sync(cwd=None):
  """Checks out main and runs `gclient sync -D` so dependencies match the updated main."""
  print("\n--- Running gclient sync -D ---")
  if get_current_branch(cwd=cwd) != 'main':
    print("Checking out 'main' so dependencies are synced to the updated main...")
    run_command(['git', 'checkout', 'main'], cwd=cwd)
  run_command(['gclient', 'sync', '-D'], cwd=cwd)


def is_rebase_in_progress(cwd=None):
  git_dir = get_git_dir(cwd=cwd)
  rebase_merge = os.path.join(git_dir, 'rebase-merge')
  rebase_apply = os.path.join(git_dir, 'rebase-apply')
  return os.path.exists(rebase_merge) or os.path.exists(rebase_apply)

  
def update_base_branches(no_fetch=False, cwd=None):
  """Manages and updates base tracking branches (main, master, lkgr, gh-pages) from origin or upstream."""
  repo_dir = cwd or os.getcwd()
  print(f"Operating in: {repo_dir}")

  if not os.path.exists(os.path.join(repo_dir, '.git')):
    print("Error: No .git directory found. This script must be run from the root of a Git repository.", file=sys.stderr)
    return False

  if not is_valid_git_repo(cwd=repo_dir):
    print("Error: No git remotes configured for this repository.", file=sys.stderr)
    return False

  if not is_working_tree_clean(cwd=repo_dir):
    print("Error: Working tree has uncommitted changes. Please commit or stash them before updating branches.", file=sys.stderr)
    return False

  if is_rebase_in_progress(cwd=repo_dir):
    print("Warning: A git rebase is currently in progress. Skipping base branch update to avoid corrupting rebase state.", file=sys.stderr)
    return False

  target_remote = 'origin'
  if has_upstream_remote(cwd=repo_dir):
    print("\nDetected 'upstream' remote (fork repository).")
    ans = input("Do you want to fetch 'upstream' and rebase base branches (main/master/gh-pages) onto upstream? [Y/n]: ").strip().lower()
    if ans not in ['n', 'no']:
      target_remote = 'upstream'

  original_branch = get_current_branch(cwd=repo_dir)
  print(f"Original branch: {original_branch}")

  if not no_fetch:
    # Fetch updates from origin first to keep origin tracking refs fresh
    try:
      optimized_fetch('origin', cwd=repo_dir)
    except RunCommandError as e:
      print(f"Error fetching from origin: {e}", file=sys.stderr)
      return False

    if target_remote == 'upstream':
      try:
        optimized_fetch('upstream', cwd=repo_dir)
      except RunCommandError as e:
        print(f"Error fetching from upstream: {e}", file=sys.stderr)
        return False
  else:
    print("\nSkipping remote fetch (--no-fetch specified).")

  # Ensure local base branches exist and track origin
  ensure_base_branches(cwd=repo_dir)

  updated_any = False
  updated_branches = []
  for branch in CANDIDATE_BASE_BRANCHES:
    if remote_branch_exists(branch, remote=target_remote, cwd=repo_dir):
      update_branch(branch, remote=target_remote, cwd=repo_dir)
      updated_any = True
      updated_branches.append(branch)
      if target_remote == 'upstream':
        push_ans = input(f"Do you want to push updated '{branch}' to your repository (origin/{branch})? [Y/n]: ").strip().lower()
        if push_ans not in ['n', 'no']:
          try:
            run_command(['git', 'push', 'origin', branch], cwd=repo_dir)
          except RunCommandError:
            force_ans = input(f"Push of '{branch}' to origin was rejected (branches diverged). Force push with lease (--force-with-lease)? [y/N]: ").strip().lower()
            if force_ans in ['y', 'yes']:
              try:
                run_command(['git', 'push', '--force-with-lease', 'origin', branch], cwd=repo_dir)
              except RunCommandError as e:
                print(f"Force push to origin failed: {e}", file=sys.stderr)

  if not updated_any:
    print(f"Warning: None of the standard base branches ({', '.join(CANDIDATE_BASE_BRANCHES)}) were found on remote '{target_remote}'.", file=sys.stderr)

  # --- Sync gclient dependencies for Chromium-style checkouts ---
  if 'main' in updated_branches and 'lkgr' in updated_branches and find_gclient_root(cwd=repo_dir):
    if no_fetch:
      print("\nSkipping gclient sync (--no-fetch specified).")
    else:
      try:
        gclient_sync(cwd=repo_dir)
      except RunCommandError as e:
        print(f"Error: gclient sync failed: {e}", file=sys.stderr)
        return False

  # --- Restore original branch ---
  current_branch = get_current_branch(cwd=repo_dir)
  if original_branch and original_branch != current_branch and branch_exists(original_branch, cwd=repo_dir):
    print(f"\n--- Restoring original branch '{original_branch}' ---")
    run_command(['git', 'checkout', original_branch], cwd=repo_dir)
    print(f"Restored to branch '{original_branch}'.")

  print("\nBase branch update finished.")
  return True


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Arborist: Git branch management utility (GitHub & Git-on-Borg).")
  parser.add_argument('--update', '-u', action='store_true', help="Update base tracking branches (main, master, lkgr, gh-pages) from remote origin. In gclient (Chromium) checkouts, also runs `gclient sync -D` after main and lkgr are updated.")
  parser.add_argument('--no-fetch', '-n', action='store_true', help="Skip fetching remote updates (and gclient sync).")
  args = parser.parse_args()

  if not args.update:
    parser.print_help()
    sys.exit(1)

  if not os.path.exists('.git'):
    print("Error: No .git directory found. This script must be run from the root of a Git repository.", file=sys.stderr)
    sys.exit(1)

  if not is_valid_git_repo():
    print("Error: No git remotes configured for this repository.", file=sys.stderr)
    sys.exit(1)

  if not update_base_branches(no_fetch=args.no_fetch):
    sys.exit(1)
