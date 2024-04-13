import os
import queue
import threading

global args
global config
global DEBUG
global encoding
global logger
global timestamp_format
global wq

def init():
	global args
	global config
	global DEBUG
	global encoding
	global logger
	global timestamp_format
	global wq

	DEBUG				= True if os.getenv("DEBUG") is not None else False
	args				= None
	config				= None
	encoding			= "utf-8"
	logger				= None
	timestamp_format	= '%Y-%m-%d_%H:%M:%S'
	wq					= queue.Queue()


