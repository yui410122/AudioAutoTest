from com.dtmilano.android.viewclient import ViewClient
import datetime
import time

import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs.logger import Logger
from libs.adbutils import Adb

TAG = "dual-cs-call-test.py"

class DmesgEntry(object):
    def __init__(self, log_str):
        arr = log_str.split()
        timestamp_str = arr[0] if len(arr[0]) > 3 else "".join(arr[:2])
        self.timestamp = float(timestamp_str[1:-1])
        self.raw = log_str

def fetch_dmesg(latest_log=None, serialno=None):
    out, err = Adb.execute(["shell", "dmesg"], tolog=False, serialno=serialno)
    dmesg_entries = map(DmesgEntry, out.splitlines())
    if latest_log:
        dmesg_entries = filter(lambda x: x.timestamp > latest_log.timestamp, dmesg_entries)
    return dmesg_entries

def get_phone_state(serialno):
    out, err = Adb.execute(["shell", "dumpsys telephony.registry"], tolog=False, serialno=serialno)
    out = filter(lambda x: "mCallState" in x, out.splitlines())
    if len(out) == 0:
        return None
    return int(out[0].strip()[-1])

def wait_for_phone_state(state, timeout, serialno):
    call_time = datetime.datetime.now()
    while (datetime.datetime.now() - call_time).total_seconds() < timeout:
        if state == get_phone_state(serialno):
            return True

        time.sleep(0.1)
    return False

def log(msg):
    Logger.log(TAG, msg)

def start_cs_call(tel, serialno):
    Adb.execute(["shell", "am", "start", "-a", "android.intent.action.CALL", "-d", "tel:{}".format(tel)], serialno=serialno)

def pick_cs_call(serialno):
    Adb.execute(["shell", "input", "keyevent", "KEYCODE_CALL"], serialno=serialno)

def end_cs_call(serialno):
    Adb.execute(["shell", "input", "keyevent", "KEYCODE_ENDCALL"], serialno=serialno)

def run(num_iter, serialno1, phoneno1, serialno2, phoneno2):
    Logger.init(Logger.Mode.BOTH_FILE_AND_STDOUT)
    # Logger.init(Logger.Mode.STDOUT)
    Adb.init()

    for serialno in [serialno1, serialno2]:
        Adb.execute(["root"], serialno=serialno)
        Adb.execute(["shell", "'echo \'related\' > msm_subsys'"], serialno=serialno)
        Adb.execute(["shell", "svc", "power", "stayon", "true"], serialno=serialno)

        out, err = Adb.execute(["shell", "getprop", "ro.vendor.build.fingerprint"], serialno=serialno)
        out = out.strip()
        log("build number: '{}'".format(out))

    latest_dmesg1 = fetch_dmesg(serialno=serialno1)
    latest_dmesg2 = fetch_dmesg(serialno=serialno2)
    latest_dmesg1 = latest_dmesg1[0] if len(latest_dmesg1) > 0 else None
    latest_dmesg2 = latest_dmesg2[0] if len(latest_dmesg2) > 0 else None

    phone_dict = {
        serialno1: phoneno1,
        serialno2: phoneno2
    }
    last_dmesg_dict = {
        serialno1: latest_dmesg1,
        serialno2: latest_dmesg2
    }
    mt_serialno = serialno1
    mo_serialno = serialno2

    pass_trial_cnt = 0
    total_trial_cnt = 0
    invalid_trial_cnt = 0
    failed_trial_cnt = 0

    try:
        for i in range(int(num_iter)):
            log("-------------------- Dual-CS-call-test #{} --------------------".format(i+1))

            log("{} makes call to {} ({})".format(mo_serialno, mt_serialno, phone_dict[mt_serialno]))
            start_cs_call(tel=phone_dict[mt_serialno], serialno=mo_serialno)
            if not wait_for_phone_state(state=1, timeout=30, serialno=mt_serialno):
                log("There is no incoming call to {}, next trial".format(mt_serialno))
                end_cs_call(serialno=mo_serialno)
                end_cs_call(serialno=mt_serialno)
                invalid_trial_cnt += 1
                continue

            log("{} picks up the call".format(mt_serialno))
            pick_cs_call(serialno=mt_serialno)
            if not wait_for_phone_state(state=2, timeout=10, serialno=mo_serialno):
                log("{} is not in phone state 'MODE_INCALL', next trial".format(mo_serialno))
                end_cs_call(serialno=mo_serialno)
                end_cs_call(serialno=mt_serialno)
                invalid_trial_cnt += 1
                continue
            if not wait_for_phone_state(state=2, timeout=10, serialno=mt_serialno):
                log("{} is not in phone state 'MODE_INCALL', next trial".format(mt_serialno))
                end_cs_call(serialno=mo_serialno)
                end_cs_call(serialno=mt_serialno)
                invalid_trial_cnt += 1
                continue

            log("To check if ADSP crashes during the CS call")
            is_passed = True
            pass_trial_cnt += 1
            total_trial_cnt += 1
            retry = 15
            while retry > 0:
                for serialno in [mt_serialno, mo_serialno]:
                    latest_dmesg = last_dmesg_dict[serialno]
                    new_dmesgs = fetch_dmesg(latest_dmesg, serialno=serialno)
                    if len(new_dmesgs) > 0:
                        last_dmesg_dict[serialno] = new_dmesgs[-1]
                        adsp_ssr_demsgs = filter(lambda x: "Restart sequence requested for adsp" in x.raw, new_dmesgs)
                        if len(adsp_ssr_demsgs) > 0:
                            for dmesg in adsp_ssr_demsgs:
                                log("SSR log detected in {}: '{}'".format(serialno, dmesg.raw))
                            is_passed = False
                            break

                    phone_state = get_phone_state(serialno=serialno)
                    if phone_state == None:
                        log("the phone state of {} is unobtainable, something wrong".format(serialno))
                        is_passed = False
                        break
                    if phone_state == 0:
                        log("the phone state of {} is in idle, the call might be dropped".format(serialno))
                        is_passed = False
                        break

                if not is_passed:
                    for serialno in [mt_serialno, mo_serialno]:
                        out, err = Adb.execute(["bugreport"], serialno)
                        log("bugreport to '{}'".format(out.strip()))
                    pass_trial_cnt -= 1
                    failed_trial_cnt += 1
                    for serialno in [mt_serialno, mo_serialno]:
                        end_cs_call(serialno=serialno)
                    break

                if retry % 5 == 0:
                    log("{} switches path to '{}'".format(mo_serialno, "speaker" if retry/5 % 2 == 1 else "receiver"))
                    Adb.execute(["shell", "input", "tap", "1000", "1000"], tolog=False, serialno=mo_serialno)

                retry -= 1
                time.sleep(1)

            log("result: {} ({}/{})".format("pass" if retry == 0 else "fail", pass_trial_cnt, total_trial_cnt))
            log("pass: {}% ({}/{}), fail: {}% ({}/{}), invalid: {}% ({}/{})".format(
                    pass_trial_cnt*100.0/total_trial_cnt, pass_trial_cnt, total_trial_cnt,
                    failed_trial_cnt*100.0/total_trial_cnt, failed_trial_cnt, total_trial_cnt,
                    invalid_trial_cnt*100.0/(i+1), invalid_trial_cnt, i+1))
            for serialno in [mo_serialno, mt_serialno]:
                end_cs_call(serialno=serialno)
                wait_for_phone_state(state=0, timeout=10, serialno=serialno)
            time.sleep(5)
    except:
        pass

    for serialno in [serialno1, serialno2]:
        end_cs_call(serialno=serialno)
        Adb.execute(["shell", "svc", "power", "stayon", "false"], serialno=serialno)
    Logger.finalize()

if __name__ == "__main__":
    run(*sys.argv[1:])
