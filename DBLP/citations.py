import pandas as pd
import requests
import re
import logging 
import subprocess

log_format = logging.Formatter(
    "[%(asctime)s][%(filename)s:%(lineno)4s - %(funcName)10s()] %(message)s"
)
logger = logging.getLogger('logger')
ch = logging.StreamHandler()
ch.setFormatter(log_format)
ch.setLevel(logging.INFO)
logger.addHandler(ch)

def file_preparation():
    erc_df = pd.read_excel('../data/NUCAR-ERC-list.xlsx')
    pc_df = pd.read_excel('../data/NUCAR-PC-list.xlsx')

    pc_df['name'] = pc_df['first'] + ' ' + pc_df['last']
    erc_df['name'] = erc_df['first'] + ' ' + erc_df['last']
    pc_df['dblp'] = ''
    pc_df['google_scholar'] = ''
    erc_df['dblp'] = ''
    erc_df['google_scholar'] = ''


    # find google scholar URLs
    def get_scholar_url(name):
        first, last = name.split(' ')
        res = requests.get('https://scholar.google.com/citations?hl=en&view_op=search_authors&mauthors=%s+%s' %(first, last))

        match = re.search('\w+(?="><span class=\'gs_hlt\'>%s %s)' % (first, last), res.text)
        if match is None:
            logger.error("cannot find google scholar profile for %s %s" % (first, last))
            return ""
        scholar_profile = 'https://scholar.google.com/citations?hl=en&user=%s' % match.group(0)
        return scholar_profile

    # find dblp URLs
    def get_dblp_url(name):
        first, last = name.split(' ')
        res = requests.get('https://dblp.uni-trier.de/search?q=%s%%20%s' % (first, last))

        re_match = re.search('Exact matches', res.text)
        try:
            _, end = re_match.span()
            exact_re_match = re.search('(?<=<a href=")\w+://dblp.uni-trier.de/pid/\d+/\d+', res.text[end:])
            if exact_re_match is None:
                logger.error("cannot find dblp match for %s %s" % (first, last))
        except Exception as e:
            logger.error("cannot find dblp match for %s %s" % (first, last))
            return ""
        return exact_re_match.group(0)

    for idx, name in enumerate(pc_df['name']):
        url = get_dblp_url(name)
        scholar = get_scholar_url(name)
        pc_df.loc[idx, 'dblp'] = url
        pc_df.loc[idx, 'google_scholar'] = scholar

    for idx, name in enumerate(erc_df['name']):
        url = get_dblp_url(name)
        scholar = get_scholar_url(name)
        erc_df.loc[idx, 'dblp'] = url
        erc_df.loc[idx, 'google_scholar'] = scholar

    erc_df[['name', 'dblp', 'google_scholar']].to_json('../data/erc.json', orient='records')
    pc_df[['name', 'dblp', 'google_scholar']].to_json('../data/pc.json', orient='records')
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 5000)


def invoke_validation_and_download():
    validate_process = subprocess.run(["python", "dblp.py", "parse-and-check", "--tpc_file", "../data/pc.json", "--erc_file", "../data/erc.json", '--out_file', "../data/validated.json"], stdout=subprocess.PIPE)
    bibtex_process = subprocess.run(["python", "dblp.py", "download-publication", "--pc_file", "../data/validated.json", "--out_file", "../data/bibtex.txt"], stdout=subprocess.PIPE)
    print(validate_process.stdout)


    
if __name__ == '__main__':
    file_preparation()
    invoke_validation_and_download()