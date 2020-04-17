import pdfquery
from lxml import etree
import os.path
import re
from pprint import pprint
import json
import sys

# Has a different format
problematics = {"C:\\Users\\dlf\\Desktop\\codeSearch\\CloneDetection\\Lopes_2017_DuplicationOnGitHub.pdf": [26,27],
    "C:\\Users\\dlf\\Desktop\\codeSearch\\CloneDetection\\Zhang_2019_ThesisLeveragingSimilarities.pdf": [182,202]}
# C:\Users\dlf\Desktop\codeSearch\Search\Ye_2002_Codebrokerprelim.pdf
def loadFile(file):
    global problematics
    pdf = pdfquery.PDFQuery(file)
    if file in problematics:
        pdf.load(problematics[file])
    else:
        pdf.load()
    print("\tloaded")
    return pdf

def getReferencePage(pdf, split_on = "REFERENCES"):
    # find references
    ref = pdf.pq("LTPage:contains('%s')" % split_on)
    if not ref:
        ref = pdf.pq("LTPage:contains('%s')" % split_on.title())

    if len(ref) != 1:
        pass #raise Exception("\tWOMP WOMP")

    return ref

def scrapeText(page, split_on = "REFERENCES"):
    citationtext = ""

    text = page.text()
    text = text.split(split_on)
    assert(len(text) == 2)
    citationtext += text[-1]
    page = page.next()

    while page:
        citationtext += page.text()
        page = page.next()

    return citationtext

def scrapeRefs(pagetext):
    hasQuotes = "\u201c" in pagetext
    endsInPeriod = None
    endsInComma = None

    pagetext = "\n" + pagetext
    citations = {}
    numbered_cite_pattern = r'\[(\d+)\]\s([^\[]+)'
    for ref in re.finditer(numbered_cite_pattern, pagetext):
        idx = int(ref.group(1))
        cite = ref.group(2)
        citations[idx] = cite.strip()

    if not citations:
        print("\tNo citations found first try!")
        authorlist = r'\n\D+?\.\s\d{4}\.'
        refs = list(re.finditer(authorlist, pagetext))
        for idx, ref in enumerate(refs, 1):
            start = ref.span()[0]
            end = refs[idx+1].span()[0] if idx+1 < len(refs) else len(pagetext)
            citations[idx] = pagetext[start:end]

    if not citations:
        print("\tNo citations found second try!")

    return citations

def fixMissing(citations):
    missing = 0
    for baseexpect, actual in enumerate(sorted(citations.keys()), 1):
        expected = baseexpect + missing
        if actual > expected:
            missinglist = list(range(expected, actual))
            missinghere = len(missinglist)
            missing += missinghere
            print("\tMISSING %s" % str(missinglist))

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
                print("\t\tNot enough.")
            elif nclen > missinghere + 1:
                print("\t\tToo many.")

            for ncidx, newcite in enumerate(newcites):
                spanstart = newcite.span()[0]
                spanend = newcites[ncidx + 1].span()[0] if (ncidx+1) < nclen else \
                    len(prevcitation)
                citations[ncidx + expected - 1] = prevcitation[spanstart:spanend]

    return citations

def printFiles(filename, citationtext, citations, out_dir = ".\\cites\\"):
    outfilename = os.path.basename(filename).split(".")[0]
    with open(out_dir + outfilename + ".txt", "w") as outfile:
        json.dump(citationtext, outfile)

    with open(out_dir + outfilename + ".json", "w") as outfile:
        json.dump(citations, outfile, indent=2, separators=(',', ': '))

def scrapeFilesNew(pdf_files, start = None):
    started = start is None
    for pdf_file in pdf_files:
        started = started or pdf_file == start
        if not started:
            continue

        try:
            print(pdf_file)
            pdf = loadFile(pdf_file)
        except Exception as e:
            print("\tCannot load: " + str(e))
            printFiles(pdf_file, "", {})
            continue

        citationtext = ""
        citations = {}
        try:
            page = getReferencePage(pdf)
            citationtext = scrapeText(page)
            citations = scrapeRefs(citationtext)
        except Exception as e:
            print(str(e))

        citations = fixMissing(citations)
        printFiles(pdf_file, citationtext, citations)
        pdf.file.close()

def walkFiles(sourcedir = "C:\\Users\\dlf\\Desktop\\codeSearch", ext = ".pdf"):
    return [os.path.join(dirpath,file) \
        for dirpath, dir, files in os.walk(sourcedir) \
        for file in files \
        if file.endswith(ext)]

def freshScrape():
    start = "C:\\Users\\dlf\\Desktop\\codeSearch\\CloneDetection\\Kim_2018_FaCoY_CodeToCodeSearch.pdf"
    files = walkFiles()
    scrapeFilesNew(files, start)

if __name__=="__main__":
    freshScrape()
    sys.exit(0)

    papers = walkFiles()
    names = set(os.path.basename(name)[:-4] for name in papers) #expect .pdf

    jsons = walkFiles(".\\cites", ".json")
    unprocessed = [name for name in jsons if os.path.basename(name)[:-5] not in names]

    empties = []
    missings = []
    for j in jsons:
        citations = json.loads(open(j).read())
        if not citations:
            empties.append(j)
            continue

        missingcites = []
        missingno = 0
        for actual, baseexpected in enumerate(sorted(map(int,citations.keys())), 1):
            expected = int(baseexpected) + missingno
            if expected < actual:
                missingcites.extend(range(expected, actual))
        if missingcites:
            missings.append((j,missingcites))

    pprint(unprocessed)
    pprint(empties)
    print(missings)
