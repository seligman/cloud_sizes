#!/usr/bin/env python3

from importlib.util import spec_from_file_location, module_from_spec
import os
import sys

def approximate_count(val):
    val = val.size
    thousands = [
        ('undecillion', 10 ** 36),
        ('decillion', 10 ** 33),
        ('nonillion', 10 ** 30),
        ('octillion', 10 ** 27),
        ('septillion', 10 ** 24),
        ('sextillion', 10 ** 21),
        ('quintillion', 10 ** 18),
        ('quadrillion', 10 ** 15),
        ('trillion', 10 ** 12),
        ('billion', 10 ** 9),
        ('million', 10 ** 6),
        ('thousand', 10 ** 3),
    ]
    for name, scale in thousands:
        if val >= scale * 0.9:
            return f"{val / scale:6.2f} {name}"
    return f"{val:3d}"

def main():
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
                name, pretty, v4, v6, show = ips.get_and_parse()
                print(f"IPv4: {approximate_count(v4):<16} / IPv6: {approximate_count(v6):<16}", flush=True)
            except Exception as ex:
                print("FAILED: " + str(ex), flush=True)

if __name__ == "__main__":
    main()