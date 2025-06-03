#!/usr/bin/env python3

from datetime import datetime
from importlib.util import spec_from_file_location, module_from_spec
import gzip
import io
import json
import math
import os
import sys
if sys.version_info >= (3, 11): from datetime import UTC
else: import datetime as datetime_fix; UTC=datetime_fix.timezone.utc

def pretty(val, show_sign=True):
    sign = ""
    if show_sign:
        if val > 0:
            sign = "+"
        elif val < 0:
            sign = "-"
            val = abs(val)
    if val >= 100000:
        e = int(math.log10(val))
        return f"{sign}{val / (10 ** (e)):.2f}e{e}"
    else:
        return f"{sign}{val}"

def create_summary():
    # Just create a summary view as a simple RSS file
    rows = []
    with open(os.path.join("data", "summary.jsonl"), "rt") as f:
        for row in f:
            row = json.loads(row)
            rows.append(row)
            if len(rows) > 11:
                rows.pop(0)

    known = set()
    for row in rows:
        known |= set(row)
    known.remove("_")

    with open("rss.xml", "wt", newline="", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
        f.write('<rss version="2.0">\n')
        f.write('  <channel>\n')
        f.write('    <title>Cloud IP Ranges Updates</title>\n')
        f.write('    <link>https://github.com/seligman/cloud_sizes</link>\n')
        f.write('    <description>Changes to Cloud IP Ranges</description>\n')

        last = None
        for row in rows:
            if last is not None:
                link = "https://github.com/seligman/cloud_sizes#summary_" + row["_"].replace(" ", "-").replace(":", "-")
                f.write('    <item>\n')
                f.write('      <title>Cloud IP summary ' + row["_"] + '</title>\n')
                f.write('      <link>' + link + '</link>\n')
                f.write('      <description><![CDATA[<pre>')
                f.write("Cloud IP Report summary for " + row["_"] + "\n")
                f.write("All values are IPv4 / IPv6\n")
                f.write("\n")
                f.write("                     Total        --       Change        --       Change %\n")
                for key in sorted(known):
                    val_cur = row.get(key, [0, 0])
                    val_last = last.get(key, [0, 0])
                    msg = f"{key + ':':<13} "
                    msg += f"{pretty(val_cur[0], False):>8} / {pretty(val_cur[1], False):>8} -- "
                    msg += f"{pretty(val_cur[0] - val_last[0]):>8} / {pretty(val_cur[1] - val_last[1]):>8} -- "
                    temp = []
                    for i in range(2):
                        if val_cur[i] > 0 and val_last[i] == 0:
                            temp.append(f" (new)  ")
                        elif val_cur[i] > 0 and val_cur[i] == val_last[i]:
                            temp.append(f"     -  ")
                        elif val_cur[i] > 0:
                            temp.append(f"{((val_cur[i] - val_last[i]) / val_cur[i]) * 100:7.2f}%")
                        else:
                            temp.append(f" (n/a)  ")
                    msg += " / ".join(temp)
                    f.write(msg + "\n")
                f.write(']]></description>\n')
                f.write('    </item>\n')
            last = row
        f.write('  </channel>\n')
        f.write('</rss>\n')

def get_data():
    run_at = datetime.now(UTC).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    all_info = {
        '_': run_at,
    }

    # What the different services are properly called
    pretties = {}

    # Loop for each file in the helpers dir, and let it doe the work for its provider
    for cur in sorted(os.listdir("helpers")):
        if cur.endswith(".py"):
            print(f"Working on {cur:<16} ", end="", flush=True)
            try:
                spec = spec_from_file_location("ips", os.path.join("helpers", cur))
                ips = module_from_spec(spec)
                spec.loader.exec_module(ips)
                temp = ips.get_and_parse()
                if not isinstance(temp, dict) or 'name' not in temp:
                    raise Exception("Invalid return")
                data = temp

                pretties[data['name']] = [data['pretty'], data['show']]

                # Basic smoke test validation, if no data is found, bail out now
                if data['v4'].size == 0:
                    raise Exception("No IPv4 data found!")

                # Add a summary to our summary dictionary
                all_info[data['name']] = [data['v4'].size, data['v6'].size]
            except Exception as e:
                print("ERROR: " + str(e))
                dest_name = os.path.join("data", f"data_{data['name']}.json.gz")
                if os.path.isfile(dest_name):
                    with gzip.open(dest_name) as f:
                        old_data = json.load(f)
                        all_info[data['name']] = [old_data.get('v4_size', 0), old_data.get('v6_size', 0)]
    return all_info

def main():
    # A summary of this run
    run_at = datetime.now(UTC).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    all_info = {
        '_': run_at,
    }

    # What the different services are properly called
    pretties = {}

    # Loop for each file in the helpers dir, and let it doe the work for its provider
    for cur in sorted(os.listdir("helpers")):
        if cur.endswith(".py"):
            print(f"Working on {cur:<16} ", end="", flush=True)
            try:
                data = {"name": cur[:-3]}

                spec = spec_from_file_location("ips", os.path.join("helpers", cur))
                ips = module_from_spec(spec)
                spec.loader.exec_module(ips)
                temp = ips.get_and_parse()
                if not isinstance(temp, dict) or 'name' not in temp:
                    raise Exception("Invalid return")
                data = temp

                pretties[data['name']] = [data['pretty'], data['show']]

                # Basic smoke test validation, if no data is found, bail out now
                if data['v4'].size == 0:
                    raise Exception("No IPv4 data found!")

                # Add a summary to our summary dictionary
                all_info[data['name']] = [data['v4'].size, data['v6'].size]

                # Read in the old data
                old_data = "--"
                dest_name = os.path.join("data", f"data_{data['name']}.json.gz")

                old_v4_size = 0
                if os.path.isfile(dest_name):
                    with gzip.open(dest_name) as f:
                        old_data = json.load(f)
                        old_v4_size = old_data.get('v4_size', 0)
                        old_data["date"] = "--"
                        old_data = json.dumps(old_data, separators=(',', ':'), sort_keys=True)
                
                # Create a new view of the data
                new_data = {
                    'date': "--",
                    'v4': sorted([str(x) for x in data['v4'].iter_cidrs()]),
                    'v6': sorted([str(x) for x in data['v6'].iter_cidrs()]),
                    'v4_size': data['v4'].size,
                    'v6_size': data['v6'].size,
                }
                new_data = json.dumps(new_data, separators=(',', ':'), sort_keys=True)

                extra_pad = ""
                if old_data != new_data:
                    # Dump out the data, set the mtime so the compressed file is deterministic
                    with io.TextIOWrapper(gzip.GzipFile(dest_name, "w", 9, mtime=0), newline="") as f:
                        json.dump({
                            'date': run_at,
                            'v4': sorted([str(x) for x in data['v4'].iter_cidrs()]),
                            'v6': sorted([str(x) for x in data['v6'].iter_cidrs()]),
                            'v4_size': data['v4'].size,
                            'v6_size': data['v6'].size,
                        }, f, separators=(',', ':'), sort_keys=True)
                    new_v4_size = data['v4'].size
                    if new_v4_size != old_v4_size and old_v4_size > 0 and new_v4_size > 0:
                        if new_v4_size > old_v4_size:
                            change = f"+{new_v4_size - old_v4_size}"
                        else:
                            change = f"-{old_v4_size - new_v4_size}"
                        print(f"got {data['v4'].size:>8} IPs, change by {change:>8}", flush=True, end="")
                    else:
                        print(f"got {data['v4'].size:>8} IPs", flush=True, end="")
                        extra_pad = ' ' * 20
                else:
                    print(f"got {data['v4'].size:>8} IPs, no change", flush=True, end="")
                    extra_pad = ' ' * 9

                # Also log out the raw data
                old_data = b'--'
                dest_name = os.path.join("data", f"raw_{data['name']}.{data['raw_format']}.gz")
                if os.path.isfile(dest_name):
                    try:
                        with gzip.open(dest_name, "rb") as f:
                            old_data = f.read()
                    except:
                        old_data = b'--'
                new_data = data['raw_data']
                if data['raw_format'] == "json":
                    new_data = json.dumps(new_data, separators=(',', ':'))
                new_data = new_data.encode("utf-8")
                if old_data != new_data:
                    with gzip.open(dest_name, "wb") as f:
                        f.write(new_data)
                        print(f",{extra_pad} wrote {len(new_data):9d} bytes raw", flush=True)
                else:
                    print(f",{extra_pad} no change of raw data.", flush=True)
            except Exception as e:
                print("ERROR: " + str(e))
                dest_name = os.path.join("data", f"data_{data['name']}.json.gz")
                if os.path.isfile(dest_name):
                    with gzip.open(dest_name) as f:
                        old_data = json.load(f)
                        all_info[data['name']] = [old_data.get('v4_size', 0), old_data.get('v6_size', 0)]

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

    # And dump out the RSS summary
    create_summary()

if __name__ == "__main__":
    main()
