#!/usr/bin/env python3

from requests import get
from netaddr import IPSet, IPNetwork

def get_and_parse():
    # Get the current IP Ranges from AWS.
    ip_ranges = get("https://api.github.com/meta").json()

    v4 = []
    v6 = []
    for key, value in ip_ranges.items():
        if key not in {"verifiable_password_authentication", "ssh_key_fingerprints", "ssh_keys"}:
            if isinstance(value, list):
                for cidr in value:
                    if ":" in cidr:
                        v6.append(cidr)
                    else:
                        v4.append(cidr)

    # Merge everything from AWS into two IPSets for each type.
    v4 = IPSet(v4)
    v6 = IPSet(v6)

    return {
        "name": "github", 
        "pretty": "GitHub", 
        "v4": v4, 
        "v6": v6, 
        "show": True, 
        "raw_data": ip_ranges, 
        "raw_format": "json", 
        "allowed_overlap": {"aws", "azure"},
    }

def test():
    data = get_and_parse()
    print(f"Results for {data['pretty']}:")
    print(f"  IPv4: {data['v4'].size:,}")
    print(f"  IPv6: {data['v6'].size:,}")

if __name__ == "__main__":
    test()
