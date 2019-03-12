import subprocess
import time
from com.dtmilano.android.viewclient import ViewClient

REBOOT_CMDS = [
    "adb -s {} reboot",
    "hwinner-wait-for-adb-devices",
    "adb -s {} root",
    "hwinner-wait-for-adb-devices",
    "adb -s {} remount",
    "hwinner-wait-for-adb-devices",
    "adb -s {} shell pm disable com.android.ramdump",
]

def run_cmd(cmd):
    return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

def run(serialno=None):
    device, serialno = ViewClient.connectToDeviceOrExit(serialno=serialno)
    for cmd in REBOOT_CMDS:
        run_cmd(cmd.format(serialno))

    time.sleep(3)
    device, serialno = ViewClient.connectToDeviceOrExit(serialno=serialno)
    device.unlock()
    time.sleep(3)
    device.startActivity("com.htc.audiofunctionsdemo/.activities.MainActivity")

if __name__ == "__main__":
    import sys
    serialno = None if len(sys.argv) < 2 else sys.argv[1]
    run(serialno=serialno)
