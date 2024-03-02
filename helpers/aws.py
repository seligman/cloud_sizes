#!/usr/bin/env python3

from requests import get
from netaddr import IPSet, IPNetwork

def get_and_parse():
    # Get the current IP Ranges from AWS.
    ip_ranges = get("https://ip-ranges.amazonaws.com/ip-ranges.json").json()

    # Merge everything from AWS into two IPSets for each type.
    v4 = IPSet([IPNetwork(x["ip_prefix"]) for x in ip_ranges["prefixes"]])
    v6 = IPSet([IPNetwork(x["ipv6_prefix"]) for x in ip_ranges["ipv6_prefixes"]])

    return {
        "name": "aws", 
        "pretty": "AWS", 
        "v4": v4, 
        "v6": v6, 
        "show": True, 
        "raw_data": ip_ranges, 
        "raw_format": "json", 
        "allowed_overlap": {"github"},
    }

def test():
    data = get_and_parse()
    print(f"Results for {data['pretty']}:")
    print(f"  IPv4: {data['v4'].size:,}")
    print(f"  IPv6: {data['v6'].size:,}")

if __name__ == "__main__":
    test()
