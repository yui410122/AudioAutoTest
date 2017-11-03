# AudioAutoTest

## audiothread.py

### Examples
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
cmd_q.put(cmd)
```
#### Detecting the frequency with its corresponding amplitude
```python
def result_cb(detected_tone, detected_amp_db):
    if detected_amp_db > 0:
        print("detected: ", int(detected_tone), " Hz", end="\r", flush=True)

cmd = ToneDetectCommand(config=AudioConfig(fs=16000, cb=result_cb), framemillis=100, nfft=4096)
cmd_q.put(cmd)
```
#### Stoping the action
```python
cmd.stop()
```
#### Stoping the thread
```python
th.join()
```