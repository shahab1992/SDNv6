#!/usr/bin/env python3

"""
The cluster version of Crackle has been splitted into 2 main parts:

    - The client part, quite similar to the previous version of crackle, that manages all the experiment
    - The server part, that executes the operations that before were executed locally.

It is important to have a server part since most of the times crackle needs to wait the termination of some operations.

"""
import json
import logging
import os
import socketserver
import subprocess
import threading
import time

import sys

import http.server

DEFAULT_LURCH_PORT = 65432

__CREATE_BRIDGE__ = "/create-bridge"
__DELETE_BRIDGE__ = "/delete-bridge"
__CREATE_TAP__ = "/create-tap"
__DELETE_TAP__ = "/delete-tap"
__ADD_INTERFACE__ = "/add-interface"
__REMOVE_INTERFACE__ = "/remove-interface"
__EXEC_CMD__ = "/exec-cmd"

__bridge_name__ = "bridge-name"
__address__ = "address"


def to_str_param(param):
    if type(param) is bytes:
        return param.decode()
    else:
        return param


def to_bytes_param(param):
    if type(param) is str:
        return param.encode()
    else:
        return param

class Server:
    """
    Implementation of the Server entity
    """

    def __init__(self, server_port=DEFAULT_LURCH_PORT):

        self.start = self.listen
        self.PORT = server_port
        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)

        while True:
            try:
                self.httpd = socketserver.TCPServer(("", server_port), CrackleServer)
                break
            except OSError:
                self.logger.warning("Port {} is busy. Will retry in 5s".format(server_port))
                time.sleep(5)

    def listen(self):
        logging.info("Server serving at port", self.PORT)
        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            pass

        self.httpd.server_close()

    def stop(self):
        self.httpd.shutdown()


class CrackleServer(http.server.BaseHTTPRequestHandler):
    """Implementation of the CLOUD entity"""

    def do_GET(self):

        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write("Crackle Server - running\n".encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Respond to a POST request."""
        if self.path.startswith(__CREATE_BRIDGE__):
            pass
        elif self.path.startswith(__CREATE_TAP__):
            pass
        elif self.path.startswith(__DELETE_BRIDGE__):
            pass
        elif self.path.startswith(__DELETE_TAP__):
            pass

        return

    def _create_bridge(self):
        """
        This function creates a linux bridge and assigns an address to it.

        :param bridge_name: Linux Bridge Identifier
        :param address: Ipv4 address of the bridge
        :return: The bridge_name of the bridge in case of successful creation, a RuntimeError otherwise
        :raises: :class:`RuntimeError` if there are problems creating the bridge
        """

        # Get the Json string..
        length = int(self.headers['Content-Length'])
        json_str = self.rfile.read(length).decode("utf-8")

        # ...and parse it!
        up_fields = json.loads(json_str)
        bridge_name = up_fields[__bridge_name__]
        address = up_fields[__address__]

        self.logger.debug("Creating bridge {0}".format(bridge_name))

        params = ["ip",
                  "link",
                  "add",
                  "bridge_name",
                  bridge_name,
                  "type",
                  "bridge"]

        p = subprocess.Popen(params, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if p.wait() == 2:
            self.logger.warning("Bridge {0} already exist".format(bridge_name))
        elif p.wait():
            self.logger.error("Impossible to create the bridge {0}".format(bridge_name))
            self.send_response(500)
            self.send_header("Content-type", "application/text")
            self.end_headers()
            self.wfile.write(to_bytes_param("Error creating the bridge {0}!".format(bridge_name)))
            return

        self.logger.debug("Setting bridge {0} up".format(bridge_name))

        params = ["ip",
                  "link",
                  "set",
                  bridge_name,
                  "up"]

        p = subprocess.Popen(params, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if p.wait():
            self.logger.error("Impossible to set up the bridge {0}".format(bridge_name))
            self.send_response(500)
            self.send_header("Content-type", "application/text")
            self.end_headers()
            self.wfile.write(to_bytes_param("Impossible to set up the bridge {0}".format(bridge_name)))
            return

        if address != "":

            self.logger.debug("Setting address {0} to the bridge {1}".format(address, bridge_name))

            params = ["ip",
                      "addr",
                      "add",
                      "dev",
                      bridge_name,
                      "{0}/24".format(address)]

            p = subprocess.Popen(params, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if p.wait() and p.wait() != 2:
                self.logger.error("Impossible to set the ip address of the bridge {0}".format(bridge_name))
                self.send_response(500)
                self.send_header("Content-type", "application/text")
                self.end_headers()
                self.wfile.write(to_bytes_param("Impossible to set up the bridge {0}".format(bridge_name)))
                return

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()


class ServerInstance(threading.Thread):
    """
    Run the Cloud/Proxy entity's algorithm
    """

    def __init__(self, server):
        """
        Create a new thread which run the specified server
         :param server: the server entity instance
        """

        threading.Thread.__init__(self)
        # set the thread to be killed when the main program exits
        self.daemon = True
        # server protocol instance
        self.server = server

    def run(self):
        # start the server
        self.server.listen()

    def stop(self):
        # stop the server
        self.server.stop()
        # wait until it stops
        self.join()

if __name__ == "__main__":

    if os.geteuid():
        print("The use of overlayfs requires privileged containers. Please run this program as superuser.")
        sys.exit(1)

    crackle_server = ServerInstance(Server())

    try:
        crackle_server.run()
    except KeyboardInterrupt:
        crackle_server.stop()
