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
    data = read_data()
    if data is not None:
        print_json(data)
        quit()

    print(C.FDATA)

    driver = build_driver()
    driver.get(api.API)

    npage = get_element(driver, C.NDAYS_ID).text
    button = get_element(driver, C.NEXT_ID)
    ndays = int(npage[npage.rindex(' ')+1:])

    print(C.OK)

    time_series = parse_data(driver, button, ndays)
    data, date = parse_time_series(time_series)

    save_data(data, date)


def parse_data(driver, button, ndays):
    print(C.SDATA)
    time_series = SortedDict()

    try:
        for i in range(ndays):
            soup = BeautifulSoup(driver.page_source, C.PARSER)
            div = soup.find(id=C.TABLE_ID)
            tds = div.find_all('td')

            dt = tds[1].text
            date = format_date(dt)
            time_series[date] = OrderedDict()
            region = ''

            for i, td in enumerate(tds[2:]):

                if i % 2 != 0:
                    n = int(td.text)
                    time_series[date][region] = n

                region = td.text

            button.click()

    finally:
        driver.quit()

    return time_series


def parse_time_series(time_series):
    data = OrderedDict()
    data['NEW_CASES_PER_DAY_REGIONS'] = time_series
    data['NEW_CASES_PER_DAY'] = build_progress(time_series)
    data['TOTAL_CASES_PER_DAY'] = build_progress(time_series, True)
    data['TOTAL_CASES_REGIONS'] = sum_time_series(time_series)

    return data, time_series.keys()[-1]


def sum_time_series(time_series):
    return sum(
        (Counter(dict(x)) for x in list(time_series.values())),
        Counter())


def build_progress(data, TOTAL=False):
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


def get_element(driver, ID):
    timeout = 10
    try:
        element = WebDriverWait(driver, timeout).until(
            ec.element_to_be_clickable((By.ID, ID)))

    except TimeoutException:
        print(C.ERROR)
        driver.quit()

    return element


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
            json.dump(data, f)
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


def read_data():
    file = C.file()
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
    FDATA = "\nFETCHING DATA...\n"
    SDATA = "SCRAPING DATA...\n"
    OK = 'OK\n'
    LOADED = '\nDATA LOADED\n'
    SAVED = 'DATA SAVED, RUN SCRIPT AGAIN TO PRINT\n'
    NEXT_ID = 'ember249'
    NDAYS_ID = 'ember245'
    TABLE_ID = 'ember252'
    ERROR = 'PAGE DID NOT LOAD IN TIME...\n'
    PARSER = 'html.parser'
    DIR = 'data'

    @staticmethod
    def file(date=None):
        return 'data/data-' + (datetime.today().strftime('%y-%m-%d')
                               if date is None
                               else str(date)) + '.txt'

    @staticmethod
    def path(p):
        return 'driver/chromium/' + p \
            if p == 'chrome' else 'driver/' + p


if __name__ == "__main__":
    main()
