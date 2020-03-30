#!/usr/bin/python
# -*- coding: utf-8 -*-

from collections import Counter, OrderedDict
from datetime import datetime, date
from modules import requests
import json


def main():
    # 0: Totalt antal per region (Not printed below)
    # 1: Antal per dag region
    # 2: Antal per dag ålder och kön, ALL=False
    # 3: Totalt antal per kön
    # 4: Totalt antal per åldersgrupp
    a = 1

    # url = api.url(a, False, api.MAN)
    url = api.url(a)
    raw = get_data(url)

    data = parse_data(raw)

    # a = 1
    print_progress(data, True)  # (date: total)
    # print_progress(data)  # (date: new-cases)
    # print_sum(data)  # (total-cases: region)


def parse_data(raw, a=1):
    data = OrderedDict()

    for i in raw['features']:
        if a == 1:
            date = format_date(i['attributes']['Statistikdatum'])
            data[date] = OrderedDict()
            # print(date)

        for i, (k, v) in enumerate(i['attributes'].items()):
            if a == 1 and i > 3:
                data[date][k] = int(v)
                # print(k, v)

            # elif a == 2 and i > 1:
                # print(k, v)

            # elif a == 3 and i > 1:
                # print(k, v)

            # elif a == 4 and i > 0:
                # print(k, v)

        # print()

    return data


def format_date(dt):
    sec = dt / 1000
    return datetime.fromtimestamp(sec).strftime('%y-%m-%d')


def sum_time_series(time_series):
    return sum(
        (Counter(dict(x)) for x in list(time_series.values())),
        Counter())


def build_progress(data, TOTAL=False):
    progress = OrderedDict()
    prev = 0
    for k, v in data.items():
        prev += sum(v.values())
        progress[k] = prev

    return progress


def print_sum(data):
    for k, v in sorted(sum_time_series(data).items(), key=lambda k: k[1]):
        print(C.FORMAT.format(k, v))


def print_progress(data, TOTAL=False):
    prev = 0
    for k, v in data.items():
        s = sum(v.values())
        prev = prev + s if TOTAL else s

        print(C.FORMAT.format(k, prev))


def get_data(url):
    try:
        res = requests.get(url)

        res.raise_for_status()

        return json.loads(res.text)

    except requests.exceptions.HTTPError as eh:
        print("HTTPError:", eh)

    except requests.exceptions.ConnectionError as ec:
        print("ConnectionError:", ec)

    except requests.exceptions.Timeout as et:
        print("Timeout:", et)

    except requests.exceptions.RequestException as er:
        print("RequestException:", er)


class api:
    URL = 'https://services5.arcgis.com/' \
        'fsYDFeRKu1hELJJs/arcgis/rest/services/FOHM_Covid_19_FME_1/FeatureServer/'
    PATH = '/query?f=json&outFields=*&'
    ALL = 'where=1%3D1'
    MAN = 'where=K%C3%B6n%3D%27Man%27'
    KVINNA = 'where=K%C3%B6n%3D%27Kvinna%27'

    @staticmethod
    def url(n, ALL=True, GENDER=None):
        return api.URL + str(n) + api.PATH + (api.ALL if ALL else GENDER)


class C:
    FORMAT = '{:15}{:>10}'


if __name__ == "__main__":
    main()
