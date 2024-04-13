import globals
import json
import os
from collections import namedtuple

def load_config():
	config_file_path = os.path.join(os.path.dirname(__file__), "config.json")
	with open(config_file_path) as json_data:
		globals.config = json.load(json_data,object_hook=ConfigJsonDecode)
		json_data.close()

def ConfigJsonDecode(configDict):
	return namedtuple('Config', configDict.keys())(*configDict.values())

class Config:
	def __init__(self,listen_ip,notify_servers,domains_to_manage_from_aws,domains_to_manage):
		self.listen_ip					= listen_ip
		self.notify_servers				= notify_servers
		self.domains_to_manage_from_aws	= domains_to_manage_from_aws
		self.domains_to_manage			= domains_to_manage
