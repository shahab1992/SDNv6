"""
This module gathers all the fundamental classes representing the different characters in the experiment.
The classes implemented in this module regard:

    - The **Router**, **Base Station** and **Mobile Station** entities
    - The **Links**
    - The **Repositories** and the **Clients**
"""

from __future__ import division
import json
import logging

import math
from numpy.core import operand_flag_tests
from sympy.geometry import Polygon, Point, Circle
from Crackle.Constants import layer_2_protocols
import Crackle.Constants as Constants
from math import sqrt
import Crackle.Globals as Globals
from Crackle.LxcUtils import AddressGenerator
from abc import ABCMeta, abstractmethod

__register__ = "register"
__unregister__ = "unregister"
__create__ = "create"
__destroy__ = "destroy"


class Router:
    """
    This class represents a router in the network. Since each node can be a router, this class is used as Base class for
    implementing the :class:`Crackle.TopologyStructs.BaseStation` and :class:`Crackle.TopologyStructs.Station` classes.

    :ivar cache_size: The size of the cache of this NDN router
    :ivar cache_policy: The cache policy on this router
    :ivar cache_probability: The probability that a piece of data will be cached on this router
    :ivar client_apps: The list of client applications running on this node
    :ivar repo_apps: The list of repositories running on this router
    :ivar links: The list of "L2" connections of this router
    :ivar routes: The L3 routing table on this router
    :ivar node_id: The identifier (also DNS name) of this router
    :ivar container: The linux container associated to this router
    :ivar mobile: Boolean that says if this node is mobile or not
    :ivar address: IP address of the underlying linux container
    """

    def __init__(self, node_id, cache_size, cache_policy, cache_probability,
                 forward_strategy, container=None, vlan=Constants.router_vlan, mobile=False):

        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)

        self.cache_size = cache_size
        self.cache_policy = cache_policy
        self.cache_prob = cache_probability
        self.forward_strategy = forward_strategy

        self.client_apps = []
        self.repo_apps = []
        self.links = {}
        self.routes = {}

        self.node_id = node_id
        self.mobile = mobile
        self.container = container
        self.vlan = vlan
        self.container.set_vlan(vlan)

        self.server = ""

    def set_forward_strategy(self, forward_strategy):
        """
        Set the cache size. The default value is 65536 packets.

        :param forward_strategye: The forward strategy for this node.
        :return: The current :class:`Router` instance
        """
        self.forward_strategy = forward_strategy
        return self

    def get_forward_strategy(self):
        """
        Get the current value of the cache size

        :return: The cache size.
        """
        return self.forward_strategy

    def get_vlan(self, bs=None):
        """
        Get the VLAN of this node.
        :return:
        """
        if bs is None:
            return self.vlan

    def set_cache_size(self, cache_size):
        """
        Set the cache size. The default value is 65536 packets.

        :param cache_size: The value of the cache size.
        :return: The current :class:`Router` instance
        """
        self.cache_size = cache_size
        return self

    def get_cache_size(self):
        """
        Get the current value of the cache size

        :return: The cache size.
        """
        return self.cache_size

    def set_cache_policy(self, cache_policy):
        """
        Set the cache policy.

        :param cache_policy: The cache policy to set.
        :return: The current :class:`Router` instance
        """
        self.cache_policy = cache_policy
        return self

    def get_cache_policy(self):
        """
        Get the current cache_policy on this node.

        :return: The cache_policy
        """
        return self.cache_policy

    def set_cache_prob(self, cache_prob):
        """
        Set the cache probability.

        :param cache_prob: The cache probability to set.
        :return: The current :class:`Router` instance
        """
        self.cache_prob = cache_prob
        return self

    def get_cache_prob(self):
        """
        Get the current cache_probability on this node.

        :return: The current :class:`Router` instance
        """
        return self.cache_prob

    def spawn_container(self):
        """
        Start the container associated with this router.

        :return: True if the container starts successfully, False otherwise
        """
        return self.container.spawn_container()

    def push_file(self, source_path, dest_path):
        """
        Push a file inside the container.

        :param source_path: The location of the file to push
        :param dest_path: The path of the file inside the container

        :return: True if the push succeed, False otherwise
        """

        return self.container.push_file(source_path, dest_path)

    def pull_file(self, source_path, dest_path):
        """
        Download a file from the container.

        :param source_path: The location of the file inside the container
        :param dest_path: The destination of the file in the host
        :return: True if the file pull succeed, false otherwise
        """

        return self.container.pull_file(source_path, dest_path)

    def stop_container(self, async=False):
        """
        Stop the container associated with this router.

        :return: True if the container starts successfully, False otherwise
        """
        return self.container.stop_container(async)

    def start_container(self):
        """
        Stop the container associated with this router.

        :return: True if the container starts successfully, False otherwise
        """
        if not self.container.start_container():
            return False
        else:
            return True

    def delete_container(self):
        """
        Stop the container associated with this router.

        :return: True if the container starts successfully, False otherwise
        """
        if not self.container.delete_container():
            return False
        else:
            return True

    def add_client(self, client):
        """
        Add a client to the list of client of this router.

        :param client: The :class:`Client` to add
        :return: The current :class:`Router` instance
        """
        self.client_apps.append(client)
        return self

    def get_status(self):
        """
        Return the status of the container.

        :return: The description of the status of the container
        """

        return self.container.get_status()

    def add_repo(self, repo):
        """
        Add a repository to the list of repository of this router.

        :param repo: The :class:`Repo` to add
        :return: The current :class:`Router` instance
        """
        self.repo_apps.append(repo)
        return self

    def delete_repo(self):
        """
        Delete a repository to the list of repository of this router.

        :return: The current :class:`Router` instance
        """
        self.repo_apps.pop()

        return self

    def add_link(self, link):
        """
        Add a link between this router and another one.

        :param link: The :class:`Link` to add
        :return: The current :class:`Router` instance
        """

        self.logger.debug("[{0}] Adding link to {1}".format(self.node_id,
                                                            link.get_node_to()))

        self.links[link.get_node_to()] = link
        return self

    def delete_link(self, link):
        """
        Delete the link from the list of link of this node.

        :param link:
        :return:
        """
        self.container.delete_neighbor(link.get_node_to())
        del self.links[link.get_node_to()]

        return self

    def delete_route(self, icn_name, next_hop):
        """
        Delete a route from the routing table of this node

        :return:
        """
        del self.routes[next_hop][icn_name]

    def delete_all_routes(self, next_hop):
        """
        Delete all the routes toward next_hop
        :param next_hop:
        :return:
        """

        del self.routes[next_hop]

    def add_route(self, node_to, prefix):
        """
        Add a route to the routing table of the node. These routes will be used in the method \
        :meth:`Crackle.NDNManager.NDNManager.create_routing_scripts`.

        :param node_to: The node_id of the next hop
        :param prefix: The name of the data
        :return: The current :class:`Router` instance
        """

        self.logger.debug("[{0}] Adding route for name {1} to {2}".format(self.node_id,
                                                                          prefix,
                                                                          node_to))

        route = Route(self, prefix, node_to)

        if node_to in self.routes:
            self.routes[node_to][prefix] = route
        else:
            self.routes[node_to] = {prefix: route}

        return self

    def set_mobile(self, mobile):
        """
        Set if the current node will move or not.

        :param mobile: Boolean that say if the node is mobile or not
        :return: The current :class:`Router` instance
        """
        self.mobile = mobile
        return self

    def is_mobile(self):
        """
        Return true if the node is mobile, false otherwise.

        :return: The value of the mobile attribute.
        """
        return self.mobile

    def set_ip_address(self, ip_address, neighbor=None):
        """
        Set the IP address of the container.

        :param ip_address: The ip address of the container
        :param neighbor: Get the ip address of the interface toward neighbor
        :return:
        """
        return self.container.set_ip_address(neighbor, ip_address)

    def get_ip_address(self, neighbor=None):
        """
        Get the IP address of the underlying linux container.

        :param neighbor: Get the ip address of the interface
        :return: The IP address of the underlying linux container
        """
        return self.container.get_ip_address(neighbor)

    def set_node_id(self, node_id):
        """
        Set the node identifier.

        :param node_id: The value of the node identifier.
        :return: The current :class:`Router` instance
        """
        self.node_id = node_id
        return self

    def get_node_id(self):
        """
        Get the identifier (also the DNS name) of this node.

        :return: The node_id of this router
        """
        return self.node_id

    def set_container(self, container):
        """
        Set the container associated with this router

        :param container: The :class:`Crackle.LxcManager.RouterRouter` object
        :return: The current :class:`Router` instance
        """
        self.container = container
        return self

    def get_container(self):
        """
        Get the container associated to this router

        :return: The :class:`Crackle.LxcManager.RouterContainer` associated with the current router
        """
        return self.container

    def get_links(self):
        """
        Get the L2 links of this router

        :return: The list of :class:`Link` of this router
        """
        return self.links

    def get_mac_address(self, neighbor=None):
        """
        Get the MAC address of the underlying container.

        :param neighbor: Get the MAC Address of the interface toward neighbor
        :return: The MAC address of the container.
        """
        return self.container.get_mac_address(neighbor)

    def set_mac_address(self, mac_address, neighbor=None):
        """
        Get the MAC address of the underlying container.

        :param neighbor: Get the MAC Address of the interface toward neighbor
        :return: The MAC address of the container.
        """
        return self.container.set_mac_address(mac_address, neighbor)

    def get_repositories(self):
        """
        Get the list of repositories of this router.

        :return: The list of :class:`Repo` on this router
        """
        return self.repo_apps

    def get_routes(self):
        """
        Get the list of L3 routes of this router

        :return: The list of routes on this router.
        """
        return self.routes

    def get_route(self, icn_name, node_to):
        """
        Return the route for the name icn_name through node_to
        :param icn_name:
        :param node_to:
        :return:
        """

        return self.routes[node_to][icn_name]

    def get_client_apps(self):
        """
        Get the list of clients of this router.

        :return: The list of :class:`Client` on this router
        """
        return self.client_apps

    def get_server(self):
        """
        Return the server on which this container will be (has been) spawn (spawned)

        :return: the DNS name of the server
        """

        return self.container.get_server()

    def set_server(self, server):
        """
        Return the server on which this container will be (has been) spawn (spawned)

        :param server:
        :return: The current :class:`Router` instance
        """

        self.container.set_server(server)

    def set_vlan(self, vlan):
        """
        Set the vlan of this node

        :param server:
        :return: The current :class:`Router` instance
        """

        self.container.set_vlan(vlan)

    def run_command(self, params,
                    sync=True,
                    check_return=True,
                    websocket=False,
                    output=False,
                    interactive=False):
        """
        Run a cmd on the this router.

        :param params: The list with the command and the parameters
        :param sync: If the command has to be executed in a sync or async manner
        :param output: If the output of the command has to be printed to stdout
        :param interactive: If the command requires an interactive session
        :return: The return code of the command
        """

        return self.container.run_command(params,
                                          check_return=check_return,
                                          interactive=interactive,
                                          websocket=websocket,
                                          sync=sync,
                                          output=output)

    def __str__(self):
        return self.node_id


class BaseStation(Router):
    """
    This class represents a base station to which the :class:`Station` can attach during the mobility.
    It inherits from the base class Router for the base functions. In addition it provides the base station
    attributes and functionalities.
    In order to provide a pseudo-realistic wireless environment, the base station is not directly connected to the
    mobile stations, but it is connected to an instance of the NS-3 simulator. The simulator is emulating the access channel,
    in order to provide a wireless environment that is closer to the reality. Then the mobile stations can connect to
    the base station by connecting themselves with the same simulator process.

    :ivar tap_list: The list of TAP devices of the NS3 simulation associated to the mobile stations
    :ivar bs_tap: The TAP device of the NS3 simulation associated to this base station
    :ivar x: The x coordinate of the base station
    :ivar y: The y coordinate of the base station
    :ivar center: The couple (x, y) as Point object
    :ivar neighbors: The list of neighbors base stations (neighbor = under radius distance)
    :ivar radius: The radius of the base station. It provides a way to find the neighbors.
    :ivar shape_type: The shape of the area covered by the base station
    :ivar side: Depending on the shape_type, it could be a radius (circle) or a side (square, hexagon).
    :ivar shape: The shape object (Circle, Square, Hexagon)
    """

    def __init__(self,
                 node_id,
                 cache_size,
                 cache_policy,
                 cache_probability,
                 forward_strategy,
                 x,
                 y,
                 container=None,
                 vlan=1,
                 bs_vlan=2,
                 mobile=False):

        Router.__init__(self, node_id, cache_size, cache_policy, cache_probability, forward_strategy, container, vlan,
                        mobile)
        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)

        self.tap_list = []
        self.bs_tap = ""
        self.bs_vlan = bs_vlan
        self.container.set_bs_vlan(bs_vlan)

        self.x = float(x)
        self.y = float(y)
        self.neighbors = []
        self.BS = True
        self.shape = None

    def create_shape(self, vertices):
        """
        Create the cell shape based on the received parameters.
        :param shape: A string with the name of the shape. SUPPORTED SHAPES: **Circle, Square and Hexagon**
        :return: the object representing the shape
        """

        self.shape = Polygon(*vertices)

    def intersect(self, segment):
        """
        Find the intersections between a segment and the cell

        :param segment: The segment the shape is going to be intersected with.
        :return: The intersection points
        """
        return self.shape.intersection(segment)

    def point_in_cell(self, p):
        """
        Check if a point is on the border of the cell or inside it
        :param p: The point to check
        :return: True if the point is inside the cell or in the border, False otherwise
        """
        if p in self.shape.vertices or any(p in s for s in self.shape.sides):
            return True
        return self.shape.encloses_point(p)

    def get_x(self):
        """
        Return the x coordinate of the Base Station.

        :return: the Base station's x coordinate
        """
        return self.x

    def get_y(self):
        """
        Return the y coordinate of the Base Station.

        :return the Base station's y coordinate
        """
        return self.y

    def get_bs_position(self):
        """
        Return a point representing the BS position.

        :return: The point representing the BS position.
        """
        return Point(self.x, self.y)

    def get_radius(self):
        """
        Return the radius of the cell's circumcircle

        :return The radius of the cell's circumcicle
        """
        return self.radius

    def set_neighbors(self, neighbors):
        """
        Set the list of closest BS

        :param neighbors: the list of neighbors
        :return: The current :class:`BaseStation` instance
        """
        self.neighbors = neighbors
        return self

    def add_neighbors(self, neighbor):
        """
        Add the new neighbors to the actual neighbors list at the index index

        :param neighbor: the list of neighbors
        :return: The current :class:`BaseStation` instance
        """
        self.neighbors.append(neighbor)
        return self

    def get_neighbors(self):
        """
        Return the list of neighbors.

        :return: The List of Neighbors
        """
        return self.neighbors

    def get_bs_vlan(self):
        """
        Return the vlan of the base station interface on this node.

        :return: the vlan ID of the node
        """

        return self.container.get_bs_vlan()

    def set_bs_vlan(self, vlan):
        """
        Set the vlan of the base station interface on this node.

        :param server:
        :return: The current :class:`Router` instance
        """

        self.container.set_bs_vlan(vlan)

    def __hash__(self):
        """
        Redefine the hash function for this class.
        :return: The hash value of the DNS name, that usually should be different
                 for each machine involved in the experiment
        """
        return hash(self.node_id)

    def add_sta_tap(self, tap, vlan):
        """
        Add a simulation tap associated to a mobile station.

        :param tap: The TAP associated to the mobile station
        :return: The current :class:`BaseStation` instance
        """
        ret = self.container.add_sta_tap(tap, vlan)

        if ret:
            self.tap_list.append(tap)

        return ret

    def get_bs_ip_address(self):
        """
        Get the IP address of the base station.

        :return:
        """

        return self.container.get_ip_address()

    def set_bs_tap(self, tap):
        """
        Add a simulation tap associated to this base station.

        :param tap: The TAP associated to the base station
        :return: The current :class:`BaseStation` instance
        """
        ret = self.container.set_simulator_tap(tap)

        if ret:
            self.bs_tap = tap

        return ret

    def create_face(self, station):
        """
        Create a face toward a certain station

        :param station:
        :return:
        """

        if Globals.layer2_prot != layer_2_protocols[4]:
            face = "{0}://{1}:6363".format(Globals.layer2_prot,
                                           station.get_ip_address(self))
        else:
            face = "ether://[{0}]/{1}".format(station.get_mac_address(self),
                                              "wlan0")

        if Globals.wldr_face:
            params = ["nfdc", "create", "-W", face]
        else:
            params = ["nfdc", "create", face]

        self.logger.debug("[{0}] Creating face to station {1}. Params: {2}".format(self.node_id,
                                                                                   station,
                                                                                   params))

        return self.container.run_command(params)

    def destroy_face(self, station):
        """
        Destroy a face

        :param station:
        :return:
        """

        if Globals.layer2_prot != layer_2_protocols[4]:
            face = "{0}://{1}:6363".format(Globals.layer2_prot,
                                           station.get_ip_address(self))
        else:
            face = "ether://[{0}]".format(station.get_mac_address(self))

        params = ["nfdc", "destroy", face]

        self.logger.debug("[{0}] Destroying face to station {1}. Params: {2}".format(self.node_id,
                                                                                     station,
                                                                                     params))

        return self.container.run_command(params)

    def serialize(self):
        """
        Serialize the Base Station object.
        :return: A string with all the parameter of the BS constructor, in order to be able to subsequently rebuild it
        """
        return json.dumps({"constructor": [self.node_id,
                                           self.cache_size,
                                           self.cache_policy,
                                           self.cache_prob,
                                           self.x,
                                           self.y,
                                           self.shape_type,
                                           self.side],
                           "neighbors": self.neighbors})

    def __str__(self):
        return self.node_id


class Station(Router):
    """
    This class represents a mobile station. It inherits from the base class :class:`Router` and defines all the elements
    that characterize a mobile station, such as the mobility configuration.

    :ivar mobility_model: The mobility model that this mobile station has to follow. It can be **RANDOM WALK** \
    or **RANDOM WAYPOINT**
    :ivar starting_point: The starting point of the mobile station.
    :ivar mobility_duration: How long this station has to move
    :ivar speed: The speed of the base station. This parameter makes sense just for the Random Waypoint mobility model.
    """

    def __init__(self,
                 node_id,
                 cache_size,
                 cache_policy,
                 cache_probability,
                 forward_strategy,
                 mobility_model="",
                 starting_point="",
                 mobility_duration="",
                 mobility_speed="",
                 boundary_x_0="",
                 boundary_x_max="",
                 boundary_y_0="",
                 boundary_y_max="",
                 container=None,
                 mobile=True):

        Router.__init__(self, node_id, cache_size, cache_policy, cache_probability, forward_strategy,
                        container=container, vlan=1, mobile=mobile)

        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)

        self.mobility_model = mobility_model
        self.starting_point = starting_point
        self.mobility_duration = mobility_duration
        self.speed = mobility_speed
        self.boundary_x_0 = boundary_x_0
        self.boundary_x_max = boundary_x_max
        self.boundary_y_0 = boundary_y_0
        self.boundary_y_max = boundary_y_max

    def set_mobility_model(self, mobility_model):
        """
        Set the mobility model for this :class:`Station`.

        :param mobility_model: The mobility model. It could be either **Random Waypoint** or **Random Walk**. It is read \
        from the configuration file "mobility.model".
        :return: The current :class:`Station` instance
        """
        self.mobility_model = mobility_model
        return self

    def get_mobility_model(self):
        """
        Get the current mobility model of the Station

        :return: The mobility model of the :class:`Station`
        """
        return self.mobility_model

    def set_starting_point(self, x, y):
        """
        Set the starting point of the Station.

        :param x: The x coordinate of the starting point
        :param y: The y coordinate of the starting point
        :return: The current :class:`Station` instance
        """
        self.starting_point = Point(float(x), float(y))
        return self

    def get_starting_point(self):
        """
        Get the current starting point of the Station.

        :return: The starting point of this Station
        """
        return self.starting_point

    def get_mac_address(self, bs):
        """
        Get the MAC address of the underlying container.

        :return: The MAC address of the container.
        """
        return self.container.get_mac_address(bs)

    def set_speed(self, speed):
        """
        Set the speed of the current Station.

        :param speed: The speed of the station.
        :return: The current :class:`Station` instance
        """
        self.speed = float(speed)
        return self

    def get_speed(self):
        """
        Get the speed of the mobility of the current Station

        :return: The mobility duration of the current :class:`Station`
        """
        return self.speed

    def set_boundaries(self, x_0, x_max, y_0, y_max):
        """
        Set the movement limits for the station
        :param x_0:
        :param x_max:
        :param y_0:
        :param y_max:
        :return:
        """
        self.boundary_x_0 = x_0
        self.boundary_x_max = x_max
        self.boundary_y_0 = y_0
        self.boundary_y_max = y_max

    def get_boundaries(self):
        """
        Get the boundaries for the moement of this station
        :return:
        """

        return [self.boundary_x_0, self.boundary_x_max, self.boundary_y_0, self.boundary_y_max]

    def attach_to_base_station(self, base_station):
        """
        Attach the current Station to the specified :class:`BaseStation`

        :param base_station_tap: The name of the TAP device associated to the :class:`BaseStation` to which the current \
        :class:`Station` has to attach
        :return: The current :class:`Station` instance
        """

        station_link = WirelessLink(self, base_station, str(base_station))
        self.add_link(station_link)
        base_station.add_link(WirelessLink(base_station, self, "wlan0"))

        return station_link.create_link() and station_link.create_face() and station_link.create_face(station=False)

    def de_attach_from_base_station(self, base_station):
        """
        De_attach the current Station from the specified :class:`BaseStation`

        :param base_station: The name of the TAP device associated to the :class:`BaseStation` from which the current \
        :class:`Station` has to de-attach
        :return: The current :class:`Station` instance
        """

        # Remove the wireless link between Base station and Mobile Station

        ret = self.links[base_station].destroy_link() and self.links[base_station].destroy_face() and self.links[base_station].destroy_face(station=False)

        del self.links[base_station]
        del base_station.get_links()[self]

        return ret

    def create_face(self, base_station):
        """
        Create a face toward a certain base station

        :param station:
        :return:
        """

        if Globals.layer2_prot != layer_2_protocols[4]:
            face = "{0}://{1}:6363".format(Globals.layer2_prot,
                                           base_station.get_ip_address())
        else:
            face = "ether://[{0}]/{1}".format(base_station.get_mac_address(),
                                              base_station)

        if Globals.wldr_face:
            params = ["nfdc", "create", "-W", face]
        else:
            params = ["nfdc", "create", face]

        self.logger.debug("[{0}] Creating face to base station {1}. Params: {2}".format(self.node_id,
                                                                                        base_station,
                                                                                        params))

        return self.container.run_command(params)

    def destroy_face(self, base_station):
        """
        Destroy a face

        :param station:
        :return:
        """

        if Globals.layer2_prot != layer_2_protocols[4]:
            face = "{0}://{1}:6363".format(Globals.layer2_prot,
                                           base_station.get_ip_address())
        else:
            face = "ether://[{0}]".format(base_station.get_mac_address())

        params = ["nfdc", "destroy", face]

        self.logger.debug("[{0}] Destroying face to base-station {1}. Params: {2}".format(self.node_id,
                                                                                          base_station,
                                                                                          params))

        return self.container.run_command(params)

    def update_default_route(self, next_hop, prefix):
        """
        Update the default route of the mobile station.
        By default, each prefix requested/served by a mobile station starts with /ndn,
        in order to minimize the number of updates for each movement.

        :param base_station: The new next hop for the mobile station
        :return:
        """

        if Globals.layer2_prot != layer_2_protocols[4]:
            face = "{0}://{1}:6363".format(Globals.layer2_prot,
                                           next_hop.get_ip_address())
        else:
            face = "ether://[{0}]/{1}".format(next_hop.get_mac_address(),
                                              next_hop)

        params1 = ["nfdc", "register", prefix, face]

        self.logger.debug("[{0}] Updating default route. Params={1}".format(self.node_id,
                                                                            params1))

        self.add_route(next_hop, prefix)

        return self.container.run_command(params1)

    # def remove_default_route(self, old_next_hop):
    #     """
    #     This function is called when a mobile station disconnect from a base station.
    #     In order to keep connectivity the first step concern the deletion of the ols next hop.
    #     Subsequently, when the station will connect to a new base station, the default route will be updated
    #     with the function update_default_route.
    #
    #     :return:
    #     """
    #
    #     if Globals.layer2_prot != layer_2_protocols[4]:
    #         face = "{0}://{1}:6363".format(Globals.layer2_prot,
    #                                        old_next_hop.get_bs_ip_address())
    #     else:
    #         face = "ether://[{0}]".format(old_next_hop.get_bs_mac_address())
    #
    #     params = ["nfdc",
    #               "destroy",
    #               face]
    #
    #     self.logger.debug("[{0}] Removing default route. Params={1}".format(self.node_id,
    #                                                                         params))
    #
    #     return self.container.run_command(params)

    def setup_network_interfaces(self, bs_list, vlans):
        """
        Set up the network interfaces of the mobile station.
        One network interface x vlan

        :param bs_list:
        :param vlans:
        :return:
        """

        self.container.setup_network_interfaces(bs_list, vlans)

    def __str__(self):
        return self.node_id

    def get_vlan(self, bs):
        """
        Return the vlan of this node.

        :return: the vlan ID of the node
        """

        return self.container.get_vlan(bs)


# TODO set the client application directly on the configuration file.
class Client:
    """
    This class represents a client application (a consumer).

    :ivar client_id: The identifier of this client
    :ivar arrival: The arrival rate of requests
    :ivar popularity: The popularity of the content requested by this client
    :ivar name: The name requested by this consumer
    :ivar catalog: The catalog of names
    :ivar start_time: The start_time of this client. The clients could either start all together or each one can start \
    at a different time
    :ivar duration: How long this client has to run
    :ivar first_req: Boolean that indicates if the first request has been issued
    """

    def __init__(self, client_id, arrival, popularity, name, start_time=0, duration=0):
        self.logger = logging.getLogger(__name__ + "." + type(self).__name__)

        self.client_id = client_id
        self.arrival = arrival
        self.popularity = popularity
        self.name = name
        self.catalog = []  # catalog of names
        self.start_time = int(start_time)
        self.duration = int(duration)
        self.first_req = False  # indicates if the first request has been issued

    def __str__(self):
        string = "Client ID: \"{0}\", Arrival:\"{1}\" " \
                 "Popularity:\"{2}\", Name:\"{3}\" " \
                 "Start Time:\"{4}\", Duration:\"{5}\"".format(self.client_id,
                                                               self.arrival,
                                                               self.popularity,
                                                               self.name,
                                                               self.start_time,
                                                               self.duration)
        return string

    def load_catalog(self, catalog):
        """
        Set the catalog fot this client

        :param catalog: The catalog of names
        :return: The current :class:`Client` instance
        """
        self.catalog = catalog
        return self

    def set_client_id(self, client_id):
        """
        Set the client identifier

        :param client_id: The identifier of this client
        :return: The current :class:`Client` instance
        """
        self.client_id = client_id
        return self

    def get_client_id(self):
        """
        Get the client identifier

        :return: The client identifier
        """
        return self.client_id

    def set_arrival(self, arrival):
        """
        Set the arrival rate of requests

        :param arrival: The arrival rate of requests
        :return: The current :class:`Client` instance
        """
        self.arrival = arrival
        return self

    def get_arrival(self):
        """
        Get the arrival rate of requests

        :return: The arrival rate of requests
        """

        return self.arrival

    def set_popularity(self, popularity):
        """
        Set the popularity of the contents required by the Client.

        :param popularity: The popularity of the content requested by the :class:`Client`
        :return: The current :class:`Client` instance
        """
        self.popularity = popularity
        return self

    def get_popularity(self):
        """
        Get the popularity of the contents required by this client

        :return: The popularity of the contents required by this client
        """
        return self.popularity

    def set_name(self, name):
        """
        Set the name of the content requested by this client

        :param name: The name of the content required by this client
        :return: The current :class:`Client` instance
        """
        self.name = name
        return self

    def get_name(self):
        """
        Get the name of the content requested by this client

        :return: The name of the content requested by this client
        """
        return self.name

    def set_start_time(self, start_time):
        """
        Set the time at which the current client has to start to generate requests

        :param start_time: The time at which start to send requests, in seconds. This time is referred to the starting \
        time of the experiment
        :return: The current :class:`Client` instance
        """
        self.start_time = int(start_time)
        return self

    def get_start_time(self):
        """
        Get the time at which the current client has to start to generate requests

        :return: The time at which the current client has to start to generate requests
        """
        return self.start_time

    def set_duration(self, duration):
        """
        Set the total duration of the period the client has to issue requests

        :param duration: The duration of the period the client has to issue requests
        :return: The current :class:`Client` instance
        """
        self.duration = int(duration)
        return self

    def get_duration(self):
        """
        Get the total duration of the period the client has to issue requests

        :return: The duration of the period the client has to issue requests
        """
        return self.duration


class Repo:
    """
    This class defines a repository that replies to the requests of the clients.

    :ivar repo_id: The identifier of the repository
    :ivar folder: The name served by the repository

    """

    def __init__(self, repo_id, f):
        self.repo_id = repo_id
        self.folder = f

    def __str__(self):
        string = "Repo ID:\"{0}\", Name:\"{1}\"".format(self.repo_id, self.folder)
        return string

    def get_folder(self):
        """
        Get the name served by the repository

        :return: The name served by the repository
        """
        return self.folder

    def get_repo_id(self):
        """
        :return: The ID repository of this node
        """
        return self.repo_id


class Route:
    """
    This class represents a route for a name between two nodes.

    :ivar node: The node where the route has to be registered
    :ivar icn_name: The icn route name
    :ivar next_hop: The next hop
    """

    def __init__(self, node, icn_name, next_hop):
        self.node = node
        self.icn_name = icn_name
        self.next_hop = next_hop

    def __str__(self):
        return self.icn_name

    def get_icn_name(self):
        """
        Get the icn name of this route.
        :return:
        """
        return self.icn_name

    def get_next_hop(self):
        """
        Get the next hop of the route
        :return:
        """
        return self.next_hop

    def command(self, operation):
        """
        Execute a face/route registration/deletion.
        :param operation:
        :return:
        """

        if Globals.layer2_prot not in layer_2_protocols:
            self.logger.error("[Route {0} in {1}] Layer 2 protocol not recognized!.".format(self.icn_name,
                                                                                            self.node))
            return
        if Globals.layer2_prot != layer_2_protocols[4]:

            face_id = "{0}://{1}:6363".format(Globals.layer2_prot, self.next_hop.get_ip_address(self.node))

            params1 = ["nfdc",
                       operation,
                       "ndn:/{0}".format(self.icn_name.replace("/", "")),
                       face_id]
        else:

            if operation == __unregister__:
                face_id = "{0}://[{1}]".format(Globals.layer2_prot,
                                               self.next_hop.get_mac_address(self.node))
            else:
                face_id = "{0}://[{1}]/{2}".format(Globals.layer2_prot,
                                                   self.next_hop.get_mac_address(self.node),
                                                   self.next_hop)

            params1 = ["nfdc",
                       operation,
                       "ndn:/{0}".format(self.icn_name.replace("/", "")),
                       face_id]

        return self.node.run_command(params1)

    def unregister(self):
        """
        Remove the route from the underlying container.
        This implementation is NFD-related!
        :return:
        """

        return self.command(__unregister__)

    def register(self):
        """
        Register the route in the underlying container.
        This implementation is NFD-related!
        :return:
        """

        return self.command(__register__)


class Link:
    """
    Class that's representing a generic Link.
    """
    def __init__(self, node_from, node_to, interface):
        self.node_from = node_from
        self.node_to = node_to
        self.interface = interface

    def get_node_from(self):
        """
        Get the first endpoint of the link

        :return: The first endpoint of the link
        """
        return self.node_from

    def set_node_from(self, node_from):
        """
        Get the fist endpoint of the link

        :param node_from: The fist endpoint of the link
        :return: The current :class:`Link` instance
        """
        self.node_from = node_from
        return self

    def get_node_to(self):
        """
        Get the second endpoint of the link

        :return: The second endpoint of the link
        """
        return self.node_to

    def set_node_to(self, node_to):
        """
        Set the second endpoint of the link.

        :param node_to: The second endpoint of the link
        :return: The current :class:`Link` instance
        """
        self.node_to = node_to
        return self

    def get_interface(self):
        """
        Get the name of the interface of this link.

        :return:  The interface number
        """
        return self.interface

    def set_interface(self, interface):
        """
        Set the interface number (on node_from)

        :param interface: The interface number
        :return: The current :class:`Link` instance
        """
        self.interface = interface
        return self

    def create_link(self):
        raise NotImplementedError()

    def create_face(self):
        raise NotImplementedError()

    def destroy_face(self):
        raise NotImplementedError()


class WirelessLink(Link):
    """
    This class represents an unidirectional wireless link between two nodes.
    The information contained in this class are used to create a wireless link between node_from and node_to.
    """

    def __init__(self, node_from, node_to, interface):
        Link.__init__(self, node_from, node_to, interface)
        self.logger = self.logger = logging.getLogger(__name__ + "." + type(self).__name__)

    def __str__(self):
        string = "Link(station:\"{0}\", base_station:\"{1}\")".format(
                self.node_from,
                self.node_to)
        return string

    def create_link(self):
        """
        Create the link in the real container.
        :return:
        """

        return self.connect_nodes()

    def destroy_link(self):
        """
        Destroy the link between station and base station.
        :return:
        """

        return self.disconnect_nodes()

    def disconnect_nodes(self):
        """
        Destroy the connection between a station and a base station
        :return:
        """

        params = ["ip", "link", "set", str(self.node_to), "down"]

        self.logger.debug("[{0}] Deattaching from base station {1}. Params: {2}".format(self.node_from,
                                                                                        self.node_to,
                                                                                        params))
        ret = self.node_from.run_command(params, websocket=False)
        print(ret)
        return ret

    def connect_nodes(self):
        """
        Create the connection between the base station and the mobile station.
        :return:
        """

        params = ["ip", "link", "set", str(self.node_to), "up"]
        params2 = ["ip", "route", "add", self.node_to.get_ip_address(), "dev", str(self.node_to)]

        self.logger.debug("[{0}] Attaching to base station {1}. Params1: {2} Params2: {3}".format(self.node_from,
                                                                                                  self.node_to,
                                                                                                  params,
                                                                                                  params2))

        return self.node_from.run_command(params, websocket=False) and self.node_from.run_command(params2, websocket=False)

    def face_command(self, operation, station):
        """
        Create/Destroy a face

        :param operation:
        :return:
        """

        # Sanity check
        if operation not in [__create__, __destroy__]:
            raise RuntimeError("Operation {0} not supported!".format(operation))

        if Globals.layer2_prot != layer_2_protocols[4]:
            face_id = "{0}://{1}:6363".format(Globals.layer2_prot, self.node_to.get_ip_address()
            if station else self.node_from.get_ip_address(self.node_to))
        else:
            if operation == __create__:
                face_id = "{0}://[{1}]/{2}".format(Globals.layer2_prot,
                                                   self.node_to.get_mac_address() if station else self.node_from.get_mac_address(self.node_to),
                                                   self.node_to if station else "wlan0")
            else:
                face_id = "{0}://[{1}]".format(Globals.layer2_prot,
                                                   self.node_to.get_mac_address() if station else self.node_from.get_mac_address(
                                                   self.node_to))

        params = ["nfdc",
                  operation,
                  face_id]

        return self.node_from.run_command(params, websocket=False) if station else self.node_to.run_command(params, websocket=False)

    def destroy_face(self, station=True):
        """
        Destroy the face toward the nexthop
        :return:
        """

        return self.face_command(__destroy__, station)

    def create_face(self, station=True):
        """
        Create a face toward the nexthop
        :return:
        """

        return self.face_command(__create__, station)


class WiredLink(Link):
    """
    This class represents an unidirectional wired link between two nodes. The informations contained in this class are used to
    create a MACVLAN interface on the node node_from.

    :ivar node_from: The node_from, the first endpoint of the link
    :ivar node_to: The node_to, the second endpoint of the link
    :ivar interface: The name of the interface
    :ivar shaped: Boolean tht indicates if the link is shaped
    :ivar bandwidth: The bandwidth to assign to this link. It is set using linux traffic shapers.
    """

    def __init__(self, node_from, node_to, interface, shaped, capacity):
        Link.__init__(self, node_from, node_to, interface)
        self.shaped = shaped
        self.capacity = capacity

        self.tc_burst = self.get_burst(self.capacity)

        node_from_mac_address = AddressGenerator.get_mac_address()
        node_from_ip_address = AddressGenerator.get_ip_address("10.2.0.0/16")
        self.node_from.set_mac_address(node_from_mac_address, self.node_to)
        self.node_from.set_ip_address(node_from_ip_address, self.node_to)

    def __str__(self):
        string = "Link(if_id:\"{0}\", node_to:\"{1}\", node_from:\"{2}\"shaped:\"{3}\",bandwidth:\"{4}\",)".format(
                self.interface,
                self.node_to,
                self.node_from,
                self.is_shaped,
                self.capacity)
        return string

    def get_burst(self, capacity=None):
        """
        Method for getting the minimum burst size for tbf given a certain link capacity

        :param capacity:
        :return: The minimum burst size
        """

        if not capacity:
            capacity = self.capacity

        burst = math.ceil((((capacity * 1000000) / 250) / 8) / 1024)
        return 1 << (burst - 1).bit_length()

    def create_interface(self):
        """
        Create the interface in the node_from container
        :return:
        """
        params1 = ["ip",
                   "link",
                   "add",
                   "name",
                   self.interface,
                   "link",
                   "eth0",
                   "type",
                   "macvlan"]

        params2 = ["ip",
                   "link",
                   "set",
                   "dev",
                   self.interface,
                   "address",
                   self.node_from.get_mac_address(self.node_to)]

        params3 = ["ip",
                   "link",
                   "set",
                   self.interface,
                   "up"]

        params4 = ["ip",
                   "addr",
                   "add",
                   self.node_from.get_ip_address(self.node_to),
                   "brd",
                   "+",
                   "dev",
                   self.interface]

        params5 = ["ip",
                   "route",
                   "add",
                   self.node_to.get_ip_address(self.node_from),
                   "dev",
                   self.interface]

        return self.node_from.run_command(params1) and self.node_from.run_command(params2) and \
               self.node_from.run_command(params3) and self.node_from.run_command(params4) and \
               self.node_from.run_command(params5)

    def destroy_interface(self):
        """
        Destroy the interface in the node_from endpoint of the link

        :return: True if success, False otherwise
        """

        params = ["ip",
                  "link",
                  "delete",
                  self.interface]

        return self.node_from.run_command(params) and self.destroy_face()

    def face_command(self, operation):
        """
        Create/Destroy a face

        :param operation:
        :return:
        """

        # Sanity check
        if operation not in [__create__, __destroy__]:
            raise RuntimeError("Operation {0} not supported!".format(operation))

        if Globals.layer2_prot != layer_2_protocols[4]:
            face_id = "{0}://{1}:6363".format(Globals.layer2_prot, self.node_to.get_ip_address(self.node_from))
        else:
            if operation == __create__:
                face_id = "{0}://[{1}]/{2}".format(Globals.layer2_prot,
                                                   self.node_to.get_mac_address(self.node_from),
                                                   self.node_to)
            else:
                face_id = "{0}://[{1}]".format(Globals.layer2_prot,
                                               self.node_to.get_mac_address(self.node_from))

        params = ["nfdc",
                  operation,
                  face_id]

        return self.node_from.run_command(params)

    def destroy_face(self):
        """
        Destroy the face toward the nexthop
        :return:
        """

        return self.face_command(__destroy__)

    def create_face(self):
        """
        Create a face toward the nexthop
        :return:
        """

        return self.face_command(__create__)

    def shape_link(self, capacity):
        """
        Set the link bandwidth using tc

        :return:
        """

        params1 = ["tc",
                   "qdisc",
                   "del",
                   "dev",
                   self.interface,
                   "root"]

        rate = str(capacity) + "Mbit"
        burst = self.get_burst(capacity)

        params2 = ["tc",
                   "qdisc",
                   "add",
                   "dev",
                   self.interface,
                   "root",
                   "handle",
                   "1:",
                   "tbf",
                   "rate",
                   rate,
                   "burst",
                   "{0}kb".format(burst),
                   "latency",
                   "70ms"]

        params3 = ["tc",
                   "qdisc",
                   "add",
                   "dev",
                   self.interface,
                   "parent",
                   "1:1",
                   "codel"]

        return self.node_from.run_command(params1, check_return=False) and \
               self.node_from.run_command(params2) and \
               self.node_from.run_command(params3)

    def create_link(self):
        """
        Create the link in the real container.
        :return:
        """

        return self.create_interface() and self.shape_link(self.capacity)

    def is_shaped(self):
        """
        Return true if the link is shaped, false otherwise

        :return: The value of the is_shaped variable.
        """
        return self.is_shaped

    def set_shaped(self, shaped):
        """
        Set if the link is shaed or not.

        :param shaped: Boolean that indicates if the link is shaped or not
        :return: The current :class:`Link` instance
        """
        self.shaped = shaped
        return self

    def get_capacity(self):
        """
        Get the bandwidth of the link.

        :return:  The link bandwidth.
        """
        return self.capacity

    def set_capacity(self, capacity):
        """
        Set The link bandwidth

        :param capacity: Tha capacity of the link
        :return: The current :class:`Link` instance
        """
        self.capacity = capacity
        return self
