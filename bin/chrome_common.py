import os
import datetime

# Features to enable.
CHROME_ENABLED_FEATURES = ["CameraMicPreview","GetUserMediaDeferredDeviceSettingsSelection"]

# Features to disable.
CHROME_DISABLED_FEATURES = []

# path: Path to the Chrome binary.
# logname: Tag to identify the logfile.
# enabled_features: List of features to enable.
# disabled_features: List of features to disable.
# user_dir: Path to user directory.
# args: List of arguments.
# extra_args: More arguments.
# env: Dict of environment variables to set on the process.
def RunChrome(path, logname, enabled_features, disabled_features, user_dir, args,
              extra_args = [], env = None):
  # The first element of the argument list is the name of the program being run,
  # not an actual commandline argument.
  execv_args = [path] + args + [
      "--enable-features=" + ",".join(enabled_features),
      "--disable-features=" + ",".join(disabled_features),
      "--user-data-dir=" + user_dir,
      ] + extra_args

  # I go low-level here with the os module since I couldn't find another way to
  # redirect stdout/stderr and then exec Chrome.  subprocess.run makes this much
  # easier, but it spawns Chrome as a child process and there's no need to keep
  # this Python process around.
  home = os.getenv("HOME")
  logfile_path = os.path.join(home, "logs")
  logfile_name = os.path.join(logfile_path,
                              "google-chrome-" + logname + "-" +
                              datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".log")
  os.makedirs(logfile_path, exist_ok=True)
  logfile_fd = os.open(logfile_name, os.O_WRONLY | os.O_CREAT)
  os.dup2(logfile_fd, 1)  # 1=STDOUT
  os.dup2(logfile_fd, 2)  # 2=STDERR
  os.write(logfile_fd, bytes(" ".join(execv_args) + "\n", "utf-8"))
  chrome_env = os.environ
  if env:
    chrome_env.update(env)
  os.execve(path, execv_args, chrome_env)
