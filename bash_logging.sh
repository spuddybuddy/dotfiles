#-*- Mode: Shell-script; -*-
# author: mark a. foltz <spuddybuddy@ubertuber.org>
# https://github.com/spuddybuddy/dotfiles

if [ -z "$MFOLTZ_LOG" ]; then
  export MFOLTZ_LOG=$HOME/logs/login-$(date '+%Y%m%d-%H%M%S').log
fi

function mf_log() {
  echo "$(date '+%Y%m%d-%H:%M:%S') $1" >> $MFOLTZ_LOG
}
