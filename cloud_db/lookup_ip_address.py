#!/usr/bin/env python3

# Use data from 
#   https://github.com/seligman/cloud_sizes
# For a online version of this tool, please see
#   https://cloud-ips.s3-us-west-2.amazonaws.com/index.html

from datetime import datetime, timedelta
from urllib.request import urlopen, Request
import json
import os
import re
import socket
import struct
import sys
if sys.version_info >= (3, 11): from datetime import UTC
else: import datetime as datetime_fix; UTC=datetime_fix.timezone.utc

# The URL of the data file
CLOUD_URL = "https://cloud-ips.s3-us-west-2.amazonaws.com/cloud_db.dat"

# Helper to download a copy of the database and save a local cached copy
def read_cache_local():
    fn = "lookup_ip_address.dat"
    # If the local copy is older than two weeks, pull down a fresh copy
    max_age = (datetime.now(UTC).replace(tzinfo=None) - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")

    if os.path.isfile(fn):
        f = open(fn, "rb")
        info = lookup_ip(f, "info")
        if info['built'] >= max_age:
            return f
        f.close()

    # Pull down the raw data
    # Output a status message as a JSON object so consumers can easily ignore it
    print(json.dumps({"info": f"Downloading cached cloud database from {CLOUD_URL}"}))
    with urlopen(CLOUD_URL) as f_src:
        with open(fn, "wb") as f_dest:
            while True:
                data = f_src.read(1048576)
                if len(data) == 0:
                    break
                f_dest.write(data)
    return open(fn, "rb")

# Helper to cache requests to a remote webserver
class read_cache_remote:
    def __init__(self):
        # Keep track of the current position
        self.offset = 0
        # And read half a megabyte at a time
        self.chunk_size = 524288
        self.buffers = {}

    def __enter__(self):
        # Nothing to do
        return self

    def __exit__(self, *args, **kwargs):
        # Nothing to close when we're done
        pass

    def seek(self, offset):
        # Move the offset location
        self.offset = offset

    def read(self, count):
        # Pull out the requested bytes
        offset = self.offset
        self.offset += count

        ret = b''
        while len(ret) < count:
            # Find the next chunk we need, read it if we haven't already, and get
            # the bytes out of it
            chunk = offset // self.chunk_size
            if chunk not in self.buffers:
                resp = urlopen(Request(CLOUD_URL, headers={
                    "Range": f"bytes={self.chunk_size * chunk}-{self.chunk_size * (chunk + 1) - 1}"
                }))
                self.buffers[chunk] = resp.read()
            temp = self.buffers[chunk][offset % self.chunk_size:offset % self.chunk_size+count]
            count -= len(temp)
            offset += len(temp)
            ret += temp

        return ret

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

def main():
    if len(sys.argv) == 1:
        print("Need to specify one or more IPs to lookup")
        exit(1)

    with read_cache_remote() as f:
        # Show the build date of the database
        info = lookup_ip(f, "info")
        print(json.dumps({"info": f"Database last built {info['built']}"}))

        for ip in sys.argv[1:]:
            # If something doesn't look like an IP, treat it as a FQDN and lookup the IP
            desc = None
            if re.match("^([0-9.]+|[0-9a-f:]+)$", ip):
                print(json.dumps({"info": f"Using '{ip}'"}))
            else:
                desc = ip
                # Look for something that looks like a URL
                m = re.match("^(http|https|ftp)://(?P<dn>[^/:]+)", ip)
                if m is not None:
                    ip = m.group('dn')
                # Try to perform a DNS query on the string
                try:
                    ip = socket.gethostbyname(ip)
                    print(json.dumps({"info": f"Using '{ip}' for '{desc}'"}))
                except Exception as e:
                    # Dump out errors
                    print(json.dumps({"ERROR": f"ERROR: {e} for {desc}"}))
                    ip = None
            if ip is not None:
                data = lookup_ip(f, ip)
            else:
                data = []
            if len(data) == 0:
                # Show that there's no IP, so we output something
                data.append({"warning": "Not found"})
            for row in data:
                # Add the IP to the return since we might lookup multiple values
                row["ip"] = ip
                if desc is not None:
                    row["desc"] = desc
                print(json.dumps(row)) 

if __name__ == "__main__":
    main()
