from com.dtmilano.android.viewclient import ViewClient
import json

import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs.logger import Logger
from libs.googlemusichelper import GoogleMusicApp

TAG = "google-music-test.py"

def log(msg):
    Logger.log(TAG, msg)

def run():
    Logger.init(Logger.Mode.STDOUT)
    log("Hello, test.")

    device, serialno = ViewClient.connectToDeviceOrExit(serialno=None)
    gmhandler = GoogleMusicApp(device, serialno)
    gmhandler.walk_through()
    gmhandler.dump()
    log(json.dumps(gmhandler.cache, indent=2))

    Logger.finalize()


if __name__ == "__main__":
    argv = sys.argv[1:]
    del sys.argv[1:]
    run(*argv)