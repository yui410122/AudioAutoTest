try:
    from com.dtmilano.android.viewclient import ViewClient
except ImportError:
    from androidviewclient3.viewclient import ViewClient

import subprocess
import datetime
import time
import json

import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs import ROOT_DIR, SEP, STDNUL
from libs.logger import Logger
from libs.aatapp import AATApp
from libs.aatapp import AATAppToneDetectorThread as ToneDetectorForDeviceThread
from libs.audiofunction import AudioFunction, ToneDetector, DetectionStateListener
from libs.trials import Trial, TrialHelper
from libs.adbutils import Adb
from libs.googlemusichelper import GoogleMusicApp

TAG = "basic_test.py"

DEVICE_MUSIC_DIR = "sdcard/Music/"
FILE_NAMES = [
    "250Hz_wav.wav",
    "440Hz_mp3.mp3"
]

REPORT_DIR = "basic_report"
BATCH_SIZE = 5

def clear_and_update_music_files(serialno):
    filenames, _ = Adb.execute(cmd=["shell", "ls", DEVICE_MUSIC_DIR], serialno=serialno)
    filenames = filenames.split()
    cmdprefix = ["shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d"]
    for filename in filenames:
        Adb.execute(cmd=["shell", "rm", DEVICE_MUSIC_DIR + filename], serialno=serialno)
        Adb.execute(cmd=cmdprefix+["file:///mnt/" + DEVICE_MUSIC_DIR + filename], serialno=serialno)

    for file_to_pushed in FILE_NAMES:
        out, _ = subprocess.Popen(["find", ROOT_DIR, "-name", file_to_pushed], stdout=subprocess.PIPE).communicate()
        file_path = out.splitlines()[0] if out else None
        if file_path:
            Adb.execute(cmd=["push", file_path, DEVICE_MUSIC_DIR], serialno=serialno)
            Adb.execute(cmd=cmdprefix+["file:///mnt/" + DEVICE_MUSIC_DIR + file_to_pushed], serialno=serialno)

def log(msg):
    Logger.log(TAG, msg)

def run(num_iter=1):
    AudioFunction.init()
    Logger.init(Logger.Mode.BOTH_FILE_AND_STDOUT)
    Adb.init()

    os.system("mkdir -p {}{}{} > {}".format(ROOT_DIR, SEP, REPORT_DIR, STDNUL))
    t = datetime.datetime.now()
    filename = "report_{}{:02d}{:02d}_{:02d}{:02d}{:02d}.json".format(t.year, t.month, t.day, t.hour, t.minute, t.second)

    device, serialno = ViewClient.connectToDeviceOrExit(serialno=None)

    device.press("HOME")
    time.sleep(1)

    gmhandler = GoogleMusicApp(device, serialno)
    log("gmhandler.to_top()")
    gmhandler.to_top()
    clear_and_update_music_files(serialno)
    time.sleep(10)

    trials = []
    batch_count = 1
    while num_iter > 0:
        log("-------- batch_run #{} --------".format(batch_count))
        trials_batch = []
        trials_batch += playback_task_run(num_iter=min([num_iter, BATCH_SIZE]), num_seek_test=5, gmhandler=gmhandler)
        trials_batch += record_task_run(device, serialno, num_iter=min([num_iter, BATCH_SIZE]), num_freqs=5)

        map(lambda trial: trial.put_extra(name="batch_id", value=batch_count), trials_batch)
        trials += trials_batch

        with open("{}{}{}{}{}".format(ROOT_DIR, SEP, REPORT_DIR, SEP, filename), "w") as f:
            f.write(TrialHelper.to_json(trials))

        for taskname, tasktrials in TrialHelper.categorize_in(trials, lambda t: t.ds["task"]).items():
            valid_trials = zip(tasktrials, TrialHelper.pass_fail_list(tasktrials, lambda t: t.ds["status"] == "valid"))
            valid_trials = [trial for trial, isvalid in valid_trials if isvalid]
            num_valid = len(valid_trials)
            num_pass = len(filter(lambda x: x, TrialHelper.pass_fail_list(valid_trials)))
            log("task[{}] valid trials: {}/{}, pass trials: {}/{}".format(taskname, num_valid, len(tasktrials), num_pass, num_valid))

        num_iter -= BATCH_SIZE
        batch_count += 1

    AudioFunction.finalize()
    Logger.finalize()

def playback_task_run(num_iter, num_seek_test, gmhandler):
    log("playback_task_run++")

    if not gmhandler.cache_init:
        log("gmhandler.walk_through()")
        if not gmhandler.walk_through():
            log("failed to walk through the UI of the google music")
            gmhandler.dump()
            return []

        log("gmhandler.cache\n{}".format(json.dumps(gmhandler.cache, indent=4, ensure_ascii=False)))
    else:
        log("gmhandler.to_top()")
        gmhandler.to_top()

    if not gmhandler.to_control_panel():
        log("failed to go to the control panel of the google music")
        gmhandler.dump()
        return []

    trials = []
    def gmplayback_pass_check(trial):
        subtasknames = ["pause", "resume", "next", "start", "seek"]
        for subtaskname in subtasknames:
            if not subtaskname in trial.ds["extra"].keys():
                return False

            subtask_result = trial.ds["extra"][subtaskname]
            if isinstance(subtask_result, str) and subtask_result != "pass":
                return False

            if isinstance(subtask_result, dict) and subtask_result["result"] != "pass":
                return False

        return True

    stm = DetectionStateListener()

    for i in range(num_iter):
        log("-------- playback_task #{} --------".format(i+1))
        trial = Trial(taskname="playback", pass_check=gmplayback_pass_check)
        trial.put_extra(name="iter_id", value=i+1)

        song = gmhandler.control_panel.get_current_song()
        log("the current song:\n{}".format(json.dumps(song, indent=4, ensure_ascii=False)))
        trial.put_extra(name="song_title", value=song["name"])
        target_freq = int(song["name"].split("Hz")[0])

        stm.clear()

        log("ToneDetector.start_listen(target_freq={})".format(target_freq))
        ToneDetector.start_listen(target_freq=target_freq, cb=lambda event: stm.tone_detected_event_cb(event))

        gmhandler.control_panel.play()
        time.sleep(1)
        if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=10) < 0:
            log("The {}Hz tone is not detected....".format(target_freq))
            trial.put_extra("start", "failed")
        else:
            log("The {}Hz tone is detected".format(target_freq))
            trial.put_extra("start", "pass")

        gmhandler.control_panel.play_pause()
        if stm.wait_for_event(DetectionStateListener.Event.INACTIVE, timeout=10) < 0:
            log("The {}Hz tone seems not to be stopped".format(target_freq))
            trial.put_extra("pause", "failed")
        else:
            log("The {}Hz tone has been stopped".format(target_freq))
            trial.put_extra("pause", "pass")

        gmhandler.control_panel.play_pause()
        if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=10) < 0:
            log("The {}Hz tone is not resumed....".format(target_freq))
            trial.put_extra("resume", "failed")
        else:
            log("The {}Hz tone is resumed".format(target_freq))
            trial.put_extra("resume", "pass")

        result = "pass"
        for _ in range(num_seek_test):
            import random
            v = random.uniform(0., 1.) * 0.9
            log("seek to {}".format(v))
            gmhandler.control_panel.seek(v)
            time.sleep(0.1)
            if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=10) < 0:
                log("seek failed: the {}Hz tone is not detected".format(target_freq))
                result = "failed"

        trial.put_extra("seek", {"num_trials": num_seek_test, "result": result})
        ToneDetector.stop_listen()
        stm.clear()

        gmhandler.control_panel.next()
        song = gmhandler.control_panel.get_current_song()
        log("the current song:\n{}".format(json.dumps(song, indent=4, ensure_ascii=False)))
        trial.put_extra(name="next_song_title", value=song["name"])
        target_freq = int(song["name"].split("Hz")[0])
        log("ToneDetector.start_listen(target_freq={})".format(target_freq))
        ToneDetector.start_listen(target_freq=target_freq, cb=lambda event: stm.tone_detected_event_cb(event))

        if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=10) < 0:
            log("The {}Hz tone is not detected....".format(target_freq))
            trial.put_extra("next", "failed")
        else:
            log("The {}Hz tone is detected".format(target_freq))
            trial.put_extra("next", "pass")

        gmhandler.control_panel.play_pause()
        ToneDetector.stop_listen()
        time.sleep(1)

        trials.append(trial)

    log("playback_task_run--")
    return trials

def record_task_run(device, serialno, num_iter=1, num_freqs=1):
    log("record_task_run++")
    log("launch AAT app")
    AATApp.launch_app(device)
    time.sleep(2)

    trials = []

    log("dev_record_start")
    AATApp.record_start(device)
    time.sleep(2)

    stm = DetectionStateListener()

    def gen_freq():
        import random
        return 440. * 2**(random.randint(-12, 12)/12.)

    for i in range(num_iter):
        log("-------- record_task #{} --------".format(i+1))

        trial = Trial(taskname="record", pass_check= \
            lambda t: "result" in t.ds["extra"].keys() and t.ds["extra"]["result"] == "pass")
        trial.put_extra(name="iter_id", value=i+1)

        AATApp.print_log(device, severity="i", tag=TAG, log="record_task #{}".format(i+1))

        result = "pass"
        freqs = []
        for _ in range(num_freqs):
            stm.clear()
            target_freq = gen_freq()
            freqs.append(target_freq)

            log("ToneDetector.start_listen(serialno={}, target_freq={})".format(serialno, target_freq))
            ToneDetector.start_listen(serialno=serialno, target_freq=target_freq, cb=lambda event: stm.tone_detected_event_cb(event), dclass=ToneDetectorForDeviceThread)
            time.sleep(2)

            log("AudioFunction.play_sound(out_freq={})".format(target_freq))
            AudioFunction.play_sound(out_freq=target_freq)

            if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=10) < 0:
                log("The {}Hz tone is not detected".format(target_freq))

                now = "_".join("{}".format(datetime.datetime.now()).split())
                log("dump the recorded pcm to \"sdcard/PyAAT/dump_{}\"".format(now))
                AATApp.record_dump(device, "sdcard/PyAAT/dump_{}".format(now))

                log("start dumping the process during capturing the frequency...")
                ToneDetector.WORK_THREAD.dump()

                result = "failed"

            log("ToneDetectorForDeviceThread.adb-read-prop-max-elapsed: {} ms".format( \
                ToneDetector.WORK_THREAD.extra["adb-read-prop-max-elapsed"]))
            log("ToneDetectorForDeviceThread.freq-cb-max-elapsed: {} ms".format( \
                ToneDetector.WORK_THREAD.extra["freq-cb-max-elapsed"]))

            AudioFunction.stop_audio()
            ToneDetector.stop_listen()
            time.sleep(2)

        trial.put_extra(name="result", value=result)
        trial.put_extra(name="test_freqs", value=freqs)
        trials.append(trial)

    log("dev_record_stop")
    AATApp.record_stop(device)
    time.sleep(2)

    log("record_task_run--")
    return trials

if __name__ == "__main__":
    num_iter = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    # ViewClient tries to access the system arguments, then it might cause RuntimeError
    if len(sys.argv) > 1: del sys.argv[1:]
    run(num_iter=num_iter)
