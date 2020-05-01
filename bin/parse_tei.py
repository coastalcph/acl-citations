#!/usr/bin/env python3

"""
Parse XML files produced by citation extractors to get years of cited publications.

Usage:
  parse_tei.py -h
  parse_tei.py <dir>... --csv <csvfile> [options]

Arguments:
  <dir>                     Directory/ies with TEI files to be parsed.

Options:
  --csv <csvfile>           File to write citation data to.
  -f, --format <format>     XML format; one of: grobid,parscit [default: grobid].
  --log <logfile>           Write log output to this file.
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


def parse_tei_file(filename):
    tree = etree.parse(filename)
    base = os.path.basename(filename)
    citation_years = []
    bibitem_total = 0
    diff = 0
    for bibitem in tree.getroot().findall(".//{*}listBibl/{*}biblStruct"):
        item_id = bibitem.get("{http://www.w3.org/XML/1998/namespace}id")
        bibitem_total += 1
        for dateitem in bibitem.findall(".//{*}date"):
            if dateitem.get("type") == "published":
                year = dateitem.get("when")[:4]
                if not year.isdigit():
                    log.warning(
                        f"{base}, biblStruct id={item_id}: Date does not appear to contain a year: {dateitem.get('when')}"
                    )
                else:
                    citation_years.append(year)
                    break
        else:
            log.debug(
                f"{base}, biblStruct id={item_id}: Could not find a published date; skipping"
            )
    if not citation_years:
        log.error(f"{base}: Could not find any bibliography dates")
    elif len(citation_years) < bibitem_total:
        diff = bibitem_total - len(citation_years)
        entries = "entries" if diff > 1 else "entry"
        log.debug(f"{base}: Could not parse dates for {diff} {entries}")
    return citation_years, diff


def parse_parscit(filename):
    try:
        tree = etree.parse(filename)
    except Exception as e:
        log.exception(e)
        return [], 0

    base = os.path.basename(filename)
    citation_years = []
    bibitem_total = 0
    diff = 0

    for c, bibitem in enumerate(
        tree.getroot().findall(".//{*}citationList/{*}citation")
    ):
        bibitem_total += 1
        for dateitem in bibitem.findall(".//{*}date"):
            year = dateitem.text
            if year is None:
                log.debug(
                    f"{base}, citation {c}: Could not find a published date; skipping"
                )
            elif not year.isdigit():
                log.warning(
                    f"{base}, citation {c}: Date does not appear to be a year: {year}"
                )
            else:
                citation_years.append(year)
                break
        else:
            log.debug(
                f"{base}, citation {c}: Could not find a published date; skipping"
            )
    if not citation_years:
        log.error(f"{base}: Could not find any bibliography dates")
    elif len(citation_years) < bibitem_total:
        diff = bibitem_total - len(citation_years)
        entries = "entries" if diff > 1 else "entry"
        log.debug(f"{base}: Could not parse dates for {diff} {entries}")
    return citation_years, diff


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

    if args["--format"] == "grobid":
        parse_file = parse_tei_file
    elif args["--format"] == "parscit":
        parse_file = parse_parscit
    else:
        log.critical(f"Unknown --format: {args['--format']}")
        exit(1)

    cited_years = {}
    for dirname in args["<dir>"]:
        if not os.path.exists(dirname):
            log.error(f"Directory not found: {dirname}")
            continue
        dir_diff, dir_files, total_files = 0, 0, 0
        for filename in glob(f"{dirname}/*.xml"):
            base = os.path.basename(filename)
            file_id = base.split(".")[0]
            if file_id.endswith("-parscit"):
                file_id = file_id[:-8]
            log.debug(f"Parsing {base}")
            cited_years[file_id], diff = parse_file(filename)
            total_files += 1
            if diff > 0:
                dir_diff += diff
                dir_files += 1
        if dir_diff > 0:
            s_entries = "entries" if dir_diff > 1 else "entry"
            s_dirname = os.path.basename(dirname)
            log.warning(
                f"{s_dirname}: Could not parse dates for {dir_diff} {s_entries} in {dir_files}/{total_files} files"
            )

    cited_count = sum(len(l) for l in cited_years.values())
    log.info(f"Found {cited_count} references with year.")

    with open(args["--csv"], "w", newline="") as csvfile:
        writer = csv.writer(
            csvfile, delimiter="\t", quotechar="|", quoting=csv.QUOTE_MINIMAL
        )
        for file_id, years in cited_years.items():
            pub_year = infer_publication_year(file_id)
            writer.writerow([file_id, pub_year, ",".join(years)])
