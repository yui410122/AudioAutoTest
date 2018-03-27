import numpy as np

def find_peaks(signal):
	peaks = []
	max_idx = np.argmax(signal)
	peaks.append((max_idx, signal[max_idx]))
	return peaks
