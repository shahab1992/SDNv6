"""
This module contains the class :class:`Crackle.ConfigReader.ConfigReader` that is able to parse the configuration files
describing the experiment to execute.

These files are the following:

    - topo.brite, that contains the topology description. The format of this file is the following (Mobile Fat Tree)::

            Topology: ( 29 ns, 42 Edges )

            Nodes: (28)
            #Name    #Not Used  #Cache Probability      #Cache Size  #Cache Policy  #Not Used                       #Node Type
            n-0      251        100                     0            l              2                       		AS_NODE
            n-1      696        100                     0            l              2                               AS_NODE
            n-2      696        100                     0            l              2                       		AS_NODE
            n-3      251        100                     0            l              2		                      	AS_NODE
            n-4      696        100                     0            l              2                               AS_NODE
            n-5      696        100                     0            l              2       	              		AS_NODE
            n-6      696        100                     0            l              2		              		    AS_NODE
            n-7      696        100                     0            l              2	 	              		    AS_NODE
            n-8      696        100                     0            l              2		              		    AS_NODE
            n-9      696        100                     0            l              2		              		    AS_NODE
            n-10     696        100                     0            l              2		              		    AS_NODE
            n-11     696        100                     0            l              2		              		    AS_NODE
            n-12     696        100                     0            l              2		              		    AS_NODE
            n-13     696        100                     1000         l              2	25	175    square   50      AS_BASE_STATION
            n-14     696        100                     1000         l              2	75	175    square   50      AS_BASE_STATION
            n-15     696        100                     1000         l              2	125	175    square   50      AS_BASE_STATION
            n-16     696        100                     1000         l              2   175	175    square   50      AS_BASE_STATION
            n-17     696        100                     1000         l              2   25	125    square   50      AS_BASE_STATION
            n-18     696        100                     1000         l              2   75	125    square   50      AS_BASE_STATION
            n-19     696        100                     1000         l              2  125	125    square   50      AS_BASE_STATION
            n-20     696        100                     1000         l              2  175	125    square   50      AS_BASE_STATION
            n-21     696        100                     1000         l              2  25	75     square   50      AS_BASE_STATION
            n-22     696        100                     1000         l              2  75	75     square   50      AS_BASE_STATION
            n-23     696        100                     1000         l              2  125	75     square   50      AS_BASE_STATION
            n-24     696        100                     1000         l              2  175	75     square   50      AS_BASE_STATION
            n-25     696        100                     1000         l              2  25	25     square   50      AS_BASE_STATION
            n-26     696        100                     1000         l              2  75	25     square   50      AS_BASE_STATION
            n-27     696        100                     1000         l              2  125	25     square   50      AS_BASE_STATION
            n-28     696        100                     0            l              2  175	25     square   50      AS_BASE_STATION
            n-29     696        100                     0            l              2  10	50                      AS_MOBILE_NODE
            n-30     696        100                     0            l              2  170	180    		            AS_MOBILE_NODE
            n-31     696        100                     0            l              2  10	50                      AS_MOBILE_NODE
            n-32     696        100                     0            l              2  170	180    		            AS_MOBILE_NODE
            n-33     696        100                     0            l              2  10	50                      AS_MOBILE_NODE
            n-34     696        100                     0            l              2  170	180    		            AS_MOBILE_NODE
            n-35     696        100                     0            l              2  10	50                      AS_MOBILE_NODE
            n-36     696        100                     0            l              2  170	180    		            AS_MOBILE_NODE
            n-37     696        100                     0            l              2  10	50                      AS_MOBILE_NODE
            n-38     696        100                     0            l              2  170	180    		            AS_MOBILE_NODE
            n-39     696        100                     0            l              2  10	50                      AS_MOBILE_NODE
            n-40     696        100                     0            l              2  170	180    		            AS_MOBILE_NODE
            n-41     696        100                     0            l              2  10	50                      AS_MOBILE_NODE
            n-42     696        100                     0            l              2  170	180    		            AS_MOBILE_NODE

            Edges: (42)
            #EdgeID     #NodeFrom   #NodeTo     #Not Used       #Not Used       #Bandwidth     #Not Used       #Not Used
            0           n-0         n-1         100000.0        0.000001          1000.0       2       0       E_AS    U
            1           n-0         n-2         100000.0        0.000001          1000.0       2       0       E_AS    U
            2           n-0         n-3         100000.0        0.000001          1000.0       2       0       E_AS    U
            3           n-0         n-4         100000.0        0.000001          1000.0       2       0       E_AS    U
            4           n-1         n-4         100000.0        0.000001        100000.0       2       0       E_AS    U
            5           n-1         n-8         100000.0        0.000001        100000.0       2       0       E_AS    U
            6           n-1         n-7         100000.0        0.000001        100000.0       2       0       E_AS    U
            7           n-1         n-6         100000.0        0.000001        100000.0       2       0       E_AS    U
            8           n-1         n-5         100000.0        0.000001        100000.0       2       0       E_AS    U
            9           n-2         n-5         100000.0        0.000001        100000.0       2       0       E_AS    U
            10          n-2         n-6         100000.0        0.000001        100000.0       2       0       E_AS    U
            11          n-2         n-7         100000.0        0.000001        100000.0       2       0       E_AS    U
            12          n-2         n-8         100000.0        0.000001        100000.0       2       0       E_AS    U
            13          n-2         n-3         100000.0        0.000001        100000.0       2       0       E_AS    U
            14          n-3         n-9         100000.0        0.000001        100000.0       2       0       E_AS    U
            15          n-3         n-10        100000.0        0.000001        100000.0       2       0       E_AS    U
            16          n-3         n-11        100000.0        0.000001        100000.0       2       0       E_AS    U
            17          n-3         n-12        100000.0        0.000001        100000.0       2       0       E_AS    U
            18          n-4         n-9         100000.0        0.000001        100000.0       2       0       E_AS    U
            19          n-4         n-10        100000.0        0.000001        100000.0       2       0       E_AS    U
            20          n-4         n-11        100000.0        0.000001        100000.0       2       0       E_AS    U
            21          n-4         n-12        100000.0        0.000001        100000.0       2       0       E_AS    U
            22          n-5         n-6         100000.0        0.000001        100000.0       2       0       E_AS    U
            23          n-5         n-13        100000.0        0.000001        100000.0       2       0       E_AS    U
            24          n-5         n-14        100000.0        0.000001        100000.0       2       0       E_AS    U
            25          n-6         n-15        100000.0        0.000001        100000.0       2       0       E_AS    U
            26          n-6         n-16        100000.0        0.000001        100000.0       2       0       E_AS    U
            27          n-7         n-8         100000.0        0.000001        100000.0       2       0       E_AS    U
            28          n-7         n-17        100000.0        0.000001        100000.0       2       0       E_AS    U
            29          n-7         n-18        100000.0        0.000001        100000.0       2       0       E_AS    U
            30          n-8         n-19        100000.0        0.000001        100000.0       2       0       E_AS    U
            31          n-8         n-20        100000.0        0.000001        100000.0       2       0       E_AS    U
            32          n-9         n-10        100000.0        0.000001        100000.0       2       0       E_AS    U
            33          n-9         n-21        100000.0        0.000001        100000.0       2       0       E_AS    U
            34          n-9         n-22        100000.0        0.000001        100000.0       2       0       E_AS    U
            35          n-10        n-23        100000.0        0.000001        100000.0       2       0       E_AS    U
            36          n-10        n-24        100000.0        0.000001        100000.0       2       0       E_AS    U
            37          n-11        n-12        100000.0        0.000001        100000.0       2       0       E_AS    U
            38          n-11        n-25        100000.0        0.000001        100000.0       2       0       E_AS    U
            39          n-11        n-26        100000.0        0.000001        100000.0       2       0       E_AS    U
            40          n-12        n-27        100000.0        0.000001        100000.0       2       0       E_AS    U
            41          n-12        n-28        100000.0        0.000001        100000.0       2       0       E_AS    U

    The first part regards the list of nodes. The nodes can be of 3 different type:

        - Router
        - Base Station
        - Mobile Station

    The parameters to specify are:

        - The node name
        - The Cache Probability
        - The Cache Size
        - The cache policy

    If the node is a base station the user has to specify 4 additional parameters:

        - The position of the base station with 2 coordinates (x, y)
        - The shape of the area covered by the base station
        - The size of the area covered by the base station

    The second part regards the links between the nodes. Of course the mobile stations do not have fixed links,
    while routers and base station does. The main parameters of a link are:

        - The link ID
        - The node from
        - The node to
        - The bandwidth

    Remember that links are bidirectional!

    - routing.dist, that contains the routing table entries of the node described in the previous file. The format of \
    this file is the following::

            #Node From      #Node To    #Route List
            n-13            n-5         A = "/ndn" ;
            n-14            n-5         A = "/ndn" ;

            n-15            n-6         A = "/ndn" ;
            n-16            n-6         A = "/ndn" ;

            n-17            n-7         A = "/ndn" ;
            n-18            n-7         A = "/ndn" ;

            n-19            n-8         A = "/ndn" ;
            n-20            n-8         A = "/ndn" ;

            n-21            n-9         A = "/ndn" ;
            n-22            n-9         A = "/ndn" ;

            n-23            n-10        A = "/ndn" ;
            n-24            n-10        A = "/ndn" ;

            n-25            n-11        A = "/ndn" ;
            n-26            n-11        A = "/ndn" ;

            n-27            n-12        A = "/ndn" ;
            n-28            n-12        A = "/ndn" ;

            n-5             n-1         A = "/ndn/n1" B = "/ndn/n4" ;
            n-5             n-2         A = "/ndn/n2" B = "/ndn/n3" ;

            n-6             n-1         A = "/ndn/n1" B = "/ndn/n4" ;
            n-6             n-2         A = "/ndn/n2" B = "/ndn/n3" ;

            n-7             n-1         A = "/ndn/n1" B = "/ndn/n4" ;
            n-7             n-2         A = "/ndn/n2" B = "/ndn/n3" ;

            n-8             n-1         A = "/ndn/n1" B = "/ndn/n4" ;
            n-8             n-2         A = "/ndn/n2" B = "/ndn/n3" ;

            n-9             n-3         A = "/ndn/n3" B = "/ndn/n2" ;
            n-9             n-4         A = "/ndn/n4" B = "/ndn/n1" ;

            n-10            n-3         A = "/ndn/n3" B = "/ndn/n2" ;
            n-10            n-4         A = "/ndn/n4" B = "/ndn/n1" ;

            n-11            n-3         A = "/ndn/n3" B = "/ndn/n2" ;
            n-11            n-4         A = "/ndn/n4" B = "/ndn/n1" ;

            n-12            n-3         A = "/ndn/n3" B = "/ndn/n2" ;
            n-12            n-4         A = "/ndn/n4" B = "/ndn/n1" ;

            n-1             n-4         A = "/ndn/n4" ;
            n-4             n-1         A = "/ndn/n1" ;
            n-2             n-3         A = "/ndn/n3" ;
            n-3             n-2         A = "/ndn/n2" ;

            n-0             n-1         A = "/ndn/n1" ;
            n-0             n-2         A = "/ndn/n2" ;
            n-0             n-3         A = "/ndn/n3" ;
            n-0             n-4         A = "/ndn/n4" ;


    Basically it contains a list of entries with:

        - The node from
        - The node to
        - The list of NDN routes from "node from" to "node to"


    - workload.conf, that contains a list of clients and repo running on the nodes defined in topo.brite. An example of this configuration file is the following::

        Clients:
        #Node   #ClientID   #Arrival    #Popularity     #Name
        n-29    client-29-0 Poisson_2   rzipf_1.3_100   /ndn/n1
        n-29    client-29-1 Poisson_2   rzipf_1.3_100   /ndn/n4

        n-30    client-30-0 Poisson_2   rzipf_1.3_100   /ndn/n2
        n-30    client-30-1 Poisson_2   rzipf_1.3_100   /ndn/n1

        n-31    client-31-0 Poisson_2   rzipf_1.3_100   /ndn/n3
        n-31    client-31-1 Poisson_2   rzipf_1.3_100   /ndn/n4

        n-32    client-32-0 Poisson_2   rzipf_1.3_100   /ndn/n2
        n-32    client-32-1 Poisson_2   rzipf_1.3_100   /ndn/n4

        n-33    client-33-0 Poisson_2   rzipf_1.3_100   /ndn/n1
        n-33    client-33-1 Poisson_2   rzipf_1.3_100   /ndn/n3

        n-34    client-34-0 Poisson_2   rzipf_1.3_100   /ndn/n3
        n-34    client-34-1 Poisson_2   rzipf_1.3_100   /ndn/n2

        n-35    client-35-0 Poisson_2   rzipf_1.3_100   /ndn/n3
        n-35    client-35-1 Poisson_2   rzipf_1.3_100   /ndn/n1

        n-36    client-36-0 Poisson_2   rzipf_1.3_100   /ndn/n2
        n-36    client-36-1 Poisson_2   rzipf_1.3_100   /ndn/n3

        n-37    client-37-0 Poisson_2   rzipf_1.3_100   /ndn/n1
        n-37    client-37-1 Poisson_2   rzipf_1.3_100   /ndn/n4

        n-38    client-38-0 Poisson_2   rzipf_1.3_100   /ndn/n1
        n-38    client-38-1 Poisson_2   rzipf_1.3_100   /ndn/n2

        n-39    client-39-0 Poisson_2   rzipf_1.3_100   /ndn/n2
        n-39    client-39-1 Poisson_2   rzipf_1.3_100   /ndn/n4

        n-40    client-40-0 Poisson_2   rzipf_1.3_100   /ndn/n4
        n-40    client-40-1 Poisson_2   rzipf_1.3_100   /ndn/n1

        n-41    client-41-0 Poisson_2   rzipf_1.3_100   /ndn/n1
        n-41    client-41-1 Poisson_2   rzipf_1.3_100   /ndn/n3

        n-42    client-42-0 Poisson_2   rzipf_1.3_100   /ndn/n3
        n-42    client-42-1 Poisson_2   rzipf_1.3_100   /ndn/n1

        Repos:
        #Node   #RepoID     #Name
        n-1     repo-0      /ndn/n1
        n-2     repo-1      /ndn/n2
        n-3     repo-2      /ndn/n3
        n-4     repo-3      /ndn/n4

    The clients have the following parameter list:

        - Node: The node on which the client is running
        - ClientID: The identifier of the client
        - Arrival: The distribution of download requests
        - Popularity: The popularity of the content
        - Name: the name asked by the client (consumer)

    The repos have the following parameter list:

        - Node: The node on which the repo is running
        - RepoID: The ID of the repository
        - Name: the name served by the repo

    - mobility.model, that contains the mobility parameters of the mobile stations. A mobility.model file looks like::

        # This configuration file is used to rapidly set the mobility model of the experiment.
        # For now, the following models are supported:
        # 1) Random Walk
        # 2) Random Waypoint


        # Parameters: Duration (seconds), StartingPoint (Coordinates(km)), speed (m/s)
        n-29 random_waypoint    600     7.5     7.5       5
        n-30 random_waypoint    600     75      75        5
        n-31 random_waypoint    600     90.5    90.5      5
        n-32 random_waypoint    600     10.3    11.8      5
        n-33 random_waypoint    600     11.2    80.1      5
        n-34 random_waypoint    600     0.4     15.9      5
        n-35 random_waypoint    600     50.2    90.4      5
        n-36 random_waypoint    600     70.2    20.3      5
        n-37 random_waypoint    600     120.2   121.4     5
        n-38 random_waypoint    600     150.3   20.1      5
        n-39 random_waypoint    600     170.34  190.2     5
        n-40 random_waypoint    600     11.3    175.2     5
        n-41 random_waypoint    600     120.56  7.5       5
        n-42 random_waypoint    600     75      75        5
        # ^	     ^          ^        ^      ^         ^
        # Node_id    model      Duration x      y         Speed

        # Note that the speed is used just for the random waypoint mobility model.

    The mobility parameters specified in this file are:

        - **Node**: the mobile node. It has to be a mobile station in topo.brite
        - **Mobility Model**: The mobility model. It can be random waypoint or random walk.
        - **Duration**: The duration of the mobility
        - **x**: The x position of the mobile station at time 0
        - **y**: the y position of the mobile station at time 0
        - **Speed**: Used only in random waypoint, it is the speed of the station when it moves from a point to another.

    - settings.conf, that contains the general configuration needed to setup the experiment. An example of this file is \
    the following::

        [Settings]

        test_folder = ~/tests
        username = nfduser
        remote_log_dir = /root/log/
        ndn_dir = /usr/local/bin
        cache_dir = cache/
        scripts_dir = /tmp/scripts/
        log_dir = ../log/
        type_of_repo = virtual
        test_start_time = 0.0
        test_duration = 120
        file_size = 100
        chunk_size = 1024
        transport_prot = udp
        file_size_distribution = constant
        file_size_parameter1 = 0
        file_size_parameter2 = 0
        flow_control_gamma = 1
        flow_control_beta = 0.9
        flow_control_p_min = 0.00001
        flow_control_p_max = 0.01
        flow_control_est_len = 30
        PIT_lifetime = 950
        flow_control_timeout = 1000
        fwd_alhpa_avg_pi = 0.9
        nfd_stats_interval = 60000000
        nfd_lb_forwarding_debug_mode = 1

        mobility_area_w = 200
        mobility_area_h = 200

        # Random Waypoint (for NS-3) Parameters
        mobility_model = random_waypoint
        min_pause = 3
        max_pause = 5

        # NS-3 script Location (For Mobility)
        home_folder = /home/shahab
        ndnmobility = NDNMobility
        ns3_folder = ns-allinone-3.24.1/ns-3.24.1
        ns3_conf_file_name = topo.conf
        ns3_script = lxc-tap-wifi-emulation

"""

import logging
import os
import shutil
from configparser import ConfigParser

#from pyvoro import compute_2d_voronoi
from random import randint

from sympy import Point
from Crackle.ColoredOutput import make_colored
from Crackle.LxcUtils import RouterContainer, BaseStationContainer, StationContainer, AddressGenerator
import Crackle.TopologyStructs as TopologyStructs
import Crackle.Globals as Globals
import Crackle.Constants as Constants

__mobility_models__ = ["constant_position", "random_waypoint"]
__topology_configuration__ = "topo.brite"
__routing_configuration__ = "routing.dist"
__workload_configuration__ = "workload.conf"
__mobility_configuration__ = "mobility.model"
__settings__ = "settings.conf"

__icn_strategies__ = ["best-route", "multicast", "load-balance", "broadcast", "ncc"]

module_logger = logging.getLogger(__name__)


class ConfigReader:
    """
    This class is in charge of reading the configuration files and setup a list of nodes with the configuration provided
    by the user. In more details, it parses the following configuration files:

        - The file topo.brite, containing the topology description
cc        - The file routing.dist, containing the routing tables of the nodes specified in topo.brite
        - The file workload.conf, containing the list of repositories and consumers
        - The file mobility.model, containing the mobility settings for the mobile stations
        - The file settings.conf, containing the general settings of the experiment

    :ivar node_list: The list of routers, base stations and mobile stations

    """

    def __init__(self):
        self.node_list = {}
        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)

        self.test_path = None

    def setup_conf(self, test_path):
        """
        Main method of this class. It reads the test_path folder and parses the configuration files inside it.

        :param test_path: The path of the test folder containing the configuration
        :return: the node_list configured with the user config inputs
        """
        # Path test folder

        if not os.path.exists(test_path):
            self.logger.error("Test folder does not exist.")
            print(make_colored("red", "[Error]: The test folder does not exist."))
            return None

        self.test_path = test_path

        self.logger.info("Creating crackle.config using the \"{0}\" folder ...".format(test_path))

        # parsing the setting

        settings_file = test_path + "/" + __settings__

        if not os.path.isfile(settings_file):
            self.logger.error("The configuration file {0} does not exist!".format(settings_file))
            return None

        try:
            self.logger.debug("Starting to parse the settings file {0}.".format(settings_file))
            self.parse_settings(settings_file)
        except SyntaxError:
            print(make_colored("red", "[SyntaxError]: Error reading the {0} file".format(settings_file)))
            self.logger.error("Error reading the {0} file".format(settings_file))
            return None

            # parsing the topology

        topo_file = test_path + "/" + __topology_configuration__

        try:
            self.logger.debug("Opening topology file {0}".format(topo_file))
            raw_topo = open(topo_file, 'r')
        except IOError:
            print(make_colored("red", "[IOError]: {0} file does not exist.".format(topo_file)))
            self.logger.error("The {0} file does not exist".format(settings_file))
            return None

        try:
            self.logger.debug("Parsing topology file {0}".format(topo_file))
            self.parse_topology(raw_topo)
        except SyntaxError:
            self.logger.error("Error reading the {0} file".format(topo_file))
            print(make_colored("red",
                               "[SyntaxError]: syntax error or malformed links in {0}/topo.brite".format(test_path)))
            return None

        # parsing the workload

        workload_file = test_path + "/workload.conf"
        try:
            self.logger.debug("Opening workload file {0}".format(workload_file))
            workload = open(workload_file, 'r')
        except IOError:
            self.logger.error("The {0} file does not exist".format(workload_file))
            print(make_colored("red", "[IOError]:: {0} file does not exists".format(workload_file)))
            return None

        try:
            self.logger.debug("Parsing workload file {0}".format(workload_file))
            self.parse_workload(workload)
        except SyntaxError:
            self.logger.error("Error reading the {0} file".format(workload_file))
            print(make_colored("red",
                               "[SyntaxError]: inconsistency between clients in {0} and {1} in {2}".format(
                                       __workload_configuration__,
                                       __topology_configuration__,
                                       test_path)))
            return None

        # parsing the routing
        routing_file = test_path + "/" + __routing_configuration__
        try:
            self.logger.debug("Opening routing file {0}".format(routing_file))
        #            routes = open(routing_file, 'r')    ------>   Temporary
        except IOError:
            self.logger.error("The {0} file does not exist".format(routing_file))
            print(make_colored("red", "[IOError]: {0} file does not exists".format(routing_file)))
            return None

        try:
            self.logger.debug("Parsing routing file {0}".format(routing_file))
#            self.parse_routing(Globals.routing_algorithm)
        except SyntaxError:
            self.logger.error("Error reading the {0} file".format(routing_file))
            print(make_colored("red",
                               "[SyntaxError]: inconsistency between clients in {0} and {1} in {2}".format(
                                       __topology_configuration__,
                                       __routing_configuration__,
                                       test_path)))
            return None

        # Parsing the mobility
        mobility_file = test_path + "/" + __mobility_configuration__
        try:
            self.logger.debug("Opening mobility file {0}".format(mobility_file))
            mobility = open(mobility_file, 'r')
        except IOError:
            self.logger.error("The {0} file does not exist".format(mobility_file))
            print(make_colored("red", "[IOError]: {0} file does not exists".format(mobility_file)))
            return None

        try:
            self.logger.debug("Parsing mobility file {0}".format(mobility_file))
            self.parse_mobility(mobility)
        except SyntaxError:
            self.logger.error("Error reading the {0} file".format(mobility_file))
            print(make_colored("red",
                               "[SyntaxError]: inconsistency between clients in {0} and {1} in {2}".format(
                                       __mobility_configuration__,
                                       __topology_configuration__,
                                       test_path)))
            return None

        # self.logger.info("Writing mapping node - IP address in /etc/hosts")
        #
        # self.write_hosts_file()

        return self.node_list

    def parse_topology(self, raw_topo):
        """
        This function is in charge of parsing the topo.brite file. It creates the list of nodes and a linux
        container for each node in the topology. The objects of the list are instances of
        :class:`Crackle.TopologyStructs.Node`.

        :param raw_topo: The file topo.brite, with the description of the topology.
        :return:  1 if parsing succeed, otherwise it raises a SyntaxError
        :raises: :class:`SyntaxError` if an error is found.
        """
        index = 0
        bs_list = []

        self.logger.debug("Reading nodes from topo.brite")

        line = raw_topo.readline()
        while line and not line.strip().startswith("Nodes:"):
            # Read the nodes from the topology file until the "Nodes:" tag is found'
            line = raw_topo.readline()

        line = raw_topo.readline()
        while line and not line.strip().startswith("Edges:"):
            if not (line.strip().startswith("#") or line.strip() == ''):
                sline = line.split()

                if len(sline) < 4:
                    raise SyntaxError

                node_type = sline[len(sline) - 1]
                node_id = Globals.experiment_id + sline[0]
                cache_size = sline[3]
                cache_policy = sline[4]
                cache_probability = sline[2]
                forward_strategy = sline[5]

                if int(cache_size) < 0:
                    self.logger.error("[{0}] Wrong value fr cache size.".format(node_id))
                    raise SyntaxError

                if forward_strategy not in __icn_strategies__:
                    self.logger.error("[{0}] Wrong value fr forward strategy.".format(node_id))
                    raise SyntaxError

                if node_type == "AS_NODE":

                    self.logger.debug("Node_Id={0} Node_Type={1} cache_size={2}".format(node_id,
                                                                                        node_type,
                                                                                        cache_size))

                    container = RouterContainer(node_id)

                    self.node_list[node_id] = TopologyStructs.Router(node_id,
                                                                     cache_size,
                                                                     cache_policy,
                                                                     cache_probability,
                                                                     forward_strategy,
                                                                     container=container,
                                                                     vlan=Constants.router_vlan)

                elif node_type == "AS_BASE_STATION":

                    x = sline[6]
                    y = sline[7]
                    self.logger.debug("Node_Id={0} Node_Type={1} cache_size={2}"
                                      "position=({3}, {4})".format(node_id,
                                                                   node_type,
                                                                   cache_size,
                                                                   x,
                                                                   y))

                    self.logger.debug("[{0}] Creating container".format(node_id))
                    container = BaseStationContainer(node_id)

                    self.node_list[node_id] = TopologyStructs.BaseStation(node_id,
                                                                          cache_size,
                                                                          cache_policy,
                                                                          cache_probability,
                                                                          forward_strategy,
                                                                          x,
                                                                          y,
                                                                          container=container,
                                                                          vlan=Constants.router_vlan,
                                                                          bs_vlan=Constants.base_station_vlan)

                    bs_list.append(self.node_list[node_id])

                elif node_type == "AS_MOBILE_NODE":
                    # Here we are setting just the parameters linked to the router.
                    # In the mobility section we'll set the mobility parameters.

                    start_x = sline[6]
                    start_y = sline[7]
                    self.logger.debug("[{0}] Node_Id={0} Node_Type={1} cache_size={2}".format(node_id,
                                                                                              node_type,
                                                                                              cache_size))

                    self.logger.debug("[{0}] Creating container".format(node_id))

                    container = StationContainer(node_id)

                    self.node_list[node_id] = TopologyStructs.Station(node_id,
                                                                      cache_size,
                                                                      cache_policy,
                                                                      cache_probability,
                                                                      forward_strategy,
                                                                      container=container,
                                                                      mobile=True)
                    self.node_list[node_id].set_starting_point(start_x, start_y)

                else:
                    raise SyntaxError

            line = raw_topo.readline()

        # Read the edges from the topology file until the end of the file
        line = raw_topo.readline()

        self.logger.debug("Node list: {0}".format(self.node_list))

        self.logger.debug("Reading links from topo.brite.")

        while line.strip() != "":
            if not (line.strip().startswith("#") or line.strip() == ''):
                sline = line.split()
                link_id = sline[0]
                node_from = Globals.experiment_id + sline[1]
                node_to = Globals.experiment_id + sline[2]
                cost = sline[4]
                bandwidth = sline[5]

                self.logger.debug("[{0}] node_from={1} node_to={2} bandwidth={3}".format(link_id,
                                                                                         node_from,
                                                                                         node_to,
                                                                                         bandwidth))

                if all(node in self.node_list.keys() for node in [node_from, node_to]):
                    self.node_list[node_from].add_link(TopologyStructs.WiredLink(self.node_list[node_from],
                                                                            self.node_list[node_to],
                                                                            node_to,
                                                                            True,
                                                                            float(bandwidth) / 1000))

                    # add also the to from link because for the moment links are bidirectional in topo.brite
                    self.node_list[node_to].add_link(TopologyStructs.WiredLink(self.node_list[node_to],
                                                                          self.node_list[node_from],
                                                                          node_from,
                                                                          True,
                                                                          float(bandwidth) / 1000))
                else:
                    self.logger.error("Endpoints of the link not in the list of nodes.")
                    raise SyntaxError

            line = raw_topo.readline()

        raw_topo.close()

        # Compute BS neighbors

        self.logger.debug("Calculating Voronoi Diagram and omputing neighbors of each base station")

        bs_list = {}

        for n in self.node_list.values():
            if type(n) is TopologyStructs.BaseStation:
                bs_list[(n.get_x(), n.get_y())] = n

        cells = compute_2d_voronoi(list(bs_list.keys()), [(Globals.mobility_area_x_0,
                                                           Globals.mobility_area_x_max),
                                                          (Globals.mobility_area_y_0,
                                                           Globals.mobility_area_y_max)], 2.0)

        for cell in cells:
            print("Creating shape with vertices: {}".format(cell["vertices"]))
            bs_list[cell["original"]].create_shape(cell["vertices"])

        return 1

    # def parse_routing(self, Algo_Name):
    #     """
    #     Parse the routing file. This function configures the nodes created in the method
    #     :func:`Crackle.ConfigReader.ConfigReader.parse_topology` by adding some NDN route entries. Each route is an instance
    #     of the class :class:`Crackle.TopologyStructs.Route`.
    #
    #     :return:  1 if parsing succeed, otherwise it raises a SyntaxError
    #     :raises: :class:`SyntaxError` if an error is found
    #     """
    #     # routing line: from to A = "component1" B = "component2" .... ;
    #
    #     # Creating Graph from networkx
    #     G = nx.Graph()
    #     G.add_nodes_from(list(self.node_list.keys()))
    #
    #     consumer = []
    #     dict_repo = {}
    #     dict_client = {}
    #
    #     # Wired Part of Network
    #     if not i.mobile:
    #         # Create Graph
    #         for j in i.links.values():
    #             G.add_edge(i.get_node_id(), j.node_to.get_node_id(), bandwidth=1 / j.bandwidth, cost=j.cost)
    #             G.add_edge(i.get_node_id(), j.node_to.get_node_id(), bandwidth=j.bandwidth, cost=1/j.bandwidth)
    #
    #         # Repository and Client Dictionary
    #         repositories = i.get_repositories()
    #
    #         if repositories:
    #             dict_repo[i.get_node_id()] = []
    #             for repo in repositories:
    #                 content = repo.get_folder()
    #                 dict_repo[i.get_node_id()].append(content)
    #
    #         clients = i.get_client_apps()
    #
    #         if clients:
    #             dict_client[i.get_node_id()] = []
    #             for client in clients:
    #                 content = client.get_name()
    #                 dict_client[i.get_node_id()].append(content)
    #
 	# # Algorithm of routing Table
    #
    #     [NodeFrom,NodeTo,Name] = Routing.routing_table(G, dict_repo, dict_client, Algo_Name)
    #
    #     [NodeFrom, NodeTo, Name] = routing_table(G, dict_repo, dict_client, Algo_Name)
    #
    #     print(NodeFrom)
    #     print(NodeTo)
    #     print(Name)
    #
    #     # Add route Node list
    #     for i in range(0, len(NodeFrom)):
    #         if all(node in self.node_list.keys() for node in [NodeFrom[i], NodeTo[i]]):
    #             self.logger.debug(
    #                 "Registering route: node_from={0} node_to={1} name={2}".format(NodeFrom[i], NodeTo[i], Name[i]))
    #
    #             self.node_list[NodeFrom[i]].add_route(self.node_list[NodeTo[i]], Name[i])
    #
    #         else:
    #             self.logger.error(
    #                 "Syntax error in the route description. node_from={0} node_to={1}".format(NodeFrom[i], NodeTo[i]))
    #
    #             raise SyntaxError
    #
    #     return 1

    def parse_workload(self, workload):
        """
        This method parses the workload configuration file, that contains a description of the repositories and the
        clients running on the nodes. Each node is then updated with the list of the clients/repos running on it.

        :param workload: The file containing the workload description
        :return:  1 if parsing succeed, otherwise it raises a SyntaxError
        :raises: :class:`SyntaxError` if an error is found
        """
        line = workload.readline()

        self.logger.debug("Reading clients from workload.conf")

        while line and not line.strip().startswith("Clients:"):
            line = workload.readline()

        line = workload.readline()
        while line and not line.startswith("Repos:"):
            if not (line.strip().startswith("#") or line.strip() == ''):
                sline = line.split()
                node_id = Globals.experiment_id + sline[0]
                client_id = sline[1]
                arrival = sline[2]
                popularity = sline[3]
                name = sline[4]

                self.logger.debug("[{0}] node_id={1} arrival={2} popularity={3} name={4}".format(client_id,
                                                                                                    node_id,
                                                                                                    arrival,
                                                                                                    popularity,
                                                                                                    name))

                if node_id in self.node_list.keys():
                    client = TopologyStructs.Client(client_id,
                                                    arrival,
                                                    popularity,
                                                    name)
                    self.node_list[node_id].add_client(client)
                    if len(sline) >= 7:
                        client.set_start_time(sline[5])
                        client.set_duration(sline[6])
                else:
                    self.logger.error("[{0}] This node is not in the nodes in the file topo.brite".format(node_id))
                    raise SyntaxError

            line = workload.readline()

        line = workload.readline()

        self.logger.debug("Reading repositories from workload.conf")

        while line.strip() != "":
            if not (line.strip().startswith("#") or line.strip() == ''):
                sline = line.split()
                node_id = Globals.experiment_id + sline[0]
                repo_id = sline[1]
                catalog = sline[2]

                self.logger.debug("[{0}] node_id={1} catalog={2}".format(repo_id,
                                                                         node_id,
                                                                         catalog))

                if node_id in self.node_list.keys():
                    self.node_list[node_id].add_repo(TopologyStructs.Repo(repo_id, catalog))
                else:
                    self.logger.error("[{0}] This node is not in the nodes in the file topo.brite".format(node_id))
                    raise SyntaxError

            line = workload.readline()

        workload.close()
        return 1

    def parse_mobility(self, mobility_file):
        """
        This function is in charge of parsing the mobility.model configuration file. It sets the mobility parameters on
        the mobile station.

        :param mobility_file: The "mobility.model" configuration file
        :return: 1 if parsing succeed, otherwise it raises a SyntaxError
        :raises: :class:`SyntaxError` if an error is found
        """
        for line in mobility_file:
            if not (line.strip().startswith("#") or line.strip() == ''):

                fields = line.split()
                try:
                    node_id = Globals.experiment_id + fields[0]
                    model = fields[1]
                    speed = float(fields[2])
                except IndexError:
                    self.logger.error("Index error reading mobility.model. Some parameters are missing.")
                    raise SyntaxError
                except ValueError:
                    self.logger.error("Value error reading mobility.model.")
                    raise SyntaxError

                self.logger.debug("[{0}] model={1}".format(node_id,
                                                           model))

                try:
                    mobility_area_x_0 = float(fields[3])
                    mobility_area_x_max = float(fields[4])
                    mobility_area_y_0 = float(fields[5])
                    mobility_area_y_max = float(fields[6])
                except:
                    mobility_area_x_0 = Globals.mobility_area_x_0
                    mobility_area_x_max = Globals.mobility_area_x_max
                    mobility_area_y_0 = Globals.mobility_area_y_0
                    mobility_area_y_max = Globals.mobility_area_y_max

                if speed < 0:
                    print(make_colored("red", "[{0}]: Speed < 0.".format(node_id)))
                    self.logger.error("[{0}]: Speed < 0.".format(node_id))
                    raise SyntaxError

                if model not in __mobility_models__:  # The model does not exist
                    print(make_colored("red", "[{0}]: The model specified does not exist!".format(node_id)))
                    self.logger.error("[{0}]: The model specified does not exist!".format(node_id))
                    raise SyntaxError

                if node_id in self.node_list.keys() and \
                        self.node_list[node_id].is_mobile() and \
                                type(self.node_list[node_id]) == TopologyStructs.Station:  # Sanity checks

                    self.node_list[node_id].set_mobility_model(model)
                    self.node_list[node_id].set_speed(speed)
                    self.node_list[node_id].set_boundaries(mobility_area_x_0,
                                                           mobility_area_x_max,
                                                           mobility_area_y_0,
                                                           mobility_area_y_max)

                    if float(self.node_list[node_id].get_starting_point().x) < mobility_area_x_0 or \
                                    float(self.node_list[node_id].get_starting_point().x) > mobility_area_x_max or \
                                    float(self.node_list[node_id].get_starting_point().y) < mobility_area_y_0 or \
                                    float(self.node_list[node_id].get_starting_point().y) > mobility_area_y_max:
                        print(make_colored("red", "[{0}]: Starting point out of the mobility area!".format(node_id)))
                        self.logger.error("[{0}] Starting point outside mobility area.".format(node_id))
                        raise SyntaxError
                else:
                    self.logger.error("[{0}]: The node is not in the nodes in topo.brite or the node is not declared "
                                      "as mobile station. "
                                      "node_list={1}, is_mobile={2}, type={3}".format(node_id,
                                                                                      self.node_list.keys(),
                                                                                      self.node_list[
                                                                                          node_id].is_mobile(),
                                                                                      type(self.node_list[node_id])))
                    raise SyntaxError

    def parse_settings(self, settings):
        """
        This function parses the settings.conf file and fills the :mod:`Crackle.Globals` file with them.

        :param settings: The settings.conf file.
        :return:  1 if parsing succeed, otherwise it raises a SyntaxError
        """

        def is_number(s):
            try:
                float(s)
                return True
            except ValueError:
                return False

        config = ConfigParser()
        config.read(settings)
        settings = config.options("Settings")
        for opt in settings:
            value = config.get("Settings", opt)
            if opt == "experiment_id":
                value = str(value)
                value += str(randint(0, 1000))
            self.logger.debug("Settings file: option={0} value={1}".format(opt, value))
            setattr(Globals, opt, value) if opt == "lxd_port" else setattr(Globals, opt,
                                                                           value if not is_number(value) else float(
                                                                               value))

        Constants.LXD_BRIDGE += Globals.experiment_id

        return 1

    def write_hosts_file(self):
        shutil.copy("/etc/hosts", "/etc/hosts.save")

        etc_hosts = open("/etc/hosts", "a")

        for node in self.node_list.values():
            self.logger.debug("Writing pair {0}\t{1} on /etc/hosts".format(node.get_ip_address(), node))
            etc_hosts.write("{0}\t{1}\n".format(node.get_ip_address(), node))
