# Track IPs for Cloud Providers

A repo to track the relative size, in terms of IP addresses, for different services using relatively large IPv4 pools, such as cloud providers.
If you want to look up an IP address, you can see if it's from any of the cloud providers using [this tool](https://cloud-ips.s3-us-west-2.amazonaws.com/index.html) or using [this Python script](https://github.com/seligman/cloud_sizes/blob/master/cloud_db/lookup_ip_address.py).

To get a daily update of the counts:

[![RSS Icon](images/rss_badge.svg)](https://raw.githubusercontent.com/seligman/cloud_sizes/master/rss.xml)

Currently, the providers have this many IPv4 addresses, shown here with a logarithmic scale:

![Compared](images/main.png)

Over time, each item's day to day change in percent:

![aws](images/history_aws.png)<br>
![azure](images/history_azure.png)<br>
![cloudflare](images/history_cloudflare.png)<br>
![digitalocean](images/history_digitalocean.png)<br>
![facebook](images/history_facebook.png)<br>
![flyio](images/history_flyio.png)<br>
![google](images/history_google.png)<br>
![github](images/history_github.png)<br>
![hetzner](images/history_hetzner.png)<br>
![icloudprov](images/history_icloudprov.png)<br>
![linode](images/history_linode.png)<br>
![oracle](images/history_oracle.png)<br>
![ovhcloud](images/history_ovhcloud.png)<br>
![vultr](images/history_vultr.png)<br>


An IP map of the big providers, in the style of [XKCD's map of the Internet](https://xkcd.com/195/):

![map](images/map.png)

### Remote write to Mimir

~~~shell
source venv/bin/activate
protoc prometheus.proto --python_out=.
export MIMIR_URL=""
export MIMIR_USERNAME=""
export MIMIR_PASSWORD=""
export FULL_EXPORT=false #true
python mimir_remote_writer.py 
~~~
