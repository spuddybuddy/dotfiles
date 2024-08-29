#!/usr/bin/python3

import getopt
#import os
import re
#import shutil
import sys

_LINE_SPLIT_RE = re.compile(r'[,\t]+')

def ParsePatternsCsv(infile):
    patterns = []
    infile_obj = sys.stdin
    if infile:
        infile_obj = open(infile)
    def quote(p): return p.strip().replace(r"'", r"\'")
    with infile_obj:
        for line in infile_obj:
            s = _LINE_SPLIT_RE.split(line);
            if len(s) == 2:
                patterns.append((quote(s[0]), quote(s[1])))
    return patterns


def WriteMffrSpec(patterns, outfile):
    outfile_obj = sys.stdout
    if outfile:
          outfile_obj = open(outfile, mode='w')
    with outfile_obj:
      outfile_obj.write('[\n')
      for p in patterns:
          outfile_obj.write("  [r'{0}', r'{1}'],\n".format(p[0], p[1]))
      outfile_obj.write(']\n')


def main(argv):
    infile = None;
    outfile = None;
    try:
        opts, extra_args = getopt.getopt(argv,
                                         "i:o:",
                                         ["in=", "out="])
        for (option, value) in opts:
            if option in ["-i", "--in"]:
                infile = value
            elif option in ["-o", "--out"]:
                outfile = value
    except getopt.GetoptError as e:
        print ("Arguments error: ", e.msg, " ", e.opt)
        PrintUsage()
        sys.exit(2)

    patterns = ParsePatternsCsv(infile)
    WriteMffrSpec(patterns, outfile)


if __name__ == "__main__":
    main(sys.argv[1:])
