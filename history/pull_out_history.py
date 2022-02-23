#!/usr/bin/env python3

import subprocess
from hashlib import sha256
import json
from datetime import datetime
import os
import gzip

def process_history(years, fn, provider):
    seen = set()

    cmd = "git rev-list --all --objects -- ../data/" + fn
    history = subprocess.check_output(cmd.split(' ')).decode("utf8")
    for row in history.split("\n"):
        row = row.strip().split(' ')
        if len(row) == 2 and row[1] == "data/" + fn:
            print("Working on " + provider + ":" + row[0], end="", flush=True)
            cmd = "git cat-file -p " + row[0]
            data = subprocess.check_output(cmd.split(' '))
            data = gzip.decompress(data)
            hash = sha256(data).hexdigest()
            if hash in seen:
                print(", dupe detected", flush=True)
            else:
                seen.add(hash)
                time = datetime(*[int(x) for x in json.loads(data)['date'][:19].replace(" ", "-").replace(":", "-").split("-")])
                if os.path.isfile(time.strftime("%Y") + ".tar.gz"):
                    print(", already archived " + time.strftime("%Y-%m-%d %H:%M:%S"), flush=True)
                    break
                else:
                    dn = time.strftime("%Y")
                    years.add(dn)
                    if not os.path.isdir(dn):
                        os.mkdir(dn)
                    dn = os.path.join(dn, provider)
                    if not os.path.isdir(dn):
                        os.mkdir(dn)
                    with open(os.path.join(dn, time.strftime("%Y-%m-%d-%H-%M-%S.json")), "wb") as f:
                        f.write(data)
                    print(", created file for " + time.strftime("%Y-%m-%d %H:%M:%S"), flush=True)

def main():
    years = set()
    for cur in sorted(os.listdir(os.path.join("..", "data"))):
        if cur.startswith("data_") and cur.endswith(".json.gz"):
            provider = cur[5:-8]
            process_history(years, cur, provider)
    
    for year in sorted(years)[:-1]:
        print(f"Compressing {year}")
        cmd = f"find {year} -type f | sort | tar --owner=0 --group=0 -T - -cvzf {year}.tar.gz ; rm -rf {year}"
        print("$ " + cmd)
        subprocess.check_call(cmd, shell=True)


if __name__ == "__main__":
    main()
