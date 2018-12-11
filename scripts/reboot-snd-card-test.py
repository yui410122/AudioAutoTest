import subprocess
import datetime
import time

import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs.logger import Logger
from libs.adbutils import Adb
from libs.trials import TrialHelper, Trial

TAG = "reboot-snd-card-test.py"

def log(msg):
    Logger.log(TAG, msg)

def wait_for_device(serialno):
    cnt = 0
    start = datetime.datetime.now()
    while True:
        out, _ = Adb.execute(["devices"], tolog=False)
        if serialno in out:
            log("adb device '{}' available".format(serialno))
            return
        wait_time = (datetime.datetime.now() - start).total_seconds()
        if int(wait_time) % 5 == 0:
            if int(wait_time) / 5 > cnt:
                log("wait_for_device('{}'): {} secs".format(serialno, wait_time))
                cnt += 1

def wait_for_snd_card(serialno, timeout):
    start = datetime.datetime.now()
    while True:
        wait_time = (datetime.datetime.now() - start).total_seconds()
        if wait_time > timeout:
            return -1

        out, _ = Adb.execute(["shell", "cat", "/proc/asound/cards"], serialno=serialno, tolog=False)
        if len(out.splitlines()) > 1:
            log("<soundcard name>")
            for line in out.splitlines():
                log(line)
            return wait_time*1000
        time.sleep(0.02)

def error_handle(serialno, trial):
    out, _ = Adb.execute(["shell", "cat", "/proc/asound/cards"], serialno=serialno)
    for line in out.splitlines():
        log(line)

    out, _ = Adb.execute(["shell", "lsmod"], serialno=serialno)
    for line in out.splitlines():
        log(line)

    out, _ = Adb.execute(["shell", "dmesg"], serialno=serialno)
    log_file_name = "./log/dmesg-{}-{}.txt".format(serialno, trial.ds["timestamp"])
    with open(log_file_name, "w") as f:
        f.write(out)
    log("write the kernel log to {}".format(log_file_name))
    for line in out.splitlines():
        if "rt5514" in line or "cs35l36" in line:
            log(line)

def run(num_iter, serialno):
    Logger.init(Logger.Mode.BOTH_FILE_AND_STDOUT)
    Adb.init()

    out, err = Adb.execute(["shell", "getprop", "ro.vendor.build.fingerprint"], serialno=serialno)
    log("build number: '{}'".format(out.strip()))

    report_file_name = "./log/test_report_{}.json".format(serialno)

    try:
        trials = TrialHelper.load(report_file_name)
        
    except:
        trials = []

    if len(trials) > 0:
        pass_cnt = len(filter(lambda x: x, TrialHelper.pass_fail_list(trials, check_func=lambda x: not x.ds["error-msg"])))
        fail_cnt = len(trials) - pass_cnt
    else:
        pass_cnt, fail_cnt = 0, 0

    try:
        for i in range(int(num_iter)):
            log("-------------------- reboot-snd-card-test #{} --------------------".format(i+1))
            trial = Trial(taskname="reboot-snd-card-test", pass_check=lambda x: not x.ds["error-msg"])

            log("reboot the device")
            _, err = Adb.execute(["reboot"], serialno=serialno)
            if len(err) > 0:
                log("adb error: '{}'".format(err.strip()))
                time.sleep(5)
                continue

            time.sleep(5)
            try:
                wait_for_device(serialno=serialno)
            except:
                break

            log("now checking the snd card")
            elapsed = wait_for_snd_card(serialno=serialno, timeout=30)
            if elapsed < 0:
                fail_cnt += 1
                trial.invalidate(errormsg="no sound card")
                error_handle(serialno=serialno, trial=trial)
            else:
                pass_cnt += 1
                log("elapsed: {} ms".format(elapsed))
                trial.put_extra("elapsed", elapsed)
    
            trials.append(trial)
            with open(report_file_name, "w") as f:
                f.write(TrialHelper.to_json(trials))

            log("pass/fail/total: {}/{}/{}".format(pass_cnt, fail_cnt, pass_cnt+fail_cnt))

            time.sleep(20)
    except:
        pass

    Logger.finalize()

if __name__ == "__main__":
    run(*sys.argv[1:3])