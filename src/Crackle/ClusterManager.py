"""
The purpose of this module is to manage a cluster of server. Sometimes the test could involve a large number of nodes,
and in this case it's much better to distribute the load across a bunch of server, exploiting the network to communicate.

This module will be responsible of the following operations:

    - Installing the manager key on each one of the server in order get passwordless control
    - Executing ssh remote commands
    - Managing the shared networks

This module is configured through the configuration parameters in the settings.conf file. In details the following \
parameters have to be set:

    - The number of servers to exploit
    - The name of the servers
    - The name of the network interface used to connect the servers together. It could, for example, eth1 or enps1s0, \
    depending on the name strategy adopted by the machine.
    - The IP addresses of the servers
    - The password of the user crackle
    - The server where the router image is stored
    - The name of the router image to use

The syntax of this file is the following (example)::

        server_names = pirl-ndn-2.cisco.com
        interfaces = enp6s0
        ip_addresses = 10.60.17.168
        lxd_password = crackle

        image_server = pirl-ndn-5.cisco.com
        router_base_image = "ubuntu/icn_image2"

"""
import logging
import os
import subprocess
from itertools import cycle
from random import randint

from Crackle.LxcUtils import AddressGenerator, __router_network__, __gre_endpoints_network__

import requests
from requests import exceptions as req_except

from Crackle import Constants
from Crackle import Globals
from Crackle.AsyncManager import start_thread_pool
from Crackle.ColoredOutput import make_colored
from Crackle.Constants import __CERTIFICATE__
from Crackle.LxcUtils import create_router_image

module_logger = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings()

__interface__ = "interface"
__ip_address__ = "ip-address"
__gre_port__ = "gre{0}"
__tunnel_endpoint__ = "{0}tep"
__default_gateway_interface__ = "{0}int"


def generate_certificate(client_cert_path, client_key_path):
    """
    Create a new PEM certificate for identifying the client.

    :param client_cert_path: The location where the certificate file will be stored
    :param client_key_path: The location where the key file will be stored
    :return:
    """

    params = ["openssl",
              "req",
              "-x509",
              "-newkey",
              "rsa:4096",
              "-keyout",
              client_key_path,
              "-out",
              client_cert_path,
              "-subj",
              "/CN=www.cisco.com/L=Paris/O=Cisco/C=FR",
              "-nodes"]

    p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

    if p.wait():
        module_logger.error("Error generating the client cert.")
        print(make_colored("red", "Error generating the client cert."))
        raise RuntimeError
    else:
        module_logger.info("Client certificate correctly created.")


def generate_key_pair(ssh_client_private_key):
    """
    Generate a new public/private key pair

    :param ssh_client_private_key: The name of the file that will store the key
    :return:
    :raise: RuntimeError if the key creation fails
    """

    params = ["ssh-keygen",
              "-t",
              "rsa",
              "-b",
              "4096",
              "-C",
              "crackle@cisco.com",
              "-f",
              ssh_client_private_key,
              "-P",
              ""]

    p = subprocess.Popen(params)

    if p.wait():
        module_logger.error("Impossible to create the RSA key. Say bye bye to passwordless ssh.")
        print(make_colored("red", "Error generating the SSh rsa key pair."))
        raise RuntimeError
    else:
        module_logger.info("RSA key successfully generated.")


class Server:
    """
    This class describes a physical server that has to be used for the experiment.

    :ivar hostname: The DNS name of the server
    :ivar interface: The name of the interface of this server that will be used for inter-server communication
    :ivar ip_address: The IP address of the server
    :ivar container_gateway: The default gateway for the containers that will be instantiated on this server
    """
    def __init__(self, hostname, interface, ip_address, container_gateway, tunnel_endpoint):

        self.hostname = hostname
        self.interface = interface
        self.ip_address = ip_address
        self.container_gateway = container_gateway
        self.tunnel_endpoint = tunnel_endpoint

    def get_hostname(self):
        """
        Get the DNS name of the server
        :return: the DNS name of the server
        """

        return self.hostname

    def get_interface(self):
        """
        Get the interface name of the server
        :return: the interface name of the server
        """

        return self.interface

    def get_ip_address(self):
        """
        Get the IP address of the server
        :return: The IP address of the server
        """

        return self.ip_address

    def get_container_gateway(self):
        """
        Get the default gateway address for the containers created on this container
        :return: the default gateway address for the containers created on this container
        """
        return self.container_gateway

    def get_tunnel_endpoint(self):
        """"
        Get the ip address of the tunnel endpoint on this server (for this experiment)
        :return: the tunnel endpoint of the bridge on this server
        """
        return self.tunnel_endpoint

    def __str__(self):

        return self.hostname


class ClusterManager:
    """
    This class contains the methods used for setting up the server.
    The constructor receives the list with the names of the nodes of the experiment.

    :ivar server_list: The list of the server involved inthe experiment.
    :ivar username: The username used to SSH the remote servers
    :ivar lxd_password: The password used to install the LXD client certificate on the servers
    :ivar lxd_port: The port the LXD daemon is running on
    :ivar node_list: The list of nodes involved in the experiment.
    """

    def __init__(self, node_list=None):

        list_server_names = Globals.server_names.split(",")
        list_interfaces = Globals.interfaces.split(",")
        list_ip_addresses = Globals.ip_addresses.split(",")
        self.username = Globals.username
        self.lxd_password = Globals.lxd_password
        self.lxd_port = int(Globals.lxd_port)
        self.node_list = node_list

        self.server_list = []

        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)

        for server, interface, ip in zip(list_server_names, list_interfaces, list_ip_addresses):
            self.server_list.append(Server(server,
                                           interface,
                                           ip,
                                           AddressGenerator.get_ip_address(__router_network__),
                                           AddressGenerator.get_ip_address(__gre_endpoints_network__)))

    def get_server_list(self):
        """
        Return the list of servers involved in the experiment

        :return: The list of servers involved in the experiment
        """
        return self.server_list

    def setup_cluster(self):
        """
        Config the cluster in order to easily access to the machines and spawn the containers.
        This method performs the following operations:

            - Assign each container to a server
            - Install the LXD client certificate on each LXD Server
            - Install the SSH client key to each server in order to achieve passwordless SSH
            - Configure the connections between the OpenVirtualSwitches
            - Create the base router image, if it has not been created yet.

        :return: True if the setup successes, False otherwise
        """
        
        try:
            if self.install_lxd_key():
                self.logger.debug("LXD client certificate installed on the servers.")
            else:
                self.logger.error("Error installing LXD certificate on the servers")
                return False

            if self.install_ssh_key():
                self.logger.debug("SSH public key installed on the servers.")
            else:
                self.logger.error("Error installing SSH public key on the servers")
                return False

            if create_router_image():
                self.logger.debug("Router image created on {0}".format(Globals.image_server))
            else:
                self.logger.error("Error creating base router image on {0}".format(Globals.image_server))
                return False

            if self.assign_servers():
                self.logger.debug("ICN nodes correctly assigned to the servers.")
            else:
                self.logger.error("Error assigning the nodes to the servers")
                return False

            if self.configure_lxd_br_tunnel():
                self.logger.debug("Bridge {0} configured on the cluster {1}".format(Constants.LXD_BRIDGE,
                                                                                    self.server_list))
            else:
                self.logger.error("Error configuring bridge {0} on the servers {1}".format(Constants.LXD_BRIDGE,
                                                                                           self.server_list))
                return False

                # if self.install_ns3_script():
                #     self.logger.debug("NS3 script installed on servers {0}".format(self.server_list))
                # else:
                #     self.logger.error("Error installing ns3 script on the servers {0}".format(self.server_list))
                #     return False
        except req_except.ConnectionError as conn_err:
            self.logger.error("Error connecting to the server {0}. "
                              "Error: {1}".format(Globals.image_server,
                                                    conn_err))
            return False
        except req_except.Timeout as timeout_error:
            self.logger.error("Timeout connecting to the server {0}. "
                              "Error: {1}".format(Globals.image_server,
                                                  timeout_error))
            return False
        except req_except.TooManyRedirects as red_err:
            self.logger.error("Error connecting to the server {0}. "
                              "Error: {1}".format(Globals.image_server,
                                                  red_error))
            return False
        except req_except.RequestException as error:
            self.logger.error("Error connecting to the server {0}. "
                              "Error: {1}".format(Globals.image_server,
                                                  error))
            return False
        
        return True

    def install_ns3_script(self):
        """
        Put the local ns3 script in the servers of the cluster.

        :return: True if success, False otherwise
        """

        def install_script(server, results):
            params = ["scp",
                      "-i",
                      Constants.ssh_client_private_key,
                      Constants.ns3_script_local,
                      "{0}@{1}:{2}{3}scratch/".format(self.username,
                                                      server,
                                                      Globals.home_folder,
                                                      Globals.ns3_folder)]

            p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

            if p.wait():
                self.logger.error("[{0}] Error copying the ns3 script.".format(server))
                results[server] = False
                return
            else:
                self.logger.debug("[{0}] Ns3 script successfully copied!".format(server))

            params = ["ssh",
                      "-i",
                      Constants.ssh_client_private_key,
                      "{0}@{1}".format(self.username, server),
                      "cd {0}{1} && ./waf".format(Globals.home_folder, Globals.ns3_folder)]

            p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

            if p.wait():
                self.logger.error("[{0}] Error compiling ns3 script.".format(server))
                results[server] = False
                return
            else:
                self.logger.debug("[{0}] Ns3 script successfully compiled!".format(server))

            results[server] = True

        return start_thread_pool(self.server_list, install_script)

    def configure_lxd_br_tunnel(self):
        """
        Configure the open virtual switches in order to connect them together and modprobe the kernel module for
        enabling IP forwarding.

        :return: True if the setup succeeds, False otherwise
        """

        def setup_lxdbr(server, results):

            params = ["ssh",
                      "-i",
                      Constants.ssh_client_private_key,
                      "{0}@{1}".format(self.username, server),
                      "sudo ovs-vsctl --if-exists del-br {0} && "
                      "sudo ovs-vsctl --may-exist add-br {0}".format(Constants.LXD_BRIDGE)]

            p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

            if p.wait():
                self.logger.error("[{0}] Error creating the LXD bridge {1}.".format(server,
                                                                                    Constants.LXD_BRIDGE))
                results[server] = False
                return
            else:
                self.logger.debug("[{0}] LXD bridge {1} successfully created".format(server,
                                                                                     Constants.LXD_BRIDGE))

            params = ["ssh",
                      "-i",
                      Constants.ssh_client_private_key,
                      "{0}@{1}".format(self.username, server),
                      "sudo ip link set {0} up && "
                      "sudo ovs-vsctl --may-exist add-port {1} {2} tag={3} -- "
                      "set Interface {2} type=internal && "
                      "sudo sysctl fs.inotify.max_user_instances=512 && "
                      "sudo ovs-vsctl --may-exist add-port {1} {4} -- "
                      "set interface {4} type=internal && "
                      "sudo ip addr add {5}/16 brd + dev {4} && "
                      "sudo ip addr add {7}/16 brd + dev {2} && "
                      "sudo ip link set {4} up && "
                      "sudo ip link set {2} up && "
                      # "sudo iptables -t nat -F POSTROUTING && "
                      "sudo iptables -t nat -A POSTROUTING -o {0} -s {6}"
                      " ! -d {6} -j MASQUERADE".format(server.get_interface(),
                                                       Constants.LXD_BRIDGE,
                                                       __default_gateway_interface__.format(Globals.experiment_id),
                                                       Constants.router_vlan,
                                                       __tunnel_endpoint__.format(Globals.experiment_id),
                                                       server.get_tunnel_endpoint(),
                                                       __router_network__,
                                                       server.get_container_gateway())]

            p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

            if p.wait():
                self.logger.error("[{0}] Error setting interface {1} up. Params: {2}".format(server,
                                                                                             server.get_interface(),
                                                                                             params))
                results[server] = False
                return
            else:
                self.logger.debug(
                    "[{0}] Interface {1} set up. Params: {2}".format(server, server.get_interface(), params))

            for serv in [s for s in self.server_list if s.get_hostname() != server.get_hostname()]:
                params = ["ssh",
                          "-i",
                          Constants.ssh_client_private_key,
                          "{0}@{1}".format(self.username, server),
                          "sudo ovs-vsctl --if-exists del-port {0} {1} && "
                          "sudo ovs-vsctl --may-exist add-port {0} {1} -- "
                          "set interface {1} type=gre "
                          "options:remote_ip={2} options:local_ip={3} && "
                          "sudo ip route add {2}/32 dev {4}".format(Constants.LXD_BRIDGE,
                                                                    __gre_port__.format(serv.get_tunnel_endpoint()),
                                                                    serv.get_tunnel_endpoint(),
                                                                    server.get_tunnel_endpoint(),
                                                                    server.get_interface())]

                p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

                if p.wait():
                    self.logger.error("[{0}] Error adding interface {1} to bridge {2}. Params = {3}".format(server,
                                                                                                     server.get_interface(),
                                                                                                     Constants.LXD_BRIDGE,
                                                                                                     params))
                    results[server] = False
                    return
                else:
                    self.logger.debug("[{0}] Interface {1} correctly added to {2}".format(server,
                                                                                      server.get_interface(),
                                                                                      Constants.LXD_BRIDGE))

            params = ["ssh",
                      "-i",
                      Constants.ssh_client_private_key,
                      "{0}@{1}".format(self.username, server),
                      "sudo sysctl -w net.ipv4.ip_forward=1"]

            p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

            if p.wait():
                self.logger.error("[{0}] Error enabling sysctl.".format(server))
                results[server] = False
                return
            else:
                self.logger.debug("[{0}] Sysctl for IP forwarding enabled".format(server))
                results[server] = True

        return start_thread_pool(self.server_list, setup_lxdbr)

    def install_lxd_key(self):
        """
        Some operations with containers requires the client to be trusted by the server.
        So at the beginning we have to upload a (self signed) client certificate for each lxd daemon.

        :return: True if the certificate uploading succeeds, False otherwise
        """

        # First: check if the certificate exist, otherwise generate a new one:

        if not (os.path.isfile(Constants.lxd_client_cert_path) or os.path.isfile(Constants.lxd_client_key_path)):
            self.logger.info("No client certificate found. Generating a new one.")

            try:
                generate_certificate(Constants.lxd_client_cert_path, Constants.lxd_client_key_path)
            except RuntimeError:
                self.logger.error("Error creating certificate for client.")
                return False

        # Install LXD certificate on each one of the servers

        def install_cert(server, results):

            request = {
                "type": "client",
                "password": self.lxd_password
            }

            url = "{0}{1}{2}{3}{4}".format("https://",
                                           server,
                                           ":",
                                           self.lxd_port,
                                           __CERTIFICATE__)
            try:
                resp = requests.post(url=url,
                                     json=request,
                                     cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                                     verify=False)

                resp.raise_for_status()
            except req_except.HTTPError as http_error:
                self.logger.error("Error registering client certificate on LXD"
                                  " server {0}. Error: {1}".format(server,
                                                                   http_error.strerror))
                results[server] = False
                # return

            results[server] = True

        return start_thread_pool(self.server_list, install_cert)

    def assign_servers(self, node=None):
        """
        This function assign each container to a certain server in the cluster. The containers are evenly distributed
        over the servers.

        :param node_list: The list of nodes. Each node is a container
        :return:
        """
        if not node:
            servers = cycle(self.server_list)
            node_server_file = open(Constants.node_server_file, "w")

            for node, server in zip(self.node_list.values(), servers):
                node.set_server(server)
                node_server_file.write("{0} {1}".format(node, server))

            node_server_file.close()

            return True
        else:
            node.set_server(self.server_list[randint(0, len(self.server_list))])

    def clean_cluster(self):
        """
        Remove the bridge and the route entries created on the cluster.
        :return:
        """

        def clean_server(server, results):

            header = ["ssh",
                      "-i",
                      Constants.ssh_client_private_key,
                      "{0}@{1}".format(self.username, server)]

            commands = ["sudo ip route del {0}; ".format(serv.get_tunnel_endpoint())
                        for serv in self.server_list if serv.get_hostname() != server.get_hostname()]

            if len(commands):
                command = [" ".join(commands)]
            else:
                command = []

            command2 = ["sudo ovs-vsctl --if-exist del-br {0} && "
                        "sudo sysctl fs.inotify.max_user_instances=128 && "
                        "sudo iptables -t nat -D POSTROUTING -o {1} -s {2}  ! -d {2} -j MASQUERADE".format(Constants.LXD_BRIDGE,
                                                                                                           server.get_interface(),
                                                                                                           __router_network__)]
            params = header + command + command2

            p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

            if p.wait():
                self.logger.error("[{0}] Error cleaning the server. params: {1}".format(server,
                                                                                        params))
                results[server] = False
                return
            else:
                self.logger.debug("[{0}] Server cleaned. Params: {1}".format(server, params))
                results[server] = True

        start_thread_pool(self.server_list, clean_server)

    def install_ssh_key(self):
        """
        Create a new RSA key and install it on the servers in order to avoid to insert passwords each time.
        Of course the first time the user has to insert the password.

        :return: True if the key installation succeeds, False otherwise
        """

        if not (os.path.isfile(Constants.ssh_client_private_key) or os.path.isfile(Constants.ssh_client_public_key)):
            try:
                generate_key_pair(Constants.ssh_client_private_key)
            except RuntimeError:
                return False

        for server in self.server_list:
            params = ["ssh-copy-id",
                      "-i",
                      Constants.ssh_client_private_key,
                      "{0}@{1}".format(self.username,
                                       server)]

            print(params)

            p = subprocess.Popen(params, stderr=subprocess.DEVNULL)

            if p.wait():
                self.logger.error("[{0}] Impossible to install the RSA key.".format(server))
                return False
            else:
                self.logger.info("RSA key successfully generated.")
                
            return True
