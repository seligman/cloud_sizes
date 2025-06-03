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

    for asn in ['AS16276','AS35540']:
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

    return {
        "name": "ovhcloud",
        "pretty": "OVHcloud",
        "v4": v4, 
        "v6": v6, 
        "show": True, 
        "raw_data": data, 
        "raw_format": "txt", 
        "allowed_overlap": {},
    }

def test():
    data = get_and_parse()
    print(f"Results for {data['pretty']}:")
    print(f"  IPv4: {data['v4'].size:,}")
    print(f"  IPv6: {data['v6'].size:,}")

if __name__ == "__main__":
    test()
