#
# Copyright (C) 2024 Denis <denis@nzbget.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with the program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
from os.path import dirname
import os
import subprocess
import unittest
import http.server
import xmlrpc.server
import threading

SUCCESS = 93
NONE = 95
ERROR = 94

root = dirname(__file__)
test_data_dir = root + '/test_data/'
tmp_dir = root + '/tmp/'

host = '127.0.0.1'
username = 'TestUser'
password = 'TestPassword'
port = '6789'

def get_python(): 
	if os.name == 'nt':
		return 'python'
	return 'python3'

class Request(http.server.BaseHTTPRequestHandler):

	def do_POST(self):
		self.send_response(200)
		self.send_header("Content-Type", "text/xml")
		self.end_headers()
		data = '<?xml version="1.0" encoding="UTF-8"?><nzb></nzb>'
		response = xmlrpc.client.dumps((data,), allow_none=False, encoding=None)
		self.wfile.write(response.encode('utf-8'))

def run_script():
	sys.stdout.flush()
	proc = subprocess.Popen([get_python(), root + '/SpeedControl.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy())
	out, err = proc.communicate()
	proc.pid
	ret_code = proc.returncode
	return (out.decode(), int(ret_code), err.decode())

def set_defaults_env():
	# NZBGet global options
	os.environ['NZBPP_DIRECTORY'] = tmp_dir
	os.environ['NZBOP_CONTROLPORT'] = port
	os.environ['NZBOP_CONTROLIP'] = host
	os.environ['NZBOP_CONTROLUSERNAME'] = username
	os.environ['NZBOP_CONTROLPASSWORD'] = password

	# script options
	os.environ['NZBOP_Version'] = '20'
	os.environ['NZBPO_Verbose'] = 'no'
	os.environ['NZBPO_Interval'] = '5'
	os.environ['NZBOP_DownloadRate'] = '15'

class Tests(unittest.TestCase):

	def test_command(self):
		set_defaults_env()
		os.environ['NZBCP_COMMAND'] = 'Test'
		server = http.server.HTTPServer((host, int(port)), Request)
		thread = threading.Thread(target=server.serve_forever)
		thread.start()
		[_, code, _] = run_script()
		server.shutdown()
		thread.join()
		self.assertTrue(code, SUCCESS)


if __name__ == '__main__':
	unittest.main()
