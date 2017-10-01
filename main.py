import sqlite3
import argparse
import os
from pandas import read_sql_query
from re import findall
import psutil
from difflib import SequenceMatcher
import win32crypt
import json
import platform


def investigate_dbs(terminate_chrome, deep):
    if terminate_chrome:
        kill_process()
    chrome_dbs_path = get_os_path()

    with open('chrome_downloads.json', 'w') as f:
        print "dump_downloads"
        f.write(json.dumps(dump_downloads(path=chrome_dbs_path)))
        f.flush()
    with open('chrome_user_pass.json', 'w') as f:
        print "dump_user_pass"
        f.write(json.dumps(dump_user_pass(path=chrome_dbs_path)))
        f.flush()
    with open('chrome_users.json', 'w') as f:
        print "dump_users"
        f.write(json.dumps(dump_users(path=chrome_dbs_path)))
        f.flush()

    if deep:
        chrome_files = generate_all_files(path=chrome_dbs_path)
        urls = generate_urls(path=chrome_dbs_path, files=chrome_files)
    else:
        chrome_db_files = ['History', 'Favicons', 'Cookies', 'Top Sites',
                           'Visited Links', 'Web Data', 'Shortcuts', 'Last Session',
                           'Last Tabs', 'Network Action Predictor', 'Current Tabs',
                           'Preferences', 'Current Session', 'TransportSecurity',
                           'TransportSecurity', 'Login Data', 'Origin Bound Certs',
                           'Bookmarks', 'QuotaManager', 'Extension Cookies']
        urls = generate_urls(path=chrome_dbs_path, files=chrome_db_files)

    with open('chrome_urls.txt', 'w') as f:
        for url in urls:
            f.write('{}\n'.format(url))
        print "*LOGGING*\tdump_data: {:5}%".format(100.0)


def generate_all_files(path):
    chrome_files = set([])
    for root, dirs, files in os.walk(path):
        chrome_files = chrome_files.union(files)
    return chrome_files


def dump_user_pass(path):
    data = ([], [])
    conn = sqlite3.connect(os.path.join(path, 'Login Data'))
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
    conn = sqlite3.connect(os.path.join(path, 'Login Data'))
    cursor = conn.cursor()
    cursor.execute(
        'SELECT username_value, update_time, origin_domain FROM stats')
    for result in cursor.fetchall():
        data.append(result)
    return data


def dump_downloads(path):
    data = []
    db_path = os.path.join(path, 'History')
    conn = sqlite3.connect(db_path)
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
    process_names = ['chrome.exe', 'chrome']
    for p in psutil.process_iter():
        for p_name in process_names:
            try:
                if p.name() == p_name:
                    p.kill()
            except psutil.NoSuchProcess:
                # unknown problem
                print "no such process"
                continue


def get_os_path():
    path_win_10_post2008 = os.path.join('C:\\', 'Users', os.getenv('username'), 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default')
    path_win_7 = os.path.join('C:\\', 'Users', os.getenv('username'), 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default')
    path_win_xp = os.path.join('C:\\', 'Documents and Settings', os.getenv('username'), 'Application Support', 'Google', 'Chrome', 'Default')
    path_mac_os_x = '~/Library/Application Support/Google/Chrome/Default/'
    path_linux = '~/.config/google-chrome/Default/'
    system_name = platform.system().upper()
    if 'JAVA' in system_name:
        return None
    if 'WINDOWS' in system_name:
        system_name += platform.release().upper()
    return {
        'WINDOWSPOST2008SERVER': path_win_10_post2008,
        'WINDOWS10': path_win_10_post2008,
        'WINDOWS8.1': path_win_10_post2008,
        'WINDOWS8': path_win_10_post2008,
        'WINDOWS7': path_win_7,
        'WINDOWSVISTA': path_win_7,
        'WINDOWSXP': path_win_xp,
        'MACOS': path_mac_os_x,
        'LINUX': path_linux
    }.get(system_name, 'WINDOWS10')


def generate_urls(path, files):
    urls = set([])
    counter = 0
    for f in files:
        try:
            counter += 1
            if not (counter % (len(files) / 10)):
                print "*LOGGING*\tgenerate_urls: {}%".format((float(counter) / len(files)) * 100)

            db = sqlite3.connect(os.path.join(path, f))
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Dump information from Google-Chrome browser databases')
    parser.add_argument('-k', '--kill-browser', help='terminate chrome process', required=False,
                        dest='terminate_chrome',
                        action='store_true')
    parser.add_argument('-d', '--deep', help='deep inspection', required=False, dest='deep',
                        action='store_true')

    investigate_dbs(**vars(parser.parse_args()))
