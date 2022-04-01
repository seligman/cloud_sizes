#!/usr/bin/env python3

from datetime import datetime, timedelta
import boto3
import sys

AWS_PROFILE = "pers"
AWS_REGION = "us-west-2"
LOG_GROUP_NAME = "/aws/lambda/trackCloudSizes"

_client = boto3.Session(profile_name=AWS_PROFILE).client('logs', region_name=AWS_REGION)

def recent():
    args = {
        'logGroupName': LOG_GROUP_NAME,
        'descending': True,
        'orderBy': 'LastEventTime',
    }
    oldest = datetime.utcnow() - timedelta(days=2)
    for cur in _client.get_paginator('describe_log_streams').paginate(**args):
        for stream in cur['logStreams']:
            at = datetime.fromtimestamp(stream['lastEventTimestamp'] / 1000)
            if at < oldest:
                return
            args = {
                'logGroupName': LOG_GROUP_NAME,
                'logStreamName': stream["logStreamName"],
                'startFromHead': True,
            }
            last_token, info = None, ""
            print("-" * 50)
            while True:
                resp = _client.get_log_events(**args)
                for event in resp['events']:
                    if len(info) == 0:
                        info = datetime.fromtimestamp(event['timestamp']/1000).strftime("%d %H:%M:%S") + ": " + event['message']
                    else:
                        info += event['message']
                    if info.endswith("\n"):
                        print(info.strip("\n"))
                        info = ""
                if resp['nextForwardToken'] == args.get('nextToken'):
                    break
                args['nextToken'] = resp['nextForwardToken']
            if len(info):
                print(info.strip("\n"))

def show_groups():
    for cur in _client.get_paginator('describe_log_groups').paginate():
        for group in cur['logGroups']:
            print(group['logGroupName'])

if __name__ == "__main__":
    cmds = {
        "show": ("Show recent log events", show_groups),
        "recent": ("Show all CloudWatch log groups", recent),
    }
    if len(sys.argv) == 2 and sys.argv[1] in cmds:
        cmds[sys.argv[1]][1]()
    else:
        print("Usage:")
        for cmd, (desc, func) in cmds.items():
            print(f"  {cmd:10s} = {desc}")
