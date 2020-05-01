#!/usr/bin/env python3

"""
Fuzzy matching for papers extracted by find_cited_papers.py

Usage:
  match_cited_papers.py -h
  match_cited_papers.py <csvfile> [options]

Arguments:
  <csvfile>                 CSV file to read from.

Options:
  -j, --join-across-years   Join matching papers from subsequent years.
  -r, --ratio NUM           Maximum allowed score for fuzzy matching. [default: 95]
  --debug                   Verbose log messages.
  -h, --help                Display this helpful text.
"""

from collections import defaultdict, Counter
from docopt import docopt
import better_exceptions
import csv
from fuzzywuzzy import fuzz
import logging
import logzero
from logzero import logger as log
from slugify import slugify
import string
from tqdm import tqdm
import os


global FUZZRATIO
FUZZRATIO = 95
SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))

global counters
counters = Counter()


def parse_author_string(s):
    authors = []
    for author_str in s.split(", "):
        elems = author_str.split(" ")
        authors.append((slugify("".join(elems[:-1])), slugify(elems[-1])))
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
    counters["authors-matched"] += 1
    # log.debug(f'fuzzy-matched authors "{authors_to_str(a_list)}" and "{authors_to_str(b_list)}"')
    return True


def clean_title(title):
    title = title.lower()
    # everything after the first period is more likely to be noise (e.g.,
    # journal/proceedings info parsed as part of the title) than not
    if ". " in title:
        idx = title.index(". ")
        title = title[:idx]
    if title.endswith("."):
        title = title[:-1]
    return slugify(title)


def check_title(a_title, b_title):
    # titles are already lower-cased
    if a_title == b_title:
        return True
    if fuzz.ratio(a_title, b_title) > FUZZRATIO:
        counters["title-matched"] += 1
        # log.debug(f'fuzzy-matched titles "{a_title}" and "{b_title}"')
        return True
    return False


def match_within_year(data, progress):
    by_id = {}  # new_id -> list of rows referring to the same paper
    next_id = 1

    for row in data:
        acl_id, _, author_string, title = row
        authors = parse_author_string(author_string)
        title = clean_title(title)
        row.extend([authors, title])

        # try to match up with all entries in by_id
        for new_id, entries in by_id.items():
            *_, c_authors, c_title = entries[0]
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

        progress.update(1)

    return by_id


def match_across_years(year_a, year_b):
    # find papers with identical authors+titles published in adjacent years, as
    # this often happens when there's an arXiv paper in year Y and a
    # peer-reviewed publication in year Y+1, and people cite either one
    merged = []
    for id_a, entries_a in year_a.items():
        *_, authors_a, title_a = entries_a[0]

        for id_b, entries_b in year_b.items():
            *_, authors_b, title_b = entries_b[0]
            if authors_a == authors_b and title_a == title_b:
                counters["cross-year-merge"] += 1
                # log.debug(f"Cross-year match:  {id_a} == {id_b}")
                # log.debug(f" --- A: {entries_a[0][1]}. {entries_a[0][2]}. {entries_a[0][3]}")
                # log.debug(f" --- B: {entries_b[0][1]}. {entries_b[0][2]}. {entries_b[0][3]}")
                entries_a.extend(entries_b)
                entries_a[0][1] = "/".join((str(entries_a[0][1]), str(entries_b[0][1])))
                merged.append(id_b)
                break

    return merged


def match_data(data):
    # gather by year, then match within year
    data_by_year = defaultdict(list)
    for row in data:
        data_by_year[row[1]].append(row)

    by_year_id = {}
    progress = tqdm(total=len(data))
    for year, rows in data_by_year.items():
        by_year_id[year] = match_within_year(rows, progress)
    progress.close()

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
    min_match = 1

    matched = match_data(data)

    if args["--join-across-years"]:
        all_years = sorted(list(matched.keys()))

        def pairwise(a):
            return list(zip(a[:-1], a[1:]))

        for year_a, year_b in tqdm(pairwise(all_years)):
            if int(year_a) + 1 != int(year_b):
                continue  # only years immediately following each other
            merged_b = match_across_years(matched[year_a], matched[year_b])
            for id_b in merged_b:
                del matched[year_b][id_b]

    output = []

    for name, count in counters.items():
        log.info(f"Counter({name}) = {count}")

    # output only rows that are matched at least N times
    for year, by_id in matched.items():
        for new_id, entries in by_id.items():
            if len(entries) < min_match:
                continue
            row = [
                f"{year}-{new_id:04d}",
                str(len(entries)),
                str(entries[0][1]),
                entries[0][2],
                # authors_to_str(entries[0][4]),
                entries[0][3],
                # entries[0][5],
                ",".join(e[0] for e in entries),
            ]
            output.append(row)

    header = ("id", "num_cited", "year", "authors", "title", "citing_papers")
    print("\t".join(header))
    for row in output:
        print("\t".join(row))
