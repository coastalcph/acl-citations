#!/usr/bin/env python3

"""
Fuzzy matching for papers extracted by find_cited_papers.py

Usage:
  match_cited_papers.py -h
  match_cited_papers.py <csvfile> [options]

Arguments:
  <csvfile>                 CSV file to read from.

Options:
  -r, --ratio NUM           Maximum allowed score for fuzzy matching. [default: 90]
  --debug                   Verbose log messages.
  -h, --help                Display this helpful text.
"""

from collections import defaultdict
from docopt import docopt
import better_exceptions
import csv
import logging
import logzero
from logzero import logger as log
import string
import os

from fuzzywuzzy import fuzz

global FUZZRATIO
FUZZRATIO = 90
SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))


def parse_author_string(s):
    authors = []
    for author_str in s.split(", "):
        elems = author_str.split(" ")
        authors.append((" ".join(elems[:-1]), elems[-1]))
    return authors


def authors_to_str(authors):
    return ", ".join(" ".join(author) for author in authors)


def check_authors(a_list, b_list):
    if a_list == b_list:
        return True
    # number of authors needs to match
    if len(a_list) != len(b_list):
        return False
    lower_first = lambda l: tuple(x[0].lower() for x in l)
    lower_last = lambda l: tuple(x[1].lower() for x in l)
    for a_last, b_last in zip(lower_last(a_list), lower_last(b_list)):
        if a_last != b_last and fuzz.ratio(a_last, b_last) <= FUZZRATIO:
            return False
    for a_first, b_first in zip(lower_first(a_list), lower_first(b_list)):
        if not a_first or not b_first:
            continue
        if (
            a_first != b_first
            and a_first[0] != b_first[0]
            and fuzz.ratio(a_first, b_first) <= FUZZRATIO
        ):
            return False
    # log.debug(f'fuzzy-matched authors "{authors_to_str(a_list)}" and "{authors_to_str(b_list)}"')
    return True


def check_title(a_title, b_title):
    # titles are already lower-cased
    if a_title == b_title:
        return True
    if fuzz.ratio(a_title, b_title) > FUZZRATIO:
        # log.debug(f'fuzzy-matched titles "{a_title}" and "{b_title}"')
        return True
    return False


def match_within_year(data):
    by_id = {}  # new_id -> list of rows referring to the same paper
    next_id = 1

    for row in data:
        acl_id, _, author_string, title = row
        authors = parse_author_string(author_string)
        row[2] = authors
        title = title.lower()

        # try to match up with all entries in by_id
        for new_id, entries in by_id.items():
            _, _, c_authors, c_title = entries[0]
            c_title = c_title.lower()
            # the easiest case: perfect match
            if authors == c_authors and title == c_title:
                by_id[new_id].append(row)
                break
            if not check_authors(authors, c_authors):
                continue
            if not check_title(title, c_title):
                continue
            by_id[new_id].append(row)
            break

        # nothing matched -- new entry
        else:
            by_id[next_id] = [row]
            next_id += 1

    return by_id


def match_data(data):
    # gather by year, then match within year
    data_by_year = defaultdict(list)
    for row in data:
        data_by_year[row[1]].append(row)

    by_year_id = {}
    for year, rows in data_by_year.items():
        by_year_id[year] = match_within_year(rows)

    return by_year_id


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = logging.DEBUG if args["--debug"] else logging.INFO
    logzero.loglevel(log_level)
    logzero.formatter(logzero.LogFormatter(datefmt="%Y-%m-%d %H:%M:%S"))

    with open(args["<csvfile>"], "r", newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter="\t", quotechar="|")
        data = [row for row in reader]

    FUZZRATIO = int(args["--ratio"])

    matched = match_data(data)
    output = []

    min_match = 5

    # output only rows that are matched at least N times
    for year, by_id in matched.items():
        for new_id, entries in by_id.items():
            if len(entries) < min_match:
                continue
            row = [
                f"{year}-{new_id:03d}",
                str(len(entries)),
                authors_to_str(entries[0][2]),
                entries[0][3],
                ",".join(e[0] for e in entries),
            ]
            output.append(row)

    for row in output:
        print("\t".join(row))
