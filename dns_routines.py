import logging

from dns import query
from dns import zone as dnszone
from dns import rdatatype as resource_type

from dns_classes import *

def get_dns_zone(server,zone_name):
	dns_zone = DNS_zone(zone_name)
	axfr = dnszone.from_xfr(query.xfr(server, zone_name))
	for rdata in axfr.iterate_rdatas():
		rrn	= rdata[0]
		rrr = rdata[2]
		name = rrn.to_text()
		ttl = rdata[1]
		record	= None
		match rrr.rdtype:
			case resource_type.SOA:
				record = DNS_zone_record_SOA(rrr.mname.to_text(),rrr.rname.to_text(),zone_name,rrr.serial,rrr.refresh,rrr.retry,rrr.expire,rrr.minimum)
				# remove the elements that we want to leave with AWS
				# record = DNS_zone_record_SOA("","", zone_name, rrr.serial, rrr.refresh, rrr.retry, rrr.expire, rrr.minimum)
			case resource_type.NS:
				# we do not want to pass along the name servers. that will be managed by route53
				continue
			case resource_type.A:
				record = DNS_zone_record_A(name,rrr.address,ttl)
			case resource_type.CNAME:
				record = DNS_zone_record_CNAME(name,rrr.target.to_text())
			case resource_type.MX:
				record = DNS_zone_record_MX(name,rrr.preference,rrr.exchange.to_text(),ttl)
			case resource_type.SRV:
				service	= name.split('.')[0]
				protocol= name.split('.')[1]
				target	= rrr.target.labels[0].decode(globals.encoding)
				record = DNS_zone_record_SRV(service,protocol,name,rrr.priority,rrr.weight,rrr.port,target,ttl)
			case resource_type.TXT:
				if len(rrr.strings) == 1:
					value = rrr.strings[0].decode(globals.encoding)
					record = DNS_zone_record_TXT(name, value, ttl)
				else:
					record	= []
					for segment in rrr.strings:
						value = segment.decode(globals.encoding)
						record.append(DNS_zone_record_TXT(name, value, ttl))
					del segment
				del value
			case _:
				logging.warning(f"unhandled record type: {resource_type.to_text(rrr.rdtype.value)}")
				continue

		if isinstance(record,list):
			for individual_rr in record: dns_zone.add(individual_rr)
		else:
			dns_zone.add(record)
	return dns_zone
