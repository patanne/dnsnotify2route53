#!/usr/bin/env python3

import argparse
import datetime
import sys
import threading
import time

from aws_routines import *
from dns_routines import *
from config import *
from notify_listener import listen_for_notify

import globals
globals.init()

def process_args():
	parser = argparse.ArgumentParser()
	parser.add_argument("--daemon", action="store_true", help="configure running as a daemon. enter listening loop for notify.")
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


def record_zone_refresh(zone_list):
	for some_zone in zone_list:
		refresh = get_dns_soa_refresh(some_zone)
		epoch_now = int(time.time())
		next_check = epoch_now + refresh

		globals.zone_dict[some_zone.domain_name] = dict()
		globals.zone_dict[some_zone.domain_name]['refresh']		= refresh
		globals.zone_dict[some_zone.domain_name]['epoch_now']	= epoch_now
		globals.zone_dict[some_zone.domain_name]['next_check']	= next_check

def update_zone_refresh(zone_name):
	refresh = globals.zone_dict[zone_name]['refresh']
	epoch_now = int(time.time())
	next_check = epoch_now + refresh
	globals.zone_dict[zone_name]['epoch_now']	= epoch_now
	globals.zone_dict[zone_name]['next_check']	= next_check


def get_zone_changes(some_zone):
	add_list = []
	chg_list = []
	del_list = []

	aws_zone = get_aws_zone(some_zone)
	internal_zone = get_dns_zone(globals.config.notify_servers[0],some_zone.domain_name)
	internal_zone.patch_SOA(aws_zone)
	internal_zone.patch_TTL()

	for internal_record in internal_zone:
		if aws_zone.exists(internal_record):
			aws_record = aws_zone.get_peer_container(internal_record)
			if internal_record != aws_record: chg_list.append(internal_record)
		else:
			add_list.append(internal_record)

	for aws_record in aws_zone:
		if not internal_zone.exists(aws_record):
			del_list.append(aws_record)

	return add_list, chg_list, del_list

def process_zones(zone_list):
	# get our three lists. inefficient? perhaps. but it works.
	for some_zone in zone_list:
		add_list, chg_list, del_list = get_zone_changes(some_zone)

		changes = aws_changes(some_zone.id)

		there_are_changes=False
		for change in add_list:
			there_are_changes=True
			name, type, ttl, value = change.for_AWS()
			changes.change__simple_value("CREATE", type, name, ttl, value)

		for change in chg_list:
			there_are_changes=True
			name, type, ttl, value = change.for_AWS()
			changes.change__simple_value("UPSERT", type, name, ttl, value)

		for change in del_list:
			there_are_changes=True
			name, type, ttl, value = change.for_AWS()
			changes.change__simple_value("DELETE", type, name, ttl, value)

		if there_are_changes:
			changes.to_AWS()

		update_zone_refresh(some_zone.domain_name)

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

def queue_processor():
	keep_running = True
	while keep_running:
		zone,serial = globals.wq.get()
		zones_received = [zone]
		zone_dict = get_aws_all_hosted_zones()
		zone_list = [hosted_zone[1] for hosted_zone in zone_dict.items() if hosted_zone[0] in zones_received]
		process_zones(zone_list)
		if serial is None:
			message = f"worker processed {zone} by need of refresh at {datetime.datetime.now().strftime(globals.timestamp_format)} local time."
		else:
			message = f"worker processed {zone} with serial '{serial}' at {datetime.datetime.now().strftime(globals.timestamp_format)} local time."
		print(message)
		logging.info(message)
		globals.wq.task_done()
		# thread.sleep(2)

def refresh_processor():
	while True:
		globals.refresh_wait_event.wait(timeout=globals.config.zone_refresh_wait_interval)
		epoch_now = int(time.time())
		for zone in globals.zone_dict.keys():
			next_check	= globals.zone_dict[zone]['next_check']
			if epoch_now < next_check:
				expire_time = time.strftime(globals.timestamp_format, time.localtime(next_check))
				logging.debug(f"refresh interval for zone {zone} does not expire until {expire_time}. skipping.")
				continue
			# this zone needs a refresh
			logging.debug(f"refresh interval for zone {zone} has expired. putting zone name on queue.")
			globals.wq.put((zone, None))

if __name__ == "__main__":
	process_args()
	load_config()
	set_logging()

	# logging.info(args)
	first_start()


	if globals.args.daemon:
		notify_listener = threading.Thread(target=listen_for_notify)
		queue_worker 	= threading.Thread(target=queue_processor)
		refresh_worker	= threading.Thread(target=refresh_processor)
		queue_worker.start()
		notify_listener.start()
		refresh_worker.start()
