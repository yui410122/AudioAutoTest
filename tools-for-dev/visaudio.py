from librosa.core import load as audioload
import numpy as np
import matplotlib.pyplot as plt
import sys

def print_sig(signal, fs, outpath, horiz_extent_ratio, tfrom, tto):
    num_ch = signal.shape[0] if signal.ndim == 2 else 1
    num_sample = signal.transpose().shape[0]
    duration = float(num_sample*1./fs)
    t_axis = np.arange(0, duration, duration/(num_sample+1))
    t_axis = t_axis[:num_sample]
    
    if num_ch > 1:
        for i, ch_sig in enumerate(signal):
            plt.subplot(num_ch, 1, i+1)
            plt.plot(t_axis, ch_sig)
            plt.gca().set_xlabel("time (s)")
            if tfrom != None and tto != None:
                plt.xlim([tfrom, tto])
            xlim = plt.gca().get_xlim()
            plt.gcf().set_size_inches([(xlim[1]-xlim[0])*horiz_extent_ratio/num_ch, 3])
    else:
        plt.plot(t_axis, signal)
        plt.gca().set_xlabel("time (s)")
        if tfrom != None and tto != None:
            plt.xlim([tfrom, tto])
        xlim = plt.gca().get_xlim()
        plt.gcf().set_size_inches([(xlim[1]-xlim[0])*horiz_extent_ratio, 3])

    try:
        plt.savefig(outpath, bbox_inches="tight", pad_inches=0, dpi=300)
    except Exception as e:
        plt.savefig(outpath, bbox_inches="tight", pad_inches=0)

    plt.gcf().clear()

def main(argv):
    if str(argv[0]) == "help" or len(argv) < 5:
        print("python visaudio.py FILEPATH OUTPATH EXT_RATIO FROM_T TO_T")
        return

    filepath = str(argv[0])
    outpath = str(argv[1])
    horiz_extent_ratio = float(argv[2])
    tfrom = float(argv[3])
    tto = float(argv[4])

    sig, fs = audioload(filepath, sr=None, mono=False)
    print_sig(signal=sig, fs=fs, outpath=outpath, horiz_extent_ratio=horiz_extent_ratio, tfrom=tfrom, tto=tto)

if __name__ == "__main__":
    main(sys.argv[1:])
