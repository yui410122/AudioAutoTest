# AudioAutoTest

## audiothread.py

### Examples
#### Simplest way
```python
from audiothread import *

th = AudioCommandThread()
th.start()
```
#### Initialize with the specified work queue
```python
from audiothread import *
import queue

cmd_q = queue.Queue()
th = AudioCommandThread(cmd_q=cmd_q)
th.start()
```
#### Playing pure tone with specific frequency
```python
cmd = TonePlayCommand(config=AudioConfig(fs=16000, ch=1), out_freq=440)
th.push(cmd)
```
#### Detecting the frequency with its corresponding amplitude
```python
def result_cb(detected_tone, detected_amp_db):
    if detected_amp_db > 0:
        print("detected: ", int(detected_tone), " Hz", end="\r", flush=True)

cmd = ToneDetectCommand(config=AudioConfig(fs=16000, cb=result_cb), framemillis=100, nfft=4096)
th.push(cmd)
```
#### Stoping the action
```python
cmd.stop()
```
#### Stoping the thread
```python
th.join()
```
**Note that the `cmd` will be "dirty" after calling `cmd.stop()` and hence it will not be executed when it is pushed again, except for calling `cmd.reset()`**
```python
th.push(cmd)
# blablabla
cmd.stop()
# If you need to execute the same command again
cmd.reset()
th.push(cmd)
```

## Trying to write some testing scripts
### scripts/example.py
```python
from com.dtmilano.android.viewclient import ViewClient
import os
import subprocess
import time
import threading

import sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs import ROOT_DIR
from libs.audiofunction import AATApp, AudioFunction, ToneDetectedDecision, DetectionStateChangeListenerThread
from libs.logger import Logger

TAG = "example.py"
OUT_FREQ = 440

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
    AATApp.record_start(device)
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
    AATApp.record_stop(device)

    log("ToneDetectedDecision.stop_listen()")
    ToneDetectedDecision.stop_listen()
    AudioFunction.stop_audio()


if __name__ == "__main__":
    run()
```

```
[2017-11-13 16:19:53.724299] example.py: dev_record_start
[2017-11-13 16:19:55.858921] example.py: ToneDetectedDecision.start_listen(serialno=HT75R1C00120, target_freq=440)
[2017-11-13 16:20:02.037908] example.py: AudioFunction.play_sound(out_freq=440)
[2017-11-13 16:20:03.542540] DetectionStateChangeListenerThread: tone_detected_event_cb: ('11-13 16:19:58.386', 'tone detected')
[2017-11-13 16:20:05.044482] example.py: thread stops the playback
[2017-11-13 16:20:05.044582] example.py: Waiting for 440 Hz pure tone detected
[2017-11-13 16:20:05.276272] DetectionStateChangeListenerThread: tone_detected_event_cb: ('11-13 16:20:01.379', 'tone missing')
[2017-11-13 16:20:09.044131] example.py: thread starts the playback
[2017-11-13 16:20:09.044249] example.py: thread returns
[2017-11-13 16:20:10.309191] DetectionStateChangeListenerThread: tone_detected_event_cb: ('11-13 16:20:05.281', 'tone detected')
[2017-11-13 16:20:10.309316] example.py: elapsed: 3902.0 ms
[2017-11-13 16:20:10.309406] example.py: Trying to wait a timeout event
[2017-11-13 16:20:20.322337] example.py: elapsed: -1 ms
[2017-11-13 16:20:20.322461] example.py: dev_record_stop
[2017-11-13 16:20:20.422659] example.py: ToneDetectedDecision.stop_listen()
```
