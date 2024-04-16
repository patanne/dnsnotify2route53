import base64
import hashlib
import globals

from abc import ABC
from enum import IntEnum, auto


### ----- record type
class DNS_RECORD_TYPE(IntEnum):
	A		= 0
	CNAME	= auto()
	MX		= auto()
	NS		= auto()
	SOA		= auto()
	SRV		= auto()
	TXT		= auto()

DNS_RECORD_TYPE_STRING = \
[
	"A",
	"CNAME",
	"MX",
	"NS",
	"SOA",
	"SRV",
	"TXT"
]

DNS_RECORD_TYPE_DICT = \
	{
		"A":		DNS_RECORD_TYPE.A,
		"CNAME":	DNS_RECORD_TYPE.CNAME,
		"MX":		DNS_RECORD_TYPE.MX,
		"NS":		DNS_RECORD_TYPE.NS,
		"SOA":		DNS_RECORD_TYPE.SOA,
		"SRV":		DNS_RECORD_TYPE.SRV,
		"TXT":		DNS_RECORD_TYPE.TXT,
	}


### ----- record class
class DNS_RECORD_CLASS(IntEnum):
	IN	= 0

DNS_RECORD_CLASS_STRING = \
[
	"IN"
]

DNS_RECORD_CLASS_DICT = \
	{
		"IN": DNS_RECORD_CLASS
	}

