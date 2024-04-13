import boto3
import json
import logging

from dns_classes import *

client = boto3.client('route53')

class AWS_hosted_zone:
	def __init__(self, domain_name, zone_id_path):
		self._domain_name = domain_name
		self._zone_id_path = zone_id_path

	@property
	def domain_name(self):
		return self._domain_name.rstrip('.')

	@property
	def id(self):
		return self._zone_id_path.split('/')[-1]

	def __repr__(self):
		return f"{self.domain_name}={self.id}"

	def __str__(self):
		return f"{self.domain_name} = {self.id}"



def get_aws_all_hosted_zones() -> dict:
	response = client.list_hosted_zones()
	zone_dict = dict()
	for zone in response['HostedZones']:
		zone_object = AWS_hosted_zone(zone['Name'], zone['Id'])
		zone_dict[zone_object.domain_name] = zone_object
	return zone_dict

def get_aws_zone(zone_object):
	aws_zone = DNS_zone(zone_object.domain_name)
	rr_response = client.list_resource_record_sets(HostedZoneId=zone_object.id)
	if rr_response['IsTruncated']:
		raise Exception('truncated response from AWS. do we have more than 300 records in the zone?')

	for response in rr_response['ResourceRecordSets']:
		name1	= response['Name'].rstrip('.')
		name2	= name1.replace(zone_object.domain_name,"")
		name3	= name2.rstrip('.')
		name	= "@" if name3 == "" else name3
		ttl		= response['TTL']
		record	= None
		match response['Type']:
			case 'NS': continue
			case 'SOA':
				rrl = response['ResourceRecords'][0]['Value'].split(' ')
				record = DNS_zone_record_SOA(rrl[0],rrl[1],zone_object.domain_name,int(rrl[2]),int(rrl[3]),int(rrl[4]),int(rrl[5]),int(rrl[6]))
				del rrl
			case 'A':
				record = DNS_zone_record_A(name,response['ResourceRecords'][0]['Value'],ttl)
			case 'CNAME':
				record = DNS_zone_record_CNAME(name,response['ResourceRecords'][0]['Value'],ttl)
			case 'MX':
				record = []
				for rr in response['ResourceRecords']:
					preference	= rr['Value'].split(' ')[0]
					exchange	= rr['Value'].split(' ')[1]
					record.append(DNS_zone_record_MX(name,int(preference),exchange,ttl))
					del exchange, preference
			case 'SRV':
				info_1 = name.split('.')
				info_2 = response['ResourceRecords'][0]['Value'].split(' ')
				record = DNS_zone_record_SRV(info_1[0],info_1[1],name,int(info_2[0]),int(info_2[1]),int(info_2[2]),info_2[3],ttl)
				pass
			case 'TXT':
				if len(response['ResourceRecords']) == 1:
					value = response['ResourceRecords'][0]['Value'].rstrip('"').lstrip('"')
					record = DNS_zone_record_TXT(name, value, ttl)
				else:
					record	= []
					for segment in response['ResourceRecords']:
						value = segment['Value'].rstrip('"').lstrip('"')
						record.append(DNS_zone_record_TXT(name, value, ttl))
					del segment
				del value
			case _:
				logging.warning(f"unhandled record type: {response['Type']}")

		if isinstance(record,list):
			for individual_rr in record: aws_zone.add(individual_rr)
		else:
			aws_zone.add(record)
	return aws_zone


# https://stackoverflow.com/questions/69087338/boto3-change-resource-record-sets-with-multiple-ipadresses
# https://stackoverflow.com/questions/58212671/how-to-change-the-name-of-a-record-set-in-route-53-using-python-boto3
# https://github.com/aws/aws-cli/issues/8241
# https://hands-on.cloud/boto3/route53/
# https://repost.aws/knowledge-center/simple-resource-record-route53-cli

class aws_changes:
	def __init__(self, zone_id):
		self.zone_id = zone_id
		self._change_list = []

	def to_AWS(self):
		full_change = dict()
		full_change['Changes'] = self._change_list
		j = json.dumps(full_change, indent=2)
		print(j)

		client.change_resource_record_sets(HostedZoneId=self.zone_id,ChangeBatch=full_change)

	def change__simple_value(self,change_type,type,name,ttl,value):
		chg = dict()
		chg['Action'] = change_type
		chg_rs = dict()
		chg_rs['Type'] = type
		if ttl is not None: chg_rs['TTL'] = ttl
		chg_rs['Name'] = name
		chg_rr = []
		if isinstance(value,list):
			for sub in value:
				if type == 'TXT':
					tmp = f'"{sub}"'
					chg_rr.append({'Value': tmp})
				else:
					chg_rr.append({'Value': sub})
		else:
			if type == 'TXT':
				tmp = f'"{value}"'
				chg_rr.append({'Value':tmp})
			else:
				chg_rr.append({'Value':value})
		chg_rs['ResourceRecords']=chg_rr
		chg['ResourceRecordSet']=chg_rs

		self._change_list.append(chg)

	def patch_multi(self):
		seen = dict()
		index = 0
		while index < len(self._change_list):
			current = self._change_list[index]
			kind = f"{current['Action']}::{current['ResourceRecordSet']['Type']}::{current['ResourceRecordSet']['Name']}"
			# we have not seen this record already
			if kind not in seen:
				seen[kind] = index
				index += 1
				continue
			previous = seen[kind]
			self._change_list[previous]['ResourceRecordSet']['ResourceRecords'].append(current['ResourceRecordSet']['ResourceRecords'][0])
			del self._change_list[index]
			pass

