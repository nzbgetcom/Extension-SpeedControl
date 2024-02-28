#!/usr/bin/env python
#
# Speed limit extension script for NZBGet.
#
# Copyright (C) 2021 Andrey Prygunkov <hugbug@users.sourceforge.net>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with the program.  If not, see <http://www.gnu.org/licenses/>.
#

##############################################################################
### TASK TIME: *
### NZBGET SCHEDULER SCRIPT

# Sets speed limit based on category.
#
# This script monitors download queue and changes download speed limit
# depending on category of item being currently downloaded.
#
# To activate the script select it in option <Extensions>. NZBGet v19 or newer is requried.
#
# Info about script:
# Author: Andrey Prygunkov (nzbget@gmail.com).
# License: GPLv3 (http://www.gnu.org/licenses/gpl.html).
# PP-Script Version: 2.0.
#
# NOTE: This script requires Python 3.8+ to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

# Check interval (seconds).
#Interval=5

# Print more logging messages (yes, no).
#
# For debugging or if you need to report a bug.
#Verbose=no

# Click to test the script.
#Test@Check now

##############################################################################
### CATEGORIES                                                             ###

# Name of the category to monitor.
#Category1.Name=

# Speed limit for that category (KB).
#Category1.DownloadRate=0

### NZBGET SCHEDULER SCRIPT
##############################################################################

import os
import sys
import time
import signal
import urllib.request
import base64

# Script exit codes defined by NZBGet
SCRIPT_SUCCESS = 93
SCRIPT_ERROR = 94

# Check if the script is called from nzbget 19.0 or later
nzbget_version = float(os.environ.get('NZBOP_Version', '1')[0:4])
if nzbget_version < 19:
    print('*** NZBGet extension script ***')
    print('This script is supposed to be called from nzbget (19.0 or later).')
    sys.exit(SCRIPT_ERROR)

# Check if all script options are available
required_options = ('NZBPO_Interval', 'NZBPO_Interval')
for	optname in required_options:
	if (not optname in os.environ):
		print('[ERROR] Option %s is missing in configuration file. Please check script settings' % optname[6:])
		sys.exit(SCRIPT_ERROR)

# Check if the script is executed from settings page with a custom command
command = os.environ.get('NZBCP_COMMAND')
test_mode = command == 'Test'
if command != None and not test_mode:
	print('[ERROR] Invalid command ' + command)
	sys.exit(SCRIPT_ERROR)

# Init script options with values from NZBGet configuration file
interval = int(os.environ['NZBPO_Interval'])
verbose = os.environ['NZBPO_Verbose'] == 'yes'
default_speed = os.environ['NZBOP_DownloadRate']
default_speed = default_speed if default_speed != '' else 0

# Speed settings for categories
categories = []
for i in range(1, 100):
	cat_name = os.environ.get('NZBPO_CATEGORY' + str(i) + '_NAME')
	cat_speed = os.environ.get('NZBPO_CATEGORY' + str(i) + '_DOWNLOADRATE')
	if cat_name == None or cat_speed == None:
		break
	categories.append({'name': cat_name, 'speed': cat_speed})

# To get queue we connect to NZBGet via API.
# For more info visit http://nzbget.net/RPC_API_reference
# First we need to know connection info: host, port and password of NZBGet server.
# NZBGet passes all configuration options to extensions scripts as environment variables.
host = os.environ['NZBOP_CONTROLIP']
port = os.environ['NZBOP_CONTROLPORT']
username = os.environ['NZBOP_CONTROLUSERNAME']
password = os.environ['NZBOP_CONTROLPASSWORD']
if host == '0.0.0.0': host = '127.0.0.1'

# Flag indicating the script has been interrupted and must gracefully terminate
interrupted = False

# Print a message and flushe the buffers for immediate text sending
def print_log(msg):
	print(msg)
	sys.stdout.flush()

# Signal handler, executed when NZBGet asks the script to terminate (on NZBGet shutdown or reload)
def signal_handler(signum , address):
	print_log('Received SIGBREAK signal')
	global interrupted
	interrupted = True

# Install signal handler
if os.name == 'nt':
    signal.signal(signal.SIGBREAK, signal_handler)
else:
    signal.signal(signal.SIGINT, signal_handler)

# Connect to NZBGet and call an RPC-API-method without using of python's XML-RPC.
# XML-RPC is easy to use but it is slow for large amount of data
def call_nzbget_direct(json_request: str):

	# Building http-URL to call the method
	httpUrl = 'http://%s:%s/jsonrpc/' % (host, port) 
	request = urllib.request.Request(httpUrl)

	base64string = base64.b64encode(('%s:%s' % (username, password)).encode()).decode() 
	request.add_header('Authorization', 'Basic %s' % base64string)

	# Load data from NZBGet
	response = urllib.request.urlopen(request, data=json_request.encode('utf-8'))
	data = response.read().decode('utf-8')

	# "data" is a JSON raw-string
	return data

# Pause NZBGet download queue using XML-RPC
def pause_download():
	print_log('[WARNING] Pausing download')
	call_nzbget_direct('{"method": "pausedownload"}')

# Change speed limit in NZBGet using XML-RPC
def set_speed_limit(limit):
	print_log('[INFO] Setting speed limit to ' + str(limit))
	call_nzbget_direct('{"method": "rate", "params": [' + str(limit) + ']}')

# Set speed limit for category
def check_category(category):
	global categories, default_speed
	print_log('[INFO] Active category changed to ' + (category if category != '' else '<None>'))
	for cat in categories:
		if cat['name'].lower() == category.lower() and category != '':
			set_speed_limit(cat['speed'])
			return

	set_speed_limit(default_speed)

# Category of the active queue item, the last time we checked.
last_active_category = ''

# Check download queue and change speed limit if necessary
def check_queue():
	global last_active_category

	if verbose:
		print_log('Checking download queue')

	data = call_nzbget_direct('{"method": "listgroups", "params": [0]}')

	# The "data" is a raw json-string. We could use json.loads(data) to parse it but
	# json-module is slower because it creates entities for each json field, which
	# we don't need here. For better performance we parse json on our own.
	for line in data.splitlines():
		if line.startswith('"ActiveDownloads" : '):
			cur_threads = int(line[20:len(line)-1])
		elif line.startswith('"NZBName" : '):
			cur_name = line[13:len(line)-2]
		elif line.startswith('"Category" : '):
			cur_category = line[14:len(line)-2]
			if cur_threads > 0:
				if verbose:
					print_log('Current: [%s] - %s  (%s()' % (cur_threads, cur_name, cur_category))
				if cur_category != last_active_category:
					check_category(cur_category)
					last_active_category = cur_category
				break

	return

# In test-mode (when executed from settings page) - check once and exit
if test_mode:
	check_queue()
	sys.exit(SCRIPT_SUCCESS)

# Our script is launched as scheduler script at NZBGet start,
# the script never exits and works as long as NZBGet is running.
# Here we setup an ifinite loop where we periodically check the download queue.
# Alternatively we could check only once and let the user to configure
# the task scheduler in NZBGet to run the script periodically. This solution
# however has a disadvantage of script start overhead (python initializing, etc.).
# By running the script only once at NZBGet start we save the overhead,
# this allows us to perform volume checks much more often than we could
# with task scheduler. Even every second checks do not produce big system load.
while not interrupted:
	try:
		check_queue()
		time.sleep(interval)
	except Exception as e:
		if not interrupted:
			print_log('[ERROR] Exception: %s' % e)

if verbose:
	print_log('Exiting')

sys.exit(SCRIPT_SUCCESS)