#!/usr/bin/env python3

from netaddr import IPSet, IPNetwork
from requests import get

def get_and_parse():
    # Google publishes the list in a simple JSON file, and also in an
    # overly complex DNS TXT record, because of course they do
    url = "https://www.gstatic.com/ipranges/cloud.json"
    data = get(url).json()

    # Pull out all of the IPv4 and v6
    v4 = IPSet(IPNetwork(y['ipv4Prefix']) for y in data['prefixes'] if 'ipv4Prefix' in y)
    v6 = IPSet(IPNetwork(y['ipv6Prefix']) for y in data['prefixes'] if 'ipv6Prefix' in y)

    return "google", "Google Cloud", v4, v6

if __name__ == "__main__":
    print("This module is not meant to be run directly")
