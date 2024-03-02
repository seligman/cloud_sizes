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

    return {
        "name": "oracle", 
        "pretty": "Oracle", 
        "v4": v4, 
        "v6": v6, 
        "show": True, 
        "raw_data": ip_ranges, 
        "raw_format": "json", 
        "allowed_overlap": {},
    }

def test():
    data = get_and_parse()
    print(f"Results for {data['pretty']}:")
    print(f"  IPv4: {data['v4'].size:,}")
    print(f"  IPv6: {data['v6'].size:,}")

if __name__ == "__main__":
    test()
