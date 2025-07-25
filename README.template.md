# Track IPs for Cloud Providers

A repo to track the relative size, in terms of IP addresses, for different services using relatively large IPv4 pools, such as cloud providers.
If you want to look up an IP address, you can see if it's from any of the cloud providers using [this tool](https://cloud-ips.s3-us-west-2.amazonaws.com/index.html) or using [this Python script](https://github.com/seligman/cloud_sizes/blob/master/cloud_db/lookup_ip_address.py).

To get a daily update of the counts:

[![RSS Icon](images/rss_badge.svg)](https://raw.githubusercontent.com/seligman/cloud_sizes/master/rss.xml)

Currently, the providers have this many IPv4 addresses, shown here with a logarithmic scale:

![Compared](images/main.png)

Over time, each item's day to day change in percent:

[[history]]

An IP map of the big providers, in the style of [XKCD's map of the Internet](https://xkcd.com/195/):

![map](images/map.png)

### Export to mimir

To run and export data:ds

~~~shell
source venv/bin/activate
protoc prometheus.proto --python_out=.
python get_all.py
protoc prometheus.proto --python_out=.python mimir.py 
~~~

### Export to mimir

To run and export data:ds

~~~shell
source venv/bin/activate
protoc prometheus.proto --python_out=.
python get_all.py
protoc prometheus.proto --python_out=.python mimir.py 
~~~
