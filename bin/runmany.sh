#!/bin/bash -x
# Usage: runmany N P <command> <args>...
# N - the number of times to run the test
# P - if 1, run the tests in parallel
# TODOs:
# - Convert to Python3.
# - Handle console output in a sane way.
# - (Maybe) allow simultaneous execution.
numtimes=$1
parallel=$2
numpass=0
numfail=0
shift
shift
for i in $(seq 1 1 $numtimes)
do
  echo "   ============>>>> $i/$numtimes <<<<============"
  if [ $parallel == "1" ]; then
    $* &
  else
    $*
  fi
  if [ $? != 0 ]; then
    echo "   ============>>>> $i/$numtimes FAILED! <<<<============"
    numfail=$(($numfail + 1))
  else
    echo "   ============>>>> $i/$numtimes PASSED <<<<============"
    numpass=$(($numpass + 1))
  fi
done
echo "   ===>>> Ran $numtimes, $numpass passed, $numfail failed <<<===";
