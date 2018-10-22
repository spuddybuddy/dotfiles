#-*- Mode: Shell-script; -*-
# mark foltz's .bashrc
# started 9/8/03

echo "$(date) Executing $HOME/.bashrc" >> $HOME/logs/login.log

function source_if_readable() {
  [ -r $1 ] && source $1
}

# environment setup
source_if_readable $HOME/.environment

# Source functions and aliases, if we are in an interactive shell.
if [ -n "${PS1}"  ]; then
  source_if_readable /etc/bash_completion
  source_if_readable ${HOME}/.aliases
  # Set the prompt to something reasonable.
  export PROMPT_COMMAND=myprompt
  unset MAILCHECK
  unset noclobber
fi
