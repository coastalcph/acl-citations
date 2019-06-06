# ACL Citations

## Prerequisites

1. Install requirements for Python scripts in this repo:

   `pip install -r requirements.txt`

2. Install GROBID.  The easiest way is via docker:

   `docker pull lfoppiano/grobid:0.5.4_1`

3. Get the following repository as well (should have no additional dependencies):

   `git clone https://github.com/kermitt2/grobid-client-python`


## Running the pipeline

1. Download the desired PDF files from the Anthology by specifying their IDs.
   Wildcards `?` and `*` are allowed.  The following would fetch all long and
   short papers from NAACL 2018:

   `python ./acl_anthology.py fetch 'N18-1*' 'N18-2*'`

   The downloaded files will be in a subfolder `pdf/N18/`.

2. Start the GROBID server (if it's not already running).  Best to do this in a
   separate terminal:

   `docker run -t --rm --init -p 8080:8070 -p 8081:8071 lfoppiano/grobid:0.5.4_1`

3. Run the PDFs through GROBID:

   `mkdir -p tei/N18`
   `python grobid-client-python/grobid-client.py --input pdf/N18 --output tei/N18 --config config.json processReferences`

4. Extract the citation years from the TEI files:

   `python ./parse_tei.py tei/N18/* --csv N18.csv`

`N18.csv` will be a tab-separated file containing the paper ID in the first
column, paper published date in the second column, and a comma-separated list of
years of cited papers in the third column.
