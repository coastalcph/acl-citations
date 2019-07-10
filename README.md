# ACL Citations

## Prerequisites

1. Install requirements for Python scripts in this repo:

   `pip install -r requirements.txt`

2. **Install ParsCit.**

   a. Clone the [ParsCit repository](https://github.com/knmnyn/ParsCit).

   b. Install the following **Perl libraries:**

      ```
      cpan install XML::Twig
      cpan install XML::Writer
      cpan install XML::Writer::String
      ```

      These are the ones most likely to not be installed on your system by
      default, but a full list can be found in [ParsCit's installation
      instructions](https://github.com/knmnyn/ParsCit/blob/master/INSTALL).

   c. **Install CRF++.** The ParsCit repo comes with version 0.51, which didn't
      compile on my system, so I downloaded the most recent version 0.58 instead
      from [the CRF++ website](https://taku910.github.io/crfpp/).

      Basically, you need to compile CRF++ from scratch and then copy some
      compiled files to the ParsCit directory:

      `cp -Rf crf_learn crf_test .libs ParsCit/crfpp/`

   d. You should now be able to run ParsCit, which you can try by `cd`ing to
      `ParsCit/bin` and running:

      `./citeExtract.pl -m extract_all ../demodata/sample2.txt`


## Running the pipeline

1. Download the desired PDF files from the Anthology by specifying their IDs.
   Wildcards `?` and `*` are allowed.  The following would fetch all long and
   short papers from NAACL 2018:

   `python ./acl_anthology.py fetch 'N18-1*' 'N18-2*'`

   The downloaded files will be in a subfolder `pdf/N18/`.

2. Convert the PDFs to text, e.g.:

   `find pdf/ -name '*.pdf' -exec pdftotext -raw "{}" "{}.txt" \;`

   (If the PDFs do not have embedded text, a full OCR pipeline would be required
   here, but we're only dealing with PDF files that do have text.)

3. Run the text files through ParsCit:

   `find pdf/ -name '*.txt' -exec perl -X ./citeExtract.pl -m extract_citations "{}" "{}.xml" \;`

   (The `-X` flag prevents you from getting spammed with countless deprecation
   warnings that will probably appear...)

4. Extract the citation years from the parsed XML files:

   `python ./parse_tei.py pdf/* --csv N18.csv -f parscit`

`N18.csv` will be a tab-separated file containing the paper ID in the first
column, paper published date in the second column, and a comma-separated list of
years of cited papers in the third column.

**_Note:_ Steps 2--4 are also implemented in the script
`bin/run_parscit_pipeline.sh`,** which might be a better starting point for
actually running this.


## Old instructions using the GROBID pipeline

To run this using GROBID instead of ParsCit, do the following:

1. Install GROBID.  The easiest way is via docker:

   `docker pull lfoppiano/grobid:0.5.4_1`

2. Get the following repository as well (should have no additional dependencies):

   `git clone https://github.com/kermitt2/grobid-client-python`

3. Start the GROBID server (if it's not already running).  Best to do this in a
   separate terminal:

   `docker run -t --rm --init -p 8080:8070 -p 8081:8071 lfoppiano/grobid:0.5.4_1`

4. Run the downloaded PDFs through GROBID:

   `mkdir -p tei/N18`

   `python grobid-client-python/grobid-client.py --input pdf/N18 --output tei/N18 --config config.json processReferences`

Then parse them as above.
