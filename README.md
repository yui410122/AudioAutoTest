# AudioAutoTest
## Description
This is a auto-testing framework of audio functions for Android devices.

## Repository
```
AudioAutoTest/
├── AudioFiles
│   ├── 440Hz.mp3
│   └── 440Hz.wav
├── install.sh
├── libs
│   ├── aatapp.py
│   ├── audiofunction.py
│   ├── audiothread.py
│   ├── __init__.py
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

    record_task_run(device, serialno)

    AudioFunction.finalize()
    Logger.finalize()

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
    log("Trying to wait a timeout event")
    elapsed = th.wait_for_event(DetectionStateChangeListenerThread.Event.FALLING_EDGE, timeout=10)
    log("elapsed: {} ms".format(elapsed))

    log("dev_record_stop")
    AATApp.record_stop(device)

    log("ToneDetector.stop_listen()")
    ToneDetector.stop_listen()
    AudioFunction.stop_audio()


if __name__ == "__main__":
    run()
```

```
[2017-11-13 16:19:53.724299] example.py: dev_record_start
[2017-11-13 16:19:55.858921] example.py: ToneDetector.start_listen(serialno=HT75R1C00120, target_freq=440)
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
[2017-11-13 16:20:20.422659] example.py: ToneDetector.stop_listen()
```
