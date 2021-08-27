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
    data = get(url).text
    m = re.search('(?P<json>https://download.*?\.json)', data)
    url = m.group("json")
    data = get(url).json()

    # Pull out all of the IPs
    azure = IPSet(IPNetwork(y) for y in chain.from_iterable(x['properties']['addressPrefixes'] for x in data['values']))

    # Pull out the v4 and v6 cidrs
    v4 = IPSet([x for x in azure.iter_cidrs() if x.network.version == 4])
    v6 = IPSet([x for x in azure.iter_cidrs() if x.network.version == 6])

    return "azure", "Azure", v4, v6, True


if __name__ == "__main__":
    print("This module is not meant to be run directly")
