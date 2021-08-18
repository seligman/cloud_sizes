#!/usr/bin/env python3

import os
from importlib.util import spec_from_file_location, module_from_spec
import json
from datetime import datetime
import gzip
import io

def main():
    # A summary of this run
    run_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    all_info = {
        '_': run_at,
    }

    # What the different services are properly called
    pretties = {}

    # Loop for each file in the helpers dir, and let it doe the work for its provider
    for cur in os.listdir("helpers"):
        if cur.endswith(".py"):
            print(f"Working on {cur}, ", end="", flush=True)
            spec = spec_from_file_location("ips", os.path.join("helpers", cur))
            ips = module_from_spec(spec)
            spec.loader.exec_module(ips)
            name, pretty, v4, v6 = ips.get_and_parse()
            pretties[name] = pretty
            # Add a summary to our summary dictionary
            all_info[name] = [v4.size, v6.size]

            # Read in the old data
            old_data = "--"
            dest_name = os.path.join("data", f"data_{name}.json.gz")
            if os.path.isfile(dest_name):
                with gzip.open(dest_name) as f:
                    old_data = json.load(f)
                    old_data["date"] = "--"
                    old_data = json.dumps(old_data, separators=(',', ':'), sort_keys=True)
            
            # Create a new view of the data
            new_data = {
                'date': "--",
                'v4': sorted([str(x) for x in v4.iter_cidrs()]),
                'v6': sorted([str(x) for x in v6.iter_cidrs()]),
            }
            new_data = json.dumps(new_data, separators=(',', ':'), sort_keys=True)

            if old_data != new_data:
                # Dump out the data, set the mtime so the compressed file is deterministic
                with io.TextIOWrapper(gzip.GzipFile(dest_name, "w", 9, mtime=0), newline="") as f:
                    json.dump({
                        'date': run_at,
                        'v4': sorted([str(x) for x in v4.iter_cidrs()]),
                        'v6': sorted([str(x) for x in v6.iter_cidrs()]),
                    }, f, separators=(',', ':'), sort_keys=True)
                print(f"got {v4.size} IPs", flush=True)
            else:
                print(f"got {v4.size} IPs, no change", flush=True)

    # Add the new summary line
    with open(os.path.join("data", "summary.jsonl"), "at", newline="") as f:
        json.dump(all_info, f, separators=(',', ':'), sort_keys=True)
        f.write("\n")

    # And a simple file with the latest summary line
    with open(os.path.join("data", "summary.json"), "wt", newline="") as f:
        json.dump(all_info, f, separators=(',', ':'), sort_keys=True)
        f.write("\n")

    # And dump out the pretty version of each system
    with open(os.path.join("data", "names.json"), "wt", newline="") as f:
        json.dump(pretties, f, separators=(',', ':'), sort_keys=True)


if __name__ == "__main__":
    main()
