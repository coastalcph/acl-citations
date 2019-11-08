#!/bin/bash

shopt -s globstar

PARSCIT=/home/bollmann/repos/ParsCit/bin/citeExtract.pl
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
LOGFILE_PDF="$DIR"/run_parscit_pipeline.pdftotext.log
LOGFILE_CIT="$DIR"/run_parscit_pipeline.parscit.log
LOGFILE_TEI="$DIR"/run_parscit_pipeline.tei.log
OUTFILE="$DIR"/../data/acl-parscit.csv

# Data directory
STORAGEDIR=/run/media/bollmann/Intenso/

for LOGFILE in "$LOGFILE_PDF" "$LOGFILE_CIT" "$LOGFILE_TEI"; do
    if [[ -e "$LOGFILE" ]]; then
        rm -f "$LOGFILE"
        touch "$LOGFILE"
    fi
done

PREFIXES=( D10 D11 D12 D13 D14 D15 D16 D17 D18 D19-1 E1 J1 N1 P1 Q1 )
TOTAL=0

for prefix in "${PREFIXES[@]}"; do
    (( TOTAL += $(find "$STORAGEDIR"/anthology-pdf -name '*.pdf' -name "$prefix"'*' | wc -l) ))
done

# Iterate over all PDF files in the data directory
for pdf in "$STORAGEDIR"/anthology-pdf/**/*.pdf ; do
    filename=$(basename $pdf)

    match_file=0
    for prefix in "${PREFIXES[@]}"; do
        if [[ $filename == "$prefix"* ]]; then
            match_file=1
            break
        fi
    done
    if [[ $match_file == 0 ]]; then
        continue
    fi

    prefix=$(echo $filename | cut -c1-3)
    echo "$filename" >>"$LOGFILE_PDF"
    echo "$filename" >>"$LOGFILE_CIT"

    # Where to store the extracted text files
    txt="$STORAGEDIR"/anthology-txt/$prefix
    mkdir -p $txt
    txt="$txt"/${filename%.pdf}.txt

    # Where to store the parsed citation files
    xml="$STORAGEDIR"/anthology-parscit/$prefix
    mkdir -p $xml
    xml="$xml"/${filename%.pdf}.xml

    # Convert to text
    pdftotext -raw "$pdf" "$txt" >>"$LOGFILE_PDF" 2>&1

    # Run ParsCit
    perl -X "$PARSCIT" -m extract_citations "$txt" "$xml" 2>&1 | grep -v "Ignoring json" >>"$LOGFILE_CIT"

    # Output a line for the progress bar
    echo 1

done | tqdm --total $TOTAL --unit file >/dev/null

# Interpret the results
python "$DIR"/parse_tei.py "$STORAGEDIR"/anthology-parscit/* --csv "$OUTFILE" -f parscit --log "$LOGFILE_TEI"
