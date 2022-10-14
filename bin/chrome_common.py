import os
import datetime

# Features to enable.
CHROME_FEATURES = ["GlobalMediaControlsCastStartStop","OpenscreenCastStreamingSession"]


# path: Path to the Chrome binary.
# logname: Tag to identify the logfile.
# features: List of features to enable.
# user_dir: Path to user directory.
# args: List of arguments.
# extra_args: More arguments.
def RunChrome(path, logname, features, user_dir, args, extra_args = []):
  # The first element of the argument list is the name of the program being run,
  # not an actual commandline argument.
  execv_args = [path] + args + [
      "--enable-features=" + ",".join(features),
      "--user-data-dir=" + user_dir,
      ] + extra_args

  # I go low-level here with the os module since I couldn't find another way to
  # redirect stdout/stderr and then exec Chrome.  subprocess.run makes this much
  # easier, but it spawns Chrome as a child process and there's no need to keep
  # this Python process around.
  home = os.getenv("HOME")
  logfile_name = os.path.join(home,
                              "logs",
                              "google-chrome-" + logname + "-" +
                              datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".log")
  os.mknod(logfile_name)
  logfile_fd = os.open(logfile_name, os.O_WRONLY)
  os.dup2(logfile_fd, 1)  # 1=STDOUT
  os.dup2(logfile_fd, 2)  # 2=STDERR
  os.write(logfile_fd, bytes(" ".join(execv_args) + "\n", "utf-8"))
  os.execv(path, execv_args)
