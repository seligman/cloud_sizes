#!/usr/bin/env python3

import os
import hashlib
import io

MULTIPART_THRESHOLD = 8388608
MULTIPART_CHUNKSIZE = 8388608
PART_LIMIT = 10000

def calculate_etag(file, progress_callback=None, include_sha256=False):
    chunk_buffer = bytearray(MULTIPART_CHUNKSIZE)
    chunk_mv = memoryview(chunk_buffer)

    if include_sha256:
        sha = hashlib.sha256()
    else:
        sha = None

    filesize = os.path.getsize(file)
    if filesize >= MULTIPART_THRESHOLD:
        if PART_LIMIT is not None:
            local_chunksize = MULTIPART_CHUNKSIZE
            while True:
                parts, extra = divmod(filesize, local_chunksize)
                if extra > 0: parts += 1
                if parts > PART_LIMIT:
                    local_chunksize *= 2
                else:
                    break
            if MULTIPART_CHUNKSIZE != local_chunksize:
                chunk_buffer = bytearray(local_chunksize)
                chunk_mv = memoryview(chunk_buffer)
        chunk_hashes = []
        with io.open(file, "rb", buffering=0) as f:
            while True:
                read = f.readinto(chunk_buffer)
                if read == 0: break
                if progress_callback: progress_callback(read)
                chunk_hashes.append(hashlib.md5(chunk_mv[:read]).digest())
                if sha: sha.update(chunk_mv[:read])
        ret = f"{hashlib.md5(b''.join(chunk_hashes)).hexdigest()}-{len(chunk_hashes)}"
    else:
        md5 = hashlib.md5()
        with io.open(file, "rb", buffering=0) as f:
            while True:
                read = f.readinto(chunk_buffer)
                if read == 0: break
                if progress_callback: progress_callback(read)
                md5.update(chunk_mv[:read])
                if sha: sha.update(chunk_mv[:read])
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
