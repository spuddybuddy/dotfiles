#-*- Mode: Shell-script; -*-
# author: mark a. foltz <spuddybuddy@ubertuber.org>
# https://github.com/spuddybuddy/dotfiles

mf_log "Executing $HOME/.aliases"

# basics.
alias ls='ls -F'
alias sl='ls -F'
alias ll='ls -lFa'
alias more=less

# Chromium development
alias an=autoninja
alias anr='autoninja -C out/release'
alias and='autoninja -C out/debug'

### !!! ACHTUNG !!!
### If you change this, update the dirtrack-list regexp in .emacs so
### that dirtrack-mode continues to function.
function myprompt() {
  PS1="[\u@\h ${PWD/$HOME/~}]$ "
}

source_if_readable $HOME/gob/dotfiles/.aliases
