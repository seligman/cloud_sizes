#!/usr/bin/env python3

# Create a single database of all of the cloud providers, and organize
# the data in this database to make lookups quick, and possible to
# accomplish in a language and library independent fashion.
#
# For a stand alone version of this tool's lookup functionality, see
#   https://github.com/seligman/seligman.github.io/blob/master/cloud-ips/lookup_ip_address.py
# And for a online version of the lookup tool, please see
#   https://seligman.github.io/cloud-ips/

from collections import deque
from datetime import datetime
from netaddr import IPNetwork
import gzip
import json
import os
import socket
import struct

BASE_DIR = os.path.split(__file__)[0]
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

def add_aws(targets, sources, short_name, long_name):
    # Add all AWS ranges to our current working set
    sources[short_name] = long_name
    with gzip.open(os.path.join(BASE_DIR, "data", "raw_aws.json.gz")) as f:
        data = json.load(f)

    for cur in data["prefixes"] + data["ipv6_prefixes"]:
        prefix = cur.get("ip_prefix", cur.get("ipv6_prefix"))
        add_data(short_name, targets, prefix, cur["service"], cur["region"])

def add_google(targets, sources, short_name, long_name):
    # Add all Google ranges to our current working set
    sources[short_name] = long_name
    with gzip.open(os.path.join(BASE_DIR, "data", "raw_google.json.gz")) as f:
        data = json.load(f)

    for cur in data['prefixes']:
        prefix = cur.get("ipv4Prefix", cur.get("ipv6Prefix"))
        add_data(short_name, targets, prefix, cur["service"], cur["scope"])

def add_azure(targets, sources, short_name, long_name):
    # Add all Azure ranges to our current working set
    sources[short_name] = long_name
    with gzip.open(os.path.join(BASE_DIR, "data", "raw_azure.json.gz")) as f:
        data = json.load(f)

    for group in data["values"]:
        for prefix in group['properties']['addressPrefixes']:
            add_data(
                short_name, targets, prefix, 
                group["properties"].get("systemService", ""), 
                group["properties"].get("region", ""),
            )

def add_private(targets, sources, short_name, long_name):
    # Add all private IPs from a hardcoded list
    sources[short_name] = long_name
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
        add_data(short_name, targets, prefix, desc, "")

def add_other(targets, source):
    # Add IPs from a pre-parsed list of data
    with gzip.open(os.path.join(BASE_DIR, "data", f"data_{source}.json.gz")) as f:
        data = json.load(f)

    for prefix in data['v4'] + data['v6']:
        add_data(source, targets, prefix, "", "")

def create_db(target_file):
    # The main page includes sub pages for IPv4 and IPv6
    targets = Level(both=None, zero=Level(), one=Level(), offset=0)

    # This sources dict will end up in the database
    sources = {
        "cloudflare": "Cloudflare", 
        "digitalocean": "DigitalOcean", 
        "facebook": "Facebook", 
        "hetzner": "Hetzner", 
        "icloudprov": "iCloud", 
        "linode": "Linode", 
        "oracle": "Oracle", 
        "vultr": "Vultr", 
    }
    for source in sources:
        add_other(targets, source)
    # Each of these helpers will add the description to the sources dictionary
    add_aws(targets, sources, "aws", "AWS")
    add_google(targets, sources, "google", "Google")
    add_azure(targets, sources, "azure", "Azure")
    add_private(targets, sources, "private", "Private IP")

    # Helper to encode a value to a byte string
    def encode_data(value):
        ret = b''
        if isinstance(value, dict):
            if len(value) >= 63: raise Exception()
            ret += struct.pack('!B', (len(value) << 2) | 1)
            for k, v in value.items():
                ret += encode_data(k)
                ret += encode_data(v)
        elif isinstance(value, list):
            if len(value) >= 63: raise Exception()
            ret += struct.pack('!B', (len(value) << 2) | 2)
            for v in value:
                ret += encode_data(v)
        else:
            value = value.encode("utf-8")
            if len(value) >= 63:
                ret += struct.pack('!BH', (63 << 2) | 3, len(value))
            else:
                ret += struct.pack('!B', (len(value) << 2) | 3)
            ret += value
        return ret

    # Figure out all of the page offsets
    valid_pages = {}
    offset = 128
    for page in enum_pages(targets):
        if page.both is None:
            page.offset = offset
            offset += 8
        else:
            key = encode_data(page.both)
            page.both = key
            valid_pages[key] = 0

    # Add one final page with some information
    info_page = encode_data({
        "sources": sources,
        "built": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    })
    valid_pages[info_page] = 0

    # Store the offsets for the data pages
    for key in valid_pages:
        valid_pages[key] = offset
        offset += len(key)

    field_size = 1
    offset *= 2
    while offset >= 256:
        field_size += 1
        offset /= 256
    
    # Write out all of the data
    with open(target_file, "wb") as f:
        header = COOKIE
        header += struct.pack("!HHQ", 2, field_size, valid_pages[info_page])
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
            f.write(key)
            offset += len(key)

def lookup_ip(db_file, ip):
    # Lookup an IP

    # First off, see if it's IPv6
    ipv6 = ":" in ip
    # If IP is "info", then we just return the info dictionary, don't decode that value
    if ip != "info":
        # Decode the IP to a byte string, add a bit to the front to pick the right page
        ip = (b'\xff' if ipv6 else b'\x00') + socket.inet_pton(socket.AF_INET6 if ipv6 else socket.AF_INET, ip)

    # Little helper to wrap a file object, this lets us open a file if it's passed in
    # as a string, or just use a file object, without closing it at the end, if one
    # is passed in
    class FileHelper:
        def __init__(self):
            pass
        def __enter__(self, *args, **kargs):
            if isinstance(db_file, str):
                self.f = open(db_file, "rb")
                return self.f
            else:
                return db_file
        def __exit__(self, *args, **kargs):
            if isinstance(db_file, str):
                self.f.close()

    with FileHelper() as f:
        # Seek past the header's cookie
        f.seek(21)
        # Get the size of a field, and the location of the info dictionary
        _, field_size, info_loc = struct.unpack("!HHQ", f.read(12))

        # Ok, we have the IP address as a list of bits, along with an extra
        # byte at the beggining.  We only care about the last bit from
        # that extra byte, so start at bit 6, which immediatly gets incremented
        # to the last bit of the first byte.
        bit = 6
        # The first offset is the first page, which is 128 bytes into the data
        # structure, times two, since the even/odd value encodes if this is
        # a page for a branch decision, or a page for a leaf information
        offset = 128 * 2

        if ip != "info":
            # While at an even number, lookup the branch decision page
            while (offset % 2) == 0:
                bit += 1
                # Seek to the offset for the given bit, and move to its page
                f.seek((offset // 2) + (((ip[bit // 8] >> (7 - (bit % 8))) & 1) * field_size))
                # Read offset value for the given bit's value
                offset = struct.unpack("!Q", b"\x00" * (8-field_size) + f.read(field_size))[0]

        def decode(f, offset):
            # Helper to decode a value, understands dicts, lists, and strings
            f.seek(offset)
            val = struct.unpack("!B", f.read(1))[0]
            offset += 1
            if (val & 3) == 1:
                # A dictionary of 63 items or less
                val >>= 2
                ret = {}
                for _ in range(val):
                    k, offset = decode(f, offset)
                    v, offset = decode(f, offset)
                    ret[k] = v
                return ret, offset
            elif (val & 3) == 2:
                # A list of 63 items or less
                val >>= 2
                ret = []
                for _ in range(val):
                    v, offset = decode(f, offset)
                    ret.append(v)
                return ret, offset
            elif (val & 3) == 3:
                # A string
                val >>= 2
                if val == 63:
                    # If it has 63 bytes or more of data, the length is stored in another field
                    val = struct.unpack("!H", f.read(2))[0]
                    offset += 2
                v = f.read(val)
                offset += val
                return v.decode("utf-8"), offset
            else:
                raise Exception()

        # Pull out the info dictionary for this database
        info_dict, _ = decode(f, info_loc)

        # If we asked for the info dictionary, just return all of it
        if ip == "info":
            return info_dict

        # Load the information for this IP to return
        temp, _ = decode(f, offset // 2)

        # Decode the data into a simple array of dicts to return
        ret = []
        for item in temp:
            item_dict = {"source": info_dict["sources"].get(item[0], item[0])}
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
        '34.80.0.0', 
        '2a01:111:f403:f910::', 
        '127.1.2.7', 
        '8.8.8.8',
    ]
    with open(fn, "rb") as f:
        info = lookup_ip(f, "info")
        print(f" Database last built: {info['built']}")
        for ip in test_ips:
            data = lookup_ip(f, ip)
            if len(data) == 0:
                print(f" {ip} - not found")
            else:
                for item in data:
                    print(f" {ip} - {json.dumps(item)}")

def show_info(value):
    print(datetime.utcnow().strftime("%d %H:%M:%S") + ": " + value)

def main():
    fn = os.path.join("data", "cloud_db.dat")
    show_info("Building database...")
    create_db(fn)
    show_info("Testing database...")
    test_data(fn)
    show_info("All done")

if __name__ == "__main__":
    main()
