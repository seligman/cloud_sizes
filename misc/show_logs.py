#!/usr/bin/env python3

from datetime import datetime, timedelta
import boto3
import sys

AWS_PROFILE = "pers"
AWS_REGION = "us-west-2"
LOG_GROUP_NAME = "/aws/lambda/trackCloudSizes"

_client = boto3.Session(profile_name=AWS_PROFILE).client('logs', region_name=AWS_REGION)

def show_quick():
    recent(quick_only=True)

def recent(quick_only=False):
    args = {
        'logGroupName': LOG_GROUP_NAME,
        'descending': True,
        'orderBy': 'LastEventTime',
    }
    oldest = datetime.utcnow() - timedelta(days=7)
    epoch = datetime(1970, 1, 1)
    last_msg = ""
    msgs = []
    at_end = False
    for cur in _client.get_paginator('describe_log_streams').paginate(**args):
        for stream in cur['logStreams']:
            at = epoch + timedelta(seconds=stream['lastEventTimestamp'] / 1000)
            if at < oldest:
                at_end = True
                break
            msg = f"Working, gathered {len(msgs)} log streams..."
            print("\r" + " " * len(last_msg) + "\r" + msg, end="", flush=True)
            last_msg = msg
            msgs.append([at])
            args = {
                'logGroupName': LOG_GROUP_NAME,
                'logStreamName': stream["logStreamName"],
                'startFromHead': True,
            }
            info = ""
            while True:
                resp = _client.get_log_events(**args)
                for event in resp['events']:
                    if len(info) == 0:
                        info = (epoch + timedelta(seconds=event['timestamp']/1000)).strftime("%d %H:%M:%S") + ": " + event['message']
                    else:
                        info += event['message']
                    if info.endswith("\n"):
                        show_line = True
                        if quick_only:
                            show_line = ": Working on " in info
                        if show_line:
                            msgs[-1].append(info.strip("\n"))
                        info = ""
                if resp['nextForwardToken'] == args.get('nextToken'):
                    break
                args['nextToken'] = resp['nextForwardToken']
            if len(info):
                show_line = True
                if quick_only:
                    show_line = ": Working on " in info
                if show_line:
                    msgs[-1].append(info.strip("\n"))
        if at_end:
            break

    print("\r" + " " * len(last_msg) + "\r", end="", flush=True)

    msgs.sort(key=lambda x:x[0])

    for i, cur in enumerate(msgs):
        if i > 0:
            print("-" * 80)
        for row in cur[1:]:
            print(row)


def show_groups():
    for cur in _client.get_paginator('describe_log_groups').paginate():
        for group in cur['logGroups']:
            print(group['logGroupName'])

if __name__ == "__main__":
    cmds = {
        "show": ("Show all CloudWatch log groups", show_groups),
        "recent": ("Show recent log events", recent),
        "quick": ("Show just the Working on lines", show_quick),
    }
    if len(sys.argv) == 2 and sys.argv[1] in cmds:
        cmds[sys.argv[1]][1]()
    else:
        print("Usage:")
        for cmd, (desc, func) in cmds.items():
            print(f"  {cmd:10s} = {desc}")
