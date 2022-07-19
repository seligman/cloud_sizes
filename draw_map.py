#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont
from netaddr import IPSet, IPNetwork
import gzip
import json
import sys
import os


def hilbert_xy(side_size, offset):
    x, y = 0, 0
    t = offset
    s = 1
    while s < side_size:
        rx = 1 & int(t / 2)
        ry = 1 & (t ^ rx)
        x, y = hilbert_rotate(s, rx, ry, x, y)
        x += s * rx
        y += s * ry
        t = int(t / 4)
        s *= 2

    return x, y


def hilbert_rotate(n, rx, ry, x, y):
    if ry == 0:
        if rx == 1:
            x = n-1 - x
            y = n-1 - y
            
        x, y = y, x
    return x, y


def main():
    colors = {
        'aws': (238, 108, 16),
        'azure': (2, 88, 211),
        'google': (50, 163, 80),
        'private': (40, 40, 40),
        'none': (0, 0, 0),
    }

    # Dump out the reserved ranges, these are can never be used.  Well, probably never.
    ranges = {
        'private': IPSet([IPNetwork(x) for x in [
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
        ]])}

    # Load some interesting IPv4 ranges
    for cur in ['aws', 'azure', 'google']:
        with gzip.open(os.path.join("data", f"data_{cur}.json.gz")) as f:
            data = json.load(f)
            ranges[cur] = IPSet([IPNetwork(x) for x in data['v4']])

    # Draw a very large map, we'll shrink it down later
    side_size = 2048
    im = Image.new('RGB', (side_size, side_size))
    pixels = [[] for _ in range(side_size * side_size)]
    curve_len = side_size ** 2
    per_pix = (256 ** 4) // curve_len

    # For each cidr in each range, map out which pixels it touches
    for cur, ips in ranges.items():
        for cidr in ips.iter_cidrs():
            if (cidr.first // per_pix) == (cidr.last // per_pix):
                # This cidr touches only one pixel, just note how many
                # IPs are in this pixel, in case another CIDR also intersects
                # with this pixel in case it should be the color used
                i = cidr.first // per_pix
                x, y = hilbert_xy(side_size, i)
                pixels[y * side_size + x].append([(cidr.last - cidr.first + 1), cur])
            else:
                # This cidr touches more than one pixel, figure out how big the first
                # and last pixel need to be
                first_size = 0 if (cidr.first % per_pix == 0) else (per_pix - (cidr.first % per_pix))
                last_size = 0 if ((cidr.last + 1) % per_pix == 0) else ((cidr.last + 1) % per_pix)
                first = cidr.first if (cidr.first % per_pix == 0) else cidr.first + first_size
                last = ((cidr.last + 1) if ((cidr.last + 1) % per_pix == 0) else (cidr.last + 1) - last_size)
                if first_size > 0:
                    # If the first pixel is a partial one, note it
                    i = (first - per_pix) // per_pix
                    x, y = hilbert_xy(side_size, i)
                    pixels[y * side_size + x].append([first_size, cur])
                if last_size > 0:
                    # And a partial last one
                    i = last // per_pix
                    x, y = hilbert_xy(side_size, i)
                    pixels[y * side_size + x].append([last_size, cur])
                for i in range(first // per_pix, last // per_pix):
                    # All the onese in between get per_pix, our max value, noted
                    x, y = hilbert_xy(side_size, i)
                    pixels[y * side_size + x].append([per_pix, cur])

    # Turn the pixels into colors
    for i, pix in enumerate(pixels):
        if len(pix) == 0:
            # Nobody claimed this pixel, just use a background color
            pixels[i] = colors["none"]
        elif len(pix) == 1:
            # Only one thing claimed this pixel, use its color
            pixels[i] = colors[pix[0][1]]
        else:
            # More than one thing claimed this pixel, find the biggest one, it wins
            pix.sort(reverse=True, key=lambda x:x[0])
            pixels[i] = colors[pix[0][1]]

    im.putdata(pixels)
    im = add_labels(im, colors)
    im.save(sys.argv[1])


def add_labels(im, colors):
    # Add some labels to the chart
    final = Image.new('RGB', (850*4, 542*4))
    dr = ImageDraw.Draw(final)
    fnt = ImageFont.truetype(os.path.join("images", "SourceSansPro-Bold.ttf"), 15 * 4)
    dr.rectangle((0, 0, final.width, final.height), (30, 30, 30))
    dr.rectangle((10*4, 10*4, 532*4, 532*4), (150, 150, 150))

    labels = [["AWS", "aws"], ["Azure", "azure"], ["Google Cloud", "google"], ["(Reserved/Private IPs)", "private"]]
    max_h = 0
    for label, color in labels:
        _x, _y, _w, h = fnt.getbbox(label)
        max_h = max(max_h, int(h))

    y = 50*4
    for label, color in labels:
        _x, _y, _w, h = fnt.getbbox(label)
        dr.rectangle((560*4, y, 600*4, y + max_h), (150, 150, 150))
        dr.rectangle((562*4, y+2*4, 598*4, y + max_h - 2*4), colors[color])
        dr.text((620*4, y), label, (255, 255, 255), fnt)
        y += int(max_h * 1.5)

    final.paste(im, (15*4, 15*4))
    return final.resize((final.width // 4, final.height // 4))


if __name__ == "__main__":
    main()
