import contextlib
import json
import os
import requests
import re
import logging
from pathlib import Path
from fuzzywuzzy import fuzz

log_format = logging.Formatter(
    "[%(asctime)s][%(filename)s:%(lineno)4s - %(funcName)10s()] %(message)s"
)
logger = logging.getLogger('logger')
ch = logging.StreamHandler()
ch.setFormatter(log_format)
ch.setLevel(logging.INFO)
logger.addHandler(ch)

class OpenAlexClient:
    def __init__(self):
        self.base_url = "https://api.openalex.org" 
        
    def get_author_id_by_title(self, author):
         if "publication" not in author:
             return False, None, None
         publications = author["publication"]
         author_name = author["name"]
         for p in publications:
             pub_title = p["title"]
             pub_title = pub_title.lower()
             pub_title = re.sub(r"\W", " ", pub_title)
             pub_title = re.sub(r" +", " ", pub_title)
             response = requests.get(url="%s/works?filter=title.search:%s'" % (self.base_url, pub_title)).json()
             try:
                 author_list = response["results"][0]['authorships'] 
                 ratio = -float("inf")
                 for a in author_list:
                     curr_ratio = fuzz.ratio(author_name.lower(), a['author']['display_name'].lower())
                     if curr_ratio > ratio:
                         ratio = curr_ratio
                         auid = a['author']['id']
                         daun = a['author']['display_name']
             except Exception as e:
                 logger.error("exception occured while ", e)
                 return False, None, None
         return True, auid, daun
     
     
    def get_pubs_by_author_id(self, author_id, count=10):
        response = requests.get(url="%s/works?filter=author.id:%s&page=1&per-page=%d" % (self.base_url, author_id, count)).json()
        return response["results"]



def get_open_alex_author_ids(out_file, authors):
    client = OpenAlexClient()
    if Path(out_file).exists():
        with open(out_file, "r") as f:
            res = json.load(f)
    else:
        res = {}
    for author in authors:
        status, auid, daun = client.get_author_id_by_title(author)
        author_name = author["name"]
        res_author = {
            "openalex_id": auid,
            "openalex_name": daun,
            "name": author["name"],
            "email": author["email"],
            "dblp": author["dblp"],
            "dblp_origin": author["dblp_origin"],
            "google_scholar": author["google_scholar"],
        }
        if not status:
            logger.info("could not find openalex id for author: %s" % (author['name']))
            res_author["openalex_id"] = ""
            res_author["openalex_name"] = ""
            continue

        res[author_name] = res_author
        print(res_author)
        logger.info(
            f"Author [{author_name:30}] | MAG Id [{auid:10}] | MAG Name [{daun:30}]"
        )

    with open(out_file, "w") as f:
       json.dump(res, f, ensure_ascii=False, indent=4)


def chmkdir(path):
    """Go to working directory and return to previous on exit."""
    prev_cwd = Path.cwd()
    Path(path).mkdir(parents=True, exist_ok=True)
    os.chdir(path)
    os.chdir(prev_cwd)


def download_papers(author_json_file, output_dir, force, num_papers=-1, num_authors=-1, all_authors=True):
    client = OpenAlexClient()
    with open(author_json_file, "r") as f:
        authors = json.load(f)
        authors = [a for _, a in authors.items()]
        if not all_authors:
            authors = authors[:number_of_authors]
    for author in authors:
        out_file = Path(output_dir) / f'{author["name"]}.json'
        if out_file.exists() and not force:
            logger.info(
                f'Found publication records for author [{author["name"]:30}], skipping'
            )
            continue

        auid = author["openalex_id"]
        pubs = client.get_pubs_by_author_id(auid, count=num_papers)
        len_pubs = len(pubs)
        logger.info(f'Got [{len_pubs:4}] publications for [{author["name"]:30}]')
        if len_pubs == 0:
            raise Exception(
                f"Found no publication for author {author}, OpenAlex response {pubs}"
            )
        if len_pubs == num_papers:
            logger.warning(
                f"    Required [{num_papers:4}] publications, "
                f"got [{len_pubs:4}], "
                f"potentially more publications to get"
            )

        with open('%s/%s.json' % (output_dir, author["name"]), "w") as f:
            json.dump(pubs, f, ensure_ascii=False, indent=4)



def init():
    in_file = "../data/bibtex.txt"
    out_file = "../data/mag.json"
    all_authors = True
    with open(in_file, "r") as f:
      authors = json.load(f)
      if not all_authors:
        authors = authors[:number_of_authors]
    if Path(out_file).exists():
        with open(out_file, "r") as f:
            res = json.load(f)
    return authors


if __name__ == '__main__':
    authors = init()
    out_file = '../data/openalex.json'
    get_open_alex_author_ids(out_file, authors)
    output_dir = '../output'
    download_papers(out_file, output_dir, True, num_papers=10)