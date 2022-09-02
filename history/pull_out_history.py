#!/usr/bin/env python3

from datetime import datetime, timedelta
from hashlib import sha256
import gzip
import json
import os
import subprocess

def process_raw_history():
    seen = set()

    epoch = datetime(1970, 1, 1)
    log = subprocess.check_output(["git", "log", "--format=format:%H %ct"]).decode("utf-8")
    for row in log.split("\n"):
        commit, at = row.split(' ')
        at = epoch + timedelta(seconds=int(at))
        if os.path.isfile(str(at.year) + ".tar.gz"):
            break
        data = subprocess.check_output(["git", "diff-tree", "--no-commit-id", "-r", commit]).decode("utf-8")
        for file in data.split("\n"):
            if len(file) > 0:
                info, file = file.split("\t")
                info = info.split(" ")
                if info[4] in {"A", "C", "M", "R"}:
                    if file.startswith("data/raw_") and file.endswith(".json.gz"):
                        provider = file[9:-8]
                        dn = os.path.join(str(at.year), "raw", provider)
                        if not os.path.isdir(dn):
                            os.makedirs(dn)
                        fn = os.path.join(dn, at.strftime("%Y-%m-%d") + ".json")
                        print(f"Raw {provider}:{info[3]}, ", end="", flush=True)
                        if not os.path.isfile(fn):
                            data = subprocess.check_output(["git", "cat-file", "-p", info[3]])
                            data = gzip.decompress(data)
                            hash = sha256(data).hexdigest()
                            if hash not in seen:
                                seen.add(hash)
                                with open(fn, "wb") as f:
                                    f.write(data)
                                print(f"wrote data for {at.strftime('%Y-%m-%d')}", flush=True)
                            else:
                                print("data seen.", flush=True)
                        else:
                            print("file exists.", flush=True)

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

    process_raw_history()

    for year in sorted(years)[:-1]:
        print(f"Compressing {year}")
        cmd = f"find {year} -type f | sort | tar --owner=0 --group=0 -T - -cvzf {year}.tar.gz ; rm -rf {year}"
        print("$ " + cmd)
        subprocess.check_call(cmd, shell=True)

if __name__ == "__main__":
    main()
