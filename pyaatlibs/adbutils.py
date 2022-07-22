import subprocess
import threading
import signal
import re
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
    SERIAL_TO_IP_INFO = {}

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
    def execute(child, cmd, serialno=None, tolog=True, retbyte=False, timeoutsec=None):
        child._check_init()

        if serialno and not serialno in child.get_devices() and \
            child.is_device_available(serialno=serialno):
            ip_info = Adb.SERIAL_TO_IP_INFO[serialno]
            ip_addr = "{}:{}".format(ip_info["addr"], ip_info["port"])
            child._log("use Wifi adb: addr[{}] of serialno '{}'".format(ip_addr, serialno), tolog)
            serialno = ip_addr

        return child._execute(cmd, serialno, tolog, retbyte, timeoutsec)

    @classmethod
    def _execute(child, cmd, serialno=None, tolog=True, retbyte=False, timeoutsec=None):
        if not isinstance(cmd, list):
            cmd = [cmd]

        cmd_prefix = ["adb"]
        if serialno:
            cmd_prefix += ["-s", serialno]

        cmd = cmd_prefix + cmd
        child._log("exec: {}".format(cmd), tolog)
        try:
            out, err =  subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate(timeout=timeoutsec)
        except:
            out = b""
            err = b"ADB execution timed out"

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
    def is_device_available(child, serialno, tolog=True):
        devices = child.get_devices(tolog=tolog)

        # establish unknown ip
        for device in devices:
            m = re.match("(?P<addr>(\\d+\\.?)+)(:(?P<port>\\d+))?$", device)
            if not m:
                continue

            ip_info = m.groupdict()
            if ip_info in Adb.SERIAL_TO_IP_INFO.values():
                continue

            out, err = child.execute(["shell", "getprop ro.serialno"], serialno=device)
            if len(err) > 0:
                continue

            Adb.SERIAL_TO_IP_INFO[out.strip()] = ip_info
            child._log("update wifi adb device: {}, {}".format(out.strip(), ip_info), tolog)

        if serialno in devices:
            return True

        if serialno in Adb.SERIAL_TO_IP_INFO and "port" in Adb.SERIAL_TO_IP_INFO[serialno]:
            ip_info = Adb.SERIAL_TO_IP_INFO[serialno]
            ip_addr = "{}:{}".format(ip_info["addr"], ip_info["port"])
            if ip_addr in devices:
                return True

        return False

    @classmethod
    def is_wifi_adb_supported(child, serialno, tolog=True):
        devices = child.get_devices(tolog=tolog)
        if not serialno in devices:
            child._log("device '{}' not found".format(serialno), tolog)
            return False

        out, err = child.execute(["shell", "ip addr show wlan0"], serialno=serialno, tolog=tolog)
        if len(err) > 0:
            child._log("got error: {}".format(err.strip()), tolog)
            return False

        for line in out.splitlines():
            m = re.match("\\s*inet (?P<addr>(\\d+\\.?)+)/", line)
            if not m:
                continue

            Adb.SERIAL_TO_IP_INFO[serialno] = dict(m.groupdict())
            return True

        if serialno in Adb.SERIAL_TO_IP_INFO:
            del Adb.SERIAL_TO_IP_INFO[serialno]
        return False

    @classmethod
    def enable_wifi_adb(child, serialno, port=5555, tolog=True):
        if not serialno in Adb.SERIAL_TO_IP_INFO \
            and not child.is_wifi_adb_supported(serialno=serialno, tolog=tolog):
            child._log("Wifi adb is not supported on device '{}'".format(serialno), tolog)
            return False

        _, err = Adb.execute(["tcpip", str(port)], serialno=serialno)
        if len(err) > 0:
            child._log("got error: {}".format(err.strip()), tolog)
            return False

        time.sleep(1)

        ip_info = Adb.SERIAL_TO_IP_INFO[serialno]
        ip_addr = "{}:{}".format(ip_info["addr"], port)
        out, err = child.execute(["connect", ip_addr])
        if len(err) > 0:
            child._log("got error: {}".format(err.strip()), tolog)
            return False

        if not re.match("(already )?connected to {}".format(ip_addr), out.strip()):
            child._log("unexpected output: {}".format(out.strip()), tolog)
            return False

        ip_info["port"] = str(port)
        return True

    @classmethod
    def disable_wifi_adb(child, serialno, tolog=True):
        if not serialno in Adb.SERIAL_TO_IP_INFO:
            child._log("Wifi adb is not constructed on device '{}'".format(serialno), tolog)
            return False

        ip_info = Adb.SERIAL_TO_IP_INFO[serialno]
        ip_addr = "{}:{}".format(ip_info["addr"], ip_info["port"])

        out, err = child.execute(["disconnect", ip_addr])
        if len(err) > 0:
            child._log("got error: {}".format(err.strip()), tolog)
            return False

        if not re.match("disconnected {}".format(ip_addr), out.strip()):
            child._log("unexpected output: {}".format(out.strip()), tolog)
            return False

        del Adb.SERIAL_TO_IP_INFO[serialno]
        return True

    @classmethod
    def get_wifi_adb_ip_addr(child, serialno, tolog=True):
        if not serialno in Adb.SERIAL_TO_IP_INFO \
            and not child.is_wifi_adb_supported(serialno=serialno, tolog=tolog):
            child._log("Wifi adb is not supported on device '{}'".format(serialno), tolog)
            return None

        ip_info = Adb.SERIAL_TO_IP_INFO[serialno]
        child._log("get_wifi_adb_ip_addr: ip_info: {}".format(ip_info), tolog)
        if not "addr" in ip_info or not "port" in ip_info:
            return None

        ip_addr = "{}:{}".format(ip_info["addr"], ip_info["port"])
        child._log(
            "get_wifi_adb_ip_addr: addr[{}] of serialno '{}'".format(ip_addr, serialno), tolog)

        out, err = child.execute(["shell", "getprop ro.serialno"], serialno=ip_addr)
        out = out.strip()
        if len(err):
            child._log("get_wifi_adb_ip_addr: get error: {}".format(err), tolog)
            return None

        if out != serialno:
            child._log("get_wifi_adb_ip_addr: the serialno does not match: " \
                "detected[{}], expected[{}]".format(serialno, out), tolog)
            return None

        return ip_addr

    @classmethod
    def wait_for_device(child, serialno, timeoutsec, tolog=True):
        while not child.is_device_available(serialno=serialno, tolog=tolog) and timeoutsec > 0:
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

