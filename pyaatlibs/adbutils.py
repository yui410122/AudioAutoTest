import subprocess
import threading
import signal
from pyaatlibs.logger import Logger

class AdbScreenRecordingThread(threading.Thread):
    def __init__(self, serialno):
        super(AdbScreenRecordingThread, self).__init__()
        self.serialno = serialno
        self.daemon = True
        self.proc = None

    def terminate(self):
        self.proc.stdin.close()
        self.proc.terminate()
        self.proc.wait(timeout=1)
        super(AdbScreenRecordingThread, self).join(timeout=1)

    def run(self):
        # shell_cmd = "screenrecord --bit-rate 4000000 /sdcard/screenrecord.mp4"
        shell_cmd = "screenrecord /sdcard/screenrecord.mp4"
        cmd = ["adb", "-s", self.serialno, "shell", shell_cmd]
        Logger.log("AdbScreenRecordingThread", "threadloop is running with the command '{}'".format(cmd))
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

class Adb(object):
    HAS_BEEN_INIT = False
    SCREEN_RECORDING_THREADS = {}
    TAG = "Adb"

    @staticmethod
    def init():
        Adb._execute("start-server", None)
        Adb.HAS_BEEN_INIT = True

    @staticmethod
    def _check_init():
        if not Adb.HAS_BEEN_INIT:
            Adb.init()

    @classmethod
    def _log(child, msg, tolog):
        if not tolog:
            return
        Logger.log(child.TAG, msg)

    @classmethod
    def execute(child, cmd, serialno=None, tolog=True, retbyte=False):
        child._check_init()
        return child._execute(cmd, serialno, tolog, retbyte)

    @classmethod
    def _execute(child, cmd, serialno, tolog=True, retbyte=False):
        if not isinstance(cmd, list):
            cmd = [cmd]

        cmd_prefix = ["adb"]
        if serialno:
            cmd_prefix += ["-s", serialno]

        cmd = cmd_prefix + cmd
        child._log("exec: {}".format(cmd), tolog)
        out, err =  subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

        if not isinstance(out, str) and not retbyte:
            try:
                out = out.decode("utf-8")
            except:
                pass
        if not isinstance(err, str) and not retbyte:
            try:
                err = err.decode("utf-8")
            except:
                pass

        return out, err

    @classmethod
    def get_devices(child, tolog=True):
        out, _ = child.execute(["devices"], tolog=tolog)
        devices = list(map(lambda x: x.strip(), out.splitlines()))
        del devices[0]
        devices = [x.split()[0] for x in devices if len(x) > 0 and x.split()[1] == "device"]
        return devices

    @classmethod
    def wait_for_device(child, serialno, timeoutsec, tolog=True):
        while not serialno in child.get_devices(tolog=tolog) and timeoutsec > 0:
            time.sleep(1)
            timeoutsec -= 1

    @classmethod
    def device_fingerprint(child, serialno=None, tolog=True):
        return child.execute(["shell", "getprop", "ro.vendor.build.fingerprint"], serialno=serialno, tolog=tolog)

    @classmethod
    def device_stayon(child, serialno=None, tolog=True, on=None):
        if on == None or type(on) is not bool:
            return
        return child.execute(["shell", "svc", "power", "stayon", str(on).lower()], serialno=serialno, tolog=tolog)

    @classmethod
    def device_keyevent(child, serialno=None, tolog=True, keyevent=None):
        if not keyevent:
            return
        return child.execute(["shell", "input", "keyevent", str(keyevent)], serialno=serialno, tolog=tolog)

    @classmethod
    def device_keyevent_menu(child, serialno=None, tolog=True):
        return child.device_keyevent(serialno, tolog, "KEYCODE_MENU")

    @classmethod
    def device_keyevent_power(child, serialno=None, tolog=True):
        return child.device_keyevent(serialno, tolog, "KEYCODE_POWER")

    @classmethod
    def device_lock(child, serialno=None, tolog=True):
        child._log("lock the screen", tolog)
        child.device_stayon(serialno, tolog, on=True)
        child.device_keyevent_power(serialno, tolog)
        child.device_stayon(serialno, tolog, on=False)

    @classmethod
    def device_unlock(child, serialno=None, tolog=True):
        child._log("unlock the screen", tolog)
        child.device_stayon(serialno, tolog, on=True)
        child.device_keyevent_menu(serialno, tolog)

    @staticmethod
    def screen_recording_start(serialno=None, tolog=True):
        if not serialno:
            devices = Adb.get_devices()
            if len(devices) == 0:
                return False
            serialno = devices[0]

        if serialno in Adb.SCREEN_RECORDING_THREADS:
            return False

        th = AdbScreenRecordingThread(serialno)
        th.start()
        Adb.SCREEN_RECORDING_THREADS[serialno] = th
        return True

    @staticmethod
    def screen_recording_stop(pullto, serialno=None, tolog=True):
        if not serialno:
            devices = Adb.get_devices()
            if len(devices) == 0:
                return False
            serialno = devices[0]

        if not serialno in Adb.SCREEN_RECORDING_THREADS:
            return False

        th = Adb.SCREEN_RECORDING_THREADS[serialno]
        th.terminate()
        del Adb.SCREEN_RECORDING_THREADS[serialno]

        time.sleep(1)
        if pullto:
            Adb.execute(["pull", "/sdcard/screenrecord.mp4", pullto], serialno=serialno)
        return True

try:
    import functools
    reduce = functools.reduce
except:
    pass

import time

class AudioAdb(Adb):
    TAG = "AudioAdb"

    @staticmethod
    def get_stream_volumes(serialno=None, tolog=True):
        out, _ = AudioAdb.execute(["shell", "dumpsys audio"], serialno=serialno, tolog=tolog)
        lines = [line.strip() if isinstance(line, str) else line.decode("utf-8").strip() for line in out.splitlines()]
        idices = [idx for idx, line in enumerate(lines) if line.startswith("- STREAM")]
        if len(idices) < 2:
            return None
        nlines = idices[1] - idices[0]
        volumes = {}

        def parse_str_v(str_v):
            str_v = str_v.strip()
            if str_v.lower() in ["true", "false"]:
                return str_v.lower() == "true"

            if str_v.isdigit():
                return int(str_v)

            try:
                return float(str_v)
            except ValueError:
                return str_v

        for idx in idices:
            stream = lines[idx].split()[1][:-1]
            volumes[stream] = {}
            for line in lines[idx+1:idx+nlines]:
                result = [fragment.split(",") for fragment in line.split(":")]
                result = reduce(lambda x, y: x + y, result)
                if len(result) == 2:
                    k, v = result
                    volumes[stream][k.strip()] = parse_str_v(v)
                elif len(result) % 2 == 1:
                    k = result[0]
                    volumes[stream][k] = {}
                    for idx in range(1, len(result), 2):
                        subk, v = result[idx], result[idx+1]
                        volumes[stream][k][subk.strip()] = parse_str_v(v)

        return volumes

    @staticmethod
    def adj_volume(keycode, times, serialno=None, tolog=True):
        for x in range(times):
            AudioAdb.execute(["shell", "input keyevent {}".format(keycode)], serialno=serialno, tolog=tolog)
            time.sleep(0.2)

    @staticmethod
    def inc_volume(serialno=None, tolog=True, volume_steps=1):
        AudioAdb.adj_volume(serialno=serialno, tolog=tolog, keycode=24, times=volume_steps+1)

    @staticmethod
    def dec_volume(serialno=None, tolog=True, volume_steps=1):
        AudioAdb.adj_volume(serialno=serialno, tolog=tolog, keycode=25, times=volume_steps+1)

