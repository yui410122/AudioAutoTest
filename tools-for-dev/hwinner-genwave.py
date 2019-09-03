#!/usr/local/google/home/hwlee/pyenv/audiopy/bin/python

import sys
import struct
from scipy.io.wavfile import write as wavwrite
import numpy as np

def gen(path, endian="little"):
	endian_tag = "<" if endian == "little" else ">"
	print("parse the file \"{}\"".format(path))
	tags = path.split("_")
	tags = map(lambda s: s.replace(".pcm", ""), tags)
	fs_tag = filter(lambda s: s.startswith("sr"), tags)
	if len(fs_tag) > 0:
		fs = int(fs_tag[0][2:])
	else:
		print("filename \"{}\" does not match the format.".format(path))
		return

	ch_tag = filter(lambda s: s.startswith("ch"), tags)
	if len(ch_tag) > 0:
		num_ch = int(ch_tag[0][2:])
	else:
		print("filename \"{}\" does not match the format.".format(path))
		return

	format_tag = filter(lambda s: s.startswith("format"), tags)
	if len(format_tag) > 0:
		proc_format = int(format_tag[0][6:])
	else:
		print("filename \"{}\" does not match the format.".format(path))
		return

	if not proc_format in [1, 5, 6]:
		print("the format must be pcm16/pcm24/pcmfloat.")
		return

	with open(path, "rb") as f:
		raw_data = f.read()

	if proc_format == 1:
		signal = np.array(struct.unpack("{}{}h".format(endian_tag, len(raw_data)/2), raw_data), dtype=np.int16)
	elif proc_format == 5:
		signal = np.array(struct.unpack("{}{}f".format(endian_tag, len(raw_data)/4), raw_data), dtype=np.float32)
	elif proc_format == 6:
		data_len = len(raw_data)/3
		data = ""
		for x in range(data_len):
			data += raw_data[x*3+1:x*3+3]
		signal = np.array(struct.unpack("{}{}h".format(endian_tag, len(data)/2), data), dtype=np.int16)


	if num_ch > 1:
		signal = np.reshape(signal, (len(signal)/num_ch, num_ch))

	output_path = "{}.wav".format(path)
	wavwrite(filename=output_path, rate=fs, data=signal)
	print("generate the file \"{}\"".format(output_path))

def main(argv):
	if len(argv) == 0:
		return

	if argv[0] == "little" or argv[0] == "big":
		endian = argv[0]
		del argv[0]
	else:
		endian = "little"

	for path in argv:
		gen(path, endian)
	
if __name__ == "__main__":
	main(sys.argv[1:])
