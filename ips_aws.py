#!/usr/bin/env python3

from requests import get
from netaddr import IPSet, IPNetwork

def get_and_parse():
    # Get the current IP Ranges from AWS.
    ip_ranges = get("https://ip-ranges.amazonaws.com/ip-ranges.json").json()

    # Merge everything from AWS into two IPSets for each type.
    v4 = IPSet([IPNetwork(x["ip_prefix"]) for x in ip_ranges["prefixes"]])
    v6 = IPSet([IPNetwork(x["ipv6_prefix"]) for x in ip_ranges["ipv6_prefixes"]])

    return "aws", "AWS", v4, v6

if __name__ == "__main__":
    print("This module is not meant to be run directly")
