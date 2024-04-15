import logging

from dns import query
from dns import zone as dnszone
from dns import rdatatype as resource_type
from dns.resolver import Resolver
from dns_classes import *

def get_dns_zone(server,zone_name):
	dns_zone = DNS_zone(zone_name)
	axfr = dnszone.from_xfr(query.xfr(server, zone_name))
	for rsdata in axfr.iterate_rdatasets():
		pass
	for rdata in axfr.iterate_rdatas():
		rrn	= rdata[0]
		rrr = rdata[2]
		name = rrn.to_text()
		ttl = rdata[1]
		record	= None
		match rrr.rdtype:
			case resource_type.SOA:
				# while we do not want mname or rname to be pushed to AWS, we need them for comparison, so include it here.
				# we replace the information with what came from AWS as a post-comparison step in routine 'patch_SOA'.
				record = DNS_zone_record_SOA(rrr.mname.to_text(),rrr.rname.to_text(),zone_name,rrr.serial,rrr.refresh,rrr.retry,rrr.expire,rrr.minimum)
			case resource_type.NS:
				# we do not want to handle the name servers for the root domain. that will be managed by route53.
				if name == "@": continue
				# NS records must be fully qualified.
				resource = rrr.target.to_text() if rrr.target.is_absolute() else rrr.target.derelativize(axfr.origin).to_text(False)
				record = DNS_zone_record_NS(name,server,ttl)
			case resource_type.A:
				record = DNS_zone_record_A(name,rrr.address,ttl)
			case resource_type.CNAME:
				resource = rrr.target.to_text() if rrr.target.is_absolute() else rrr.target.derelativize(axfr.origin).to_text(False)
				record = DNS_zone_record_CNAME(name,resource)
			case resource_type.MX:
				resource = rrr.exchange.to_text() if rrr.exchange.is_absolute() else rrr.exchange.derelativize(axfr.origin).to_text(False)
				record = DNS_zone_record_MX(name,rrr.preference,resource,ttl)
			case resource_type.SRV:
				service	= name.split('.')[0]
				protocol= name.split('.')[1]
				target	= rrr.target.to_text()
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

def get_dns_soa_refresh(zone):
	resolver = Resolver()
	resolver.nameservers = globals.config.notify_servers
	raw_answer = resolver.query(zone.domain_name, 'SOA')
	answer_dict = raw_answer.response.answer[0].items
	answer = list(answer_dict)[0].refresh

	return answer
