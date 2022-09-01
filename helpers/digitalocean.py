#!/usr/bin/env python3

from requests import get
from netaddr import IPSet, IPNetwork

def get_and_parse():
    # Get the current IP Ranges from a CSV, how quaint
    ip_ranges = get("https://digitalocean.com/geo/google.csv").text

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
    data = {}
    data["ip_v4"] = [str(x) for x in v4.iter_cidrs()]
    data["ip_v6"] = [str(x) for x in v6.iter_cidrs()]

    return "digitalocean", "DigitalOcean", v4, v6, True, data

if __name__ == "__main__":
    print("This module is not meant to be run directly")
