import threading
import queue
import sounddevice as sd
import numpy as np
from scipy.fftpack import fft

class AudioConfig(object):
    def __init__(self, fs, ch=1, dtype="float32", cb=None):
        self.fs = fs
        self.ch = ch
        self.dtype = dtype
        self.cb = cb

class AudioCommand(object):
    def __init__(self, config):
        self.config = config

class TonePlayCommand(AudioCommand):
    def __init__(self, config, out_freq):
        super(TonePlayCommand, self).__init__(config)
        self.out_freq = out_freq
        self.is_playing = True

    def stop(self):
        self.is_playing = False

    def reset(self):
        self.is_playing = True

class ToneDetectCommand(AudioCommand):
    def __init__(self, config, framemillis=100, nfft=-1):
        super(ToneDetectCommand, self).__init__(config)
        self.framemillis = framemillis
        self.nfft = nfft
        if self.nfft < 0:
            self.nfft = int(framemillis*self.config.fs/1000)
        self.is_detecting = True

    def stop(self):
        self.is_detecting = False

    def reset(self):
        self.is_detecting = True

class AudioCommandThread(threading.Thread):
    def __init__(self, cmd_q=None):
        super(AudioCommandThread, self).__init__()
        self.cmd_q = cmd_q if cmd_q else queue.Queue()
        self.stoprequest = threading.Event()

    def join(self, timeout=None):
        self.stoprequest.set()
        super(AudioCommandThread, self).join(timeout)

    def run(self):
        while not self.stoprequest.isSet():
            try:
                cmd = self.cmd_q.get(True, 0.1)
                if isinstance(cmd, AudioCommand):
                    self._process_command(cmd)
            except queue.Empty:
                continue

    def push(self, cmd):
        if isinstance(cmd, AudioCommand):
            self.cmd_q.put(cmd)
        else:
            raise ValueError("The command type is not AudioCommand.")

    def _process_command(self, cmd):
        if type(cmd) is TonePlayCommand:
            self._process_playback_command(cmd)
        elif type(cmd) is ToneDetectCommand:
            self._process_detect_command(cmd)

    def _process_playback_command(self, cmd):
        phase_offset = 0
        cfg = cmd.config

        def playback_cb(outdata, frames, time, status):
            nonlocal phase_offset, cmd, cfg
            signal = np.arange(outdata.shape[0])
            signal = signal * 2*np.pi/cfg.fs + phase_offset
            phase_offset += outdata.shape[0] * 2*np.pi/cfg.fs
            signal = np.sin(signal * cmd.out_freq)

            for cidx in range(outdata.shape[1]):
                outdata[:, cidx] = signal

        with sd.OutputStream(channels=cfg.ch, callback=playback_cb, samplerate=cfg.fs, dtype="float32"):
            while cmd.is_playing:
                sd.sleep(500)

    def _process_detect_command(self, cmd):
        cfg = cmd.config
        buff = np.array([])
        framesize = int(cfg.fs*cmd.framemillis/1000)

        def record_cb(indata, frames, time, status):
            nonlocal cmd, cfg, buff, framesize
            if buff.any():
                buff = np.vstack((buff, indata[:, :]))
            else:
                buff = np.array(indata[:, :])

            if buff.size >= framesize:
                spectrum = np.abs(fft(buff[:framesize, 0], cmd.nfft))
                spectrum = spectrum[:int(cmd.nfft/2)]
                max_idx = np.argmax(spectrum)
                unit_freq = cfg.fs / cmd.nfft
                if cfg.cb:
                    cfg.cb(detected_tone=max_idx*unit_freq, detected_amp_db=20*np.log10(spectrum[max_idx]))

                buff = buff[framesize:, :]

        with sd.InputStream(channels=cfg.ch, callback=record_cb, samplerate=cfg.fs, dtype="float32"):
            while cmd.is_detecting:
                sd.sleep(500)
