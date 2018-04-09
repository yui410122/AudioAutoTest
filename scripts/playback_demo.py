import subprocess
import threading
import datetime
import time
import json
import numpy as np
from scipy.fftpack import fft

try:
    import queue
except ImportError:
    import Queue as queue

import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs.logger import Logger
from libs.audiofunction import AudioFunction
from libs.audiothread import RawRecordCommand, AudioConfig
from libs.audiosignalframelogger import AudioSignalFrameLogger
from libs.tictoc import TicToc
from libs.signalanalyzer import sort_values

TAG = "playback_demo.py"
FRAMEMILLIS = 20
FS = 8000
FREQ = 440

def target_detected(freq, target_freq):
    if freq == 0:
        return False

    if target_freq == None:
        return True

    diff_semitone = np.abs(np.log(1.0*freq/target_freq) / np.log(2) * 12)
    return diff_semitone < 2

def run(num_iter=1):
    AudioFunction.init()
    Logger.init(Logger.Mode.STDOUT)

    Logger.log(TAG, "delete the existed dump folder...")
    subprocess.Popen(["rm", "-rf", "./record-dump"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

    audiodump = AudioSignalFrameLogger()
    databuff = queue.Queue()
    th_tictoc = TicToc()
    push_tictoc = TicToc()
    push_tictoc.extra = {
        "initialized": False,
        "max_period": -1,
        "avg_period": -1,
        "push_count": 0,
        "max_snr": None,
        "min_snr": None,
        "avg_snr": -1
    }
    def process_buff():
        th_tictoc.tic()
        try:
            data = databuff.get(timeout=FRAMEMILLIS*.1/1000.)
            if push_tictoc.extra["initialized"]:
                elapsed = push_tictoc.toc()
                push_tictoc.extra["max_period"] = max([push_tictoc.extra["max_period"], elapsed])
                push_tictoc.extra["avg_period"] *= push_tictoc.extra["push_count"]
                push_tictoc.extra["avg_period"] += elapsed
                push_tictoc.extra["avg_period"] /= float(push_tictoc.extra["push_count"]+1)
            else:
                push_tictoc.tic()
                push_tictoc.extra["initialized"] = True

            push_tictoc.extra["push_count"] += 1

            audiodump.push(name="signal", fs=FS, values=data)
            nfft = np.ceil(np.log2(data.shape[0]))
            nfft = int(2**nfft)
            spectrum = np.abs(fft(data.flatten(), nfft))
            audiodump.push(name="spectrum", fs=-1, values=spectrum)

            spectrum = spectrum[:nfft/2]
            unit_freq = FS*1./nfft
            spectrum = map(lambda x: (x[0]*unit_freq, -x[1]), sort_values(-spectrum))
            signal_spectrum = filter(lambda x: target_detected(freq=x[0], target_freq=FREQ), spectrum)
            noise_spectrum = filter(lambda x: not target_detected(freq=x[0], target_freq=FREQ), spectrum)
            if len(signal_spectrum) > 0 and len(noise_spectrum) > 0:
                snr = np.mean(map(lambda x: x[1], signal_spectrum)) / np.mean(map(lambda x: x[1], noise_spectrum))
                snr = 20*np.log10(snr)
                if target_detected(freq=spectrum[0][0], target_freq=FREQ):
                    if push_tictoc.extra["max_snr"] == None or push_tictoc.extra["max_snr"][0] < snr:
                        push_tictoc.extra["max_snr"] = [snr, push_tictoc.extra["push_count"]-1]
                    if push_tictoc.extra["min_snr"] == None or push_tictoc.extra["min_snr"][0] > snr:
                        push_tictoc.extra["min_snr"] = [snr, push_tictoc.extra["push_count"]-1]
                    push_tictoc.extra["avg_snr"] *= (push_tictoc.extra["push_count"]-1)
                    push_tictoc.extra["avg_snr"] += snr
                    push_tictoc.extra["avg_snr"] /= float(push_tictoc.extra["push_count"])

            sleeptime = max([FRAMEMILLIS - th_tictoc.toc(), 0])
            time.sleep(sleeptime * .99/1000.)
        except queue.Empty:
            pass

    def threadloop():
        while True:
            process_buff()

    def record_cb(indata):
        databuff.put(indata)

    record_cmd = RawRecordCommand(config=AudioConfig(fs=FS, ch=1, dtype="float32", cb=record_cb), framemillis=FRAMEMILLIS)
    AudioFunction.COMMAND.cmd = record_cmd
    AudioFunction.WORK_THREAD.push(AudioFunction.COMMAND.cmd)
    Logger.log(TAG, "start recording on the server...")

    time.sleep(1)
    Logger.log(TAG, "start processing the data buffers...")
    th = threading.Thread(target=threadloop)
    th.daemon = True
    th.start()

    time.sleep(10)

    AudioFunction.stop_audio()
    Logger.log(TAG, "stop recording on the server...")
    audiodump.dump(path="./record-dump")

    Logger.log(TAG, "------------------------ profiling in process_buff ------------------------")
    Logger.log(TAG, "max period: {}".format(push_tictoc.extra["max_period"]))
    Logger.log(TAG, "avg period: {}".format(push_tictoc.extra["avg_period"]))
    Logger.log(TAG, "push count: {}".format(push_tictoc.extra["push_count"]))
    Logger.log(TAG, "max SNR   : {}".format(push_tictoc.extra["max_snr"]))
    Logger.log(TAG, "min SNR   : {}".format(push_tictoc.extra["min_snr"]))
    Logger.log(TAG, "avg SNR   : {}".format(push_tictoc.extra["avg_snr"]))

    AudioFunction.finalize()
    Logger.finalize()


if __name__ == "__main__":
    run()
