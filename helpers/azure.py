#!/usr/bin/env python3

from netaddr import IPSet, IPNetwork
from itertools import chain
from requests import get
import re

def get_and_parse():
    # I'm shocked, shocked I tell you to see that MS requires you do
    # something oddball like dig into an HTML page to get the latest
    # data file.
    url = "https://www.microsoft.com/en-us/download/confirmation.aspx?id=56519"
    data = get(url, headers={"User-Agent": "Not a Robot"}).text

    m = re.search('(?P<json>https://download.*?\\.json)', data)
    url = m.group("json")
    data = get(url, headers={"User-Agent": "Not a Robot"}).json()

    # Pull out all of the IPs
    azure = IPSet(IPNetwork(y) for y in chain.from_iterable(x['properties']['addressPrefixes'] for x in data['values']))

    # Pull out the v4 and v6 cidrs
    v4 = IPSet([x for x in azure.iter_cidrs() if x.network.version == 4])
    v6 = IPSet([x for x in azure.iter_cidrs() if x.network.version == 6])

    return {
        "name": "azure", 
        "pretty": "Azure", 
        "v4": v4, 
        "v6": v6, 
        "show": True, 
        "raw_data": data, 
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
