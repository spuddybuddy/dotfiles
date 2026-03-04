#!/usr/bin/env python3

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

  
def update_chromium_branches():
  """Manages and updates 'main' and 'lkgr' branches in Chromium checkout."""
  chromium_src_dir = os.getcwd()
  print(f"Operating in: {chromium_src_dir}")

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

if __name__ == '__main__':
    if not os.path.exists('chrome'):
      print("Warning: 'chrome' not found. This script should ideally be run from the root of the Chromium 'src' directory.", file=sys.stderr)
    update_chromium_branches()
