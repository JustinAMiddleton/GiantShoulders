import pdfquery
from lxml import etree
import os.path
import pprint
import re
import json
import sys


class SimpleLogger:
    def __init__(self, debug=True): self.debug = debug

    def print(self, string):
        if self.debug:
            print(string)


LOG = SimpleLogger()

PAGE_ANOMALIES = {"C:\\Users\\dlf\\Desktop\\codeSearch\\CloneDetection\\Lopes_2017_DuplicationOnGitHub.pdf": [26, 27],
                  "C:\\Users\\dlf\\Desktop\\codeSearch\\CloneDetection\\Zhang_2019_ThesisLeveragingSimilarities.pdf": [182, 202]}
# C:\Users\dlf\Desktop\codeSearch\Search\Ye_2002_Codebrokerprelim.pdf

"""Load the pdf file, staging it for reading."""
def load_file(file):
    global PAGE_ANOMALIES

    pdf = pdfquery.PDFQuery(file)
    if file in PAGE_ANOMALIES:
        pdf.load(PAGE_ANOMALIES[file])
    else:
        pdf.load()

    LOG.print("\tFile loaded")
    return pdf


"""
Input:
    files: list of string filenames
    start: string filename to start with, or None if start from beginning
Output: list of dicts representing each file and its citations
"""
def scrape_files(files, start=None):
    citations = []
    started = start is None
    for pdf_file in files:
        started = started or pdf_file == start
        if not started:
            continue

        citations.append(scrape_file(pdf_file))

    return citations

"""
Scrape an individual file.
Outputs the dict with filename and citations.
"""
def scrape_file(pdf_file):
    LOG.print(pdf_file)

    try:
        pdf = load_file(pdf_file)
    except Exception as e:
        LOG.print("\tCannot load: " + str(e))
        return { "filename": pdf_file, "text": "", "citations": None }

    try:
        page = get_reference_page(pdf)
        citationtext = scrape_text(page)
        citations = scrape_refs(citationtext)
    except Exception as e:
        LOG.print(str(e))
        citationtext = ""
        citations = {}

    citations = fix_missing(citations)
    pdf.file.close()

    return { "filename": pdf_file, "text": citationtext, "citations": citations }


CANDIDATE_SPLITS = [ "REFERENCES", "References" ]
"""Figure out where the reference page begins in the PDF structure.
Return the LTPage object."""
def get_reference_page(pdf):
    # pq queries the pdf structure for an LTPage object that contains my delimiter.
    # Typically, I delimit at a hopefully unique word that designates references.

    ref = None
    for candidate in CANDIDATE_SPLITS:
        ref = pdf.pq("LTPage:contains('%s')" % candidate)
        if ref: break

    if not ref:
        raise Exception("\tget_reference_page: No reference page found. You " \
                        + "probably need more a more accurate word to identify " \
                        + "the reference section.")
    elif len(ref) != 1:
        raise Exception("\tget_reference_page: More than one reference delimiter " \
                        + "found. You probably need a more specific delimiter.")

    return ref

"""Given the LTPage page object, scrape all the text off and until the end of
the paper. Return the string text."""
def scrape_text(page):
    text = page.text()

    for candidate in CANDIDATE_SPLITS:
        text = text.split(candidate)
        if len(text) == 2: break

    if len(text) != 2:
        raise Exception("\tscrape_text: No true delimiter found. You probably "
                        + "a more accurate word to identify the reference section.")

    citationtext = text[-1]
    page = page.next()

    while page:
        citationtext += page.text()
        page = page.next()

    return citationtext

"""Text of citations to dict of discrete citations. Dict instead of list because
this might miss some and be nonsequential."""
def scrape_refs(pagetext):
    pagetext = "\n" + pagetext
    citations = {}

    # hasQuotes = "\u201c" in pagetext # Unicode quotes versus ascii quotes.
    # endsInPeriod = None
    # endsInComma = None

    # First assumption: the citations will follow a numbered format.
    # If first assumption failed, try the unnumbered format.
    styles = [
        CITESTYLE_numbered_bracket,
        CITESTYLE_numbered_dot,
        CITESTYLE_unnumbered
    ]
    for style in styles:
        citations = style(pagetext)
        # print(citations)
        if citations: break

    if not citations:
        LOG.print("\tNo citations found!")

    return citations

def CITESTYLE_numbered_bracket(pagetext):
    citations = {}
    numbered_cite_pattern = r'\[(\d+)\]\s([^\[]+)'
    for ref in re.finditer(numbered_cite_pattern, pagetext):
        idx = int(ref.group(1))
        cite = ref.group(2)
        citations[idx] = cite.strip()
    return citations

def CITESTYLE_numbered_dot(pagetext):
    citations = {}
    number = r"\n(\d{1,2})\.\s"
    numbered_cite_pattern = r'%s((?:.|\n)+?)(?=%s)' % (number, number)
    pagetext += "\n99. " # A dummy ending flag.

    print(numbered_cite_pattern)

    for ref in re.finditer(numbered_cite_pattern, pagetext, re.MULTILINE):
        idx = int(ref.group(1))
        cite = ref.group(2)
        citations[idx] = cite.strip()
    return citations

def CITESTYLE_unnumbered(pagetext):
    citations = {}
    authorlist = r'\n\D+?\.\s\d{4}\.'
    refs = list(re.finditer(authorlist, pagetext))
    for idx, ref in enumerate(refs, 1):
        start = ref.span()[0]
        end = refs[idx + 1].span()[0] if idx + \
            1 < len(refs) else len(pagetext)
        citations[idx] = pagetext[start:end]
    return citations

# This doesn't get all the citations as cleanly as it would like.
# Often, the citation is just included with the one before or after it.
def fix_missing(citations):
    missing = 0
    for baseexpect, actual in enumerate(sorted(citations.keys()), 1):
        expected = baseexpect + missing
        if actual > expected:
            missinglist = list(range(expected, actual))
            missinghere = len(missinglist)
            missing += missinghere
            LOG.print("\tMISSING %s" % str(missinglist))

            if expected == 1:
                continue

            # initials = r'(-?[a-zA-Z]\.\s?)+[^.,]+'
            # authors = rf'\n{initials}((,\s{initials})*,\sand\s{initials}[,.])?'

            authors = r'\n\D+(\u201c|http)'
            prevcitation = "\n" + citations[expected - 1]
            newcites = list(re.finditer(authors, prevcitation))

            # Bug: some cases, it's the one after the real one.
            nclen = len(newcites)
            if nclen < missinghere + 1:
                LOG.print("\t\tNot enough.")
            elif nclen > missinghere + 1:
                LOG.print("\t\tToo many.")

            for ncidx, newcite in enumerate(newcites):
                spanstart = newcite.span()[0]
                spanend = newcites[ncidx + 1].span()[0] if (ncidx + 1) < nclen else \
                    len(prevcitation)
                citations[ncidx + expected -
                          1] = prevcitation[spanstart:spanend]

    return citations


"""
Assumes the creation of a file with topics and their reference numbers, like
    Code Search: 1, 65, 4 , 25
    Code Clones: 3,4,5
Input:
    topics: list of strings representing the topics in the file, as above
    citations: the list of numbered citations output by scrape_files
"""
def process_rw(paper, rwfile): # topics, citations):
    name = os.path.basename(paper).split(".")[0]
    with open(rwfile, "r") as infile:
        rwtopics = process_rw(infile.read(), citations)

    topiclist = []
    for topicline in topics.strip().split("\n"):
        topic, refs = topicline.split(":")
        topiclist.append(
            {"topic": topic, "refs": [citations[int(i.strip())] for i in refs.split(",")]})

    with open("rws/RW_%s.txt" % name, "wb") as outfile:
        for topic in rwtopics:
            outfile.write(topic["topic"].encode("utf8") + b":\n")
            for ref in topic["refs"]:
                outfile.write(b"\t- ")
                outfile.write(ref.replace("\n", "\n\t\t").encode("utf8"))
                outfile.write(b"\n")
            outfile.write(b"\n")

"""
Wrapper for dual printout functions: txt and json.
"""
def print_files(filename, text, citations):
    outfilename = ".\\cites\\" + os.path.basename(filename).split(".")[0]

    with open(outfilename + ".txt", "w", encoding="utf8") as outfile:
        outfile.write(text)

    with open(outfilename + ".json", "w") as outfile:
        json.dump(citations, outfile, indent=2, separators=(',', ': '))

"""
Wrapper function.
"""
def walk_files(sourcedir, ext=".pdf"):
    return [os.path.join(dirpath, file)
            for dirpath, dir, files in os.walk(sourcedir)
            for file in files
            if file.endswith(ext)]

if __name__ == "__main__":
    if len(sys.argv) == 1:
        file = ["C:\\Users\\dlf\\Dropbox\\CodeSearchLiterature\\Examples\\Glassman_2018_Exemplore.pdf"]
        # raise Exception("Need a file to analyze.")
    else:
        file = [sys.argv[1]]

    citations = scrape_files(file)[0]
    print_files(**citations)

    if len(sys.argv) > 2:
        pass

def analysis():
    names = set(os.path.basename(name)[:-4] for name in papers)  # expect .pdf
    jsons = walk_files(".\\cites", ".json")
    unprocessed = [name for name in jsons if os.path.basename(name)[
        :-5] not in names]

    empties = []
    missings = []
    for j in jsons:
        citations = json.loads(open(j).read())
        if not citations:
            empties.append(j)
            continue

        missingcites = []
        missingno = 0
        for actual, baseexpected in enumerate(sorted(map(int, citations.keys())), 1):
            expected = int(baseexpected) + missingno
            if expected < actual:
                missingcites.extend(range(expected, actual))
        if missingcites:
            missings.append((j, missingcites))

    LOG.print(unprocessed)
    LOG.print(empties)
    LOG.print(missings)
