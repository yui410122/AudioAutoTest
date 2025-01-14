# AudioAutoTest
## Description
This is a auto-testing framework of audio functions for Android devices.

- For checking the detailed information of APIs, please refer to the [documentation](https://github.com/HW-Lee/AudioAutoTest/blob/master/libs/README.md)

## Release Note
### v1.5
### v1.5.6
- Update the version of scikit-learn for the compatibility of Python 3.11.4

### v1.5.5
- Fix the crash when calling Adb.disable_wifi_adb after Adb.is_wifi_adb_supported

### v1.5.4
- Add timeout support for Adb APIs.

### v1.5.3
- Update audioworker.apk (c66b90f-python-audio-autotest-v1.5.3)
- Add btsco_on option in record_start
- Add file option in playback_nonoffload

### v1.5.2
- Update audioworker.apk (ecf0145-python-audio-autotest-v1.5.2)
- Update setup.py to compact Python3.10

### v1.5.1
- Update audioworker.apk (44f0c2c66-python-audio-autotest-v1.5.1)
- PlaybackStartFunction supports file playing in offload types (.mp3, .aac)
- Playback and capture support more sampling rates and channels
- Update audioworker_test.py
- Fix versions of dependencies to avoid them from breaking in future releases
- Add `get_apk_version` in `AppInterface`
- Add `get_version_from_device` in `AudioWorkerApp`

### v1.5
- Update audioworker.apk (4ca8a47-python-audio-autotest-v1.5)
- AudioWorker supports concurrent capture
- PyAAT supports concurrent capture control on AudioWorker
- Some coding style reformation on audioworker.py
- Add test scripts to verify the compatibility between AudioWorker and PyAAT
  - Playback
  - Record

### v1.4
### v1.4.3
- Update audioworker.apk

### v1.4.2
- AudioWorker supports different input sources, APIs, and performance modes

### v1.4.1 (Deleted)
- fix crashes in Adb.safe_clean_non_default_sockets()

### v1.4.0 (Deleted)
- support using an independent socket to manage wifi adb devices
- keep the identical behavior when the adb multi-socket listening is disabled

### v1.3
### v1.3.6
- pyaatlibs: adb: fix line length
- pyaatlibs: adbutils: use "cmd wifi status" instead of "ip addr show wlan0" to check wifi status
- pyaatlibs: adbutils: suppress logs if tolog is false

### v1.3.5 (Deleted)
- support using an independent socket to manage wifi adb devices

### v1.3.4
- update audioworker.apk: configurable input source for recording

### v1.3.3
- add API to get the IP addr used by Wifi adb.

### v1.3.2
- fix the logic of whether it's feasible to use wifi adb

### v1.3.1
- add delay between "adb tcpip" and "adb connect"

### v1.3.0
- support wifi adb

### v1.2
### v1.2.12
- fix the memory leakage of repeatedly initialization with the same name.

### v1.2.11
- store the running threads instead of directly using the iterator to avoid exceptions.

### v1.2.10
- make logger always print messages with default settings.

### v1.2.8
- fix granting permissions for Android apps.

### v1.2.7
- update audioworker to solve recording underrun.

#### v1.2.5
- simplify AudioWorkerApp.voip_tx_dump

#### v1.2.1
- change log tag with verbosity level of `pyaat.logger`
- correct README

#### v1.2.0
- add verbosity level control of `pyaatlibs.logger`
- add `wait_for_device` API of `pyaatlibs.adbutils`

## Installation
### Requirements
- pip
- Python 3.7+
- virtualenv

#### Create a virtual environment
```
{WORK_DIR}$ mkdir venv
{WORK_DIR}$ virtualenv -p python3 venv/py3
Running virtualenv with interpreter /usr/bin/python3
New python executable in {WORK_DIR}/venv/py3/bin/python
Also creating executable in {WORK_DIR}/venv/py3/bin/python
Installing setuptools, pip, wheel...done.
{WORK_DIR}$ source venv/py3/bin/activate
(py3) {WORK_DIR}$
```

#### The dependencies should be installed with a command
```
(py3) {WORK_DIR}$ pip install -r requirements-py3.txt
```
