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

    return {
        "name": "digitalocean", 
        "pretty": "DigitalOcean", 
        "v4": v4, 
        "v6": v6, 
        "show": True, 
        "raw_data": ip_ranges, 
        "raw_format": "csv", 
        "allowed_overlap": {},
    }

def test():
    data = get_and_parse()
    print(f"Results for {data['pretty']}:")
    print(f"  IPv4: {data['v4'].size:,}")
    print(f"  IPv6: {data['v6'].size:,}")

if __name__ == "__main__":
    test()
