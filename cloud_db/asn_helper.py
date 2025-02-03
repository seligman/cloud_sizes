#!/usr/bin/env python3

from delaymsg import DelayMsg
from netaddr import IPAddress, IPRange
from urllib.request import urlopen, Request
import gzip
import os

def download(url, fn, desc=None):
    print(f"Downloading '{fn if desc is None else desc}'...")
    with open(fn, "wb") as f:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"})
        resp = urlopen(req)
        while True:
            bits = resp.read(131072)
            if len(bits) == 0:
                break
            f.write(bits)

def get_data():
    target = os.path.join("data", "ip2asn-combined.tsv.gz")

    if not os.path.isdir("data"):
        os.mkdir("data")

    if not os.path.isfile(target):
        url = "https://iptoasn.com/data/ip2asn-combined.tsv.gz"
        download(url, target)

    with DelayMsg() as msg:
        with gzip.open(target, "rt") as f:
            for line_no, row in enumerate(f):
                msg(f"Loading ASN data, on line {line_no:,}...")
                row = row.strip("\n").split("\t")
                first, last, asn, country, desc = row
                if asn != "0":
                    first = IPAddress(first)
                    last = IPAddress(last)
                    ips = IPRange(first, last)
                    yield "AS" + asn, desc, [str(x) for x in ips.cidrs()]

if __name__ == "__main__":
    print("This module is not meant to be run directly")
