import os
import subprocess
import json
import datetime
from libs.adbutils import Adb

class AudioWorkerApp(object):
    INTENT_PREFIX = "am broadcast -a"
    AUDIOWORKER_INTENT_PREFIX = "com.google.audioworker.intent."

    PACKAGE = "com.google.audioworker"
    MAINACTIVITY = ".activities.MainActivity"

    DATA_FOLDER = "/storage/emulated/0/Google-AudioWorker-data"

    @staticmethod
    def device_shell(device=None, serialno=None, cmd=None):
        if not cmd:
            return

        if device:
            return device.shell(cmd)
        else:
            return Adb.execute(["shell", cmd], serialno=serialno)

    @staticmethod
    def relaunch_app(device=None, serialno=None):
        AudioWorkerApp.device_shell(device=device, serialno=serialno, cmd="am force-stop {}".format(AudioWorkerApp.PACKAGE))
        AudioWorkerApp.launch_app(device)

    @staticmethod
    def launch_app(device=None, serialno=None):
        component = AudioWorkerApp.PACKAGE + "/" + AudioWorkerApp.MAINACTIVITY
        AudioWorkerApp.device_shell(device=device, serialno=serialno, cmd="am start -n {}".format(component))

    @staticmethod
    def send_intent(device, serialno, name, configs={}):
        cmd_arr = [AudioWorkerApp.INTENT_PREFIX, name]
        for key, value in configs.items():
            if type(value) is float:
                cmd_arr += ["--ef", key]
            elif type(value) is int:
                cmd_arr += ["--ei", key]
            else:
                cmd_arr += ["--es", key]
            cmd_arr.append(str(value))

        AudioWorkerApp.device_shell(device=device, serialno=serialno, cmd=" ".join(cmd_arr))

    @staticmethod
    def playback_nonoffload(device=None, serialno=None, freq=440., playback_id=0, fs=16000, nch=2, amp=0.6, bit_depth=16):
        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "playback.start"
        configs = {
            "type": "non-offload",
            "target-freq": freq,
            "playback-id": playback_id,
            "sampling-freq": fs,
            "num-channels": nch,
            "amplitude": amp,
            "pcm-bit-width": bit_depth
        }
        AudioWorkerApp.send_intent(device, serialno, name, configs)

    @staticmethod
    def playback_offload(device=None, serialno=None, freq=440., playback_id=0, fs=16000, nch=2, amp=0.6, bit_depth=16):
        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "playback.start"
        configs = {
            "type": "offload",
            "target-freq": freq,
            "playback-id": playback_id,
            "sampling-freq": fs,
            "num-channels": nch,
            "amplitude": amp,
            "pcm-bit-width": bit_depth
        }
        AudioWorkerApp.send_intent(device, serialno, name, configs)

    @staticmethod
    def playback_info(device=None, serialno=None):
        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "playback.info"
        AudioWorkerApp.send_intent(device, serialno, name, {"filename": "info.txt"})
        out, _ = AudioWorkerApp.device_shell(None, serialno, cmd="cat {}/PlaybackController/info.txt".format(AudioWorkerApp.DATA_FOLDER))
        out = out.splitlines()
        if len(out) <= 1:
            return None

        try:
            info_timestamp = float(out[0].strip().split("::")[1]) / 1000.
            info_t = datetime.datetime.fromtimestamp(info_timestamp)
            if (datetime.datetime.now() - info_t).total_seconds() > 1:
                return None
        except:
            return None

        return json.loads("".join(out[1:]))

    @staticmethod
    def playback_stop(device=None, serialno=None):
        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "playback.stop"
        info = AudioWorkerApp.playback_info(device, serialno)
        for pbtype in info.keys():
            for pbid in info[pbtype].keys():
                configs = {
                    "type": pbtype,
                    "playback-id": int(pbid)
                }
                AudioWorkerApp.send_intent(device, serialno, name, configs)

    @staticmethod
    def record_info(device=None, serialno=None):
        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "record.info"
        AudioWorkerApp.send_intent(device, serialno, name, {"filename": "info.txt"})
        out, _ = AudioWorkerApp.device_shell(None, serialno, cmd="cat {}/RecordController/info.txt".format(AudioWorkerApp.DATA_FOLDER))
        out = out.splitlines()
        if len(out) <= 1:
            return None

        try:
            info_timestamp = float(out[0].strip().split("::")[1]) / 1000.
            info_t = datetime.datetime.fromtimestamp(info_timestamp)
            if (datetime.datetime.now() - info_t).total_seconds() > 1:
                return None
        except:
            return None

        info = json.loads("".join(out[1:]))
        if len(info) > 1:
            for key, value in info[1].items():
                info[1][key] = json.loads(value)

        return info

    @staticmethod
    def record_start(device=None, serialno=None, fs=16000, nch=2, bit_depth=16, dump_buffer_ms=0):
        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "record.start"
        configs = {
            "sampling-freq": fs,
            "num-channels": nch,
            "pcm-bit-width": bit_depth,
            "dump-buffer-ms": dump_buffer_ms
        }
        AudioWorkerApp.send_intent(device, serialno, name, configs)

    @staticmethod
    def record_stop(device=None, serialno=None):
        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "record.stop"
        AudioWorkerApp.send_intent(device, serialno, name)

    @staticmethod
    def record_dump(device=None, serialno=None, path=None):
        if not path:
            return

        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "record.dump"
        AudioWorkerApp.send_intent(device, serialno, {"filename": path})

    @staticmethod
    def record_detector_register(device=None, serialno=None, dclass=None, params={}):
        if not dclass:
            return
        try:
            params = json.dumps(json.dumps(params))
        except:
            log("params cannot be converted to json string")
            return

        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "record.detect.register"
        configs = {
            "class": dclass,
            "params": params
        }
        AudioWorkerApp.send_intent(device, serialno, name, configs)

    @staticmethod
    def record_detector_set_params(device=None, serialno=None, chandle=None, params={}):
        if not chandle:
            return
        try:
            params = json.dumps(json.dumps(params))
        except:
            log("params cannot be converted to json string")
            return

        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "record.detect.setparams"
        configs = {
            "class-handle": chandle,
            "params": params
        }
        AudioWorkerApp.send_intent(device, serialno, name, configs)

    @staticmethod
    def voip_info(device=None, serialno=None):
        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "voip.info"
        AudioWorkerApp.send_intent(device, serialno, name, {"filename": "info.txt"})
        out, _ = AudioWorkerApp.device_shell(None, serialno, cmd="cat {}/VoIPController/info.txt".format(AudioWorkerApp.DATA_FOLDER))
        out = out.splitlines()
        if len(out) <= 1:
            return None

        try:
            info_timestamp = float(out[0].strip().split("::")[1]) / 1000.
            info_t = datetime.datetime.fromtimestamp(info_timestamp)
            if (datetime.datetime.now() - info_t).total_seconds() > 1:
                return None
        except:
            return None

        return json.loads("".join(out[1:]))

    @staticmethod
    def voip_start(device=None, serialno=None, rxfreq=440., rxamp=0.6,
        rxfs=8000, txfs=8000, rxnch=1, txnch=1, rxbit_depth=16, txbit_depth=16, dump_buffer_ms=0):
        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "voip.start"
        configs = {
            "rx-target-freq": rxfreq,
            "rx-amplitude": rxamp,
            "rx-sampling-freq": rxfs,
            "rx-num-channels": rxnch,
            "rx-pcm-bit-width": rxbit_depth,
            "tx-sampling-freq": txfs,
            "tx-num-channels": txnch,
            "tx-pcm-bit-width": txbit_depth,
            "tx-dump-buffer-ms": dump_buffer_ms
        }
        AudioWorkerApp.send_intent(device, serialno, name, configs)

    @staticmethod
    def voip_stop(device=None, serialno=None):
        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "voip.stop"
        AudioWorkerApp.send_intent(device, serialno, name)

    @staticmethod
    def voip_use_speaker(device=None, serialno=None, use=True):
        pass

    @staticmethod
    def voip_use_receiver(device=None, serialno=None):
        AudioWorkerApp.voip_use_speaker(device, serialno, use=False)

    @staticmethod
    def voip_change_configs(device=None, serialno=None, rxfreq=-1, rxamp=-1):
        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "voip.config"
        configs = {
            "rx-target-freq": rxfreq,
            "rx-amplitude": rxamp
        }
        AudioWorkerApp.send_intent(device, serialno, name, configs)

    @staticmethod
    def voip_mute_output(device=None, serialno=None):
        AudioWorkerApp.voip_change_configs(device, serialno, rxamp=0)

    @staticmethod
    def voip_tx_dump(device=None, serialno=None, path=None):
        if not path:
            return

        name = AudioWorkerApp.AUDIOWORKER_INTENT_PREFIX + "voip.tx.dump"
        AudioWorkerApp.send_intent(device, serialno, {"filename": path})

    @staticmethod
    def print_log(device=None, serialno=None, severity="i", tag="AudioWorkerAPIs", log=None):
        pass
