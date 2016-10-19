"""
This module controls the NDN components of the network, as the forwarder NFD or the routing, and allows to run the
experiment by starting the repos/client in the network.
"""

import stat
import os
import logging
import threading
import time
import shutil

from Crackle.ColoredOutput import make_colored
import Crackle.Globals as Globals
from Crackle.AsyncManager import start_thread_pool
from Crackle.Constants import layer_2_protocols, __tree_on_consumer__, __min_cost_multipath__, \
    __tree_on_producer__, __maximum_flow__, nfd_conf_file
from Crackle import TopologyStructs
from Crackle.RoutingNdn import RoutingNdn

# TODO Move constants to Globals

REPO = "ndn-virtual-repo"

_DEBUG = False

module_logger = logging.getLogger(__name__)

## Routing files
routing_reset_suffix = "_resetndnrouting.sh"
routing_suffix = "_setndnrouting.sh"
route_register_template = "nfdc register ndn:/{0} {1}://{2}:6363\n"
ethernet_route_register_template = "nfdc register ndn:/{0} {1}://[{2}]/{3}\n"
face_create_template = "nfdc create {} {}://{}:6363\n"
ethernet_face_create_template = "nfdc create {} {}://[{}]/{}\n"

route_unregister_template = "nfdc unregister ndn:/{0} {1}://{2}:6363\n"
ethernet_route_unregister_template = "nfdc unregister ndn:/{0} {1}://[{2}]\n"
face_destroy_template = "nfdc destroy {0}://{1}:6363\n"
ethernet_face_destroy_template = "nfdc destroy {0}://[{1}]\n"

## NFD configuration file
__nfd_conf_file__ = "/etc/ndn/nfd.conf"

# Script template

route_script = """
#!/bin/bash

create_faces() {{
    :
    {}
}}

destroy_faces() {{
    :
    {}
}}

reset_routing() {{
    :
    {}
}}

set_routing() {{
    :
    {}
}}

case $1 in
    create_faces)
    create_faces
    ;;
    destroy_faces)
    destroy_faces
    ;;
    reset_routing)
    reset_routing
    ;;
    set_routing)
    set_routing
    ;;
    set)
    create_faces
    set_routing
    ;;
    reset)
    destroy_faces
    reset_routing
    ;;
    *)
    exit 1
    ;;
esac

exit 0

"""


class NDNManager:
    """
    This class contains the methods for managing the NDN part of the experiment and starting the experiment itself.

    :ivar node_list: The list of all the node in the network (routers, base stations and mobile stations)
    """

    def __init__(self, node_list, server_list):
        self.node_list = node_list
        self.server_list = server_list
        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)

    def configure_router(self):
        """
        Set the cache size using the value contained in the configuration file "topo.brite".

        :return:
        """

        def set_strategy_cache(n, results):

            try:
                cache_size = n.get_cache_size()
                cache_policy = n.get_cache_policy()
                forward_strategy = n.get_forward_strategy()

                if cache_policy == "l":
                    cache_policy = "LRU"

                params = ["sed",
                          "-i",
                          "s/^.*cs_max_packets .*$/  cs_max_packets {0}/".format(cache_size),
                          __nfd_conf_file__]

                params2 = ["sed",
                           "-i",
                           "0,/\/ / s/best-route/{0}/".format(forward_strategy),
                           __nfd_conf_file__]

                ret = n.run_command(params) and n.run_command(params2)

                if not ret:
                    print(make_colored("red", "[{0}] Error while configuring router".format(n)))
                    self.logger.error("[{0}] Error while setting cache".format(n))
                    results[n] = False
                else:
                    logging.info("[{0}] Router configured. Cache={1} and "
                                 "Forwarding Strategy={2}".format(n, cache_size, forward_strategy))
                    results[n] = True

                params = ["service",
                          "nfd",
                          "restart"]

                ret = n.run_command(params)

                if not ret:
                    self.logger.error("[{0}] Error restarting NFD".format(n))
                    print(make_colored("red", "[{0}] Error restarting NFD".format(n)))
                    results[n] = False
                else:
                    self.logger.info("[{0}] NFD restarted".format(n))
                    results[n] = True
            except Exception as error:
                self.logger.error("[{0}] Error setting up the router. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), set_strategy_cache, sleep_time=0.1)

    def start_nfd(self):
        """
        Start the NDN forwarder on all the nodes in the network.

        :return:
        """

        def start(n, results):

            ret = n.push_file(nfd_conf_file, __nfd_conf_file__)
            if not ret:
                self.logger.error("[{0}] Error sending NFD configuration file".format(n))
                print(make_colored("red", "[{0}] Error sending NFD configuration file".format(n)))
                results[n] = False
            else:
                self.logger.info("[{0}] NFD configuration file sent".format(n))
                results[n] = True

            params = ["service", "nfd", "start"]

            try:

                ret = n.run_command(params)

                if not ret:
                    self.logger.error("[{0}] Error starting NFD".format(n))
                    print(make_colored("red", "[{0}] Error starting NFD".format(n)))
                    results[n] = False
                else:
                    self.logger.info("[{0}] NFD started".format(n))
                    results[n] = True
            except Exception as error:
                self.logger.error("[{0}] Error starting ICN forwarder. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), start)

    def stop_nfd(self):
        """
        Stop the NDN forwarder on each node of the network.

        :return:
        """
        print("* Stopping NFD on hosts")

        def stop(n, results):

            params = ["service", "nfd", "stop"]

            try:
                ret = n.run_command(params, check_return=False)

                if not ret:
                    self.logger.error("[{0}] Error stopping NFD".format(n))
                    print(make_colored("red", "[{0}] Error stopping NFD".format(n)))
                    results[n] = False
                else:
                    self.logger.info("[{0}] NFD stopped".format(n))
                    results[n] = True
            except Exception as error:
                self.logger.error("[{0}] Error stopping ICN forwader. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), stop)

    def list_repositories(self, number):
        """
        Show the list of repositories for the current experiment.
        :param number : a boolean returns number of repositories if True 
        :return r: number of repositories on network
        """
        r = 0
        for node in self.node_list.values():

            repositories = node.get_repositories()

            if repositories:
                print(make_colored("blue", "Repos on {0}:".format(node)))
                for repo in repositories:
                    r += 1
                    print(make_colored("cyan", "\t{0}".format(repo)))

        if number:
            return r

    def add_repository(self, node_name, repoId, folder):

        """
        Add repository to node_name

        :return:
        """

        self.node_list[node_name].add_repo(TopologyStructs.Repo(repoId, folder))

    def delete_repository(self, node_name, repoId, folder):

        """
        Remove repository to node_name

        :return:
        """

        node = self.node_list[node_name]

        for repo in node.get_repositories():

            if repo.get_repo_id() == repoId:
                node.get_repositories().remove(repo)

    def list_clients(self):
        """
        Show the list of clients (consumers) for the current experiment.

        :return:
        """
        for node in self.node_list.values():

            clients = node.get_client_apps()

            if clients:
                print(make_colored("blue", "Clients on {0}:".format(node)))
                for client in clients:
                    print(make_colored("cyan", "\t{0}".format(client)))

    def add_consumer(self, node_name, clientId, name):

        """
        Add client to node_name

        :return:
        """

        self.node_list[node_name].add_client(TopologyStructs.Client(clientId, "Poisson_2", "rzipf_1.3_100", name))

    def delete_consumer(self, node_name, clientId, name):
        """
        Remove repository to node_name

        :return:
        """

        node = self.node_list[node_name]

        for client in node.get_client_apps():
            if client.get_client_id() == clientId:
                node.get_client_apps().remove(client)

    def reset_cache(self):
        """
        Reset the cache with the default value (65536 Packets)

        :return:
        """

        def rst_cache(n, results):

            try:
                params = ["sed",
                          "-i",
                          "s/^.*cs_max_packets .*$/  cs_max_packets 65536/",
                          __nfd_conf_file__]

                ret = n.run_command(params)

                if ret:
                    self.logger.error("[{0}] Error resetting cache".format(n))
                    print(make_colored("red", "[{0}] Error resetting cache".format(n)))
                    results[n] = False
                else:
                    self.logger.info("[{0}] Cache reset successfully".format(n))
                    results[n] = True

                params = ["service",
                          "nfd",
                          "restart"]

                ret = n.run_command(params)

                if ret:
                    self.logger.error("[{0}] Error restarting NFD".format(n))
                    print(make_colored("red", "[{0}] Error restarting NFD".format(n)))
                else:
                    self.logger.info("[{0}] NFD restarted".format(n))
            except Exception as error:
                self.logger.error("[{0}] Error re-setting the cache. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), rst_cache)

    def show_route(self, node):
        """
        Show the routing table of a node.

        :param node:
        :return:
        """

        if node in self.node_list:
            routes = self.node_list[node].get_routes()
            if routes:
                print(make_colored("blue", node).replace(Globals.experiment_id, ""))
                for route in routes.values():
                    for route2 in route.values():
                        print(make_colored("yellow", "\ticn_name:"),
                              "ndn:/{0}".format(route2.get_icn_name()).replace("/", ""),
                              make_colored("yellow", "next hop:"),
                              "{0}".format(route2.get_next_hop()).replace(Globals.experiment_id, ""))

    def add_route(self, node, name, nexthop, container_created=False):
        """
        Add a route for name "name" in the node "node" with nexthop "nexthop"
        :param node:
        :param name:
        :param nexthop:
        :return:
        """

        if all([n in self.node_list for n in [node, nexthop]]):

            if self.node_list[nexthop] not in self.node_list[node].get_links():
                self.logger.error("The nodes {0} and {1} are not directly connected!".format(node, nexthop).replace(
                        Globals.experiment_id, ""))
                print(make_colored("red",
                                   "The nodes {0} and {1} are not directly connected!".format(node, nexthop).replace(
                                           Globals.experiment_id, "")))
                return

            self.node_list[node].add_route(self.node_list[nexthop], name)

            if container_created:
                if not self.node_list[node].get_route(name, self.node_list[nexthop]).register():
                    self.logger.error("Error creating the routes.")
                    print(make_colored("red", "Error creating the routes!"))
        else:
            self.logger.error("Trying to add the route {0} toward {1}, but {0} does not exist.".format(name,
                                                                                                       nexthop))
            print(make_colored("red", "The node {0} does not exist!".format(node)))

    def recompute_global_routing(self, route, routing_algorithm, container_created=False, rerouting=False):
        """
        Recompute the routing of the network using routing_algorithm

        :param routing_algorithm:
        :return:
        """

        if routing_algorithm not in [__maximum_flow__,
                                     __min_cost_multipath__,
                                     __tree_on_consumer__,
                                     __tree_on_producer__]:
            self.logger.error("Routing algorithm not in the list of allowed algorithms!")
            print(make_colored("red", "Routing algorithm not in the list of allowed algorithms!"))
            return

        RoutingNdn(self.node_list).algo_ndn(routing_algorithm)

        self.create_routing_scripts()

        if container_created:
            self.reset_ndn_routing(rerouting=rerouting)
            self.push_routing_scripts()
            self.set_ndn_routing(rerouting=rerouting)

    def delete_route(self, node, name, nexthop, container_created=False):
        """
        Delete a route for name "name" in the node "node" with nexthop "nexthop"
        :param node:
        :param name:
        :param nexthop:
        :return:
        """

        if all([n in self.node_list for n in [node, nexthop]]):

            route = self.node_list[node].get_route(name, self.node_list[nexthop])

            if container_created:
                if not route.unregister():
                    self.logger.error("Error deleting the route.")
                    print(make_colored("red", "Error deleting the route!"))

            self.node_list[node].delete_route(name, self.node_list[nexthop])

        else:
            self.logger.error("Trying to add the route {0} toward {1}, but {0} does not exist.".format(name,
                                                                                                       nexthop))
            print(make_colored("red", "The node {0} does not exist!".format(node)))

    def start_repositories(self):
        """
        Start all the repositories in the network.

        :return:
        """

        def start_repo(n, results):

            ret_val = True

            try:
                for repo in n.get_repositories():
                    name = repo.get_folder()

                    params = ["service",
                              "repo-ng",
                              "start"]

                    self.logger.debug("[{0}] Repo {1}. Params={2}".format(n,
                                                                          params,
                                                                          params))

                    ret = n.run_command(params, sync=True)

                    if not ret:
                        print(make_colored("red", "[{0}] Error starting repo for {1}".format(n,
                                                                                             name)))
                    else:
                        self.logger.info("[{0}]: repo-ng {1} started".format(n,
                                                                             name))

                    ret_val &= ret

                results[n] = ret_val
            except Exception as error:
                self.logger.error("[{0}] Error starting repositories. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), start_repo)

    def start_virtual_repositories(self):
        """
        Start all the repositories in the network.

        :return:
        """

        def start_virtual_repo(n, results):

            ret_val = True

            try:
                for repo in n.get_repositories():
                    name = repo.get_folder()

                    params = ["ndn-virtual-repo",
                              name,
                              "-s",
                              "1400"]

                    self.logger.debug("[{0}] Repo {1}. Params={2}".format(n,
                                                                          params,
                                                                          params))

                    ret = n.run_command(params, sync=False)

                    if not ret:
                        print(make_colored("red", "[{0}] Error starting repo for {1}".format(n,
                                                                                             name)))
                    else:
                        self.logger.info("[{0}]: repo-ng {1} started".format(n,
                                                                             name))

                    ret_val &= ret

                results[n] = ret_val
            except Exception as error:
                self.logger.error("[{0}] Error starting repositories. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), start_virtual_repo)

    def stop_repositories(self):
        """
        Stop the NDN repositories in the network.

        :return:
        """
        print(make_colored("blue", "* Stopping repositories on the nodes..."))

        def kill_repo(n, results):

            try:
                if n.run_command("service", "repo-ng", "stop"):
                    self.logger.info("[{0}]: Repositories stopped.".format(n))
                    results[n] = True
                else:
                    print(make_colored("red", "[{0}]: Repositories failed to stop.".format(n)))
                    self.logger.error("[{0}]: Repositories failed to stop.".format(n))
                    results[n] = False
            except Exception as error:
                self.logger.error("Error deleting container {0}. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), kill_repo)

    def create_routing_scripts(self):
        """
        Create the routing scripts for setting the routing tables of the nodes.

        :return:
        """

        def create_script(n_from, results):
            routing_script = open(Globals.scripts_dir + str(n_from) + routing_suffix, 'w')
            create_faces, destroy_faces, registers, unregisters = [], [], [], []

            for link in n_from.get_links().values():
                if Globals.layer2_prot != layer_2_protocols[4]:
                    create_faces.append(face_create_template.format("-W" if Globals.wldr_face else "",
                                                                    Globals.layer2_prot,
                                                                    link.get_node_to().get_ip_address(
                                                                            n_from)))
                    destroy_faces.append(face_destroy_template.format(Globals.layer2_prot,
                                                                      link.get_node_to().get_ip_address(
                                                                              n_from)))
                else:
                    create_faces.append(ethernet_face_create_template.format("-W" if Globals.wldr_face else "",
                                                                             Globals.layer2_prot,
                                                                             link.get_node_to().get_mac_address(n_from),
                                                                             link.get_node_to() if (type(
                                                                                     link.get_node_to()) is not TopologyStructs.Station) or
                                                                                                   (type(
                                                                                                           link.get_node_to()) is TopologyStructs.Station and
                                                                                                    type(
                                                                                                            n_from) is TopologyStructs.Router) else "wlan0"))
                    destroy_faces.append(ethernet_face_destroy_template.format(Globals.layer2_prot,
                                                                               link.get_node_to().get_mac_address(
                                                                                       n_from)))

            for node_to in n_from.get_routes():
                for prefix in n_from.get_routes()[node_to]:
                    if Globals.layer2_prot not in layer_2_protocols:
                        self.logger.error("[{0}] Layer 2 protocol not recognized!.".format(n_from))
                        results[n_from] = False
                        return
                    if Globals.layer2_prot != layer_2_protocols[4]:

                        unregisters.append(route_unregister_template.format(prefix,
                                                                            Globals.layer2_prot,
                                                                            node_to.get_ip_address(n_from)))
                        registers.append(route_register_template.format(prefix,
                                                                        Globals.layer2_prot,
                                                                        node_to.get_ip_address(n_from)))
                    else:
                        unregisters.append(ethernet_route_unregister_template.format(prefix,
                                                                                     Globals.layer2_prot,
                                                                                     node_to.get_mac_address(n_from)))
                        registers.append(ethernet_route_register_template.format(prefix,
                                                                                 Globals.layer2_prot,
                                                                                 node_to.get_mac_address(n_from),
                                                                                 node_to if type(
                                                                                         node_to) is not TopologyStructs.Station else "wlan0"))

            routing_script.write(route_script.format("\n".join(create_faces),
                                                     "\n".join(destroy_faces),
                                                     "\n".join(unregisters),
                                                     "\n".join(registers)))

            routing_script.close()

            os.chmod(Globals.scripts_dir + str(n_from) + routing_suffix,
                     stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR | stat.S_IRWXU)

            self.logger.debug("[{0}] NDN routing scripts created.".format(n_from))
            results[n_from] = True

        self.logger.info("Creating the NDN routing scripts")

        return start_thread_pool(self.node_list.values(), create_script)

    def reset_ndn_routing(self, rerouting=False):
        """
        Execute the routing script that cleans the routing table of each node.

        :return:
        """

        def reset_routing(n, results):

            if rerouting:
                params = ["/root/{0}{1}".format(n, routing_suffix), "reset_routing"]
            else:
                params = ["/root/{0}{1}".format(n, routing_suffix), "reset"]

            try:
                ret = n.run_command(params)

                if ret:
                    self.logger.info("[{0}] Routing table successfully cleaned".format(n))
                    results[n] = True
                else:
                    self.logger.error("[{0}] Error cleaning the routing table. Params: {1}".format(n, params))
                    print(make_colored("red", "[{0}] Error cleaning the routing table".format(n)))
                    results[n] = False
            except Exception as error:
                self.logger.error("[{0}] Error cleaning the routing table. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), reset_routing)

    def push_routing_scripts(self):
        """
        Push the routing scripts inside the containers

        :return:
        """

        def push_scripts(n, results):

            routing_set_script = "/root/{0}{1}".format(n,
                                                       routing_suffix)

            try:
                ret = n.push_file(Globals.scripts_dir + str(n) + routing_suffix,
                                  routing_set_script)

                if ret:
                    self.logger.info("[{0}] Routing script successfully pushed inside the container".format(n))
                    results[n] = True
                else:
                    self.logger.error("[{0}] Error pushing NDN routing script".format(n))
                    print(make_colored("red", "[{0}] Error pushing NDN routing script".format(n)))
                    results[n] = False
            except Exception as error:
                self.logger.error("[{0}] Error pushing NDN routing script."
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        return start_thread_pool(self.node_list.values(), push_scripts)

    def set_ndn_routing(self, rerouting=False):
        """
        Execute the routing scripts in order to fill the routing tables of the nodes.

        :return:
        """

        def set_routing(n, results):
            try:
                if rerouting:
                    params = ["/root/{0}{1}".format(n, routing_suffix), "set_routing"]
                else:
                    params = ["/root/{0}{1}".format(n, routing_suffix), "set"]

                ret = n.run_command(params)

                if ret:
                    self.logger.info("[{0}] NDN routing set".format(n))
                    results[n] = True
                else:
                    self.logger.error("[{0}] Error while executing the NDN routing script".format(n))
                    print(make_colored("red", "[{0}] Error while executing the NDN routing script".format(n)))
                    results[n] = False
            except Exception as error:
                self.logger.error("Error while executing the NDN routing script {0}. "
                                  "Error: {1}".format(n,
                                                      error))
                results[n] = False

        self.logger.info("Setting NDN routing")

        return start_thread_pool(self.node_list.values(), set_routing)

    def list_nfd_status(self):
        """
        Show the routing tables of the nodes in the network.

        :return:
        """
        self.logger.info("Listing nfd status")

        for node in self.node_list.values():
            params = ["nfd-status", "-fb"]
            print(make_colored("blue", node))
            print("\n\n")
            try:
                ret = node.run_command(params, output=True)
            except Exception as error:
                self.logger.error("[{0}] Error showing NFD status. "
                                  "Error: {1}".format(node,
                                                      error))
                ret = False

            if not ret:
                self.logger.error("[{0}] Error displaying NFD-STATUS".format(node))
                print(make_colored("red", "[{0}] Error displaying NFD-STATUS".format(node)))

    def execute_cmd(self, cmd):
        """
        Execute the command on each node of the network.

        :param cmd: The array with the command and the parameters to execute.
        :return:
        """
        self.logger.info("Executing cmd {0}".format(cmd))

        def exec_command(n, results):
            try:
                ret = n.run_command(cmd)

                if ret:
                    self.logger.error("[{0}] executeCmd {1} returned an error".format(n,
                                                                                      cmd))
                    print(make_colored("red", "[{0}] executeCmd returned an error".format(n)))
                    results[n] = False
                else:
                    self.logger.info("[{0}] Successfully Executed cmd {1}".format(n,
                                                                                  cmd))
                    results[n] = True
            except Exception as error:
                self.logger.error("[{0}] Error executing command {2}. "
                                  "Error: {1}".format(n,
                                                      error,
                                                      cmd))
                results[n] = False

        return start_thread_pool(self.node_list.values(), exec_command)

    def start_test(self):
        """
        Run the test by starting the clients.

        :return:
        """
        shutil.rmtree(Globals.log_dir)
        os.mkdir(Globals.log_dir)

        self.logger.info("BEGIN TEST")

        Globals.test_start_time = time.time()

        self.logger.info("Test start time={0}".format(Globals.test_start_time))

        client_manager_list = []

        # Start all the clients

        for node in self.node_list.values():
            for client in node.get_client_apps():
                self.logger.debug("[{0}] Starting client {1}".format(node, client))

                cm = ClientManager(client, node)
                client_manager_list.append(cm)
                cm.start()

        # Wait for clients' end
        for cm in client_manager_list:
            cm.join()

        # Wait until the end of the test in case the total
        # duration = time.time() - int(Globals.test_start_time)
        # if duration <= int(Globals.test_duration):
        #     time.sleep(float(int(Globals.test_duration) - duration))

        for node in self.node_list.values():
            params = ["killall",
                      "ndn-icp-download"]

            ret = node.run_command(params)
            if ret:
                print(make_colored("red", "\t# Error while stopping ndn-icp-download on {0}".format(node)))

        self.logger.info("END TEST")


class ClientManager(threading.Thread):
    """
    Class that start the clients on the network. This class extends the :class:`threading.Thread` class, and it is
    used to start each producer with a different thread. In this way all the clients start more or less at the same time.

    :ivar client: The client to start
    :ivar container: The container on which the client has to run
    """

    def __init__(self, client, node):
        threading.Thread.__init__(self)
        self._stopper = threading.Event()
        self.client = client
        self.file_sizes = {}
        self.node = node

        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)

    def run(self):
        """
        The function executed in the thread. It simply starts the client on the node container.

        :return:
        """
        # client_duration = Globals.test_duration \
        #     if (self.client.get_duration() <= 0 or
        #         self.client.get_duration > Globals.test_duration - self.client.get_start_time()) \
        #     else self.client.get_duration()
        #
        # params = ["localclient",
        #           str(Globals.file_size),
        #           str(Globals.file_size_distribution),
        #           str(self.client.arrival),
        #           str(Globals.flow_control_gamma),
        #           str(Globals.flow_control_p_min),
        #           str(Globals.flow_control_p_max),
        #           str(Globals.flow_control_beta),
        #           str(Globals.flow_control_est_len),
        #           str(Globals.PIT_lifetime),
        #           str(Globals.flow_control_timeout),
        #           str(Globals.test_duration),
        #           str(self.client.popularity),
        #           str(self.client.catalog_name),
        #           str(self.client.cid),
        #           str(self.client.start_time),
        #           str(client_duration)]
        #
        # self.logger.info("[{0}] Params={1}".format(self.client.get_client_id(), params))

        params = ["ndn-icp-download",
                  "-u",
                  self.client.get_name()]
        print(make_colored('blue', 'downloading ...'))
        ret = self.node.run_command(params)

        if not ret:
            self.logger.error("[{0}] Error executing client application {1}".format(self.node,
                                                                                    self.client.get_client_id()))
            print(make_colored("red", "[{0}] Error executing "
                                      "client application {1}".format(self.node,
                                                                      self.client.get_client_id())))

    def stop(self):
        self._stopper.set()
