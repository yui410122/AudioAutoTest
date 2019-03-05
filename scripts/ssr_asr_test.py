from com.dtmilano.android.viewclient import ViewClient
import os
import subprocess
import time
import datetime

import sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs import ROOT_DIR, SEP, STDNUL
from libs.adbutils import Adb
from libs.audiofunction import AudioFunction, ToneDetector, DetectionStateListener
from libs.logger import Logger
from libs.aatapp import AATApp
from libs.trials import Trial, TrialHelper

RELAUCH = True
TEST_CONFIG = "asr" # "ssr"|"asr"
TAG = "{}_test.py".format(TEST_CONFIG)

DEVICE_MUSIC_DIR = "sdcard/Music/"
OUT_FREQ = 440
BATCH_SIZE = 5

FILE_NAMES = [
    "440Hz_wav.wav",
    "440Hz_mp3.mp3"
]

def push_files(serialno):
    for file_to_pushed in FILE_NAMES:
        out, _ = subprocess.Popen(["find", ROOT_DIR, "-name", file_to_pushed], stdout=subprocess.PIPE).communicate()
        file_path = out.splitlines()[0] if out else None
        if file_path:
            os.system("adb -s {} push {} {} > {}".format(serialno, file_path, DEVICE_MUSIC_DIR, STDNUL))
        else:
            raise ValueError("Cannot find the file \"{}\", please place it under the project tree.".format(file_to_pushed))

def log(msg):
    Logger.log(TAG, msg)

def trigger_ssr(serialno):
    Adb.execute(["shell", "crash_adsp"], serialno=serialno)

def trigger_asr(serialno):
    Adb.execute(["shell", "killall", "audioserver"], serialno=serialno)

def relauch_app(device):
    if RELAUCH:
        AATApp.relauch_app(device)
        time.sleep(5)

def trigger_bugreport(serialno):
    out, err = subprocess.Popen("adb bugreport", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    if len(err) > 0:
        log("trigger_bugreport failed: '{}'".format(err.strip()))
        return None
    else:
        bugreport_path = out.splitlines()[0].split()[-1]
        log("trigger_bugreport: '{}'".format(bugreport_path.strip()))
        return bugreport_path.strip()

def try_to_reboot_device(serialno, timeout):
    import threading
    from libs.tictoc import TicToc
    class runner(threading.Thread):
        def __init__(self):
            super(runner, self).__init__()
            self.lock = threading.Lock()
            self.done = False

        def run(self):
            self.proc = subprocess.Popen("python reboot.py {}".format(serialno), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            log("python reboot.py {} running...".format(serialno))
            timer = TicToc()
            timer.tic()
            self.proc.communicate()
            elapsed = timer.toc()
            log("python reboot.py done. (elapsed: {} ms)".format(elapsed))
            self.lock.acquire()
            self.done = True
            self.lock.release()

        def is_done(self):
            self.lock.acquire()
            d = self.done
            self.lock.release()
            return d

    reboot_runner = runner()
    reboot_runner.start()
    timer = TicToc()
    timer.tic()
    timeout *= 1000.
    while timeout > 0:
        if reboot_runner.is_done():
            return True
        time.sleep(10)
        timeout -= timer.toc()
        log("remaining time: {} msec".format(timeout))

    return False


def run(num_iter=1, serialno=None):
    AudioFunction.init()
    Logger.init(Logger.Mode.BOTH_FILE_AND_STDOUT)
    # Logger.init(Logger.Mode.STDOUT)
    # Logger.init(Logger.Mode.FILE)
    Adb.init()

    os.system("mkdir -p {}{}{}_report > {}".format(ROOT_DIR, SEP, TEST_CONFIG, STDNUL))
    os.system("mkdir -p {}{}{}_report-bugreport > {}".format(ROOT_DIR, SEP, TEST_CONFIG, STDNUL))
    t = datetime.datetime.now()
    postfix = "{}{:02d}{:02d}_{:02d}{:02d}{:02d}".format(t.year, t.month, t.day, t.hour, t.minute, t.second)
    filename = "report_{}.json".format(postfix)
    os.system("mkdir -p {}{}{}_report-bugreport/{} > {}".format(ROOT_DIR, SEP, TEST_CONFIG, postfix, STDNUL))

    device, serialno = ViewClient.connectToDeviceOrExit(serialno=serialno)
    push_files(serialno)

    Adb.execute(["shell", "svc", "power", "stayon", "true"], serialno=serialno)

    out, _ = Adb.execute(["shell", "getprop", "ro.vendor.build.fingerprint"], serialno=serialno)
    out = out.strip()
    log("build number: '{}'".format(out))

    # keymap reference:
    #   https://github.com/dtmilano/AndroidViewClient/blob/master/src/com/dtmilano/android/adb/androidkeymap.py
    # device.press("HOME")
    # time.sleep(1)
    relauch_app(device)
    # time.sleep(5)

    function_items = [
        lambda x: playback_task_run(device, num_iter=x, postfix=postfix),
        lambda x: record_task_run(device, serialno, num_iter=x),
        lambda x: voip_task_run(device, serialno, num_iter=x)
    ]

    trials = []
    batch_count = 1
    temp = num_iter
    while num_iter > 0:
        log("-------- batch_run #{} --------".format(batch_count))
        AATApp.print_log(device, severity="i", tag=TAG, log="-------- batch_run #{} --------".format(batch_count))
        trials_batch = []
        # trials_batch += playback_task_run(device, num_iter=min([num_iter, BATCH_SIZE]))
        # trials_batch += record_task_run(device, serialno, num_iter=min([num_iter, BATCH_SIZE]))
        # trials_batch += voip_task_run(device, serialno, num_iter=min([num_iter, BATCH_SIZE]))
        need_to_reboot = False
        for test_item in function_items:
            test_results = test_item(min([num_iter, BATCH_SIZE]))
            trials_batch += test_results
            if len(filter(lambda t: t.ds["status"] == "valid", test_results)) == 0:
                log("Function failed after {} trials...".format(temp - num_iter))
                need_to_reboot = True

        map(lambda trial: trial.put_extra(name="batch_id", value=batch_count), trials_batch)
        trials += trials_batch
        with open("{}{}{}_report{}{}".format(ROOT_DIR, SEP, TEST_CONFIG, SEP, filename), "w") as f:
            f.write(TrialHelper.to_json(trials))

        for taskname, tasktrials in TrialHelper.categorize_in(trials, lambda t: t.ds["task"]).items():
            valid_trials = zip(tasktrials, TrialHelper.pass_fail_list(tasktrials, lambda t: t.ds["status"] == "valid"))
            valid_trials = [trial for trial, isvalid in valid_trials if isvalid]
            num_valid = len(valid_trials)
            num_pass = len(filter(lambda x: x, TrialHelper.pass_fail_list(valid_trials)))
            log("task[{}] valid trials: {}/{}, pass trials: {}/{}".format(taskname, num_valid, len(tasktrials), num_pass, num_valid))

        if need_to_reboot:
            AudioFunction.stop_audio()
            log("No valid trials, might be some problems!")
            log("trigger bugreport!")
            trigger_bugreport(device)
            log("Try to reboot the device")
            if not try_to_reboot_device(serialno, timeout=300):
                log("reboot failed!")
                os.system("mv bugreport*.zip {}{}{}_report-bugreport{}{}{}".format(ROOT_DIR, SEP, TEST_CONFIG, SEP, postfix, SEP))
                os.system("mv {}-*.png {}{}{}_report-bugreport{}{}{}".format(postfix, ROOT_DIR, SEP, TEST_CONFIG, SEP, postfix, SEP))
                break
            else:
                time.sleep(5)
                device, serialno = ViewClient.connectToDeviceOrExit(serialno=serialno)

        # elif batch_count % 10 == 0:
        #     log("Try to reboot the device and continue the test...")
        #     if not try_to_reboot_device(serialno, timeout=300):
        #         log("reboot failed!")
        #         os.system("mv bugreport*.zip {}{}{}_report-bugreport{}{}{}".format(ROOT_DIR, SEP, TEST_CONFIG, SEP, postfix, SEP))
        #         break
        #     else:
        #         device, serialno = ViewClient.connectToDeviceOrExit(serialno=serialno)

        os.system("mv bugreport*.zip {}{}{}_report-bugreport{}{}{}".format(ROOT_DIR, SEP, TEST_CONFIG, SEP, postfix, SEP))

        num_iter -= BATCH_SIZE
        batch_count += 1
        time.sleep(5)

    AudioFunction.finalize()
    Logger.finalize()


def playback_task_run(device, num_iter=1, postfix=None):
    log("playback_task_run++")

    trials = []

    stm = DetectionStateListener()

    log("ToneDetector.start_listen(target_freq={})".format(OUT_FREQ))
    ToneDetector.start_listen(target_freq=OUT_FREQ, cb=lambda event: stm.tone_detected_event_cb(event))

    funcs = {
        "nonoffload": AATApp.playback_nonoffload,
        "offload"   : AATApp.playback_offload
    }

    files = {
        "nonoffload": "440Hz_wav.wav",
        "offload"   : "440Hz_mp3.mp3"
    }

    has_triggered_bugreport = False

    for i in range(num_iter):
        log("-------- playback_task #{} --------".format(i+1))
        for name, func in funcs.items():
            trial = Trial(taskname="playback_{}".format(name), pass_check=lambda t: t.ds["extra"]["elapsed"] > 0)
            trial.put_extra(name="iter_id", value=i+1)

            AATApp.print_log(device, severity="i", tag=TAG, log="playback_{}_task #{}".format(name, i+1))

            log("dev_playback_{}_start".format(name))
            time.sleep(1)
            stm.reset()
            log("reset DetectionStateChangeListener")
            func(device, filename=files[name])

            if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=5) < 0:
                log("the tone was not detected, abort the iteration this time...")
                AATApp.playback_stop(device)
                trial.invalidate(errormsg="early return, possible reason: rx no sound")
                trials.append(trial)
                continue
            time.sleep(1)

            log("trigger_{}()".format(TEST_CONFIG))
            if TEST_CONFIG == "ssr":
                trigger_ssr(serialno)
            else:
                trigger_asr(serialno)

            log("Waiting for {} recovery".format("SSR" if TEST_CONFIG == "ssr" else "ASR"))
            elapsed = stm.wait_for_event(DetectionStateListener.Event.RISING_EDGE, timeout=15)
            log("elapsed: {} ms".format(elapsed))
            if elapsed < 0:
                log("Timeout in waiting for rising event, possibly caused by missing event not being caught")
                log("Waiting for the tone being detected")
                if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=5) < 0:
                    log("The tone is not detected")
                    screenshot_path = "{}-{}.png".format(postfix, int(time.time()));
                    os.system("python {}/tools-for-dev/dump-screen.py {}/{}_report-bugreport/{}/{}".format(ROOT_DIR, ROOT_DIR, TEST_CONFIG, postfix, screenshot_path))
                    trial.put_extra("screenshot", screenshot_path)
                    if not has_triggered_bugreport:
                        AATApp.playback_stop(device)
                        log("get bugreport...")
                        p = trigger_bugreport(device)
                        trial.put_extra("bugreport", "{}/{}".format(postfix, p))
                        has_triggered_bugreport = True
                else:
                    log("The tone is detected, please also check the device log for confirming if it is a false alarm")
                    trial.put_extra(name="msg", value="possible false alarm")

            trial.put_extra(name="elapsed", value=elapsed)
            trials.append(trial)

            log("dev_playback_stop")
            AATApp.playback_stop(device)
            stm.wait_for_event(DetectionStateListener.Event.INACTIVE, timeout=5)
            if elapsed > 0:
                time.sleep(20 - elapsed/1000.)

    log("-------- playback_task done --------")
    log("ToneDetector.stop_listen()")
    ToneDetector.stop_listen()

    log("playback_task_run--")
    relauch_app(device)
    return trials

def record_task_run(device, serialno, num_iter=1):
    log("record_task_run++")

    trials = []

    log("dev_record_start")
    Adb.execute(cmd=["shell", "rm", "-f", "sdcard/AudioFunctionsDemo-record-prop.txt"], serialno=serialno)
    AATApp.record_start(device)
    time.sleep(2)

    stm = DetectionStateListener()

    out_freq = OUT_FREQ
    log("ToneDetector.start_listen(serialno={}, target_freq={})".format(serialno, out_freq))
    ToneDetector.start_listen(serialno=serialno, target_freq=out_freq, cb=lambda event: stm.tone_detected_event_cb(event))
    log("AudioFunction.play_sound(out_freq={})".format(out_freq))

    has_triggered_bugreport = False

    time.sleep(3)
    for i in range(num_iter):
        AudioFunction.play_sound(out_freq=out_freq)
        log("-------- record_task #{} --------".format(i+1))
        Adb.execute(cmd=["shell", "rm", "-f", "sdcard/AudioFunctionsDemo-record-prop.txt"], serialno=serialno)

        trial = Trial(taskname="record", pass_check=lambda t: t.ds["extra"]["elapsed"] > 0)
        trial.put_extra(name="iter_id", value=i+1)

        AATApp.print_log(device, severity="i", tag=TAG, log="record_task #{}".format(i+1))

        ToneDetector.WORK_THREAD.clear_dump()
        stm.reset()
        if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=5) < 0:
            log("the tone was not detected, abort the iteration this time...")
            log("ToneDetectorForDeviceThread.adb-read-prop-max-elapsed: {} ms".format( \
                ToneDetector.WORK_THREAD.extra["adb-read-prop-max-elapsed"]))
            log("ToneDetectorForDeviceThread.freq-cb-max-elapsed: {} ms".format( \
                ToneDetector.WORK_THREAD.extra["freq-cb-max-elapsed"]))
            trial.invalidate(errormsg="early return, possible reason: tx no sound")
            trials.append(trial)

            now = "_".join("{}".format(datetime.datetime.now()).split())
            log("dump the recorded pcm to \"sdcard/PyAAT/dump_{}\"".format(now))
            AATApp.record_dump(device, "sdcard/PyAAT/dump_{}".format(now))
            continue

        log("trigger_{}()".format(TEST_CONFIG))
        if TEST_CONFIG == "ssr":
            trigger_ssr(serialno)
        else:
            trigger_asr(serialno)

        log("waiting for incative....")
        stm.wait_for_event(DetectionStateListener.Event.INACTIVE, timeout=5)
        Adb.execute(cmd=["shell", "rm", "-f", "sdcard/AudioFunctionsDemo-record-prop.txt"], serialno=serialno)

        log("Waiting for {} recovery".format("SSR" if TEST_CONFIG == "ssr" else "ASR"))
        elapsed = stm.wait_for_event(DetectionStateListener.Event.RISING_EDGE, timeout=15)
        if elapsed < 0:
            log("Timeout in waiting for rising event, possibly caused by missing event not being caught")
            log("Waiting for the tone being detected")
            if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=5) < 0:
                log("The tone is not detected")
                if not has_triggered_bugreport:
                    AudioFunction.stop_audio()
                    log("get bugreport...")
                    p = trigger_bugreport(device)
                    trial.put_extra("bugreport", p)
                    has_triggered_bugreport = True
                now = "_".join("{}".format(datetime.datetime.now()).split())
                log("dump the recorded pcm to \"sdcard/PyAAT/dump_{}\"".format(now))
                AATApp.record_dump(device, "sdcard/PyAAT/dump_{}".format(now))

                log("start dumping the process during capturing the frequency...")
                ToneDetector.WORK_THREAD.dump()
            else:
                log("The tone is detected, please also check the device log for confirming if it is a false alarm")
                trial.put_extra(name="msg", value="possible false alarm")
            
        log("elapsed: {} ms".format(elapsed))
        AudioFunction.stop_audio()

        log("ToneDetectorForDeviceThread.adb-read-prop-max-elapsed: {} ms".format( \
            ToneDetector.WORK_THREAD.extra["adb-read-prop-max-elapsed"]))
        log("ToneDetectorForDeviceThread.freq-cb-max-elapsed: {} ms".format( \
            ToneDetector.WORK_THREAD.extra["freq-cb-max-elapsed"]))

        trial.put_extra(name="elapsed", value=elapsed)
        trials.append(trial)

        import random
        out_freq = OUT_FREQ * 2**(random.randint(0, 12)/12.)
        ToneDetector.set_target_frequency(target_freq=out_freq)
        log("ToneDetector.set_target_frequency(serialno={}, target_freq={})".format(serialno, out_freq))

        if elapsed > 0:
            time.sleep(30 - elapsed/1000.)

    log("-------- record_task done --------")
    log("AudioFunction.stop_audio()")

    log("dev_record_stop")
    AATApp.record_stop(device)
    time.sleep(5)
    log("ToneDetector.stop_listen()")
    ToneDetector.stop_listen()

    log("record_task_run--")
    relauch_app(device)
    return trials

def voip_task_run(device, serialno, num_iter=1):
    log("voip_task_run++")

    trials = []

    # AATApp.voip_use_speaker(device)
    time.sleep(2)

    stm = DetectionStateListener()

    out_freq = OUT_FREQ
    log("ToneDetector.start_listen(target_freq={})".format(serialno, out_freq))
    ToneDetector.start_listen(target_freq=out_freq, cb=lambda event: stm.tone_detected_event_cb(event))

    has_triggered_bugreport = False

    Adb.execute(cmd=["shell", "rm", "-f", "sdcard/AudioFunctionsDemo-record-prop.txt"], \
                serialno=serialno)
    AATApp.voip_start(device)
    for i in range(num_iter):
        log("-------- dev_voip_rx_task #{} --------".format(i+1))

        trial = Trial(taskname="voip_rx", pass_check=lambda t: t.ds["extra"]["elapsed"] > 0)
        trial.put_extra(name="iter_id", value=i+1)

        AATApp.print_log(device, severity="i", tag=TAG, log="voip_rx_task #{}".format(i+1))

        time.sleep(1)
        stm.reset()

        if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=5) < 0:
            log("the tone was not detected, abort the iteration this time...")
            trial.invalidate(errormsg="early return, possible reason: rx no sound")
            trials.append(trial)
            continue
        time.sleep(1)

        log("trigger_{}()".format(TEST_CONFIG))
        if TEST_CONFIG == "ssr":
            trigger_ssr(serialno)
        else:
            trigger_asr(serialno)

        log("Waiting for {} recovery".format("SSR" if TEST_CONFIG == "ssr" else "ASR"))
        elapsed = stm.wait_for_event(DetectionStateListener.Event.RISING_EDGE, timeout=15)
        log("elapsed: {} ms".format(elapsed))

        if elapsed < 0:
            log("Timeout in waiting for rising event, possibly caused by missing event not being caught")
            log("Waiting for the tone being detected")
            if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=5) < 0:
                log("The tone is not detected")
                if not has_triggered_bugreport:
                    log("get bugreport...")
                    p = trigger_bugreport(device)
                    trial.put_extra("bugreport", p)
                    has_triggered_bugreport = True
            else:
                log("The tone is detected, please also check the device log for confirming if it is a false alarm")
                trial.put_extra(name="msg", value="possible false alarm")
            AATApp.voip_stop(device)
            time.sleep(5)
            AATApp.voip_start(device)
        else:
            AATApp.voip_stop(device)
            time.sleep(30 - elapsed/1000.)
            AATApp.voip_start(device)
            
        trial.put_extra(name="elapsed", value=elapsed)
        trials.append(trial)

    log("-------- dev_voip_rx_task done --------")
    log("ToneDetector.stop_listen()")
    ToneDetector.stop_listen()

    stm = DetectionStateListener()

    time.sleep(2)
    AATApp.voip_mute_output(device)
    time.sleep(10)
    log("ToneDetector.start_listen(serialno={}, target_freq={})".format(serialno, 440))
    ToneDetector.start_listen(serialno=serialno, target_freq=440, cb=lambda event: stm.tone_detected_event_cb(event))

    has_triggered_bugreport = False

    for i in range(num_iter):
        log("-------- dev_voip_tx_task #{} --------".format(i+1))

        trial = Trial(taskname="voip_tx", pass_check=lambda t: t.ds["extra"]["elapsed"] > 0)
        trial.put_extra(name="iter_id", value=i+1)

        AATApp.print_log(device, severity="i", tag=TAG, log="voip_tx_task #{}".format(i+1))

        time.sleep(2)

        log("AudioFunction.play_sound(out_freq={})".format(out_freq))
        AudioFunction.play_sound(out_freq=out_freq)

        stm.reset()
        if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=5) < 0:
            log("the tone was not detected, abort the iteration this time...")
            trial.invalidate(errormsg="early return, possible reason: tx no sound")
            trials.append(trial)
            continue
        time.sleep(2)

        log("trigger_{}()".format(TEST_CONFIG))
        if TEST_CONFIG == "ssr":
            trigger_ssr(serialno)
        else:
            trigger_asr(serialno)

        log("waiting for incative....")
        stm.wait_for_event(DetectionStateListener.Event.INACTIVE, timeout=5)
        Adb.execute(cmd=["shell", "rm", "-f", "sdcard/AudioFunctionsDemo-record-prop.txt"], serialno=serialno)

        log("Waiting for {} recovery".format("SSR" if TEST_CONFIG == "ssr" else "ASR"))
        elapsed = stm.wait_for_event(DetectionStateListener.Event.RISING_EDGE, timeout=15)
        log("elapsed: {} ms".format(elapsed))

        if elapsed < 0:
            log("Timeout in waiting for rising event, possibly caused by missing event not being caught")
            log("Waiting for the tone being detected")
            if stm.wait_for_event(DetectionStateListener.Event.ACTIVE, timeout=5) < 0:
                log("The tone is not detected")
                if not has_triggered_bugreport:
                    AudioFunction.stop_audio()
                    log("get bugreport...")
                    p = trigger_bugreport(device)
                    trial.put_extra("bugreport", p)
                    has_triggered_bugreport = True

                now = "_".join("{}".format(datetime.datetime.now()).split())
                log("dump the recorded pcm to \"sdcard/PyAAT/dump_{}\"".format(now))
                AATApp.record_dump(device, "sdcard/PyAAT/dump_{}".format(now))

                log("start dumping the process during capturing the frequency...")
                ToneDetector.WORK_THREAD.dump()
            else:
                log("The tone is detected, please also check the device log for confirming if it is a false alarm")
                trial.put_extra(name="msg", value="possible false alarm")

            

        log("AudioFunction.stop_audio()")
        AudioFunction.stop_audio()

        log("ToneDetectorForDeviceThread.adb-read-prop-max-elapsed: {} ms".format( \
            ToneDetector.WORK_THREAD.extra["adb-read-prop-max-elapsed"]))
        log("ToneDetectorForDeviceThread.freq-cb-max-elapsed: {} ms".format( \
            ToneDetector.WORK_THREAD.extra["freq-cb-max-elapsed"]))

        trial.put_extra(name="elapsed", value=elapsed)
        trials.append(trial)

        import random
        out_freq = OUT_FREQ * 2**(random.randint(0, 12)/12.)
        ToneDetector.set_target_frequency(target_freq=out_freq)
        log("ToneDetector.set_target_frequency(serialno={}, target_freq={})".format(serialno, out_freq))

        if elapsed > 0:
            time.sleep(30 - elapsed/1000.)

    log("-------- dev_voip_tx_task done --------")
    log("dev_voip_stop")
    AATApp.voip_stop(device)
    time.sleep(5)
    log("ToneDetector.stop_listen()")
    ToneDetector.stop_listen()

    log("voip_task_run--")
    relauch_app(device)
    return trials


if __name__ == "__main__":
    num_iter = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    serialno = sys.argv[2] if len(sys.argv) > 2 else None
    # ViewClient tries to access the system arguments, then it might cause RuntimeError
    if len(sys.argv) > 1: del sys.argv[1:]
    while True:
        try:
            run(num_iter=num_iter, serialno=serialno)
            break
        except Exception as e:
            print(e)