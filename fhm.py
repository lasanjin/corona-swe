#!/usr/bin/python
# -*- coding: utf-8 -*-

from collections import Counter, OrderedDict
from datetime import datetime, date
from modules import requests
from sys import argv
import json


def main():
    # p=0: Totalt antal per region
    # p=1: Antal per dag region
    # p=2: Antal per dag ålder och kön  # NO DATA
    # p=3: Totalt antal per kön
    # p=4: Totalt antal per åldersgrupp
    p0, p1, p2 = get_params()

    url = api.url(p0)
    jdata = get_data(url)

    if p0 == 0:
        data = parse_cases_per_region(jdata)

        print_cases_per_region(data, p1)
        print_cases_per_region_sum(data)

    elif p0 == 1:
        data = parse_regions(jdata)

        if p1 == 0:  # (date: new-cases)
            print_regions(data, False),
        elif p1 == 1:  # (date: new-cases per region)
            print_regions(data, True, False, p2),
        elif p1 == 2:  # (date: total)
            print_regions(data, False, True),
        elif p1 == 3:  # (date: total per region)
            print_regions(data, True, True, p2),
        elif p1 == 4:  # (region: total-cases)
            print_regions_sum(data)

    elif p0 == 2:
        print('NO DATA')

    elif p0 == 3:
        data = parse_gender(jdata)

        print_gender(data)
        print_gender_sum(data)

    elif p0 == 4:
        data = parse_age_groups(jdata)

        print_age_groups(data)
        print_age_groups_sum(data)


def get_params():
    try:
        p0 = int(argv[1:][0])
        p1 = None
        p2 = None

        try:
            p1 = int(argv[1:][1])
        except Exception:
            if p0 == 1:
                print(C.USAGE)
                quit()

        try:
            tmp = ' '.join(argv[1:][2:]).title()
            p2 = tmp if bool(tmp) else None
        except Exception:
            pass

        if p0 < 0 or p0 > 4 or p1 > 4:
            print(C.USAGE)
            quit()

        return p0, p1, p2

    except Exception:
        print(C.USAGE)
        quit()


def parse_cases_per_region(jdata):
    data = OrderedDict()
    region = None

    for r in jdata['features']:
        for i, (k, v) in enumerate(r['attributes'].items()):

            if i > 0 and i != 3 and i < 6:

                if i == 1:
                    region = v.upper()
                    data[region] = OrderedDict()

                else:
                    n = 0 if v is None else v
                    text = k.replace('Totalt_antal_', '').capitalize()

                    data[region][text] = int(n)

    return data


def parse_regions(jdata):
    data = OrderedDict()

    for i in jdata['features']:
        date = format_date(i['attributes']['Statistikdatum'])
        data[date] = OrderedDict()

        for i, (k, v) in enumerate(i['attributes'].items()):
            if i > 3 and i < 25:  # only regions
                n = 0 if v is None else v
                text = k.replace('_', ' ')

                data[date][text] = int(n)

    return data


def parse_age_groups(jdata):
    data = OrderedDict()
    age_group = None

    for i in jdata['features']:
        for i, (k, v) in enumerate(i['attributes'].items()):

            if i > 0 and i != 2:

                if i == 1:
                    age_group = v.upper()
                    data[age_group] = OrderedDict()

                else:
                    n = 0 if v is None else v
                    text = k.replace('Totalt_antal_', '').capitalize()

                    data[age_group][text] = int(n)

    return data


def parse_gender(jdata):
    return parse_age_groups(jdata)


def format_date(dt):
    sec = dt / 1000
    return datetime.fromtimestamp(sec).strftime('%y-%m-%d')


def sum_data(data):
    return sum(
        (Counter(dict(x)) for x in list(data.values())),
        Counter())


def build_progress(data):
    progress = OrderedDict()
    prev = 0

    for k, v in data.items():
        prev += sum(v.values())
        progress[k] = prev

    return progress


def print_regions(data, ALL=False, TOTAL=False, REGION=None):
    if REGION is not None:
        if list(data.values())[-1].get(REGION) is None:
            print('NO SUCH REGION')
            quit()
        else:
            print(color.blue(REGION.upper()))

    if ALL:
        prev = [0] * 21  # regions
        for date, v in data.items():
            if REGION is None:
                print(color.blue(date))

            for idx, (region, n) in enumerate(v.items()):
                if REGION is None:
                    prev[idx] = prev[idx] + n if TOTAL else n
                    print(C.FORMAT.format(region, prev[idx]))

                elif REGION == region:
                    prev[idx] = prev[idx] + n if TOTAL else n
                    print(C.FORMAT.format(date, prev[idx]))

            if REGION is None:
                print()

    else:
        prev = 0
        for date, v in data.items():
            n = sum(v.values())
            prev = prev + n if TOTAL else n

            print(C.FORMAT.format(date, prev))


def print_regions_sum(data):
    tot = sum_data(data)
    print(color.blue('TOTALT'))

    for k, v in sorted(tot.items(), key=lambda k: k[1]):
        print(C.FORMAT.format(k, v))


def print_age_groups(data, SORT=None):
    for k, v in sort(data, SORT):
        print(color.blue(k))

        for i, (case, n) in enumerate(v.items()):
            if i == 2:
                print(C.FORMAT.format(case, n))

            else:
                print(C.FORMAT.format(case, n))

        print()


def sort(data, SORT):
    s = {0: 'Fall', 1: 'Avlidna', 2: 'Intensivvårdade'}.get(SORT)
    SORT = None if s is None else s
    return data.items() if SORT is None else sorted(data.items(), key=lambda x: x[1][s])


def print_age_groups_sum(data):
    tot = sum_data(data)
    print(color.blue('TOTALT'))

    for i, (k, v) in enumerate(tot.items()):
        if i == 2:
            print(C.FORMAT.format(k, v))

        else:
            print(C.FORMAT.format(k, v))


def print_gender(data):
    print_age_groups(data)


def print_gender_sum(data):
    print_age_groups_sum(data)


def print_cases_per_region(data, SORT):
    print_age_groups(data, SORT)


def print_cases_per_region_sum(data):
    print_age_groups_sum(data)


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
    PATH = '/query?f=json&outFields=*'
    ALL = '&where=1%3D1'
    REGIONS = '&where=Region <> \'dummy\'&returnGeometry=false'

    @staticmethod
    def url(n):
        return api.URL + str(n) + api.PATH + (api.REGIONS if n == 0 else api.ALL)


class C:
    FORMAT = '{:<20}{:>15}'
    USAGE = 'Usage: ./fhm_hax.py 0 [1..3] | 2 | 3 | 4 | 1 1..4 [REGION]\n' \
        '\n0: Total per region' \
            '\n\t\t0: Sort by "Fall"' \
            '\n\t\t1: Sort by "Intensivvårdade"' \
            '\n\t\t2: Sort by "Avlidna"' \
        '\n1: Custom:' \
            '\n\t\t0: New cases per day' \
            '\n\t\t1: New cases per day per region' \
            '\n\t\t2: Total cases per day' \
            '\n\t\t3: Total per day per region' \
            '\n\t\t4: Total per region' \
        '\n2: No data yet' \
        '\n3: Total per gender' \
        '\n4: Total per age group' \
        '\n\nExamples:' \
            '\n\t\t./fhm.py 0 1' \
            '\n\t\t./fhm.py 1 1 Västra Götaland'


class color:
    DEFAULT = '\033[0m'
    BLUE = '\033[94m'

    @staticmethod
    def blue(output):
        return color.BLUE + str(output) + color.DEFAULT


if __name__ == "__main__":
    main()
