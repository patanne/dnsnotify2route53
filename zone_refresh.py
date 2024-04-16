import datetime
import logging
import time

from aws_routines import *
from dns_routines import *


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

def refresh_processor():

	message = "starting the refresh timer"
	logging.info(message)

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
