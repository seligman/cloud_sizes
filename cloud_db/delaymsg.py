#!/usr/bin/env python3

from datetime import datetime, timedelta
from sys import stdout
import sys
if sys.version_info >= (3, 11): from datetime import UTC
else: import datetime as datetime_fix; UTC=datetime_fix.timezone.utc

class DelayMsg:
    def __init__(self, delay=5, show_all=False, log_format="Time", single_line=False, file=stdout):
        if log_format.lower() not in {"time", "timer", "none"}:
            raise Exception("Use 'Time' or 'Timer' for the log format")
        self.file = file
        self.start = datetime.now(UTC).replace(tzinfo=None)
        self.log_format = log_format.lower()
        self.next_msg = datetime.now(UTC).replace(tzinfo=None)
        self.delay = delay
        self.show_all = show_all
        self.single_line = single_line
        self.last_msg = ""

    def __call__(self, value):
        self.show(value)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kargs):
        self.finalize()

    def show(self, value):
        now = datetime.now(UTC).replace(tzinfo=None)
        if now >= self.next_msg or self.show_all:
            if not stdout.isatty():
                return

            end, flush, begin = "\n", False, ""
            if self.single_line:
                end, flush = "", True
                begin = "\r" + " " * len(self.last_msg) + "\r"
            if self.log_format == "timer":
                self.last_msg = show_timer(value, self.start, end=end, flush=flush, begin=begin, file=self.file)
            elif self.log_format == "time":
                self.last_msg = show(value, end=end, flush=flush, begin=begin, file=self.file)
            elif self.log_format == "none":
                self.last_msg = value
                print(begin + value, end=end, flush=flush, file=self.file)
            while now >= self.next_msg:
                self.next_msg += timedelta(seconds=self.delay)

    def finalize(self):
        if self.single_line and len(self.last_msg):
            print("\r" + " " * len(self.last_msg) + "\r", end="", flush=True, file=self.file)

    def force(self, value):
        now = datetime.now(UTC).replace(tzinfo=None)
        if self.log_format == "timer":
            show_timer(value, self.start, file=self.file)
        elif self.log_format == "time":
            show(value, file=self.file)
        elif self.log_format == "none":
            print(value, file=self.file)
        while now >= self.next_msg:
            self.next_msg += timedelta(seconds=self.delay)

    def time_to_show(self):
        return datetime.now(UTC).replace(tzinfo=None) >= self.next_msg

class TempMsg:
    def __init__(self):
        self.last = ""

    def __call__(self, value):
        self.show(value, temp=True)
    
    def show(self, value, temp=False):
        if not stdout.isatty():
            return

        value = datetime.now(UTC).replace(tzinfo=None).strftime("%d %H:%M:%S: ") + value
        if len(self.last) > 0:
            extra = len(self.last) - len(value)
            if extra > 0:
                print("\b" * extra + " " * extra + "\r" + value, end="" if temp else None, flush=True)
            else:
                print("\r" + value, end="" if temp else None, flush=True)
        else:
            print(value, end="" if temp else None, flush=True)
        self.last = value if temp else ""

    def clear(self):
        if len(self.last):
            print("\r" + " " * len(self.last) + "\r", end="", flush=True)
            self.last = ""

    def __enter__(self):
        return self

    def __exit__(self, *args, **kargs):
        self.clear()

def show(value, end="\n", flush=False, begin="", file=stdout):
    msg = f'{datetime.now(UTC).replace(tzinfo=None).strftime("%d %H:%M:%S")}: {value}'
    print(begin + msg, end=end, flush=flush, file=file)
    return msg

def show_timer(value, start, end="\n", flush=False, begin="", file=stdout):
    secs = int((datetime.now(UTC).replace(tzinfo=None) - start).total_seconds())
    msg = f'{secs // 3600}:{(secs // 60) % 60:02d}:{secs % 60:02d}: {value}'
    print(begin + msg, end=end, flush=flush, file=file)
    return msg

if __name__ == '__main__':
    print("This module is not meant to be run directly")
