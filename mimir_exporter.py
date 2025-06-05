import os
import time

from prometheus_client import start_http_server, Gauge

from get_all import get_data

# Define the Prometheus Gauge metric
cloud_provider_ips_pool_size = Gauge('cloud_provider_ips_pool_size', 'Size of IP pool for cloud providers', ['name', 'type'])

def export_data():
    # Fetch data
    data = get_data()

    # Process and export data
    for provider, sizes in data.items():
        if provider != '_':  # Skip the timestamp entry
            v4_size, v6_size = sizes
            cloud_provider_ips_pool_size.labels(name=provider, type='IPv4').set(v4_size)
            cloud_provider_ips_pool_size.labels(name=provider, type='IPv6').set(v6_size)

if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(9800)
    # Get the environment variable, default to '3600' if not defined
    sleep_duration_str = os.getenv('SLEEP_DURATION', '3600')
    # Convert the environment variable to an integer
    try:
        sleep_duration = int(sleep_duration_str)
    except ValueError:
        # If conversion fails, default to 3600
        sleep_duration = 3600
    # Ensure the sleep duration is not less than 3600
    if sleep_duration < 3600:
        sleep_duration = 3600
    while True:
        export_data()
        time.sleep(sleep_duration)  # Sleep for 1h minutes
