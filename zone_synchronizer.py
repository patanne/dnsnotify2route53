import datetime

from aws_routines import *
from dns_routines import *
from zone_refresh import update_zone_refresh

def get_zone_changes(some_zone):
	add_list = []
	chg_list = []
	del_list = []

	aws_zone = get_aws_zone(some_zone)
	internal_zone = get_dns_zone(globals.config.notify_servers[0],some_zone.domain_name)
	internal_zone.patch_SOA(aws_zone)
	# internal_zone.patch_TTL()

	for internal_record in internal_zone:
		if aws_zone.exists(internal_record):
			aws_record = aws_zone.get_peer_resource_set(internal_record)
			if internal_record != aws_record: chg_list.append(internal_record)
		else:
			add_list.append(internal_record)

	for aws_record in aws_zone:
		if not internal_zone.exists(aws_record):
			del_list.append(aws_record)

	return add_list, chg_list, del_list

def process_zones(zone_list: list[AWS_hosted_zone]):
	# get our three lists. inefficient? perhaps. but it works.
	for some_zone in zone_list:
		add_list, chg_list, del_list = get_zone_changes(some_zone)

		changes = aws_changes(some_zone.id)

		there_are_changes=False
		for change in add_list:
			there_are_changes=True
			label, resource_type_string, ttl, data = change.for_AWS()
			changes.change__simple_value("CREATE", resource_type_string, label, data, ttl)

		for change in chg_list:
			there_are_changes=True
			label, resource_type_string, ttl, data = change.for_AWS()
			changes.change__simple_value("UPSERT", resource_type_string, label, data, ttl)

		for change in del_list:
			there_are_changes=True
			label, resource_type_string, ttl, data = change.for_AWS()
			changes.change__simple_value("DELETE", resource_type_string, label, data, ttl)

		if there_are_changes:
			message = f"changes were found at {datetime.datetime.now().strftime(globals.timestamp_format)} for zone '{some_zone.domain_name}'. pushing to Route53."
			logging.info(message)

			a_dict = changes.get_aws_dict()
			changes.send_aws_dict(a_dict)
		else:
			message = f"finished synchronization cycle at {datetime.datetime.now().strftime(globals.timestamp_format)} for zone '{some_zone.domain_name}'. no changes found."
			logging.info(message)
		update_zone_refresh(some_zone.domain_name)


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
