from dns_class_common import *
from dns_class_zone import DNS_zone

class DNS_zone_record(ABC):
	def __init__(self, label, record_type:DNS_RECORD_TYPE, data=None, ttl=None, record_class:DNS_RECORD_CLASS=DNS_RECORD_CLASS.IN):
		self._label			: str = label
		self._record_class	: DNS_RECORD_CLASS	= record_class
		self._record_type	: DNS_RECORD_TYPE	= record_type
		self._data			: any = data
		self._ttl			: int = int(ttl) if isinstance(ttl, str) else ttl
		self._parent_zone	: DNS_zone = None

	def __eq__(self, other):
		if self._record_type != other.record_type: return False
		return  self._label	== other.label \
			and self._data	== other.data \
			and self._ttl	== other.ttl

	def __str__(self):
		return f"{self._label} {DNS_RECORD_CLASS_STRING[self._record_class]} {DNS_RECORD_TYPE_STRING[self._record_type]} {self._data}"

	@property
	def record_class(self)-> DNS_RECORD_CLASS: return self._record_class

	@property
	def record_type(self)-> DNS_RECORD_TYPE: return self._record_type

	@property
	def label(self)-> str : return self._label

	@property
	def data(self)-> any : return self._data

	@property
	def parent_zone(self) -> DNS_zone:	return self._parent_zone

	@parent_zone.setter
	def parent_zone(self, zone: DNS_zone): self._parent_zone = zone

	@property
	def ttl(self) -> int:	return self._ttl

	@ttl.setter
	def ttl(self,ttl) -> int:	self._ttl = ttl

	@property
	def unique_key(self):
		if not isinstance(self._data, list):
			return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{self._label}"

		input_value = ""
		for segment in self._data:
			input_value = input_value + segment

		hasher = hashlib.sha1(input_value.encode())
		value = base64.b16encode(hasher.digest()[:10]).decode(globals.encoding)
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{self._label}::{value}"

	@property
	def resource_set_key(self):
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{self._label}"

	def for_AWS(self):
		return self._data


### ----- DNS_zone_record_A
class DNS_zone_record_A(DNS_zone_record):
	def __init__(self, label, ip_address, ttl=None):	super().__init__(label,DNS_RECORD_TYPE.A,ip_address,ttl)


### ----- DNS_zone_record_CNAME
class DNS_zone_record_CNAME(DNS_zone_record):
	def __init__(self, label, alias, ttl=None):	super().__init__(label,DNS_RECORD_TYPE.CNAME,alias,ttl)


### ----- DNS_zone_record_MX
class DNS_zone_record_MX(DNS_zone_record):
	def __init__(self, 	 label, preference, exchange, ttl=None):
		super().__init__(label,DNS_RECORD_TYPE.MX,exchange,ttl)
		self._preference = preference

	def __eq__(self, other):
		if self._record_type != other._record_type: return False
		return  self._label			== other._label \
			and self._preference	== other._preference \
			and self._data			== other._data \
			and self._ttl			== other._ttl

	def __str__(self):
		return f"{self._label} {DNS_RECORD_CLASS_STRING[self._record_class]} {DNS_RECORD_TYPE_STRING[self._record_type]} {self._preference} {self._data}"

	@property
	def unique_key(self):
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{self._label}::{self._preference}"

	def for_AWS(self):
		value = f"{self._preference} {self._data}"
		return value


### ----- DNS_zone_record_NS
class DNS_zone_record_NS(DNS_zone_record):
	def __init__(self, name, server, ttl=None):	super().__init__(name,DNS_RECORD_TYPE.NS,server,ttl)


### ----- DNS_zone_record_SOA
class DNS_zone_record_SOA(DNS_zone_record):
	def __init__(self, mname, rname, label, serial, refresh, retry, expire, ttl=None):
		super().__init__(label,DNS_RECORD_TYPE.SOA,label,ttl=ttl)
		self._mname		= mname
		self._rname		= rname
		self._serial	= serial
		self._refresh	= refresh
		self._retry 	= retry
		self._expire 	= expire

	def __eq__(self, other):
		if self._record_type != other._record_type: return False
		return  self._label		== other._label \
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


### ----- DNS_zone_record_SRV
class DNS_zone_record_SRV(DNS_zone_record):
	def __init__(self, service, protocol, label, priority, weight, port, target, ttl=None):
		super().__init__(label,DNS_RECORD_TYPE.SRV,target,ttl)
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
			and self._data		== other._data \
			and self._ttl		== other._ttl

	@property
	def unique_key(self):
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{str(self._service)}::{str(self._protocol)}::{str(self._port)}::{str(self._data)}"

	def for_AWS(self):
		value = f"{self._priority} {self._weight} {self._port} {self._data}"
		return value


### ----- DNS_zone_record_TXT
class DNS_zone_record_TXT(DNS_zone_record):
	def __init__(self, label, data, ttl=None): super().__init__(label, DNS_RECORD_TYPE.TXT, data, ttl)

	@property
	def unique_key(self):
		input_value = ""
		if isinstance(self._data, list):
			for segment in self._data:
				input_value = input_value + segment
		else:
			input_value = str(self._data)

		hasher = hashlib.sha1(input_value.encode())
		value = base64.b16encode(hasher.digest()[:10]).decode(globals.encoding)
		return f"{DNS_RECORD_CLASS_STRING[self._record_class]}::{DNS_RECORD_TYPE_STRING[self._record_type]}::{self._label}::{value}"
