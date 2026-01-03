#!/usr/bin/python3

import argparse
import yaml
import os
import re
import subprocess
import sys
import concurrent.futures
from pathlib import Path

CONFIG_FILENAME = 'jooce.yaml'

def _ToLower(s):
  """
  Returns a lowercase version of s with non-alphanumeric characters replaced
  by '_'.
  """
  return re.sub(r'[^\w]', '_', s.lower())

class Config:
  def __init__(self, action, input_pattern, output_pattern, command):
    self.action = action
    self.input_pattern = input_pattern
    self.output_pattern = output_pattern
    self.command = command

  def _MakeDict(self, input_path, n, output_path = None):
    return {
      'action': self.action,
      'input': str(input_path),
      'output': str(output_path),
      'name' : input_path.name,
      'stem' : input_path.stem,
      'stem_lower' : _ToLower(input_path.stem),
      'suffix': input_path.suffix,
      'n': str(n),
    }

  def MakeCommand(self, input_path, n):
    output_path = self.MakeOutputPath(input_path, n)
    format_dict = self._MakeDict(input_path, n, output_path)
    return self.command.format(**format_dict)

  def MakeOutputPath(self, input_path, n):
    format_dict = self._MakeDict(input_path, n)    
    return input_path.parents[0].joinpath(self.output_pattern.format(**format_dict))

  
def ReadConfigs(config_file):
    """
    Reads the configuration from the YAML file.

    Args:
        config_file (str): Path to the config.yaml file.

    Returns:
        dict: Configuration dictionary.
    """
    configs = {}
    with open(config_file, 'r') as f:
      config_parsed = yaml.safe_load(f)
    # TODO: Support multiple configs by checking if a sequence is returned by yaml.
    config = config_parsed
#    for config in config_parsed:
    is_valid = True;
    for item in ['action', 'input', 'output', 'command']:
      if item not in config or not isinstance(item, str):
        is_valid = False
        
    if not is_valid:
      print("Invalid config, skipping", str(config))
    else:
      configs[config['action']] = Config(config['action'],
                                         config['input'],
                                         config['output'],
                                         config['command'])
    return configs

  
def IsNewer(a, b):
  if not b.exists():
    return False

  a_stat = a.stat()
  b_stat = b.stat()
  return b_stat.st_mtime >= a_stat.st_mtime


def RunCommand(command, input_path, n):
    """
    Runs a subprocess command for a given input and output file.
    This is where you would define the actual command to be executed.
    For this example, we're just creating a placeholder command that
    demonstrates the process.

    Args:
        command (str): The command to run.
        input_path (Path): Path to the input file.
    """
    try:
      process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
      stdout, stderr = process.communicate()

      if process.returncode == 0:
        print(f"[{n}] Successfully ran {command}")
      else:
        print(f"[{n}] Error running {command}")
        print(f"[{n}] Return code {process.returncode}")
        if stderr:
          print(f"[{n}] stderr: {stderr.decode()}") # Decode bytes to string for printing

    except Exception as e:
      print(f"[{n}] Exception during subprocess execution for {input_path}: {e}")

        
def RunConfig(config, root, max_workers, dry_run):
  input_paths = root.glob(config.input_pattern)
  if not input_paths:
    print(f"No input files found matching pattern: {input_pattern}")
    return

  n = 1;
  with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
    futures = []
    for input_path in input_paths:
      output_path = config.MakeOutputPath(input_path, n)
      if IsNewer(input_path, output_path):
        print(f"[{n}] Skipping {input_path} as {output_path} is newer")
        continue
      
      command = config.MakeCommand(input_path, n)
      print(f"[{n}] Running command: {command}")
      if not dry_run:
        futures.append(executor.submit(RunCommand, command, input_path, n))
        
    if futures:
      concurrent.futures.wait(futures) # Wait for all subprocesses to complete
      
  print("Parallel processing completed.")

        
def main(argv):
  parser = argparse.ArgumentParser(
    prog='jooce.py',
    description='Runs a command in parallel across multiple files.')
  parser.add_argument('-a', '--action', help='The action to take.')
  parser.add_argument('-n', '--dry_run', action='store_true', default=False, help='Whether to run any commands.')
  parser.add_argument('-m', '--max_workers', type=int, default=10, help='The maximum number of commands to run at once.')
  parser.add_argument('-i', '--path', help='Path to look for input files.')

  args = parser.parse_args(argv)

  if not args.action:
    parser.print_help()
    return 1

  configs = ReadConfigs(os.path.join(os.path.dirname(__file__), CONFIG_FILENAME))
  config = configs[args.action]

  if not config:
    print(f"Missing action {action} from {config_path}")
    return 1

  root = Path.cwd()
  if args.path:
    root = Path(args.path)
  RunConfig(config, root, args.max_workers, args.dry_run)
  return 0

  
if __name__ == "__main__":
  # Example config.yaml content:
  # ```yaml
  # youtube:
  #   input: "**/*.mp4"
  #   output: "{stem}-{config}.{suffix}"
  #   command: "ffmpeg -i ${input} ${output}"
  # -
  # ```
  sys.exit(main(sys.argv[1:]))

