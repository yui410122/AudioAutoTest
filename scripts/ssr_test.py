from com.dtmilano.android.viewclient import ViewClient
import os
import subprocess
import time
import datetime

import sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs import ROOT_DIR
from libs.audiofunction import AudioFunction, ToneDetectedDecision
from libs.logger import Logger
from libs.logcatlistener import LogcatListener, LogcatEvent

TAG = "ssr_test.py"

INTENT_PREFIX = "am broadcast -a"
HTC_INTENT_PREFIX = "audio.htc.com.intent."
DEVICE_MUSIC_DIR = "sdcard/Music/"
OUT_FREQ = 440

FILE_NAMES = [
    "440Hz.wav",
    "440Hz.mp3"
]

def push_files_if_needed(serialno):
    out, _ = subprocess.Popen(["adb", "-s", serialno, "shell", "ls", DEVICE_MUSIC_DIR], stdout=subprocess.PIPE).communicate()

    # The command "adb shell ls" might return several lines of strings where each line lists multiple file names
    # Then the result should be handled line by line:
    #           map function for split with spaces and reduce function for concatenate the results of each line
    files = reduce(lambda x, y: x+y, map(lambda s: s.split(), out.splitlines())) if out else []

    for file_to_pushed in FILE_NAMES:
        if file_to_pushed in files:
            continue
        out, _ = subprocess.Popen(["find", ROOT_DIR, "-name", file_to_pushed], stdout=subprocess.PIPE).communicate()
        file_path = out.splitlines()[0] if out else None
        if file_path:
            os.system("adb -s {} push {} {} > /dev/null".format(serialno, file_path, DEVICE_MUSIC_DIR))
        else:
            raise ValueError("Cannot find the file \"{}\", please place it under the project tree.".format(file_to_pushed))

def trigger_ssr(device):
    device.shell("asound -crashdsp")

def dev_playback_nonoffload(device):
    cmd = " ".join([INTENT_PREFIX, HTC_INTENT_PREFIX + "playback.nonoffload", "--es", "file", "440Hz.wav"])
    device.shell(cmd)

def dev_playback_offload(device):
    cmd = " ".join([INTENT_PREFIX, HTC_INTENT_PREFIX + "playback.offload", "--es", "file", "440Hz.mp3"])
    device.shell(cmd)

def dev_playback_stop(device):
    cmd = " ".join([INTENT_PREFIX, HTC_INTENT_PREFIX + "playback.stop"])
    device.shell(cmd)

def dev_record_start(device):
    cmd = " ".join([INTENT_PREFIX, HTC_INTENT_PREFIX + "record.start", "--ei", "spt_xmax", "1000"])
    device.shell(cmd)

def dev_record_stop(device):
    cmd = " ".join([INTENT_PREFIX, HTC_INTENT_PREFIX + "record.stop"])
    device.shell(cmd)

def dev_print_detected_tone(device):
    cmd = " ".join([INTENT_PREFIX, HTC_INTENT_PREFIX + "print.properties"])
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

    push_files_if_needed(serialno)

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
    log("trigger_ssr()")
    trigger_ssr(device)
    elapsed = th.wait_for_event(DetectionStateChangeListenerThread.Event.RISING_EDGE, timeout=10)
    log("elapsed: {} ms".format(elapsed))
    elapsed = th.wait_for_event(DetectionStateChangeListenerThread.Event.FALLING_EDGE, timeout=10)
    log("elapsed: {} ms".format(elapsed))

    log("dev_record_stop")
    dev_record_stop(device)

    log("ToneDetectedDecision.stop_listen()")
    ToneDetectedDecision.stop_listen()

    AudioFunction.finalize()
    Logger.finalize()


import threading
import datetime

try:
    import queue
except ImportError:
    import Queue as queue

class DetectionStateChangeListenerThread(threading.Thread):
    class Event(object):
        RISING_EDGE = "rising"
        FALLING_EDGE = "falling"

    def __init__(self):
        super(DetectionStateChangeListenerThread, self).__init__()
        self.daemon = True
        self.stoprequest = threading.Event()
        self.event_q = queue.Queue()
        self.current_event = None

    def reset(self):
        self.current_event = None

    def tone_detected_event_cb(self, event):
        log(event)
        self._handle_event(event)

    def _handle_event(self, event):
        if self.current_event and self.current_event[1] != event[1]:
            rising_or_falling = DetectionStateChangeListenerThread.Event.RISING_EDGE \
                            if event[1] == ToneDetectedDecision.Event.TONE_DETECTED else \
                                DetectionStateChangeListenerThread.Event.FALLING_EDGE

            t2 = datetime.datetime.strptime(event[0], ToneDetectedDecision.TIME_STR_FORMAT)
            t1 = datetime.datetime.strptime(self.current_event[0], ToneDetectedDecision.TIME_STR_FORMAT)
            t_diff = t2 - t1
            self.event_q.put((rising_or_falling, t_diff.total_seconds()*1000.0))

        self.current_event = event

    def wait_for_event(self, event, timeout):
        cnt = 0
        while cnt < timeout*10:
            cnt += 1
            if self.stoprequest.isSet():
                return -1
            try:
                ev = self.event_q.get(timeout=0.1)
                if ev[0] == event:
                    return ev[1]
            except queue.Empty:
                pass
        return -1

    def join(self, timeout=None):
        self.stoprequest.set()
        super(DetectionStateChangeListenerThread, self).join(timeout)

    def run(self):
        while self.stoprequest.isSet():
            time.sleep(0.1)

if __name__ == "__main__":
    run()
