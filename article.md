# DNS Notify to Route53

This article presents a project that will allow Route53 domains to serve your public-facing needs while acting, essentially, as a slave domain server to your existing infrastructure. Using this project Route53 can be synchronized to changes signaled in DNS NOTIFY ([RFC 1996](https://datatracker.ietf.org/doc/html/rfc1996)) messages.

### The Objective

This project attempts one thing: to be the gateway between normal DNS and Route53. By normal, I mean the DNS that adheres to standards, specifically domain transfers and notify.

Plain and simple, for years I have wanted Route53 to house slave domains, nothing more. I want my masters to be where it is easy for me to change them. Then I want to use the significant infrastructure of somthing like AWS to publish the information publicly. You cannot do that with Route53, at least not with something as easy as a zone transfer.

### The Challenge

Because we want Route53 to be a slave, the only way to get zone information to Route53 is through the AWS API via a push. So, to put it in terms that will resonate with techo types, we need to translate domain notify and AXFR to boto3.

### Why

Why would I want to do this? Why not just use Godaddy or ClouDNS or Cloudflare to manage DNS? In the case of Godaddy, they are a sales and marketing machine, obnoxiously. Their interface is horrible for the functionally-focused. They keep trying to cram new things down my throat. I don't want them. Just let me do my work. I have never been a fan about AWS' interface. Any time a search bar is needed over navigation, things have gotten too big. ClouDNS is a little better, but far more costly than AWS once you scale.

I use the excellent [Technitium project](https://technitium.com/) to manage all domains, for us and all our clients. I have no affiliation with the project but it checks every box. It handles DNS flawlessly, allowing me to finially replace BIND. It has a great UI. It supplies good metrics, and it has an API if I want to automate things.

### How it Works

This project performs one core function. It compares the contents of one or more domains you manage to its slave counterpart on Route53, then performs a one-way synchronization, a push. For simplicity it does this by first generating three lists: add_resource_set, change, delete. It then applies them accordingly. It uses the standard AXFR to get primary domain information then uses boto3 to pull from and push to AWS.

At first start the project needs to bring everything to synchronization and so performs the above steps. If you do not run this as a daemon, that is all it does and exits. You could simply change to the project directory, run ./start.py and do nothing more. If you never change things, why devote a background process? Run it only when needed.

As a daemon, after first start, the project spawns a thread which establishes a listener on UDP port 53 to listen for the NOTIFY message from the primary DNS server(s). It also  spawns a thread that operates on a timer to request a transfer when needed to adhere to the zone's SOA refresh setting.

### Requirements

As written, this project uses **systemd** to establish itself as a service.

UDP port 53. This is the default port on which to listen to notifies. It can be changed in the config file.

outbound TCP. As per DNS standards, the actual transfer (AXFR) is initiated by this project over TCP, not the primary DNS server. It also needs outbound TCP to contact AWS.

permission to transfer. The IP of the machine hosting this project must have permission on the primary DNS server to perform the transfer. This is likely a per-domain permission.

permission to push. The IAM credentials need the permission to change existing domains. We are never trying to create or delete a domain. That is something, I think should be performed manually for security reasons, unless you are at scale.

pre-established AWS CLI with IAM credentials. This project uses boto3 and assumes the connection will "just happen".  Setting up the credentials is not handled in the code. The lines below should get you there.

```shell
apt install -y awscli
aws configure
```

### install and run

assuming your rerequisites exist, this is all you need.

```shell
git clone
assets/install_all.sh
```

### Expectations

Personally, I have an endless list of things to do. This is a project of need, not love. What does that mean? When it suits my needs I probably won't make many more changes to it. This effort took two days. I should not complain.

This project is sloppy. I had an idea of what I wanted to do. That got wrecked by Route53's concept of consolidating multiple dns records in to a ResourceRecords collection, or a ResourceRecordSet. It's not that they are wrong. It's part of [RFC 2181](https://datatracker.ietf.org/doc/html/rfc2181). It's just that I've spent over 20 years working with BIND. Every entry is its own record. It thinks records, not record sets. The DNS_zone_resource_set class I created is a shim put in post-design to accomodate record sets. If I rewrote this with the record set design in mind (using dnspyton's axfr.iterate_rdatasets rather than axfr.iterate_rdatas) the code would work the same way but look a lot nicer.

There is no documentation, no exception handling, no tests. Like I said, I have no time. Maybe I will change that.

This project was deployed on Debian 12. Python 3.11 is the standard for that distro. So that is what this project was written with.

I hate Docker. I love LXC. Don't expect a container any time soon.

### Debugging

If you want debug-level logging from this project, execute the following from the project directory:

```shell
sed -i 's/^Environment=.*$/Environment="DEBUG=1"/' assets/dnsnotify2route53.service

./assets/install.sh
systemctl restart dnsnotify2route53.service;systemctl status dnsnotify2route53.service
```

To turn debugging off execute this:

```shell
sed -i 's/^Environment=.*$/Environment=/' assets/dnsnotify2route53.service

./assets/install.sh
systemctl restart dnsnotify2route53.service;systemctl status dnsnotify2route53.service
```

### Configuration

The project uses a simple **config.json** file to function. In this section is a descriptions of each setting. The install script creates a subfolder called, config. it copies the config file to this folder. At startup the project checks the subfolder for the config file first.All this is done because .gitignore ignores this folder. Otherwise any subsequent git pull would override all your settings.

| setting   | description                                                  |
| --------- | ------------------------------------------------------------ |
| listen_ip | The IP address the listener establishes itself on. The current code only supports a single IP at the moment, not a collection of IP's, if you are multi-homed. If you intend to run this on your primary DNS server, on a port other than 53, you can make set this to 127.0.0.1. Otherwise leave it at 0.0.0.0. |
|listen_port|The UDP port to listen on for DNS NOTIFY messages.|
|notify_servers|The list of servers from which notification is permitted. Any others are ignored.|
|domains_to_manage|The list of domains we want this project to manage and synchronize.|
|domains_to_manage_from_aws|If the list of domains is long we could just take the lead of Route53 and manage every domain we have.|
|zone_refresh_wait_interval|This is the number of seconds the refresh thread sleeps before checking for refresh needs again.|

### DNS Record Types Currently Supported

Presently the following are supported: A, CNAME, MX, NS¹, SOA, SRV, TXT

¹This project intentionally discards NS records of the root domain (but not subdomains) to preserve the ability of Route53 to properly function as a public-facing slave zone. Additionally this project ignores the mname and rname fields of the SOA record for the same reason.

