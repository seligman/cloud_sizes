#!/usr/bin/env python3

from urllib.request import urlopen, Request

def build_badge(url, fn):
    with open(fn, "wb") as f:
        f.write(urlopen(Request(url, headers={"User-Agent": "Builder"})).read())
    print("Built " + fn)

build_badge("https://img.shields.io/badge/RSS-Daily_Updates-blue?logo=rss", "rss_badge.svg")