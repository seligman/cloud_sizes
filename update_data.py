#!/usr/bin/env python3

import subprocess
from datetime import datetime
import os
import matplotlib.pyplot as plt
import json

started = datetime.utcnow()
def log_step(value):
    # Simple helper to show how long everything takes
    print(f"{(datetime.utcnow() - started).total_seconds():8.4f}: {value}", flush=True)

def run(cmd):
    # Run commands
    log_step("$ " + " ".join([f'"{x}"' if " " in x else x for x in cmd]))
    subprocess.check_call(cmd)

log_step("Starting work")

# Main worker
run(["python3", "get_all.py"])

# Draw the images
if not os.path.isdir("images"):
    os.mkdir("images")

data = []
with open("summary.jsonl", "rt") as f:
    for row in f:
        data.append(row)
        if len(data) > 365:
            data.pop(0)

providers = set()
for i in range(len(data)):
    data[i] = json.loads(data[i])
    providers |= set(data[i])

md = ""
providers.remove("_")
with plt.style.context("dark_background"):
    log_step("Main chart")
    plt.figure(figsize=(7, 5))
    plt.bar(range(len(providers)), [data[-1].get(x, [0])[0] for x in sorted(providers)])
    plt.xticks(range(len(providers)), sorted(providers))
    plt.yticks(plt.yticks()[0], [f"{int(x/1000000):d}m" for x in plt.yticks()[0]])
    plt.tight_layout()
    plt.savefig(os.path.join("images", "main.png"), dpi=100)

    for cur in providers:
        log_step(f"Chart for {cur}")
        md += f"![{cur}](images/history_{cur}.png)\n\n"
        plt.clf()
        plt.figure(figsize=(7, 2))
        history = [x.get(cur, [0])[0] for x in data]
        plt.plot(range(len(history)), history)
        plt.xticks([])
        plt.yticks([])
        plt.ylabel("gcloud")
        plt.tight_layout()
        plt.savefig(os.path.join("images", f"history_{cur}.png"), dpi=100)

# Update the README
log_step("README")
with open("README.template.md", "rt") as f_src:
    with open("README.md", "wt") as f_dest:
        data = f_src.read()
        data = data.replace("[[history]]", md)

        f_dest.write(data)

# Check in any changes
run(["git", "add", "."])
changes = subprocess.check_output(["git", "status", "--porcelain"]).decode("utf-8")
changes = len([x for x in changes.split("\n") if len(changes.strip()) > 0])
if changes > 0:
    # Only bother with a commit if something changes
    run(["git", "commit", "-a", "-m", "Update data files"])
    run(["git", "push"])
else:
    log_step("No changes")

log_step("All done")
