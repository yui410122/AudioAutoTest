import os
import subprocess
import json
import datetime
import time

from pyaatlibs import ROOT_DIR
from pyaatlibs.adbutils import Adb
from pyaatlibs.appinterface import AppInterface

class AudioWorkerApp(AppInterface):
    TAG = "AudioWorkerApp"
    APK_PATHS = [
        os.path.join(ROOT_DIR, "apk", "debug", "audioworker.apk"),
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "apk", "audioworker.apk")
    ]
    INTENT_PREFIX = "am broadcast -a"
    AUDIOWORKER_INTENT_PREFIX = "com.google.audioworker.intent."

    PACKAGE = "com.google.audioworker"
    MAINACTIVITY = ".activities.MainActivity"

    DATA_FOLDER = "/storage/emulated/0/Google-AudioWorker-data"

    @staticmethod
    def get_apk_path():
        for path in __class__.APK_PATHS:
            if os.path.exists(path):
                return path

        raise(RuntimeError("no apk file is found."))

    @staticmethod
    def get_launch_component():
        return "{}/{}".format(__class__.PACKAGE, __class__.MAINACTIVITY)

    @staticmethod
    def get_package():
        return __class__.PACKAGE

    @staticmethod
    def device_shell(device=None, serialno=None, cmd=None, tolog=True):
        if not cmd:
            return

        if device:
            return device.shell(cmd)
        else:
            return Adb.execute(["shell", cmd], serialno=serialno, tolog=tolog)

    @staticmethod
    def is_alive(device=None, serialno=None, tolog=False):
        ack_funcs = [
            __class__.playback_info,
            __class__.record_info,
            __class__.voip_info
        ]

        for func in ack_funcs:
            if func(device, serialno, tolog) == None:
                return False

        return True

    @staticmethod
    def relaunch_app(device=None, serialno=None):
        __class__.stop_app(device, serialno)
        time.sleep(2)
        __class__.launch_app(device, serialno)

    @staticmethod
    def send_intent(device, serialno, name, configs={}, tolog=True):
        cmd_arr = [__class__.INTENT_PREFIX, name]
        for key, value in configs.items():
            if type(value) is float:
                cmd_arr += ["--ef", key]
            elif type(value) is int:
                cmd_arr += ["--ei", key]
            else:
                cmd_arr += ["--es", key]
            cmd_arr.append(str(value))

        __class__.device_shell(device=device, serialno=serialno, cmd=" ".join(cmd_arr), tolog=tolog)

    @staticmethod
    def playback_nonoffload(device=None, serialno=None, freq=440., playback_id=0, fs=16000, nch=2, amp=0.6, bit_depth=16, low_latency_mode=False):
        name = __class__.AUDIOWORKER_INTENT_PREFIX + "playback.start"
        configs = {
            "type": "non-offload",
            "target-freq": freq,
            "playback-id": playback_id,
            "sampling-freq": fs,
            "num-channels": nch,
            "amplitude": amp,
            "pcm-bit-width": bit_depth,
            "low-latency-mode": low_latency_mode
        }
        __class__.send_intent(device, serialno, name, configs)

    @staticmethod
    def playback_offload(device=None, serialno=None, freq=440., playback_id=0, fs=16000, nch=2, amp=0.6, bit_depth=16):
        name = __class__.AUDIOWORKER_INTENT_PREFIX + "playback.start"
        configs = {
            "type": "offload",
            "target-freq": freq,
            "playback-id": playback_id,
            "sampling-freq": fs,
            "num-channels": nch,
            "amplitude": amp,
            "pcm-bit-width": bit_depth
        }
        __class__.send_intent(device, serialno, name, configs)

    @staticmethod
    def _common_info(device=None, serialno=None, ctype=None, controller=None, tolog=False):
        name = __class__.AUDIOWORKER_INTENT_PREFIX + "{}.info".format(ctype)
        ts = datetime.datetime.timestamp(datetime.datetime.now())
        ts = int(ts * 1000)
        filename = "{}-info.txt".format(ts)
        filepath = "{}/{}/{}".format(__class__.DATA_FOLDER, controller, filename)
        __class__.send_intent(device, serialno, name, {"filename": filename}, tolog=tolog)

        retry = 10
        while retry > 0:
            out, err = __class__.device_shell(None, serialno, cmd="cat {}".format(filepath), tolog=tolog)
            if len(out) == 0:
                time.sleep(0.5)
                retry -= 1
                continue
            break

        out = out.splitlines()
        __class__.device_shell(None, serialno, cmd="rm {}".format(filepath), tolog=tolog)
        if len(out) == 0:
            return None
        elif len(out) == 1:
            return {}

        import traceback
        try:
            info_timestamp = float(out[0].strip().split("::")[1]) / 1000.
            info_t = datetime.datetime.fromtimestamp(info_timestamp)
            # if (datetime.datetime.now() - info_t).total_seconds() > 1:
            #     return None
        except:
            traceback.print_exc()
            return None

        return json.loads("".join(out[1:]))

    @staticmethod
    def playback_info(device=None, serialno=None, tolog=False):
        return __class__._common_info(device, serialno, "playback", "PlaybackController", tolog=tolog)

    @staticmethod
    def playback_stop(device=None, serialno=None, tolog=False):
        name = __class__.AUDIOWORKER_INTENT_PREFIX + "playback.stop"
        info = __class__.playback_info(device, serialno, tolog)
        if not info:
            return

        for pbtype in info.keys():
            for pbid in info[pbtype].keys():
                configs = {
                    "type": pbtype,
                    "playback-id": int(pbid)
                }
                __class__.send_intent(device, serialno, name, configs)

    @staticmethod
    def record_info(device=None, serialno=None, tolog=False):
        info = __class__._common_info(device, serialno, "record", "RecordController", tolog=tolog)
        if info == None:
            return None

        if len(info) > 1:
            for key, value in info[1].items():
                info[1][key] = json.loads(value)

        return info

    @staticmethod
    def tx_detector_register(prefix, device, serialno, dclass, params):
        if not dclass:
            return
        try:
            params = json.dumps(json.dumps(params))
        except:
            __class__.log("params cannot be converted to json string")
            return

        name = __class__.AUDIOWORKER_INTENT_PREFIX + "{}.detect.register".format(prefix)
        configs = {
            "class": dclass,
            "params": params
        }
        __class__.send_intent(device, serialno, name, configs)

    @staticmethod
    def tx_detector_unregister(prefix, device, serialno, chandle):
        if not chandle:
            return

        name = __class__.AUDIOWORKER_INTENT_PREFIX + "{}.detect.unregister".format(prefix)
        __class__.send_intent(device, serialno, name, {"class-handle": chandle})

    @staticmethod
    def tx_detector_clear(prefix, device, serialno, info_func):
        info = info_func(device, serialno)
        if not info:
            return

        for chandle in info[1].keys():
            __class__.tx_detector_unregister(prefix, device, serialno, chandle)

    @staticmethod
    def tx_detector_set_params(prefix, device, serialno, chandle, params):
        if not chandle:
            return
        try:
            params = json.dumps(json.dumps(params))
        except:
            __class__.log("params cannot be converted to json string")
            return

        name = __class__.AUDIOWORKER_INTENT_PREFIX + "{}.detect.setparams".format(prefix)
        configs = {
            "class-handle": chandle,
            "params": params
        }
        __class__.send_intent(device, serialno, name, configs)

    @staticmethod
    def record_start(device=None, serialno=None, fs=16000, nch=2, bit_depth=16, dump_buffer_ms=0):
        name = __class__.AUDIOWORKER_INTENT_PREFIX + "record.start"
        configs = {
            "sampling-freq": fs,
            "num-channels": nch,
            "pcm-bit-width": bit_depth,
            "dump-buffer-ms": dump_buffer_ms
        }
        __class__.send_intent(device, serialno, name, configs)

    @staticmethod
    def record_stop(device=None, serialno=None):
        name = __class__.AUDIOWORKER_INTENT_PREFIX + "record.stop"
        __class__.send_intent(device, serialno, name)

    @staticmethod
    def record_dump(device=None, serialno=None, path=None):
        if not path:
            return

        name = __class__.AUDIOWORKER_INTENT_PREFIX + "record.dump"
        __class__.send_intent(device, serialno, name, {"filename": path})

    @staticmethod
    def record_detector_register(device=None, serialno=None, dclass=None, params={}):
        __class__.tx_detector_register("record", device, serialno, dclass, params)

    @staticmethod
    def record_detector_unregister(device=None, serialno=None, chandle=None):
        __class__.tx_detector_unregister("record", device, serialno, chandle)

    @staticmethod
    def record_detector_clear(device=None, serialno=None):
        __class__.tx_detector_clear("record", device, serialno, __class__.record_info)

    @staticmethod
    def record_detector_set_params(device=None, serialno=None, chandle=None, params={}):
        __class__.tx_detector_set_params("record", device, serialno, chandle, params)

    @staticmethod
    def voip_info(device=None, serialno=None, tolog=False):
        return __class__._common_info(device, serialno, "voip", "VoIPController", tolog=tolog)

    @staticmethod
    def voip_start(device=None, serialno=None, rxfreq=440., rxamp=0.6, rxspkr=False,
        rxfs=8000, txfs=8000, rxnch=1, txnch=1, rxbit_depth=16, txbit_depth=16, dump_buffer_ms=0):
        name = __class__.AUDIOWORKER_INTENT_PREFIX + "voip.start"
        configs = {
            "rx-target-freq": rxfreq,
            "rx-amplitude": rxamp,
            "rx-sampling-freq": rxfs,
            "rx-num-channels": rxnch,
            "rx-pcm-bit-width": rxbit_depth,
            "rx-use-spkr": rxspkr,
            "tx-sampling-freq": txfs,
            "tx-num-channels": txnch,
            "tx-pcm-bit-width": txbit_depth,
            "tx-dump-buffer-ms": dump_buffer_ms
        }
        __class__.send_intent(device, serialno, name, configs)

    @staticmethod
    def voip_stop(device=None, serialno=None):
        name = __class__.AUDIOWORKER_INTENT_PREFIX + "voip.stop"
        __class__.send_intent(device, serialno, name)

    @staticmethod
    def voip_use_speaker(device=None, serialno=None, use=True):
        name = __class__.AUDIOWORKER_INTENT_PREFIX + "voip.config"
        configs = {
            "rx-use-spkr": use
        }
        __class__.send_intent(device, serialno, name, configs)

    @staticmethod
    def voip_use_receiver(device=None, serialno=None):
        __class__.voip_use_speaker(device, serialno, use=False)

    @staticmethod
    def voip_change_configs(device=None, serialno=None, rxfreq=-1, rxamp=-1):
        name = __class__.AUDIOWORKER_INTENT_PREFIX + "voip.config"
        configs = {
            "rx-target-freq": rxfreq,
            "rx-amplitude": rxamp
        }
        __class__.send_intent(device, serialno, name, configs)

    @staticmethod
    def voip_mute_output(device=None, serialno=None):
        __class__.voip_change_configs(device, serialno, rxamp=0)

    @staticmethod
    def voip_tx_dump(device=None, serialno=None, path=None, tolog=False):
        if not path:
            return

        dpath = "{}/VoIPController".format(__class__.DATA_FOLDER)
        out, _ = __class__.device_shell(device, serialno, cmd="ls {}".format(dpath), tolog=tolog)
        if len(out.split()) > 0:
            __class__.device_shell(device, serialno, cmd="rm -f {}/*".format(dpath), tolog=tolog)

        name = __class__.AUDIOWORKER_INTENT_PREFIX + "voip.tx.dump"
        __class__.send_intent(device, serialno, name, {"filename": "dump.wav"})

        interval = 0.2
        timeout = 3 / interval
        while timeout > 0:
            out, _ = __class__.device_shell(device, serialno, cmd="ls {}".format(dpath), tolog=tolog)
            if "dump.wav" in out.split():
                break
            timeout -= 1
            time.sleep(interval)

        Adb.execute(cmd=["pull", "{}/dump.wav".format(dpath), path], serialno=serialno, tolog=tolog)
        __class__.device_shell(device, serialno, cmd="rm -f {}/dump.wav".format(dpath), tolog=tolog)

    @staticmethod
    def voip_detector_register(device=None, serialno=None, dclass=None, params={}):
        __class__.tx_detector_register("voip", device, serialno, dclass, params)

    @staticmethod
    def voip_detector_unregister(device=None, serialno=None, chandle=None):
        __class__.tx_detector_unregister("voip", device, serialno, chandle)

    @staticmethod
    def voip_detector_clear(device=None, serialno=None):
        __class__.tx_detector_clear("voip", device, serialno, __class__.voip_info)

    @staticmethod
    def voip_detector_set_params(device=None, serialno=None, chandle=None, params={}):
        __class__.tx_detector_set_params("voip", device, serialno, chandle, params)

    @staticmethod
    def print_log(device=None, serialno=None, severity="i", tag="AudioWorkerAPIs", log=None):
        pass


import threading
import time
from pyaatlibs.timeutils import TicToc, TimeUtils
from pyaatlibs.audiofunction import ToneDetectorThread, ToneDetector
from pyaatlibs.aatapp import AATAppToneDetectorThread
from pyaatlibs.logger import Logger

class AudioWorkerToneDetectorThread(AATAppToneDetectorThread):
    def __init__(self, serialno, target_freq, callback,
        detector_reg_func, detector_unreg_func, detector_setparams_func, info_func, parse_detector_func):
        super(AudioWorkerToneDetectorThread, self).__init__(serialno=serialno, target_freq=target_freq, callback=callback)
        self.serialno = serialno
        self.chandle = None
        self.detector_reg_func = detector_reg_func
        self.detector_unreg_func = detector_unreg_func
        self.detector_setparams_func = detector_setparams_func
        self.info_func = info_func
        self.parse_detector_func = parse_detector_func
        self.detector_reg_func(serialno=serialno,
            dclass="ToneDetector", params={"target-freq": [target_freq]})

    def get_tag(self):
        return "AudioWorkerToneDetectorThread"

    def get_info(self):
        # Record
        # [
        #   {
        #     "params": {
        #       "num-channels": 2,
        #       "sampling-freq": 16000,
        #       "pcm-bit-width": 16,
        #       "dump-buffer-ms": 0
        #     },
        #     "class": "com.google.audioworker.functions.audio.record.RecordStartFunction",
        #     "has-ack": false
        #   },
        #   {
        #     "com.google.audioworker.functions.audio.record.detectors.ToneDetector@af8d417": {
        #       "Targets": [
        #         {
        #           "target-freq": 440
        #         }
        #       ],
        #       "Handle": "com.google.audioworker.functions.audio.record.detectors.ToneDetector@af8d417",
        #       "Process Frame Size": 50,
        #       "unit": {
        #         "Process Frame Size": "ms",
        #         "Sampling Frequency": "Hz"
        #       },
        #       "Sampling Frequency": 16000
        #     }
        #   }
        # ]

        # VoIP
        # [
        #   {
        #     "non-offload": {
        #       "0": {
        #         "command-id": "Google-AudioWorker::WorkerFunctionView-1572251050140p-start",
        #         "params": {
        #           "num-channels": 1,
        #           "pcm-bit-width": 16,
        #           "amplitude": 0.6,
        #           "playback-id": 0,
        #           "target-freq": 220,
        #           "sampling-freq": 8000,
        #           "type": "non-offload",
        #           "low-latency-mode": false
        #         },
        #         "class": "com.google.audioworker.functions.audio.playback.PlaybackStartFunction",
        #         "has-ack": false
        #       }
        #     }
        #   },
        #   {
        #     "command-id": "Google-AudioWorker::WorkerFunctionView-1572251050140c-start",
        #     "params": {
        #       "num-channels": 1,
        #       "sampling-freq": 8000,
        #       "pcm-bit-width": 16,
        #       "dump-buffer-ms": 0
        #     },
        #     "class": "com.google.audioworker.functions.audio.record.RecordStartFunction",
        #     "has-ack": false
        #   },
        #   {
        #     "com.google.audioworker.functions.audio.record.detectors.ToneDetector@ca926e4": {
        #       "Targets": [
        #         {
        #           "target-freq": 110
        #         }
        #       ],
        #       "Handle": "com.google.audioworker.functions.audio.record.detectors.ToneDetector@ca926e4",
        #       "Process Frame Size": 50,
        #       "unit": {
        #         "Process Frame Size": "ms",
        #         "Sampling Frequency": "Hz"
        #       },
        #       "Sampling Frequency": 8000
        #     },
        #     "com.google.audioworker.functions.audio.record.detectors.ToneDetector@5ea1714": {
        #       "Targets": [
        #         {
        #           "target-freq": 440
        #         }
        #       ],
        #       "Handle": "com.google.audioworker.functions.audio.record.detectors.ToneDetector@5ea1714",
        #       "Process Frame Size": 50,
        #       "unit": {
        #         "Process Frame Size": "ms",
        #         "Sampling Frequency": "Hz"
        #       },
        #       "Sampling Frequency": 8000
        #     }
        #   }
        # ]
        info = self.info_func(serialno=self.serialno)
        if not info:
            Logger.log("{}::get_info".format(self.get_tag()), "no active record, null info returned")
            return

        detectors = self.parse_detector_func(info)
        chandle = None
        for key, value in detectors.items():
            for each in value["Targets"]:
                if super(AudioWorkerToneDetectorThread, self).target_detected(each["target-freq"]):
                    chandle = key
                    break
            if chandle:
                Logger.log("{}::get_info".format(self.get_tag()), "found detector handle: {} for target {} Hz".format(chandle, self.target_freq))

        if not chandle:
            Logger.log("{}::get_info".format(self.get_tag()), "no detector handle!")
            self.dump()
        else:
            self.chandle = chandle

    def enable_detect_dump(self, enable):
        self.get_info()
        if not self.chandle:
            return

        self.detector_setparams_func(
            serialno=self.serialno, chandle=self.chandle, params={"dump-history": str(enable).lower()})

    def set_target_frequency(self, target_freq):
        self.target_freq = target_freq
        self.detector_setparams_func(
            serialno=self.serialno, chandle=self.chandle,
            params={"target-freq": [target_freq], "clear-target": "false", "dump-history": "true"})
        self.shared_vars["msg"] = None

    def run(self):
        self.shared_vars = {
            "start_time": None,
            "last_event": None,
            "last_state": None,
            "msg": None,
            "tictoc": TicToc(),
            "state_keep_ms": 0
        }

        self.extra = {}
        self.extra["adb-read-prop-max-elapsed"] = -1
        self.extra["freq-cb-max-elapsed"] = -1
        self.extra["dump"] = []
        self.extra["dump-lock"] = threading.Lock()

        self.shared_vars["tictoc"].tic()

        def freq_cb(msg):
            line = msg.splitlines()[0].strip()
            strs = line.split()
            t = datetime.datetime.fromtimestamp(float(strs[0][:-1]) / 1000.)
            freq = float(strs[1])

            if not self.target_detected(freq):
                self.push_to_dump(
                    "the frequency {} Hz is not the target".format(freq))
                return

            active = (strs[2].lower() == "active")

            if not self.shared_vars["start_time"]:
                self.shared_vars["start_time"] = t

            if active != self.shared_vars["last_state"]:
                self.push_to_dump(
                    "the detection state has been changed from {} to {}".format(self.shared_vars["last_state"], active))
                self.shared_vars["last_state"] = active
                self.shared_vars["start_time"] = t
                self.shared_vars["tictoc"].toc()
                self.shared_vars["state_keep_ms"] = 0

            t = self.shared_vars["start_time"]
            t_str = TimeUtils.str_from_time(t)

            self.shared_vars["state_keep_ms"] += self.shared_vars["tictoc"].toc()
            if self.shared_vars["state_keep_ms"] > 200:
                event = ToneDetector.Event.TONE_DETECTED if active else ToneDetector.Event.TONE_MISSING
                if self.shared_vars["last_event"] != event:
                    self.shared_vars["last_event"] = event
                    Logger.log(self.get_tag(),
                        "send_cb({}, {}) on {} Hz".format(t_str, "TONE_DETECTED" if active else "TONE_MISSING", self.target_freq))
                    self.cb((t_str, event))

        self.enable_detect_dump(enable=True)

        freq_cb_tictoc = TicToc()
        adb_tictoc = TicToc()

        freq_cb_tictoc.tic()
        while not self.stoprequest.isSet():
            if not self.chandle:
                self.get_info()

            adb_tictoc.tic()
            msg_in_device, _ = Adb.execute(cmd=["shell", "cat /storage/emulated/0/Google-AudioWorker-data/{}.txt".format(self.chandle)],
                serialno=self.serialno, tolog=False)
            elapsed = adb_tictoc.toc()

            msg_in_device = map(lambda x: x.strip(), msg_in_device.splitlines())
            msg_in_device = [x for x in msg_in_device if self.target_detected(float(x.split()[1]))]
            self.shared_vars["msg"] = msg_in_device[-1] if len(msg_in_device) > 0 else self.shared_vars["msg"]

            if elapsed > self.extra["adb-read-prop-max-elapsed"]:
                self.extra["adb-read-prop-max-elapsed"] = elapsed

            if self.shared_vars["msg"]:
                try:
                    self.push_to_dump("{} (adb-shell elapsed: {} ms)".format(self.shared_vars["msg"], elapsed))
                    freq_cb(self.shared_vars["msg"])
                except Exception as e:
                    Logger.log(self.get_tag(), "crashed in freq_cb('{}')".format(self.shared_vars["msg"]))
                    Logger.log(self.get_tag(), str(e))

                elapsed = freq_cb_tictoc.toc()
                if elapsed > self.extra["freq-cb-max-elapsed"]:
                    self.extra["freq-cb-max-elapsed"] = elapsed

            time.sleep(0.04)

        self.enable_detect_dump(enable=False)
