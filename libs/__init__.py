import os
import platform

__author__ = "Hao-Wei Lee"
if platform.system() == "Windows":
    SEP = "\\"
    STDNUL = "NUL"
else:
    SEP = "/"
    STDNUL = "/dev/null"

ROOT_DIR = SEP.join(os.path.dirname(os.path.realpath(__file__)).split(SEP)[:-1])
