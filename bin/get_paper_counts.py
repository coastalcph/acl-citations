#!/usr/bin/env python3

"""
Gets the paper counts from ACL + CL for 1980--2018 and outputs them csv format.

Usage:
  get_paper_counts.py --csv <csvfile> [options]

Options:
  --csv <csvfile>          File to write citation data to.
  --debug                  Verbose log messages.
  -h, --help               Display this helpful text.
"""

from docopt import docopt
import better_exceptions
import csv
import logging
import logzero
from logzero import logger as log
import os

from acl_anthology import update_acl_repo, match_ids


SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = logging.DEBUG if args["--debug"] else logging.INFO
    logzero.loglevel(log_level)
    logzero.formatter(logzero.LogFormatter(datefmt="%Y-%m-%d %H:%M:%S"))

    update_acl_repo(f"{SCRIPTDIR}/.anthology-repo")
    counts = {}
    # All papers from 1980--2018
    for year in range(1980, 2019):
        year_suffix = str(year)[-2:]
        # Everything All "ACL" and "CL" papers
        idlist = (f"?{year_suffix}-*",)
        counts[year] = len(match_ids(idlist))

    with open(args["--csv"], "w", newline="") as csvfile:
        writer = csv.writer(
            csvfile, delimiter="\t", quotechar="|", quoting=csv.QUOTE_MINIMAL
        )
        for year, count in counts.items():
            writer.writerow([year, count])
