#!/usr/bin/env python3

from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt
import os
import subprocess
import sys
if sys.version_info >= (3, 11): from datetime import UTC
else: import datetime as datetime_fix; UTC=datetime_fix.timezone.utc

_started = datetime.now(UTC).replace(tzinfo=None)
def log_step(value):
    # Simple helper to show how long everything takes
    print(f"{(datetime.now(UTC).replace(tzinfo=None) - _started).total_seconds():8.4f}: {value}", flush=True)

def run(cmd):
    # Run commands
    log_step("$ " + " ".join([f'"{x}"' if " " in x else x for x in cmd]))
    subprocess.check_call(cmd)

def fast_parse_date(text):
    return datetime(
        year=int(text[0:4]),
        month=int(text[5:7]),
        day=int(text[8:10]),
        hour=int(text[11:13] or 0),
        minute=int(text[14:16] or 0),
        second=int(text[17:19] or 0)
    )

def main():
    show_help = False
    chart_only = False
    draw_hilbert = True
    run_git_commands = True
    force_draw = set()

    args = sys.argv[1:]
    while len(args) > 0:
        if args[0].lower() == "charts":
            args.pop(0)
            chart_only = True
            run_git_commands = False
        elif args[0].lower() in {"no_hilbert", "nohilbert"}:
            args.pop(0)
            draw_hilbert = False
            run_git_commands = False
        elif args[0].lower() in {"skip_git", "skipgit"}:
            args.pop(0)
            run_git_commands = False
        elif args[0].lower() == "force" and len(args) > 1:
            args.pop(0)
            force_draw.add(args.pop(0))
        else:
            show_help = True
            break
    
    if show_help:
        print("Usage:")
        print("  charts     - Only draw charts, don't update date or check in changes")
        print("  no_hilbert - Don't update the Hilbert Curve map")
        print("  skip_git   - Skip running all git commands")
        print("  force <x>  - Force helper <x> to be included, even if previously disabled")
        exit(1)

    log_step("Starting work")

    if not chart_only:
        # Main worker to update all data
        run(["python3", "get_all.py"])

    # Draw the images
    if not os.path.isdir("images"):
        os.mkdir("images")

    data = []
    with open(os.path.join("data", "summary.jsonl"), "rt") as f:
        for row in f:
            data.append(row)
            if len(data) > 365:
                data.pop(0)

    # Find all off the different providers being used
    providers = set()
    for i in range(len(data)):
        data[i] = json.loads(data[i])
        providers |= set(data[i])
    if "_" in providers:
        providers.remove("_")
    
    # Load the pretty names, if the file exists
    if os.path.isfile(os.path.join("data", "names.json")):
        with open(os.path.join("data", "names.json")) as f:
            pretties = json.load(f)
    else:
        pretties = {}

    # Get the list of enabled providers
    enabled = {x for x, y in pretties.items() if y[1] or x in force_draw}
    # Get the providers in a simple list, and make sure to sort
    # them by the pretty name, since it could, but probably won't,
    # change the sort order
    providers = sorted(providers, key=lambda x: pretties.get(x, [x])[0].lower())
    # Limit the providers to only the enabled ones
    providers = [x for x in providers if x in enabled]

    # Run through and find the y limits of all the providers
    # so we can use one y limit for all charts
    min_y = None
    max_y = None
    for cur in providers:
        temp = [x[cur][0] for x in data if cur in x]
        if len(temp):
            cur_min_y = min(temp)
            cur_max_y = max(temp)
            if min_y is None:
                min_y, max_y = cur_min_y, cur_max_y
            else:
                min_y = min(min_y, cur_min_y)
                max_y = max(max_y, cur_max_y)

    if min_y is None:
        min_y, max_y = 0, 100

    # Limit to a nice edge on a log scale
    min_y = 1
    max_y = int('1' + '0' * len(str(int(max_y))))

    # Order elements on the chart by size
    pretty_order = providers[:]
    pretty_order.sort(key=lambda x:data[-1].get(x, [0])[0], reverse=True)

    md = ""
    with plt.style.context("dark_background"):
        log_step("Main chart")
        plt.figure(figsize=(8, 5))
        plt.grid(True, which='major', axis='y', zorder=1, color=(.5, .5, .5))
        plt.grid(True, which='minor', axis='y', zorder=1, color=(.5, .5, .5))
        plt.bar(range(len(providers)), [data[-1].get(x, [0])[0] for x in pretty_order], zorder=2)
        plt.xticks(range(len(providers)), [("\n" if i % 2 == 1 else "") + pretties.get(x, [x])[0] for i, x in enumerate(pretty_order)])
        plt.yticks(plt.yticks()[0], [f"{int(x/1000000):d}m" for x in plt.yticks()[0]])
        plt.yscale('log')
        plt.ylim((min_y, max_y))
        plt.tight_layout()
        plt.savefig(os.path.join("images", "main.png"), dpi=100)

        # Pull out the dates, use a number so matplotlib can align things
        epoch = datetime(2020, 1, 1)
        xaxis = [(fast_parse_date(x['_']) - epoch).total_seconds() / 86400.0 for x in data]

        min_y, max_y = 0, 0
        percent_change = {}
        # Calculate the percent change for all of the providers
        for cur in providers:
            history = [x.get(cur, [None])[0] for x in data]
   
            # Fill in any gaps to prevent drops to zero when no data is found
            last_value = 0
            for i, x in enumerate(history):
                if x is None:
                    history[i] = last_value
                else:
                    last_value = x

            temp = []
            last_value = history[0]
            for cur_value in history:
                if last_value > 0:
                    temp.append(((cur_value - last_value) / last_value) * 100)
                else:
                    temp.append(0)
                last_value = cur_value
            percent_change[cur] = temp
            temp = [x for x in temp if abs(x) <= 5]
            if len(temp) > 0:
                min_y = min(min_y, min(temp))
                max_y = max(max_y, max(temp))

        if (max_y - min_y) > 0.05:
            buffer = (max_y - min_y) * 0.05
        else:
            buffer = 0.025

        min_y -= buffer
        max_y += buffer

        for cur in providers:
            log_step(f"Chart for {cur}")
            md += f"![{cur}](images/history_{cur}.png)<br>\n"
            plt.clf()
            plt.figure(figsize=(8, 2))
            history = percent_change[cur]

            plt.plot(xaxis, history, linewidth=3.0)
            plt.ylim((min_y, max_y))
            plt.xlim((min(xaxis), max(xaxis)))
            plt.xticks(plt.xticks()[0], [f"{(epoch + timedelta(days=x)).strftime('%m-%d')}" for x in plt.xticks()[0]])
            plt.yticks(plt.yticks()[0], [f"{int(x):d}%" for x in plt.yticks()[0]])
            plt.ylabel(pretties.get(cur, [cur])[0])
            plt.tight_layout()
            plt.savefig(os.path.join("images", f"history_{cur}.png"), dpi=100)

    if draw_hilbert:
        log_step("Draw a map of the big IP ranges")
        subprocess.check_call(["python3", "draw_map.py", os.path.join("images", "map.png")])

    # Update the README
    log_step("Create README from template")
    with open("README.template.md", "rt") as f_src:
        with open("README.md", "wt", newline="") as f_dest:
            data = f_src.read()
            data = data.replace("[[history]]", md)
            f_dest.write(data)

    if run_git_commands:
        # Check in any changes
        run(["git", "add", "."])
        log_step("Look for changes")
        changes = subprocess.check_output(["git", "status", "--porcelain"]).decode("utf-8")
        changes = len([x for x in changes.split("\n") if len(changes.strip()) > 0])
        if changes > 0:
            # Only bother with a commit if something changes
            run(["git", "commit", "-a", "-m", "Update data files"])
            run(["git", "push"])
        else:
            log_step("No changes")

    log_step("All done")

if __name__ == "__main__":
    main()
