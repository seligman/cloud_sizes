import calendar
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from prometheus_pb2 import (
    WriteRequest
)

try:
    import snappy
except ImportError:
    print("Error: python-snappy not found. Please install it with:")
    print("pip install python-snappy")
    sys.exit(1)


def dt2ts(dt):
    """Converts a datetime object to UTC timestamp
    naive datetime will be considered UTC.
    """
    return calendar.timegm(dt.utctimetuple())


def send_to_mimir(timestamp: datetime, provider: str,type:str, value: int, mimir_url: str, auth: tuple) -> None:
    """
    Send metric to Mimir using HTTP POST with Snappy compression
    Raises exception if the request fails
    """
    write_request = WriteRequest()

    series = write_request.timeseries.add()

    # name label always required
    label = series.labels.add()
    label.name = "__name__"
    label.value = "cloud_provider_ips_pool_size"

    # as many labels you like
    label = series.labels.add()
    label.name = "name"
    label.value = provider

    label = series.labels.add()
    label.name = "type"
    label.value = type

    sample = series.samples.add()
    sample.value = value  # your count?
    sample.timestamp = dt2ts(timestamp) * 1000

    uncompressed = write_request.SerializeToString()
    compressed = snappy.compress(uncompressed)

    headers = {
        "Content-Encoding": "snappy",
        "Content-Type": "application/x-protobuf",
        "X-Prometheus-Remote-Write-Version": "0.1.0",
        "User-Agent": "metrics-worker"
    }
    try:
        response = requests.post(mimir_url, headers=headers, auth=auth,
                                 data=compressed)
    except Exception as e:
        raise RuntimeError(f"Error sending metric for {provider}: {e}")

    if response.status_code != 200:
        raise RuntimeError(f"Error sending metric for {provider}: {response.status_code} - {response.text}")


def process_json_data(data: dict, mimir_url: str, username: str, password: str,
                      line_number: Optional[int] = None) -> None:
    """
    Process a single JSON data entry and send metrics to Mimir
    """
    try:
        timestamp = datetime.strptime(data['_'], '%Y-%m-%d %H:%M:%S')

        # Process each provider's data
        for provider, values in data.items():
            # Skip the timestamp field
            if provider == '_':
                continue

            # Extract the IPv4 count (first element of the array)
            if isinstance(values, list) and len(values) > 0:
                ipv4_count = values[0]
                try:
                    # Send metric to Mimir
                    send_to_mimir(
                        timestamp=timestamp,
                        provider=provider,
                        type="v4",
                        value=ipv4_count,
                        mimir_url=f"{mimir_url}/api/v1/push",
                        auth=(username, password)
                    )
                    print(f"Successfully sent metric for {provider}: {ipv4_count}")

                except Exception as e:
                    print(f"Error at line {line_number}: {str(e)}" if line_number else f"Error sending metric: {str(e)}")

                # Add a small delay to avoid overwhelming the server
                time.sleep(0.1)

                ipv6_count = values[1]
                try:
                    # Send metric to Mimir
                    send_to_mimir(
                        timestamp=timestamp,
                        provider=provider,
                        type="v6",
                        value=ipv6_count,
                        mimir_url=f"{mimir_url}/api/v1/push",
                        auth=(username, password)
                    )
                    print(f"Successfully sent metric for {provider}: {ipv4_count}")

                except Exception as e:
                    print(f"Error at line {line_number}: {str(e)}" if line_number else f"Error sending metric: {str(e)}")


                # Add a small delay to avoid overwhelming the server
                time.sleep(0.1)

    except Exception as e:
        if not isinstance(e, json.JSONDecodeError):  # Don't wrap JSON errors
            error_msg = f"Unexpected error at line {line_number}: {e}" if line_number else f"Unexpected error processing data: {e}"
            print(error_msg)
        raise


def process_file(file_path: Path, mimir_url: str, username: str, password: str) -> None:
    """
    Process the entire JSONL file and send metrics to Mimir
    Stops processing if any error occurs
    """
    with open(file_path, 'r') as f:
        for line_number, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                process_json_data(data, mimir_url, username, password, line_number)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON at line {line_number}: {e}")
                sys.exit(1)
            except Exception as e:
                sys.exit(1)  # Error message already printed in process_json_data

def process_all_lines(file_path: Path, mimir_url: str, username: str, password: str) -> None:
    """
    Process only the last line of the JSONL file and send metrics to Mimir
    Stops processing if any error occurs
    """
    try:
        # Read the last line of the file
        with open(file_path, 'r') as f:

          for l in f.readlines():
            try:
                data = json.loads(l)
                process_json_data(data, mimir_url, username, password)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON in last line: {e}")
            except Exception as e:
                pass

    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

def process_last_line(file_path: Path, mimir_url: str, username: str, password: str) -> None:
    """
    Process only the last line of the JSONL file and send metrics to Mimir
    Stops processing if any error occurs
    """
    try:
        # Read the last line of the file
        with open(file_path, 'r') as f:
            last_line = find_last_line(f)

        if last_line == -1:
            return

            # Process the last line
        try:
            data = json.loads(last_line.strip())
            process_json_data(data, mimir_url, username, password)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON in last line: {e}")
            sys.exit(1)
        except Exception as e:
            sys.exit(1)  # Error message already printed in process_json_data

    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)


def find_last_line(f):
    # Move cursor to the end of file
    f.seek(0, 2)
    file_size = f.tell()

    # If file is empty, return
    if file_size == 0:
        print("File is empty")
        return -1
    # Start from the end and read backwards until we find a newline
    position = file_size - 1
    while position >= 0:
        f.seek(position)
        char = f.read(1)
        if char == '\n' and position != file_size - 1:
            # Found the last complete line
            last_line = f.readline()
            break
        position -= 1
    else:
        # If we didn't find a newline, read the entire file as one line
        f.seek(0)
        last_line = f.readline()
    return last_line


def main():
    # Configuration
    MIMIR_URL = os.getenv("MIMIR_URL")  # Replace with your Mimir URL
    USERNAME = os.getenv("MIMIR_USERNAME")
    PASSWORD = os.getenv("MIMIR_PASSWORD")
    FILE_PATH = Path("data/summary.jsonl")
    FULL = os.getenv("FULL_EXPORT")

    if not FILE_PATH.exists():
        print(f"Error: File not found at {FILE_PATH}")
        sys.exit(1)

    print(f"Starting to process {FILE_PATH}")
    if FULL:
        process_all_lines(FILE_PATH, MIMIR_URL, USERNAME, PASSWORD)
    else:
        process_last_line(FILE_PATH, MIMIR_URL, USERNAME, PASSWORD)
    print("Processing complete")


if __name__ == "__main__":
    main()
