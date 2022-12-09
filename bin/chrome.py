#!/usr/bin/python3

import getopt
import os
import sys

import chrome_common

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


def RunChromeChannel(channel, extra_args):
  home = os.getenv("HOME")
  chrome_common.RunChrome(os.path.join(CHROME_PATHS[channel], "chrome"),
            channel,
            chrome_common.CHROME_ENABLED_FEATURES,
            chrome_common.CHROME_DISABLED_FEATURES,
            os.path.join(home, CHROME_USER_DIRS[channel]),
            [
                "--enable-logging",
                "--also-log-to-stderr",
                "--no-proxy-server",
                "--show-component-extension-options",
            ],
            extra_args)


def main(argv):
  try:
    channel = "stable"
    opts, extra_args = getopt.getopt(argv,"c:",["channel="])
    for opt, value in opts:
      if opt in ("-c", "--channel"):
        channel = value
        if channel not in CHROME_PATHS.keys():
          raise getopt.GetoptError
    RunChromeChannel(channel, extra_args)
  except getopt.GetoptError:
    print (sys.argv[0], " [-c [stable|beta|dev]]")
    sys.exit(2)


if __name__ == "__main__":
  main(sys.argv[1:])
