import subprocess
import time

import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs.logger import Logger
from libs.aatapp import AATApp
from libs.audiofunction import AudioFunction, ToneDetector, DetectionStateListener
from libs.adbutils import Adb

TAG = "patch-test.py"

def log(msg):
    Logger.log(TAG, msg)

def main():
    Logger.init(Logger.Mode.STDOUT)
    Adb.init()

    trial_num = 1
    pass_trial_num = 0
    try:
        while True:
            Adb.execute(["shell", "input", "keyevent", "POWER"])
            Adb.execute(["shell", AATApp.INTENT_PREFIX, AATApp.HTC_INTENT_PREFIX + "record.start"])
            time.sleep(2)
            log("play 220Hz_44100Hz_15secs_2ch.wav")
            os.system("adb shell tinyplay /data/220Hz_44100Hz_15secs_2ch.wav > /dev/null &")
            retry = 5
            detected = False
            while retry > 0:
                out, err = Adb.execute(["shell", "cat", "/storage/emulated/0/AudioFunctionsDemo-record-prop.txt"], tolog=False)
                try: out = float(out.split(",")[0])
                except: out = 0.0

                if out > 200.0 and out < 240.0:
                    log("detected tones.")
                    detected = True
                    break

                time.sleep(0.1)

            time.sleep(1)

            log("turn off the screen.")
            Adb.execute(["shell", "input", "keyevent", "POWER"])

            time.sleep(2)

            retry = 5
            detected = False
            detected_cnt = 0
            while retry > 0:
                out, err = Adb.execute(["shell", "cat", "/storage/emulated/0/AudioFunctionsDemo-record-prop.txt"], tolog=False)
                try: out = float(out.split(",")[0])
                except: out = 0.0

                if out > 200.0 and out < 240.0:
                    log("detected tones.")
                    detected_cnt += 1
                    if detected_cnt == 10:
                        log("detected for a sufficient times.")
                        detected = True
                        break

                time.sleep(0.1)

            if detected:
                pass_trial_num += 1
                log("trial #{}: passed. ({}/{})".format(trial_num, pass_trial_num, trial_num))
            else:
                log("trial #{}: failed. ({}/{})".format(trial_num, pass_trial_num, trial_num))

            trial_num += 1
            time.sleep(15)

    except:
        pass

    Logger.finalize()

if __name__ == "__main__":
    main()
