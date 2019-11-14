#!/usr/bin/env python3

"""
Summarize logs produced by running the ParsCit pipeline.

Usage:
  summarize_logs.py [options]

Options:
  --debug                   Verbose log messages.
  -h, --help                Display this helpful text.
"""

from collections import defaultdict
from docopt import docopt
import logging
import logzero
from logzero import logger as log
import re
import os


SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))


def re_match_group(pattern, string):
    m = re.search(pattern, string)
    if m is not None:
        return m.group(1)
    return False


def gather_pdftotext_log(logfile):
    logs = defaultdict(lambda: defaultdict(int))
    curr_id = None
    for line in logfile:
        line = line.strip()
        if line.endswith(".pdf"):
            curr_id = line[:-4]
        elif "Warning" in line:
            logs[curr_id]["pdftotext_warning"] += 1
        elif "Error" in line:
            logs[curr_id]["pdftotext_error"] += 1
        else:
            log.warning(f"pdftotext log: ignoring message: {line}")

    return logs


def gather_parscit_log(logfile):
    logs = defaultdict(lambda: defaultdict(int))
    pdf_list = []
    curr_id = None
    for line in logfile:
        line = line.strip()
        if line.endswith(".pdf"):
            curr_id = line[:-4]
            pdf_list.append(curr_id)
        elif line.startswith("Die in"):
            logs[curr_id]["parscit_died"] += 1
        elif line.startswith("Citation text longer than article body"):
            logs[curr_id]["parscit_cite_too_long"] += 1
        else:
            logs[curr_id]["parscit_other"] += 1

    return pdf_list, logs


def gather_parsetei_log(logfile):
    logs = defaultdict(lambda: defaultdict(int))
    for line in logfile:
        line = line.strip()
        if line.startswith("[E") or line.startswith("[W"):
            key = re_match_group("] ([^ ]+): ", line)
            assert key
            if key.endswith(".xml"):
                key = key[:-4]

            if "Could not find any" in line:
                logs[key]["tei_no_dates"] += 1
            elif "Could not parse dates for" in line:
                no_date_entries = re_match_group("for ([0-9]+) entries", line)
                if no_date_entries:
                    logs[key]["tei_no_date_entries"] = int(no_date_entries)
                num_files = re_match_group("entries in ([0-9]+)/[0-9]+ files", line)
                if num_files:
                    logs[key]["tei_files_with_probs"] = int(num_files)

    return logs


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = logging.DEBUG if args["--debug"] else logging.INFO
    logzero.loglevel(log_level)
    logzero.formatter(logzero.LogFormatter(datefmt="%Y-%m-%d %H:%M:%S"))

    parsed_logs = {}

    log_pdftotext = f"{SCRIPTDIR}/run_parscit_pipeline.pdftotext.log"
    if not os.path.exists(log_pdftotext):
        log.warning(f"Couldn't find pdf2totext log!  (expected under: {log_pdftotext})")
    else:
        with open(log_pdftotext, "r") as f:
            parsed_logs["pdftotext"] = gather_pdftotext_log(f)

    log_parscit = f"{SCRIPTDIR}/run_parscit_pipeline.parscit.log"
    if not os.path.exists(log_parscit):
        log.error(f"Couldn't find ParsCit log!  (expected under: {log_parscit})")
        exit(1)
    else:
        with open(log_parscit, "r") as f:
            all_ids, parsed_logs["parscit"] = gather_parscit_log(f)

    log_parsetei = f"{SCRIPTDIR}/run_parscit_pipeline.tei.log"
    if not os.path.exists(log_parsetei):
        log.warning(f"Couldn't find parse_tei log!  (expected under: {log_parsetei})")
    else:
        with open(log_parsetei, "r") as f:
            parsed_logs["tei"] = gather_parsetei_log(f)

    failures = set()
    warnings = 0

    for file_id, problems in parsed_logs["parscit"].items():
        # errors that cause no output file to be generated
        if problems["parscit_died"] or problems["parscit_other"]:
            failures.add(file_id)

    for file_id, problems in parsed_logs["tei"].items():
        # top-level stats
        if len(file_id) == 3:
            warnings += problems["tei_files_with_probs"]
        # file parsed, but no dates found
        elif problems["tei_no_dates"]:
            failures.add(file_id)

    log.info(f"              Total files processed: {len(all_ids):6d}")
    log.info(f" Total files w/ date parsing issues: {warnings:6d}")
    log.info(f"Total files that couldn't be parsed: {len(failures):6d}")
    log.warning(f"List of IDs that couldn't be parsed:")
    failures = sorted(failures)
    while failures:
        log.warning("   " + ", ".join(failures[:8]) + ",")
        failures = failures[8:]
