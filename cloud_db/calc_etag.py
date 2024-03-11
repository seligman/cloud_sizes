#!/usr/bin/env python3

import os
import hashlib
import io

__version__ = 3

MULTIPART_THRESHOLD = 8388608
MULTIPART_CHUNKSIZE = 8388608
PART_LIMIT = 10000

class FileHelper:
    def __init__(self, file):
        if isinstance(file, str):
            self.f = io.open(file, "rb", buffering=0)
            self.size = os.path.getsize(file)
            self.data = None
            self.off = 0
        else:
            self.f = None
            self.data = file
            self.size = len(file)
            self.off = 0
    
    def readinto(self, dest):
        if self.f is None:
            size = min(len(dest), len(self.data) - self.off)
            dest[0:size] = self.data[self.off:self.off+size]
            self.off += size
            return size
        else:
            return self.f.readinto(dest)
    
    def close(self):
        if self.f is not None:
            self.f.close()

def calculate_etag(file, progress_callback=None, include_sha256=False):
    chunk_buffer = bytearray(MULTIPART_CHUNKSIZE)
    chunk_mv = memoryview(chunk_buffer)

    if include_sha256:
        sha = hashlib.sha256()
    else:
        sha = None

    helper = FileHelper(file)
    if helper.size >= MULTIPART_THRESHOLD:
        if PART_LIMIT is not None:
            local_chunksize = MULTIPART_CHUNKSIZE
            while True:
                parts, extra = divmod(helper.size, local_chunksize)
                if extra > 0: parts += 1
                if parts > PART_LIMIT:
                    local_chunksize *= 2
                else:
                    break
            if MULTIPART_CHUNKSIZE != local_chunksize:
                chunk_buffer = bytearray(local_chunksize)
                chunk_mv = memoryview(chunk_buffer)
        chunk_hashes = []
        while True:
            read = helper.readinto(chunk_buffer)
            if read == 0: break
            if progress_callback: progress_callback(read)
            chunk_hashes.append(hashlib.md5(chunk_mv[:read]).digest())
            if sha: sha.update(chunk_mv[:read])
        helper.close()
        ret = f"{hashlib.md5(b''.join(chunk_hashes)).hexdigest()}-{len(chunk_hashes)}"
    else:
        md5 = hashlib.md5()
        while True:
            read = helper.readinto(chunk_buffer)
            if read == 0: break
            if progress_callback: progress_callback(read)
            md5.update(chunk_mv[:read])
            if sha: sha.update(chunk_mv[:read])
        helper.close()
        ret = md5.hexdigest()
    
    if sha:
        return ret, sha.hexdigest()
    else:
        return ret

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        print(f"Working on {sys.argv[1]}...")
        etag, sha = calculate_etag(sys.argv[1], include_sha256=True)
        print(f"ETag: {etag}")
        print(f"SHA256: {sha}")
    else:
        print(f"Usage: {os.path.split(__file__)[-1]} <filename>")
        exit(1)
