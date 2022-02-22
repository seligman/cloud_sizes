#!/usr/bin/env python3

from requests import get
from netaddr import IPSet, IPNetwork

def get_and_parse():
    # Get the current IP Ranges from a CSV
    ip_ranges = get("https://mask-api.icloud.com/egress-ip-ranges.csv").text

    v4 = []
    v6 = []

    for row in [x.strip().split(",") for x in ip_ranges.split("\n") if len(x.strip())]:
        cidr = IPNetwork(row[0])
        if cidr.network.version == 4:
            v4.append(cidr)
        else:
            v6.append(cidr)

    v4 = IPSet(v4)
    v6 = IPSet(v6)

    return "icloudprov", "iCloud", v4, v6, True

if __name__ == "__main__":
    print("This module is not meant to be run directly")
