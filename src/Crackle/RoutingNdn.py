"""
  This class Implements virtual Routing algorithms in NDN
  Algo_Name to be chosen : 'TreeOnProducer', 'TreeOnConsumer',
  MinCostMultipath', 'MaxFlow'
"""
__author__ = 'shahab SHARIAT BAGHERI'

import random
import networkx as nx
import configparser
from collections import defaultdict
import itertools
import Crackle.TopologyStructs as TopologyStructs
import Crackle.Globals as Globals


class RoutingNdn:
    def __init__(self, node_list=None):

        """
        This function initializes node list and builds graph

        :param node_list: list of nodes.
        """

        self.node_list = node_list

        # Creating Graph
        # Topology dictionaries
        self.G = nx.Graph()
        self.dict_repo = {}
        self.dict_client = {}
        self.network_index = 0

    def create_graph(self):

        self.G.add_nodes_from(list(self.node_list.keys()))

        network_index = 0
        for i in self.node_list.values():

            # Wired Part of Network

            # Create Graph
            for j in i.links.values():
                self.G.add_edge(i.get_node_id(), j.node_to.get_node_id(),
                                capacity=j.capacity if type(j) is TopologyStructs.WiredLink else 1000,
                                cost=1 / j.capacity if type(j) is TopologyStructs.WiredLink else 1000)
                network_index += 1

            # Repository and Client Dictionary

            repositories = i.get_repositories()

            if repositories:

                self.dict_repo[i.get_node_id()] = []
                for repo in repositories:
                    content = repo.get_folder()
                    self.dict_repo[i.get_node_id()].append(content)

            clients = i.get_client_apps()

            if clients:

                self.dict_client[i.get_node_id()] = []
                for client in clients:
                    content = client.get_name()
                    self.dict_client[i.get_node_id()].append(content)

    def get_index(self):

        """
        Get maximum network index
        """

        return self.network_index

    def get_graph(self):

        """
        Get graph
        """

        return self.G

    def algo_ndn(self, Algo_Name):

        """
        Find best path between consumer and producer. 
        and list.

        :param Algo_Name: name of chosen algorithm
        :return lis:  list of calculated routes.
        """

        self.create_graph()

        #  Init Routing
        for i in self.node_list.values():
            i.routes = {}

        # TreeOnConsumer Algorithm

        if Algo_Name == 'TreeOnConsumer':

            # TreeOnConsumer Algorithm

            for repo, prefix in self.dict_repo.items():
                for p in prefix:
                    for k, v in nx.single_source_shortest_path(self.G, repo).items():

                        if len(v) > 1 and v[-1] in self.dict_client :

                            for i in range(0, len(v) - 1):

                                self.node_list[v[i + 1]].add_route(self.node_list[v[i]], p)
        # TreeOnProducer Algorithm

        elif Algo_Name == 'TreeOnProducer':

            for client, prefix in self.dict_client.items():
                name = self.dict_repo.values()
                for p in name:

                    for k, v in nx.single_source_shortest_path(self.G, client).items():
                        if len(v) > 1 and v[-1] in self.dict_repo:
                            for i in range(0, len(v) - 1): 
     
                                self.node_list[v[i]].add_route(self.node_list[v[i + 1]], p[0])

        # MinCostMultipathConsumer Algorithm

        elif Algo_Name == 'MinCostMultipath':

            lc = len(self.dict_client)
            lr = len(self.dict_repo)

            if (lc > 1 and lr == 1) or (lc == 1 and lr == 1):
                for repo, prefix in self.dict_repo.items():
                    for client, prefix in self.dict_client.items():
                       name =  self.dict_repo.values()
                       for p in name:
                          l = min(map(len, nx.all_simple_paths(self.G, repo, client)))
                          for member in nx.all_simple_paths(self.G, repo, client):
                     
                              if len(member) == l:    
                                  for i in range(0, l-1): 

                                     self.node_list[member[i + 1]].add_route(self.node_list[member[i]], p[0])                               
    

            if lc > 1 and lr > 1:
                                                                                         
                for client, prefix in self.dict_client.items():

                    l = []

                    for repo , p in self.dict_repo.items():       
           
                        l.append(nx.shortest_path(self.G, client, repo))

                    v = min(l,key=len)
                    for i in range(0,len(v)-1):

                         self.node_list[v[i]].add_route(self.node_list[v[i+1]], p[0])   
                                                                       

        elif Algo_Name == 'MaxFlow':

            for client, prefix in self.dict_client.items():

                for repo, p in self.dict_repo.items():

                    flow_value, flow_dict = nx.maximum_flow(self.G, client, repo, capacity='capacity')
                    for k, v in flow_dict.items():
                        
                        for ki, vi in v.items():
                            if vi != 0:
                                self.node_list[k].add_route(self.node_list[ki], p[0]) 



        else:
            print('-----------------------------------------------------------------')
            print('You should choose the name of algorithm.')
            print('-----------------------------------------------------------------')

    def add_edge(self, n1, n2):
        """
        Add a link to topology

        :param n1: node1 of graph.
        :param n2: node2 of graph.
        :param b: bandwidth of link.
        :param c: cost of link.
        """

        self.G.add_edge(n1, n2)

    def delete_edge(self, n1, n2):

        """
        remove a linke from topology
        and list.

        :param n1: node1 of graph.
        :param n2: node2 of graph.
        """
        self.G.remove_edge(n1, n2)
