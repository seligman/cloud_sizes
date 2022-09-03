#!/usr/bin/env python3

import socket
from netaddr import IPSet, IPNetwork

def whois(asn):
    try:
        # whois -h whois.radb.net -- '-i origin ...'
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect(("whois.radb.net", 43))
        query = "-i origin " + asn + "\r\n"
        query = query.encode("utf-8")
        s.send(query)

        ret = b''
        while True:
            chunk = s.recv(4096)
            if len(chunk) == 0:
                break
            ret += chunk
        s.close()
        ret = ret.decode("utf-8")
    except:
        ret = ""

    return ret

def get_and_parse():
    # Get the current IP Ranges from a series of whois queries
    v4 = []
    v6 = []

    for asn in ["AS24940", "AS213230", "AS212317"]:
        data = whois(asn)

        # Parse it out
        for line in data.split("\n"):
            if line.startswith("route:"):
                v4.append(IPNetwork(line[6:].strip()))
            elif line.startswith("route6:"):
                v6.append(IPNetwork(line[7:].strip()))

    v4 = IPSet(v4)
    v6 = IPSet(v6)
    data = {}
    data["ip_v4"] = [str(x) for x in v4.iter_cidrs()]
    data["ip_v6"] = [str(x) for x in v6.iter_cidrs()]

    return "hetzner", "Hetzner", v4, v6, False, data

if __name__ == "__main__":
    print("This module is not meant to be run directly")
