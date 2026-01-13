#!/usr/bin/env python3

from datetime import datetime, timedelta
from hashlib import sha256
import gzip
import json
import os
import subprocess

def process_raw_history():
    seen = set()

    # Some of the early raw data dumps aren't really raw data, ignore the problematic cases
    to_ignore = {
        "cd39953c5a2ba2123ace2655c92427a6a2966754",
        "39d0d309bae76cdc0fcc5df2d79571dd27dd2db2",
        "91d8246bcd6cdeb9e2bb8dab228e61302fd24358",
        "4cae717fba4ddfa9f32aad18f528b699b4708078",
        "3ee2a4dafa3d0f6d0e8865678e37d6d2159f409d",
        "9595c2f6c92d9d65e54a83b855d3a6926899455d",
        "ba6d04eda5bca0d85be22ba5f7034c1dc93e9066",
        "d33db441d2292071e213145be685dbe68fec18a1",
        "a2ff3ee0c30520775e2cb280470b382ab1b99fc9",
        "e513433caf81c4ead1d46307d40e49f85693ddf7",
        "3a74ce99af393b7a9ab2f60959ea380afd17836a",
        "c96dacfdc4f91856edc2f76387898e80e1fbf191",
    }

    epoch = datetime(1970, 1, 1)
    log = subprocess.check_output(["git", "log", "--format=format:%H %ct"]).decode("utf-8")
    for row in log.split("\n"):
        commit, at = row.split(' ')
        at = epoch + timedelta(seconds=int(at))
        if os.path.isfile(str(at.year) + ".tar.gz") or os.path.isfile(str(at.year) + "_01.tar.gz"):
            break
        data = subprocess.check_output(["git", "diff-tree", "--no-commit-id", "-r", commit]).decode("utf-8")
        for file in data.split("\n"):
            if len(file) > 0:
                info, file = file.split("\t")
                info = info.split(" ")
                if info[4] in {"A", "C", "M", "R"}:
                    if file.startswith("data/raw_") and (file.endswith(".json.gz") or file.endswith(".csv.gz") or file.endswith(".txt.gz")):
                        provider = file.split("/")[-1].split(".")[0][4:]
                        dn = os.path.join(str(at.year), "raw", provider)
                        if not os.path.isdir(dn):
                            os.makedirs(dn)
                        fn = os.path.join(dn, at.strftime("%Y-%m-%d") + "." + file.split("/")[-1].split(".")[1])
                        if info[3] not in to_ignore:
                            print(f"Raw {provider:<12}:{info[3]}, ", end="", flush=True)
                            if not os.path.isfile(fn):
                                data = subprocess.check_output(["git", "cat-file", "-p", info[3]])
                                data = gzip.decompress(data)
                                hash = sha256(data).hexdigest()
                                if hash not in seen:
                                    seen.add(hash)
                                    with open(fn, "wb") as f:
                                        f.write(data)
                                    print(f"wrote for {at.strftime('%Y-%m-%d')}, {len(data):8d} bytes of {file.split('/')[-1].split('.')[1]:<4}", flush=True)
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
            print(f"Working on {provider:<12}:{row[0]}", end="", flush=True)
            cmd = "git cat-file -p " + row[0]
            data = subprocess.check_output(cmd.split(' '))
            data = gzip.decompress(data)
            hash = sha256(data).hexdigest()
            if hash in seen:
                print(", dupe detected", flush=True)
            else:
                seen.add(hash)
                time = datetime(*[int(x) for x in json.loads(data)['date'][:19].replace(" ", "-").replace(":", "-").split("-")])
                if os.path.isfile(time.strftime("%Y") + ".tar.gz") or os.path.isfile(time.strftime("%Y") + "_01.tar.gz"):
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
        files = []
        for dirname, dirnames, filenames in os.walk(year):
            for fn in filenames:
                full_name = os.path.join(dirname, fn)
                files.append({
                    'fn': fn,
                    'full_name': full_name, 
                    'size': os.path.getsize(full_name),
                })

        # Sort by filename, in other words, sort by date
        files.sort(key=lambda x: x['fn'])
        batches = []

        # Try to find the compression ratio
        test_batch = {
            "size": 0,
            "files": [],
        }
        for file in files:
            test_batch["size"] += file['size']
            test_batch["files"].append(file)
            if test_batch["size"] >= (50 * 1024 * 1024):
                break
        with open("_temp_files", "wt") as f:
            for cur in test_batch['files']:
                f.write(cur['full_name'] + "\n")
        dest_fn = "test_batch.tar.gz"
        cmd = f"tar --owner=0 --group=0 -T _temp_files -czf {dest_fn}"
        print("$ " + cmd)
        subprocess.check_call(cmd, shell=True)
        os.unlink('_temp_files')
        # Give ourselves a 10% buffer for future files
        test_batch["actual_compressed"] = os.path.getsize(dest_fn)
        test_batch["compressed"] = int(os.path.getsize(dest_fn) * 1.1)
        os.unlink(dest_fn)
        compression_ratio = test_batch['size'] / test_batch['compressed']
        print(f"# Got an expected ratio of {compression_ratio:.2f}")

        for file in files:
            # Given the test file compressed, try to limit filesize to 95 MiB
            if len(batches) == 0 or batches[-1]['size'] >= (95 * 1024 * 1024) * compression_ratio:
                batches.append({'files': [], 'size': 0, 'id': ''})
            batches[-1]['files'].append(file)
            batches[-1]['size'] += file['size']

        if len(batches) > 1:
            for i, batch in enumerate(batches):
                batch['id'] = f"_{i+1:02d}"

        for batch in batches:
            with open("_temp_files", "wt") as f:
                for cur in batch['files']:
                    f.write(cur['full_name'] + "\n")
            dest_fn = f"{year}{batch['id']}.tar.gz"
            cmd = f"tar --owner=0 --group=0 -T _temp_files -czf {dest_fn}"
            print("$ " + cmd)
            subprocess.check_call(cmd, shell=True)
            os.unlink('_temp_files')
            actual_size = os.path.getsize(dest_fn)
            expected_size = int(batch['size'] / (test_batch['size'] / test_batch['actual_compressed']))
            print(f"# File size is {actual_size:,}, expected {expected_size:,}, that's {abs(expected_size - actual_size)/actual_size*100:.2f}% off")
            if os.path.getsize(dest_fn) >= 100 * 1024 * 1024:
                raise Exception(f"{dest_fn} is too big!")
        cmd = f"rm -rf {year}"
        print("$ " + cmd)
        subprocess.check_call(cmd, shell=True)

if __name__ == "__main__":
    main()
