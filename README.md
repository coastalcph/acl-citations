# ACL Citations

This repo contains data and code for the paper:

+ Marcel Bollmann and Desmond Elliott (2020). [**On Forgetting to Cite Older
  Papers: An Analysis of the ACL Anthology.**](https://www.aclweb.org/anthology/2020.acl-main.699/)
  In *Proceedings of ACL2020.*

Please use the [official ACL Anthology BibTeX entry](https://www.aclweb.org/anthology/2020.acl-main.699.bib)
to cite this paper, e.g. when you use our dataset.

## Dataset

We include three data files that we base our analysis on:

+ `acl-parscit.tsv` contains the years of papers cited in the References section
  of [ACL Anthology](https://www.aclweb.org/anthology) papers.  It is a TSV file
  with the following columns:

  1. The ACL Anthology ID of the paper we extracted references from.
  2. The year of publication of that paper.
  3. A comma-separated list of years of publications for papers in the
     References section.

+ `citations-all.tsv` additionally contains author/title information for each
  cited paper.  It is a TSV file with one reference entry per line and the
  following columns:

  1. The ACL Anthology ID of the paper the reference is extracted from.
  2. The year of publication *of the extracted reference.*
  3. The author list of the extracted reference.
  4. The title of the extracted reference.

+ `citations-all.matched.tsv` is the result of running `citations-all.tsv`
  through [our fuzzy-matching algorithm](bin/match_cited_papers.py).  It is a
  TSV file with one reference entry per line and the following columns:

  1. An ID for the extracted reference.
  2. The number of times this reference was cited in our dataset.
  3. The year of publication of the extracted reference.
  4. Its author list.
  5. Its title.
  6. A comma-separated list of ACL Anthology IDs of papers that were identified
     as citing this reference.


## Reproducing the pipeline

To reproduce the full pipeline we used, starting from extracting the citation
data from PDFs, here are the steps that you need to take.

### Prerequisites

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


### Running the pipeline

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


## Scripts

Here is a brief overview of included scripts.  All scripts will provide the
`-h/--help` flag to obtain more information about their exact usage.

+ `acl_anthology.py` downloads PDFs from the ACL Anthology based on ID prefixes.

+ `find_cited_papers.py` is used to produce `citations-all.tsv` from the parsed
  ParsCit XML files.

+ `get_paper_counts.py` is used to obtain the number of publications in the
  Anthology, by year and publication venue.  (Used to produce Figure 1 in the
  paper.)

+ `match_cited_papers.py` implements the fuzzy-matching algorithm and is used to
  produce `citations-all.matched.tsv` from the `citations-all.tsv` file.

+ `parse_tei.py` extracts the years of cited papers from the parsed ParsCit XML
  files.

+ `run_parscit_pipeline.sh` is the full extraction pipeline, described above.

+ `summarize_logs.py` is a convenience script to get stats about where and how
  often the extraction process encountered problems.

