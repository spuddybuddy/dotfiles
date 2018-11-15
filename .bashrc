#-*- Mode: Shell-script; -*-
# author: mark a. foltz <spuddybuddy@ubertuber.org>
# https://github.com/spuddybuddy/dotfiles

# Sourced for every shell.

function source_if_readable() {
  [ -r $1 ] && source $1
}

source_if_readable $HOME/.bash_logging

mf_log "Executing $HOME/.bashrc"

# environment setup
source_if_readable $HOME/.environment

# Source functions and aliases, if we are in an interactive shell.
if [ -n "${PS1}"  ]; then
  source_if_readable /etc/bash_completion
  source_if_readable $HOME/.aliases
  
  # Set the prompt to something reasonable.
  export PROMPT_COMMAND=myprompt
  unset MAILCHECK
  unset noclobber
fi

source_if_readable $HOME/gob/dotfiles/.bashrc

