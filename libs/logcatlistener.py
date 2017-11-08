import threading
import subprocess

try:
    import queue
except ImportError:
    import Queue as queue

class LogcatOutputThread(threading.Thread):
    def __init__(self, serialno):
        super(LogcatOutputThread, self).__init__()
        self.daemon = True
        self.msg_q = queue.Queue()
        self.stoprequest = threading.Event()
        self.proc = None

    def join(self, timeout=None):
        self.stoprequest.set()
        super(LogcatOutputThread, self).join(timeout)

    def poll(self):
        return self.proc.poll() if self.proc else None

    def run(self):
        self.proc = subprocess.Popen(["adb", "logcat"], stdout=subprocess.PIPE)
        while not self.stoprequest.isSet():
            if self.proc.poll() != None:
                break

            line = self.proc.stdout.readline()

class LogcatListener(object):
    WORK_THREADS = {}

    @staticmethod
    def kill_finished_threads():
        while len(LogcatListener.WORK_THREADS.keys()) > 0:
            for serialno, th in LogcatListener.WORK_THREADS.items():
                if th.poll() != None:
                    th.join()
                    del LogcatListener.WORK_THREADS[serialno]

    @staticmethod
    def init(serialno=None):
        if not serialno:
            out, _ = subprocess.Popen(["adb", "devices"], stdout=subprocess.PIPE).communicate()
            if len(out.splitlines()) > 1:
                serialno = out.splitlines()[1].split("\t")[0]
        LogcatListener.WORK_THREADS[serialno] = LogcatOutputThread(serialno)
        LogcatListener.WORK_THREADS[serialno].start()

        if len(LogcatListener.WORK_THREADS.keys()) == 1:
            threading.Thread(target=LogcatListener.kill_finished_threads).start()
