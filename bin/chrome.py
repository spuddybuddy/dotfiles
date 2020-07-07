#!/usr/bin/python3

import datetime
import getopt
import os
import subprocess
import sys

# Features to enable
CHROME_FEATURES = ["CastMediaRouteProvider", "GlobalMediaControlsForCast"]

# Where the Chrome binary lives
CHROME_PATHS = {
    "stable": "/opt/google/chrome",
    "beta":   "/opt/google/chrome-beta",
    "dev":    "/opt/google/chrome-unstable"
}

# Where Chrome profile data lives, relative to $HOME
CHROME_USER_DIRS = {
    "stable": ".config/google-chrome",
    "beta":   ".config/google-chrome-beta",
    "dev":    ".config/google-chrome-unstable"
}

def RunChrome(channel, extra_args):
  home = os.getenv("HOME")
  chrome_args = [
      "--enable-logging",
      "--also-log-to-stderr",
      "--no-proxy-server",
      "--show-component-extension-options",
      "--enable-features=" + ",".join(CHROME_FEATURES),
      "--user-data-dir=" + os.path.join(home, CHROME_USER_DIRS[channel]),
      ] + extra_args

  # I go low-level here with the os module since I couldn't find another way to
  # redirect stdout/stderr and then exec Chrome.  subprocess.run makes this much
  # easier, but it spawns Chrome as a child process and there's no need to keep
  # this Python process around.
  logfile_name = os.path.join(home,
                              "logs",
                              "google-chrome-" + channel + "-" +
                              datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".log")
  os.mknod(logfile_name)
  logfile_fd = os.open(logfile_name, os.O_WRONLY)
  chrome_path = os.path.join(CHROME_PATHS[channel], "chrome")
  os.dup2(logfile_fd, 1)  # 1=STDOUT
  os.dup2(logfile_fd, 2)  # 2=STDERR
  os.write(logfile_fd, bytes(chrome_path + " ".join(chrome_args) + "\n", "utf-8"))
  os.execv(chrome_path, chrome_args)


def main(argv):
  try:
    channel = "stable"
    opts, args = getopt.getopt(argv,"c:",["channel="])
    for opt, value in opts:
      if opt in ("-c", "--channel"):
        channel = value
        if channel not in CHROME_PATHS.keys():
          raise getopt.GetoptError
    RunChrome(channel, args)
  except getopt.GetoptError:
    print (sys.argv[0], " [-c [stable|beta|dev]]")
    sys.exit(2)


if __name__ == "__main__":
  main(sys.argv[1:])
