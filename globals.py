import os

global config
global DEBUG
global args
global logger
global encoding

def init():
	global config
	global DEBUG
	global args
	global logger
	global encoding

	DEBUG		= True if os.getenv("DEBUG") is not None else False
	args		= None
	logger		= None
	config		= None
	encoding	= "utf-8"

