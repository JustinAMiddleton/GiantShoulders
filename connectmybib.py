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
            "authors": [author.text for author in \
                record.findall("./contributors/authors/author")]
        })
    return papers

def findpaper(author, title):
    try:
        authors = scholarly.search_author(author)
    except StopIteration:
        print("\tNo one by that name...")
        return None

    for fullauthor in authors:
        fullauthor = fullauthor.fill()
        print("\t" + author + " found!")

        authorbib = fullauthor.publications
        try:
            for b in authorbib:
                bibtitle = b.bib["title"]
                if bibtitle.lower() == title.lower():
                    return b.fill()
        except StopIteration:
            continue

    return None


bib = readBib("C:/Users/dlf/git/codesearchcenter/My Collection.xml")
bib = [ { "authors": ["Mel O. Cinneide"], "title": "Impact of stack overflow code snippets on software cohesion: A preliminary study"}]
for paper in bib:
    title = paper["title"]
    print(title)

    for author in paper["authors"][::-1]: #sorted(paper["authors"], key=len, reverse=True):
        author = " ".join(author.split(", ")[::-1])

        scholar = findpaper(author, title)
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
