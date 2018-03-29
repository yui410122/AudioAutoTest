from scipy.io.wavfile import write as wavwrite
from librosa.core import load as audioload
import numpy as np
import sys


def main(argv):
    if str(argv[0]) == "help" or len(argv) < 1:
        print("python gendefect.py glitch INPATH OUTPATH FRAMESIZE(MS) DURATION(MS)")
        print("python gendefect.py nosound INPATH OUTPATH OFFSET(MS) DURATION(MS)")
        print("python gendefect.py intermitted INPATH OUTPATH FRAMESIZE(MS) DURATION(MS)")
        return

    defect_name = str(argv[0]).lower()
    inpath = str(argv[1])
    outpath = str(argv[2]) if len(argv) > 2 else "out.wav"
    params = []

    sig, fs = audioload(inpath, sr=None, mono=False)
    sig = np.array(sig * (2**15-1))
    sig = sig.transpose()

    if defect_name == "glitch" or defect_name == "intermitted":
        params.append(float(argv[3]) if len(argv) > 3 else 1)
        params.append(float(argv[4]) if len(argv) > 4 else 20)
        framesize = int(round(params[0]/1000.*fs))
        duration = int(round(params[1]/1000.*fs))

        for offset in range(0, sig.shape[0]-framesize, duration):
            if defect_name == "intermitted":
                ramp_mask = np.arange(0., 1., 1./(framesize/2.))
                start_idx = max([offset-framesize/2, 0])
                end_idx = min([offset+framesize+framesize/2, sig.shape[0]])
            if sig.ndim > 1:
                sig[offset:offset+framesize, :] = 0
                if defect_name == "intermitted":
                    for ch in range(sig.shape[1]):
                        sig[start_idx:offset+1, ch] *= ramp_mask[::-1][-(offset-start_idx+1):]
                        sig[offset+framesize:end_idx, ch] *= ramp_mask[:(end_idx-offset-framesize)]
            else:
                sig[offset:offset+framesize] = 0
                if defect_name == "intermitted":
                    sig[start_idx:offset+1] *= ramp_mask[::-1][-(offset-start_idx+1):]
                    sig[offset+framesize:end_idx] *= ramp_mask[:(end_idx-offset-framesize)]

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

    sig = np.array(np.round(sig), dtype=np.int16)
    wavwrite(outpath, fs, sig)


if __name__ == "__main__":
    main(sys.argv[1:])
