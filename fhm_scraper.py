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
    print(C.FDATA)

    driver = build_driver()
    driver.get(api.API)

    npage = get_element(driver, C.NDAYS_ID).text
    button = get_element(driver, C.NEXT_ID)
    ndays = int(npage[npage.rindex(' ')+1:])

    print(C.OK)

    time_series = parse_data(driver, button, ndays)
    data = parse_time_series(time_series)

    # save_data(data)

    print_json(data)


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
    data = dict()
    data['TIME_SERIES'] = time_series
    data['PROGRESS'] = build_progress(time_series)
    data['TOTAL'] = sum_time_series(time_series)

    return data


def sum_time_series(time_series):
    return sum(
        (Counter(dict(x)) for x in list(time_series.values())),
        Counter())


def build_progress(data):
    progress = OrderedDict()
    prev = 0
    for k, v in data.items():
        prev += v['Totalt']
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


def save_data(data):
    file = C.FILE
    # if not os.path.isfile(file):
    try:
        file = open(file, "w")
        json.dump(data, file)
        file.close()

    except OSError as eos:
        print('OSError:', eos)

    except IOError as eio:
        print("IOError:", eio)


def read_data():
    try:
        file = open(C.FILE, "r")
        json_data = json.load(file)
        file.close()

    except IOError as eio:
        print("IOError:", eio)

    return json_data


def print_json(json_data):
    print(json.dumps(json_data, indent=4, ensure_ascii=False))


class api:
    API = 'https://fohm.maps.arcgis.com/apps/opsdashboard/' \
        'index.html#/68d4537bf2714e63b646c37f152f1392'


class C:
    FDATA = "\nFETCHING DATA...\n"
    SDATA = "SCRAPING DATA...\n"
    OK = 'OK\n'
    NEXT_ID = 'ember249'
    NDAYS_ID = 'ember245'
    TABLE_ID = 'ember252'
    FILE = 'data.txt'
    ERROR = 'PAGE DID NOT LOAD IN TIME...'
    PARSER = 'html.parser'

    @staticmethod
    def path(p):
        return 'driver/chromium/' + p \
            if p == 'chrome' else 'driver/' + p


if __name__ == "__main__":
    main()
