from com.dtmilano.android.viewclient import ViewClient
import subprocess
import time

import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs import ROOT_DIR, SEP, STDNUL
from libs.logger import Logger
from libs.aatapp import AATApp
from libs.audiofunction import AudioFunction, ToneDetector, DetectionStateListener
from libs.trials import Trial, TrialHelper
from libs.adbutils import Adb
from libs.googlemusichelper import GoogleMusicApp

TAG = "basic_test.py"

DEVICE_MUSIC_DIR = "sdcard/Music/"
FILE_NAMES = [
    "440Hz_wav.wav",
    "440Hz_mp3.mp3"
]

def clear_and_update_music_files(serialno):
    filenames, _ = Adb.execute(cmd=["shell", "ls", DEVICE_MUSIC_DIR], serialno=serialno)
    filenames = filenames.split()
    cmdprefix = ["shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d"]
    for filename in filenames:
        Adb.execute(cmd=["shell", "rm", DEVICE_MUSIC_DIR + filename], serialno=serialno)
        Adb.execute(cmd=cmdprefix+["file:///mnt/" + DEVICE_MUSIC_DIR + filename], serialno=serialno)

    for file_to_pushed in FILE_NAMES:
        out, _ = subprocess.Popen(["find", ROOT_DIR, "-name", file_to_pushed], stdout=subprocess.PIPE).communicate()
        file_path = out.splitlines()[0] if out else None
        if file_path:
            Adb.execute(cmd=["push", file_path, DEVICE_MUSIC_DIR], serialno=serialno)
            Adb.execute(cmd=cmdprefix+["file:///mnt/" + DEVICE_MUSIC_DIR + file_to_pushed], serialno=serialno)

def log(msg):
    Logger.log(TAG, msg)

def run(num_iter=1):
    AudioFunction.init()
    Logger.init(Logger.Mode.BOTH_FILE_AND_STDOUT)
    Adb.init()

    device, serialno = ViewClient.connectToDeviceOrExit(serialno=None)
    gmhandler = GoogleMusicApp(device, serialno)
    log("gmhandler.to_top()")
    gmhandler.to_top()
    clear_and_update_music_files(serialno)
    time.sleep(10)

    playback_run(num_iter=1, gmhandler=gmhandler)

    AudioFunction.finalize()
    Logger.finalize()

def playback_run(num_iter, gmhandler):
    log("gmhandler.walk_through()")
    if not gmhandler.walk_through():
        log("failed to walk through the UI of the google music")
        gmhandler.dump()

    import json
    log("gmhandler.cache\n{}".format(json.dumps(gmhandler.cache, indent=4, ensure_ascii=False)))

if __name__ == "__main__":
    num_iter = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    # ViewClient tries to access the system arguments, then it might cause RuntimeError
    if len(sys.argv) > 1: del sys.argv[1:]
    run(num_iter=num_iter)
