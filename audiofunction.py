from audiothread import *

# Initialization of used variables
class CommandHandler(object):
    def __init__(self):
        self.cmd = None

    def stop(self):
        if self.cmd:
            self.cmd.stop()

WORK_THREAD = AudioCommandThread()
WORK_THREAD.daemon = True
AUDIO_CONFIG = AudioConfig(fs=16000, ch=1)
COMMAND = CommandHandler()

def init():
    WORK_THREAD.start()

def finalize():
    WORK_THREAD.join()

def play_sound(out_freq):
    global WORK_THREAD, AUDIO_CONFIG, COMMAND
    COMMAND.cmd = TonePlayCommand(config=AUDIO_CONFIG, out_freq=out_freq)
    WORK_THREAD.push(COMMAND.cmd)

def stop_audio():
    global COMMAND
    COMMAND.stop()

def start_record(cb):
    global WORK_THREAD, AUDIO_CONFIG, COMMAND
    AUDIO_CONFIG.cb = cb
    COMMAND.cmd = ToneDetectCommand(config=AUDIO_CONFIG, framemillis=100, nfft=4096)
    WORK_THREAD.push(COMMAND.cmd)
