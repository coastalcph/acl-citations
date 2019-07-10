#!/bin/bash

shopt -s globstar

PARSCIT=/home/bollmann/repositories/ParsCit/bin/citeExtract.pl
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
LOGFILE="$DIR"/run_parscit_pipeline.log
OUTFILE="$DIR"/../data/acl-parscit.csv

# Data directory
STORAGEDIR=/run/media/bollmann/Intenso/

if [[ -e "$LOGFILE" ]]; then
    rm -f "$LOGFILE"
    touch "$LOGFILE"
fi

# Iterate over all PDF files in the data directory
for pdf in "$STORAGEDIR"/anthology-pdf/**/*.pdf ; do
    filename=$(basename $pdf)
    prefix=$(echo $filename | cut -c1-3)
    echo "$filename" >>"$LOGFILE"

    # Where to store the extracted text files
    txt="$STORAGEDIR"/anthology-txt/$prefix
    mkdir -p $txt
    txt="$txt"/${filename%.pdf}.txt

    # Where to store the parsed citation files
    xml="$STORAGEDIR"/anthology-parscit/$prefix
    mkdir -p $xml
    xml="$xml"/${filename%.pdf}.xml

    # Convert to text
    pdftotext -raw "$pdf" "$txt" >>"$LOGFILE" 2>&1

    # Run ParsCit
    perl -X "$PARSCIT" -m extract_citations "$txt" "$xml" 2>&1 | grep -v "Ignoring json" >>"$LOGFILE"

    # Output a line for the progress bar
    echo 1

done | tqdm --total $(find "$STORAGEDIR"/anthology-pdf -name '*.pdf' | wc -l) --unit file >/dev/null

# Interpret the results
python "$DIR"/parse_tei.py "$STORAGEDIR"/anthology-parscit/* --csv "$OUTFILE" -f parscit
