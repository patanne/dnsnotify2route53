import logging

from dns_class_common import *
from dns_class_zone import DNS_zone
from dns_class_resource import DNS_zone_record

from typing import *

class DNS_zone_resource_set:
	def __init__(self, zone: DNS_zone, label: str, record_class: DNS_RECORD_CLASS, record_type: DNS_RECORD_TYPE):
		self._label				: str = label
		self._record_class		: DNS_RECORD_CLASS = record_class
		self._record_type		: DNS_RECORD_TYPE = record_type
		self._resource_records	: dict[str, DNS_zone_record] = dict()
		self._parent_zone		: DNS_zone = zone

	def __str__(self):
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]} {DNS_RECORD_TYPE_STRING[self._record_type]} {self._label}"

	def __eq__(self, other):
		for entry in self._resource_records.values():
			# does resource exist in the other resource set?
			if entry.unique_key not in other.resource_records:
				return False
			# are they equal?
			if entry != other.resource_records[entry.unique_key]:
				return False
		return True

	@property
	def type(self)-> DNS_RECORD_TYPE:
		return self._record_type

	@property
	def resource_set_key(self)-> str:
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{self._label}"

	@property
	def resource_records(self)-> dict[str, DNS_zone_record]:
		return self._resource_records

	@property
	def parent_zone(self): return self._parent_zone

	@parent_zone.setter
	def parent_zone(self, zone: DNS_zone): self._parent_zone = zone

	# @property
	# def resource_records_as_list(self): pass

	def add_resource(self, resource: DNS_zone_record):
		if len(self.resource_records) == 0:
			if self._parent_zone is None:
				raise Exception("resource added to resource set before parent zone has been initialized.")

			self._record_class	: DNS_RECORD_CLASS	= resource.record_class
			self._record_type	: DNS_RECORD_TYPE	= resource.record_type
			self._label			: str				= resource.label
		else:
			if self.resource_set_key != resource.resource_set_key:
				raise Exception("group key mismatch. this container is already for a different group.")
		self.resource_records[resource.unique_key] = resource

	def merge_resource_set(self, other_set: 'DNS_zone_resource_set'):
		if self.resource_set_key != other_set.resource_set_key:
			raise("resource set keys do not match.")

		for resource in other_set.resource_records:
			if resource.unique_key not in self._resource_records.values():
				self.add_resource(resource)


	def for_AWS(self)-> (str, str, int, any):
		# for AWS, the "@" is replaced by the domain name
		if	  self._label == "@": label = self._parent_zone.zone_name

		# if the label already is the domain name, use it
		elif  self._label == self._parent_zone.zone_name: label = self._parent_zone.zone_name

		# otherwise we use the fqdn of label + domain
		else: label = self._label + '.' + self._parent_zone.zone_name

		record_type_as_string = DNS_RECORD_TYPE_STRING[self._record_type]

		# handle difference of resource set having one resource record or multiple
		rr_values = self.resource_records.values()
		if len(rr_values) == 1:
			key = next(iter(self.resource_records))
			rr = self.resource_records[key]
			value = rr.for_AWS()
			# this is where we fix missing ttl, setting it = domain ttl
			ttl = rr.ttl if rr.ttl is not None else self.parent_zone.ttl
			return label, record_type_as_string, value, ttl
		else:
			value_list = []
			ttl = None
			first_record=True
			for rr in self.resource_records.values():
				value_list.append(rr.for_AWS())
				# this is where we fix missing ttl, setting it = domain ttl.
				# this has a slight flaw that if each resource record has a different value, changes will alwayys happen.
				if not first_record and rr.ttl != ttl:
					message = f"for domain '{self.parent_zone.zone_name}', record type '{record_type_as_string}', label '{label}' there are multiple records with different TTL. fix at source."
					logging.error(message)
				if rr.ttl is not None: ttl = rr.ttl # set ttl if it exists.

			if ttl is None: ttl = self.parent_zone.ttl # set ttl to parent if not exists.
			return label, record_type_as_string, value_list, ttl

