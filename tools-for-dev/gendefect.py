from scipy.io.wavfile import write as wavwrite
from librosa.core import load as audioload
import numpy as np
import sys


def main(argv):
    if str(argv[0]) == "help" or len(argv) < 1:
        print("python gendefect.py glitch INPATH OUTPATH FRAMESIZE(MS) DURATION(MS)")
        print("python gendefect.py nosound INPATH OUTPATH OFFSET(MS) DURATION(MS)")
        return

    defect_name = str(argv[0]).lower()
    inpath = str(argv[1])
    outpath = str(argv[2]) if len(argv) > 2 else "out.wav"
    params = []

    sig, fs = audioload(inpath, sr=None, mono=False)
    sig = np.array(np.round(sig * (2**15-1)), dtype=np.int16)
    sig = sig.transpose()

    if defect_name == "glitch":
        params.append(float(argv[3]) if len(argv) > 3 else 1)
        params.append(float(argv[4]) if len(argv) > 4 else 20)
        framesize = int(round(params[0]/1000.*fs))
        duration = int(round(params[1]/1000.*fs))

        for offset in range(0, sig.shape[0]-framesize, duration):
            if sig.ndim > 1: sig[offset:offset+framesize, :] = 0
            else: sig[offset:offset+framesize] = 0

    elif defect_name == "nosound":
        params.append(float(argv[3]) if len(argv) > 3 else 0)
        params.append(float(argv[4]) if len(argv) > 4 else 5000)
        offset = int(round(params[0]/1000.*fs))
        duration = int(round(params[1]/1000.*fs))

        if sig.ndim > 1: sig[offset:offset+duration, :] = 0
        else: sig[offset:offset+duration] = 0

    else:
        print("unknown defect name.")
        return

    wavwrite(outpath, fs, sig)


if __name__ == "__main__":
    main(sys.argv[1:])
