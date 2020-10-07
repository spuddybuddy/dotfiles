# -*-Mode: Shell-script;-*-
# Sourced for every shell.
# author: mark a. foltz <spuddybuddy@ubertuber.org>
# https://github.com/spuddybuddy/dotfiles

# a minimal set of environment variables that allows, e.g. cron scripts to run.
# this is designed to be sourced once at login, so that all shells inherit
# these settings.

if [ -z "$MFOLTZ_ENVIRONMENT_WAS_SOURCED" ]; then

mf_log "Executing $HOME/.environment"

########### Unix variables.

# these should be set for us, but sometimes they are not.

[ -z "$USER" ] && export USER="mfoltz"
[ -z "$HOST" ] && export HOST=`hostname`

# normally, I would defer to the platform setting, but leaving these to
# chance causes all sorts of gnarliness

export LANG="en_US.UTF-8"
export TZ="America/Los_Angeles"

# Figure out what OS we are on
export OS="$(uname)"

########### Emacs

export EDITOR="$HOME/bin/mfedit"
export VISUAL="$HOME/bin/mfedit"

########### Chromium

export CHROMIUM_ROOT="$HOME/chrome"
export OPENSCREEN_ROOT="$HOME/openscreen"
export CHROMIUM_SRC="$CHROMIUM_ROOT/src"
export LLVM_SYMBOLIZER_PATH="third_party/llvm-build/Release+Asserts/bin/llvm-symbolizer"
unset CC CXX

# Figure out what flavor of Chromium buildtools to use
chromium_buildtools_platform='unknown'
if [ $OS == 'Linux' ]; then
  chromium_buildtools_platform='linux64'
elif [ $OS == 'Darwin' ]; then
  chromium_buildtools_platform='mac'
fi


########### $PATH
local mypath_pre=""
function add_to_path_pre() {
  if [ -d $1 ]; then
    if [ -z "$mypath_pre" ]; then
      mypath_pre="$1"
    else
      mypath_pre="$mypath_pre:$1"
    fi
  fi
}
local mypath_post=""
function add_to_path_post() {
  if [ -d $1 ]; then
    if [ -z "$mypath_post" ]; then
      mypath_post="$1"
    else
      mypath_post="$mypath_post:$1"
    fi
  fi
}

# Personal scripts
add_to_path_post $HOME/github/spuddybuddy/dotfiles/bin

# Chrome related
add_to_path_pre $CHROMIUM_ROOT/depot_tools
# Sometimes, depot_tools is checked out into $HOME.
add_to_path_pre $HOME/depot_tools

# Add the path to Chromium buildtools before depot_tools, so they can be used
# outside of $CHROMIUM_ROOT.  Used for gn and clang-format
add_to_path_pre $CHROMIUM_SRC/buildtools/$chromium_buildtools_platform
add_to_path_post $CHROMIUM_SRC/third_party/llvm-build/Release+Asserts/bin

# TODO: Add openscreen buildtools to $PATH if they are not found in $CHROMIUM_SRC

# Android tools
add_to_path_post $HOME/android/android-sdk-linux/platform-tools
# Sometimes, there are just binaries dropped in a folder (no SDK)
add_to_path_post $HOME/android

# Appengine tools
# https://cloud.google.com/appengine/downloads
add_to_path_post $HOME/google_appengine

# gsutil
# https://cloud.google.com/storage/docs/gsutil_install
add_to_path_post $HOME/gsutil

# Scripts installed by pip (Python).  Mostly for bikeshed
add_to_path_post $HOME/.local/bin

# Locally built binaries on OS X
if [ $OS == 'Darwin' ]; then
    add_to_path_post /opt/local/bin
fi

# pyenv: https://github.com/pyenv/pyenv
if [ -d $HOME/.pyenv ]; then
    export PYENV_ROOT="$HOME/.pyenv"
    add_to_path_pre "$PYENV_ROOT/bin"
fi

source_if_readable $HOME/gob/dotfiles/.environment

[ -n "$mypath_pre" ] && export PATH="$mypath_pre:$PATH"
[ -n "$mypath_post" ] && export PATH="$PATH:$mypath_post"

# pyenv prepends shims to $PATH to override the system-wide Python installation.
# We need Python3 >= 3.7 for Bikeshed.
if [ "command -v pyenv 1>/dev/null 2>&1" ]; then
    eval "$(pyenv init -)"
fi

# kilroy was here - don't run more than once.
export MFOLTZ_ENVIRONMENT_WAS_SOURCED="true"

fi
