import json
import scholarly
import sys
import xml.etree.ElementTree as ET

class SimpleLogger:
    def __init__(self, debug=True): self.debug = debug
    def print(self, string):
        if self.debug: print(string)
LOG = SimpleLogger()

"""paper: list of dicts with "authors" list and "title" string."""
def findCitedBy(paper):
    title = paper["title"]
    LOG.print(title)

    # I reverse because: in an author's list, younger researchers go up front
    #   and might be less often to have a Scholar profile.
    #   Elder researchers go in the back, often.
    # sorted(paper["authors"], key=len, reverse=True):

    for author in paper["authors"][::-1]:
        # TODO: Names arrive in that Robertson, Bob form. Will middle initials
        #   interfere?
        author = " ".join(author.split(", ")[::-1])
        scholar = findPaper(author, title)

        if scholar is None:
            LOG.print("\tNot found...")
        else:
            if hasattr(scholar, "citedby"):
                LOG.print("\tCited by %d" % scholar.citedby)
            else:
                LOG.print("\tWho knows how cited???")

            citedby = scholar.get_citedby()
            return citedby

    return None

"""Both parameters "author" and "title" are strings."""
def findPaper(author, title):
    title = title.lower()

    try:
        authors = scholarly.search_author(author)
    except StopIteration:
        LOG.print("\tNo one by that name...")
        return None

    for fullauthor in authors:
        fullauthor = fullauthor.fill()
        LOG.print("\tOne " + author + " found! Searching for their paper...")
        authorbib = fullauthor.publications

        try:
            for b in authorbib:
                if b.bib["title"].lower() == title:
                    return b.fill()
        except StopIteration:
            LOG.print("\t\t%s has an empty bib!")  # I need a test case.
            continue

    return None


def readMendeleyBib(filepath):
    papers = []
    tree = ET.parse(filepath).getroot()
    for record in tree.findall("./records/record"):
        papers.append({
            "title": record.findall("./titles/title")[0].text,
            "authors": [author.text for author in
                        record.findall("./contributors/authors/author")]
        })
    return papers


if __name__ == "__main__":
    """I can export from Mendeley with the below comment if I want all papers.
    This is not at all feasible with Scholar's rate limits."""
    # testbib = readMendeleyBib("C:/Users/dlf/git/GiantShoulders/My Collection.xml")

    testbib = [{"authors": ["Matt Staats", "Gregg Rothermel"],
                "title": "Understanding User Understanding: Determining Correctness of Generated Program Invariants"}]

    for paper in testbib:
        citedby = findCitedBy(paper)
        
        # TODO: Broken here, type 'Publication' is not iterable.
        paper["citedby"] = [{"authors": paper["authors"] if "authors" in paper else "",
                             "title": paper["title"] if "title" in paper else "",
                             "year": paper["year"] if "year" in paper else "",
                             "journal": paper["journal"] if "journal" in paper else "",
                             "citedby": paper.citedby
                             } for paper in citedby]

        json_outfile = "./citedby/" + "".join(x if x.isalnum() else "_" for x in paper["title"]) + ".json"
        with open(json_outfile, "w+") as outfile:
            json.dump(paper, outfile, indent=2, separators=(',', ': '))

SAMPLEBIB = [{"authors": ["Andy Podgurski"],
              "title": "Retrieving Reusable Software by Sampling Behavior"}]

# Current failure: I do ONE of these queries and Scholar doesn't like it! 😡
#   I don't think there's a way around it; they don't want scraping like I'm
#       trying to do, even though it's through a library.

# Current failure: empty get_citedby sets.
#   In get_citedby(): hasattr(self, 'id_scholarcitedby') returns false after fill.
#   In fill(): source is citations.
#       key == 'Total citations' is never true for the URL.
#   Nevermind...I was just pinging a document with no cites...
