import subprocess
from libs.logger import Logger

class Adb(object):
    HAS_BEEN_INIT = False
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
    def execute(child, cmd, serialno=None, tolog=True):
        child._check_init()
        return child._execute(cmd, serialno, tolog)

    @classmethod
    def _execute(child, cmd, serialno, tolog=True):
        if not isinstance(cmd, list):
            cmd = [cmd]

        cmd_prefix = ["adb"]
        if serialno:
            cmd_prefix += ["-s", serialno]

        cmd = cmd_prefix + cmd
        if tolog:
            Logger.log(child.TAG, "exec: {}".format(cmd))
        out, err =  subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

        if not isinstance(out, str):
            out = out.decode("utf-8")
        if not isinstance(err, str):
            err = err.decode("utf-8")

        return out, err

    @classmethod
    def get_devices(child, tolog=True):
        out, _ = child.execute(["devices"], tolog=tolog)
        devices = list(map(lambda x: x.strip(), out.splitlines()))
        del devices[0]
        devices = [x.split()[0] for x in devices if len(x) > 0 and x.split()[1] == "device"]
        return devices

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
        return child.execute(["shell", "input", "keyevent", str(keyevent)])

    @classmethod
    def device_keyevent_menu(child, serialno=None, tolog=True):
        return child.device_keyevent(serialno, tolog, "KEYCODE_MENU")

    @classmethod
    def device_keyevent_power(child, serialno=None, tolog=True):
        return child.device_keyevent(serialno, tolog, "KEYCODE_POWER")

    @classmethod
    def device_lock(child, serialno=None, tolog=True):
        if tolog:
            Logger.log(child.TAG, "lock the screen")
        child.device_stayon(serialno, tolog, on=True)
        child.device_keyevent_power(serialno, tolog)
        child.device_stayon(serialno, tolog, on=False)

    @classmethod
    def device_unlock(child, serialno=None, tolog=True):
        if tolog:
            Logger.log(child.TAG, "unlock the screen")
        child.device_stayon(serialno, tolog, on=True)
        child.device_keyevent_menu(serialno, tolog)

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

