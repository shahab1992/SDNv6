import copy
import logging
import socket
import subprocess
import threading
import time
from random import uniform, randint
import json

from decorator import decorator
from sympy import Point, Segment

from threading import Lock
import Crackle.ConfigReader
import Crackle.Globals as Globals
import Crackle.Constants as Constants
from Crackle import TopologyStructs
from Crackle.ColoredOutput import make_colored
from Crackle.AsyncManager import Async, start_thread_pool
from Crackle.ConfigReader import __mobility_models__

"""
Module that is in charge of emulate the mobility of the entities in the network.
The module support map-me mobility protocol, and is able to handle n different entities with n different mobility
models. Each entity is independent and is controlled by a different thread, so if we have n mobile entities, we'll se
all the n entities moving at the same time.
"""

# TODO Take mobility paramenters cell size and max/min speed from the nodes instead from the conf file settings.conf.

async = decorator(Async())

# BaseStation-MobileEntity-Tap
__bs_tap_template__ = "{0}t"
__tap_template__ = "{0}{1}t"

# NS3 script name + parameters
__param_bs_tap__ = "--bs-tap={0}"
__param_n_sta__ = "--n-sta={0}"
__param_sta_taps__ = "--sta-taps={0}"
__param_sta_macs__ = "--sta-macs={0}"
__param_bs_x__ = "--bs-x={0}"
__param_bs_y__ = "--bs-y={0}"
__param_bs_name__ = "--bs-name={0}"
__param_cell_size__ = "--cell-size={0}"
__param_bs_mac__ = "--bs-mac={0}"
__param_control_port__ = "--control-port={0}"
__param_sta_list__ = "--sta-list={0}"
__param_experiment_id__ = "--experiment-id={0}"

# This prefix is used in order to aggregate all the requests of the mobile station toward a common nexthop.
__sta_prefix__ = "/n"

# Constants used to describe the movement
__mobility_model__ = "mobility_model"
__base_station__ = "base_station"
__station__ = "station"
__start_x__ = "start_x"
__start_y__ = "start_y"
__end_x__ = "end_x"
__end_y__ = "end_y"
__duration__ = "duration"
__experiment_id__ = "experiment_id"


def grouped(iterable, n):
    """
    Function that returns n elements each time
    :param iterable: The list of objects
    :param n: How many object return each time
    :return: n Objects from the iterable
    """
    return zip(*[iter(iterable)] * n)


def check_port(address, port):
    # Create a TCP socket
    s = socket.socket()
    try:
        s.connect((address, port))
        return True
    except socket.error as e:
        return False


class MobilityManager:
    """
    This class handle the Mobility Configuration and launch the correct
    function in order to emulate the wanted Mobility Model.
    """

    def __init__(self, node_list, server_list, ndn):

        self.nodes_list = node_list
        self.base_station_list = []
        self.mobile_station_list = []
        self.server_list = server_list
        self.kill_ns3 = False
        self.ndn = ndn

        port = 7000

        # One simulation per base station, so BaseStation => PortNumber map
        self.simulation_control_port_map = {}

        self.mobility_threads = []

        self.tap_list = []
        self.ns3_pid_list = {}

        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)
        self.logger.debug("Instantiating MobilityManager.")

        for node in self.nodes_list.values():
            if type(node) == TopologyStructs.BaseStation:
                self.base_station_list.append(node)
            elif type(node) == TopologyStructs.Station:
                self.mobile_station_list.append(node)

        # Setup a VLAN for each mobile station

        self.cv = threading.Condition()
        self.repo_command = "ndn-virtual-repo"  # Hardcoded! (for now)
        self.consumer_application = "ndn-icp-download"

        self.thread_output = False
        self.killall = False

        self.mutex = Lock()

    def kill_threads(self):
        self.killall = True

        for t in self.mobility_threads:
            t.join()

        return True

    def thread_print(self, string):
        """
        This function prints a string (if the user has set the mobility manager in order to print the string through
        the function show_mobility_status

        :param string: The string to print
        """

        if self.thread_output:
            print(string)

        self.logger.info(string)

    def set_output(self):
        """This function sets a flag that enable the output of the threads"""

        self.logger.debug("Set output of mobility threads.")
        self.thread_output = True

    def unset_output(self):
        """This function unsets a flag that enable the output of the threads"""

        self.logger.debug("Unset output of mobility threads.")
        self.thread_output = False

    def setup_mobility(self):
        """
        Setup the mobility, by creating the TAP devices required by NS3 and starting the NS3 processes themselves.


        :param notification: Boolean that indicates if sending or not the Interest Notification
        """

        self.logger.info("Setting up mobility")
        self.killall = False

        if self.create_tap_devices():
            self.logger.info("NS3 simulations started!")
            return True
        else:
            self.logger.error("Error creating tap devices and starting NS3 simulations")
            return False

    @async
    def start_mobility(self):
        """
        Start the mobility of the mobile nodes. Asynchronous function, because it waits wor the completion of all
        the threads.
        It spawns as many threads as the number of mobile stations. Each thread controls
        the movement of one mobile station.

        :return:
        """
        self.killall = False
        self.start_mobility_threads()

    def create_tap_devices(self):
        """
        Create the taps devices for connecting the NS3 proces to the other containers and start the NS3 process.

        :return: True if the Tap creation successes, False otherwise
        """

        def setup_mobility(bs, results):
        
            try:
                # Sanity check: in Linux an interface cannot have a length > 15 bytes
                bs_tap = __bs_tap_template__.format(bs)[:14]

                self.logger.debug("[{0}] Creating tap {1}".format(bs, bs_tap))

                if not bs.set_bs_tap(bs_tap):
                    self.logger.error("[{0}] Error creating tap device {1} for mobility.".format(bs,
                                                                                                 bs_tap))
                    print(make_colored("red", "[{0}] Error creating tap device {1}".format(bs,
                                                                                           bs_tap)))
                    results[bs] = False
                    return
                    
                self.tap_list.append([bs_tap, bs.get_server()])

                param_sta_list = ""
                param_sta_taps = ""
                param_sta_macs = ""

                time.sleep(uniform(0, 4))

                self.mobile_station_list.sort(key=lambda x: x.node_id, reverse=True)

                for station in enumerate(self.mobile_station_list, start=1):
                    tap_name = __tap_template__.format(bs, station[1])[:14]

                    self.logger.debug("[{0}] Creating tap {1}".format(station, tap_name))

                    if not bs.add_sta_tap(tap_name, station[1].get_vlan(bs)):
                        self.logger.error("[{0}] Error creating tap device {1} for mobility.".format(bs,
                                                                                                     tap_name))
                        print(make_colored("red", "[{0}] Error creating tap device {1}".format(bs,
                                                                                               tap_name)))
                        results[bs] = False
                        return
                       
                    self.tap_list.append([tap_name, bs.get_server()])

                    param_sta_list += station[1].get_node_id() + ","
                    param_sta_taps += tap_name + ","
                    param_sta_macs += station[1].get_mac_address(bs) + ","

                # Remove final comma
                param_sta_list = param_sta_list[:-1]
                param_sta_taps = param_sta_taps[:-1]
                param_sta_macs = param_sta_macs[:-1]

                # Assign a port to the simulation
                port = randint(10000, 50000)
                while check_port(bs.get_server().get_hostname(), port):
                    port = randint(10000, 50000)

                self.simulation_control_port_map[bs] = port

                while True:
                    params = ["ssh",
                              "-i",
                              Constants.ssh_client_private_key,
                              "{0}@{1}".format(Globals.username, bs.get_server()),
                              "sudo nohup {ns3_script} "
                              "{sta_list} {bs_tap} {n_sta} {sta_taps} "
                              "{sta_macs} {bs_x} {bs_y} "
                              "{bs_name} {bs_mac} {experiment_id} {control_port} "
                              "2>> /tmp/{base_station}.log &".format(
                                      home_folder=Globals.home_folder,
                                      ns3_folder=Globals.ns3_folder,
                                      ns3_script=Globals.ns3_script,
                                      sta_list=__param_sta_list__.format(param_sta_list),
                                      bs_tap=__param_bs_tap__.format(bs_tap),
                                      n_sta=__param_n_sta__.format(len(self.mobile_station_list)),
                                      sta_taps=__param_sta_taps__.format(param_sta_taps),
                                      sta_macs=__param_sta_macs__.format(param_sta_macs),
                                      bs_x=__param_bs_x__.format(bs.get_x()),
                                      bs_y=__param_bs_y__.format(bs.get_y()),
                                      bs_name=__param_bs_name__.format(bs),
                                      bs_mac=__param_bs_mac__.format(bs.get_mac_address()),
                                      experiment_id=__param_experiment_id__.format(Globals.experiment_id),
                                      control_port=__param_control_port__.format(self.simulation_control_port_map[bs]),
                                      base_station=bs)]

                    self.logger.debug("[{0}] Starting Ns-3. Params={1}".format(bs, params))

                    p = subprocess.Popen(params, stdout=subprocess.PIPE, stderr=open("/tmp/{0}-bs".format(bs), 'w'))
                    results[bs] = True

                    pid = None

                    for line in iter(p.stdout.readline, ''):
                        if line.decode().startswith("PID:"):
                            pid = int(line.decode().replace("PID:", ""))
                            break

                    self.ns3_pid_list[bs] = pid
                    p.wait()

                    if self.kill_ns3:
                        return

            except ConnectionError as error:
                self.logger.error("[[0]] Error creating TAP devices. "
                                  "Error: {1}".format(bs,
                                                      error))
                results[bs] = False

            # if p.wait() == 0:
            #     self.logger.info("[{0}] NS3 process correctly started".format(bs.get_server()))
            #     print("[{0}] NS3 process correctly started".format(bs.get_server()))
            # else:
            #     print(make_colored("red", "[{0}] Error starting NS3 process.".format(bs.get_server())))
            #     self.logger.error("[{0}] Error closing NS3 processes.".format(bs.get_server()))

        return start_thread_pool(self.base_station_list, setup_mobility, join=False, sleep_time=0.1)

    def start_mobility_threads(self):
        """
        Start N threads controlling the mobile station of the network.
        N is the number of the mobile station.

        :return:
        """

        for mobile_station in self.mobile_station_list:
            self.logger.info("Starting {0}".format(mobile_station))

            if mobile_station.get_mobility_model() == Crackle.ConfigReader.__mobility_models__[0]:
                # Constant Position
                t = threading.Thread(target=self.constant_position, args=[mobile_station])
            elif mobile_station.get_mobility_model() == Crackle.ConfigReader.__mobility_models__[1]:
                # Random Waypoint
                t = threading.Thread(target=self.random_waypoint, args=[mobile_station])

            t.start()
            self.mobility_threads.append(t)

        for t in self.mobility_threads:
            t.join()

        self.mobility_threads.clear()

    def clean_servers(self):
        """
        Clean the servers by deleting the NS3 interfaces and killing the NS3 processes
        :return: True if the cleaning successes, False otherwise
        """

        def clean_server(server, results):

            try:

                header = ["ssh",
                          "-i",
                          Constants.ssh_client_private_key,
                          "{0}@{1}".format(Globals.username, server)]

                commands = ["sudo kill -9 {0}; ".format(pid) for pid in self.ns3_pid_list.values()]

                print(commands)

                if len(commands):
                    command = [" ".join(commands)]
                    params = header + command
                    p = subprocess.Popen(params, stdout=subprocess.DEVNULL)

                    if p.wait() == 0:
                        self.logger.info("[{0}] NS3 processes correctly terminated".format(server))
                    else:
                        print(make_colored("red", "[{0}] Error closing NS3 processes. Params: {1}".format(server,
                                                                                                          params)))
                        self.logger.error("[{0}] Error closing NS3 processes.".format(server))

                time.sleep(2)

                commands = ["sudo ip tuntap del {0} mod tap; ".format(t[0]) for t in self.tap_list if t[1] == server]

                if len(commands):
                    command = [" ".join(commands)[:-2]]
                    params = header + command

                    self.logger.info(params)

                    p = subprocess.Popen(params)

                    if p.wait() == 0:
                        self.logger.info("[{0}] Taps interfaces correctly deleted!".format(server))
                        results[server] = True
                    else:
                        print(make_colored("red", "[{0}] Error deleting tap interfaces.".format(server)))
                        self.logger.error("[{0}] Error deleting tap interfaces. Params: {1}".format(server,
                                                                                                    params))

            except Exception as error:
                self.logger.error("[{0}] Error cleaning up server. "
                                  "Error: {1}".format(server,
                                                      error))
                results[server] = False

        self.kill_ns3 = True
        return start_thread_pool(self.server_list, clean_server)

    def constant_position(self, node):
        """
        This function implements the constant position mobility model.
        :param node:
        :return:
        """
        print("\t * Constant Position: Starting movement of the entity {0}".format(node))

        bs = self.base_station_list[0]

        d = node.get_starting_point().distance(Point(self.base_station_list[0].get_x(),
                                                     self.base_station_list[0].get_y()))

        for base_station in self.base_station_list:
            distance = node.get_starting_point().distance(Point(base_station.get_x(), base_station.get_y()))
            if distance < d:
                bs = base_station
                d = distance

        movement_description = {
            __mobility_model__: __mobility_models__[0],
            __base_station__: bs.get_node_id(),
            __station__: node.get_node_id(),
            __start_x__: float(node.get_starting_point().x),
            __start_y__: float(node.get_starting_point().y)
        }

        self.send_movement_description(bs, movement_description)
        self.attach_to(node, bs)

    def random_waypoint(self, node):
        """
        Code to be executed on the master node. Here we are simulating the random waypoint mobility.
        We start from a fixed point, and then we select a random destination point. We go with a certain speed toward
        this point, by traversing a certain number of Base Stations, and as soon as we reach it we select
        a new destination point, repeating the procedure.
        :param node -> The mobile station
        :param notification -> Boolean that indicates if sending or not the Interest Notification
        """

        print("\t * Random Waypoint: Starting movement of the entity {0}".format(node))

        previous_base_station = None

        start_point = node.get_starting_point()

        # Compute Node List Based on the speed and the topology

        while True:

            if self.killall:
                self.thread_print(make_colored("green", "[{0}][Random Waypoint]: Killing mobility thread".format(node)))
                return

            mobility_description = self.compute_traversed_nodes(node, start_point)

            start_point_x = round(float(mobility_description[0][1].x), 2)
            start_point_y = round(float(mobility_description[0][1].y), 2)
            end_point_x = round(float(mobility_description[-1][1].x), 2)
            end_point_y = round(float(mobility_description[-1][1].y), 2)

            self.thread_print(make_colored("blue",
                                           "[{node}][Random Waypoint]: Starting movement from "
                                           "[{start_point_x}, {start_point_y}] "
                                           "to the position "
                                           "[{end_point_x}, {end_point_y}]".format(node=node,
                                                                                   start_point_x=start_point_x,
                                                                                   start_point_y=start_point_y,
                                                                                   end_point_x=end_point_x,
                                                                                   end_point_y=end_point_y)))

            for start, stop in grouped(mobility_description, 2):

                # Create json containing the coordinates of the movement to send to the NS3 simulation

                movement_description = {
                    __mobility_model__: __mobility_models__[1],
                    __base_station__: start[0].get_node_id(),
                    __station__: node.get_node_id(),
                    __start_x__: float(start[1].x),
                    __start_y__: float(start[1].y),
                    __end_x__: float(stop[1].x),
                    __end_y__: float(stop[1].y),
                    __duration__: float(stop[2])
                }
                self.logger.debug("[{}] Sending mobility description {} to base station {}. Port: {}".format(node,
                                                                                                             movement_description,
                                                                                                             start[0],
                                                                                                             self.simulation_control_port_map[
                                                                                                                 start[
                                                                                                                     0]]))
                self.send_movement_description(start[0], movement_description)

                # This avoid a disconnection/reconnection when the station is just changing its direction and not bs
                if previous_base_station and previous_base_station.get_node_id() != start[0].get_node_id():
                    self.do_handoff(node, previous_base_station, start[0])
                elif previous_base_station is None:
                    self.attach_to(node, start[0])

                time.sleep(float(stop[2]))
                previous_base_station = stop[0]
                if self.killall:
                    return

        return

    def do_handoff(self, node, previous_base_station, next_base_station):
        """
        This function forces an handover from previous_base_station to next_base_station.

        :param node:
        :param previous_base_station:
        :param next_base_station:
        :return:
        """

        self.disconnect_from(node, previous_base_station)
        self.logger.debug("[{0}] Attaching to base station {1}".format(node, next_base_station))
        self.attach_to(node, next_base_station)

    def disconnect_from(self, node, base_station):
        """

        :param node:
        :param base_station:
        :return:
        """

        if node.de_attach_from_base_station(base_station):
            self.logger.debug("[{0}] Successfully de-attached from {1}".format(node,
                                                                               base_station))
        else:
            self.logger.error("[{0}] Error de-attaching from {1}".format(node,
                                                                         base_station))

    def attach_to(self, node, base_station):
        """
        Attach to a the base station base_station
        :param node:
        :param base_station:
        :return:
        """

        if node.attach_to_base_station(base_station):
            self.logger.debug("[{0}] Successfully attached to {1}".format(node,
                                                                          base_station))
        else:
            self.logger.error("[{0}] Error attaching from {1}".format(node,
                                                                      base_station))
        if node.get_client_apps():
            node.update_default_route(base_station, __sta_prefix__)

        if node.get_repositories():
            if Globals.global_routing:
                self.ndn.recompute_global_routing(None, Constants.__tree_on_consumer__, True, rerouting=True)

    def send_movement_description(self, base_station, description):
        """
        This function sends the description of the movement to a specific NS-3 simulation.
        :param base_station: The base station corresponding to the simulation
        :param description: The description of the movement
        :return:
        """

        control_port = self.simulation_control_port_map[base_station]

        description[__experiment_id__] = Globals.experiment_id
        description_json = json.dumps(description) + "\r\n\r\n"

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        try:
            s.connect((base_station.get_server().get_hostname(), control_port))
            s.sendall(description_json.encode())
        except socket.error as exc:
            print(make_colored("red", "[{}] Error connecting to remote simulation: {}".format(base_station,
                                                                                              exc)))
            self.logger.error("[{}] Error connecting to remote simulation: {}".format(base_station,
                                                                                      exc))



    @staticmethod
    def send_iu(node, name, seq_number, notification):
        """
        This function is useful in the mobility scheme in which crackle manages the mobility
        attaching and de-attaching the container to different NS3 instances
        :param node : The mobile entity that we have to deattach
        :param name :
        :param seq_number :
        :param notification: The base station from which deattach the container
        """

        if not notification:
            params = ["mapme-cli",
                      "-n",
                      name,
                      "-c",
                      str(seq_number)]
        else:
            params = ["mapme-cli",
                      "-n",
                      name,
                      "-c",
                      str(seq_number),
                      "-a"]

        node.run_command(params)

    def compute_traversed_nodes(self, node, start_point):

        def find_closest_bs(bs_list, point):
            # Find closes BS
            d = float(point.distance(bs_list[0].get_bs_position()))
            bs = bs_list[0]
            for b in bs_list:
                dist = float(point.distance(b.get_bs_position()))
                if dist < d:
                    d = dist
                    bs = b
            return bs

        p1 = start_point
        points = []

        speed = node.get_speed()

        bs1 = find_closest_bs(self.base_station_list, p1)

        points.append((bs1, p1))

        boundaries = node.get_boundaries()

        # First: Compute the destination:
        p2_x = uniform(boundaries[0], boundaries[1])
        p2_y = uniform(boundaries[2], boundaries[3])
        p2 = Point(p2_x, p2_y)

        self.logger.debug("[{0}] Starting from ({1}, {2}) to ({3}, {4})".format(node,
                                                                                p1.x,
                                                                                p1.y,
                                                                                p2.x,
                                                                                p2.y))
        bs2 = find_closest_bs(self.base_station_list, p2)

        points.append((bs2, p2))

        s = Segment(p1, p2)

        print("Starting point: [{},{}]. Arrival point: [{},{}]".format(float(p1.x), float(p1.y), float(p2.x),
                                                                       float(p2.y)))

        # Compute the cells traversed by the station

        for bs in self.base_station_list:
            inters = bs.intersect(s)
            for p in inters:
                points.append((bs, p))

        # Order the points by x and y (ascending or descending order depending on the direction)
        if p1.x <= p2.x and p1.y <= p2.y:
            points.sort(key=lambda element: (element[0].get_x(), element[0].get_y()))
            points.sort(key=lambda element: (element[1].x, element[1].y))
        elif p1.x <= p2.x and p1.y > p2.y:
            points.sort(key=lambda element: (element[0].get_x(), -1 * element[0].get_y()))
            points.sort(key=lambda element: (element[1].x, -1 * element[1].y))
        elif p1.x >= p2.x and p1.y <= p2.y:
            points.sort(key=lambda element: (-1 * element[0].get_x(), element[0].get_y()))
            points.sort(key=lambda element: (-1 * element[1].x, element[1].y))
        elif p1.x >= p2.x and p1.y > p2.y:
            points.sort(key=lambda element: (-1 * element[0].get_x(), -1 * element[0].get_y()))
            points.sort(key=lambda element: (-1 * element[1].x, -1 * element[1].y))

        mobility_description = []

        for p_a, p_b in grouped(points, 2):
            s = Segment(p_a[1], p_b[1])
            print("BS={} P1={}, P2={}".format(p_a[0], [float(p_a[1].x), float(p_a[1].y)],
                                              [float(p_b[1].x), float(p_b[1].y)]))
            print(float(s.length), "Time: {}".format(float(s.length) / speed))
            mobility_description.append((p_a[0], p_a[1], 0))
            mobility_description.append((p_b[0], p_b[1], float(s.length) / speed))
            self.logger.debug("[{0}] base_station={1}, segment={2}, time={3}".format(node,
                                                                                     p_b[0],
                                                                                     float(s.length),
                                                                                     float(s.length / speed)))

        return mobility_description
