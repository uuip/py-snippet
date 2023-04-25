# coding=utf8
import hashlib
import json
import re
import sys
import threading
import time
import traceback
from datetime import datetime

import psutil
import tqdm
from sqlitedict import SqliteDict

p = psutil.Process()
stop = False
active = SqliteDict(flag="n")


def mem_monit():
    m = p.memory_info()
    rss, vms = m.rss, m.vms
    while not stop:
        try:
            if p.is_running():
                m = p.memory_full_info()
                if m.rss > rss:
                    rss, vms = m.rss, m.vms
                time.sleep(1)
        except:
            traceback.print_exc()
    print(list(map(lambda x: x / 1024 / 1024, [rss, vms])))


def main():
    path = "data/train_sys-20201210.txt"
    f = open(path, encoding="utf-8")
    for line in f:
        pbar.update(1)
        if not line:
            break
        line = re.sub(r"\\", r"\\\\", line)
        line = line.strip()
        try:
            rs = json.loads(line)
            h = hashlib.sha1(line.encode("utf-8")).hexdigest()
            if h in active:
                _tmp = active[h]
                continue
            else:
                active[h] = rs
        except:
            breakpoint()
            traceback.print_exc()
            continue
    f.close()


if __name__ == "__main__":
    t1 = time.time()
    a = threading.Thread(target=mem_monit)
    a.start()
    sys.stderr.write("start time " + str(datetime.now()) + "\n")
    pbar = tqdm.tqdm(unit="line", total=3126256)
    main()
    pbar.close()
    stop = True
    t2 = time.time()
    print(len(active))
    sys.stderr.write("end time " + str(datetime.now()) + "\n")
    sys.stderr.write("total process time " + str((t2 - t1) / 60) + " minutes \n")
