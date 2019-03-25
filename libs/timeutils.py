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

    @staticmethod
    def now_str():
        return TimeUtils.str_from_time(datetime.datetime.now())

    @staticmethod
    def str_from_time(t):
        return datetime.datetime.strftime(t, TimeUtils.TIME_STR_FORMAT)

    @staticmethod
    def time_from_str(s):
        return datetime.datetime.strptime(s, TimeUtils.TIME_STR_FORMAT)
