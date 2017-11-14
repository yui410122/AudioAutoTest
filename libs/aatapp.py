class AATApp(object):
    INTENT_PREFIX = "am broadcast -a"
    HTC_INTENT_PREFIX = "audio.htc.com.intent."

    @staticmethod
    def trigger_ssr(device):
        device.shell("asound -crashdsp")

    @staticmethod
    def playback_nonoffload(device):
        cmd = " ".join([AATApp.INTENT_PREFIX, AATApp.HTC_INTENT_PREFIX + "playback.nonoffload", "--es", "file", "440Hz.wav"])
        device.shell(cmd)

    @staticmethod
    def playback_offload(device):
        cmd = " ".join([AATApp.INTENT_PREFIX, AATApp.HTC_INTENT_PREFIX + "playback.offload", "--es", "file", "440Hz.mp3"])
        device.shell(cmd)

    @staticmethod
    def playback_stop(device):
        cmd = " ".join([AATApp.INTENT_PREFIX, AATApp.HTC_INTENT_PREFIX + "playback.stop"])
        device.shell(cmd)

    @staticmethod
    def record_start(device):
        cmd = " ".join([AATApp.INTENT_PREFIX, AATApp.HTC_INTENT_PREFIX + "record.start", "--ei", "spt_xmax", "1000"])
        device.shell(cmd)

    @staticmethod
    def record_stop(device):
        cmd = " ".join([AATApp.INTENT_PREFIX, AATApp.HTC_INTENT_PREFIX + "record.stop"])
        device.shell(cmd)
