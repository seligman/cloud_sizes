#!/usr/bin/env python3

from requests import get
from netaddr import IPSet, IPNetwork
from itertools import chain

def get_and_parse():
    # Get the current IP Ranges from Oracle.
    ip_ranges = get("https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json").json()

    # Merge everything from AWS into one IPSet.
    oracle = IPSet([IPNetwork(x) for x in chain.from_iterable([[y['cidr'] for y in x['cidrs']] for x in ip_ranges["regions"]])])

    # Pull out the v4 and v6 cidrs
    v4 = IPSet([x for x in oracle.iter_cidrs() if x.network.version == 4])
    v6 = IPSet([x for x in oracle.iter_cidrs() if x.network.version == 6])

    return "oracle", "Oracle", v4, v6, True, ip_ranges, "json"

if __name__ == "__main__":
    print("This module is not meant to be run directly")
