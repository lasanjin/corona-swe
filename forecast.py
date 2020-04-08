#!/usr/bin/python
# -*- coding: utf-8 -*-

import fhm
import numpy
from scipy.optimize import curve_fit
from datetime import datetime, timedelta
try:
    import matplotlib.ticker as ticker
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdate
except ImportError:
    pass


ndays = 7  # ndays forecast


def main():
    url = fhm.api.url(1)
    raw = fhm.get_data(url)
    data = fhm.parse_regions(raw)
    progress = fhm.build_progress(data)

    # Get everything for plot & print
    dates = list(progress.keys())
    xarr, yarr = build_func_data(progress)
    a, k_e, b, L, k_l, x0 = get_functions(xarr, yarr)
    B = 0  # b  # b-value in exp function

    # Print functions and data
    print_functions(a, k_e, B, L, k_l, x0)
    print_forecast(L, k_l, x0, a, k_e, B, dates, yarr, ndays)

    # Print last expected date and estimated number of confirmed cases based on logistic function
    start = datetime.strptime(dates[0], "%y-%m-%d").date()
    print_last_day(L, k_l, x0, start)

    # Plot graph
    try:
        # Generate dates for x-axis
        x_values = [start + timedelta(days=x)
                    for x in range(len(dates) + ndays)]

        # Generate y-values
        end = len(x_values)
        x = numpy.linspace(0, end, num=end)
        y_values_e = exponential(x, *[a, k_e, B])
        y_values_l = logistic(x, *[L, k_l, x0])

        # Set size
        plt.rcParams['figure.figsize'] = [16, 9]
        plt.rc('font', size=10)

        # Format x-axis & y-axis
        fig, ax = plt.subplots()
        fig.autofmt_xdate()
        formatter = mdate.DateFormatter('%y-%m-%d')
        ax.xaxis.set_major_formatter(formatter)
        ax.get_xaxis().set_major_locator(mdate.DayLocator(interval=7))
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))

        plt.scatter(
            x_values[:len(xarr)],
            yarr,
            zorder=3,
            marker='o',
            s=40,
            alpha=0.75,
            edgecolors="dimgrey",
            color="lightgrey",
            label="Real")

        plt.plot(
            x_values,
            y_values_e,
            marker='.',
            markersize=4,
            linewidth=1,
            color='firebrick',
            label="Exponential")

        plt.plot(
            x_values,
            y_values_l,
            marker='.',
            markersize=4,
            linewidth=1,
            color='green',
            label="Logistic")

        plt.text(
            x_values[-ndays],
            yarr[-1],
            '{:,.0f}'.format(yarr[-1]),
            color="dimgrey")

        plt.grid()
        plt.legend()
        plt.show()

    except Exception as e:
        print(e.args)


def calc_last_day(k, x0):
    # Estimating last day with threshold very close to 1
    # Exactly 1 will take infinitely long time
    threshold = 1.0001
    return int(round(
        (-1 / k) * numpy.log((1 - threshold) / (threshold * numpy.exp(-k) - 1)) + x0))


def exponential(x, a, k, b):
    return a * numpy.exp(x * k) + b  # a*e^(x*k)+b


def logistic(x, L, k, x0):
    return L / (1 + numpy.exp(-k * (x - x0)))  # L/(1+e^(-k*(x-x0)))


def get_functions(xarr, yarr):
    popt_e = fit_curve(exponential, xarr, yarr, 0.1)
    popt_l = fit_curve(logistic, xarr, yarr, 1)

    r = 5
    a, k_e, b = popt_e
    L, k_l, x0 = popt_l

    return round(a, r), round(k_e, r), round(b, r), round(L, r), round(k_l, r), round(x0, r)


def fit_curve(func, xarr, yarr, p01):
    # p0 = scipy.optimize.curve_fit() will gueress a value of 1 for all parameters.
    # This is generally not a good idea.
    # Always explicitly supply own initial guesses.

    # Use maxfev to set a high number of iterations to assure it will converge.
    popt, pcov = curve_fit(
        func,
        xarr,
        yarr,
        p0=(0, p01, 0),
        maxfev=100000)

    return popt


def build_func_data(data):
    xarr, yarr = [], []

    for x, v in enumerate(data.values()):
        y = int(v)
        yarr.append(y)
        xarr.append(x)

    return xarr, yarr


def print_functions(a, k, b, L, k_l, x0):
    # a*e^(x*k)+b
    print('\nEXPONENTIAL:\t{}e^({}x)+{}'.format(a, k, b))
    # L/(1+e^(-k*(x-x0)))
    print('\nLOGISTIC:\t{}/e^(-{}*(x-{}))'.format(L, k, x0))


def print_last_day(L, k_l, x0, start):
    ndays = calc_last_day(k_l, x0)

    last_day = start + timedelta(days=ndays)
    nconfirmed = logistic(ndays, L, k_l, x0)

    print('\n{}\t{}'.format(C.LASTD, last_day))
    print('{}\t\t{:,.0f}\n'.format(C.EST, int(nconfirmed)))


def print_forecast(L, k_l, x0, a, k_e, b, dates, yarr, ndays):
    print_header()

    for x, date in enumerate(dates):
        print_data(date, yarr[x], x, L, k_l, x0, a, k_e, b)

    last = datetime.strptime(dates[-1], "%y-%m-%d")
    start = len(dates)
    end = start + ndays

    for i, x in enumerate(range(start, end)):
        date = next_date(last, i)
        print_data(date, 0, x, L, k_l, x0, a, k_e, b)


def print_data(date, real, x, L, k_l, x0, a, k_e, b):
    log = int(logistic(x, L, k_l, x0))
    exp = int(exponential(x, a, k_e, b))

    print(C.TABLE.format(date, real, exp, log))


def next_date(last, i):
    next_date = last + timedelta(days=(i + 1))
    date = next_date.strftime("%y-%m-%d")

    return date


def print_header():
    l, h = C.header(C.HEADER)
    print()
    print(l)
    print(h)
    print(l)


class C:
    ERROR = "\nINSTALL \"matplotlib\" TO PLOT GRAPH ?\n"
    LASTD = "LAST DAY BASED ON LOGISTIC FUNCTION:"
    EST = 'ESTIMATED INFECTED ON LAST DAY:'
    TABLE = '{:10}{:>12,.0f}{:>12,.0f}{:>12,.0f}'
    HEADER = '{:10}{:>12}{:>12}{:>12}'.format('Date', 'Real', 'Exp', 'Log')

    @staticmethod
    def header(head):
        return C.line(head), head

    @staticmethod
    def line(head):
        return '-' * len(head.expandtabs())


if __name__ == "__main__":
    main()
