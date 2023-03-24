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

    return "github", "GitHub", v4, v6, True, ip_ranges, "json", {"aws", "azure"}

if __name__ == "__main__":
    print("This module is not meant to be run directly")
