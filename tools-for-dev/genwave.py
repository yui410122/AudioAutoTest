from librosa.output import write_wav as wavwrite
import numpy as np
import sys


def main(argv):
    freq = float(argv[0]) if len(argv) > 0 else 440
    duration = float(argv[1]) if len(argv) > 1 else 30
    fs = int(argv[2]) if len(argv) > 2 else 44100
    nch = int(argv[3]) if len(argv) > 3 else 2
    outpath = str(argv[4]) if len(argv) > 4 else "out.wav"

    sig = np.zeros([int(fs*duration), nch])
    sinewave = 0.99 * np.sin(np.arange(sig.shape[0]) * freq*1.0/fs * 2*np.pi)

    for ich in range(sig.shape[1]):
        sig[:, ich] = sinewave

    wavwrite(outpath, sig, fs)


if __name__ == "__main__":
    main(sys.argv[1:])
