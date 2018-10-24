#-*- Mode: Shell-script; -*-
# mark foltz's .bashrc
# started 9/8/03

function source_if_readable() {
  [ -r $1 ] && source $1
}

source_if_readable $HOME/.bash_logging

echo "$(date) Executing $HOME/.bashrc"

# environment setup
source_if_readable $HOME/.environment
source_if_readable $HOME/gob/dotfiles/.environment

# Source functions and aliases, if we are in an interactive shell.
if [ -n "${PS1}"  ]; then
  source_if_readable /etc/bash_completion
  source_if_readable $HOME/.aliases
  source_if_readable $HOME/gob/dotfiles/.aliases
  
  # Set the prompt to something reasonable.
  export PROMPT_COMMAND=myprompt
  unset MAILCHECK
  unset noclobber
fi
