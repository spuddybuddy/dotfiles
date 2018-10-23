# Executed on login

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
create_local logs

source_if_readable $HOME/.bash_logging

echo "$(date) Executing $HOME/.bash_profile"

# Take a big dump.
ulimit -c unlimited

# Set umask appropriately.
umask 022

[ -d $HOME/gob/dotfiles ] && source $HOME/gob/dotfiles/.bash_profile
