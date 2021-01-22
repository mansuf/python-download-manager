import urllib.parse
from math import log

class StringVar:
    """
    adapted from tkinter.StringVar() class,
    but with get() and set() function only
    """
    def __init__(self, initial_value: str=None):
        self._value = initial_value or ''

    def set(self, value: str):
        self._value = value

    def get(self):
        return self._value


def get_filename(response):
    REPLACERS = [
        'attachment; filename*=UTF-8\'\'',
        'attachment; filename='
    ]
    content_unparsed = response.headers['Content-Disposition']
    value = StringVar()
    for replacer in REPLACERS:
        if value.get() == '':
            value.set(content_unparsed.replace(replacer, ''))
        else:
            v = value.get()
            value.set(v.replace(replacer, ''))
    return urllib.parse.unquote(value.get())

# adapted from https://github.com/choldgraf/download/blob/master/download/download.py#L425
def sizeof_fmt(num):
    """Turn number of bytes into human-readable str.
    Parameters
    ----------
    num : int
        The number of bytes.
    Returns
    -------
    size : str
        The size in human-readable format.
    """
    units = ["bytes", "kB", "MB", "GB", "TB", "PB"]
    decimals = [0, 0, 1, 2, 2, 2]
    if num > 1:
        exponent = min(int(log(num, 1024)), len(units) - 1)
        quotient = float(num) / 1024 ** exponent
        unit = units[exponent]
        num_decimals = decimals[exponent]
        format_string = "{0:.%sf} {1}" % (num_decimals)
        return format_string.format(quotient, unit)
    if num == 0:
        return "0 bytes"
    if num == 1:
        return "1 byte"