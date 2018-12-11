#!/usr/local/google/home/hwlee/pyenv/audiopy/bin/python

from librosa.core import load as audioload
from scipy.signal import spectrogram
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import sys

def print_sig(signal, fs, outpath, tfrom, tto, maxfreq, nfft):
    num_ch = signal.shape[0] if signal.ndim == 2 else 1
    num_sample = signal.transpose().shape[0]
    duration = float(num_sample*1./fs)
    t_axis = np.arange(0, duration, duration/(num_sample+1))
    t_axis = t_axis[:num_sample]

    signal = signal[0, int(tfrom*fs):int(tto*fs)] if signal.ndim == 2 else signal[int(tfrom*fs):int(tto*fs)]
    f_axis, t_axis, S = spectrogram(signal, fs=fs, nfft=nfft)
    S += 1e-20
    S = 20 * np.log10(S)
    t_axis += tfrom

    maxfreq_idx = np.ceil(maxfreq * 1. / (f_axis[1] - f_axis[0]))
    S = S[:int(maxfreq_idx), :]

    plt.imshow(S, vmax=np.max(S), vmin=np.max(S)-40, \
        cmap="gray", origin="lower", interpolation="nearest")

    # plt.gca().set_ylabel("frequency index ({} Hz/index)".format(f_axis[1] - f_axis[0]))
    plt.gca().set_ylabel("frequency (Hz)")
    recbufsize_ms = (t_axis[1] - t_axis[0])*1000
    plt.gca().set_xlabel("frame index ({} ms/frame)".format(recbufsize_ms))

    ticks = plt.gca().get_yticks() * (f_axis[1] - f_axis[0])
    ticks = np.array(np.round(ticks), dtype=int)
    plt.gca().set_yticklabels(ticks)

    divider = make_axes_locatable(plt.gca())
    cax = divider.append_axes("right", size="2%", pad=0.05)
    plt.colorbar(cax=cax)

    xlim = plt.gca().get_xlim()
    plt.gcf().set_size_inches([(xlim[1]-xlim[0])*100, 3])
    
    # if num_ch > 1:
    #     for i, ch_sig in enumerate(signal):
    #         plt.subplot(num_ch, 1, i+1)
    #         plt.plot(t_axis, ch_sig)
    #         plt.gca().set_xlabel("time (s)")
    #         if tfrom != None and tto != None:
    #             plt.xlim([tfrom, tto])
    #         xlim = plt.gca().get_xlim()
    #         plt.gcf().set_size_inches([(xlim[1]-xlim[0])*horiz_extent_ratio/num_ch, 3])
    # else:
    #     plt.plot(t_axis, signal)
    #     plt.gca().set_xlabel("time (s)")
    #     if tfrom != None and tto != None:
    #         plt.xlim([tfrom, tto])
    #     xlim = plt.gca().get_xlim()
    #     plt.gcf().set_size_inches([(xlim[1]-xlim[0])*horiz_extent_ratio, 3])

    try:
        plt.savefig(outpath, bbox_inches="tight", pad_inches=0, dpi=300)
    except Exception as e:
        plt.savefig(outpath, bbox_inches="tight", pad_inches=0)

    plt.gcf().clear()

def main(argv):
    if str(argv[0]) == "help" or len(argv) < 6:
        print("python visaudio.py FILEPATH OUTPATH FROM_T TO_T MAX_FREQ NFFT")
        return

    filepath = str(argv[0])
    outpath = str(argv[1])
    tfrom = float(argv[2])
    tto = float(argv[3])
    maxfreq = float(argv[4])
    nfft = int(argv[5])

    sig, fs = audioload(filepath, sr=None, mono=False)
    print_sig(signal=sig, fs=fs, outpath=outpath, tfrom=tfrom, tto=tto, maxfreq=maxfreq, nfft=nfft)

if __name__ == "__main__":
    main(sys.argv[1:])
