#!/bin/bash
# Usage: runmany N <command> <args>...
# TODOs:
# - Convert to Python3.
# - Handle console output in a sane way.
# - (Maybe) allow simultaneous execution.
numtimes=$1
numpass=0
numfail=0
shift
for i in $(seq 1 1 $numtimes)
do
  echo "   ============>>>> $i/$numtimes <<<<============"
  $*
  if [ $? != 0 ]; then
    echo "   ============>>>> $i/$numtimes FAILED! <<<<============"
    numfail=$(($numfail + 1))
  else
    echo "   ============>>>> $i/$numtimes PASSED <<<<============"
    numpass=$(($numpass + 1))
  fi
done
echo "   ===>>> Ran $numtimes, $numpass passed, $numfail failed <<<===";
