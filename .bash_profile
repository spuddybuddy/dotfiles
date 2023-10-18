#-*- Mode: Shell-script; -*-
# author: mark a. foltz <spuddybuddy@ubertuber.org>
# https://github.com/spuddybuddy/dotfiles

# Executed on login.

# Usage: source_if_readable <file>
function source_if_readable() {
  [ -r $1 ] && source $1
}

# Usage: create_local <dir>
#
# Creates a directory $HOME/<dir> if it does not exist.
#
function create_local() {
  local dir=$1
  local path=${HOME}/${dir}
  if [ ! -d ${path} ]; then
    mkdir -p ${path}
    chmod 700 ${path}
  fi
}

# Create some directories we expect to live on local disk.  We do this here
# because some programs expect them to exist, and misbehave if they do not.
create_local tmp
create_local tmp/emacs
create_local logs

source_if_readable $HOME/github/spuddybuddy/dotfiles/bash_logging.sh

mf_log "Executing $HOME/.bash_profile"

# Take a big dump.
ulimit -c unlimited

# Set umask appropriately.
umask 022

# Needs to be before any ssh-agent related stuff.
source_if_readable $HOME/gob/dotfiles/.bash_profile

# Start ssh agent if not already started.
if [ -z "$SSH_AUTH_SOCK" ]; then
  eval $(ssh-agent -s)
fi

# Add GitHub keys.
function add_ssh_key() {
  local private_key=$1
  if [ -r ${private_key} ]; then
    mf_log "Adding ${private_key} to ssh-agent"
    ssh-add ${private_key}
  fi
}

add_ssh_key $HOME/.ssh/id_github_mfoltzgoogle
add_ssh_key $HOME/.ssh/id_github_spuddybuddy

# To debug SSH agent issues.
mf_log "SSH_AUTH_SOCK=$SSH_AUTH_SOCK"
mf_log "FWD_SSH_AUTH_SOCK=$SSH_AUTH_SOCK"
mf_log "SSH_AGENT_PID=$SSH_AGENT_PID"
mf_log "ssh-agent=$(ps auxwww | fgrep ssh-agent)"

echo "ssh-agent identities:"
ssh-add -l

# Source remaining files.
source_if_readable $HOME/.bashrc
