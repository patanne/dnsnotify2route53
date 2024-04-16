# DNS Notify to Route53

Accept DNS NOTIFY messages. Then through zone transfers (AXFR) push changes to Route53.

## Motivation

You want your DNS zones to be published to infrastructure that is scalable, reliable, and has good protection against DoS. However you do not want to pay a lot, and the UI of cloud service providers is usually tedious, preventing good workflow.

Domain registrars have terrible interfaces to manage DNS records. Cloud service providers are slightly better but get expensive at scale. So how do we manage DNS zones in our tool of choice but push to AWS Route53, using them for slave zones? This is the tool.

## What This Project Does

It uses AXFR to pull the contents of your domain(s) managed elsewhere. It then compares the content of your domain(s) with what you have already published on AWS. It makes any changes to AWS to reflect the current state of your domain.

## How to Use

setup aws cli

```shell
apt install -y awscli
aws configure
```

download

```shell
cd /opt
git clone https://github.com/patanne/dnsnotify2route53.git
cd dnsnotify2route53
```

configure

```shell
nano config.json
```

install

```shell
assets/install_all.sh
```

## Configuration

The project uses a simple **config.json** file to function. In this section is a descriptions of each setting. The install script creates a subfolder called, config. it copies the config file to this folder. At startup the project checks the subfolder for the config file first.All this is done because .gitignore ignores this folder. Otherwise any subsequent git pull would override all your settings.

you can lint the config file in the following way:

```shell
python3 -m json.tool /opt/dnsnotify2route53/config/config.json
```



| setting                    | description                                                  |
| -------------------------- | ------------------------------------------------------------ |
| listen_ip                  | The IP address the listener establishes itself on. The current code only supports a single IP at the moment, not a collection of IP's, if you are multi-homed. If you intend to run this on your primary DNS server, on a port other than 53, you can make set this to 127.0.0.1. Otherwise leave it at 0.0.0.0. |
| listen_port                | The UDP port to listen on for DNS NOTIFY messages.           |
| notify_servers             | The list of servers from which notification is permitted. Any others are ignored. |
| domains_to_manage          | The list of domains we want this project to manage and synchronize. |
| domains_to_manage_from_aws | If the list of domains is long we could just take the lead of Route53 and manage every domain we have. |
| zone_refresh_wait_interval | This is the number of seconds the refresh thread sleeps before checking for refresh needs again. |

## DNS Record Types Currently Supported

Presently the following are supported: A, CNAME, MX, NS¹, SOA, SRV, TXT

¹This project intentionally discards NS records of the root domain (but not subdomains) to preserve the ability of Route53 to properly function as a public-facing slave zone. Additionally this project ignores the mname and rname fields of the SOA record for the same reason.