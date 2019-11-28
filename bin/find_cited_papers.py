#!/usr/bin/env python3

"""
Parse XML files produced by ParsCit to extract cited papers (with authors/title).

Usage:
  find_cited_papers.py -h
  find_cited_papers.py <dir>... --csv <csvfile> [options]

Arguments:
  <dir>                     Directory/ies with TEI files to be parsed.

Options:
  --csv <csvfile>           File to write citation data to.
  --log <logfile>           Write log output to this file.
  -a, --age <range>         Only consider citations in the given age range,
                            where <range> is of the form "<min>-<max>".
  --debug                   Verbose log messages.
  -h, --help                Display this helpful text.
"""

from docopt import docopt
import better_exceptions
import csv
from glob import glob
import logging
import logzero
from logzero import logger as log
from lxml import etree
import os


SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))


def parse_parscit(filename, min_year, max_year):
    try:
        tree = etree.parse(filename)
    except Exception as e:
        log.exception(e)
        return [], 0

    base = os.path.basename(filename)
    output = []

    for c, bibitem in enumerate(
        tree.getroot().findall(".//{*}citationList/{*}citation")
    ):
        for dateitem in bibitem.findall(".//{*}date"):
            year = dateitem.text
            if year is None or not year.isdigit():
                continue
            year = int(year)
            break
        else:
            continue

        if year > max_year or year < min_year:
            continue

        title = ""
        for elem in bibitem.findall(".//{*}title"):
            title = elem.text
        if not title:
            continue

        authors = []
        for elem in bibitem.findall(".//{*}authors//{*}author"):
            authors.append(elem.text)

        output.append([year, ", ".join(authors), title])

    return output


def infer_publication_year(file_id):
    yearstr = file_id[1:3]
    if int(yearstr) < 50:
        return f"20{yearstr}"
    else:
        return f"19{yearstr}"


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = logging.DEBUG if args["--debug"] else logging.INFO
    logzero.loglevel(log_level)
    logzero.formatter(logzero.LogFormatter(datefmt="%Y-%m-%d %H:%M:%S"))

    if args["--log"]:
        logzero.logfile(
            args["--log"],
            encoding="utf-8",
            formatter=logzero.LogFormatter(datefmt="%Y-%m-%d %H:%M:%S", color=False),
        )

    output = {}
    min_age, max_age = 0, 9999
    if args["--age"]:
        min_age, max_age = args["--age"].split("-")
        min_age = int(min_age) if min_age else 0
        max_age = int(max_age) if max_age else 9999

    for dirname in args["<dir>"]:
        log.info(f"Processing {dirname}")
        if not os.path.exists(dirname):
            log.error(f"Directory not found: {dirname}")
            continue
        for filename in glob(f"{dirname}/*.xml"):
            base = os.path.basename(filename)
            file_id = base.split(".")[0]
            if file_id.endswith("-parscit"):
                file_id = file_id[:-8]
            log.debug(f"Parsing {base}")
            pub_year = int(infer_publication_year(file_id))
            minimum_year = pub_year - max_age
            maximum_year = pub_year - min_age
            output[file_id] = parse_parscit(filename, minimum_year, maximum_year)

    with open(args["--csv"], "w", newline="") as csvfile:
        writer = csv.writer(
            csvfile, delimiter="\t", quotechar="|", quoting=csv.QUOTE_MINIMAL
        )
        for file_id, rows in output.items():
            for row in rows:
                writer.writerow([file_id] + row)
