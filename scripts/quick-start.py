import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs.argutils import AATArgParseUtils
from libs.adbutils import Adb
from libs.logger import Logger

LOGGER_TAG = "quick-start"

def run(num_iter=1, serialno=None):
    num_iter = int(num_iter)
    Adb.init()
    Logger.init(Logger.Mode.BOTH_FILE_AND_STDOUT, prefix="quick-start")

    check_props = {
        "Device name": "ro.product.model",
        "Project": "ro.build.product",
        "ROM": "ro.product.build.fingerprint",
    }

    passed = True
    for tag, prop in check_props.items():
        out, err = Adb.execute(["shell", "getprop {}".format(prop)], serialno=serialno)
        passed &= len(err) == 0
        out = out.strip()
        Logger.log(LOGGER_TAG, "{}: {}".format(tag, out))

    Logger.log(LOGGER_TAG, "result: {}".format("passed" if passed else "failed"))
    Logger.finalize()

if __name__ == "__main__":
    success, ret = AATArgParseUtils.parse_arg(sys.argv[1:], options=["num_iter=", "serialno="], required=["serialno"])
    if not success:
        raise(ret)

    if len(sys.argv) > 1: del sys.argv[1:]
    run(**ret)
