
if [ -z "$DIRS" -o -z "$REVIEWER" ]; then
  echo "Formats .cc, .h, and .mm files using clang-format."
  echo "Usage:"
  echo "  $DIRS: Space separated list of paths to format."
  echo "  $REVIEWER: Email of code reviewer."
  exit 1;
fi

git new-branch format_$(date '+%Y%m%d_%H%M%S')
for DIR in $DIRS; do
  find $DIR -name "*.cc" -o -name "*.h" -o -name "*.mm" | xargs clang-format -i;
  git commit -a -m "[cleanup] clang-format $DIR." -m "Produced with:" -m "find $DIR
 -name \"*.cc\" -o -name \"*.h\" -o -name \"*.mm\" | xargs clang-format -i" -m "Bug: none";
done
git cl upload --commit-description + -d -r $REVIEWER -s --bypass-hooks;
