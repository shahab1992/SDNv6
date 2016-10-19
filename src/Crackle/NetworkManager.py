"""
This module deals with the network managing and configuration. It exposes some methods that allow to easily deploy and
set up the network.
"""

import os
import random
import shutil
import ssl
import stat
import logging
import subprocess
import threading

import time

from Crackle import TopologyStructs
from Crackle.ColoredOutput import make_colored
import Crackle.Globals as Globals
import Crackle.Constants as Constants

from Crackle.AsyncManager import start_thread_pool
from Crackle.LxcUtils import RouterContainer

_DEBUG = False

create_suffix = "_create.sh"
remove_suffix = "_remove.sh"

net_card_name = "$(ifconfig | grep eth0 | cut -d \" \" -f 1)"

macvlan_template = "ip link add name {0} link " + net_card_name + " type macvlan && ip link set dev {0} address {3} && " \
                                                                  "ip link set {0} up && ip addr add {1}/32 brd + dev {0} && ip route add {2} dev {0}\n"

delete_macvlan_template = "ip link delete {0}"

# with HTB:

shaping_template = "tc qdisc del dev {0} root; tc qdisc add dev {0} root handle 1: " \
                   "tbf rate {1} burst {2}kb latency 70ms && tc qdisc add dev {0} parent 1:1 codel\n"

ifstat_path_template = "{0}link_{1}_{2}.log"
mpstat_path_template = "{0}mpstat_{1}.log"

nfd_log = "/var/log/ndn/nfd.log"
__nfd_conf_file__ = "/etc/ndn/nfd.conf"


class NetworkManager:
    """
    This class handles the network management. It allows to set up the **topology**, the **link bandwidth**,
    the **IPIP tunnels** and the **statistics**. Also it allows to test if the network is up by executing some
    network commands on the experiment nodes.

    :ivar: node_list: The complete list of nodes of the network.
    """

    def __init__(self, node_list, server_list):
        self.node_list = node_list
        self.server_list = server_list
        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)
        self.stat_files = {}

        self.base_station_list = []
        self.mobile_station_list = []

        for node in self.node_list.values():
            if type(node) == TopologyStructs.BaseStation:
                self.base_station_list.append(node)
            elif type(node) == TopologyStructs.Station:
                self.mobile_station_list.append(node)

    def open_terminal(self, container):
        """
        Open a terminal in the specified container

        :param container:
        :return:
        """

        if container not in self.node_list.keys():
            self.logger.error("Open Terminal: No container named {0}".format(container))
            print(make_colored("red", "No container named {0}".format(container)))
            return

        node = self.node_list[container]

        port = random.randint(5000, 10000)

        params = ["ssh",
                  "-i",
                  Constants.ssh_client_private_key,
                  "-NL",
                  "{1}:{0}:22".format(node.get_ip_address(),
                                      port),
                  "{0}@{1}".format(Globals.username,
                                   node.get_server())]

        params1 = ["bash",
                   "-c",
                   "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "
                   "-X -p {0} ubuntu@localhost".format(port)]

        # def popenCallback():
        #     p2 = subprocess.Popen(params1) #, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        #     p2.wait()
        #     p.kill()
        #
        #     return

        p = subprocess.Popen(params)
        time.sleep(1)

        # t = threading.Thread(target=popenCallback)
        # t.start()

        p2 = subprocess.Popen(params1)  # , stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p2.wait()
        p.kill()

        return

    def show_container_status(self):
        """
        Test if the nodes in the network are still alive.

        :return:

        """

        for node in self.node_list.values():

            self.logger.debug("Querying containers for status.")
            status = node.get_status()

            if status:
                self.logger.debug("[{0}] Printing status of the container.".format(node))
                print(make_colored("blue", "Container: {0}".format(node)))
                print(status)
            else:
                self.logger.error("[{0}] Impossible to retrieve the status of the container")
                print(make_colored("blue", "[{0}] Impossible to retrieve the status of the container"))

    def list_routes(self):
        """
        Lists the kernel routing table of each host/container. This routing table is NOT used to globally route the
        packets, it is just exploited to route the packets toward the correct tunnel interface inside the node.

        :return:
        """
        self.logger.info("Showing current routing tables of the nodes in the network:")

        for node in self.node_list.values():

            print(make_colored("blue", "\nRoutes of node {0}\n".format(node)))

            ret = node.run_command("route", "-n")

            if ret:
                self.logger.error("[{0}] Error listing routes".format(node))
                print(make_colored("red", "[{0}] Error listing routes".format(node)))

    def show_links(self):
        """
        Print a summary of all the links in the network
        :return:
        """

        node_list = sorted(self.node_list.values(), key=lambda x: x.node_id, reverse=False)

        for node in node_list:
            print(make_colored("green", node.get_node_id().replace(Globals.experiment_id, "")))
            links = sorted(node.get_links().values(), key=lambda x: x.get_node_to().get_node_id(), reverse=False)
            for link in links:
                print("\t{0} Capacity: {1} mbps".format(
                        link.get_node_to().get_node_id().replace(Globals.experiment_id, ""), link.get_capacity() if type(link) is TopologyStructs.WiredLink else "Wireless"))

    def edit_link(self, node_from, node_to, capacity, container_created=False):
        """
        Edit an existing link in the network

        :param node_from:
        :param node_to:
        :param capacity:
        :param container_created:
        :return:
        """

        if not all(n in self.node_list for n in [node_to, node_from]):
            self.logger.error("Error in link edit: one between node_to or node_from does not exist.")
            print(make_colored("red", "Impossible to edit this link. "
                                      "At least one of the nodes is not part of the network."))
            return

        # Sanity check
        assert type(capacity) == float and capacity > 0

        # Check if the link exist!
        try:
            l_node_to_node_from = self.node_list[node_to].get_links()[self.node_list[node_from]]
            l_node_from_node_to = self.node_list[node_from].get_links()[self.node_list[node_to]]
        except KeyError:
            self.logger.error("Deletion of link between {0} and {1} failed: "
                              "the link does not exist.".format(node_to,
                                                                node_from))
            return

        l_node_to_node_from.set_capacity(capacity)
        l_node_from_node_to.set_capacity(capacity)

        if container_created:
            if not (l_node_to_node_from.shape_link(capacity) and l_node_from_node_to.shape_link(capacity)):
                self.logger.error("Error removing the physical interface on {0} or {1}".format(node_from,
                                                                                               node_to))
                print(make_colored("red", "Error removing the physical interface on {0} or {1}".format(node_from,
                                                                                                       node_to)))

    def delete_link(self, node_from, node_to, container_created=False):
        """
        Delete an existing link between 2 nodes
        :return:
        """

        if not all(n in self.node_list for n in [node_to, node_from]):
            self.logger.error("Error in link del: one between node_to or node_from does not exist.")
            print(make_colored("red", "Impossible to delete this link. "
                                      "At least one of the nodes is not part of the network."))
            return

        # Check if the link exist, and let's get rid of it!
        try:
            l_node_to_node_from = self.node_list[node_to].get_links()[self.node_list[node_from]]
            l_node_from_node_to = self.node_list[node_from].get_links()[self.node_list[node_to]]
        except KeyError:
            self.logger.error("Deletion of link between {0} and {1} failed: "
                              "the link does not exist.".format(node_to,
                                                                node_from))
            return

        if container_created:
            if not (l_node_to_node_from.destroy_interface() and l_node_from_node_to.destroy_interface()):
                self.logger.error("Error removing the physical interface on {0} or {1}".format(node_from,
                                                                                               node_to))
                print(make_colored("red", "Error removing the physical interface on {0} or {1}".format(node_from,
                                                                                                       node_to)))

        self.node_list[node_to].delete_link(l_node_to_node_from)
        self.node_list[node_from].delete_link(l_node_from_node_to)

    def add_link(self, node_to, node_from, capacity, container_created=False):
        """
        Add a new link between two nodes
        :return:
        """

        if capacity < 0 or not all(n in self.node_list for n in [node_to, node_from]):
            self.logger.error("Error in link add: one value among capacity, node_to or node_from is not valid.")
            print(make_colored("red", "Capacity negative or at least one of the nodes is not part of the network."))
            return

        l_node_to_node_from = TopologyStructs.WiredLink(self.node_list[node_to],
                                                   self.node_list[node_from],
                                                   node_from,
                                                   True,
                                                   capacity)

        l_node_from_node_to = TopologyStructs.WiredLink(self.node_list[node_from],
                                                   self.node_list[node_to],
                                                   node_to,
                                                   True,
                                                   capacity)

        self.node_list[node_from].add_link(l_node_from_node_to)
        self.node_list[node_to].add_link(l_node_to_node_from)

        if container_created:
            if not (l_node_from_node_to.create_link() and l_node_to_node_from.create_link()):
                self.logger.error("Error creating new link between {0} and {1}".format(node_from,
                                                                                       node_to))
                print(make_colored("red", "Error creating new link between {0} and {1}".format(node_from,
                                                                                               node_to)))

    def show_nodes(self, node_name):
        """
        Print a resume of all the nodes in the network
        :return:
        """

        if node_name in self.node_list:
            node = self.node_list[node_name]
            print(make_colored("blue", node.get_node_id().replace(Globals.experiment_id, "")))
            print(make_colored("yellow", "\tNode Type:"),
                  str(type(node)).replace("<class 'Crackle.TopologyStructs.", "").replace("'>", ""))

            print(make_colored("yellow", "\tCache Size:"), node.get_cache_size())
            print(make_colored("yellow", "\tForwarding Strategy:"), node.get_forward_strategy())
            print(make_colored("yellow", "\tVLAN:"), node.get_vlan())
            print(make_colored("yellow", "\tServer:"), node.get_server())

            print(make_colored("yellow", "\tMain Interface (eth0):"),
                  "IP Address:", node.get_container().get_ip_address(),
                  "MAC Address:", node.get_container().get_mac_address())

            if type(node) == TopologyStructs.BaseStation:
                print(make_colored("yellow", "\tWireless Interface (wlan0):"),
                      "IP Address:", node.get_container().get_ip_address(),
                      "MAC Address:", node.get_container().get_mac_address())

            print(make_colored("yellow", "\tNeighbors:"))

            for link in sorted(node.get_links().values(), key=lambda x: x.get_node_to().get_node_id(), reverse=False):
                print("\t\t", "Interface:", link.get_interface(),
                      "IP address:", node.get_ip_address(link.get_node_to()),
                      "MAC Address:", node.get_mac_address(link.get_node_to()))

    def edit_node(self, node_name, forward_strategy, container_created=False):
        """
        Edit an existing link in the network

        :param node_name:
        :param container_created:
        :return:
        """

        if not all(n in self.node_list for n in [node_name]):
            self.logger.error("Error in link edit: one between node_to or node_from does not exist.")

            print(make_colored("red", "Impossible to edit this node becasue the node doesn't exit on the network'. "))

            return

        try:
            node = self.node_list[node_name]

        except KeyError:

            self.logger.error("{0} node_name doesn't exist' ".format(forward_strategy))

            return

        forward_strategy_old = node.get_forward_strategy()

        node.set_forward_strategy(forward_strategy)

        self.reset_node_strategy(node, forward_strategy, forward_strategy_old)

        if not container_created:
            self.logger.error("{0} Error in forward_strategy".format(forward_strategy))

            print(make_colored("red", "{0} Error in forward_strategy".format(forward_strategy)))

    def reset_node_strategy(self, n, forward_strategy, forward_strategy_old):

        try:

            param = ["sed",
                     "-i",
                     "0,/\/ / s/{0}/{1}/".format(forward_strategy_old, forward_strategy),
                     __nfd_conf_file__]

            ret = n.run_command(param)

            if not ret:
                print(make_colored("red", "[{0}] Error while reseting node".format(n)))
                self.logger.error("[{0}] Error while reseting node".format(n))

            else:
                logging.info("[{0}] Router configured. and "
                             "Forwarding Strategy={1}".format(n, forward_strategy))

            params = ["service",
                      "nfd",
                      "restart"]

            ret = n.run_command(params)

            if not ret:
                self.logger.error("[{0}] Error restarting NFD".format(n))
                print(make_colored("red", "[{0}] Error restarting NFD".format(n)))

            else:
                self.logger.info("[{0}] NFD restarted".format(n))

        except Exception as error:
            self.logger.error("[{0}] Error setting up the router. "
                              "Error: {1}".format(n,
                                                  error))

    def add_node(self, node_name, cache_size, forwarding_strategy, container_created=False):
        """
        Add a new node to the network
        :return:
        """

        if node_name not in self.node_list:
            self.node_list[node_name] = TopologyStructs.Router(node_name,
                                                               cache_size,
                                                               "l",
                                                               100,
                                                               forwarding_strategy,
                                                               container=RouterContainer(node_name),
                                                               vlan=Constants.router_vlan)

            self.node_list[node_name].set_server(self.server_list[random.randint(0, len(self.server_list) - 1)])

            if container_created:
                self.node_list[node_name].spawn_container()
                self.node_list[node_name].start_container()
        else:
            self.logger.error("The node {0} already exist. Impossible to create it!".format(node_name))
            print(make_colored("red", "The node {0} already exist. Impossible to create it!".format(node_name)))

    def delete_node(self, node_id, container_created):
        """
        Dynamically delete the node node_id from the network
        :return:
        """

        if node_id in self.node_list:
            # Delete all the links toward this node
            for link in list(self.node_list[node_id].get_links().values()):
                self.delete_link(link.get_node_from().get_node_id(),
                                 link.get_node_to().get_node_id(),
                                 container_created)

            # Delete the node itself

            if not self.node_list[node_id].stop_container(async=True):
                self.node_list[node_id].delete_container()

            del self.node_list[node_id]
        else:
            self.logger.error("The node {0} is not part of the network.".format(node_id))

    def ping(self, pinger, pinged):
        """
        Test the connectivity between two nodes.

        :param pinger: The node starting the ping
        :param pinged: The node to be "pinged"
        :return:
        """

        if all(node in self.node_list for node in [pinger, pinged]):
            # The 2 nodes exist

            try:
                params = ["ping",
                          self.node_list[pinged].get_ip_address(self.node_list[pinger]),
                          "-w",
                          "1"]
            except KeyError:
                self.logger.error("The nodes {0} and {1} are not directly connected.".format(pinger,
                                                                                             pinged).replace(
                        Globals.experiment_id, ""))
                print(make_colored("red", "The nodes {0} and {1} are not directly connected.".format(pinger,
                                                                                                     pinged).replace(
                        Globals.experiment_id, "")))
                return

            if self.node_list[pinger].run_command(params, output=True):
                print(make_colored("green", "The two nodes can talk together."))
            else:
                print(make_colored("yellow", "Reachability problem between {0} and {1}".format(
                        pinger,
                        pinged).replace(Globals.experiment_id, "")))
        else:
            self.logger.error(
                    "One node between {0} and {1} does not exist.".format(pinger,
                                                                          pinged).replace(Globals.experiment_id, ""))
            print(make_colored("red", "One node between {0} and {1} does not exist.".format(pinger,
                                                                                            pinged).replace(
                    Globals.experiment_id, "")))

    def exec(self, node, command, container_created):
        """
        Execute the command command on the node
        :param node: The target node
        :param command: An array containing the command to execute
        :return:
        """

        if node in self.node_list:
            if container_created:
                self.node_list[node].run_command(command, output=True)
            else:
                print(make_colored("yellow", "Please start the containers before running a command on them!"))
        else:
            self.logger.error("The node {0} does not exist.".format(node.replace(Globals.experiment_id, "")))
            print(make_colored("red", "Node {0} does not exist!".format(node.replace(Globals.experiment_id, ""))))

    def list_tunnels(self):
        """
        Shows the configurations of all the tunnels in the network.

        :return:

        """
        self.logger.info("Showing current tunnels:")

        for node in self.node_list.values():

            print(make_colored("blue", "\nTunnels of node {0}\n".format(node)))

            ret = node.run_command("iptunnel", "show")

            if ret:
                self.logger.error("[{0}] Error listing tunnels".format(node))
                print(make_colored("red", "[{0}] Error listing tunnels".format(node)))

    def list_interfaces(self):
        """
        Lists the configuration of all the interfaces in the network.

        :return:

        """
        self.logger.info("Showing interfaces:")

        for node in self.node_list.values():

            print(make_colored("blue", "\nInterfaces of node {0}\n".format(node)))

            ret = node.run_command("ifconfig")

            if ret:
                self.logger.error("[{0}] Error showing interfaces".format(node))
                print(make_colored("red", "[{0}] Error showing interfaces".format(node)))

    def create_scripts(self):
        """
        This method creates some BASH scripts in order to create the MACVLAN interfaces and the traffic shapers on the nodes.
        This allows to create the virtual topology and to set the link bandwith according on the configuration that has
        been specified in the topo.brite file.

        :return:

        """

        def create_script(n_from, results):

            f = open(Globals.scripts_dir + str(n_from) + create_suffix, 'w')

            f.write("#!/bin/bash\n\n"
                    "sysctl -w net.ipv4.ip_forward=1\n")

            for link in n_from.get_links().values():

                self.logger.debug("[{0}] Creating script for creating link from {0} to {1}".format(n_from,
                                                                                                   link.get_node_to()))

                f.write(macvlan_template.format(link.get_node_to(),
                                                n_from.get_ip_address(link.get_node_to()),
                                                link.get_node_to().get_ip_address(n_from),
                                                n_from.get_mac_address(link.get_node_to())))

                burst = link.get_burst()

                if link.is_shaped():
                    f.write(shaping_template.format(link.get_node_to(),
                                                    str(link.get_capacity()) + "Mbit",
                                                    burst))
                f.write("\n")
            f.write("exit 0\n")
            f.close()
            os.chmod(Globals.scripts_dir + str(n_from) + create_suffix,
                     stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR | stat.S_IRWXU)

            results[n_from] = True

        def remove_script(n_from, results):
            if len(n_from.get_links()) > 0:
                f = open(Globals.scripts_dir + str(n_from) + remove_suffix, 'w')
                f.write("#!/bin/bash\n\n")

                for link in n_from.get_links().values():
                    self.logger.debug("[{0}] Creating script for removing link from {0} to {1}".format(n_from,
                                                                                                       link.get_node_to()))

                    f.write(delete_macvlan_template.format(link.get_node_to()))
                f.close()
                os.chmod(Globals.scripts_dir + str(n_from) + remove_suffix,
                         stat.S_IXUSR | stat.S_IRUSR |
                         stat.S_IWUSR | stat.S_IRWXU)

            results[n_from] = True

        self.logger.info("Creating scripts to set/remove links...")

        if not os.path.exists(Globals.scripts_dir):
            os.makedirs(Globals.scripts_dir, exist_ok=True)

        return start_thread_pool(self.node_list.values(),
                                 create_script) and start_thread_pool(self.node_list.values(),
                                                                      remove_script)

    def create_links(self):
        """
        This method is in charge of building the virtual topology on the physical one. It creates the IP tunnels and
        configures the traffic shapers by executing the scripts created in \
        :meth:`Crackle.NetworkManager.NetworkManager.create_scripts`.

        :return:

        """

        def create_links(n, res):

            try:
                if not n.push_file(Globals.scripts_dir + str(n) + create_suffix,
                                   "/root/{0}{1}".format(n, create_suffix)):
                    self.logger.error("[{0}] Error pushing the file. SourcePath={1}, DestPath={2}.".format(n,
                                                                                                           Globals.scripts_dir + str(
                                                                                                                   n) + create_suffix,
                                                                                                           "/root/create_link_scripts"))
                    res[n] = False
                    return
                else:
                    self.logger.debug("[{0}] File {1} successfully pushed.".format(n,
                                                                                   Globals.scripts_dir + str(
                                                                                           n) + create_suffix))

                ret = n.run_command(["/root/{0}{1}".format(n, create_suffix)])

                if not ret:
                    self.logger.error("[{0}]: Error while executing the link creation script".format(n))
                    print(make_colored("red", "[{0}]: Error while executing the link creation script".format(n)))
                    res[n] = False
                else:
                    self.logger.info("[{0}] Links created.".format(n))
                    res[n] = True
            except Exception as error:
                self.logger.error("Error creating links. "
                                  "Error: {1}".format(n,
                                                      error))
                res[n] = False

        self.logger.info("Creating the links...")

        return start_thread_pool(self.node_list.values(), create_links)

    def assign_station_vlans(self):
        """
        Assign the mobile stations to the correct vlans for avoiding loops in the network
        :return:
        """

        self.logger.debug("Setup of the network interfaces for the mobile stations")

        start_vlan = Constants.mobile_station_vlan_start

        for node in self.mobile_station_list:
            node.setup_network_interfaces(self.base_station_list, range(start_vlan,
                                                                        start_vlan + len(self.base_station_list)))
            start_vlan += len(self.base_station_list) + 1

    def spawn_containers(self):
        """
        Create the containers on the servers in the cluster.

        :return:
        """

        self.assign_station_vlans()

        def spawn_container(n, results):
            try:
                if n.spawn_container():
                    results[n] = True
                else:
                    results[n] = False
            except req_except.RequestException as error:
                self.logger.error("Error spawning container {0}. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), spawn_container, sleep_time=0.2)

    def start_containers(self):
        """
        This method starts the container associated to the nodes.

        :return:

        """

        self.logger.info("Starting all the containers")

        def start_container(n, results):

            try:
                ret = n.push_file(Constants.nfd_conf_file, __nfd_conf_file__)
                if not ret:
                    self.logger.error("[{0}] Error sending NFD configuration file".format(n))
                    print(make_colored("red", "[{0}] Error sending NFD configuration file".format(n)))
                    results[n] = False
                else:
                    self.logger.info("[{0}] NFD configuration file sent".format(n))
                    results[n] = True
                if n.start_container():
                    self.logger.info("[{0}]: Container started.".format(n))
                    results[n] = True
                else:
                    print(make_colored("red", "[{0}]: Container failed to start.".format(n)))
                    self.logger.error("[{0}]: Container failed to start.".format(n))
                    results[n] = False
            except Exception as error:
                self.logger.error("Error starting container {0}. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), start_container, sleep_time=0.2)

    def delete_containers(self):
        """
        This method deletes the container associated to the nodes.

        :return:

        """

        self.logger.info("Deleting all the containers")

        def delete_container(n, results):

            try:
                if n.delete_container():
                    self.logger.info("[{0}]: Container deleted.".format(n))
                    results[n] = True
                else:
                    print(make_colored("red", "[{0}]: Container deletion failed.".format(n)))
                    self.logger.error("[{0}]: Container deletion failed".format(n))
                    results[n] = False
            except Exception as error:
                self.logger.error("Error deleting container {0}. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), delete_container)

    def stop_containers(self, old=False):
        """
        This method stops the container associated to the nodes.

        :return:

        """

        self.logger.info("Stopping all the containers")

        def stop_container(n, results):

            try:
                if n.stop_container():
                    self.logger.info("[{0}]: Container stopped.".format(n))
                    results[n] = True
                else:
                    print(make_colored("red", "[{0}]: Container failed to stop.".format(n)))
                    self.logger.error("[{0}]: Container failed to stop.".format(n))
                    results[n] = False
            except Exception as error:
                self.logger.error("Error stopping container {0}. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), stop_container)

    def remove_links(self):
        """
        Remove the network links created by the previous method :meth:`Crackle.NetworkManager.NetworkManager.create_links`

        :return:

        """

        def remove_link(n, results):

            if not n.push_file(Globals.scripts_dir + str(n) + remove_suffix,
                               "/root/{0}{1}".format(n, remove_suffix)):
                self.logger.error("[{0}] Error pushing the file. SourcePath={1}, "
                                  "DestPath={2}.".format(n,
                                                         Globals.scripts_dir + str(n) + create_suffix,
                                                         "/root/remove_link_scripts"))
                results[n] = False
                return
            else:
                self.logger.debug("[{0}] File {1} successfully pushed.".format(n,
                                                                               Globals.scripts_dir + str(
                                                                                       n) + create_suffix))

            ret = n.run_command(["/root/{0}{1}".format(n,
                                                       remove_suffix)])

            if ret:
                self.logger.error("[{0}]: Error while executing the link deleting script".format(n))
                print(
                        make_colored("red", "[{0}]: Error while executing the link deleting script".format(n)))
                results[n] = False
            else:
                self.logger.info("[{0}] Links removed".format(n))
                results[n] = True

        self.logger.info("Removing the links.")

        return start_thread_pool(self.node_list.values(), remove_link)

    def workload_routing(self):

        r = 0
        c = 0
        number = 0

        for n in self.node_list.values():
            c += len(n.get_client_apps())
            r += len(n.get_repositories())
            number += 1

        if r == 1 and c == 1:
            routing_algorithm = 'MaxFlow'
        elif r == 1 and c == number - 1:
            routing_algorithm = 'MinCostMultipath'
        elif r > 1 and c == 1:
            routing_algorithm = 'TreeOnProducer'
        elif r == 1 and c > 1:
            routing_algorithm = 'TreeOnConsumer'
        elif r > 1 and c > 1:
            routing_algorithm = 'TreeOnConsumer'
        else:
            print('NoAlgorithm')

        return routing_algorithm

    def set_stats(self):
        """
        Starts the software *ifstat* and *mpstat* in the network, in order to take some statistics about the usage of
        each link/interface and about the CPU usage.

        :return:

        """
        self.logger.info("Set up per link statistics.")

        def start_stat(n, results):

            self.stat_files[n] = []

            # try:
            ret = n.run_command(["rm", "-rf", Globals.remote_log_dir])
            if not ret:
                results[n] = False
                self.logger.error("[{1}]: Error deleting folder {0}".format(Globals.remote_log_dir, n))
                print(
                        make_colored("red",
                                     "[{1}]: Error deleting folder {0}".format(Globals.remote_log_dir, n)))
                return
            else:
                self.logger.info("[{1}] Folder {0} deleted".format(Globals.remote_log_dir, n))

            ret = n.run_command(["mkdir", "-p", Globals.remote_log_dir])

            if not ret:
                results[n] = False
                self.logger.error("[{1}]: Error creating folder {0}".format(Globals.remote_log_dir, n))
                print(
                        make_colored("red",
                                     "[{1}]: Error creating folder {0}".format(Globals.remote_log_dir, n)))
                return
            else:
                self.logger.info("[{1}] Folder {0} created".format(Globals.remote_log_dir, n))

            if type(n) != TopologyStructs.Station:

                for link in n.get_links().values():

                    params = ["/bin/bash",
                              "-c",
                              "nohup ifstat -i {0} -b -t > {1} &".format(link.get_node_to(),
                                                                         ifstat_path_template.format(
                                                                               Globals.remote_log_dir,
                                                                               link.get_node_from(),
                                                                               link.get_node_to()))]
                    self.stat_files[n].append(ifstat_path_template.format(Globals.remote_log_dir,
                                                                          link.get_node_from(),
                                                                          link.get_node_to()))
                    if not n.run_command(params):
                        results[n] = False
                        self.logger.error("[{0}] Error setting up ifstat statistics".format(n))
                        return

            if type(n) == TopologyStructs.BaseStation:

                params = ["/bin/bash",
                          "-c",
                          "nohup ifstat -i wlan0 -b -t > {0} &".format(
                                  ifstat_path_template.format(Globals.remote_log_dir,
                                                              n,
                                                              "base_station"))]
                self.stat_files[n].append(ifstat_path_template.format(Globals.remote_log_dir,
                                                                      n,
                                                                      "bs_aggregate_traffic"))
                if not n.run_command(params):
                    results[n] = False
                    self.logger.error("[{0}] Error setting up ifstat statistics".format(n))
                    return

            if type(n) == TopologyStructs.Station:

                for bs in self.base_station_list:

                    params = ["/bin/bash",
                              "-c",
                              "nohup ifstat -i {0} -b -t > {1} &".format(bs, ifstat_path_template.format(
                                      Globals.remote_log_dir,
                                      n,
                                      bs))]
                    self.stat_files[n].append(ifstat_path_template.format(Globals.remote_log_dir,
                                                                          n,
                                                                          bs))
                    if not n.run_command(params):
                        results[n] = False
                        self.logger.error("[{0}] Error setting up ifstat statistics".format(n))
                        return
                    else:
                        self.logger.info("[{0}] ifstat statistics set up".format(n))

            params = ["/bin/bash",
                      "-c",
                      "nohup mpstat -P ALL 1 > {0} &".format(mpstat_path_template.format(Globals.remote_log_dir,
                                                                                         n))]

            self.stat_files[n].append(mpstat_path_template.format(Globals.remote_log_dir, n))

            if not n.run_command(params):
                results[n] = False
                self.logger.error("[{0}] Error setting up mpstat statistics".format(n))
                return
            else:
                self.logger.info("[{0}] mpstat statistics set up".format(n))

            results[n] = True
            # except Exception as error:
            #     self.logger.error("[{0}] Error setting up statistics. "
            #                       "Error: {1}".format(n,
            #                                           error))
            #     results[n] = False

        return start_thread_pool(self.node_list.values(), start_stat)

    def kill_stats(self):
        """
        Stop *ifstat* and *mpstat* on each node in the network.

        :return:

        """

        def kill_stat(n, results):

            try:
                params = ["killall",
                          "-9",
                          "ifstat"]

                ret = n.run_command(params)

                if ret:
                    results[n] = False
                    self.logger.error("[{0}]: Error killing ifstat".format(n))
                    print(
                            make_colored("red", "[{0}]: Error killing ifstat".format(n)))
                else:
                    self.logger.info("[{0}] Ifstat killed".format(n))
                    results[n] = True

                params = ["killall",
                          "-9",
                          "mpstat"]

                ret = n.run_command(params)

                if ret:
                    results[n] = False
                    self.logger.error("[{0}]: Error killing mpstat".format(n))
                    print(
                            make_colored("red", "[{0}]: Error killing mpstat".format(n)))
                else:
                    results[n] = True
                    self.logger.info("[{0}] Mpstat killed".format(n))
            except Exception as error:
                self.logger.error("[{0}] Error killing statisctics. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        self.logger.info("Tearing down per link statistics.")

        return start_thread_pool(self.node_list.values(), kill_stat)

    def get_stats(self):
        """
        Get the statistics from the nodes.

        :return:

        """
        if os.path.isdir(Globals.log_dir):
            shutil.rmtree(Globals.log_dir)

        os.makedirs(Globals.log_dir, exist_ok=True)

        def gather(n, results):

            directory = Globals.log_dir + "/" + str(n)
            os.makedirs(directory, exist_ok=True)

            try:
                n.pull_file(nfd_log, directory + "/" + os.path.basename(os.path.normpath(nfd_log)))
            #                for f in self.stat_files[n]:
            #                    if n.pull_file(f, directory + "/" + os.path.basename(os.path.normpath(f))):
            #                        self.logger.info("[{0}] File nfd.log retrieved".format(n))
            #                    else:
            #                        self.logger.error("[{1}]: File {0} not found in".format(nfd_log, n))
            #                        print(make_colored("red", "[{1}]: File {0} not found in".format(nfd_log, n)))
            except Exception as error:
                self.logger.error("[{0}] Error gathering statistic files. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), gather)

        # stest_path = Globals.test_folder.split("/")
        # test = stest_path[-1]
        # if test == "":
        #     test = stest_path[-2]

        # os.system("mkdir " + name)
        # os.system("mkdir " + name + "/scenario")
        # os.system("cp -r " + myglobals.log_dir + " " + name)
        # os.system("cp -r " + myglobals.scripts_dir + " " + name + "/scenario")
        # os.system("cp -r crackle/Globals.py " + name + "/scenario")
        # os.system("cp " + myglobals.test_path + "/* " + name + "/scenario")
        # os.system("cp hosts " + name + "/scenario")
        # os.system("cp crackle.conf " + name + "/scenario")
        # os.system("tar cvzf " + name + ".tar.gz " + name)
        # os.system("rm -rf " + name)
        # os.system("scp " + name + ".tar.gz " + myglobals.remote_server_user + "@" + myglobals.remote_server
        #           + ":" + myglobals.remote_server_folder)
        # os.system("rm -rf " + name + ".tar.gz")
