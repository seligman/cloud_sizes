#!/usr/bin/env python3

from requests import get
from netaddr import IPSet, IPNetwork

def get_and_parse():
    # Get the current IP Ranges from Cloudflare

    data = {}

    ips = get("https://www.cloudflare.com/ips-v4").text
    v4 = IPSet([IPNetwork(x) for x in ips.split("\n")])
    data["ip_v4"] = [str(x) for x in v4.iter_cidrs()]

    ips = get("https://www.cloudflare.com/ips-v6").text
    v6 = IPSet([IPNetwork(x) for x in ips.split("\n")])
    data["ip_v6"] = [str(x) for x in v6.iter_cidrs()]

    return "cloudflare", "Cloudflare", v4, v6, True, data

if __name__ == "__main__":
    print("This module is not meant to be run directly")
