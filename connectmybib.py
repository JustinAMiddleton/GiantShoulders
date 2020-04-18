import scholarly
import sys
import xml.etree.ElementTree as ET

# read in existing analyzed DB

# read in current bib


def readBib(file):
    papers = []
    tree = ET.parse(file).getroot()
    for record in tree.findall("./records/record"):
        papers.append({
            "title": record.findall("./titles/title")[0].text,
            "authors": [author.text for author in
                        record.findall("./contributors/authors/author")]
        })
    return papers

def findPaper(author, title):
    title = title.lower()

    try:
        authors = scholarly.search_author(author)
    except StopIteration:
        print("\tNo one by that name...")
        return None

    for fullauthor in authors:
        fullauthor = fullauthor.fill()
        print("\tOne " + author + " found! Searching for their paper...")

        authorbib = fullauthor.publications

        try:
            for b in authorbib:
                if b.bib["title"].lower() == title:
                    return b.fill()
        except StopIteration:
            print("\t\t%s has an empty bib!")
            continue

    return None


bib = readBib("C:/Users/jalan/git/GiantShoulders/My Collection.xml")
bib = [{"authors": ["Andy Podgurski"],
        "title": "Retrieving Reusable Software by Sampling Behavior"}]
for paper in bib:
    title = paper["title"]
    print(title)

    # sorted(paper["authors"], key=len, reverse=True):
    for author in paper["authors"][::-1]:
        author = " ".join(author.split(", ")[::-1])

        scholar = findPaper(author, title)
        if scholar is None:
            print("\tNot found...")
        else:
            if hasattr(scholar, "citedby"):
                print("\tCited by %d" % scholar.citedby)
            else:
                print("\tWho knows how cited???")

            citedby = scholar.get_citedby()
            print([x for x in citedby])
            break

# Current failure: empty get_citedby sets.
#   In get_citedby(): hasattr(self, 'id_scholarcitedby') returns false after fill.
#   In fill(): source is citations.
#       key == 'Total citations' is never true for the URL.
#   Nevermind...I was just pinging a document with no cites...
