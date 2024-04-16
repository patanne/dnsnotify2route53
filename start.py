#!/usr/bin/env python3

import argparse
import datetime
import sys
import threading

from aws_routines import *
from dns_routines import *
from config import *
from notify_listener import listen_for_notify
from zone_refresh import record_zone_refresh, refresh_processor
from zone_synchronizer import process_zones, queue_processor

import globals
globals.init()

def process_args():
	parser = argparse.ArgumentParser()
	parser.add_argument("--daemon", action="store_true", help="configure running as a daemon. enter listening loop for notify.")
	parser.add_argument("--no-push", action="store_true", help="for debugging. if set will not push changes to Route53.")
	parser.add_argument("-d","--domains", help="comma-separated list of domains to manage, overriding config file.")
	parser.add_argument("-s","--notify-servers", help="comma-separated list of notify servers to override config file.")
	globals.args = parser.parse_args()

def set_logging():
	log_level	= logging.DEBUG if globals.DEBUG else logging.INFO
	log_stream	= sys.stderr if globals.DEBUG else sys.stdout

	if globals.args.daemon:
		logging.basicConfig(stream=log_stream, level=log_level)
	else:
		if globals.DEBUG:
			logging.basicConfig(stream=log_stream, level=log_level)
			# logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
		else:
			logging.basicConfig(filename='/var/log/dnsnotify2route53.log',level=log_level)


def first_start():
	# get all zones hosted on AWS
	zone_dict = get_aws_all_hosted_zones()

	# do we want to use all the AWS zones as the guide, or use the list in the config file?
	if globals.config.domains_to_manage_from_aws:
		zone_list = [hosted_zone for hosted_zone in zone_dict.values()]
	else:
		# the logic here stops us from accidentally trying to process a zone not already created in route53
		zone_list = [hosted_zone[1] for hosted_zone in zone_dict.items() if hosted_zone[0] in globals.config.domains_to_manage]

	record_zone_refresh(zone_list)
	process_zones(zone_list)

	message = f"ran 'first_start' routine at {datetime.datetime.now().strftime(globals.timestamp_format)} local time."
	logging.info(message)
	print(message)

if __name__ == "__main__":
	process_args()
	load_config()
	set_logging()

	# logging.info(args)
	first_start()


	if globals.args.daemon:

		message = "running in daemon mode."
		logging.info(message)

		notify_listener = threading.Thread(target=listen_for_notify)
		queue_worker 	= threading.Thread(target=queue_processor)
		refresh_worker	= threading.Thread(target=refresh_processor)

		queue_worker.start()
		notify_listener.start()
		refresh_worker.start()

	else:
		message = "we ran one-off. execution finished."
		logging.info(message)
