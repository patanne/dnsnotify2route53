import argparse
import sys

from aws_routines import *
from dns_routines import *
from config import *

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
			aws_record = aws_zone.get_peer(internal_record)
			if internal_record != aws_record: chg_list.append(internal_record)
		else:
			add_list.append(internal_record)

	for aws_record in aws_zone:
		if not internal_zone.exists(aws_record):
			del_list.append(aws_record)

	return add_list, chg_list, del_list

def first_start():
	# get all zones hosted on AWS
	zone_dict = get_aws_all_hosted_zones()

	# do we want to use all the AWS zones as the guide, or use the list in the config file?
	if globals.config.domains_to_manage_from_aws:
		zone_list = [hosted_zone for hosted_zone in zone_dict.values()]
	else:
		zone_list = [hosted_zone[1] for hosted_zone in zone_dict.items() if hosted_zone[0] in globals.config.domains_to_manage]

	# get our three lists. inefficient? perhaps. but it works.
	for some_zone in zone_list:
		add_list, chg_list, del_list = get_zone_changes(some_zone)

		changes = aws_changes(some_zone.id)

		# for change in add_list:
		# 	name, type, ttl, value = change.for_AWS()
		# 	changes.change__simple_value("CREATE", type, name, ttl, value)

		for change in chg_list:
			name, type, ttl, value = change.for_AWS()
			changes.change__simple_value("UPSERT", type, name, ttl, value)

		for change in del_list:
			name, type, ttl, value = change.for_AWS()
			changes.change__simple_value("DELETE", type, name, ttl, value)

		changes.patch_multi()
		changes.to_AWS()

	if globals.DEBUG:
		print("--- add ---")
		print([x.unique_key for x in add_list])
		print("--- del---")
		print([x.unique_key for x in del_list])
		print("--- change ---")
		print([x.unique_key for x in chg_list])


if __name__ == "__main__":
	process_args()
	load_config()
	set_logging()

	# logging.info(args)
	first_start()
