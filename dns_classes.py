import base64
import hashlib
import globals

from abc import ABC
from enum import IntEnum, auto

class DNS_RECORD_TYPE(IntEnum):
	A		= 0
	CNAME	= auto()
	MX		= auto()
	SOA		= auto()
	SRV		= auto()
	TXT		= auto()

DNS_RECORD_TYPE_STRING = \
[
	"A",
	"CNAME",
	"MX",
	"SOA",
	"SRV",
	"TXT"
]

class DNS_RECORD_CLASS(IntEnum):
	IN	= 0

DNS_RECORD_CLASS_STRING = \
[
	"IN"
]

class DNS_zone:
	def __init__(self, zone_name):
		self._zone_name = zone_name
		self._resource_dict = dict()
		self._resource_iter = 0
		self._ttl = None

	@property
	def _iterable_dict(self):
		return list(self._resource_dict.values())

	def __iter__(self):
		self._resource_iter = 0
		return self._iterable_dict.__iter__()

	def __next__(self):
		self._resource_iter += 1
		if self._resource_iter < len(self._iterable_dict):
			return self._iterable_dict[self._resource_iter]
		raise StopIteration

	def add(self, resource: 'DNS_zone_record'):
		if resource.group_key in self._resource_dict:
			container = self._resource_dict[resource.group_key]
		else:
			container = DNS_zone_record_container()
			self._resource_dict[resource.group_key] = container

		resource._parent_domain = self._zone_name
		container.add(resource)

	def exists(self, rr_to_be_compared_to) -> bool:
		for internal_rr in self._iterable_dict:
			if rr_to_be_compared_to.group_key == internal_rr.group_key: return True
		return False

	def get_peer_container(self,rr_to_match):
		for internal_rr_container in self._iterable_dict:
			if rr_to_match.group_key == internal_rr_container.group_key:
				return internal_rr_container
		return None

	def get_peer_rr(self,rr_to_match):
		for internal_rr_container in self._iterable_dict:
			if rr_to_match.group_key == internal_rr_container.group_key:
				for internal_rr in internal_rr_container._resource_records.values():
					if rr_to_match.unique_key == internal_rr.unique_key:
						return internal_rr
		return None

	def patch_SOA(self, aws_zone):
		record = None
		for aws_record_container in aws_zone:
			if aws_record_container._record_type == DNS_RECORD_TYPE.SOA:
				for aws_record in aws_record_container._resource_records.values():
					record = aws_record

		rr = self.get_peer_rr(record)
		rr._mname = record._mname
		rr._rname = record._rname
		self._ttl = rr._ttl

	def patch_TTL(self):
		# for record in self._iterable_dict:
		# 	if record._record_type == DNS_RECORD_TYPE.SOA: self._ttl = record._ttl

		for container in self._iterable_dict:
			if container._ttl is None: container._ttl = self._ttl
			for record in container._resource_records.values():
				if record._ttl is None: record._ttl = self._ttl

class DNS_zone_record_container:
	def __init__(self):
		self._name				= None
		self._record_class		= None
		self._record_type		= None
		self._ttl				= None
		self._resource_records	= dict()

	def __str__(self):
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]} {DNS_RECORD_TYPE_STRING[self._record_type]} {self._name}"

	def __eq__(self, other):
		# internal_sorted_dict	= dict(sorted( self._resource_records.items(), key=lambda item: item[0]))
		# other_sorted_dict		= dict(sorted(other._resource_records.items(), key=lambda item: item[0]))
		# internal_sorted_dict	= dict(sorted( self._resource_records.items()))
		# other_sorted_dict		= dict(sorted(other._resource_records.items()))

		for entry in self._resource_records.values():
			if entry.unique_key not in other._resource_records:
				return False
			other_entry = other._resource_records[entry.unique_key]
			if entry != other_entry:
				return False
		return True

	@property
	def group_key(self):
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{self._name}"

	@property
	def resource_records(self): return self._resource_records

	@property
	def resource_records_as_list(self): pass

	def add(self,resource: 'DNS_zone_record'):
		if len(self._resource_records) == 0:
			self._name			= resource._name
			self._record_class	= resource._record_class
			self._record_type	= resource._record_type
			self._ttl			= resource._ttl
			self._parent_domain	= resource._parent_domain
		else:
			if self.group_key != resource.group_key:
				raise Exception("group key mismatch. this container is already for a different group.")
		self._resource_records[resource.unique_key] = resource

	def for_AWS(self):
		if	  self._name == "@": name = self._parent_domain
		elif  self._name == self._parent_domain: name = self._parent_domain
		else: name = self._name + '.' + self._parent_domain

		type = DNS_RECORD_TYPE_STRING[self._record_type]

		rr_values = self._resource_records.values()
		if len(rr_values) == 1:
			key = next(iter(self._resource_records))
			rr = self._resource_records[key]
			value = rr.for_AWS()
			return name, type, self._ttl, value
		else:
			value_list = []
			for rr in self._resource_records.values():
				value_list.append(rr.for_AWS())

			return name, type, self._ttl, value_list

class DNS_zone_record(ABC):
	def __init__(self, name, record_type:DNS_RECORD_TYPE, value=None, ttl=None, record_class:DNS_RECORD_CLASS=DNS_RECORD_CLASS.IN):
		self._name = name
		self._record_class = record_class
		self._record_type = record_type
		self._value = value
		self._ttl = int(ttl) if isinstance(ttl, str) else ttl
		self._parent_domain = None

	def __eq__(self, other):
		if self._record_type != other._record_type: return False
		return  self._name	== other._name \
			and self._value	== other._value \
			and self._ttl	== other._ttl

	def __str__(self):
		return f"{self._name} {DNS_RECORD_CLASS_STRING[self._record_class]} {DNS_RECORD_TYPE_STRING[self._record_type]} {self._value}"

	@property
	def unique_key(self):
		if not isinstance(self._value,list):
			return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{self._name}"

		input_value = ""
		for segment in self._value:
			input_value = input_value + segment

		hasher = hashlib.sha1(input_value.encode())
		value = base64.b16encode(hasher.digest()[:10]).decode(globals.encoding)
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{self._name}::{value}"

	@property
	def group_key(self):
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{self._name}"

	def for_AWS(self):
		return self._value

class DNS_zone_record_A(DNS_zone_record):
	def __init__(self, name, ip_address, ttl=None):	super().__init__(name,DNS_RECORD_TYPE.A,ip_address,ttl)

class DNS_zone_record_CNAME(DNS_zone_record):
	def __init__(self, name, alias, ttl=None):	super().__init__(name,DNS_RECORD_TYPE.CNAME,alias,ttl)

class DNS_zone_record_MX(DNS_zone_record):
	def __init__(self, name, preference, exchange, ttl=None):
		super().__init__(name,DNS_RECORD_TYPE.MX,exchange,ttl)
		self._preference = preference

	def __eq__(self, other):
		if self._record_type != other._record_type: return False
		return  self._name			== other._name \
			and self._preference	== other._preference \
			and self._value			== other._value \
			and self._ttl			== other._ttl

	def __str__(self):
		return f"{self._name} {DNS_RECORD_CLASS_STRING[self._record_class]} {DNS_RECORD_TYPE_STRING[self._record_type]} {self._preference} {self._value}"

	@property
	def unique_key(self):
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{self._name}::{self._preference}"

	def for_AWS(self):
		value = f"{self._preference} {self._value}"
		return value

class DNS_zone_record_SOA(DNS_zone_record):
	def __init__(self, mname, rname, name, serial, refresh, retry, expire, ttl=None):
		super().__init__(name,DNS_RECORD_TYPE.SOA,name,ttl=ttl)
		self._mname		= mname
		self._rname		= rname
		self._serial	= serial
		self._refresh	= refresh
		self._retry 	= retry
		self._expire 	= expire

	def __eq__(self, other):
		if self._record_type != other._record_type: return False
		return  self._name		== other._name \
			and self._mname		== other._mname \
			and self._rname		== other._rname \
			and self._serial	== other._serial \
			and self._refresh	== other._refresh \
			and self._retry		== other._retry \
			and self._expire	== other._expire \
			and self._ttl		== other._ttl

	def for_AWS(self):
		value = f"{self._mname} {self._rname} {self._serial} {self._refresh} {self._retry} {self._expire} {self._ttl}"
		return value

class DNS_zone_record_SRV(DNS_zone_record):
	def __init__(self, service, protocol, name, priority, weight, port, target, ttl=None):
		super().__init__(name,DNS_RECORD_TYPE.SRV,target,ttl)
		self._service	= service
		self._protocol	= protocol
		self._priority	= priority
		self._weight	= weight
		self._port		= port

	def __eq__(self, other):
		if self._record_type != other._record_type: return False
		return  self._service	== other._service \
			and self._protocol	== other._protocol \
			and self._priority	== other._priority \
			and self._weight	== other._weight \
			and self._port		== other._port \
			and self._value		== other._value \
			and self._ttl		== other._ttl

	@property
	def unique_key(self):
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{str(self._service)}::{str(self._protocol)}::{str(self._port)}::{str(self._value)}"

	def for_AWS(self):
		# value = f"{self._service}.{self._protocol}.{self._parent_domain} {self._priority} {self._weight} {self._port} {self._value}"
		value = f"{self._priority} {self._weight} {self._port} {self._value}"
		return value

class DNS_zone_record_TXT(DNS_zone_record):
	def __init__(self, name, value, ttl=None): super().__init__(name,DNS_RECORD_TYPE.TXT,value,ttl)

	@property
	def unique_key(self):
		input_value = ""
		if isinstance(self._value,list):
			for segment in self._value:
				input_value = input_value + segment
		else:
			input_value = str(self._value)

		hasher = hashlib.sha1(input_value.encode())
		value = base64.b16encode(hasher.digest()[:10]).decode(globals.encoding)
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{self._name}::{value}"
