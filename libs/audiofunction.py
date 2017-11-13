from audiothread import *
import threading
import numpy as np
import time
import os

from libs.logcatlistener import LogcatListener, LogcatEvent

# Initialization of used variables
class CommandHandler(object):
    def __init__(self):
        self.cmd = None

    def stop(self):
        if self.cmd:
            self.cmd.stop()

class AudioFunction(object):
    WORK_THREAD = AudioCommandThread()
    WORK_THREAD.daemon = True
    AUDIO_CONFIG = AudioConfig(fs=16000, ch=1)
    COMMAND = CommandHandler()

    @staticmethod
    def init():
        AudioFunction.WORK_THREAD.start()

    @staticmethod
    def finalize():
        AudioFunction.WORK_THREAD.join()

    @staticmethod
    def play_sound(out_freq):
        AudioFunction.COMMAND.cmd = TonePlayCommand(config=AudioFunction.AUDIO_CONFIG, out_freq=out_freq)
        AudioFunction.WORK_THREAD.push(AudioFunction.COMMAND.cmd)

    @staticmethod
    def stop_audio():
        AudioFunction.COMMAND.stop()

    @staticmethod
    def start_record(cb):
        AudioFunction.AUDIO_CONFIG.cb = cb
        AudioFunction.COMMAND.cmd = ToneDetectCommand(config=AudioFunction.AUDIO_CONFIG, framemillis=100, nfft=4096)
        AudioFunction.WORK_THREAD.push(AudioFunction.COMMAND.cmd)


class ToneDetectedDecisionThread(threading.Thread):
    def __init__(self, serialno, target_freq, callback):
        super(ToneDetectedDecisionThread, self).__init__()
        self.daemon = True
        self.stoprequest = threading.Event()
        self.serialno = serialno
        self.event_counter = 0
        self.target_freq = target_freq
        self.cb = callback

    def join(self, timeout=None):
        self.stoprequest.set()
        super(ToneDetectedDecisionThread, self).join(timeout)

    def run(self):
        LogcatListener.init(self.serialno)

        shared_vars = {
            "start_time": None
        }

        def freq_cb(pattern, msg):
            strs = msg.split()
            freq, amp_db = map(float, strs[-1].split(","))
            the_date, the_time = strs[:2]

            time_str = the_date + " " + the_time

            diff_semitone = -1
            if freq > 0:
                diff_semitone = np.abs(np.log(1.0*freq/self.target_freq) / np.log(2) * 12)

            if freq > 0 and diff_semitone < 0.1:
                self.event_counter += 1
                if self.event_counter == 1:
                    shared_vars["start_time"] = time_str
                if self.event_counter == 10:
                    self.cb((shared_vars["start_time"], ToneDetectedDecision.Event.TONE_DETECTED))

            else:
                if self.event_counter > 10:
                    shared_vars["start_time"] = None
                    self.cb((time_str, ToneDetectedDecision.Event.TONE_MISSING))
                self.event_counter = 0

        logcat_event = LogcatEvent(pattern="AudioFunctionsDemo::properties", cb=freq_cb)
        LogcatListener.register_event(serialno=self.serialno, logcat_event=logcat_event)

        while not self.stoprequest.isSet():
            os.system("adb -s {} shell am broadcast -a audio.htc.com.intent.print.properties > /dev/null".format(self.serialno))
            time.sleep(0.01)

        LogcatListener.unregister_event(serialno=self.serialno, logcat_event=logcat_event)


class ToneDetectedDecision(object):
    WORK_THREAD = None

    TIME_STR_FORMAT = "%m-%d %I:%M:%S.%f"

    class Event(object):
        TONE_DETECTED = "tone detected"
        TONE_MISSING = "tone missing"

    @staticmethod
    def start_listen(serialno, target_freq, cb):
        os.system("adb -s {} logcat -c > /dev/null".format(serialno))
        ToneDetectedDecision.WORK_THREAD = ToneDetectedDecisionThread(serialno=serialno, target_freq=target_freq, callback=cb)
        ToneDetectedDecision.WORK_THREAD.start()

    @staticmethod
    def stop_listen():
        ToneDetectedDecision.WORK_THREAD.join()
        ToneDetectedDecision.WORK_THREAD = None
