from com.dtmilano.android.viewclient import ViewClient
import os
import subprocess
import time
import threading

import sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs import ROOT_DIR
from libs.audiofunction import AudioFunction, ToneDetectedDecision, DetectionStateChangeListenerThread
from libs.logger import Logger

TAG = "example.py"

INTENT_PREFIX = "am broadcast -a"
HTC_INTENT_PREFIX = "audio.htc.com.intent."
OUT_FREQ = 440

def dev_record_start(device):
    cmd = " ".join([INTENT_PREFIX, HTC_INTENT_PREFIX + "record.start", "--ei", "spt_xmax", "1000"])
    device.shell(cmd)

def dev_record_stop(device):
    cmd = " ".join([INTENT_PREFIX, HTC_INTENT_PREFIX + "record.stop"])
    device.shell(cmd)

def log(msg):
    Logger.log(TAG, msg)

def run():
    AudioFunction.init()
    Logger.init(True)
    os.system("adb start-server > /dev/null")

    package = "com.htc.audiofunctionsdemo"
    activity = ".activities.MainActivity"
    component = package + "/" + activity

    device, serialno = ViewClient.connectToDeviceOrExit()
    vc = ViewClient(device, serialno, autodump=False)

    if not device.isScreenOn():
        device.wake()
        vc.dump()

        import StringIO as sio
        so = sio.StringIO()
        vc.traverse(stream=so)
        if "lockscreen" in so.getvalue():
            device.unlock()

    # keymap reference:
    #   https://github.com/dtmilano/AndroidViewClient/blob/master/src/com/dtmilano/android/adb/androidkeymap.py
    device.press("HOME")
    time.sleep(1)
    device.startActivity(component=component)
    time.sleep(1)

    record_task_run(device, serialno)

    AudioFunction.finalize()
    Logger.finalize()

def record_task_run(device, serialno):
    log("dev_record_start")
    dev_record_start(device)
    time.sleep(2)

    th = DetectionStateChangeListenerThread()
    th.start()

    log("ToneDetectedDecision.start_listen(serialno={}, target_freq={})".format(serialno, OUT_FREQ))
    ToneDetectedDecision.start_listen(serialno=serialno, target_freq=OUT_FREQ, cb=lambda event: th.tone_detected_event_cb(event))
    log("AudioFunction.play_sound(out_freq={})".format(OUT_FREQ))
    AudioFunction.play_sound(out_freq=OUT_FREQ)

    time.sleep(3)

    def stop_then_play():
        log("thread stops the playback")
        AudioFunction.stop_audio()
        time.sleep(4)
        log("thread starts the playback")
        AudioFunction.play_sound(out_freq=OUT_FREQ)
        log("thread returns")

    threading.Thread(target=stop_then_play).start()
    log("Waiting for {} Hz pure tone detected".format(OUT_FREQ))
    elapsed = th.wait_for_event(DetectionStateChangeListenerThread.Event.RISING_EDGE, timeout=10)
    log("elapsed: {} ms".format(elapsed))
    log("Trying to wait a timeout event")
    elapsed = th.wait_for_event(DetectionStateChangeListenerThread.Event.FALLING_EDGE, timeout=10)
    log("elapsed: {} ms".format(elapsed))

    log("dev_record_stop")
    dev_record_stop(device)

    log("ToneDetectedDecision.stop_listen()")
    ToneDetectedDecision.stop_listen()
    AudioFunction.stop_audio()


if __name__ == "__main__":
    run()
