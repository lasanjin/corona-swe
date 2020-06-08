#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import utils as u
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
        print(u.debug(), 'NO SAVED DATA AVAILABLE FROM TODAY...')

    try:
        print(u.debug(), 'LOADING DRIVER...')
        t1 = time.time()
        driver = build_driver()
        driver.get(api.API)
        print_elapsed_time('DRIVER LOADED:', t1)

        print(u.debug(), 'LOOKING FOR ELEMENTS...')
        t2 = time.time()
        table = get_element(driver, C.TABLE_ID)
        button = get_element(driver, C.BUTTON_ID, True)
        pagination = get_element(driver, C.PAGINATION_ID)
        ndays = parse_pagination(pagination)
        print_elapsed_time('ELEMENTS FOUND:', t2)

        print(u.debug(), 'SCRAPING DATA...')
        t3 = time.time()
        data = scrape_data(table, button, ndays)
        print_elapsed_time('DATA SCRAPED:', t3)

    finally:
        driver.quit()

    data, date = parse_data(data)
    save_data(data, date)
    print_elapsed_time('TIME:', t0)
    ask(data)


def print_elapsed_time(string, t):
    print('{} {} {}{}'.format(u.info(), string, round(time.time() - t, 2), 's'))


def ask(data):
    sys.stdout.write(u.info() + ' PRINT DATA ? [Y/N]: ')
    choice = input().lower()

    if choice is not None and choice == 'y':
        print_json(data)


def scrape_data(table, button, ndays):
    data = SortedDict()

    for i in range(ndays):
        html = table.get_attribute('innerHTML')
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('tr')

        dt = rows[0].find_all('td')[1].text
        date = format_date(dt)

        data[date] = OrderedDict()

        for row in rows[1:]:
            col = row.find_all('td')
            region = col[0].text
            n = int(col[1].text.replace(',', ''))

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
        print(u.error(), 'PAGE DID NOT LOAD IN TIME...')

    return element


def parse_pagination(pagination):
    p = pagination.text
    try:
        return int(p[p.rindex(' ')+1:])

    except ValueError:
        print(u.error(), 'CAN NOT FIND PAGINATION')


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

            print(u.debug(), 'DATA SAVED')

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

            print(u.debug(), 'DATA LOADED')

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
    DIR = 'data'
    DIV_ID = 'ember119'
    PAGINATION_ID = 'ember277'
    BUTTON_ID = 'ember282'
    TABLE_ID = 'ember284'
    PARSER = 'html.parser'

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
