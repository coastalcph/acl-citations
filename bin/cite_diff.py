#!/usr/bin/env python3

"""
Diffs two files with extracted citation data in a readable way.

Usage:
  parse_tei.py -h
  parse_tei.py <file_a> <file_b> [options]

Arguments:
  <file_a>                  First file in comparison.
  <file_b>                  Second file in comparison.

Options:
  --debug                   Verbose log messages.
  -h, --help                Display this helpful text.
"""

from docopt import docopt
import better_exceptions
import csv
import logging
import logzero
from logzero import logger as log
import os


def parse_csv(filename):
    data = {}
    with open(filename, "r", newline="") as csvfile:
        reader = csv.reader(
            csvfile, delimiter="\t", quotechar="|", quoting=csv.QUOTE_MINIMAL
        )
        for row in reader:
            paper_id = row[0]
            cited_years = [] if len(row) < 3 else row[2].split(",")
            data[paper_id] = sorted(cited_years)
    return data


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = logging.DEBUG if args["--debug"] else logging.INFO
    logzero.loglevel(log_level)
    logzero.formatter(logzero.LogFormatter(datefmt="%Y-%m-%d %H:%M:%S"))

    a = parse_csv(args["<file_a>"])
    b = parse_csv(args["<file_b>"])
    all_keys = sorted(set(a.keys()) | set(b.keys()))

    for key in all_keys:
        if key not in a:
            print(f"{key}\tN/A\t{','.join(b[key])}")
            continue
        if key not in b:
            print(f"{key}\t{','.join(a[key])}\tN/A")
            continue
        if a[key] == b[key]:
            continue
        a_list, b_list = a[key][:], b[key][:]
        for item in a[key]:
            if item in b_list:
                del b_list[b_list.index(item)]
        for item in b[key]:
            if item in a_list:
                del a_list[a_list.index(item)]

        a_list = ",".join(a_list) if a_list else "--"
        b_list = ",".join(b_list) if b_list else "--"
        print(f"{key}\t{a_list}\t{b_list}")
