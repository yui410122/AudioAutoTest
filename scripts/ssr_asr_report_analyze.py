import subprocess

import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")

from libs import ROOT_DIR
from libs.trials import Trial, TrialHelper

def run(dir_path):
    json_files = subprocess.Popen("ls {} | grep json".format(dir_path), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].split()
    trials = []
    for jf in json_files:
        trials += TrialHelper.load("{}/{}".format(dir_path, jf))
    for t in trials:
        t.pass_check = lambda t: t.ds["extra"]["elapsed"] > 0 or "msg" in t.ds["extra"]
        if t.ds["status"] == "invalid" and "msg" in t.ds["extra"].keys() and "bugreport" in t.ds["extra"].keys():
            bugreport_file = subprocess.Popen(
                "find {}/ssr_report-bugreport/ -name {}".format(ROOT_DIR, t.ds["extra"]["bugreport"]),
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].strip()
            if len(bugreport_file) > 0:
                os.system("rm -f {}".format(bugreport_file))

    tt = len(trials)
    trials = filter(lambda t: t.ds["status"] == "valid", trials)
    print("valid trials: {}/{}".format(len(trials), tt))
    trials = filter(lambda t: t.ds["status"] == "valid", trials)
    trials = TrialHelper.categorize_in(trials, cat_func=lambda t: t.ds["task"])

    for taskname, results in trials.items():
        print("pass in task[{}]: {}/{}".format(taskname, len([t for t in results if t.is_pass()]), len(results)))

    for taskname, results in trials.items():
        print("failed cases in task[{}]".format(taskname))
        print(TrialHelper.to_json([t for t in results if not t.is_pass()]))

if __name__ == "__main__":
    run(sys.argv[1])
