#-*- Mode: Shell-script; -*-
# author: mark a. foltz <spuddybuddy@ubertuber.org>
# https://github.com/spuddybuddy/dotfiles

# Sourced for every shell.

function source_if_readable() {
  [ -r $1 ] && source $1
}

source_if_readable $HOME/github/spuddybuddy/dotfiles/bash_logging.sh

mf_log "Executing $HOME/.bashrc"

# environment setup
source_if_readable $HOME/github/spuddybuddy/dotfiles/environment.sh

# Source functions and aliases, if we are in an interactive shell.
if [ -n "${PS1}"  ]; then
  source_if_readable /etc/bash_completion
  source_if_readable $HOME/github/spuddybuddy/dotfiles/aliases.sh
  
  # Set the prompt to something reasonable.
  export PROMPT_COMMAND=myprompt
  unset MAILCHECK
  unset noclobber
fi

source_if_readable $HOME/gob/dotfiles/.bashrc


# added by travis gem
[ -f /home/mfoltz/.travis/travis.sh ] && source /home/mfoltz/.travis/travis.sh
