
# dns_class_* imports at bottom of module to prevent cirtular import

class DNS_zone:
	def __init__(self, zone_name:str,ttl:int=None):
		self._zone_name = zone_name
		self._resource_set_dict = dict()
		self._resource_iter = 0
		self._ttl = ttl

	@property
	def _iterable_dict(self) -> list['DNS_zone_resource_set']:
		return list(self._resource_set_dict.values())

	def __iter__(self):
		self._resource_iter = 0
		return self._iterable_dict.__iter__()

	def __next__(self):
		self._resource_iter += 1
		if self._resource_iter < len(self._iterable_dict):
			return self._iterable_dict[self._resource_iter]
		raise StopIteration

	@property
	def zone_name(self)-> str: return self._zone_name

	@property
	def ttl(self)-> int: return self._ttl

	def add_resource_set(self, resource_set: 'DNS_zone_resource_set'):
		resource_set._parent_zone = self
		if not resource_set.resource_set_key in self._resource_set_dict:
			self._resource_set_dict[resource_set.resource_set_key] = resource_set
		else:
			# TODO: create merge method
			self._resource_set_dict[resource_set.resource_set_key].merge_resource_set(resource_set)


	def add_resource(self, record: 'DNS_zone_record'):
		if record.ttl is None: record.ttl = self._ttl

		if not record.resource_set_key in self._resource_set_dict:
			self._resource_set_dict[record.resource_set_key] = DNS_zone_resource_set(self,record.label,record.record_class,record.record_type) # if we do not already have such a resource set, add it
		self._resource_set_dict[record.resource_set_key].add_resource(record)

	def exists(self, rr_to_be_compared_to) -> bool:
		for internal_rr in self._iterable_dict:
			if rr_to_be_compared_to.resource_set_key == internal_rr.resource_set_key: return True
		return False

	def get_peer_resource_set(self, resource_set_to_match):
		for internal_resource_set in self._iterable_dict:
			if resource_set_to_match.resource_set_key == internal_resource_set.resource_set_key:
				return internal_resource_set
		return None

	def get_peer_resource(self, resource_to_match):
		for internal_resource_set in self._iterable_dict:
			if resource_to_match.resource_set_key == internal_resource_set.resource_set_key:
				for internal_resource in internal_resource_set._resource_records.values():
					if resource_to_match.unique_key == internal_resource.unique_key:
						return internal_resource
		return None

	def patch_SOA(self, aws_zone: 'DNS_zone'):
		record = None
		for aws_record_record_set in aws_zone:
			if aws_record_record_set._record_type == DNS_RECORD_TYPE.SOA:
				for aws_record in aws_record_record_set._resource_records.values():
					record = aws_record

		rr = self.get_peer_resource(record)
		rr._mname = record._mname
		rr._rname = record._rname
		self._ttl = rr._ttl

	def patch_TXT(self):
		record_value = ""

		for container in self._iterable_dict:
			if container.type == DNS_RECORD_TYPE.TXT:
				if len(container.resource_records) > 1 and "_domainkey" in container._label:
					dict_first_entry = list(container.resource_records.keys())[0]
					resource_key = container._label
					ttl = container.resource_records[dict_first_entry].ttl
					records = container.resource_records
					for entry_key in records:
						record_value += f'"{container.resource_records[entry_key].data}" '
					record_value = record_value.rstrip(' ').rstrip('"').lstrip('"') # we do this to match what we do to the record from amazon
					new_record = DNS_zone_record_TXT(resource_key, record_value, ttl)
					new_dict = {new_record.unique_key:new_record}
					container._resource_records = new_dict
					pass

	def patch_TTL(self):
		# for record in self._iterable_dict:
		# 	if record._record_type == DNS_RECORD_TYPE.SOA: self._ttl = record._ttl

		for container in self._iterable_dict:
			if container._ttl is None: container._ttl = self._ttl
			for record in container._resource_records.values():
				if record._ttl is None: record._ttl = self._ttl


# dns_class_* imports
from dns_class_common import *
from dns_class_resource import DNS_zone_record,DNS_zone_record_TXT
from dns_class_resource_set import DNS_zone_resource_set
