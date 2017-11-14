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
[2017-11-14 17:07:40.861162] example.py: dev_record_start
[2017-11-14 17:07:42.927700] example.py: ToneDetector.start_listen(serialno=HT75R1C00120, target_freq=440)
[2017-11-14 17:07:49.168638] example.py: AudioFunction.play_sound(out_freq=440)
[2017-11-14 17:07:50.270595] DetectionStateChangeListenerThread: tone_detected_event_cb: ('11-14 17:07:45.077', 'tone detected')
[2017-11-14 17:07:52.173830] example.py: Waiting for 440 Hz pure tone detected
[2017-11-14 17:07:52.173946] DetectionStateChangeListenerThread: get event: ('active', 0)
[2017-11-14 17:07:52.173986] example.py: thread stops the playback
[2017-11-14 17:07:52.574604] DetectionStateChangeListenerThread: tone_detected_event_cb: ('11-14 17:07:48.271', 'tone missing')
[2017-11-14 17:07:52.574725] DetectionStateChangeListenerThread: get event: ('inactive', 0)
[2017-11-14 17:07:52.574770] DetectionStateChangeListenerThread: get event: ('falling', 3194.0)
[2017-11-14 17:07:56.179464] example.py: thread starts the playback
[2017-11-14 17:07:56.179604] example.py: thread returns
[2017-11-14 17:07:57.180927] DetectionStateChangeListenerThread: tone_detected_event_cb: ('11-14 17:07:52.036', 'tone detected')
[2017-11-14 17:07:57.181038] DetectionStateChangeListenerThread: get event: ('active', 0)
[2017-11-14 17:07:57.181132] DetectionStateChangeListenerThread: get event: ('rising', 3765.0)
[2017-11-14 17:07:57.181193] example.py: elapsed: 3765.0 ms
[2017-11-14 17:07:57.181260] example.py: Trying to wait a timeout event
[2017-11-14 17:08:07.195175] example.py: elapsed: -1 ms
[2017-11-14 17:08:07.195293] example.py: dev_record_stop
[2017-11-14 17:08:07.295486] example.py: ToneDetector.stop_listen()
```
