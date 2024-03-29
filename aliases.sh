#-*- Mode: Shell-script; -*-
# author: mark a. foltz <spuddybuddy@ubertuber.org>
# https://github.com/spuddybuddy/dotfiles

mf_log "Executing $HOME/.aliases"

# basics.
alias ls='ls -F'
alias sl='ls -F'
alias ll='ls -lFa'
alias more=less

# Chromium.
alias crdebug="./out/debug/chrome --enable-logging=stderr --user-data-dir=/tmp --v=0 --log-level=1"
alias crrelease="./out/release/chrome --enable-logging=stderr --user-data-dir=/tmp --v=0 --log-level=1"
alias crformat="git clang-format --force --verbose origin/main -- "

### !!! ACHTUNG !!!
### If you change this, update the dirtrack-list regexp in .emacs so
### that dirtrack-mode continues to function.
function myprompt() {
  PS1="[\u@\h ${PWD/$HOME/~}]$ "
}

function setdisplay() {
  export DISPLAY="$1";
  echo "$1" > $HOME/.xdisplay
}

function httpd() {
  python -m SimpleHTTPServer $1 2>&1 & > "$HOME/logs/SimpleHttpServer.$(date '%Y%M%d-%H%M%s').log"
}

source_if_readable $HOME/gob/dotfiles/.aliases
