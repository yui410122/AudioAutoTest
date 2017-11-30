from com.dtmilano.android.viewclient import ViewClient
import os
import subprocess
import time
import datetime
import json

import sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs import ROOT_DIR
from libs.adbutils import Adb
from libs.audiofunction import AudioFunction, ToneDetector, DetectionStateChangeListenerThread
from libs.logger import Logger
from libs.aatapp import AATApp

TAG = "ssr_test.py"

DEVICE_MUSIC_DIR = "sdcard/Music/"
OUT_FREQ = 440
BATCH_SIZE = 5

FILE_NAMES = [
    "440Hz.wav",
    "440Hz.mp3"
]

def push_files_if_needed(serialno):
    out, _ = Adb.execute(cmd=["shell", "ls", DEVICE_MUSIC_DIR], serialno=serialno)

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

def log(msg):
    Logger.log(TAG, msg)

def run(num_iter=1):
    AudioFunction.init()
    Logger.init(Logger.Mode.BOTH_FILE_AND_STDOUT)
    Adb.init()

    os.system("mkdir -p {}/ssr_report > /dev/null".format(ROOT_DIR))
    t = datetime.datetime.now()
    filename = "report_{}{:02d}{:02d}_{:02d}{:02d}{:02d}.json".format(t.year, t.month, t.day, t.hour, t.minute, t.second)

    package = "com.htc.audiofunctionsdemo"
    activity = ".activities.MainActivity"
    component = package + "/" + activity

    device, serialno = ViewClient.connectToDeviceOrExit(serialno=None)
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

    trials = []
    batch_count = 1
    while num_iter > 0:
        log("-------- batch_run #{} --------".format(batch_count))
        trials_batch = []
        trials_batch += playback_task_run(device, num_iter=min([num_iter, BATCH_SIZE]))
        trials_batch += record_task_run(device, serialno, num_iter=min([num_iter, BATCH_SIZE]))
        trials_batch += voip_task_run(device, serialno, num_iter=min([num_iter, BATCH_SIZE]))

        map(lambda trial: trial.put_extra(name="batch_id", value=batch_count), trials_batch)
        trials += trials_batch
        with open("{}/ssr_report/{}".format(ROOT_DIR, filename), "w") as f:
            f.write(json.dumps( map(lambda trial: trial.ds, trials), indent=4 ))

        num_iter -= BATCH_SIZE
        batch_count += 1

    AudioFunction.finalize()
    Logger.finalize()


def playback_task_run(device, num_iter=1):
    log("playback_task_run++")

    trials = []

    th = DetectionStateChangeListenerThread()
    th.start()

    log("ToneDetector.start_listen(target_freq={})".format(OUT_FREQ))
    ToneDetector.start_listen(target_freq=OUT_FREQ, cb=lambda event: th.tone_detected_event_cb(event))

    funcs = {
        "nonoffload": AATApp.playback_nonoffload,
        "offload"   : AATApp.playback_offload
    }

    for i in range(num_iter):
        log("-------- playback_task #{} --------".format(i+1))
        for name, func in funcs.items():
            trial = Trial(taskname="playback_{}".format(name))
            trial.put_extra(name="iter_id", value=i+1)

            log("dev_playback_{}_start".format(name))
            time.sleep(1)
            th.reset()
            func(device)

            if th.wait_for_event(DetectionStateChangeListenerThread.Event.ACTIVE, timeout=5) < 0:
                log("the tone was not detected, abort the iteration this time...")
                AATApp.playback_stop(device)
                trial.invalidate(errormsg="early return, possible reason: rx no sound")
                trials.append(trial)
                continue
            time.sleep(1)

            log("trigger_ssr()")
            AATApp.trigger_ssr(device)
            log("Waiting for SSR recovery")
            elapsed = th.wait_for_event(DetectionStateChangeListenerThread.Event.RISING_EDGE, timeout=10)
            log("elapsed: {} ms".format(elapsed))

            trial.put_extra(name="elapsed", value=elapsed)
            trials.append(trial)

            log("dev_playback_stop")
            AATApp.playback_stop(device)
            th.wait_for_event(DetectionStateChangeListenerThread.Event.INACTIVE, timeout=5)

    log("-------- playback_task done --------")
    log("ToneDetector.stop_listen()")
    ToneDetector.stop_listen()
    th.join()

    log("playback_task_run--")
    return trials

def record_task_run(device, serialno, num_iter=1):
    log("record_task_run++")

    trials = []

    log("dev_record_start")
    AATApp.record_start(device)
    time.sleep(2)

    th = DetectionStateChangeListenerThread()
    th.start()

    log("ToneDetector.start_listen(serialno={}, target_freq={})".format(serialno, OUT_FREQ))
    ToneDetector.start_listen(serialno=serialno, target_freq=OUT_FREQ, cb=lambda event: th.tone_detected_event_cb(event))
    log("AudioFunction.play_sound(out_freq={})".format(OUT_FREQ))
    AudioFunction.play_sound(out_freq=OUT_FREQ)

    time.sleep(3)
    for i in range(num_iter):
        log("-------- record_task #{} --------".format(i+1))

        trial = Trial(taskname="record")
        trial.put_extra(name="iter_id", value=i+1)

        th.reset()
        if th.wait_for_event(DetectionStateChangeListenerThread.Event.ACTIVE, timeout=5) < 0:
            log("the tone was not detected, abort the iteration this time...")
            trial.invalidate(errormsg="early return, possible reason: tx no sound")
            trials.append(trial)
            continue

        log("trigger_ssr()")
        AATApp.trigger_ssr(device)
        log("Waiting for SSR recovery")
        elapsed = th.wait_for_event(DetectionStateChangeListenerThread.Event.RISING_EDGE, timeout=10)
        log("elapsed: {} ms".format(elapsed))

        trial.put_extra(name="elapsed", value=elapsed)
        trials.append(trial)

    log("-------- record_task done --------")
    log("AudioFunction.stop_audio()")
    AudioFunction.stop_audio()

    log("dev_record_stop")
    AATApp.record_stop(device)
    time.sleep(5)
    log("ToneDetector.stop_listen()")
    ToneDetector.stop_listen()
    th.join()

    log("record_task_run--")
    return trials

def voip_task_run(device, serialno, num_iter=1):
    log("voip_task_run++")

    trials = []

    # AATApp.voip_use_speaker(device)
    time.sleep(2)

    th = DetectionStateChangeListenerThread()
    th.start()

    log("ToneDetector.start_listen(target_freq={})".format(serialno, OUT_FREQ))
    ToneDetector.start_listen(target_freq=OUT_FREQ, cb=lambda event: th.tone_detected_event_cb(event))

    AATApp.voip_start(device)
    for i in range(num_iter):
        log("-------- dev_voip_rx_task #{} --------".format(i+1))

        trial = Trial(taskname="voip_rx")
        trial.put_extra(name="iter_id", value=i+1)

        time.sleep(1)
        th.reset()

        if th.wait_for_event(DetectionStateChangeListenerThread.Event.ACTIVE, timeout=5) < 0:
            log("the tone was not detected, abort the iteration this time...")
            trial.invalidate(errormsg="early return, possible reason: rx no sound")
            trials.append(trial)
            continue
        time.sleep(1)

        log("trigger_ssr()")
        AATApp.trigger_ssr(device)
        log("Waiting for SSR recovery")
        elapsed = th.wait_for_event(DetectionStateChangeListenerThread.Event.RISING_EDGE, timeout=10)
        log("elapsed: {} ms".format(elapsed))

        trial.put_extra(name="elapsed", value=elapsed)
        trials.append(trial)

    log("-------- dev_voip_rx_task done --------")
    log("ToneDetector.stop_listen()")
    ToneDetector.stop_listen()
    th.join()

    th = DetectionStateChangeListenerThread()
    th.start()

    time.sleep(2)
    AATApp.voip_mute_output(device)
    time.sleep(10)
    log("ToneDetector.start_listen(serialno={}, target_freq={})".format(serialno, None))
    ToneDetector.start_listen(serialno=serialno, target_freq=None, cb=lambda event: th.tone_detected_event_cb(event))

    for i in range(num_iter):
        log("-------- dev_voip_tx_task #{} --------".format(i+1))

        trial = Trial(taskname="voip_tx")
        trial.put_extra(name="iter_id", value=i+1)

        time.sleep(2)

        log("AudioFunction.play_sound(out_freq={})".format(OUT_FREQ))
        AudioFunction.play_sound(out_freq=OUT_FREQ)

        th.reset()
        if th.wait_for_event(DetectionStateChangeListenerThread.Event.ACTIVE, timeout=5) < 0:
            log("the tone was not detected, abort the iteration this time...")
            trial.invalidate(errormsg="early return, possible reason: tx no sound")
            trials.append(trial)
            continue
        time.sleep(2)

        log("trigger_ssr()")
        AATApp.trigger_ssr(device)
        log("Waiting for SSR recovery")
        elapsed = th.wait_for_event(DetectionStateChangeListenerThread.Event.RISING_EDGE, timeout=10)
        log("elapsed: {} ms".format(elapsed))

        trial.put_extra(name="elapsed", value=elapsed)
        trials.append(trial)

        log("AudioFunction.stop_audio()")
        AudioFunction.stop_audio()

    log("-------- dev_voip_tx_task done --------")
    log("dev_voip_stop")
    AATApp.voip_stop(device)
    time.sleep(5)
    log("ToneDetector.stop_listen()")
    ToneDetector.stop_listen()
    th.join()

    log("voip_task_run--")
    return trials


class Trial(object):
    def __init__(self, taskname=None):
        self.ds = {
            "task": taskname,
            "timestamp": str(datetime.datetime.now()),
            "status": "valid",
            "error-msg": None,
            "extra": None
        }

    def put_extra(self, name, value):
        if self.ds["extra"] == None:
            self.ds["extra"] = {}

        self.ds["extra"][name] = value

    def invalidate(self, errormsg):
        self.ds["status"] = "invalid"
        self.ds["error-msg"] = errormsg


if __name__ == "__main__":
    num_iter = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    # ViewClient tries to access the system arguments, then it might cause RuntimeError
    if len(sys.argv) > 1: del sys.argv[1:]
    try:
        run(num_iter=num_iter)
    except Exception as e:
        print(e)
