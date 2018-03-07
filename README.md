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
│   ├── 440Hz_mp3.mp3
│   └── 440Hz_wav.wav
├── install.sh
├── libs
│   ├── __init__.py
│   ├── aatapp.py
│   ├── audiofunction.py
│   ├── audiothread.py
│   ├── logcatlistener.py
│   ├── logger.py
│   ├── tictoc.py
│   ├── trials.py
│   └── README.md
├── README.md
├── requirements.txt
├── scripts
│   ├── example.py
│   └── ssr_test.py
└── tools-for-dev
    ├── dump-screen.py
    ├── genwave.py
    └── viewclient-example.py
```

- For checking the detailed information of APIs, please refer to the [documentation](https://github.com/HW-Lee/AudioAutoTest/blob/master/libs/README.md)

## Installation
### Requirements
- pip
- Python 2.7 (3.x is not supported in `ViewClient`)
- virtualenv

#### Create a virtual environment
```
{WORK_DIR}$ mkdir venv
{WORK_DIR}$ virtualenv -p python2 venv/py2
Running virtualenv with interpreter /usr/bin/python2
New python executable in {WORK_DIR}/venv/py2/bin/python2
Also creating executable in {WORK_DIR}/venv/py2/bin/python
Installing setuptools, pip, wheel...done.
{WORK_DIR}$ source venv/py2/bin/activate
(py2) {WORK_DIR}$
```

#### The dependencies should be installed with a command
```
(py2) {WORK_DIR}$ pip install -r requirements.txt
```

#### Tested the example scripts
```
(py2) {WORK_DIR}$ python scripts/example.py
```
