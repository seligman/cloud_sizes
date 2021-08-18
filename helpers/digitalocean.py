#!/usr/bin/env python3

from requests import get
from netaddr import IPSet, IPNetwork

def get_and_parse():
    # Get the current IP Ranges from a CSV, how quaint
    ip_ranges = get("https://digitalocean.com/geo/google.csv").text

    v4 = IPSet()
    v6 = IPSet()

    for row in [x.strip().split(",") for x in ip_ranges.split("\n") if len(x.strip())]:
        cidr = IPNetwork(row[0])
        if cidr.network.version == 4:
            v4.add(cidr)
        else:
            v6.add(cidr)

    return "digitalocean", "DigitalOcean", v4, v6

if __name__ == "__main__":
    print("This module is not meant to be run directly")
