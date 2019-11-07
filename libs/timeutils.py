import datetime

def TicTocGenerator():
    tf = datetime.datetime.now()
    while True:
        ti = tf
        tf = datetime.datetime.now()
        yield (tf - ti).total_seconds()

class TicToc(object):
    def __init__(self):
        self.tictoc = TicTocGenerator()

    def toc(self):
        return next(self.tictoc) * 1000.0

    def tic(self):
        next(self.tictoc)

class TimeUtils(object):
    TIME_STR_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
    TIME_UNITS = ["d", "h", "m", "s"]

    @staticmethod
    def now_str():
        return TimeUtils.str_from_time(datetime.datetime.now())

    @staticmethod
    def str_from_time(t):
        return datetime.datetime.strftime(t, TimeUtils.TIME_STR_FORMAT)

    @staticmethod
    def time_from_str(s):
        return datetime.datetime.strptime(s, TimeUtils.TIME_STR_FORMAT)

    @staticmethod
    def pretty_str(ms):
        if ms <= 0:
            return "0s"
        t = datetime.datetime.fromtimestamp(ms / 1000.0) - datetime.datetime.fromtimestamp(0)
        t = [str(int(s)) if s.isdigit() else str(float(s))
                 for s in str(t).replace(" days, ", ":").split(":") if float(s) > 0]
        s = "{} ".join(t) + "{}"
        s = s.format(*TimeUtils.TIME_UNITS[-len(t):])
        return s
