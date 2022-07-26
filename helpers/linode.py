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

    return "linode", "Linode", v4, v6, True

if __name__ == "__main__":
    print("This module is not meant to be run directly")
