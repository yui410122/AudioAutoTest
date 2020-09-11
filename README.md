# AudioAutoTest
## Description
This is a auto-testing framework of audio functions for Android devices.

- For checking the detailed information of APIs, please refer to the [documentation](https://github.com/HW-Lee/AudioAutoTest/blob/master/libs/README.md)

## Release Note
### v1.2
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
