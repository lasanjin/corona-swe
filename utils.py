#!/usr/bin/python3


def info():
    return color.green("[INFO]")


def debug():
    return color.blue("[DBUG]")


def error():
    return color.red("[ERRR]")


def warn():
    return color.yellow("[WARN]")


class color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    DEFAULT = '\033[0m'
    BOLD = "\033[1m"

    @staticmethod
    def green(output):
        return color.GREEN + output + color.DEFAULT

    @staticmethod
    def red(output):
        return color.RED + str(output) + color.DEFAULT

    @staticmethod
    def yellow(output):
        return color.YELLOW + output + color.DEFAULT

    @staticmethod
    def blue(output):
        return color.BLUE + output + color.DEFAULT
