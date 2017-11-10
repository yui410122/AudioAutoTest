import threading
import datetime
import shutil
import os

from libs import ROOT_DIR

try:
    import queue
    import io as sio
except ImportError:
    import Queue as queue
    import StringIO as sio

class LoggerThread(threading.Thread):
    MAX_SIZE = 1000
    LOG_DIR = ROOT_DIR + "/log/"

    def __init__(self, max_size=MAX_SIZE, log_dir=LOG_DIR):
        super(LoggerThread, self).__init__()
        self.daemon = True
        self.msg_q = queue.Queue()
        self.stoprequest = threading.Event()
        self.msg_stream = sio.StringIO()
        self.max_size = max_size
        self.current_size = 0
        self.log_dir = log_dir
        self._to_stdout = False

        if len(self.log_dir) < 1 and self.log_dir[-1] != "/":
            self.log_dir += "/"
        self._update_timestamp()

    def to_stdout(self):
        self._to_stdout = True

    def _update_timestamp(self):
        self.log_timestamp = datetime.datetime.now()

    def _dump(self):
        t = self.log_timestamp
        self._update_timestamp()
        if self._to_stdout:
            import sys
            sys.stdout.write(self.msg_stream.getvalue())
            sys.stdout.flush()
        else:
            filename = "{}{}{}_{}{}{}.log".format(t.year, t.month, t.day, t.hour, t.minute, t.second)
            with open(self.log_dir + filename, "w") as f:
                self.msg_stream.seek(0)
                shutil.copyfileobj(self.msg_stream, f)

        self.msg_stream.truncate(0)

    def push(self, msg):
        self.msg_q.put(msg)

    def join(self, timeout=None):
        self.stoprequest.set()
        super(LoggerThread, self).join(timeout)

    def run(self):
        os.system("mkdir -p {}".format(self.log_dir))
        while not self.stoprequest.isSet():
            try:
                msg = self.msg_q.get(True, 0.1)
                self.msg_stream.write("[{}] {}\n".format(datetime.datetime.now(), msg))
                self.current_size += 1
                if self.current_size >= self.max_size:
                    self._dump()
                    self.current_size = 0

            except queue.Empty:
                continue

        if self.current_size > 0:
            self._dump()
            self.current_size = 0

class Logger(object):
    WORK_THREAD = LoggerThread()
    HAS_BEEN_INIT = False

    @staticmethod
    def init(mode=None):
        if Logger.HAS_BEEN_INIT:
            return

        if mode:
            Logger.WORK_THREAD.to_stdout()
            Logger.WORK_THREAD.max_size = 1
        Logger.WORK_THREAD.start()
        Logger.HAS_BEEN_INIT = True

    @staticmethod
    def finalize():
        if not Logger.HAS_BEEN_INIT:
            return

        Logger.WORK_THREAD.join()
        Logger.HAS_BEEN_INIT = False

    @staticmethod
    def log(tag, msg):
        Logger.WORK_THREAD.push("{}: {}".format(tag, msg))
