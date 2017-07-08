import sqlite3
import argparse
import os
from pandas import read_sql_query
from re import findall
from psutil import process_iter
from difflib import SequenceMatcher

PROCESS_NAME = 'chrome.exe'
PATH_WINDOWS_VISTA_AND_LATER = 'C:\\Users\\' + os.getenv(
    'username') + '\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\'
PATH_WINDOWS_XP = 'C:\\Documents and Settings\\' + os.getenv(
    'username') + '\\Application Support\\Google\\Chrome\\Default\\'
PATH_MAC_OS_X = '~/Library/Application Support/Google/Chrome/Default/'
PATH_LINUX = '~/.config/google-chrome/Default/'

DATA_FILES = ['History', 'Favicons', 'Cookies', 'Top Sites',
              'Visited Links', 'Web Data', 'Shortcuts', 'Last Session',
              'Last Tabs', 'Network Action Predictor', 'Current Tabs',
              'Preferences', 'Current Session', 'TransportSecurity',
              'TransportSecurity', 'Login Data', 'Origin Bound Certs',
              'Bookmarks', 'QuotaManager', 'Extension Cookies']

ALL_FILES = set([])


def generate_all_files(path):
    global ALL_FILES
    for root, dirs, files in os.walk(path):
        ALL_FILES = ALL_FILES.union(files)


def fuzzy_search(name1, name2, strictness):
    similarity = SequenceMatcher(None, name1, name2)
    return similarity.ratio() > strictness


def kill_process():
    for p in process_iter():
        if fuzzy_search(p.name(), PROCESS_NAME, 0.9):
            p.kill()


def get_os_path(os):
    return {
        'WINDOWS10': PATH_WINDOWS_VISTA_AND_LATER,
        'WINDOWS7': PATH_WINDOWS_VISTA_AND_LATER,
        'WINDOWSVISTA': PATH_WINDOWS_VISTA_AND_LATER,
        'WINDOWSXP': PATH_WINDOWS_XP,
        'MAC': PATH_MAC_OS_X,
        'LINUX': PATH_LINUX
    }.get(os, 'WINDOWS10')


def generate_urls(path, files):
    urls = set([])
    counter = 0
    for f in files:
        try:
            counter += 1
            if not (counter % (len(files) / 10)):
                print "*LOGGING*\tgenerate_urls: {}%".format((float(counter) / len(files)) * 100)

            db = sqlite3.connect(path + f)
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
                # print 'File:{:15}Success'.format(f)
        except sqlite3.DatabaseError, e:
            print '*LOGGING*\tgenerate_urls: {:30}File: {:30}Failed: {:30}'.format(
                str((float(counter) / len(files)) * 100) + '%', f,
                e)
    print "*LOGGING*\tgenerate_urls: {}%".format(100.0)
    return urls


def dump_data(os, kill_chrome, deep):
    if kill_chrome:
        kill_process()
    path = get_os_path(os=os.upper())
    if deep:
        generate_all_files(path=path)
        urls = generate_urls(path=path, files=ALL_FILES)
    else:
        urls = generate_urls(path=path, files=DATA_FILES)

    with open('chrome_urls.txt', 'w') as f:
        for url in urls:
            f.write("%s\n" % url)
        print "*LOGGING*\tdump_data: {:5}%".format(100.0)


def main(os, kill_chrome, deep):
    dump_data(os=os, kill_chrome=kill_chrome, deep=deep)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Dump urls from GoogleChrome Browser databases')
    parser.add_argument('-o', '--os', type=str, help='operating system', required=True, dest='os')
    parser.add_argument('-k', '--kill', type=bool, help='kill chrome process', required=False, default=False,
                        dest='kill_chrome')
    parser.add_argument('-d', '--deep', type=bool, help='deep dump', required=False, default=False, dest='deep')
    args = parser.parse_args()

    main(**vars(args))
