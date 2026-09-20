#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
import os

STATE_FILE = '.git/arborist_state.json'

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


def run_interactive_command(command, cwd=None):
  """Runs an interactive command attached directly to standard I/O (e.g. editor)."""
  try:
    print(f"Running: {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=cwd)
    if result.returncode != 0:
      raise RunCommandError(f"Error: Command failed with exit code {result.returncode}: {' '.join(command)}")
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


def get_base_branches(cwd=None):
  """Returns existing base/trunk branches (main, master, lkgr, gh-pages) in this repository."""
  return [
      b for b in CANDIDATE_BASE_BRANCHES
      if remote_branch_exists(b, remote='origin', cwd=cwd)
      or remote_branch_exists(b, remote='upstream', cwd=cwd)
      or branch_exists(b, cwd=cwd)
  ]

    
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


def get_local_branches(cwd=None):
  """Gets a list of all local git branches."""
  result = subprocess.run(['git', 'for-each-ref', '--format=%(refname:short)', 'refs/heads/'], check=True, cwd=cwd, text=True, capture_output=True)
  return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def get_upstream_branch(branch, cwd=None):
  """Gets the upstream tracking branch for a given local branch."""
  result = subprocess.run(['git', 'for-each-ref', '--format=%(upstream:short)', f'refs/heads/{branch}'], cwd=cwd, text=True, capture_output=True)
  return result.stdout.strip()


def get_commits_since_fork_point(branch, fork_point, cwd=None):
  """Gets a list of commits unique to the branch (fork_point..branch)."""
  result = subprocess.run(['git', 'log', '--oneline', f'{fork_point}..{branch}'], capture_output=True, text=True, cwd=cwd)
  if result.returncode != 0:
    return []
  return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def get_fork_point(branch, upstream, cwd=None):
  """Computes the merge-base between upstream and branch."""
  res = subprocess.run(['git', 'merge-base', upstream, branch], capture_output=True, text=True, cwd=cwd)
  if res.returncode == 0:
    return res.stdout.strip()
  return None


def is_valid_commit(commit_hash, cwd=None):
  """Verifies whether a commit hash exists in the git repository."""
  if not commit_hash:
    return False
  res = subprocess.run(['git', 'cat-file', '-e', f'{commit_hash}^{{commit}}'], capture_output=True, cwd=cwd)
  return res.returncode == 0


def sort_branches_topologically(branches, cwd=None):
  """Sorts branches so that upstream/parent branches come before downstream branches."""
  branch_set = set(branches)
  parents = {}
  for b in branches:
    upstream = get_upstream_branch(b, cwd=cwd)
    if upstream in branch_set:
      parents[b] = upstream
    else:
      parents[b] = None

  sorted_branches = []
  visited = set()
  visiting = set()

  def visit(node):
    if node in visiting:
      # Cycle detected, avoid infinite loop
      return
    if node in visited:
      return
    visiting.add(node)
    parent = parents.get(node)
    if parent and parent in branch_set:
      visit(parent)
    visiting.remove(node)
    visited.add(node)
    sorted_branches.append(node)

  for b in branches:
    if b not in visited:
      visit(b)

  return sorted_branches


def squash_branch_commits(branch, fork_point, cwd=None):
  """Squashes all commits on branch unique to fork_point into a single commit."""
  current_branch = get_current_branch(cwd=cwd)
  if current_branch != branch:
    print(f"Error: Cannot squash branch '{branch}' because current branch is '{current_branch}'.", file=sys.stderr)
    return False

  orig_commit_res = subprocess.run(['git', 'rev-parse', branch], capture_output=True, text=True, cwd=cwd)
  if orig_commit_res.returncode != 0:
    print(f"Error: Could not resolve branch '{branch}' commit hash.", file=sys.stderr)
    return False
  orig_commit = orig_commit_res.stdout.strip()

  # 1. Get the combined commit messages
  result = subprocess.run(['git', 'log', '--format=%B', '--reverse', f'{fork_point}..{branch}'], capture_output=True, text=True, cwd=cwd)
  if result.returncode != 0:
    print(f"Error: Failed to get commit messages for '{branch}'.", file=sys.stderr)
    return False

  commit_messages = result.stdout.strip()
  
  # 2. Soft reset to fork point
  try:
    run_command(['git', 'reset', '--soft', fork_point], cwd=cwd)
  except RunCommandError as e:
    print(f"Error during soft reset: {e}", file=sys.stderr)
    return False

  # 3. Write combined messages to a temp file
  git_dir = get_git_dir(cwd=cwd)
  msg_file = os.path.join(git_dir, 'arborist_squash_msg')
  try:
    with open(msg_file, 'w') as f:
      f.write(commit_messages)
  except Exception as e:
    print(f"Error writing temporary commit message file: {e}", file=sys.stderr)
    print("Restoring branch to original state...")
    subprocess.run(['git', 'reset', '--hard', orig_commit], cwd=cwd)
    return False

  # 4. Commit using interactive command so terminal editor opens properly
  try:
    run_interactive_command(['git', 'commit', '-F', msg_file, '-e'], cwd=cwd)
    print(f"Successfully squashed commits on '{branch}'.")
    success = True
  except RunCommandError:
    print(f"Squash commit aborted or failed. Restoring branch '{branch}' to original state...", file=sys.stderr)
    subprocess.run(['git', 'reset', '--hard', orig_commit], cwd=cwd)
    success = False
  finally:
    if os.path.exists(msg_file):
      try:
        os.remove(msg_file)
      except Exception:
        pass

  return success


def get_git_dir(cwd=None):
  """Gets the absolute path to the .git directory (supports git worktrees)."""
  result = subprocess.run(['git', 'rev-parse', '--git-dir'], capture_output=True, text=True, cwd=cwd)
  if result.returncode == 0:
    git_dir = result.stdout.strip()
    if not os.path.isabs(git_dir):
      git_dir = os.path.join(cwd or os.getcwd(), git_dir)
    return git_dir
  return os.path.join(cwd or os.getcwd(), '.git')


def get_state_file_path(cwd=None):
  return os.path.join(get_git_dir(cwd=cwd), 'arborist_state.json')


def load_state(cwd=None):
  state_path = get_state_file_path(cwd=cwd)
  if os.path.exists(state_path):
    try:
      with open(state_path, 'r') as f:
        return json.load(f)
    except Exception as e:
      print(f"Warning: Failed to load state file: {e}", file=sys.stderr)
  return None


def save_state(state, cwd=None):
  state_path = get_state_file_path(cwd=cwd)
  try:
    with open(state_path, 'w') as f:
      json.dump(state, f, indent=2)
  except Exception as e:
    print(f"Error saving state file: {e}", file=sys.stderr)


def clear_state(cwd=None):
  state_path = get_state_file_path(cwd=cwd)
  if os.path.exists(state_path):
    try:
      os.remove(state_path)
    except Exception as e:
      print(f"Error: Failed to remove state file: {e}", file=sys.stderr)


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
  for branch in CANDIDATE_BASE_BRANCHES:
    if remote_branch_exists(branch, remote=target_remote, cwd=repo_dir):
      update_branch(branch, remote=target_remote, cwd=repo_dir)
      updated_any = True
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

  # --- Restore original branch ---
  current_branch = get_current_branch(cwd=repo_dir)
  if original_branch and original_branch != current_branch and branch_exists(original_branch, cwd=repo_dir):
    print(f"\n--- Restoring original branch '{original_branch}' ---")
    run_command(['git', 'checkout', original_branch], cwd=repo_dir)
    print(f"Restored to branch '{original_branch}'.")

  print("\nBase branch update finished.")
  return True


def rebase_local_branches(no_fetch=False, cwd=None):
  """Mode to rebase existing local branches on their upstreams."""
  cwd = cwd or os.getcwd()
  print(f"Operating in: {cwd}")

  if not os.path.exists(os.path.join(cwd, '.git')):
    print("Error: No .git directory found. This script must be run from the root of a Git repository.", file=sys.stderr)
    return

  if not is_valid_git_repo(cwd=cwd):
    print("Error: No git remotes configured for this repository.", file=sys.stderr)
    return

  state = load_state(cwd=cwd)
  if state:
    print("\nFound saved rebase state from a previous run.")
    ans = input("Do you want to resume the previous rebase session? [Y/n/abort]: ").strip().lower()
    if ans in ['n', 'no', 'abort']:
      if is_rebase_in_progress(cwd=cwd):
        print("A git rebase is currently in progress.")
        abort_ans = input("Do you want to `git rebase --abort`? [Y/n]: ").strip().lower()
        if abort_ans not in ['n', 'no']:
          run_command(['git', 'rebase', '--abort'], cwd=cwd)
      clear_state(cwd=cwd)
      print("Cleared saved rebase state.")
      if ans == 'abort':
        return
      state = None
    else:
      # Resuming previous session
      rebasing_branch = state.get('current_rebasing_branch')
      if rebasing_branch and is_rebase_in_progress(cwd=cwd):
        print(f"\nA git rebase is currently in progress for branch '{rebasing_branch}'.")
        print("If you have resolved the merge conflicts, we can continue the rebase.")
        cont_ans = input("Run `git rebase --continue` now? [Y/n]: ").strip().lower()
        if cont_ans not in ['n', 'no']:
          try:
            run_command(['git', 'rebase', '--continue'], cwd=cwd)
            print(f"Successfully rebased '{rebasing_branch}'.")
            state['current_rebasing_branch'] = None
            if state['pending_branches'] and state['pending_branches'][0] == rebasing_branch:
              state['pending_branches'].pop(0)
            save_state(state, cwd=cwd)
          except RunCommandError:
            print(f"\n`git rebase --continue` stopped (conflicts may still be unresolved).")
            print("Please resolve the conflicts, and then run this script again to resume.")
            sys.exit(1)
        else:
          print("Exiting so you can resolve conflicts manually. Run the script again to resume.")
          sys.exit(0)
      elif rebasing_branch:
        print(f"\nGit rebase is no longer in progress for '{rebasing_branch}'. Assuming it was completed manually.")
        state['current_rebasing_branch'] = None
        if state['pending_branches'] and state['pending_branches'][0] == rebasing_branch:
          state['pending_branches'].pop(0)
        save_state(state, cwd=cwd)

  if state is None:
    # Check for clean working tree before starting a fresh session
    if not is_working_tree_clean(cwd=cwd):
      print("Error: Working tree has uncommitted changes. Please commit or stash them before rebasing branches.", file=sys.stderr)
      return

    # Check for upstream fork sync before starting rebase
    if has_upstream_remote(cwd=cwd):
      print("\nDetected 'upstream' remote (fork repository).")
      sync_ans = input("Do you want to sync local base branches (main/master/gh-pages) with 'upstream' before rebasing local branches? [Y/n]: ").strip().lower()
      if sync_ans not in ['n', 'no']:
        if not update_base_branches(no_fetch=no_fetch, cwd=cwd):
          print("Base branch update aborted or encountered an error. Stopping rebase session.", file=sys.stderr)
          return

    # Starting a fresh rebase session
    original_branch = get_current_branch(cwd=cwd)

    # 1. Print a map of existing branches (using git map-branches if available, else git branch -vv)
    print("\n--- 1. Branch Map ---")
    try:
      run_command(['git', 'map-branches'], cwd=cwd)
    except RunCommandError:
      try:
        run_command(['git', 'branch', '-vv'], cwd=cwd)
      except RunCommandError as e:
        print(f"Warning: Failed to list branches: {e}", file=sys.stderr)

    # Initialize state for steps 2 and 3
    ensure_base_branches(cwd=cwd)
    all_branches = get_local_branches(cwd=cwd)
    base_branches = get_base_branches(cwd=cwd)
    filtered_branches = [b for b in all_branches if b not in base_branches]
    pending_branches = sort_branches_topologically(filtered_branches, cwd=cwd)
    
    fork_points = {}
    for b in pending_branches:
      upstream = get_upstream_branch(b, cwd=cwd)
      if upstream:
        fp = get_fork_point(b, upstream, cwd=cwd)
        if fp:
          fork_points[b] = fp

    state = {
      'original_branch': original_branch,
      'pending_branches': pending_branches,
      'fork_points': fork_points,
      'squashing_completed': False,
      'current_rebasing_branch': None
    }
    save_state(state, cwd=cwd)

  # --- Phase 1: Squashing ---
  if not state.get('squashing_completed'):
    print("\n--- 2. Squashing Local Branches ---")
    for branch in list(state['pending_branches']):
      upstream_branch = get_upstream_branch(branch, cwd=cwd)
      if not upstream_branch:
        continue

      # Dynamically retrieve or validate fork point
      fork_point = state['fork_points'].get(branch)
      if not is_valid_commit(fork_point, cwd=cwd):
        fork_point = get_fork_point(branch, upstream_branch, cwd=cwd)
        if fork_point:
          state['fork_points'][branch] = fork_point
          save_state(state, cwd=cwd)

      if not fork_point:
        continue

      commits = get_commits_since_fork_point(branch, fork_point, cwd=cwd)
      if len(commits) >= 2:
        print(f"\nChecking out '{branch}'...")
        try:
          run_command(['git', 'checkout', branch], cwd=cwd)
        except RunCommandError as e:
          print(f"Error checking out branch '{branch}': {e}", file=sys.stderr)
          continue

        print(f"\nCommits unique to '{branch}' relative to '{upstream_branch}':")
        for commit in commits:
          print(f"  {commit}")
        
        squash_ans = input(f"This branch has {len(commits)} commits. Do you want to squash them into a single commit? [y/N]: ").strip().lower()
        if squash_ans in ['y', 'yes']:
          squash_branch_commits(branch, fork_point, cwd=cwd)

    state['squashing_completed'] = True
    save_state(state, cwd=cwd)

  # --- Phase 2: Rebasing ---
  print("\n--- 3. Rebasing Local Branches ---")
  while state['pending_branches']:
    branch = state['pending_branches'][0]
    upstream_branch = get_upstream_branch(branch, cwd=cwd)

    # Dynamic fork point fallback
    fork_point = state['fork_points'].get(branch)
    if not is_valid_commit(fork_point, cwd=cwd) and upstream_branch:
      fork_point = get_fork_point(branch, upstream_branch, cwd=cwd)
      if fork_point:
        state['fork_points'][branch] = fork_point
        save_state(state, cwd=cwd)

    if not upstream_branch or not fork_point:
      print(f"\nBranch '{branch}' has no upstream or fork point configured. Skipping.")
      state['pending_branches'].pop(0)
      save_state(state, cwd=cwd)
      continue

    ans = input(f"\nDo you want to rebase '{branch}' onto its upstream '{upstream_branch}'? [Y/n]: ").strip().lower()
    if ans in ['n', 'no']:
      print(f"Skipping '{branch}'.")
      state['pending_branches'].pop(0)
      save_state(state, cwd=cwd)
      continue

    print(f"\nRebasing '{branch}' onto '{upstream_branch}'...")
    state['current_rebasing_branch'] = branch
    save_state(state, cwd=cwd)

    try:
      run_command(['git', 'rebase', '--onto', upstream_branch, fork_point, branch], cwd=cwd)
    except RunCommandError:
      print(f"\nRebase of '{branch}' stopped (likely due to merge conflicts or error).")
      print("Please resolve the conflicts, and then run this script again to resume.")
      sys.exit(1)

    print(f"Successfully rebased '{branch}'.")
    state['current_rebasing_branch'] = None
    state['pending_branches'].pop(0)
    save_state(state, cwd=cwd)

  print("\nAll local branches have been processed.")
  original_branch = state.get('original_branch')
  current_branch = get_current_branch(cwd=cwd)
  if original_branch and original_branch != current_branch and branch_exists(original_branch, cwd=cwd):
    print(f"\n--- Restoring original branch '{original_branch}' ---")
    run_command(['git', 'checkout', original_branch], cwd=cwd)
    print(f"Restored to branch '{original_branch}'.")

  clear_state(cwd=cwd)
  print("\nRebase process finished.")


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Arborist: Git branch management utility (GitHub & Git-on-Borg).")
  parser.add_argument('--update', '-u', action='store_true', help="Update base tracking branches (main, master, lkgr, gh-pages) from remote origin.")
  parser.add_argument('--rebase', '-r', action='store_true', help="Rebase existing local branches on their upstreams.")
  parser.add_argument('--no-fetch', '-n', action='store_true', help="Skip fetching remote updates.")
  args = parser.parse_args()

  if not args.update and not args.rebase:
    parser.print_help()
    sys.exit(1)

  if not os.path.exists('.git'):
    print("Error: No .git directory found. This script must be run from the root of a Git repository.", file=sys.stderr)
    sys.exit(1)

  if not is_valid_git_repo():
    print("Error: No git remotes configured for this repository.", file=sys.stderr)
    sys.exit(1)

  if args.update:
    update_base_branches(no_fetch=args.no_fetch)

  if args.rebase:
    rebase_local_branches(no_fetch=args.no_fetch)
