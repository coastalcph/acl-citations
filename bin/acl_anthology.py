#!/usr/bin/env python3

"""
Download files from the ACL Anthology.

Usage:
  acl_anthology.py -h
  acl_anthology.py update
  acl_anthology.py (match|fetch) <expr>... [options]

Arguments:
  <expr>                   Expression specifying an ACL Anthology ID;
                           may contain ? and * wildcards.

Options:
  -d, --destination DIR    Directory to save files to [default: {SCRIPTDIR}/pdf].
  -n, --dry-run            Don't download files.
  --debug                  Verbose log messages.
  -h, --help               Display this helpful text.
"""

from docopt import docopt
import better_exceptions
from glob import glob
import logging
import logzero
from logzero import logger as log
from lxml import etree
import os
import re
import requests
import time
from tqdm import tqdm


ACL_REPO = "https://github.com/acl-org/acl-anthology"
ANTHOLOGY_URL = "https://www.aclweb.org/anthology/{}.pdf"
SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))


def update_acl_repo(repo_dir, force=False):
    from datetime import datetime, timedelta
    from git import Repo

    repo_token = os.path.join(repo_dir, ".pulled")

    if not os.path.exists(repo_dir):
        os.mkdir(repo_dir)
        log.info("Fetching Anthology metadata...")
        repo = Repo.clone_from(ACL_REPO, repo_dir, branch="master")
        with open(repo_token, "a"):
            os.utime(repo_token, None)
        delta = timedelta(hours=0)
    elif os.path.exists(repo_token):
        delta = datetime.now() - datetime.fromtimestamp(os.path.getmtime(repo_token))
        log.debug(
            "Last checked for metadata updates: {} ago".format(
                ":".join(str(delta).split(":")[:2])
            )
        )
    else:
        delta = timedelta.max

    repo = Repo(repo_dir)
    if force or delta > timedelta(hours=24):
        log.info("Checking Anthology metadata for updates...")
        repo.remotes.origin.pull()
        with open(repo_token, "a"):
            os.utime(repo_token, None)
    else:
        log.info("Anthology metadata is up-to-date.")


def build_anthology_id(collection_id, volume_id, paper_id=None):
    """
    Transforms collection id, volume id, and paper id to a width-padded
    Anthology ID. e.g., ('P18', '1', '1') -> P18-1001.
    """
    if (
        collection_id.startswith("W")
        or collection_id == "C69"
        or (collection_id == "D19" and int(volume_id) >= 5)
    ):
        anthology_id = f"{collection_id}-{int(volume_id):02d}"
        if paper_id is not None:
            anthology_id += f"{int(paper_id):02d}"
    else:
        anthology_id = f"{collection_id}-{int(volume_id):01d}"
        if paper_id is not None:
            anthology_id += f"{int(paper_id):03d}"

    return anthology_id


def match_ids(ids):
    map_to_prefix = lambda x: x[: x.find("*") + 1] if "*" in x[:3] else x[:3]
    map_to_regex = lambda x: x.replace("?", ".").replace("*", ".+")

    id_regex = "|".join(map_to_regex(x) for x in ids)
    id_pattern = re.compile(id_regex)
    file_regex = "|".join(map_to_regex(map_to_prefix(x)) for x in ids)
    file_pattern = re.compile(file_regex)

    matched = []
    for xmlfile in glob(f"{SCRIPTDIR}/.anthology-repo/data/xml/*.xml"):
        prefix = os.path.basename(xmlfile)[:3]
        if file_pattern.match(prefix) is None:
            continue
        log.debug(f"Parsing file: {xmlfile}")
        tree = etree.parse(xmlfile)
        for volume in tree.getroot().findall(".//volume"):
            volume_id = volume.get("id")
            for paper in volume.findall(".//paper"):
                paper_id = paper.get("id")
                full_id = build_anthology_id(prefix, volume_id, paper_id)
                if id_pattern.match(full_id) is None:
                    continue
                log.debug(f"Matched: {full_id}")
                url = paper.findtext("url")
                if url is None:
                    url = paper.findtext("pdf")
                if url is None:
                    log.warn(f"Couldn't find PDF for matched entry: {full_id}")
                    continue
                if not url.startswith("http"):
                    url = ANTHOLOGY_URL.format(full_id)
                matched.append((full_id, url))

    log.info(
        f"Found {len(matched)} matching {'entry' if len(matched)==1 else 'entries'}."
    )
    return matched


def check_ids(ids, destdir, force=False):
    checked = []
    for full_id, url in ids:
        local_file = f"{destdir}/{full_id[:3]}/{full_id}.pdf"
        if not force and os.path.exists(local_file):
            continue
        if not os.path.exists(os.path.dirname(local_file)):
            os.makedirs(os.path.dirname(local_file))
        checked.append((full_id, url, local_file))

    if len(checked) < len(ids):
        log.info(f"Skipping download of {len(ids) - len(checked)} files.")

    return checked


def download_ids(ids):
    log.info(f"Downloading {len(entries)} {'file' if len(entries)==1 else 'files'}...")
    progress = tqdm(total=len(entries), unit="files")
    for i, (full_id, url, local_file) in enumerate(entries):
        progress.set_description_str(f"{full_id} ")
        for _ in range(5):
            try:
                h = requests.head(url, allow_redirects=True)
            except Exception as e:
                progress.write(f"{full_id}: HEAD caused exception '{str(e)}'")
                time.sleep(5)
                continue
            content_type = h.headers.get("content-type")
            if "pdf" not in content_type.lower():
                progress.write(f"{url} is not a PDF file (got: {content_type})")
                break
            else:
                try:
                    r = requests.get(url, allow_redirects=True)
                except Exception as e:
                    progress.write(f"{full_id}: GET caused exception '{str(e)}'")
                    time.sleep(5)
                    continue
                if r.status_code == requests.codes.ok:
                    with open(local_file, "wb") as f:
                        f.write(r.content)
                    break
                else:
                    progress.write(f"{full_id}: received HTTP status {r.status_code}")
        else:
            progress.write(f"{full_id}: giving up")
        progress.update()
        # if (i+1) % 50 == 0:
        #    tqdm.write(f"Downloaded {i+1:4d} files -- pausing for 10 seconds")
        #    time.sleep(10)
    progress.close()


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = logging.DEBUG if args["--debug"] else logging.INFO
    logzero.loglevel(log_level)
    logzero.formatter(logzero.LogFormatter(datefmt="%Y-%m-%d %H:%M:%S"))

    update_acl_repo(f"{SCRIPTDIR}/.anthology-repo", force=args["update"])
    if args["match"] or args["fetch"]:
        entries = match_ids(args["<expr>"])
    if args["fetch"]:
        destdir = args["--destination"]
        if "{SCRIPTDIR}" in destdir:
            destdir = destdir.replace("{SCRIPTDIR}", SCRIPTDIR)
        entries = check_ids(entries, destdir)
        if entries and not args["--dry-run"]:
            download_ids(entries)
