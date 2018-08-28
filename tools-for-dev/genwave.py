from scipy.io.wavfile import write as wavwrite
import numpy as np
import sys


def main(argv):
    if str(argv[0]) == "help":
        print("python genwave.py FREQ AMP DURATION FS NUMCH OUTPATH")
        return

    freq = float(argv[0]) if len(argv) > 0 else 440
    amp = float(argv[1]) if len(argv) > 1 else 0.7
    duration = float(argv[2]) if len(argv) > 2 else 30
    fs = int(argv[3]) if len(argv) > 3 else 44100
    nch = int(argv[4]) if len(argv) > 4 else 2
    outpath = str(argv[5]) if len(argv) > 5 else "out.wav"

    sig = np.zeros([int(fs*duration), nch], dtype=np.int16)
    sinewave = amp * np.sin(np.arange(sig.shape[0]) * freq*1.0/fs * 2*np.pi)

    for ich in range(sig.shape[1]):
        sig[:, ich] = np.round(sinewave * (2**15-1))

    wavwrite(outpath, fs, sig)


if __name__ == "__main__":
    main(sys.argv[1:])
