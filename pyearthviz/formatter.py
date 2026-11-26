import matplotlib as mpl


def log_formatter(x):
    a, b = f"{x:.1e}".split("e")
    b = int(b)
    return rf"${a} \times 10^{{{b}}}$"


def float_formatter(x):
    a = f"{x:.1f}"
    return a


class MathTextSciFormatter(mpl.ticker.Formatter):
    def __init__(self, fmt="%1.2e"):
        self.fmt = fmt

    def __call__(self, x, pos=None):
        s = self.fmt % x
        decimal_point = "."
        positive_sign = "+"
        tup = s.split("e")
        significand = tup[0].rstrip(decimal_point)
        sign = tup[1][0].replace(positive_sign, "")
        exponent = tup[1][1:].lstrip("0")
        if exponent:
            exponent = f"10^{{{sign}{exponent}}}"
        if significand and exponent:
            s = rf"{significand}{{\times}}{exponent}"
        else:
            s = rf"{significand}{exponent}"
        return f"${s}$"


class OOMFormatter(mpl.ticker.ScalarFormatter):
    def __init__(self, order=0, fformat="%1.1e", offset=True, mathText=True):
        self.oom = order
        self.fformat = fformat
        mpl.ticker.ScalarFormatter.__init__(
            self, useOffset=offset, useMathText=mathText
        )

    def _set_order_of_magnitude(self):
        self.orderOfMagnitude = self.oom

    def _set_format(self, vmin=None, vmax=None):
        self.format = self.fformat
        if self._useMathText:
            self.format = r"$\mathdefault{%s}$" % self.format
