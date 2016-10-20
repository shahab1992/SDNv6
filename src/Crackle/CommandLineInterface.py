"""
This module provide to the user a useful CLI through which he can control and setup the experiments.
"""
import argparse
import cmd
import copy
import logging
import logging.config
import os
import shlex
import sys
import traceback
import time
from random import uniform

import Crackle.NDNManager as NDNManager
import Crackle.NetworkManager as NetworkManager
from Crackle import ConfigReader as ConfigParser
from Crackle.RoutingNdn import RoutingNdn
from Crackle.ClusterManager import ClusterManager
from Crackle.ColoredOutput import make_colored
from Crackle.MobilityManager import MobilityManager, grouped
import Crackle.Globals as Globals
from Crackle.Constants import __maximum_flow__, __tree_on_producer__, \
    __min_cost_multipath__, __tree_on_consumer__
from sympy import Point, Segment
from Crackle.TopologyStructs import Station, BaseStation

__author__ = 'shahab'

# Create a logger
logging.config.fileConfig('../config/logging.conf',
                          disable_existing_loggers=False)

module_logger = logging.getLogger(__name__)
log_file = "/tmp/crackle.log"

# TODO Change the code of ns3 in order to have a different mobility model for each  mobile entity
# TODO Print an experiment summary
# TODO Move routes to link in order to delete everything recursively?

"""
This module implements the Command Line Interface (CLI) for Crackle. It expose a set of commands through which the user
can interact with the software, by executing experiments and retrieving the results.

"""

welcome = make_colored("cyan",
                       """
       /---------------------------
      /  |5                       /
     /  _|\/                     /
    /  |_|/\/                   /
   /   ----- Welcom To Crackle / 
  /      ||_5                  /
 /      _||                  /
/      |_||                 /
---------------------------
                     """)

help = make_colored("darkgreen",
                    """
                    * Help:
                        General commands:
                            help: this help
                            help [command]: help for the command
                            howto: how-to
                            clear: bash clear command to clean-up the terminal
                            configure -c <directory>: configure crackle for the experiment described in directory
                            configure -s: display the configuration
                            quit: quit crackle

                        NDN commands:
                            start_ndn: start nfd
                            stop_ndn: kill nfd
                            start_repo: start ndn repository(ies)
                            kill_repo: kill ndn repository(ies)
                            list_clients: list ndn consumers
                            list_repo: list ndn repositories
                            route_ndn: set ndn routing
                            stat_ndn: list nfd forwarding table
                            set_cache: set the cache following the settings in topo.brite file
                            reset_cache: reset cache
                            check_forwarder_status: check if the forwarder is alive on every node

                        Network commands:
                            ping: ping nodes
                            list_nodes: list nodes
                            route: list routes
                            ifconf: list interfaces
                            script: create scripts
                            create_links: execute creation scripts
                            remove_links: execute removal scripts
                            start_stats: launch ifstat commands to capture per link bandwidth and mpstats for CPU occupancy
                            kill_stats: kill ifstat and mpstats

                        Mobility commands:
                            start_mobility: start the movement of the mobile nodes of the experiment
                            show_mobility_status: allow thread to print out their status to see information about mobility
                            stop_mobility: stop_nodes_movement

                        Test commands:
                            setup_environment: prepare network and ndn to the test (executes script, lcreate, startndn, startrepo, routendn)
                            start: run the test (and collect statistics at the end)
                            get_stats: collect statistics
                            start_bulk <n>: execute n identical tests one after the other
                    """)

how_to = """
  * Brief guided tour of the functions of Crackle:
    0) fill the configuration files (mobility.model, routing.dist, topo.brite, workload.conf, settings.conf) and start crackle
    1) configure crackle by typing "configure -c <path_to_test_folder>"
    2) verify the connectivity of the nodes --> ping, list_repo, list_client, tunnel, ifconf
    3) create and execute tunnel scripts --> script, lcreate
    4) start nfd and the repositories --> startndn, startrepo
    5) configure ndn routing --> routendn
    6) start the mobility (if any) --> start_mobility
    7) start download test --> start
        NOTE: for a fast test use setup_environment, start
"""

Routing_Table = make_colored("yellow", "----------------- Routing_Table -------------------")
dash_line = make_colored("yellow", "---------------------------------------------------")

__command_link__ = "link"
__command_route__ = "route"
__command_node__ = "node"
__command_repo__ = "repo"

__command_add__ = "add"
__command_delete__ = "delete"
__command_edit__ = "edit"
__command_show__ = "show"
__command_ping__ = "ping"
__command_exec__ = "exec"
__command_set__ = "set"
__command_auto__ = "auto"

__command_start__ = "start"
__command_stop__ = "stop"
__command_hide__ = "hide"


class ArgumentParser(argparse.ArgumentParser):
    """
    The class ArgumentParser extends the system class :class:`argparse.ArgumentParser`
    for what concerns the error management.
    """

    def error(self, message):
        """
        Print the error and the list of available commands.

        :param message: The error message
        :return:
        """
        self.print_usage(sys.stderr)
        self._print_message('{prog}: error: {message}\n'.format(prog=self.prog, message=message), sys.stderr)


def raw_input(prompt):
    """
    Print a message on command line and get user input
    :param prompt: message to be shown
    :return: the input line (without the '\n' character)
    """
    print(prompt, end='', flush=True)
    return sys.stdin.readline()[:-1]


class MyCmd(cmd.Cmd, object):
    """
    The class MyCmd inherits from the system class :class:`cmd.Cmd` and adds the following extensions:
        - The preloop prints the welcome message::

                       ================================================
                                       Welcome to Crackle
                       ================================================
                                * Type 'help' for a brief help
        - The list of available commands does not show the EOF command (ctrl + D)
        - The empty line command does not execute the last command
        - It override the class variables prompt, doc_header and ruler

    :cvar prompt: the prompt of the CLI. Value: "Crackle >"
    :cvar doc_header: the header for the list of available commands. Value: "Available commands (type help <command> for more info)"
    :cvar ruler: The character used to draw separator lines under the help-message headers. Value: "-"

    """
    prompt = make_colored('blue', 'Crackle > ')
    doc_header = make_colored("green", 'Available commands (type help <command> for more info)')
    ruler = '-'

    def preloop(self):
        """
        Print the welcome message before starting the CLI loop.

        :return:
        """
        print(welcome)

    def get_names(self):
        """
        Return the list of available commands.

        :return: The list of commands without the EOF (Ctrl + D) function.
        """
        names = super(MyCmd, self).get_names()
        if "do_EOF" in names:
            names.remove("do_EOF")
        return names

    def emptyline(self):
        """
        Override the base function in order to avoid re-executing the last command.
        """
        pass


class CrackleCmd(MyCmd):
    """
    CLI for Crackle. It inherits from MyCmd and implements the user interface.

    :ivar node_list: the list of nodes involved in the experiment. The object of the list are :class:`Crackle.TopologyStructs.Node`.
    :ivar net: the instance of :class:`Crackle.NetworkManager.NetworkManager`, that is in charge of managing the network.
    :ivar ndn: the instance of :class:`Crackle.NDNManager.NDNManager`, that is in charge of managing NDN.
    :ivar mob: the instance of :class:`Crackle.MobilityManager.MobilityManager`, that is in charge of managing the mobility.
    :ivar configured: boolean that indicates if crackle has been fed with the configuration files
    :ivar configure_parser: :class:`ArgumentParser` instance for parsing the configure command that require some arguments
    :ivar startbulk_parser: :class:`ArgumentParser` instance for parsing the start_bulk command that require some arguments
    """

    def __init__(self, node_list=None, net=None, ndn=None, mob=None, cluster=None, route=None):
        """
        Instantiate a CLI for crackle. If all the inputs are valid (not None) it configures the experiment with the
        received parameters, otherwise the CLI will be started without configuration. The user later has to specify
        the path of the experiment folder through the configure command.

        :param node_list: The list of nodes involved in the experiment. If received, it has been created by the creator of :class:`Crackle.CommandLineInterface.CrackleCmd`
        :param net: The instance of the :class:`Crackle.NetworkManager.NetworkManager`, that manages the network.
        :param ndn: The instance of the :class:`Crackle.NDNManager.NDNManager`, that manages NDN.
        :param mob: The instance of the :class:`Crackle.MobilityManager.MobilityManager`, that manages the mobility.
        :return:
        """
        super(MyCmd, self).__init__()

        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)

        self.logger.debug("Creating CLI instance.")

        self.node_list = None
        self.mobility_configured = False
        self.cluster_configured = False
        self.container_created = False

        if any(item is None for item in [net, ndn, mob, cluster, route]):
            self.logger.warning("WARNING: Configuration file is not set. You can set it through the configure"
                                "command. Type \'help configure\' for further details.")
            self.configured = False
        else:

            self.node_list = node_list
            self.net = net
            self.ndn = ndn
            self.mob = mob
            self.cluster = cluster
            self.route = route
            self.configured = True

            self.logger.debug("CLI initialized.")

        self.configure_parser = ArgumentParser('configure',
                                               description="Set up the experiment by reading the "
                                                           "configuration files contained in "
                                                           "directory_path.")

        self.configure_parser.add_argument('-c', '--conf_dir',
                                           metavar='directory_path',
                                           help="Path to directory with input files")

        self.configure_parser.add_argument('-s', '--show',
                                           action='store_true',
                                           help="Display the current crackle configuration")

        self.link_parser, self.link_subparsers = self.create_link_parser()
        self.node_parser, self.node_subparsers = self.create_node_parser()
        self.repo_parser, self.repo_subparser = self.create_repo_parser()
        self.client_parser, self.client_subparser = self.create_client_parser()

        self.route_parser, self.route_subparsers = self.create_route_parser()

        self.mobility_parser, self.mobility_subparsers = self.create_mobility_parser()

        self.startbulk_parser = ArgumentParser('start_bulk', description="Start N test")
        self.startbulk_parser.add_argument('N', help="Number of tests")

    def precmd(self, line):
        """
        Hook method executed just before the command line line is interpreted, but after the input prompt is generated and issued.
        It overrides the basic method of :class:`cmd.Cmd` by checking that crackle has been correctly configured with a proper configuration.
        If not, the issued command is not executed.

        :param line: The command line typed by the user
        :return: string of the command which will be executed
        """
        if line.startswith("configure") or self.configured or line == "" or line == "EOF" or line.startswith("help"):
            return line
        else:
            print(make_colored("red", "Crackle not configured."))
            print("Tap \"configure -c <path to experiment folder>\" to configure crackle. See documentation for details.")

            return ""

    def do_EOF(self, line):
        """
        Type Ctrl+D to exit from User CLI
        """
        self.logger.debug("Exiting from crackle.")
        self.exit_gracefully()
        return True

    # TODO Deprecated list of commands!
    def do_help(self, line):
        """
        Print the help message::

            * Help:
                General commands:
                    help: this help
                    help [command]: help for the command
                    howto: how-to
                    clear: bash clear command to clean-up the terminal
                    configure -c <directory>: configure crackle for the experiment described in directory
                    configure -s: display the configuration
                    quit: quit crackle

                NDN commands:
                    start_ndn: start nfd
                    stop_ndn: kill nfd
                    start_repo: start ndn repository(ies)
                    kill_repo: kill ndn repository(ies)
                    list_clients: list ndn consumers
                    list_repo: list ndn repositories
                    route_ndn: set ndn routing
                    stat_ndn: list nfd forwarding table
                    set_cache: set the cache following the settings in topo.brite file
                    reset_cache: reset cache
                    check_forwarder_status: check if the forwarder is alive on every node

                Network commands:
                    ping: ping nodes
                    list_nodes: list nodes
                    route: list routes
                    tunnel: list tunnels
                    ifconf: list interfaces
                    script: create scripts
                    create_links: execute creation scripts
                    remove_links: execute removal scripts
                    start_stats: launch ifstat commands to capture per link bandwidth and mpstats for CPU occupancy
                    kill_stats: kill ifstat and mpstats

                Mobility commands:
                    start_mobility: start the movement of the mobile nodes of the experiment
                    show_mobility_status: allow thread to print out their status to see information about mobility
                    stop_mobility: stop_nodes_movement
                Test commands:
                    setup_environment: prepare network and ndn to the test (executes script, lcreate, startndn, startrepo, routendn)
                    start: run the test (and collect statistics at the end)
                    get_stats: collect statistics
                    start_bulk <n>: execute n identical tests one after the other

        :param line: If this parameter is specified, this function prints the help message of the command contained in line.
        :return:
        """
        self.logger.debug("Printing help message")
        if line == "":
            print(help)
        else:
            super(CrackleCmd, self).do_help(line)

    def do_start(self, line):
        """
        Run the test and collect statistics at the end.
        """

        self.logger.debug("Starting Test.")
        self.ndn.start_test()
        self.net.get_stats()

    def do_ping(self, line):
        """
        Ping the nodes involved in the experiment.
        """

        self.net.ping_all()

    def do_ifconf(self, line):
        """
        Show the interfaces configuration (tunnel/physical/taps/bridges) on each node.
        """

        self.logger.debug("Showing interfaces on containers")
        self.net.list_interfaces()

    def do_howto(self, line):
        """
        Print a quick tutorial for running the experiment.
        """

        self.logger.debug("Printing How To")
        print(how_to)

    def do_clear(self, line):
        """
        Clear the screen.
        """
        os.system('clear')

    @staticmethod
    def create_node_parser():
        """
        Create an argument parser for the node command
        :return:
        """
        node_parser = ArgumentParser(__command_node__,
                                     description="Create/Delete nodes at runtime.")

        node_subparser = node_parser.add_subparsers(title="Subcommands",
                                                    description="Valid subcommands for "
                                                                "adding/deleting/editing/managing nodes",
                                                    dest="command_name")

        add_parser = node_subparser.add_parser(__command_add__,
                                               help="Add a new node, initially disconnected from the network.")
        add_parser.add_argument("node_name", type=str, help="The name of the node")
        add_parser.add_argument("cache_size", type=str, help="The cache size of the node in number of packets")
        add_parser.add_argument("forwarding_strategy", type=str, help="The forwarding strategy of the node")

        del_parser = node_subparser.add_parser(__command_delete__,
                                               help="Delete a node given the node ID")
        del_parser.add_argument("node_name", type=str, help="The identifier of the node")

        ping_parser = node_subparser.add_parser(__command_ping__,
                                                help="Test the connectivity between two nodes")
        ping_parser.add_argument("pinger", type=str, help="The node that start the ping")
        ping_parser.add_argument("pinged", type=str, help="The node to ping")

        show_parser = node_subparser.add_parser(__command_show__,
                                                help="Show the details of the node")
        show_parser.add_argument("node_name", type=str, help="The identifier of the node")

        exec_parser = node_subparser.add_parser(__command_exec__,
                                                help="Execute a command in the node.")
        exec_parser.add_argument("node_name", type=str, help="The name of the node")
        exec_parser.add_argument("command", type=str, nargs='+', help="The command to execute")

        edit_parser = node_subparser.add_parser(__command_edit__,
                                                help="Show the details of the node")
        edit_parser.add_argument("node_name", type=str, help="The identifier of the node")
        edit_parser.add_argument("forwarding_strategy", type=str, help="The forwarding strategy of the node")

        return node_parser, {__command_add__: add_parser,
                             __command_delete__: del_parser,
                             __command_ping__: ping_parser,
                             __command_show__: show_parser,
                             __command_edit__: edit_parser}

    @staticmethod
    def create_link_parser():
        """
        Create an argument parser for the link command.

        :return:
        """

        link_parser = ArgumentParser(__command_link__,
                                     description="Create/Delete links at runtime.")

        link_subparser = link_parser.add_subparsers(title="Subcommands",
                                                    description="Valid subcommands for "
                                                                "adding/deleting/editing/showing links",
                                                    dest="command_name")

        add_parser = link_subparser.add_parser(__command_add__,
                                               help="Add a link between 2 nodes.")
        add_parser.add_argument("node_from", type=str, help="The first endpoint of the link")
        add_parser.add_argument("node_to", type=str, help="The second endpoint of the link")
        add_parser.add_argument("capacity", type=str, help="The capacity of the link [kbps]")

        del_parser = link_subparser.add_parser(__command_delete__,
                                               help="Delete a link given the link ID")
        del_parser.add_argument("node_from", type=str, help="The first endpoint of the link")
        del_parser.add_argument("node_to", type=str, help="The second endpoint of the link")

        edit_parser = link_subparser.add_parser(__command_edit__,
                                                help="Edit the capacity of a link")
        edit_parser.add_argument("node_from", type=str, help="The first endpoint of the link")
        edit_parser.add_argument("node_to", type=str, help="The second endpoint of the link")
        edit_parser.add_argument("capacity", type=str, help="The capacity of the link [kbps]")

        show_parser = link_subparser.add_parser(__command_show__,
                                                help="Show all the link of the topology")

        return link_parser, {__command_add__: add_parser,
                             __command_delete__: del_parser,
                             __command_edit__: edit_parser,
                             __command_show__: show_parser}

    @staticmethod
    def create_mobility_parser():
        """
        Create an argument parser for the mobility command.

        :return:
        """

        mobility_parser = ArgumentParser(__command_link__,
                                         description="Start/Stop/Show/Hide mobility")

        mobility_subparser = mobility_parser.add_subparsers(title="Subcommands",
                                                            description="Valid subcommands for "
                                                                        "starting/stopping/showing/hiding links",
                                                            dest="command_name")

        start_parser = mobility_subparser.add_parser(__command_start__,
                                                     help="Start mobility of the stations.")

        stop_parser = mobility_subparser.add_parser(__command_stop__,
                                                    help="Stop the mobility of the stations")

        show_parser = mobility_subparser.add_parser(__command_show__,
                                                    help="Show the output of the mobility")

        hide_parser = mobility_subparser.add_parser(__command_hide__,
                                                    help="Hide the output of the mobility")

        return mobility_parser, {__command_start__: start_parser,
                                 __command_stop__: stop_parser,
                                 __command_show__: show_parser,
                                 __command_hide__: hide_parser}

    @staticmethod
    def create_repo_parser():

        """
        Create an argument parser for the repo command.

        :return:
        """

        repo_parser = ArgumentParser(__command_repo__,
                                     description="Add/Delete repo at runtime.")

        repo_subparser = repo_parser.add_subparsers(title="Subcommands",
                                                    description="Valid subcommands for "
                                                                "adding/deleting repos",
                                                    dest="command_name")

        add_parser = repo_subparser.add_parser(__command_add__,
                                               help="Add repo to node.")
        add_parser.add_argument("node_name", type=str, help="The node to put repo")
        add_parser.add_argument("repoId", type=str, help="RepoID of repository")
        add_parser.add_argument("folder", type=str, help="The folder to put")

        del_parser = repo_subparser.add_parser(__command_delete__,
                                               help="Delete a repository")
        del_parser.add_argument("node_name", type=str, help="The node to delete repo")
        del_parser.add_argument("repoId", type=str, help="RepoID of repository")
        del_parser.add_argument("folder", type=str, help="The folder to delete")

        return repo_parser, {__command_add__: add_parser,
                             __command_delete__: del_parser}

    @staticmethod
    def create_client_parser():
        """
        Create an argument parser for the repo command.

        :return:
        """

        client_parser = ArgumentParser(__command_repo__,
                                       description="Add/Delete client at runtime.")

        client_subparser = client_parser.add_subparsers(title="Subcommands",
                                                        description="Valid subcommands for "
                                                                    "adding/deleting repos",
                                                        dest="command_name")

        add_parser = client_subparser.add_parser(__command_add__,
                                                 help="Add client to node.")
        add_parser.add_argument("node_name", type=str, help="The node to put client")
        add_parser.add_argument("clientId", type=str, help="clientId of client")
        add_parser.add_argument("name", type=str, help="The name to search")

        del_parser = client_subparser.add_parser(__command_delete__,
                                                 help="Delete a client")
        del_parser.add_argument("node_name", type=str, help="The node to delete client")
        del_parser.add_argument("clientId", type=str, help="clientId of client")
        del_parser.add_argument("name", type=str, help="The name to delete")

        return client_parser, {__command_add__: add_parser,
                               __command_delete__: del_parser}

    @staticmethod
    def create_route_parser():
        """
        Create an argument parser for the link command.

        :return:
        """

        route_parser = ArgumentParser(__command_link__,
                                      description="Create/Delete routes at runtime and recompute global routing.")

        route_subparser = route_parser.add_subparsers(title="Subcommands",
                                                      description="Valid subcommands for "
                                                                  "adding/deleting/showing routes and "
                                                                  "setting routing algorithms",
                                                      dest="command_name")

        add_parser = route_subparser.add_parser(__command_add__,
                                                help="Add a route between 2 nodes.")
        add_parser.add_argument("icn_name", type=str, help="The icn name")
        add_parser.add_argument("node_name", type=str, help="The node where setting the route")
        add_parser.add_argument("next_hop", type=str, help="The nexthop")

        del_parser = route_subparser.add_parser(__command_delete__,
                                                help="Delete a route from the routing table of a node")
        del_parser.add_argument("icn_name", type=str, help="The name of the route")
        del_parser.add_argument("node_name", type=str, help="The node on which delete the route")
        del_parser.add_argument("next_hop", type=str, help="The nexthop")

        show_parser = route_subparser.add_parser(__command_show__,
                                                 help="Show the routing table of a node.")
        show_parser.add_argument("node_name", type=str, help="The name of the node")

        set_parser = route_subparser.add_parser(__command_set__,
                                                help="Set the global routing using a specific routing algorithm.")
        set_parser.add_argument("routing_algorithm", type=str,
                                help="The routing algorithm to use to compute the routing."
                                     " Options: {0} {1} {2} {3}".format(__tree_on_consumer__,
                                                                        __tree_on_producer__,
                                                                        __min_cost_multipath__,
                                                                        __maximum_flow__))

        auto_parser = route_subparser.add_parser(__command_auto__,
                                                 help="Set the global routing using automatic routing algorithm.")

        return route_parser, {__command_add__: add_parser,
                              __command_delete__: del_parser,
                              __command_show__: show_parser,
                              __command_set__: set_parser,
                              __command_auto__: auto_parser}

    def complete_link(self, text, line, begidx, endidx):
        """
        Auto completion for the link commande.

        :param text: String prefix we are attempting to match
        :param line: Current input line with leading whitespace removed
        :param begidx: beginning index of the prefix text, which could be used to provide different completion depending
                       upon which position the argument is in.
        :param endidx: ending index of the prefix text, which could be used to provide different completion depending
                       upon which position the argument is in.
        :return: List of matches for the current file path
        """

        commands = [__command_add__, __command_delete__, __command_edit__, __command_show__]

        splitted_line = shlex.split(line)

        if line[-1] == "-":
            text = splitted_line[-1]

        if len(splitted_line) == 1:
            return commands
        elif len(splitted_line) == 2 and text:
            return [command for command in commands if command.startswith(text)]
        if splitted_line[1] in [__command_add__, __command_delete__, __command_edit__]:
            if len(splitted_line) in [2, 3] and not text:
                return [node.get_node_id().replace(Globals.experiment_id, "") for node in self.node_list.values()]
            elif len(splitted_line) in [3, 4] and text:
                return [
                    node.get_node_id().replace(Globals.experiment_id, "")
                    for node in self.node_list.values()
                    if node.get_node_id().replace(Globals.experiment_id, "").startswith(
                            splitted_line[len(splitted_line) - 1])]

    def complete_node(self, text, line, begidx, endidx):
        """
        Auto completion for the node command.

        :param text: String prefix we are attempting to match
        :param line: Current input line with leading whitespace removed
        :param begidx: beginning index of the prefix text, which could be used to provide different completion depending
                       upon which position the argument is in.
        :param endidx: ending index of the prefix text, which could be used to provide different completion depending
                       upon which position the argument is in.
        :return: List of matches for the current file path
        """

        commands = [__command_add__, __command_delete__, __command_ping__, __command_show__, __command_exec__]

        splitted_line = shlex.split(line)

        if line[-1] == "-":
            text = splitted_line[-1]

        if len(splitted_line) == 1:
            return commands
        elif len(splitted_line) == 2 and text:
            return [command for command in commands if command.startswith(text)]
        if splitted_line[1] in [__command_delete__, __command_ping__, __command_show__, __command_exec__]:
            if len(splitted_line) in [2, 3] and not text:
                return [node.get_node_id().replace(Globals.experiment_id, "") for node in self.node_list.values()]
            elif len(splitted_line) in [3, 4] and text:
                return [
                    node.get_node_id().replace(Globals.experiment_id, "")
                    for node in self.node_list.values()
                    if node.get_node_id().replace(Globals.experiment_id, "").startswith(
                            splitted_line[len(splitted_line) - 1])]

    def complete_route(self, text, line, begidx, endidx):
        """
        Auto completion for the route command..

        :param text: String prefix we are attempting to match
        :param line: Current input line with leading whitespace removed
        :param begidx: beginning index of the prefix text, which could be used to provide different completion depending
                       upon which position the argument is in.
        :param endidx: ending index of the prefix text, which could be used to provide different completion depending
                       upon which position the argument is in.
        :return: List of matches for the current file path
        """

        commands = [__command_add__, __command_delete__, __command_set__, __command_show__, __command_auto__]

        splitted_line = shlex.split(line)

        if line[-1] == "-":
            text = splitted_line[-1]

        if len(splitted_line) == 1:
            return commands
        elif len(splitted_line) == 2 and text:
            return [command for command in commands if command.startswith(text)]
        if splitted_line[1] in [__command_show__]:
            if len(splitted_line) in [2, 3] and not text:
                return [node.get_node_id().replace(Globals.experiment_id, "") for node in self.node_list.values()]
            elif len(splitted_line) in [3, 4] and text:
                return [
                    node.get_node_id().replace(Globals.experiment_id, "")
                    for node in self.node_list.values()
                    if node.get_node_id().replace(Globals.experiment_id, "").startswith(
                            splitted_line[len(splitted_line) - 1])]
        if splitted_line[1] in [__command_delete__, __command_add__]:
            if len(splitted_line) in [3, 4] and not text:
                return [node.get_node_id().replace(Globals.experiment_id, "") for node in self.node_list.values()]
            elif len(splitted_line) in [4, 5] and text:
                return [
                    node.get_node_id().replace(Globals.experiment_id, "")
                    for node in self.node_list.values()
                    if node.get_node_id().replace(Globals.experiment_id, "").startswith(
                            splitted_line[len(splitted_line) - 1])]
        if splitted_line[1] in [__command_set__]:
            if len(splitted_line) in [2, 3] and not text:
                return [__tree_on_producer__, __tree_on_consumer__, __min_cost_multipath__,
                        __maximum_flow__]
            elif len(splitted_line) in [3, 4] and text:
                return [
                    routing_protocol
                    for routing_protocol in [__tree_on_producer__, __tree_on_consumer__, __min_cost_multipath__,
                                             __maximum_flow__]
                    if routing_protocol.startswith(
                            splitted_line[len(splitted_line) - 1])]

    def do_node(self, line):
        """
        Command for managing the nodes in the network
        :param line:
        :return:
        """

        try:
            args = self.node_parser.parse_args(shlex.split(line))
        except TypeError:
            return
        except SystemExit:
            return

        if args is None:
            self.logger.warning("You must specify an option among add|delete|ping|show|exec for the node command!")
            return

        node_name = None
        pinger = None
        pinged = None
        cache_size = None
        forwarding_strategy = None
        cmd = None

        if args.command_name in [__command_add__, __command_ping__, __command_delete__, __command_exec__,
                                 __command_show__, __command_edit__]:
            if not all([args.node_name]):
                self.node_subparsers[args.command_name].print_help()
                return
            node_name = Globals.experiment_id + args.node_name

        if args.command_name in [__command_ping__]:
            if not all([args.pinged, args.pinged]):
                self.node_subparsers[args.command_name].print_help()
                return
            pinger = Globals.experiment_id + args.pinger
            pinged = Globals.experiment_id + args.pinged

        if args.command_name in [__command_exec__]:
            if not all([args.command]):
                self.node_subparsers[args.command_name].print_help()
                return
            cmd = args.command

        if args.command_name in [__command_add__]:
            if not all([args.cache_size, args.forwarding_strategy]):
                self.node_subparsers[args.command_name].print_help()
                return
            try:
                cache_size = int(args.cache_size)
                if cache_size < 0:
                    raise ValueError
            except ValueError:
                self.logger.error("Error in node add: cache size should be an integer number.")
                print(make_colored("red", "ValueError for the cache size. Please insert a positve integer number."))
                return
            forwarding_strategy = args.forwarding_strategy

        if args.command_name in [__command_edit__]:
            if not all([args.forwarding_strategy]):
                self.node_subparsers[args.command_name].print_help()
                return

            forwarding_strategy = args.forwarding_strategy

        if args.command_name == __command_add__:
            self.net.add_node(node_name, cache_size, forwarding_strategy, self.container_created)
        elif args.command_name == __command_delete__:
            self.net.delete_node(node_name, self.container_created)
        elif args.command_name == __command_edit__:
            self.net.edit_node(node_name, forwarding_strategy, self.container_created)
        elif args.command_name == __command_ping__:
            self.net.ping(pinger, pinged)
        elif args.command_name == __command_exec__:
            self.net.exec(node_name, cmd, self.container_created)
        elif args.command_name == __command_show__:
            self.net.show_nodes(node_name)

    def do_link(self, line):
        """
        Command for managing the links in the network.
        """

        try:
            args = self.link_parser.parse_args(shlex.split(line))
        except TypeError:
            return
        except SystemExit:
            return

        if args is None:
            self.logger.warning("You must specify an option among add|delete|edit|show for the link command!")
            return

        node_to = None
        node_from = None
        capacity = None

        if args.command_name in [__command_add__, __command_delete__, __command_edit__]:
            if not all([args.node_from, args.node_to]):
                self.link_subparsers[args.command_name].print_help()
                return
            node_from = Globals.experiment_id + args.node_from
            node_to = Globals.experiment_id + args.node_to

        if args.command_name in [__command_add__, __command_edit__]:
            if not args.capacity:
                self.link_subparsers[args.command_name].print_help()
                return
            try:
                capacity = float(args.capacity) / 1000
            except ValueError:
                print(make_colored("red", "Please specify a float number for the capacity."))
                self.link_parser.print_help()
                return

        if args.command_name == __command_add__:
            self.net.add_link(node_to, node_from, capacity, self.container_created)

        # self.route.add_edge(node_from, node_to)

        elif args.command_name == __command_delete__:

            self.net.delete_link(node_from, node_to, self.container_created)

        # self.route.remove_edge(node_from, node_to)

        elif args.command_name == __command_edit__:
            self.net.edit_link(node_from, node_to, capacity, self.container_created)
        elif args.command_name == __command_show__:
            self.net.show_links()

    def do_repo(self, line):
        """
        Command for managing the repo in the network
        :param line:
        :return:
        """

        try:
            args = self.repo_parser.parse_args(shlex.split(line))
        except TypeError:
            return
        except SystemExit:
            return

        if args is None:
            self.logger.warning("You must specify an option among add|delete|ping|show|exec for the node command!")
            return

        node_name = None
        folder = None
        repoId = None
        if args.command_name in [__command_add__, __command_delete__]:
            if not all([args.node_name]):
                self.node_subparsers[args.command_name].print_help()
                return
            node_name = Globals.experiment_id + args.node_name

        if args.command_name in [__command_add__, __command_delete__]:

            if not all([args.folder, args.repoId]):
                self.node_subparsers[args.command_name].print_help()
                return
            try:
                folder = args.folder
                repoId = args.repoId
            except ValueError:
                self.logger.error("Error in node add: folder should be first prefix.")
                print(make_colored("red", "Error in node add: folder should be first prefix."))
                return

        if args.command_name == __command_add__:
            self.ndn.add_repository(node_name, repoId, folder)
        elif args.command_name == __command_delete__:
            self.ndn.delete_repository(node_name, repoId, folder)

    def do_client(self, line):
        """
        Command for managing the repo in the network
        :param line:
        :return:
        """

        try:
            args = self.client_parser.parse_args(shlex.split(line))
        except TypeError:
            return
        except SystemExit:
            return

        if args is None:
            self.logger.warning("You must specify an option among add|delete|ping|show|exec for the node command!")
            return

        node_name = None
        name = None
        clientId = None
        if args.command_name in [__command_add__, __command_delete__]:
            if not all([args.node_name]):
                self.node_subparsers[args.command_name].print_help()
                return
            node_name = Globals.experiment_id + args.node_name

        if args.command_name in [__command_add__, __command_delete__]:

            if not all([args.name, args.clientId]):
                self.node_subparsers[args.command_name].print_help()
                return
            try:
                name = args.name
                clientId = args.clientId
            except ValueError:
                self.logger.error("Error in node add: folder should be first prefix.")
                print(make_colored("red", "Error in node add: folder should be first prefix."))
                return

        if args.command_name == __command_add__:
            self.ndn.add_consumer(node_name, clientId, name)
        elif args.command_name == __command_delete__:
            self.ndn.delete_consumer(node_name, clientId, name)

    def help_link(self):
        """
        Print the help for the configure command.
        """
        self.logger.debug("Printing link help")
        self.link_parser.print_help()

    def complete_mobility(self, text, line, begidx, endidx):
        """
        Auto completion for the route command..

        :param text: String prefix we are attempting to match
        :param line: Current input line with leading whitespace removed
        :param begidx: beginning index of the prefix text, which could be used to provide different completion depending
                       upon which position the argument is in.
        :param endidx: ending index of the prefix text, which could be used to provide different completion depending
                       upon which position the argument is in.
        :return: List of matches for the current file path
        """

        commands = [__command_start__, __command_stop__, __command_show__, __command_hide__]

        splitted_line = shlex.split(line)

        if line[-1] == "-":
            text = splitted_line[-1]

        if len(splitted_line) == 1:
            return commands
        elif len(splitted_line) == 2 and text:
            return [command for command in commands if command.startswith(text)]

    def do_mobility(self, line):
        """
        Manage mobility from command line
        :return:
        """

        try:
            args = self.mobility_parser.parse_args(shlex.split(line))
        except TypeError:
            return
        except SystemExit:
            return

        if args is None:
            self.logger.warning("You must specify an option among start|stop|show|hide for the link command!")
            return

        if not self.mobility_configured:
            print(make_colored("yellow", "Start the experiment before starting the mobility!"))

        if args.command_name == __command_start__:
            self.logger.debug("Starting mobility of mobile stations")
            self.mob.start_mobility()
        elif args.command_name == __command_stop__:
            self.logger.debug("Stopping mobility threads")
            print("Stopping mobility threads")
            if self.mob.kill_threads():
                print(make_colored("green", "Mobility stopped"))
            else:
                print(make_colored("red", "Error stopping mobility."
                                          "See the log file {0} for details.".format(log_file)))
        elif args.command_name == __command_show__:
            self.logger.debug("Mobility thread output enabled")
            self.mob.set_output()
            print("Mobility thread output enabled")
        elif args.command_name == __command_hide__:
            self.logger.debug("Mobility thread output disabled")
            self.mob.unset_output()
            print("Mobility thread output disabled")

    def do_configure_router(self, line):
        """
        Set the caches of the nodes by reading the value from the topo.brite configuration file.
        """

        self.logger.debug("Setting cache of nodes")

        print(make_colored("blue", "Setting cache of nodes"))
        if self.ndn.configure_router():
            print(make_colored("green", "Caches set"))
        else:
            print(make_colored("red", "Error setting caches. See the log file {0} for details.".format(log_file)))

    def do_reset_cache(self, line):
        """
        Reset cache to the default value (65536 Packets).
        """

        self.logger.debug("Resetting cache of nodes")
        if self.ndn.reset_cache():
            print(make_colored("green", "Cache reset!"))
        else:
            print(make_colored("red", "Error resetting caches. See the log file {0} for details.".format(log_file)))

    def do_quit(self, line):
        """
        Quit from Crackle and clean the testbed.
        """

        self.logger.info("Exit from Crackle")
        self.exit()

    def do_configure(self, line):
        """
        Configure the experiment by reading the configuration file specified.
        Available command line arguments:

            -c <conf_directory_path>: Path to the directory containing the configuration files
            -s Show the current Crackle configuration
        """

        self.logger.debug("Parsing configuration files")
        self.logger.debug("Parsing configuration files")

        try:
            args = self.configure_parser.parse_args(shlex.split(line))
        except TypeError:
            return
        except SystemExit:
            return

        if args is None:
            self.logger.warning("You must specify the directory with the input files, or write -s to show the"
                                "configuration file!")
            return

        if args.show:

            self.logger.debug("Showing the list of nodes")

            if self.node_list is not None:
                for node in self.node_list.values():
                    print(node)
            else:
                self.logger.warning("No configuration!")
        elif args.conf_dir is not None:

            self.logger.info("Parsing configuration files")
            print(make_colored("blue", "Parsing configuration files"))

            self.node_list = ConfigParser.ConfigReader().setup_conf(args.conf_dir)

            if self.node_list is not None:
                self.cluster = ClusterManager(self.node_list)
                self.net = NetworkManager.NetworkManager(self.node_list, self.cluster.get_server_list())
                self.ndn = NDNManager.NDNManager(self.node_list, self.cluster.get_server_list())
                self.mob = MobilityManager(self.node_list, self.cluster.get_server_list(), self.ndn)
                self.route = RoutingNdn(self.node_list)
                self.configured = True
                print(make_colored("green", "Configuration terminated."))
                print(make_colored("green", "Your experiment ID is: {0}".format(Globals.experiment_id)))
            else:
                print(make_colored("red", "Error reading configuration files."
                                          "See the log file {0} for details.".format(log_file)))
        else:
            print(make_colored("yellow", "No options found. Type help to see the usage of this command."))
            self.logger.warning("No options found. Type help to see the usage of this command.")

    def help_configure(self):
        """
        Print the help for the configure command.
        """
        self.logger.debug("Printing configuration")
        print("Printing configuration")
        self.configure_parser.print_help()

    def complete_configure(self, text, line, begidx, endidx):
        """
        Auto completion for the file name. This function is really useful when the user has to specify the path to the
        experiment folder in the configure command.

        :param text: String prefix we are attempting to match
        :param line: Current input line with leading whitespace removed
        :param begidx: beginning index of the prefix text, which could be used to provide different completion depending
                       upon which position the argument is in.
        :param endidx: ending index of the prefix text, which could be used to provide different completion depending
                       upon which position the argument is in.
        :return: List of matches for the current file path
        """

        line = line.split()
        if len(line) == 2 and begidx == endidx:
            filename = ''
            path = './'
        elif len(line) == 3:
            path = line[2]
            if '/' in path:
                i = path.rfind('/')
                filename = path[i + 1:]
                path = path[0:i + 1]
            else:
                filename = path
                path = './'
        else:
            return

        ls = os.listdir(path)
        ls.sort()

        ls = ls[:]
        for i in range(len(ls)):
            if os.path.isdir(os.path.join(path, ls[i])):
                ls[i] += '/'
        if filename == '':
            return ls
        else:
            return [f for f in ls if f.startswith(filename)]

    def do_route(self, line):
        """
        Command for managing the routes in the network.
        """

        try:
            args = self.route_parser.parse_args(shlex.split(line))
        except TypeError:
            return
        except SystemExit:
            return

        if args is None:
            self.logger.warning("You must specify an option among add|delete|set|show| for the route command!")
            return

        icn_name = None
        node_name = None
        next_hop = None
        routing_algorithm = None

        if args.command_name in [__command_add__, __command_delete__]:
            if not all([args.icn_name, args.node_name, args.next_hop]):
                self.route_subparsers[args.command_name].print_help()
                return
            node_name = Globals.experiment_id + args.node_name
            icn_name = args.icn_name
            next_hop = Globals.experiment_id + args.next_hop

        if args.command_name in [__command_show__]:
            if not all([args.node_name]):
                self.route_subparsers[args.command_name].print_help()
                return
            node_name = Globals.experiment_id + args.node_name

        if args.command_name in [__command_auto__]:
            routing_algorithm = self.net.workload_routing()
            print(make_colored('green', routing_algorithm + ' Algorithm is used.'))

            self.ndn.recompute_global_routing(routing_algorithm, self.container_created)

        if args.command_name in [__command_set__]:
            if not all([args.routing_algorithm]):
                self.route_subparsers[args.command_name].print_help()
                return
            routing_algorithm = args.routing_algorithm

        if args.command_name == __command_add__:
            self.ndn.add_route(node_name, icn_name, next_hop, self.container_created)
        elif args.command_name == __command_delete__:
            self.ndn.delete_route(node_name, icn_name, next_hop, self.container_created)

        elif args.command_name == __command_set__:

            self.ndn.recompute_global_routing(self.route, routing_algorithm, self.container_created)

        elif args.command_name == __command_show__:
            self.ndn.show_route(node_name)

    def do_script(self, line):
        """
        Write the scripts for creating the tunnels in order to create the virtual topology.
        """

        self.logger.debug("Creating scripts for MACVALN interfaces")
        print(make_colored("blue", "Creating scripts for MACVALN interfaces"))
        if self.net.create_scripts():
            print("Scripts for MACVLAN interfaces created")
        else:
            print(make_colored("red", "Error creating scripts for links."
                                      "See the log file {0} for details.".format(log_file)))

    def do_create_links(self, line):
        """
        Create the links among the nodes in the network. The links are created by using IP tunnels.
        """

        self.logger.debug("Executing scripts for creating links")
        print("Executing scripts for creating links")
        if self.net.create_links():
            print(make_colored("green", "Links created successfully!"))
        else:
            print(make_colored("red", "Error creating links."
                                      "See the log file {0} for details.".format(log_file)))

    def do_remove_links(self, line):
        """
        Remove the links in the network (by removing the IP tunnel interfaces)
        """

        self.logger.debug("Executing scripts for removing links")
        print("Executing scripts for removing links")
        if self.net.remove_links():
            print(make_colored("green", "Links removed"))
        else:
            print(make_colored("red", "Error removing links."
                                      "See the log file {0} for details.".format(log_file)))

    def do_start_stats(self, line):
        """
        Launch, on each node, ifstat (to capture per link bandwidth) and mpstats (for CPU occupancy).
        """

        self.logger.debug("Starting ifstat and mpstat on nodes")
        if self.net.set_stats():
            print(make_colored("green", "Ifstat and mpstat started!"))
        else:
            print(make_colored("red", "Error starting ifstat and mpstat."
                                      "See the log file {0} for details.".format(log_file)))

    def do_print(self, line):
        #        l = []
        #        for i in self.node_list.values():


        #            l.append(format(i))
        #            for j in i.links.values():

        #                l.append(format(j.node_to))
        #                l.append(format(j.bandwidth))
        #            l.append("")
        #        print("ss")
        #        for node in self.node_list:
        ll = {}
        for node in self.node_list.keys():
            #            repositories = node.get_repositories()

            #            for repo in repositories:
            #                content = repo.get_folder().replace('/ndn/', '')

            #                ll[repo.get_repo_id().strip('repo-')] = content

            print(node)

    def do_kill_stats(self, line):
        """
        Kill ifstat and mpstats on each node involved in the experiment.
        """

        self.logger.debug("Killing ifstat and mpstat on nodes")
        if self.net.kill_stats():
            print(make_colored("green", "Ifstat and mpstat killed!"))
        else:
            print(make_colored("red", "Error killing ifstat and mpstat."
                                      "See the log file {0} for details.".format(log_file)))

    def do_start_ndn(self, line):
        """
        Start the NDN forwarder on each node involved in the experiment.
        """

        self.logger.debug("Starting NFD on nodes in the network")
        if self.ndn.start_nfd():
            print(make_colored("green", "NFD started!"))
        else:
            print(make_colored("red", "Error starting NFD."
                                      "See the log file {0} for details.".format(log_file)))

    def do_stop_ndn(self, line):
        """
        Stop the NDN forwarder on thenodes involved in the experiment
        """

        self.logger.debug("Stopping NFD on nodes in the network")
        if self.ndn.stop_nfd():
            print(make_colored("green", "NFD stopped!"))
        else:
            print(make_colored("red", "Error stopping NFD."
                                      "See the log file {0} for details.".format(log_file)))

    def do_route_ndn(self, line):
        """
        Fill the NDN routing tables by reading the configuration file routing.dist.
        """

        self.logger.debug("Filling routing tables of nodes")
        if self.ndn.create_routing_scripts():
            print(make_colored("green", "Routing scripts created!"))
        else:
            print(make_colored("red", "Error creating routing scripts."
                                      "See the log file {0} for details.".format(log_file)))

    def do_stat_ndn(self, line):
        """
        Show the NDN routing table of each node involved in the experiment.
        """
        self.logger.debug("Showing routing tables of nodes")
        self.ndn.list_nfd_status()

    def do_start_repo(self, line):
        """
        Start the ndn repository(ies)
        """

        self.logger.debug("Starting repositories in the network")
        if self.ndn.start_repositories():
            print(make_colored("green", "Repositories started!"))
            print(make_colored("green", "Please wait ..."))
        else:
            print(make_colored("red", "Error starting repositories."
                                      "See the log file {0} for details.".format(log_file)))

    def do_start_virtual_repo(self, line):
        """
        Start the ndn repository(ies)
        """

        self.logger.debug("Starting repositories in the network")
        if self.ndn.start_virtual_repositories():
            print(make_colored("green", "Repositories started!"))
            print(make_colored("green", "Please wait ..."))
        else:
            print(make_colored("red", "Error starting repositories."
                                      "See the log file {0} for details.".format(log_file)))

    def do_kill_repo(self, line):
        """
        Kill the NDN repository(ies)
        """

        self.logger.debug("Killing repositories in the network")
        if self.ndn.stop_repositories():
            print(make_colored("green", "Repositories killed!"))
        else:
            print(make_colored("red", "Error killing repositories."
                                      "See the log file {0} for details.".format(log_file)))

    def do_list_repo(self, line):
        """
        Show all the NDN repository(ies) (the producers)
        """

        self.logger.debug("Showing repositories in the network")
        self.ndn.list_repositories(False)

    def do_list_client(self, line):
        """
        List the NDN client(s) (the consumers)
        """
        self.logger.debug("Showing clients in the network")
        self.ndn.list_clients()

    def do_exec(self, line):
        """
        Execute a command on all the node of the experiment
        """

        args = self.configure_parser.parse_args(shlex.split(line))
        self.logger.debug("Executing command {0} on each node of the network".format(args))
        if self.ndn.execute_cmd(args):
            print(make_colored("green", "Command {0} executed!".format(args)))
        else:
            print(make_colored("red", "Error executing {0}."
                                      "See the log file {1} for details.".format(args, log_file)))

    def do_start_containers(self, line):
        """
        Start the linux containers representing the nodes of the experiment.
        """

        self.logger.debug("Starting linux containers")
        if self.net.start_containers():
            print(make_colored("green", "Containers started!"))
        else:
            print(make_colored("red", "Error starting containers."
                                      "See the log file {0} for details.".format(log_file)))

    def setup_environment(self):
        """
        Quickly setup the experiment environment following the configuration file. This function does not start the
        experiment itself but set up the environment by:

            - Creating the virtual links between the nodes
            - Setting the cache size with the value in the topo.brite file
            - Starting the NDN forwarder
            - Setting the cache on the NDN forwarder
            - Setting the NDN routing tables of each node
            - Starting the mobility of the stations
        """

        self.logger.debug("Setting up the environment")

        try:
            if not self.cluster_configured:
                if self.cluster.setup_cluster():
                    print(make_colored("green", "Cluster set up!"))
                    self.logger.debug("Cluster successfully set up!")
                    self.cluster_configured = True
                else:
                    print(make_colored("red", "Error setting up the cluster."
                                              "See the log file {0} for details.".format(log_file)))
                    return False

            if not self.container_created:
                if self.net.spawn_containers():
                    print(make_colored("green", "Containers spawned!"))
                    self.container_created = True
                    self.logger.debug(
                            "Containers created on the cluster. Servers: {0}".format(self.cluster.get_server_list()))
                else:
                    self.logger.error(
                            "Error spawning containers on the cluster. Servers: {0}".format(
                                    self.cluster.get_server_list()))
                    print(make_colored("red", "Error spawning containers. "
                                              "See the log file {0} for details.".format(log_file)))
                    return False

                if self.net.start_containers():
                    print(make_colored("green", "Containers started!"))
                else:
                    print(make_colored("red", "Error starting containers. "
                                              "See the log file {0} for details.".format(log_file)))
                    return False

                if self.net.create_scripts():
                    print(make_colored("green", "Scripts for MACVLAN interfaces created"))
                else:
                    print(make_colored("red", "Error creating scripts for links. "
                                              "See the log file {0} for details.".format(log_file)))
                    return False

                if self.net.create_links():
                    print(make_colored("green", "Links created successfully!"))
                else:
                    print(make_colored("red", "Error creating links. "
                                              "See the log file {0} for details.".format(log_file)))
                    return False

                if self.net.set_stats():
                    print(make_colored("green", "Ifstat and mpstat started!"))
                else:
                    print(make_colored("red", "Error starting ifstat and mpstat. "
                                              "See the log file {0} for details.".format(log_file)))
                    return False

                if self.ndn.configure_router():
                    print(make_colored("green", "Router Configured"))
                else:
                    print(make_colored("red",
                                       "Error Configuring router. See the log file {0} for details.".format(log_file)))
                    return False

                if self.ndn.create_routing_scripts():
                    print(make_colored("green", "Routing scripts created!"))
                else:
                    print(make_colored("red", "Error creating routing scripts. "
                                              "See the log file {0} for details.".format(log_file)))
                    return False

                if self.ndn.push_routing_scripts() and self.ndn.set_ndn_routing():
                    print(make_colored("green", "NDN routing set!"))
                else:
                    print(make_colored("red", "Error setting the routing. "
                                              "See the log file {0} for details.".format(log_file)))
                    return False

                if self.mob.setup_mobility():
                    print(make_colored("green", "Mobility correctly set up!"))
                    self.mobility_configured = True
                else:
                    print(make_colored("red", "Error setting the mobility. "
                                              "See the log file {0} for details.".format(log_file)))
                    return False
        except Exception as e:
            self.logger.error("Error during the configuration. {0}".format(traceback.print_exc()))
            print(make_colored("red", "Error during the configuration. See log for further details."))

    def do_setup_environment(self, line):
        """
        Quickly setup the experiment environment following the configuration file. This function does not start the
        experiment itself but set up the environment by:

            - Creating the virtual links between the nodes
            - Setting the cache size with the value in the topo.brite file
            - Starting the NDN forwarder
            - Setting the cache on the NDN forwarder
            - Setting the NDN routing tables of each node
            - Starting the mobility of the stations
        """
        self.setup_environment()

    def do_reset_environment(self, line):
        """
        Quickly reset the environment in order to start a new experiment
        """

        self.logger.debug("Resetting the environment.")
        self.mob.kill_threads()
        self.mobility_configured = False
        self.net.stop_containers()
        self.container_created = False
        self.setup_environment()

    def do_open_terminal(self, line):
        """
        Open a terminal in a given linux container enabling X 11 Forwarding

        :param line:
        :return:
        """

        if line:
            container_name = shlex.split(line)[0]
        else:
            print(make_colored("red", "Please insert the nome of one node."))
            return

        if container_name is None:
            self.logger.debug("Error: no container specified.")
            print(make_colored("red", "You must specify the name of the container!"))
            return
        else:
            self.net.open_terminal(container_name)

    def do_start_bulk(self, line):
        """
        Start n experiment in parallel. The n parameter has to be specified as command line argument as follow:

        start_bulk n
        """

        try:
            args = self.startbulk_parser.parse_args(shlex.split(line))
        except SystemExit:
            return

        if args.N is None:
            self.logger.debug("Error: no test number specified in the start_bulk call.")
            print(make_colored("red", "You must specify the number of tests to execute"))
            return
        else:
            self.logger.debug("Starting {0} experiments.".format(args.N))
            for i in range(int(args.N)):
                self.mob.kill_threads()
                self.net.stop_containers()
                self.net.start_containers()
                self.setup_environment()

    def help_start_bulk(self):
        """
        Print the help for the start_bulk command.
        """

        self.logger.debug("Printing start_bulk help")
        self.startbulk_parser.print_help()

    def do_get_stats(self, line):
        """
        Get statistics from each node after the experiment
        """

        self.logger.debug("Getting the statistic files")
        self.net.get_stats()

    def exit(self):
        """
        Exit from the program by cleaning the environment.
        """

        print(make_colored("green", "Cleaning the cluster. Wait.."))
        if self.configured:
            if self.container_created:
                self.logger.debug("Killing all the containers")
                if not self.net.stop_containers():
                    self.net.delete_containers()

            if self.mobility_configured:
                self.mob.kill_threads()
                self.mob.clean_servers()

            if self.cluster_configured:
                self.logger.debug("Cleaning the cluster")
                self.cluster.clean_cluster()

            self.logger.debug("Killing any other thread launched by this application")
            # params = ["killall",
            #          "-9",
            #          "python3"]
            # p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

            # Never reached..
        sys.exit()

    def exit_gracefully(self):
        """
        Ask the user if he really wants to exit from the cmd loop
        :return:
        """

        try:
            if raw_input(make_colored("yellow", "\nReally quit? (y/n) ")).lower().startswith('y'):
                self.exit()
        except KeyboardInterrupt:
            print(make_colored("red", "\nOk ok, quitting"))
            self.exit()
