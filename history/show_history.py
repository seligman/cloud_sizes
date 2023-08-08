#!/usr/bin/env python3

from netaddr import IPSet, IPNetwork
import json
import os
import tarfile

def get_history(provider):
    # Load all history files for a given provider, including history files inside of .tar.gz files
    dirs = [(".", "")]
    while len(dirs) > 0:
        cur_dir, cur_pretty = dirs.pop(0)
        for cur in sorted(os.listdir(cur_dir)):
            pretty = cur if len(cur_pretty) == 0 else cur_pretty + "/" + cur
            cur = os.path.join(cur_dir, cur)
            if os.path.isdir(cur):
                dirs.append((cur, pretty))
            else:
                if cur.endswith(".tar.gz"):
                    with tarfile.open(cur, "r:gz") as tar:
                        for obj in tar:
                            if obj.name.endswith(".json"):
                                temp = obj.name.split("/")
                                if temp[1] == provider:
                                    yield json.load(tar.extractfile(obj))
                else:
                    if cur.endswith(".json"):
                        temp = pretty.split("/")
                        if temp[1] == provider:
                            with open(cur) as f:
                                yield json.load(f)

def main():
    # TODO: Do something interesting with the files
    providers = ["aws", "azure", "digitalocean", "facebook", "github", "google", "hetzner", "icloudprov", "linode", "oracle", "vultr"]
    for provider in providers:
        print("")
        print("# " + provider)
        print(",ipv4_count,ipv6_count")
        for data in get_history(provider):
            ipv4 = IPSet(IPNetwork(x) for x in data['v4'])
            ipv6 = IPSet(IPNetwork(x) for x in data['v6'])
            print(",".join([data['date'], str(ipv4.size), str(ipv6.size)]))

if __name__ == "__main__":
    main()
