import sys
import subprocess

def run(dir_name, *key_words):
    if dir_name.endswith("/"):
        dir_name = dir_name[:-1]
    key_words = list(key_words)

    out, _ = subprocess.Popen("ls {}".format(dir_name), shell=True, stdout=subprocess.PIPE).communicate()
    log_files = [x for x in out.split() if x.endswith(".log")]
    
    def check_patterns(s):
        return reduce(lambda x, y: x | y, map(lambda x: x in s, key_words))

    cnt = 0
    for log_file in log_files:
        path = "{}/{}".format(dir_name, log_file)
        with open(path, "r") as f:
            patterns = [x for x in f.readlines() if check_patterns(x)]
            if len(patterns) == 0:
                continue
            patterns = [x for x in patterns[-1].split() if x.startswith("#")]
            for p in patterns:
                try:
                    cnt += int(p[1:])
                    break
                except:
                    continue

    print("check patters: {}".format(key_words))
    print("trial conut: {}".format(cnt))


if __name__ == "__main__":
    run(*sys.argv[1:])
