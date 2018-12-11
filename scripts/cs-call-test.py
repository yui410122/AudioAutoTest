from com.dtmilano.android.viewclient import ViewClient
import datetime
import time

import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs.logger import Logger
from libs.adbutils import Adb

TAG = "cs-call-test.py"

class SetModeEvent(object):
    def __init__(self, log_str):
        arr = log_str.split()
        timestamp_str = " ".join(arr[:2])
        timestamp_str = "{}000".format(timestamp_str)
        self.timestamp = datetime.datetime.strptime(timestamp_str, "%m-%d %H:%M:%S:%f")
        self.mode = mode_str = arr[2][8:-1]
        self.raw = log_str

class DmesgEntry(object):
    def __init__(self, log_str):
        arr = log_str.split()
        timestamp_str = arr[0] if len(arr[0]) > 3 else "".join(arr[:2])
        self.timestamp = float(timestamp_str[1:-1])
        self.raw = log_str

def get_phone_state(serialno):
    out, err = Adb.execute(["shell", "dumpsys telephony.registry"], tolog=False, serialno=serialno)
    out = filter(lambda x: "mCallState" in x, out.splitlines())
    if len(out) == 0:
        return None
    return int(out[0].strip()[-1])

def wait_for_phone_state(state, timeout, serialno):
    retry = timeout * 10
    while retry > 0:
        if state == get_phone_state(serialno):
            return True

        retry -= 1
        time.sleep(0.1)
    return False

def fetch_setmode_events(serialno):
    out, err = Adb.execute(["shell", "dumpsys", "audio"], tolog=False, serialno=serialno)
    setmode_events = filter(lambda x: "setMode" in x, out.splitlines())
    return map(SetModeEvent, setmode_events)

def fetch_dmesg(latest_log=None, serialno=None):
    out, err = Adb.execute(["shell", "dmesg"], tolog=False, serialno=serialno)
    dmesg_entries = map(DmesgEntry, out.splitlines())
    if latest_log:
        dmesg_entries = filter(lambda x: x.timestamp > latest_log.timestamp, dmesg_entries)
    return dmesg_entries

def log(msg):
    Logger.log(TAG, msg)

def start_cs_call(tel, serialno):
    Adb.execute(["shell", "am", "start", "-a", "android.intent.action.CALL", "-d", "tel:{}".format(tel)], serialno=serialno)

def end_cs_call(serialno):
    Adb.execute(["shell", "input", "keyevent", "KEYCODE_ENDCALL"], serialno=serialno)

def run(num_iter, serialno):
    Logger.init(Logger.Mode.BOTH_FILE_AND_STDOUT)
    # Logger.init(Logger.Mode.STDOUT)
    Adb.init()

    Adb.execute(["root"], serialno=serialno)
    Adb.execute(["shell", "'echo \'related\' > msm_subsys'"], serialno=serialno)
    Adb.execute(["shell", "svc", "power", "stayon", "true"], serialno=serialno)

    out, err = Adb.execute(["shell", "getprop", "ro.vendor.build.fingerprint"], serialno=serialno)
    out = out.strip()
    log("build number: '{}'".format(out))

    latest_dmesg = fetch_dmesg(serialno=serialno)
    latest_dmesg = latest_dmesg[0] if len(latest_dmesg) > 0 else None

    pass_trial_cnt = 0

    try:
        for i in range(num_iter):
            log("-------------------- CS call test #{} --------------------".format(i+1))

            events = fetch_setmode_events(serialno=serialno)
            latest_event = events[-1] if len(events) > 0 else None
            log("The latest setMode event: '{}'".format(latest_event.raw if latest_event else "None"))
            
            log("Make call to 0988102544")
            start_cs_call(tel="0988102544", serialno=serialno)
            log("Waiting to the mode 'MODE_IN_CALL'")
            if not wait_for_phone_state(state=2, timeout=10, serialno=serialno):
                log("The phone state never turns in 'MODE_IN_CALL', ignore this trial")
                continue

            log("To check if ADSP crashes during the CS call")
            is_passed = True
            pass_trial_cnt += 1
            retry = 15
            while retry > 0:
                new_dmesgs = fetch_dmesg(latest_dmesg, serialno=serialno)
                if len(new_dmesgs) > 0:
                    latest_dmesg = new_dmesgs[-1]
                    adsp_ssr_demsgs = filter(lambda x: "Restart sequence requested for adsp" in x.raw, new_dmesgs)
                    if len(adsp_ssr_demsgs) > 0:
                        for dmesg in adsp_ssr_demsgs:
                            log("SSR log detected: '{}'".format(dmesg.raw))
                        is_passed = False

                phone_state = get_phone_state(serialno=serialno)
                if phone_state == None:
                    log("the phone state is unobtainable, something wrong")
                    is_passed = False
                if phone_state == 0:
                    log("the phone state is in idle, the call might be dropped")
                    is_passed = False

                if not is_passed:
                    out, err = Adb.execute(["bugreport"])
                    log("bugreport to '{}'".format(out.strip()))
                    pass_trial_cnt -= 1
                    break

                if retry % 5 == 0:
                    log("switch path to '{}'".format("speaker" if retry/5 % 2 == 1 else "receiver"))
                    Adb.execute(["shell", "input", "tap", "1000", "1000"], tolog=False, serialno=serialno)

                retry -= 1
                time.sleep(1)

            log("result: {} ({}/{})".format("pass" if retry == 0 else "fail", pass_trial_cnt, i+1))
            end_cs_call(serialno=serialno)
            time.sleep(10)
    except:
        pass

    Adb.execute(["shell", "svc", "power", "stayon", "false"], serialno=serialno)
    Logger.finalize()

if __name__ == "__main__":
    num_iter = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    serialno = sys.argv[2] if len(sys.argv) > 2 else None
    run(num_iter=num_iter, serialno=serialno)
