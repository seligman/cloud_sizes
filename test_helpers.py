#!/usr/bin/env python3

from importlib.util import spec_from_file_location, module_from_spec
from netaddr import IPSet, IPNetwork
import gzip
import json
import os
import sys

def approximate_count(val):
    val = val.size
    for scale in range(36, 0, -3):
        if val >= (10 ** scale) * 0.9:
            return f"{val / (10 ** scale):6.2f}e{scale}"
    return f"{val:3d}"

def get_main_ranges():
    # Stolen from https://github.com/seligman/aws-ip-ranges
    internet = IPSet([IPNetwork("0.0.0.0/0")])

    private = IPSet([IPNetwork(x) for x in [
        "0.0.0.0/8",       # RFC 1700 broadcast addresses
        "10.0.0.0/8",      # RFC 1918 Private address space (aka, your work LAN)
        "100.64.0.0/10",   # IANA Carrier Grade NAT (not your home NAT, no sirree)
        "100.64.0.0/10",   # RFC 6598 Carrier graded NAT
        "127.0.0.0/8",     # Loopback addresses (because you need 16 million IPs for localhost)
        "169.254.0.0/16",  # RFC 6890 Link Local address (aka, the broken LAN)
        "172.16.0.0/12",   # RFC 1918 Private address space (aka, Goldilocks' LAN)
        "192.0.0.0/24",    # RFC 5736 IANA IPv4 Special Purpose Address Registry
        "192.0.2.0/24",    # RFC 5737 TEST-NET for internal use
        "192.168.0.0/16",  # RFC 1918 Private address space (aka, your home LAN)
        "192.88.99.0/24",  # RFC 3068 6to4 anycast relays
        "198.18.0.0/15",   # RFC 2544 Testing of inter-network communications
        "198.51.100.0/24", # RFC 5737 TEST-NET-2 for internal use
        "203.0.113.0/24",  # RFC 5737 TEST-NET-3 for internal use
        "224.0.0.0/4",     # RFC 5771 Multicast Addresses
        "240.0.0.0/4",     # RFC 6890 Reserved for future use (or if the RFC team needs to make a few bucks)
    ]])

    return internet, private

def main():
    internet, private = get_main_ranges()
    known = {
        "private": private,
    }
    public_ips = internet.size - private.size
    print(public_ips)

    for cur in sorted(os.listdir("helpers")):
        use = cur.endswith(".py")
        if len(sys.argv) > 1:
            if sys.argv[1].lower() not in cur:
                use = False
        if use:
            print(f"{cur:<18}", end="", flush=True)
            try:
                spec = spec_from_file_location("ips", os.path.join("helpers", cur))
                ips = module_from_spec(spec)
                spec.loader.exec_module(ips)
                data = ips.get_and_parse()
                if data['raw_format'] == "json":
                    data['raw_data'] = json.dumps(data['raw_data'], separators=(',', ':'))
                data['raw_data'] = gzip.compress(data['raw_data'].encode("utf-8"))
                print(f"IPv4: {approximate_count(data['v4']):<9} ({data['v4'].size / public_ips * 100:6.4f}%) / IPv6: {approximate_count(data['v6']):<9} / Raw: {len(data['raw_data']):7d}", flush=True)
                for other, other_v4 in known.items():
                    overlap = other_v4 & data['v4']
                    if overlap.size > 0 and other not in data['allowed_overlap']:
                        print(f"WARNING: This overlaps with {other} by {overlap.size} IP addresses")
                known[data['name']] = data['v4']
            except Exception as ex:
                print("FAILED: " + str(ex), flush=True)

if __name__ == "__main__":
    main()