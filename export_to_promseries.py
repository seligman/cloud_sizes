import json
from datetime import datetime

from mimir_remote_writer import dt2ts


def read_summary_jsonl(file_path):
    metrics = []
    with open(file_path, 'r') as file:
        for line in file:
            metrics.append(json.loads(line))
    return metrics


def construct_prometheus_series(lines):
    prometheus_series = []
    for data in lines:
        timestamp = datetime.strptime(data['_'], '%Y-%m-%d %H:%M:%S')
        timestamp = dt2ts(timestamp) * 1000
        for provider, values in data.items():
            # Skip the timestamp field
            if provider == '_':
                continue
            ipv4_count = values[0]
            series = f'cloud_provider_ips_pool_size{{name="{provider}",type="v4"}} {ipv4_count} {timestamp}'
            prometheus_series.append(series)
            ipv6_count = values[1]
            series = f'cloud_provider_ips_pool_size{{name="{provider}",type="v6"}} {ipv6_count} {timestamp}'
            prometheus_series.append(series)
    return prometheus_series


def main():
    metrics = read_summary_jsonl("data/summary.jsonl")
    prometheus_series = construct_prometheus_series(metrics)
    with open('export.txt', 'w') as f:
        for serie in prometheus_series:
            f.write(serie + "\n")
        f.write("# EOF")


if __name__ == '__main__':
    main()
