#!/usr/bin/env bash
#set -x

# to be run from the root of the project dir, not the assets dir.

pip3 install -r requirements.txt

mkdir -p /usr/local/lib/systemd/system

cp /opt/dnsnotify2route53/assets/dnsnotify2route53.service /usr/local/lib/systemd/system
systemctl daemon-reload
systemctl enable dnsnotify2route53.service
