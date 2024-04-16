#!/usr/bin/env bash
#set -x

# to be run from the root of the project dir, not the assets dir.

if [ ! -d  ./config ]; then
  mkdir -p ./config
fi

if [ ! -f ./config/config.json ]; then
    cp config.json ./config/
fi

pip3 install -r requirements.txt --break-system-packages

mkdir -p /usr/local/lib/systemd/system

cp /opt/dnsnotify2route53/assets/dnsnotify2route53.service /usr/local/lib/systemd/system
systemctl daemon-reload
systemctl enable  dnsnotify2route53.service
systemctl restart dnsnotify2route53.service
systemctl status  dnsnotify2route53.service