from audiothread import *
import threading
import numpy as np
import time
import os
import datetime

from libs.adbutils import Adb
from libs.logger import Logger

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

    HAS_BEEN_INIT = False

    @staticmethod
    def init():
        if AudioFunction.HAS_BEEN_INIT:
            return
        AudioFunction.WORK_THREAD.start()
        AudioFunction.HAS_BEEN_INIT = True

    @staticmethod
    def finalize():
        if not AudioFunction.HAS_BEEN_INIT:
            raise RuntimeError("The AudioFunction should be initialized before calling APIs")
        AudioFunction.WORK_THREAD.join()

        AudioFunction.HAS_BEEN_INIT = False

    @staticmethod
    def play_sound(out_freq):
        if not AudioFunction.HAS_BEEN_INIT:
            raise RuntimeError("The AudioFunction should be initialized before calling APIs")
        AudioFunction.COMMAND.stop()
        AudioFunction.COMMAND.cmd = TonePlayCommand(config=AudioFunction.AUDIO_CONFIG, out_freq=out_freq)
        AudioFunction.WORK_THREAD.push(AudioFunction.COMMAND.cmd)

    @staticmethod
    def stop_audio():
        AudioFunction.COMMAND.stop()

    @staticmethod
    def start_record(cb):
        if not AudioFunction.HAS_BEEN_INIT:
            raise RuntimeError("The AudioFunction should be initialized before calling APIs")
        AudioFunction.COMMAND.stop()
        AudioFunction.AUDIO_CONFIG.cb = cb
        AudioFunction.COMMAND.cmd = ToneDetectCommand(config=AudioFunction.AUDIO_CONFIG, framemillis=50, nfft=2048)
        AudioFunction.WORK_THREAD.push(AudioFunction.COMMAND.cmd)

class ToneDetectorThread(threading.Thread):
    def __init__(self, target_freq, callback):
        super(ToneDetectorThread, self).__init__()
        self.daemon = True
        self.stoprequest = threading.Event()
        self.event_counter = 0
        self.target_freq = target_freq
        self.cb = callback
        self.extra = None

    def join(self, timeout=None):
        self.stoprequest.set()
        super(ToneDetectorThread, self).join(timeout)

    def run(self):
        raise RuntimeError("The base class does not have implemented run() function.")

    def target_detected(self, freq):
        if freq == 0:
            return False

        if self.target_freq == None:
            return True

        diff_semitone = np.abs(np.log(1.0*freq/self.target_freq) / np.log(2) * 12)
        return diff_semitone < 2

class ToneDetectorForDeviceThread(ToneDetectorThread):
    def __init__(self, serialno, target_freq, callback):
        super(ToneDetectorForDeviceThread, self).__init__(target_freq=target_freq, callback=callback)
        self.serialno = serialno

    def push_to_dump(self, msg):
        self.extra["dump-lock"].acquire()
        self.extra["dump"].append(msg)
        self.extra["dump-lock"].release()

    def clear_dump(self):
        self.extra["dump-lock"].acquire()
        del self.extra["dump"][:]
        self.extra["dump-lock"].release()

    def dump(self):
        self.extra["dump-lock"].acquire()
        Logger.log("ToneDetectorForDeviceThread", "dump called")
        Logger.log("ToneDetectorForDeviceThread", "----------------------------------------------")
        map(lambda msg: Logger.log("ToneDetectorForDeviceThread::dump", "\"{}\"".format(msg)), self.extra["dump"])
        del self.extra["dump"][:]
        Logger.log("ToneDetectorForDeviceThread", "----------------------------------------------")
        self.extra["dump-lock"].release()

    def join(self, timeout=None):
        super(ToneDetectorForDeviceThread, self).join(timeout)

    def run(self):
        shared_vars = {
            "start_time": None,
            "last_event": None,
            "last_freq": -1
        }

        self.extra = {}
        self.extra["adb-read-prop-max-elapsed"] = -1
        self.extra["freq-cb-max-elapsed"] = -1
        self.extra["dump"] = []
        self.extra["dump-lock"] = threading.Lock()

        def freq_cb(msg):
            strs = msg.split()
            freq, amp_db = map(float, strs[-1].split(","))
            the_date, the_time = strs[:2]

            time_str = the_date + " " + the_time

            if shared_vars["last_freq"] != freq:
                Logger.log("ToneDetectorForDeviceThread", \
                    "the detected freq has been changed from {} to {} Hz".format(shared_vars["last_freq"], freq))
                shared_vars["last_freq"] = freq

            thresh = 10 if self.target_freq else 1
            if super(ToneDetectorForDeviceThread, self).target_detected(freq):
                self.event_counter += 1
                if self.event_counter == 1:
                    shared_vars["start_time"] = time_str
                if self.event_counter == thresh:
                    if not shared_vars["last_event"] or shared_vars["last_event"] != ToneDetector.Event.TONE_DETECTED:
                        Logger.log("ToneDetectorForDeviceThread", "send_cb({}, TONE_DETECTED)".format(shared_vars["start_time"]))
                        self.cb((shared_vars["start_time"], ToneDetector.Event.TONE_DETECTED))
                        shared_vars["last_event"] = ToneDetector.Event.TONE_DETECTED

            else:
                if self.event_counter > thresh:
                    shared_vars["start_time"] = None
                    self.push_to_dump("the tone is not detected and the event_counter is over the threshold")
                    self.push_to_dump("last_event: \"{}\"".format(shared_vars["last_event"]))
                    if not shared_vars["last_event"] or shared_vars["last_event"] != ToneDetector.Event.TONE_MISSING:
                        Logger.log("ToneDetectorForDeviceThread", "send_cb({}, TONE_MISSING)".format(time_str))
                        self.cb((time_str, ToneDetector.Event.TONE_MISSING))
                        shared_vars["last_event"] = ToneDetector.Event.TONE_MISSING
                self.event_counter = 0

            if self.event_counter <= thresh: self.push_to_dump("event_counter: {}".format(self.event_counter))

        Adb.execute(cmd= \
            ["shell", "am", "broadcast", "-a", "audio.htc.com.intent.print.properties.enable", "--ez", "v", "1"], \
            serialno=self.serialno)

        from libs.tictoc import TicToc
        freq_cb_tictoc = TicToc()
        adb_tictoc = TicToc()

        freq_cb_tictoc.tic()
        while not self.stoprequest.isSet():
            adb_tictoc.tic()
            msg, _ = Adb.execute(cmd=["shell", "cat", "sdcard/AudioFunctionsDemo-record-prop.txt"], \
                serialno=self.serialno, tolog=False)
            elapsed = adb_tictoc.toc()

            if elapsed > self.extra["adb-read-prop-max-elapsed"]:
                self.extra["adb-read-prop-max-elapsed"] = elapsed

            if "," in msg:
                msg = msg.replace("\n", "")
                import datetime
                t = datetime.datetime.now()
                msg = "{:02d}-{:02d} {:02d}:{:02d}:{:02d}.{:06d} {}".format( \
                    t.month, t.day, t.hour, t.minute, t.second, t.microsecond, msg)

                try:
                    self.push_to_dump("{} (adb-shell elapsed: {} ms)".format(msg, elapsed))
                    freq_cb(msg)
                except Exception as e:
                    Logger.log("ToneDetectorThread", "crashed in freq_cb('{}')".format(msg))

                elapsed = freq_cb_tictoc.toc()
                if elapsed > self.extra["freq-cb-max-elapsed"]:
                    self.extra["freq-cb-max-elapsed"] = elapsed

            time.sleep(0.01)

        Adb.execute(cmd= \
            ["shell", "am", "broadcast", "-a", "audio.htc.com.intent.print.properties.enable", "--ez", "v", "0"], \
            serialno=self.serialno)


class ToneDetectorForServerThread(ToneDetectorThread):
    def __init__(self, target_freq, callback):
        super(ToneDetectorForServerThread, self).__init__(target_freq=target_freq, callback=callback)

    def join(self, timeout=None):
        super(ToneDetectorForServerThread, self).join(timeout)

    def run(self):
        shared_vars = {
            "start_time": None,
            "last_event": None
        }

        def freq_cb(detected_tone, detected_amp_db):
            time_str = datetime.datetime.strftime(datetime.datetime.now(), ToneDetector.TIME_STR_FORMAT)
            freq = detected_tone

            thresh = 2 if self.target_freq else 1
            if super(ToneDetectorForServerThread, self).target_detected(freq):
                self.event_counter += 1
                if self.event_counter == 1:
                    shared_vars["start_time"] = time_str
                if self.event_counter == thresh:
                    if not shared_vars["last_event"] or shared_vars["last_event"] != ToneDetector.Event.TONE_DETECTED:
                        self.cb((shared_vars["start_time"], ToneDetector.Event.TONE_DETECTED))
                        shared_vars["last_event"] = ToneDetector.Event.TONE_DETECTED

            else:
                if self.event_counter > thresh:
                    shared_vars["start_time"] = None
                    if not shared_vars["last_event"] or shared_vars["last_event"] != ToneDetector.Event.TONE_MISSING:
                        self.cb((time_str, ToneDetector.Event.TONE_MISSING))
                        shared_vars["last_event"] = ToneDetector.Event.TONE_MISSING
                self.event_counter = 0

        AudioFunction.start_record(cb=freq_cb)

        while not self.stoprequest.isSet():
            time.sleep(0.1)

        AudioFunction.stop_audio()


class ToneDetector(object):
    WORK_THREAD = None

    TIME_STR_FORMAT = "%m-%d %H:%M:%S.%f"

    class Event(object):
        TONE_DETECTED = "tone detected"
        TONE_MISSING = "tone missing"

    @staticmethod
    def start_listen(target_freq, cb, serialno=None):
        if serialno:
            ToneDetector.WORK_THREAD = ToneDetectorForDeviceThread(serialno=serialno, target_freq=target_freq, callback=cb)
        else:
            ToneDetector.WORK_THREAD = ToneDetectorForServerThread(target_freq=target_freq, callback=cb)
        ToneDetector.WORK_THREAD.start()

    @staticmethod
    def stop_listen():
        ToneDetector.WORK_THREAD.join()
        ToneDetector.WORK_THREAD = None

class DetectionStateListener(object):
    class Event(object):
        ACTIVE = "active"
        INACTIVE = "inactive"
        RISING_EDGE = "rising"
        FALLING_EDGE = "falling"

    def __init__(self):
        self.daemon = True
        self.stoprequest = threading.Event()
        self.event_q = queue.Queue()
        self.current_event = None
        Logger.init()

    def reset(self):
        # reset function must consider the event handling:
        #   if the current state is not None, the active/inactive event might have been sent
        #   and such event should be sent again because it must be same with the case of None -> active
        #   so the active/inactive event needs to be sent again before setting the current state to None
        active_or_inactive = None
        if self.current_event:
            active_or_inactive = DetectionStateListener.Event.ACTIVE \
                            if self.current_event[1] == ToneDetector.Event.TONE_DETECTED else \
                                 DetectionStateListener.Event.INACTIVE

        with self.event_q.mutex:
            self.event_q.queue.clear()

        if active_or_inactive:
            Logger.log("DetectionStateListener", "reset and resend the event ({}, 0)".format(active_or_inactive))
            self.event_q.put((active_or_inactive, 0))

    def tone_detected_event_cb(self, event):
        Logger.log("DetectionStateListener", "tone_detected_event_cb: {}".format(event))
        self._handle_event(event)

    def _handle_event(self, event):
        active_or_inactive = DetectionStateListener.Event.ACTIVE \
                        if event[1] == ToneDetector.Event.TONE_DETECTED else \
                             DetectionStateListener.Event.INACTIVE

        self.event_q.put((active_or_inactive, 0))

        if self.current_event and self.current_event[1] != event[1]:
            rising_or_falling = DetectionStateListener.Event.RISING_EDGE \
                            if event[1] == ToneDetector.Event.TONE_DETECTED else \
                                DetectionStateListener.Event.FALLING_EDGE

            t2 = datetime.datetime.strptime(event[0], ToneDetector.TIME_STR_FORMAT)
            t1 = datetime.datetime.strptime(self.current_event[0], ToneDetector.TIME_STR_FORMAT)
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
                Logger.log("DetectionStateListener", "get event: {}".format(ev))
                if ev[0] == event:
                    return ev[1]
            except queue.Empty:
                if self.current_event:
                    active_or_inactive = DetectionStateListener.Event.ACTIVE \
                        if self.current_event[1] == ToneDetector.Event.TONE_DETECTED else \
                             DetectionStateListener.Event.INACTIVE
                    if active_or_inactive == event:
                        Logger.log("DetectionStateListener", "the current state '{}' fits the waited event".format(event))
                        return 0
        return -1
