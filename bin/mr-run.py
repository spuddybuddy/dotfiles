#!/usr/bin/python3

import getopt
import os
import shutil
import sys

import chrome_common

VMODULE_PATTERNS = [
    "?resentation*",
    "cast_*",
    "media_r*",
    "offscreen_tab*",
    "dial*",
    "cast_cert*",
]

def RunChromeBuild(path, chrome_folder, user_dir, vmodule, prefix_args, extra_args):
    vmodule_arg = ",".join([pattern + "=2" for pattern in VMODULE_PATTERNS + vmodule])
    args = prefix_args + [
        "--enable-logging",
        "--also-log-to-stderr",
        "--vmodule=" + vmodule_arg,
        "--no-proxy-server",
        "--unsafely-treat-insecure-origin-as-secure=http://web-platform.test:8001",
        "--enable-experimental-web-platform-features",
        "--disable-gesture-requirement-for-presentation",
    ]
    chrome_common.RunChrome(
        os.path.join(chrome_folder, "chrome"),
        'local',
        chrome_common.CHROME_FEATURES,
        user_dir,
        args,
        extra_args)


def RemoveUserDir(user_dir):
    if os.access(user_dir, os.W_OK):
        print ("Removing %s..." % user_dir)
        shutil.rmtree(user_dir)


def PrintUsage():
    print ("Runs a local Chrome build in $CHROMIUM_SRC/out/debug")
    print ("Extra arguments are passed to Chrome.")
    print ("  -d|--debug:              Run under GDB.")
    print ("  -c|--clean:              Start with an empty user data dir.")
    print ("  -b|--build <folder>:     Find Chrome in $CHROMIUM_SRC/out/<folder>.")
    print ("  -v|--vmodule <pattern>:  Comma-separated file patterns for verbose logging.")
    print ("Usage: ", sys.argv[0], " [options] extra_args...")


def main(argv):
    build_root = os.path.join(os.getenv("CHROMIUM_SRC"), "out")
    run_gdb = False
    clean_user_dir = False
    build_type = "debug"
    vmodule = []
    try:
        opts, extra_args = getopt.getopt(argv, "dcb:v:", ["debug", "clean", "build=", "vmodule="])
        for (option, value) in opts:
            if option in ["-d", "--debug"]:
                run_gdb = True
            elif option in ["-c", "--clean"]:
                clean_user_dir = True
            elif option in ["-b", "--build"]:
                build_type = value
            elif option in ["-v", "--vmodule"]:
                vmodule = value.split(",")

        chrome_folder = os.path.join(build_root, build_type)
        user_dir = os.path.join(chrome_folder, "google-chrome-local")
        if clean_user_dir:
            RemoveUserDir(user_dir)
        path = chrome_folder
        prefix_args = []
        if run_gdb:
            prefix_args += ["--args", chrome_folder]
            path = "/usr/bin/gdb"
        RunChromeBuild(path, chrome_folder, user_dir, vmodule, prefix_args, extra_args)
    except getopt.GetoptError as e:
        print ("Arguments error: ", e.msg, " ", e.opt)
        PrintUsage()
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
