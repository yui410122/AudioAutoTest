import sys
import time
import datetime
import subprocess

def now():
    return datetime.datetime.now()

def run_cmd(cmd):
    return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

def wait_for_boot_to_home(serialno, timeout):
    cnt = 0
    time_start = now()
    while (now() - time_start).total_seconds() < timeout:
        out, err = run_cmd("adb -s {} shell dumpsys window".format(serialno))
        if len(err) == 0:
            cnt += 1
            if cnt == 5:
                return True
            continue
        else:
            cnt = 0
        time.sleep(1)

    return False

def wait_for_adb_device(serialno):
    while True:
        out, _ = run_cmd("adb devices")
        if len(filter(lambda x: serialno in x, out.splitlines())) > 0:
            return True

def run(serialno):
    try:
        while True:
            print("wait for booting to home")
            if wait_for_boot_to_home(serialno=serialno, timeout=120):
                print("The phone '{}' is booting to home".format(serialno))
                return
            print("reboot the device")
            run_cmd("adb -s {} reboot".format(serialno))
            print("wait for the device")
            wait_for_adb_device(serialno=serialno)
    except:
        pass

if __name__ == "__main__":
    run(serialno=sys.argv[1])
