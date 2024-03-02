#!/usr/bin/env python3

from requests import get
from netaddr import IPSet, IPNetwork

def get_and_parse():
    # Get the current IP Ranges from Cloudflare
    data = []

    ips = get("https://www.cloudflare.com/ips-v4").text
    data.append(ips)
    v4 = IPSet([IPNetwork(x) for x in ips.split("\n")])

    ips = get("https://www.cloudflare.com/ips-v6").text
    data.append(ips)
    v6 = IPSet([IPNetwork(x) for x in ips.split("\n")])

    return {
        "name": "cloudflare", 
        "pretty": "Cloudflare", 
        "v4": v4, 
        "v6": v6, 
        "show": True, 
        "raw_data": data, 
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
