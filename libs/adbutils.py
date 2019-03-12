import subprocess
from libs.logger import Logger

TAG = "Adb"
def log(msg):
    Logger.log(TAG, msg)

class Adb(object):
    HAS_BEEN_INIT = False

    @staticmethod
    def init():
        Adb._execute("start-server", None)
        Adb.HAS_BEEN_INIT = True

    @staticmethod
    def _check_init():
        if not Adb.HAS_BEEN_INIT:
            Adb.init()

    @staticmethod
    def execute(cmd, serialno=None, tolog=True):
        Adb._check_init()
        return Adb._execute(cmd, serialno, tolog)

    @staticmethod
    def _execute(cmd, serialno, tolog=True):
        if not isinstance(cmd, list):
            cmd = [cmd]

        cmd_prefix = ["adb"]
        if serialno:
            cmd_prefix += ["-s", serialno]

        cmd = cmd_prefix + cmd
        if tolog:
            log("exec: {}".format(cmd))
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

    @staticmethod
    def device_fingerprint(serialno=None, tolog=True):
        return Adb.execute(["shell", "getprop", "ro.vendor.build.fingerprint"], serialno=serialno, tolog=tolog)

    @staticmethod
    def device_stayon(serialno=None, tolog=True, on=None):
        if on == None or type(on) is not bool:
            return
        return Adb.execute(["shell", "svc", "power", "stayon", str(on).lower()], serialno=serialno, tolog=tolog)

    @staticmethod
    def device_keyevent(serialno=None, tolog=True, keyevent=None):
        if not keyevent:
            return
        return Adb.execute(["shell", "input", "keyevent", str(keyevent)])

    @staticmethod
    def device_keyevent_menu(serialno=None, tolog=True):
        return Adb.device_keyevent(serialno, tolog, "KEYCODE_MENU")

    @staticmethod
    def device_keyevent_power(serialno=None, tolog=True):
        return Adb.device_keyevent(serialno, tolog, "KEYCODE_POWER")

    @staticmethod
    def device_lock(serialno=None, tolog=True):
        if tolog:
            log("lock the screen")
        Adb.device_stayon(serialno, tolog, on=True)
        Adb.device_keyevent_power(serialno, tolog)
        Adb.device_stayon(serialno, tolog, on=False)

    @staticmethod
    def device_unlock(serialno=None, tolog=True):
        if tolog:
            log("unlock the screen")
        Adb.device_stayon(serialno, tolog, on=True)
        Adb.device_keyevent_menu(serialno, tolog)
