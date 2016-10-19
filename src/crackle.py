#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
import time
import traceback

import Crackle.Globals as MyGlobals
from Crackle import Constants
from Crackle.NetworkManager import NetworkManager
from Crackle.ColoredOutput import make_colored
from Crackle.NDNManager import NDNManager
from Crackle.CommandLineInterface import CrackleCmd
from Crackle.ConfigReader import ConfigReader
from Crackle.MobilityManager import MobilityManager
from Crackle.ClusterManager import ClusterManager

# _DEBUG=True
_DEBUG = False


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self._print_message(make_colored('red', '{prog}: error: {message}\n'.format(prog=self.prog, message=message)),
                            sys.stderr)

        self.print_usage(sys.stdout)
        sys.exit(-1)


batch_usage = make_colored("green",
    """
        Usage: python crackle.py [-s] path_to_folder [-n] n_times]:
        -t: start test (only if you give a valid experiment description in the files described above).
        -s: folder containing the configuration for the experiment. It should contain 4 files:
              - topo.brite     -> it contains the description of the topology
              - routing.dist   -> it contains the informations for building the routing tables at each node
              - workload.conf  -> it contains the description of the clients and the repos involved in the experiment
              - mobility.model -> it contains the description of the mobility models for each mobile entity involved
                                  in the experiment
              - settings.conf  -> it contains the settings for the experiment regarding username, file locations ...
        -n n_times: execute the test multiple times
    """)


def setup(ndn, net, mobility):
    shutil.rmtree(MyGlobals.log_dir + "/*")
    net.create_scripts()
    net.create_links()
    net.set_stats()
    ndn.start_nfd()
    ndn.start_repositories()
    ndn.configure_router()
    ndn.create_routing_scripts()
    ndn.set_ndn_routing()
    time.sleep(10)

    # TODO Start test function call


def main():

    n_times = 1
    background = False
    node_list, net, ndn, mob, cluster = None, None, None, None, None

    parser = ArgumentParser(description=make_colored('green', "Batch usage of Crackle."))
    parser.add_argument('-s', metavar='configuration_file_path',
                        help="folder containing the configuration for the experiment. It should contain 4 files:"
                             "- topo.brite     -> it contains the description of the topology\n"
                             "- routing.dist   -> it contains the informations for building the routing tables"
                             "at each node\n"
                             "- workload.conf  -> it contains the description of the clients and the repos involved in"
                             "the experiment\n"
                             "- mobility.model -> it contains the description of the mobility models for each"
                             "mobile entity involve in the experiment)\n"
                             "- settings.conf  -> it contains the settings for the experiment regarding username,"
                             "file locations ...")
    parser.add_argument('-t', action='store_true', help='Start test in background')
    parser.add_argument('-n', metavar='n_times', type=int,  help='Execute the test multiple times')

    arguments = parser.parse_args()
    args = vars(arguments)

    for option in args.keys():
        if args[option] is not None:
            if option == "s":
                print(" * Loading the configuration files at {0}".format(args[option]))
                conf_reader = ConfigReader()
                node_list = conf_reader.setup_conf(args[option])
            elif option == "t" and args[option] is True:
                background = True
            elif option == "n":
                n_times = args[option]

    if node_list is not None:
        cluster = ClusterManager(node_list=node_list)
        net = NetworkManager(node_list, cluster.get_server_list())
        ndn = NDNManager(node_list, cluster.get_server_list())
        mob = MobilityManager(node_list, cluster.get_server_list(), ndn)

        if background:
            for i in range(n_times):
                setup(ndn, net, mob)
                ndn.start_test()
                net.get_stats()
                sys.exit(0)

    crackle = CrackleCmd() if any(item is None for item in [node_list, net, ndn, mob, cluster]) else CrackleCmd(node_list=node_list,
                                                                                                          net=net,
                                                                                                          ndn=ndn,
                                                                                                          mob=mob,
                                                                                                          cluster=cluster)
    while True:
        try:
            crackle.cmdloop()
            break
        except KeyboardInterrupt:
            crackle.exit_gracefully()
        except Exception as e:
            traceback.print_exc()
            crackle.exit()

if __name__ == "__main__":

    main()
