#!/usr/bin/env python3

import subprocess
from datetime import datetime

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
