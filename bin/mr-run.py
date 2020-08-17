#!/usr/bin/python3

import getopt
import os
import sys

import chrome_common

VMODULE_PATTERNS = [
    "?resentation*",
    "cast_message*"
    "media_r*",
    "offscreen_tab*",
]

def RunChromeBuild(path, chrome_folder, user_dir, prefix_args, extra_args):
    vmodule_arg = ",".join([pattern + "=2" for pattern in VMODULE_PATTERNS])
    args = prefix_args + [
        "--enable-logging",
        "--also-log-to-stderr",
        "--vmodule=" + vmodule_arg,
        "--no-proxy-server",
        "--show-component-extension-options",
        "--unsafely-treat-insecure-origin-as-secure=http://web-platform.test:8001",
        "--disable-gesture-requirement-for-presentation",
    ]
    chrome_common.RunChrome(
        os.path.join(chrome_folder, "chrome"),
        'local',
        chrome_common.CHROME_FEATURES,
        user_dir,
        args,
        extra_args)


def PrintUsage():
    print ("Runs a local Chrome build in $CHROMIUM_SRC/out/<folder>.")
    print ("Extra arguments are passed to Chrome.")
    print ("  -d|--debug:           Run under GDB.")
    print ("  -c|--clean:           Start with an empty user data dir.")
    print ("  -x|--extension:       Run without the component extension.")
    print ("  -b|--build <folder>:  Find Chrome in $CHROMIUM_SRC/out/<folder>.")
    print ("Usage: ", sys.argv[0], " [options] extra_args...")


def main(argv):
    build_root = os.path.join(os.getenv("CHROMIUM_SRC"), "out")
    run_gdb = False
    clean_user_dir = False
    component = True
    build_type = "Default"
    prefix_args = []
    try:
        opts, extra_args = getopt.getopt(argv, "dcxb:", ["debug", "clean", "extension", "build="])
        for (option, value) in opts:
            if option in ["-d", "--debug"]:
                run_gdb = True
            elif option in ["-c", "--clean"]:
                clean_user_dir = True
            elif option in ["-x", "--extension"]:
                component = False
            elif option in ["-b", "--build"]:
                build_type = value

        chrome_folder = os.path.join(build_root, build_type)
        user_dir = os.path.join(chrome_folder, "google-chrome-local")
        if clean_user_dir:
            RemoveUserDir(user_dir)
        path = chrome_folder
        prefix_args = []
        if run_gdb:
            prefix_args += ["--args", chrome_folder]
            path = "/usr/bin/gdb"
        if not component:
            prefix_args += ["--load-media-router-component-extension=0"]
        RunChromeBuild(path, chrome_folder, user_dir, prefix_args, extra_args)
    except getopt.GetoptError:
        PrintUsage()
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
