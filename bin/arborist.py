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

    
def get_current_branch(cwd=None):
  """Gets the current git branch name."""
  result = subprocess.run(['git', 'branch', '--show-current'], check=True, cwd=cwd, text=True, capture_output=True)
  return result.stdout.strip()

  
def branch_exists(branch_name, cwd=None):
  """Checks if a local git branch exists."""
  result = subprocess.run(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch_name}'], cwd=cwd)
  return result.returncode == 0

def update_branch(branch, cwd=None):
  print(f"\n--- Updating '{branch}' branch ---")
  if not branch_exists(branch, cwd=cwd):
    print(f"Branch '{branch}' does not exist. Creating and tracking origin/{branch}...")
    run_command(['git', 'checkout', '-b', branch, '-t', 'origin/' + branch], cwd=cwd)
  elif get_current_branch(cwd=cwd) != branch:
    print(f"Checking out '{branch}'...")
    run_command(['git', 'checkout', branch], cwd=cwd)

  print(f"Pulling latest changes for '{branch}' from origin/{branch}...")
  run_command(['git', 'pull', '--rebase', 'origin', branch], cwd=cwd)


def get_local_branches(cwd=None):
  """Gets a list of all local git branches."""
  result = subprocess.run(['git', 'for-each-ref', '--format=%(refname:short)', 'refs/heads/'], check=True, cwd=cwd, text=True, capture_output=True)
  return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def get_upstream_branch(branch, cwd=None):
  """Gets the upstream tracking branch for a given local branch."""
  result = subprocess.run(['git', 'for-each-ref', '--format=%(upstream:short)', f'refs/heads/{branch}'], cwd=cwd, text=True, capture_output=True)
  return result.stdout.strip()


def load_state(cwd=None):
  state_path = os.path.join(cwd or os.getcwd(), STATE_FILE)
  if os.path.exists(state_path):
    try:
      with open(state_path, 'r') as f:
        return json.load(f)
    except Exception as e:
      print(f"Warning: Failed to load state file: {e}", file=sys.stderr)
  return None


def save_state(state, cwd=None):
  state_path = os.path.join(cwd or os.getcwd(), STATE_FILE)
  try:
    with open(state_path, 'w') as f:
      json.dump(state, f, indent=2)
  except Exception as e:
    print(f"Error saving state file: {e}", file=sys.stderr)


def clear_state(cwd=None):
  state_path = os.path.join(cwd or os.getcwd(), STATE_FILE)
  if os.path.exists(state_path):
    try:
      os.remove(state_path)
    except Exception as e:
      print(f"Error: Failed to remove state file: {e}", file=sys.stderr)


def is_rebase_in_progress(cwd=None):
  result = subprocess.run(['git', 'rev-parse', '--git-dir'], capture_output=True, text=True, cwd=cwd)
  if result.returncode != 0:
    return False
  git_dir = result.stdout.strip()
  rebase_merge = os.path.join(cwd or os.getcwd(), git_dir, 'rebase-merge')
  rebase_apply = os.path.join(cwd or os.getcwd(), git_dir, 'rebase-apply')
  return os.path.exists(rebase_merge) or os.path.exists(rebase_apply)

  
def update_chromium_branches():
  """Manages and updates 'main' and 'lkgr' branches in Chromium checkout."""
  chromium_src_dir = os.getcwd()
  print(f"Operating in: {chromium_src_dir}")

  if is_rebase_in_progress(cwd=chromium_src_dir):
    print("Warning: A git rebase is currently in progress. Skipping main/lkgr update to avoid corrupting rebase state.", file=sys.stderr)
    return

  if not os.path.exists(os.path.join(chromium_src_dir, '.git')):
    print("Error: No .git directory found. This script must be run from the root of a Git repository.", file=sys.stderr)
    return

  original_branch = get_current_branch(cwd=chromium_src_dir)
  print(f"Original branch: {original_branch}")

  update_branch('main', cwd=chromium_src_dir)
  update_branch('lkgr', cwd=chromium_src_dir)

  # --- Restore original branch ---
  current_branch = get_current_branch(cwd=chromium_src_dir)
  if original_branch and original_branch != current_branch:
    print(f"\n--- Restoring original branch '{original_branch}' ---")
    run_command(['git', 'checkout', original_branch], cwd=chromium_src_dir)
    print(f"Restored to branch '{original_branch}'.")

  print("\nBranch update process finished.")


def rebase_local_branches(cwd=None):
  """Mode to rebase existing local branches on their upstreams."""
  cwd = cwd or os.getcwd()
  print(f"Operating in: {cwd}")

  if not os.path.exists(os.path.join(cwd, '.git')):
    print("Error: No .git directory found. This script must be run from the root of a Git repository.", file=sys.stderr)
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
    # Starting a fresh rebase session
    original_branch = get_current_branch(cwd=cwd)

    # 1. Print a map of existing branches using git map-branches
    print("\n--- 1. Branch Map ---")
    try:
      run_command(['git', 'map-branches'], cwd=cwd)
    except RunCommandError as e:
      print(f"Warning: Failed to run git map-branches: {e}", file=sys.stderr)

    # Initialize state for step 2
    all_branches = get_local_branches(cwd=cwd)
    pending_branches = [b for b in all_branches if b not in ['main', 'lkgr']]
    state = {
      'original_branch': original_branch,
      'pending_branches': pending_branches,
      'current_rebasing_branch': None
    }
    save_state(state, cwd=cwd)

  # 2. For each local branch that is not main or lkgr, offer to rebase it on its upstream
  print("\n--- 2. Rebasing Local Branches ---")
  while state['pending_branches']:
    branch = state['pending_branches'][0]
    upstream_branch = get_upstream_branch(branch, cwd=cwd)
    if not upstream_branch:
      print(f"\nBranch '{branch}' has no upstream configured. Skipping.")
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
      run_command(['git', 'rebase', '--onto', upstream_branch, '--fork-point', upstream_branch, branch], cwd=cwd)
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
  parser = argparse.ArgumentParser(description="Arborist: Chromium git branch management utility.")
  parser.add_argument('--update', '-u', action='store_true', help="Update main and lkgr branches from their remote upstreams.")
  parser.add_argument('--rebase', '-r', action='store_true', help="Rebase existing local branches on their upstreams.")
  args = parser.parse_args()

  if not args.update and not args.rebase:
    parser.print_help()
    sys.exit(1)

  if not os.path.exists('chrome'):
    print("Warning: 'chrome' not found. This script should ideally be run from the root of the Chromium 'src' directory.", file=sys.stderr)

  if args.update:
    update_chromium_branches()

  if args.rebase:
    rebase_local_branches()
