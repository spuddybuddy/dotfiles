#!/usr/bin/python3

import datetime
import getopt
import os
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
      "--v=1",
      "--show-component-extension-options",
      "--enable-features=" + ",".join(CHROME_FEATURES),
      "--user-data-dir=" + os.path.join(home, CHROME_USER_DIRS[channel]),
      ] + extra_args
  log_file = open(os.path.join(home,
                               "logs",
                               "google-chrome-" + channel + "-" +
                               datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".log"),
                  'w')
  sys.stdout = log_file
  sys.stderr = log_file
  chrome_path = os.path.join(CHROME_PATHS[channel], "chrome")
  print (chrome_path, " ".join(chrome_args))
  os.execv(chrome_path, chrome_args)


def main(argv):
  try:
    channel = "stable"
    opts, args = getopt.getopt(argv,"c:",["channel"])
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
