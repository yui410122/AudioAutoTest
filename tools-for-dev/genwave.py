from scipy.io.wavfile import write as wavwrite
import numpy as np
import sys


def main(argv):
    if str(argv[0]) == "help":
        print("python genwave.py FREQ AMP DURATION FS NUMCH BITS f/i OUTPATH")
        return

    freq = float(argv[0]) if len(argv) > 0 else 440
    amp = float(argv[1]) if len(argv) > 1 else 0.7
    duration = float(argv[2]) if len(argv) > 2 else 30
    fs = int(argv[3]) if len(argv) > 3 else 44100
    nch = int(argv[4]) if len(argv) > 4 else 2
    bits = int(argv[5]) if len(argv) > 5 else 16
    f_or_i = argv[6] if len(argv) > 6 else "i"
    outpath = str(argv[7]) if len(argv) > 7 else "out.wav"

    if bits == 16:
        sig = np.zeros([int(fs*duration), nch], dtype=np.int16)
    elif bits == 32:
        if f_or_i == "i":
            sig = np.zeros([int(fs*duration), nch], dtype=np.int32)
        else:
            sig = np.zeros([int(fs*duration), nch], dtype=np.float32)
    else:
        print("invalid bit-width: 16/32 required")
        return

    sinewave = amp * np.sin(np.arange(sig.shape[0]) * freq*1.0/fs * 2*np.pi)

    for ich in range(sig.shape[1]):
        if f_or_i == "i":
            sig[:, ich] = np.round(sinewave * (2**(bits-1)-1))
        else:
            sig[:, ich] = sinewave[:]

    wavwrite(outpath, fs, sig)


if __name__ == "__main__":
    main(sys.argv[1:])
