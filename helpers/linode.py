#!/usr/bin/env python3

from requests import get
from netaddr import IPSet, IPNetwork

def get_and_parse():
    # Get the current IP Ranges from Linode

    ips = get("https://geoip.linode.com/").text
    v4, v6 = [], []
    for row in ips.split("\n"):
        row = row.strip()
        if not row.startswith("#"):
            row = row.split(",")
            if len(row) > 1:
                if ":" in row[0]:
                    v6.append(IPNetwork(row[0]))
                else:
                    v4.append(IPNetwork(row[0]))
    
    v4 = IPSet(v4)
    v6 = IPSet(v6)

    return {
        "name": "linode", 
        "pretty": "Linode", 
        "v4": v4, 
        "v6": v6, 
        "show": True, 
        "raw_data": ips, 
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
