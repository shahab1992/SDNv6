"""
The nodes described in the configuration files in fact are represented by means of linux containers.
This module exposes some API for creating, destroying, managing linux containers by wrapping the lxc python APIs.
Also it contains some functions for easily creating tap and bridges for connecting them together.
So while the class :class:`Crackle.NetworkManager.NetworkManager` sees topology, links and nodes at high level,
this class manages the connection and the nodes at low level.

Containers are configured in the following way:

    - The routers are connected together through a linux bridge. The virtual topology is then created on top of this \
    star topology by means of IPIP tunnels::

         -------0                                                   0-------
        | LxC-1 |\_                                               _/| LxC-5 |
        | Router|  \_                                           _/  | Router|
         -------     \_                                       _/     -------
                       \____________0=======0________________/
                                    \ Linux \\
                       _____________\ Bridge\________________
                     _/             0===0===0                \_
                   _/                   |                      \_
                  /                     |                        \\
             ----0--                    |                        0------
            | LxC-1 |                   |                       | LxC-4 |
            | Router|                   |                       | Router|
             -------                    |                        -------
                                        |
                                        |
                                     ---0---
                                    | LxC-3 |
                                    | Router|
                                     -------




    - The base stations have two network interfaces: one is connected to the same linux bridge of the routers while \
    the other is connected to the simulator NS-3::

         -------0                                                   0-------
        | Linux |\_                                               _/| Linux |
        | Bridge|  \_                                           _/  | Bridge|
         -------     \_                                   _____/     ---0---
                       \____________0=======0____________/              |
                                    \Base   \\                           |
                                    \Station\                           |
                                     =======                            |
                                                                        |
                                                                     ---0---
                                                                    | NS-3 |
                                                                    | Simul|
                                                                     -------

    - The mobile stations are connected to a linux bridge that is dynamically connected/disconnected to/from different \
     NS-3 processes (so different base stations) during the mobility::

                 -------                 -------
                | LxC   |_______________| Linux |
                |Station|               | Bridge|
                 -------                 -------

Putting all the pieces together, Routers and Base Stations are connected through a linux bridge. Then the base stations
are in turn connected to the simulator NS-3, one process per base station. Each simulator process provides some tap
interfaces through which the mobile stations can connect to the base station (exploiting the simulator).
"""
import logging
import random
import socket
import binascii
import ssl
import struct
import time

import Crackle.Globals
from Crackle import LxdAPI

import Crackle.Constants as Constants
from Crackle import Globals
from Crackle.ColoredOutput import make_colored
import subprocess


# Tap / Bridges templates
__bs_bridge__ = "{0}-br"
__bs_tap__ = "{0}-tap"
__sta_bridge__ = "{0}-mbr"

module_logger = logging.getLogger(__name__)

__router_network__ = "10.{0}.0.0/16".format(random.randint(0x05, 0xfe))
__base_station_network__ = "10.1.0.0/16"
__links_addresses__ = "10.2.0.0/16"
__gre_endpoints_network__ = "10.4.0.0/16"


def check_image(image_name):
    """
    Check if the image server contains a copy of the image that will be used for cloning the nodes in the network.

    :param image_name: The name of the image.
    :return: True if the image exist, false otherwise.
    :raise: Runtime error if the image server is not reachable
    """

    images = LxdAPI.list_images(server=Globals.image_server)

    if any(image.endswith(image_name)
           for image in images):
        return True
    else:
        return False


def create_router_image():
    """
    Create the base image that will be used for cloning the other containers

    :return:
    """

    if check_image(Globals.router_base_image):
        return True

    container_name = "icn-router-base-container"

    # Get an image of ubuntu 14.04 for amd64

    image_description = {
        "name": container_name,  # 64 chars max, ASCII, no slash, no colon and no comma
        "architecture": "x86_64",
        "profiles": ["default"],  # List of profiles
        "ephemeral": False,  # Whether to destroy the container on shutdown
        "config": {},
        "devices": {
            "eth0": {
                "name": "eth0",
                "nictype": "bridged",
                "parent": "lxdbr0",
                "type": "nic"
            }
        },  # Config override.
        "source": {"type": "image",  # Can be: "image", "migration", "copy" or "none"
                   "mode": "pull",  # One of "local" (default) or "pull"
                   "server": "https://cloud-images.ubuntu.com/releases/",  # Remote server (pull mode only)
                   "protocol": "simplestreams",  # Protocol (one of lxd or simplestreams, defaults to lxd)
                   "alias": "xenial"}  # Name of the alias
    }

    # try:
    #     LxdAPI.create_container(description=image_description,
    #                             server=Globals.image_server,
    #                             error_message="Impossible to create the router base image.",
    #                             success_message="Router base image successfully created!")
    # except RuntimeError:
    #     module_logger.error("Error creating the router base image.")
    #     return False
    #
    # # Install ICN software in the container
    # print(make_colored("blue", "Installing ICN software on base node. This operation may require some time."))
    # module_logger.info("Pushing script for installing ICN software inside the container.")
    #
    # try:
    #     LxdAPI.push_file(server=Globals.image_server,
    #                      container=container_name,
    #                      source_path="../scripts/init_container.sh",
    #                      destination_path="/root/init_container.sh",
    #                      mode={Constants.__header_X_LXD_gid__: "0",
    #                            Constants.__header_X_LXD_uid__: "0",
    #                            Constants.__header_X_LXD_mode__: "700"})
    # except RuntimeError:
    #     module_logger.error("Error pushing installation script on router base image.")
    #     return False
    #
    # module_logger.info("Pushing script for changing password in container")
    #
    # try:
    #     LxdAPI.push_file(server=Globals.image_server,
    #                      container=container_name,
    #                      source_path="../scripts/ch_password.sh",
    #                      destination_path="/root/ch_password.sh",
    #                      mode={Constants.__header_X_LXD_gid__: "0",
    #                            Constants.__header_X_LXD_uid__: "0",
    #                            Constants.__header_X_LXD_mode__: "700"})
    # except RuntimeError:
    #     module_logger.error("Error pushing change password script on router base image.")
    #     return False
    # module_logger.info("Executing installation script on router base container, "
    #                    "in order to install the ICN software on it.")
    # try:
    #    LxdAPI.start_container(Globals.image_server,
    #                           container_name)
    # except RuntimeError:
    #     module_logger.error("Error starting the base router container.")
    #     return False

    # try:
    #     LxdAPI.exec_cmd(server=Globals.image_server,
    #                     container=container_name,
    #                     cmd=["/root/init_container.sh"],
    #                     environment={"HOME": "/root", "USER": "root"},
    #                     interactive=False,
    #                     output=True)
    #     time.sleep(3)
    # except RuntimeError:
    #     module_logger.error("Error executing the startup script on the base router image.")
    #     return False

    # params = ["ssh",
    #           "-i",
    #           Constants.ssh_client_private_key,
    #           "{0}@{1}".format(Globals.username, Globals.image_server),
    #           "lxc exec {0} /root/init_container.sh".format(container_name)]
    # p = subprocess.Popen(params)
    # if p.wait():
    #     module_logger.error("Error executing installation script on router base image.")
    #     return False

    try:
        LxdAPI.stop_container(Globals.image_server,
                              container_name)
    except RuntimeError:
        module_logger.error("Error stopping the base router container.")
        return False

    # Create router Image for next usages, starting from the container just configured

    publish_description = {

        "public": True,  # Whether the image can be downloaded by untrusted users  (defaults to false)
        "properties": {  # Image properties (optional)
            "os": "Ubuntu",
            "architecture": "x86_64",
            "description": "Ubuntu 14.04 image with ICN software already installed",
        },
        "source": {
            "type": "container",  # One of "container" or "snapshot"
            "name": "icn-router-base-container"
        }
    }

    try:
        fingerprint = LxdAPI.publish_image(server=Globals.image_server, publish_description=publish_description)
    except RuntimeError:
        module_logger.error("Error publishing router base image.")
        return False

    # Set an alias for the image

    try:
        LxdAPI.set_alias(server=Globals.image_server,
                         image_fingerprint=fingerprint,
                         alias=Globals.router_base_image)
    except RuntimeError:
        module_logger.error("Error setting ALIAS {0} for base router image.")
        return False

    try:
        LxdAPI.delete_container(server=Globals.image_server, container=container_name)
    except RuntimeError:
        module_logger.error("Error deleting base router container after image creation.")
        return False

    return True


def create_tap_device(tap_name, server, vlan):
    """
    Create a tap device and set it to work in promiscous mode.

    :param tap_name: The name of the tap device to create.
    :param server: The server on which create the tap device
    :return:
    :raises: :class:`RuntimeError` if it's not possible to create the tap.
    """

    module_logger.debug("Creating tap device {0}".format(tap_name))

    params = ["ssh",
              "-i",
              Constants.ssh_client_private_key,
              "{0}@{1}".format(Globals.username, server),
              "sudo ip tuntap add name {0} mode tap".format(tap_name)]

    p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

    if not p.wait():
        module_logger.info("Tap {0} correctly created!".format(tap_name))
    elif p.wait() == 1:
        module_logger.warning("Tap {0} already exists.".format(tap_name))
    else:
        module_logger.error("Error creating tap {0}. Params: {1}".format(tap_name, params))
        raise RuntimeError

    module_logger.debug("Setting promisc mode and address 0.0.0.0 to tap {0} "
                        "and connecting it to the LXD bridge".format(tap_name))

    params = ["ssh",
              "-i",
              Constants.ssh_client_private_key,
              "{0}@{1}".format(Globals.username, server),
              "sudo ip addr add dev {0} 0.0.0.0 && "
              "sudo ip link set dev {0} promisc on && "
              "sudo ip link set {0} up && "
              "sudo ovs-vsctl --may-exist add-port {1} {0} tag={2}".format(tap_name,
                                                                           Constants.LXD_BRIDGE,
                                                                           vlan)]

    p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

    if not p.wait():
        module_logger.info("Tap {0} correctly configured and added to {1}!".format(tap_name,
                                                                                   Constants.LXD_BRIDGE))
    else:
        module_logger.error("Error configuring tap {0}. Params: {1}".format(tap_name, params))
        print(make_colored("red", "Error configuring tap {0}".format(tap_name)))
        raise RuntimeError


class AddressGenerator:
    """
    The purpose of this class is to generate sequential deterministic MAC/IP addresses
    in order to assign them to the node in the network.
    """

    mac_address = 0x00163e000000
    router_ip_address = struct.unpack(">I", socket.inet_aton(__router_network__[:-3]))[0]
    bs_ip_address = 0x0a010000
    link_ip_address = 0x0a020000
    gre_endpoint_start_address = 0x0a040000
    gre_endpoint_final_address = 0x0a04fffe

    @staticmethod
    def get_mac_address():
        """
        Generate a new mac address to assign to the containers created.

        :return: The MAC address
        """
        AddressGenerator.mac_address += 1
        return ':'.join(map(''.join, zip(*[iter(hex(AddressGenerator.mac_address)[2:].zfill(12))]*2)))

    @staticmethod
    def get_ip_address(network):
        """
        Generate a new ip address to assign to the containers created.

        :return: The MAC address
        """

        if network == __base_station_network__:
            AddressGenerator.bs_ip_address += 1
            return socket.inet_ntoa(struct.pack('>I', AddressGenerator.bs_ip_address))
        elif network == __router_network__:
            AddressGenerator.router_ip_address += 1
            return socket.inet_ntoa(struct.pack('>I', AddressGenerator.router_ip_address))
        elif network == __links_addresses__:
            AddressGenerator.link_ip_address += 1
            return socket.inet_ntoa(struct.pack('>I', AddressGenerator.link_ip_address))
        elif network == __gre_endpoints_network__:
            return socket.inet_ntoa(struct.pack('>I', random.randint(AddressGenerator.gre_endpoint_start_address,
                                                                     AddressGenerator.gre_endpoint_final_address)))
        else:
            raise RuntimeError


class RouterContainer:
    """
    This class represents the container associated to a router. It is a wrapper of the :class:`lxc.Container` class.
    It adds to it the name of the bridge to which the container is connected.

    :ivar bridge_eth0: The bridge to which the veth associated to the interface eth0 of the container is connected.
    """

    def __init__(self, name):
        """
        Create a new router container

        :param name: The name of the container
        """

        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)
        self.logger.debug("Creating routing container {0}".format(name))

        self.bridge_eth0 = ""
        self.server = None
        self.name = name
        self.veth0_name = name
        self.vlan = Constants.router_vlan

        self.router_ip_address = AddressGenerator.get_ip_address(__router_network__)
        self.router_mac_address = AddressGenerator.get_mac_address()

        self.map_interface_ip_address = {}
        self.map_interface_mac_address = {}

        self.description = {

            "name": self.name,  # 64 chars max, ASCII, no slash, no colon and no comma
            "architecture": "x86_64",
            "profiles": ["default"],  # List of profiles
            "ephemeral": True,  # Whether to destroy the container on shutdown
            "config": {
                "user.network_mode": "link-local"
            },
            "devices": {
                "eth0": {
                    "name": "eth0",
                    "nictype": "p2p",
                    "type": "nic",
                    "hwaddr": self.router_mac_address,
                    "host_name": "{0}".format(self.veth0_name),
                }
            },  # Config override.
            "source": {"type": "image",  # Can be: "image", "migration", "copy" or "none"
                       "mode": "pull",  # One of "local" (default) or "pull"
                       "server": "https://{0}:{1}".format(Globals.image_server,
                                                          Globals.lxd_port),  # Remote server (pull mode only)
                       "protocol": "lxd",  # Protocol (one of lxd or simplestreams, defaults to lxd)
                       "alias": Globals.router_base_image
                       }
        }

    def set_bridge_eth0(self, bridge_eth0):
        """
        Set the bridge associated to the interface eth0.

        :param bridge_eth0: The bridge to associate
        """

        self.bridge_eth0 = bridge_eth0

    def delete_neighbor(self, neighbor):
        """
        Delete interface relations
        :return:
        """

        del self.map_interface_ip_address[neighbor]

    def get_bridge_eth0(self):
        """
        Get the bridge associated to the interface eth0.
        :return: The bridge associated to the interface eth0.
        """
        return self.bridge_eth0

    def get_mac_address(self, neighbor=None):
        """
        Return the MAC address associated to the underlying container.

        :param neighbor: The interface toward a certain node
        :return: The MAC address of the underlying container.
        """

        if neighbor is None:
            return self.router_mac_address
        else:
            return self.map_interface_mac_address[neighbor]

    def set_ip_address(self, neighbor, ip_address):
        """
        Set the IP address of the container.

        :param ip_address: The ip address of the container
        :return:
        """

        self.map_interface_ip_address[neighbor] = ip_address

    def set_mac_address(self, mac_address, neighbor):
        """
        Set the mac address of

        :param neighbor: The interface toward the neighbor node
        :param mac_address: The mac address to set
        :return:
        """

        self.map_interface_mac_address[neighbor] = mac_address
        return self

    def get_ip_address(self, neighbor=None):
        """
        Get the IP address of the underlying linux container.

        :param neighbor: The interface toward the neighbor node
        :return: The IP address of the underlying linux container (eventually of the neighbor interface)
        """

        if neighbor is None:
            return self.router_ip_address
        else:
            return self.map_interface_ip_address[neighbor]

    def set_server(self, server):
        """
        Return the server on which this container will be (has been) spawn (spawned)

        :param server: The DNS name of the server
        """
        self.server = server

    def get_server(self):
        """
        Return the server on which this container will be (has been) spawn (spawned)
        :return: The bridge associated to the interface eth0.
        """
        return self.server

    def set_vlan(self, vlan):
        """
        Set the vlan of this container

        :param server: The vlan for the linux container
        """
        self.vlan = vlan

    def get_vlan(self):
        """
        Return the vlan of this lnux container
        :return: The vlan associated to the interface eth0.
        """
        return self.vlan

    def get_status(self):
        """
        Return the current status of the container.

        :return:
        """

        try:
            status = LxdAPI.get_container_status(self.server,
                                                 self.name)
        except RuntimeError:
            print(make_colored("red", "[{0}] Error retrieving container status. "
                                      "See log for futher details.".format(self.name)))
            self.logger.error("[{0}] Error retrieving container status. See log for futher details.")
            return False

        return status

    def spawn_container(self):
        """
        Spawn container on the right server.

        :return:
        """

        try:  
            image_server_certificate = ssl.get_server_certificate((Globals.image_server, Globals.lxd_port),
                                                     ssl_version=ssl.PROTOCOL_TLSv1_2)
        except Exception as error:
            self.logger.error("[{0}] Error retrieving server certificate. "
                              "Error: {1}".format(Globals.image_server,
                                                  error))

        if self.server is None:
            self.logger.error("[{0}] Impossible to spawn the container. "
                              "Server on which launch the container not set.".format(self.name))
            raise RuntimeError

        # open certificate

        self.description["source"]["certificate"] = image_server_certificate

        try:

            LxdAPI.create_container(description=self.description,
                                    server=self.server)
        except RuntimeError:
            print(make_colored("red", "[{0}] Error spawning container. See log for futher details.".format(self.name)))
            self.logger.error("[{0}] Error spawning container. See log for futher details.")
            return False

        return True

    def stop_container(self, async=False):
        """
        Stop the container. **Remember that in this architecture stopping a node means to destroy it!**

        :return:
        """

        if self.server is None:
            self.logger.error("[{0}] Impossible to stop the container. "
                              "Server on which launch the container not set. (Strange behavior!).".format(self.name))
            raise RuntimeError

        try:
            LxdAPI.stop_container(self.server,
                                  self.name,
                                  async)
        except RuntimeError:
            module_logger.error("[{0}] Error stopping the container.".format(self.name))
            return False

        return True

    def delete_container(self):
        """
        Delete the container after the experiment.

        :return:
        """

        if self.server is None:
            self.logger.error("[{0}] Impossible to delete the container. "
                              "Server on which launch the container not set. (Strange behavior!).".format(self.name))
            raise RuntimeError

        try:
            LxdAPI.delete_container(self.server,
                                    self.name)
        except RuntimeError:
            module_logger.error("[{0}] Error deleting the container.".format(self.name))
            return False

        return True

    def start_container(self):
        """
        Start the container.

        :return:
        """

        if self.server is None:
            self.logger.error("[{0}] Impossible to start the container. "
                              "Server on which launch the container not set. (Strange behavior!).".format(self.name))
            raise RuntimeError

        try:
            LxdAPI.start_container(self.server,
                                   self.name)
            LxdAPI.exec_cmd(server=self.server,
                            container=self.name,
                            cmd=["service", "nfd", "stop"],
                            environment={"HOME": "/root", "USER": "root"},
                            interactive=False,
                            check_return=False,
                            output=False)
        except RuntimeError:
            module_logger.error("[{0}] Error stopping the container.".format(self.name))
            return False

        time.sleep(3)
        params = ["ssh",
                  "-i",
                  Constants.ssh_client_private_key,
                  "{0}@{1}".format(Globals.username, self.server),
                  "lxc exec {1} /root/ch_password.sh && "
                  "sudo ovs-vsctl --if-exists del-port {0} {1} && "
                  "sudo ovs-vsctl --may-exist add-port {0} {1} tag={3} && "
                  "lxc exec {1} ip addr add {2}/16 brd + dev eth0 && "
                  "lxc exec {1} ip route add default via {4}".format(Constants.LXD_BRIDGE,
                                                                     self.veth0_name,
                                                                     self.router_ip_address,
                                                                     self.vlan,
                                                                     self.server.get_container_gateway())]

        p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

        if p.wait():
            self.logger.error("[{0}] Error adding interface {1} to bridge {2}.".format(self.server,
                                                                                       self.veth0_name,
                                                                                       Constants.LXD_BRIDGE))
            return False
        else:
            self.logger.debug("[{0}] Interface {1} correctly added to {2}".format(self.server,
                                                                                  self.veth0_name,
                                                                                  Constants.LXD_BRIDGE))
        return True

    def pull_file(self, source_path, dest_path):
        """
        Download a file from the container.

        :param source_path: The location of the file inside the container
        :param dest_path: The destination of the file in the host
        :return: True if the file pull succeed, false otherwise
        """

        self.logger.info("[{0}] Pulling file {1}. Destination: {2}".format(self.name,
                                                                           source_path,
                                                                           dest_path))

        try:
            LxdAPI.pull_file(server=self.server,
                             container=self.name,
                             source_path=source_path,
                             destination_path=dest_path,
                             mode={Constants.__header_X_LXD_gid__: "0",
                                   Constants.__header_X_LXD_uid__: "0",
                                   Constants.__header_X_LXD_mode__: "700"})
        except RuntimeError:
            self.logger.error("[{0}] Error pushing file {1} to {2}.".format(self.name,
                                                                            source_path,
                                                                            dest_path))
            return False

        # port = random.randint(5000, 10000)
        #
        # params = ["ssh",
        #           "-i",
        #           Constants.ssh_client_private_key,
        #           "-NL",
        #           "{1}:{0}:22".format(self.get_ip_address(),
        #                               port),
        #           "{0}@{1}".format(Constants.username,
        #                            self.get_server())]
        #
        # params1 = ["scp -r -P {0} ubuntu@localhost:{1} {2}".format(port, source_path, dest_path)]
        #
        # p1 = subprocess.Popen(params)
        # time.sleep(1)
        # p2 = subprocess.Popen(params1)
        #
        # ret = p2.wait()
        #
        # p1.kill()

        return True

    def push_file(self, source_path, dest_path):
        """
        Push a file inside the container.

        :param source_path: The location of the file to push
        :param dest_path: The path of the file inside the container

        :return: True if the push succeed, False otherwise
        """

        self.logger.info("[{0}] Pushing file {1} inside the container ({2})".format(self.name,
                                                                                    source_path,
                                                                                    dest_path))

        try:
            LxdAPI.push_file(server=self.server,
                             container=self.name,
                             source_path=source_path,
                             destination_path=dest_path,
                             mode={Constants.__header_X_LXD_gid__: "0",
                                   Constants.__header_X_LXD_uid__: "0",
                                   Constants.__header_X_LXD_mode__: "700"})
        except RuntimeError:
            self.logger.error("[{0}] Error pushing file {1} to {2}.".format(self.name,
                                                                            source_path,
                                                                            dest_path))
            return False

        return True

    def run_command(self, params, check_return=True, interactive=False, websocket=False, output=False, sync=True):
        """
        Run a command inside the container.

        :param params: The list with the command and the parameters
        :param sync: If the command has to be executed in a sync or async manner
        :param output: If the output of the command has to be printed to stdout
        :param interactive: If the command requires an interactive session
        :return:
        """

        try:
            LxdAPI.exec_cmd(server=self.server,
                            container=self.name,
                            cmd=params,
                            environment={"HOME": "/root", "USER": "root"},
                            interactive=interactive,
                            output=output,
                            websocket=websocket,
                            check_return=check_return,
                            sync=sync)
        except RuntimeError:
            self.logger.error("[{0}] Error executing command {1}".format(self.name, params))
            return False

        return True


class BaseStationContainer(RouterContainer):
    """
    This class represents the container associated to a base station.
    It contains the reference to linux kernel tools used to connect the container with:

        - The ns3 simulation (bs_bridge + bs_tap)
        - The other stations (sta_taps list)

    :ivar ns3_simulation: The ns3 simulation to which the base station container is attached
    :ivar bridge_wlan0: The bridge to which the veth associated to the interface wlan0 of the container is connected.
    :ivar simulator_tap: The name of the tap through which the container connects to the simulator
    :ivar sta_taps: The list of taps associated to the mobile stations that can connect to the base station
    """

    def __init__(self, name):
        """
        Create a new BaseStationContainer.

        :param: name -> The name of the container
        """

        RouterContainer.__init__(self, name)
        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)
        self.logger.debug("Creating base station container {0}".format(name))

        self.ns3_simulation = None

        self.bs_ip_address = AddressGenerator.get_ip_address(__base_station_network__)
        self.bs_mac_address = AddressGenerator.get_mac_address()

        self.vwlan0_name = "bs-{0}".format(self.name)

        self.sta_taps = []
        self.simulator_tap = ""
        self.bs_vlan = Constants.base_station_vlan

        self.description = {

            "name": self.name,  # 64 chars max, ASCII, no slash, no colon and no comma
            "architecture": "x86_64",
            "profiles": ["default"],  # List of profiles
            "ephemeral": True,  # Whether to destroy the container on shutdown
            "config": {
                "user.network_mode": "link-local"
            },
            "devices": {
                "eth0": {
                    "name": "eth0",
                    "nictype": "p2p",
                    "type": "nic",
                    "hwaddr": self.router_mac_address,
                    "host_name": "{0}".format(self.veth0_name)
                },
                "wlan0": {
                    "name": "wlan0",
                    "nictype": "p2p",
                    "type": "nic",
                    "hwaddr": self.bs_mac_address,
                    "host_name": "{0}".format(self.vwlan0_name)
                },
            },  # Config override.
            "source": {"type": "image",  # Can be: "image", "migration", "copy" or "none"
                       "mode": "pull",  # One of "local" (default) or "pull"
                       "server": "https://{0}:{1}".format(Globals.image_server,
                                                          Globals.lxd_port),  # Remote server (pull mode only)
                       "protocol": "lxd",  # Protocol (one of lxd or simplestreams, defaults to lxd)
                       "alias": Globals.router_base_image
                       }
        }

    def set_bridge_wlan0(self, bridge_wlan0):
        """
        Set the bridge associated to the interface wlan0.

        :param bridge_wlan0: The bridge to associate
        """
        self.bridge_wlan0 = bridge_wlan0

    def set_simulator_tap(self, tap):
        """
        Connect the container to the NS3 interface by bridging container and simulator.

        :param tap: The L2 interface of the simulator
        :return: True if the operation succeed, False otherwise
        """

        # self.logger.debug("Connecting simulator to container {0}".format(self.name))

        self.simulator_tap = tap
        try:
            create_tap_device(tap, self.server, self.bs_vlan)
        except RuntimeError:
            return False

        return True

    def set_ns3_simulation(self, ns3_simulation):
        """
        Set the simulator associated to this base station.
        :param ns3_simulation:  The name of the simulator process
        :return:
        """
        self.ns3_simulation = ns3_simulation
        return self

    def get_ns3_simulation(self):
        """
        Return the name of the simulator process associated to the base station.
        :return:
        """
        return self.ns3_simulation

    def add_sta_tap(self, tap, vlan):
        """
        Add a tap for connecting the station to this simulation.

        :param tap: The name of the tap interface
        :return:
        """
        if tap not in self.sta_taps:
            self.sta_taps.append(tap)

        try:
            create_tap_device(tap, self.server, vlan)
        except RuntimeError:
            return False

        return True

    def set_bs_vlan(self, vlan):
        """
        Set the vlan associated to the base station interface

        :param vlan: The vlan of the base station
        """
        self.bs_vlan = vlan

    # def get_bs_ip_address(self):
    #     """
    #     Get the IP address associated to the base station.
    #
    #     :return: The IP address of the base station
    #     """
    #
    #     return self.bs_ip_address

    def get_ip_address(self, neighbor=None):
        """
        Get the IP address of the underlying linux container.

        :param neighbor: The interface toward the neighbor node
        :return: The IP address of the underlying linux container (eventually of the neighbor interface)
        """

        try:
            return self.map_interface_ip_address[neighbor]
        except KeyError:
            return self.bs_ip_address

    def get_mac_address(self, neighbor=None):
        """
        Return the MAC address associated to the underlying container.

        :param neighbor: The interface toward a certain node
        :return: The MAC address of the underlying container.
        """

        try:
            return self.map_interface_mac_address[neighbor]
        except KeyError:
            return self.bs_mac_address

    def get_bs_vlan(self):
        """
        Return the vlan associated to the base station interface
        :return: The vlan associated to the interface wlan0.
        """
        return self.bs_vlan

    def start_container(self):
        """
        Start the container.

        :return:
        """

        if self.server is None:
            self.logger.error("[{0}] Impossible to start the container. "
                              "Server on which launch the container not set. (Strange behavior!).".format(self.name))
            raise RuntimeError

        try:
            LxdAPI.start_container(self.server,
                                   self.name)
        except RuntimeError:
            self.logger.error("Error stopping the base router container.")
            return False

        time.sleep(3)

        params = ["ssh",
                  "-i",
                  Constants.ssh_client_private_key,
                  "{0}@{1}".format(Globals.username, self.server),
                  "lxc exec {1} /root/ch_password.sh && "
                  "sudo ovs-vsctl --if-exists del-port {0} {1} && "
                  "sudo ovs-vsctl --if-exists del-port {0} {2} && "
                  "sudo ovs-vsctl --may-exist add-port {0} {1} tag={3} && "
                  "sudo ovs-vsctl --may-exist add-port {0} {2} tag={4} && "
                  "lxc exec {1} ip addr add {5}/16 brd + dev eth0 && "
                  "lxc exec {1} ip addr add {6}/16 brd + dev wlan0 && "
                  "lxc exec {1} ip route add default via {7}".format(Constants.LXD_BRIDGE,
                                                                     self.veth0_name,
                                                                     self.vwlan0_name,
                                                                     self.vlan,
                                                                     self.bs_vlan,
                                                                     self.router_ip_address,
                                                                     self.bs_ip_address,
                                                                     self.server.get_container_gateway())]

        p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

        if p.wait():
            self.logger.error("[{0}] Error adding interface {1} {2} to bridge {3}.".format(self.server,
                                                                                           self.veth0_name,
                                                                                           self.vwlan0_name,
                                                                                           Constants.LXD_BRIDGE))
            return False
        else:
            self.logger.debug("[{0}] Interface {1} {2} correctly added to {3}".format(self.server,
                                                                                      self.veth0_name,
                                                                                      self.vwlan0_name,
                                                                                      Constants.LXD_BRIDGE))
        return True


class StationContainer(RouterContainer):
    """
    This class represents the linux container associated to a mobile station.
    """

    def __init__(self, name):
        RouterContainer.__init__(self, name)
        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)
        self.logger.debug("Creating station {0}".format(name))

        # self.map_interface_ip_address = {}
        # self.map_interface_mac_address = {}

        self.map_interface_vlan = {}
        self.map_interface_intname = {}
        self.configured = False

    def get_mac_address(self, base_station):
        """
        Return the MAC address of an interface associated to a certain base station

        :param base_station: The base station the mac address is associated to
        :return: The MAC address of the interface associated to the base station
        """

        return self.map_interface_mac_address[base_station]

    # def get_station_ip_address(self, base_station):
    #     """
    #     Return the IP address of the interface used to connect to the base station bs
    #
    #     :param base_station: The base station associated to the ip address
    #     :return: The IP address associated to the base station bs
    #     """
    #
    #     return self.map_interface_ip_address[base_station][0]

    def setup_network_interfaces(self, base_station_list, vlans):

        if not self.configured:
            devices = {}

            devices["eth0"] = {
                "name": "eth0",
                "nictype": "p2p",
                "type": "nic",
                "hwaddr": self.router_mac_address,
                "host_name": self.name
            }

            i = 0

            for bs in base_station_list:

                mac_address = AddressGenerator.get_mac_address()

                devices[str(bs)] = {
                    "name": str(bs),
                    "nictype": "p2p",
                    "type": "nic",
                    "hwaddr": mac_address,
                    "host_name": "{0}-{1}".format(self.name, str(bs))
                }

                ip_addr = AddressGenerator.get_ip_address(__base_station_network__)

                while ip_addr in ["0.0.0.0", "255.255.255.255"]:
                    ip_addr = AddressGenerator.get_ip_address(__base_station_network__)

                # self.map_interface_ip_address[bs] = [ip_addr,
                #                                      vlans[i],
                #                                      "{0}-{1}".format(self.name, str(bs)),
                #                                      bs.get_bs_ip_address(),
                #                                      mac_address]
                self.map_interface_ip_address[bs] = ip_addr
                self.map_interface_mac_address[bs] = mac_address
                self.map_interface_vlan[bs] = vlans[i]
                self.map_interface_intname[bs] = "{0}-{1}".format(self.name, str(bs))

                i += 1

            self.description["devices"] = devices

            self.configured = True

    def get_vlan(self, bs):
        """
        Return the vlan associated to the base station.

        :param bs:
        :return:
        """

        return self.map_interface_vlan[bs]

    def start_container(self):
        """
        Start the container.

        :return:
        """

        if self.server is None:
            self.logger.error("[{0}] Impossible to start the container. "
                              "Server on which launch the container not set. (Strange behavior!).".format(self.name))
            raise RuntimeError

        try:
            LxdAPI.start_container(self.server,
                                   self.name)
        except RuntimeError:
            self.logger.error("Error stopping the base router container.")
            return False

        time.sleep(3)

        header = ["ssh",
                  "-i",
                  Constants.ssh_client_private_key,
                  "{0}@{1}".format(Globals.username, self.server)]

        eth0_conf = ["lxc exec {0} /root/ch_password.sh && "
                     "sudo ovs-vsctl --if-exists del-port {2} {0} && "
                     "sudo ovs-vsctl --may-exist add-port {2} {0} tag={3} && "
                     "lxc exec {0} ip addr add {1}/16 brd + dev eth0 && " \
                     "lxc exec {0} ip link set eth0 up && "
                     "lxc exec {0} ip route add default via {4} &&".format(self.name,
                                                                           self.router_ip_address,
                                                                           Constants.LXD_BRIDGE,
                                                                           Constants.router_vlan,
                                                                           self.server.get_container_gateway())]
        commands = ["sudo ovs-vsctl --if-exists del-port {0} {1} && "
                    "sudo ovs-vsctl --may-exist add-port {0} {1} tag={2} && "
                    "lxc exec {3} ip addr add {4}/32 brd + dev {5} && "
                    "lxc exec {3} ip link set {5} down &&".format(Constants.LXD_BRIDGE,
                                                                  self.map_interface_intname[interface],
                                                                  self.map_interface_vlan[interface],
                                                                  self.name,
                                                                  self.map_interface_ip_address[interface],
                                                                  interface) for interface in
                    self.map_interface_ip_address if interface in self.map_interface_intname and interface in self.map_interface_vlan]

        command = [" ".join(eth0_conf + commands)[:-3]]
        params = header + command
        p = subprocess.Popen(params, stdout=subprocess.DEVNULL)
        if p.wait():
            self.logger.error("[{0}] Error setting interfaces of mobile station {1}. Params: {2}".format(self.server,
                                                                                                         self.veth0_name,
                                                                                                         params))
            return False
        else:
            self.logger.debug("[{0}] Interfaces of {1} correctly configured.".format(self.server,
                                                                                     self.veth0_name,
                                                                                     params))
        return True
