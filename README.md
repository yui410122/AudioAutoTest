# AudioAutoTest
## Description
This is a auto-testing framework of audio functions for Android devices.

## Repository
```
AudioAutoTest/
├── apk
│   └── debug
│       ├── audiofunctionsdemo.apk
│       └── output.json
├── audiofiles
│   ├── 440Hz.mp3
│   └── 440Hz.wav
├── install.sh
├── libs
│   ├── __init__.py
│   ├── aatapp.py
│   ├── audiofunction.py
│   ├── audiothread.py
│   ├── logcatlistener.py
│   ├── logger.py
│   └── README.md
├── README.md
├── requirements.txt
└── scripts
    ├── example.py
    └── ssr_test.py
```

- For checking the detailed information of APIs, please refer to the [documentation](https://github.com/HW-Lee/AudioAutoTest/blob/master/libs/README.md)

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
from libs.audiofunction import AudioFunction, ToneDetector, DetectionStateChangeListenerThread
from libs.logger import Logger
from libs.aatapp import AATApp

TAG = "example.py"
OUT_FREQ = 440

def log(msg):
    Logger.log(TAG, msg)

def run():
    AudioFunction.init()
    Logger.init(Logger.Mode.STDOUT)
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

    playback_task_run(device)
    record_task_run(device, serialno)

    AudioFunction.finalize()
    Logger.finalize()

def playback_task_run(device):
    log("dev_playback_start(nonoffload)")
    AATApp.playback_nonoffload(device)

    th = DetectionStateChangeListenerThread()
    th.start()

    log("ToneDetector.start_listen(target_freq={})".format(OUT_FREQ))
    ToneDetector.start_listen(target_freq=OUT_FREQ, cb=lambda event: th.tone_detected_event_cb(event))

    if th.wait_for_event(DetectionStateChangeListenerThread.Event.ACTIVE, timeout=5) < 0:
        log("the tone was not detected, abort the function...")
        AATApp.playback_stop(device)
        return

    time.sleep(1)

    def dev_stop_then_play():
        log("thread stops the playback")
        AATApp.playback_stop(device)
        time.sleep(4)
        log("thread starts the playback")
        AATApp.playback_nonoffload(device)
        log("thread returns")

    threading.Thread(target=dev_stop_then_play).start()
    log("Waiting for {} Hz pure tone detected".format(OUT_FREQ))
    elapsed = th.wait_for_event(DetectionStateChangeListenerThread.Event.RISING_EDGE, timeout=10)
    log("elapsed: {} ms".format(elapsed))

    log("ToneDetector.stop_listen()")
    ToneDetector.stop_listen()
    th.join()

    log("dev_playback_stop(nonoffload)")
    AATApp.playback_stop(device)


def record_task_run(device, serialno):
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

    time.sleep(1)

    log("Trying to wait a timeout event")
    elapsed = th.wait_for_event(DetectionStateChangeListenerThread.Event.FALLING_EDGE, timeout=10)
    log("elapsed: {} ms".format(elapsed))

    log("dev_record_stop")
    AATApp.record_stop(device)

    log("ToneDetector.stop_listen()")
    ToneDetector.stop_listen()
    th.join()

    AudioFunction.stop_audio()


if __name__ == "__main__":
    run()
```

```
[2017-11-14 19:00:44.178287] example.py: dev_playback_start(nonoffload)
[2017-11-14 19:00:44.278559] example.py: ToneDetector.start_listen(target_freq=440)
[2017-11-14 19:00:44.742716] DetectionStateChangeListenerThread: tone_detected_event_cb: ('11-14 19:00:44.686626', 'tone detected')
[2017-11-14 19:00:44.758219] DetectionStateChangeListenerThread: get event: ('active', 0)
[2017-11-14 19:00:45.759623] example.py: thread stops the playback
[2017-11-14 19:00:45.759733] example.py: Waiting for 440 Hz pure tone detected
[2017-11-14 19:00:46.191784] DetectionStateChangeListenerThread: tone_detected_event_cb: ('11-14 19:00:46.186130', 'tone missing')
[2017-11-14 19:00:46.191900] DetectionStateChangeListenerThread: get event: ('inactive', 0)
[2017-11-14 19:00:46.191949] DetectionStateChangeListenerThread: get event: ('falling', 1499.504)
[2017-11-14 19:00:49.860090] example.py: thread starts the playback
[2017-11-14 19:00:49.923690] example.py: thread returns
[2017-11-14 19:00:50.339844] DetectionStateChangeListenerThread: tone_detected_event_cb: ('11-14 19:00:50.292214', 'tone detected')
[2017-11-14 19:00:50.371318] DetectionStateChangeListenerThread: get event: ('active', 0)
[2017-11-14 19:00:50.371405] DetectionStateChangeListenerThread: get event: ('rising', 4106.084)
[2017-11-14 19:00:50.371437] example.py: elapsed: 4106.084 ms
[2017-11-14 19:00:50.371465] example.py: ToneDetector.stop_listen()
[2017-11-14 19:00:50.371493] example.py: dev_playback_stop(nonoffload)
[2017-11-14 19:00:50.471638] example.py: dev_record_start
[2017-11-14 19:00:52.537983] example.py: ToneDetector.start_listen(serialno=HT75R1C00120, target_freq=440)
[2017-11-14 19:00:58.750057] example.py: AudioFunction.play_sound(out_freq=440)
[2017-11-14 19:01:00.029309] DetectionStateChangeListenerThread: tone_detected_event_cb: ('11-14 19:00:54.672', 'tone detected')
[2017-11-14 19:01:01.763414] example.py: thread stops the playback
[2017-11-14 19:01:01.763544] example.py: Waiting for 440 Hz pure tone detected
[2017-11-14 19:01:01.763657] DetectionStateChangeListenerThread: get event: ('active', 0)
[2017-11-14 19:01:02.127692] DetectionStateChangeListenerThread: tone_detected_event_cb: ('11-14 19:00:57.712', 'tone missing')
[2017-11-14 19:01:02.127852] DetectionStateChangeListenerThread: get event: ('inactive', 0)
[2017-11-14 19:01:02.127892] DetectionStateChangeListenerThread: get event: ('falling', 3040.0)
[2017-11-14 19:01:05.764172] example.py: thread starts the playback
[2017-11-14 19:01:05.764279] example.py: thread returns
[2017-11-14 19:01:06.829230] DetectionStateChangeListenerThread: tone_detected_event_cb: ('11-14 19:01:01.514', 'tone detected')
[2017-11-14 19:01:06.829327] DetectionStateChangeListenerThread: get event: ('active', 0)
[2017-11-14 19:01:06.829383] DetectionStateChangeListenerThread: get event: ('rising', 3802.0)
[2017-11-14 19:01:06.829415] example.py: elapsed: 3802.0 ms
[2017-11-14 19:01:07.831154] example.py: Trying to wait a timeout event
[2017-11-14 19:01:17.844611] example.py: elapsed: -1 ms
[2017-11-14 19:01:17.844748] example.py: dev_record_stop
[2017-11-14 19:01:17.944896] example.py: ToneDetector.stop_listen()
```
