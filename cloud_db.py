#!/usr/bin/env python3

from collections import deque
from datetime import datetime
from netaddr import IPNetwork
import gzip
import json
import os
import socket
import struct

BASE_DIR = "."
COOKIE = b'Cloud IPs Database\n\x00\x00'

class Level:
    # The basic idea here is to store a series of pages.  Each page
    # can refer to either the page for the '0' and '1' bit, or 
    # if all items below this page are for the same data blob, they
    # can point to 'both', which is that data blob.
    # The 'offset' variable is used to track where this page will
    # be written to the final file, so we can write out the pointers.
    __slots__ = ('both', 'zero', 'one', 'offset')
    def __init__(self, both=[], zero=None, one=None, offset=-1):
        self.both = both
        self.zero = zero
        self.one = one
        self.offset = offset

def add_data(source, targets, prefix, service, region):
    # Add an data blob to our tree

    # First off, pick the IPv4 or IPv6 tree
    cidr = IPNetwork(prefix)
    if cidr.ip.version == 4:
        level = targets.zero
    elif cidr.ip.version == 6:
        level = targets.one
    else:
        raise Exception(f"Invalid CIDR IP version: {cidr.ip.version}")

    # Now we pick the pages for each bit in turn, until we hit the hostmask bits
    hostmask = cidr.hostmask.bits().replace(".", "").replace(":", "") + '1'
    ip = cidr.ip.bits().replace(".", "").replace(":", "") + '?'

    # This is the final data blob we're storing
    key = [source, service, region, prefix]

    for h, i in zip(hostmask, ip):
        if h == '1':
            # Ok, we want to add this key to this page however, if we have 
            # pages below this page because of some other value, we want to 
            # add this data to all of the final leafs
            for page in enum_pages(level):
                if page.both is not None:
                    page.both.append(key)
            break
        else:
            # We have deeper to go, go ahead and break this page into two
            # sub pages if it's a leaf
            if level.both is not None:
                level.zero = Level(level.both[:])
                level.one = Level(level.both)
                level.both = None

            # And go into the sub page
            if i == '0':
                level = level.zero
            elif i == '1':
                level = level.one
            else:
                raise Exception(f"Unknown bit in IP: {i}")

def enum_pages(targets):
    # Simple helper to return all pages under a given page
    todo = deque([targets])
    while len(todo):
        page = todo.pop()
        yield page
        if page.both is None:
            todo.appendleft(page.zero)
            todo.appendleft(page.one)

def add_aws(targets):
    # Add all AWS ranges to our current working set
    with gzip.open(os.path.join(BASE_DIR, "data", "raw_aws.json.gz")) as f:
        data = json.load(f)

    for cur in data["prefixes"] + data["ipv6_prefixes"]:
        prefix = cur.get("ip_prefix", cur.get("ipv6_prefix"))
        add_data("aws", targets, prefix, cur["service"], cur["region"])

def add_google(targets):
    # Add all Google ranges to our current working set
    with gzip.open(os.path.join(BASE_DIR, "data", "raw_google.json.gz")) as f:
        data = json.load(f)

    for cur in data['prefixes']:
        prefix = cur.get("ipv4Prefix", cur.get("ipv6Prefix"))
        add_data("google", targets, prefix, cur["service"], cur["scope"])

def add_azure(targets):
    # Add all Azure ranges to our current working set
    with gzip.open(os.path.join(BASE_DIR, "data", "raw_azure.json.gz")) as f:
        data = json.load(f)

    for group in data["values"]:
        for prefix in group['properties']['addressPrefixes']:
            add_data("azure", targets, prefix, group["properties"].get("systemService", ""), group["properties"].get("region", ""))

def add_private(targets):
    # Add all private IPs from a hardcoded list
    ranges = [
        ("0.0.0.0/8", "RFC 1700 broadcast addresses"),
        ("10.0.0.0/8", "RFC 1918 Private address space"),
        ("100.64.0.0/10", "IANA Carrier Grade NAT"),
        ("100.64.0.0/10", "RFC 6598 Carrier graded NAT"),
        ("127.0.0.0/8", "Loopback addresses"),
        ("169.254.0.0/16", "RFC 6890 Link Local address"),
        ("172.16.0.0/12", "RFC 1918 Private address space"),
        ("192.0.0.0/24", "RFC 5736 IANA IPv4 Special Purpose Address Registry"),
        ("192.0.2.0/24", "RFC 5737 TEST-NET for internal use"),
        ("192.168.0.0/16", "RFC 1918 Private address space"),
        ("192.88.99.0/24", "RFC 3068 6to4 anycast relays"),
        ("198.18.0.0/15", "RFC 2544 Testing of inter-network communications"),
        ("198.51.100.0/24", "RFC 5737 TEST-NET-2 for internal use"),
        ("203.0.113.0/24", "RFC 5737 TEST-NET-3 for internal use"),
        ("224.0.0.0/4", "RFC 5771 Multicast Addresses"),
        ("240.0.0.0/4", "RFC 6890 Reserved for future use"),
        ("fd00::/8", "RFC 4193 Unique local address"),
        ("fe80::/10", "RFC 4291 Link Local address"),
        ("::1/128", "Loopback addresses"),
    ]
    for prefix, desc in ranges:
        add_data("private", targets, prefix, desc, "")

def add_other(targets, source):
    # Add IPs from a pre-parsed list of data
    with gzip.open(os.path.join(BASE_DIR, "data", f"data_{source}.json.gz")) as f:
        data = json.load(f)

    for prefix in data['v4'] + data['v6']:
        add_data(source, targets, prefix, "", "")

def create_db(target_file):
    # The main page includes sub pages for IPv4 and IPv6
    targets = Level(both=None, zero=Level(), one=Level(), offset=0)

    add_aws(targets)
    add_google(targets)
    add_azure(targets)
    add_private(targets)
    others = [
        "cloudflare", 
        "digitalocean", 
        "facebook", 
        "hetzner", 
        "icloudprov", 
        "linode", 
        "oracle", 
        "vultr", 
    ]
    for other in others:
        add_other(targets, other)

    # Figure out all of the page offsets
    valid_pages = {}
    offset = 128
    for page in enum_pages(targets):
        if page.both is None:
            page.offset = offset
            offset += 8
        else:
            key = b'\x01'.join(b'\x00'.join(x.encode("utf-8") for x in item) for item in page.both)
            page.both = key
            valid_pages[key] = 0

    # Store the offsets for the data pages
    for key in valid_pages:
        valid_pages[key] = offset
        # Two extra bytes for the length header
        offset += len(key) + 2

    field_size = 1
    offset *= 2
    while offset >= 256:
        field_size += 1
        offset /= 256
    
    # Write out all of the data
    with open(target_file, "wb") as f:
        header = COOKIE
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S").encode("utf-8")
        header += struct.pack("!HHH", 1, field_size, len(now))
        header += now
        header += b'\x00' * (128 - len(header))
        f.write(header)

        offset = 128
        for page in enum_pages(targets):
            if page.both is None:
                if offset != page.offset:
                    raise Exception("Incorrect offset for page!")
                offset += 8
                for x in [page.zero, page.one]:
                    if x.both is None:
                        # This item points to another page
                        f.write(struct.pack("!Q", x.offset*2)[-field_size:])
                    else:
                        # Points to a data page, add one so we know it's a data page
                        f.write(struct.pack("!Q", valid_pages[x.both]*2+1)[-field_size:])

        # Write out the data pages, in order
        valid_pages = [(k, v) for k, v in valid_pages.items()]
        valid_pages.sort(key=lambda x: x[1])
        for key, target_offset in valid_pages:
            if offset != target_offset:
                raise Exception("Incorrect offset for page!")
            # Data pages are two bytes for the length, followed by the data
            f.write(struct.pack("!H", len(key)) + key)
            offset += len(key) + 2

def lookup_ip(db_file, ip):
    # Lookup an IP
    # First off, see if it's IPv6
    ipv6 = ":" in ip
    # Decode the IP to a byte string, add a bit to the front to pick the right page
    ip = (b'\xff' if ipv6 else b'\x00') + socket.inet_pton(socket.AF_INET6 if ipv6 else socket.AF_INET, ip)

    with open(db_file, "rb") as f:
        f.seek(len(COOKIE))
        # Get the size of a field
        _, field_size, _ = struct.unpack("!HHH", f.read(6))

        # For each bit in the IP, starting at byte #7, lookup which page to use
        bit = 6
        offset = 128 * 2
        # While at an even number, lookup the page
        while (offset % 2) == 0:
            bit += 1
            # Seek to the right offset, and move to the page for the give bit
            f.seek((offset // 2) + (((ip[bit // 8] >> (7 - (bit % 8))) & 1) * field_size))
            # Read the next offset
            offset = struct.unpack("!Q", b"\x00" * (8-field_size) + f.read(field_size))[0]

        # All done, so go ahead and read the data size
        f.seek(offset // 2)
        str_len = struct.unpack("!H", f.read(2))[0]
        # And read all of the data
        temp = f.read(str_len)
        ret = []
        # Decode the data into a simple array of dicts to return
        for item in temp.split(b"\x01"):
            if len(item) > 0:
                item = item.split(b'\x00')
                item = [x.decode("utf-8") for x in item]
                item_dict = {"source": item[0]}
                if len(item[1]) > 0:
                    item_dict['service'] = item[1]
                if len(item[2]) > 0:
                    item_dict['region'] = item[2]
                if len(item[3]) > 0:
                    item_dict['prefix'] = item[3]
                ret.append(item_dict)
        return ret

def test_data(fn):
    # Just show simple output for some test IPs
    test_ips = [
        '2600:1ff2:4000::', 
        '34.80.0.0', 
        '2600:1900:4030::', 
        '40.126.0.0', 
        '2a01:111:f403:f910::', 
        '127.1.2.7', 
        '::1', 
        '8.8.8.8',
    ]
    for ip in test_ips:
        print(f"-- Testing {ip} --")
        data = lookup_ip(fn, ip)
        if len(data) == 0:
            print("(nothing found)")
        else:
            for item in data:
                print(json.dumps(item))

def main():
    fn = os.path.join("data", "cloud_db.dat")
    create_db(fn)
    test_data(fn)

if __name__ == "__main__":
    main()
