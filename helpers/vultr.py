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
    # Get the current IP Ranges from a whois query
    v4 = []
    v6 = []
    data = ""

    for asn in ['AS20473']:
        results = whois(asn)
        data += results

        # Parse it out
        for line in results.split("\n"):
            if line.startswith("route:"):
                v4.append(IPNetwork(line[6:].strip()))
            elif line.startswith("route6:"):
                v6.append(IPNetwork(line[7:].strip()))

    v4 = IPSet(v4)
    v6 = IPSet(v6)
    
    return "vultr", "Vultr", v4, v6, False, data, "txt"

if __name__ == "__main__":
    print("This module is not meant to be run directly")
