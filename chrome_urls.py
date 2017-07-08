import sqlite3
from os import getenv
from pandas import read_sql_query
from re import findall
from psutil import process_iter
from difflib import SequenceMatcher

PROCESS_NAME = 'chrome.exe'
PATH = 'C:\\Users\\' + getenv('username') + '\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\'
DATA_FILES = ['History', 'Favicons', 'Cookies', 'Top Sites',
              'Visited Links', 'Web Data', 'Shortcuts', 'Last Session',
              'Last Tabs', 'Network Action Predictor', 'Current Tabs',
              'Preferences', 'Current Session', 'TransportSecurity',
              'TransportSecurity', 'Login Data', 'Origin Bound Certs',
              'Bookmarks', 'QuotaManager', 'Extension Cookies']


def fuzzy_search(name1, name2, strictness):
    similarity = SequenceMatcher(None, name1, name2)
    return similarity.ratio() > strictness


def kill_chrome():
    for p in process_iter():
        if fuzzy_search(p.name(), PROCESS_NAME, 0.9):
            p.kill()


def dump_data():
    urls = set([])
    for f in DATA_FILES:
        try:
            db = sqlite3.connect(PATH + f)
            cursor = db.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for table_name in tables:
                table_name = table_name[0]
                table = read_sql_query("SELECT * from %s" % table_name, db)
                new_urls = findall(
                    '[\d\w/.-:]+[\.][a-zA-Z][\d\w/.-]+[-/, ]',
                    table.to_string())
                urls = urls.union(new_urls)
            print 'File:{:35}Success'.format(f)
        except sqlite3.DatabaseError, e:
            print 'File:{:35}Failed:{:35}'.format(f, e)
    with open('chrome_urls.txt', 'w') as f:
        for url in urls:
            f.write("%s\n" % url)


def main():
    kill_chrome()
    dump_data()


if __name__ == '__main__':
    main()
