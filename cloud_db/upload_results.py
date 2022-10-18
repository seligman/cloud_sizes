#!/usr/bin/env python3

from calc_etag import calculate_etag
from datetime import datetime
import boto3
import os

files = [
    ("html", "index.html", "text/html", False),
    ("html", "cidr_helper.min.js", "text/javascript", False),
    ("html", "favicon-32x32.png", "image/png", False),
    ("html", "favicon-16x16.png", "image/png", False),
    ("data", "cloud_db.dat", "application/octect-stream", True),
]

s3 = boto3.client('s3')
paginator = s3.get_paginator('list_objects_v2')
tags = {}
for page in paginator.paginate(Bucket='cloud-ips'):
    for cur in page.get('Contents', []):
        tags[cur['Key']] = cur['ETag'].strip('"')

for source, key, mime, historical in files:
    fn = os.path.join(source, key)
    if os.path.isfile(fn):
        cur_tag = calculate_etag(fn)
        if tags.get(key, "--") == cur_tag:
            print(f"{key} is up to date")
        else:
            print(f"Uploading {key}...")
            s3.upload_file(
                fn, 
                "cloud-ips", 
                key, 
                ExtraArgs={
                    'ACL': 'public-read', 
                    'ContentType': mime,
                },
            )
            if historical:
                key = "history/cloud_" + datetime.utcnow().strftime("%Y/%m/%Y%m%d-%H%M%S") + ".dat"
                print(f"Uploading {key}...")
                s3.upload_file(fn, "cloud-ips", key)
