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
export DOGFOOD_STACKED_CHANGES=1
unset CC CXX

# Figure out what flavor of Chromium buildtools to use
chromium_buildtools_platform='unknown'
if [ $OS == 'Linux' ]; then
  chromium_buildtools_platform='linux64'
elif [ $OS == 'Darwin' ]; then
  chromium_buildtools_platform='mac'
fi

########### Chrome Remote Desktop

# Set the host desktop to match native monitor resolution.
export CHROME_REMOTE_DESKTOP_DEFAULT_DESKTOP_SIZES="3840x2160"

########### $PATH
mypath_pre=""
function add_to_path_pre() {
  if [ -d $1 ]; then
    if [ -z "$mypath_pre" ]; then
      mypath_pre="$1"
    else
      mypath_pre="$mypath_pre:$1"
    fi
  fi
}
mypath_post=""
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

# Sometimes, depot_tools is checked out into $HOME.
# 
# Ensure it's added before system paths, as some depot_tools binaries shadow
# system-installed ones.
add_to_path_pre $HOME/depot_tools

add_to_path_post $CHROMIUM_SRC/third_party/llvm-build/Release+Asserts/bin

# Android tools
add_to_path_post $HOME/android/platform-tools

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

# Rust installed packages.
add_to_path_pre $HOME/.cargo/bin

# Go installed commands.
add_to_path_pre $HOME/go/bin

[ -n "$mypath_pre" ] && export PATH="$mypath_pre:$PATH"
[ -n "$mypath_post" ] && export PATH="$PATH:$mypath_post"

# pyenv prepends shims to $PATH to override the system-wide Python installation.
# We need Python3 >= 3.7 for Bikeshed.
command -v pyenv 1>/dev/null 2>&1
if [ $? -eq 0 ]; then
    eval "$(pyenv init -)"
fi

# kilroy was here - don't run more than once.
export MFOLTZ_ENVIRONMENT_WAS_SOURCED="true"

fi
