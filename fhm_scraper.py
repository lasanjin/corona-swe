#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
from datetime import datetime, date
from collections import OrderedDict, Counter

from modules.bs4 import BeautifulSoup
from modules.sortedcontainers import SortedSet, SortedDict

from modules.selenium import webdriver
from modules.selenium.webdriver.common.by import By
from modules.selenium.webdriver.support.ui import WebDriverWait
from modules.selenium.webdriver.support import expected_conditions as ec
from modules.selenium.common.exceptions import TimeoutException


def main():
    t0 = time.time()
    data = read_data()

    if data is not None:
        ask(data)
        quit()

    else:
        print(C.NAVAILABLE)

    try:
        print(C.LDRIVER)
        t1 = time.time()
        driver = build_driver()
        driver.get(api.API)
        print_time(C.DRIVERL, t1)

        print(C.LOOKE)
        t2 = time.time()
        table = get_element(driver, C.TABLE_ID)
        button = get_element(driver, C.BUTTON_ID, True)
        pagination = get_element(driver, C.PAGINATION_ID)
        ndays = parse_pagination(pagination)
        print_time(C.EFOUND, t2)

        print(C.SDATA)
        t3 = time.time()
        data = scrape_data(table, button, ndays)
        print_time(C.DATAS, t3)

    finally:
        driver.quit()

    data, date = parse_data(data)

    save_data(data, date)

    print_time(C.TIME, t0)

    ask(data)


def print_time(string, t):
    print('{} {}{}'.format(string, round(time.time() - t, 2), 's'))


def ask(data):
    sys.stdout.write(C.PRINT)
    choice = input().lower()

    if choice is not None and choice == C.YES:
        print_json(data)


def scrape_data(table, button, ndays):
    data = SortedDict()

    for i in range(ndays):
        html = table.get_attribute('innerHTML')
        soup = BeautifulSoup(html, C.PARSER)
        rows = soup.find_all('tr')

        dt = rows[0].find_all('td')[1].text
        date = format_date(dt)

        data[date] = OrderedDict()

        for row in rows[1:]:
            col = row.find_all('td')
            region = col[0].text
            n = int(col[1].text)

            data[date][region] = n

        button.click()

    return data


def parse_data(data):
    parsed = OrderedDict()
    parsed['NEW_CASES_PER_DAY_REGIONS'] = data
    parsed['NEW_CASES_PER_DAY'] = parse_time_series(data)
    parsed['TOTAL_CASES_PER_DAY'] = parse_time_series(data, True)
    parsed['TOTAL_CASES_REGIONS'] = sum_time_series(data)

    return parsed, data.keys()[-1]


def sum_time_series(time_series):
    return sum(
        (Counter(dict(x)) for x in list(time_series.values())),
        Counter())


def parse_time_series(data, TOTAL=False, REGION=None):
    progress = OrderedDict()
    prev = 0
    for k, v in data.items():
        prev = prev + v['Totalt'] if TOTAL else v['Totalt']
        progress[k] = prev

    return progress


def build_driver():
    # prepare the option for the chrome driver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument("--disable-webgl")

    chrome = os.path.abspath(C.path('chrome'))
    if os.path.isfile(chrome):
        options.binary_location = chrome
    # start chrome driver
    driver = webdriver.Chrome(
        executable_path=os.path.abspath(C.path('chromedriver')),
        options=options)

    return driver


def get_element(driver, ID, BUTTON=False):
    timeout = 20
    exp_cond = ec.element_to_be_clickable((By.ID, ID)) if BUTTON \
        else ec.presence_of_element_located((By.ID, ID))

    try:
        wait = WebDriverWait(
            driver,
            timeout,
            poll_frequency=0.1)

        element = wait.until(exp_cond)

    except TimeoutException:
        print(C.ERROR)

    return element


def parse_pagination(pagination):
    p = pagination.text
    try:
        return int(p[p.rindex(' ')+1:])

    except ValueError:
        print(C.PERROR)


def format_date(date):
    time = datetime \
        .strptime(str(date), '%d/%m/%Y') \
        .strftime('%y-%m-%d')

    return time


def save_data(data, date):
    create_dir()
    file = C.file(date)
    if not os.path.isfile(file):

        try:
            f = open(file, "w")
            json.dump(data, f, ensure_ascii=False)
            f.close()

            print(C.SAVED)

        except OSError as eos:
            print('OSError:', eos)

        except IOError as eio:
            print("IOError:", eio)


def create_dir():
    try:
        os.mkdir(C.DIR)

    except FileExistsError:
        pass


def read_data(FILE=None):
    file = C.file() if FILE is None else FILE

    if os.path.isfile(file):
        try:
            f = open(file, "r")
            json_data = json.load(f)
            f.close()

            print(C.LOADED)

        except IOError as eio:
            print("IOError:", eio)

        return json_data

    else:
        return None


def print_json(json_data):
    print(json.dumps(json_data, indent=4, ensure_ascii=False))


class api:
    API = 'https://fohm.maps.arcgis.com/apps/opsdashboard/' \
        'index.html#/68d4537bf2714e63b646c37f152f1392'


class C:
    NAVAILABLE = 'NO SAVED DATA AVAILABLE FROM TODAY...'
    LDRIVER = 'LOADING DRIVER...'
    DRIVERL = 'DRIVER LOADED:'
    LOOKE = 'LOOKING FOR ELEMENTS...'
    EFOUND = 'ELEMENTS FOUND:'
    SDATA = 'SCRAPING DATA...'
    DATAS = 'DATA SCRAPED:'
    PERROR = 'CAN NOT FIND PAGINATION'
    ERROR = 'PAGE DID NOT LOAD IN TIME...'
    TIME = 'TIME:'
    SAVED = 'DATA SAVED'
    LOADED = 'DATA LOADED'
    PRINT = 'PRINT DATA ? [Y/N]: '
    YES = 'y'
    DIV_ID = 'ember119'
    PAGINATION_ID = 'ember277'
    BUTTON_ID = 'ember282'
    TABLE_ID = 'ember284'
    PARSER = 'html.parser'
    DIR = 'data'

    @staticmethod
    def file(date=None):
        return 'data/data-' + (datetime.today().strftime('%y-%m-%d')
                               if date is None
                               else str(date)) + '.json'

    @staticmethod
    def path(p):
        return 'driver/chromium/' + p \
            if p == 'chrome' else 'driver/' + p


if __name__ == "__main__":
    main()
