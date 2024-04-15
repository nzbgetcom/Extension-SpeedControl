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
# along with the program.  If not, see <https://www.gnu.org/licenses/>.
#


import json
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

ROOT_DIR = dirname(__file__)
TEST_DATA_DIR = ROOT_DIR + "/test_data/"
TMP_DIR = ROOT_DIR + "/tmp/"

HOST = "127.0.0.1"
USERNAME = "TestUser"
PASSWORD = "TestPassword"
PORT = "6789"


def get_python():
    if os.name == "nt":
        return "python"
    return "python3"


class Request(http.server.BaseHTTPRequestHandler):

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.end_headers()
        data = '<?xml version="1.0" encoding="UTF-8"?><nzb></nzb>'
        response = xmlrpc.client.dumps((data,), allow_none=False, encoding=None)
        self.wfile.write(response.encode("utf-8"))


def run_script():
    sys.stdout.flush()
    proc = subprocess.Popen(
        [get_python(), ROOT_DIR + "/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
    )
    out, err = proc.communicate()
    proc.pid
    ret_code = proc.returncode
    return (out.decode(), int(ret_code), err.decode())


def set_defaults_env():
    # NZBGet global options
    os.environ["NZBPP_DIRECTORY"] = TMP_DIR
    os.environ["NZBOP_CONTROLPORT"] = PORT
    os.environ["NZBOP_CONTROLIP"] = HOST
    os.environ["NZBOP_CONTROLUSERNAME"] = USERNAME
    os.environ["NZBOP_CONTROLPASSWORD"] = PASSWORD

    # script options
    os.environ["NZBOP_Version"] = "20"
    os.environ["NZBPO_Verbose"] = "no"
    os.environ["NZBPO_Interval"] = "5"
    os.environ["NZBOP_Version"] = "24"
    os.environ["NZBOP_DownloadRate"] = "15"


class Tests(unittest.TestCase):

    def test_command(self):
        set_defaults_env()
        os.environ["NZBCP_COMMAND"] = "Test"
        server = http.server.HTTPServer((HOST, int(PORT)), Request)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        [_, code, _] = run_script()
        server.shutdown()
        server.server_close()
        thread.join()
        self.assertEqual(code, SUCCESS)

    def test_nzbget_version(self):
        set_defaults_env()
        os.environ["NZBOP_Version"] = "22"
        server = http.server.HTTPServer((HOST, int(PORT)), Request)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        [_, code, _] = run_script()
        server.shutdown()
        server.server_close()
        thread.join()
        self.assertEqual(code, ERROR)

        os.environ["NZBOP_Version"] = "24"
        server = http.server.HTTPServer((HOST, int(PORT)), Request)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        [_, code, _] = run_script()
        server.shutdown()
        server.server_close()
        thread.join()
        self.assertEqual(code, SUCCESS)

    def test_manifest(self):
        with open(ROOT_DIR + "/manifest.json", encoding="utf-8") as file:
            try:
                json.loads(file.read())
            except ValueError as e:
                self.fail("manifest.json is not valid.")


if __name__ == "__main__":
    unittest.main()
