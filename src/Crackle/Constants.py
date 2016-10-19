"""
This module contains constant values useful for avoiding mistakes for dictionary keys and so on.
It contains the following constants values:

    - `__node_types__`: The types of node. It can be **AS_NODE, AS_BASE_STATION and AS_MOBILE_NODE**
    - `__mobility_model__`: The name of the mobility model. It can be **random_walk** or **random_waypoint**
    - `__cell_shapes__`: The allowed cell shape. It can be **circle**, **square** or **hexagon**

"""

__author__ = 'shahab'

__node_types__ = ["AS_NODE",
                  "AS_BASE_STATION",
                  "AS_MOBILE_NODE"]

__cell_shapes__ = ["circle", "square", "hexagon"]

## Routing algorithms
__tree_on_producer__ = 'TreeOnProducer'
__tree_on_consumer__ = 'TreeOnConsumer'
__min_cost_multipath__ = 'MinCostMultipath'
__maximum_flow__ = 'MaxFlow'

layer_2_protocols = ["udp", "udp4", "tcp", "tcp4", "ether"]  # websocket ?

lxd_client_cert_path = "../config/lxd_client_cert/client_cert.pem"
lxd_client_key_path = "../config/lxd_client_cert/client_key.pem"
ssh_client_private_key = "../config/ssh_client_cert/ssh_client_key"
ssh_client_public_key = "../config/ssh_client_cert/ssh_client_key.pub"

ns3_script_local = "../ns3-script/lxc-tap-wifi-emulation.cc"
nfd_conf_file = "../ns3-script/nfd.conf"

node_server_file = "/tmp/nsf.crackle"

LXD_BRIDGE = "br0"

router_vlan = 1
base_station_vlan = 2
mobile_station_vlan_start = 3

__operation_created__ = 100
__operation_started__ = 101
__operation_stopped__ = 102
__operation_running__ = 103
__operation_cancelling__ = 104
__operation_pending__ = 105
__operation_starting__ = 106
__operation_stopping__ = 107
__operation_aborting__ = 108
__operation_freezing__ = 109
__operation_frozen__ = 110
__operation_thawed__ = 111
__success_code__ = 200
__failure_code__ = 400
__canceled__ = 401

__response_type__ = "type"
__failure__ = "error"
__return__ = "return"
__success__ = "Success"
__running__ = "Running"
__async__ = "async"
__status__ = "status"
__status_code__ = "status_code"
__error_code__ = "error_code"
__metadata__ = "metadata"
__operation__ = "operation"
__fingerprint__ = "fingerprint"
__file_descriptor__ = "fds"

__header_X_LXD_uid__ = "X-LXD-uid"
__header_X_LXD_gid__ = "X-LXD-gid"
__header_X_LXD_mode__ = "X-LXD-mode"
__header_content_type__ = "content-type"

__API_VERSION__ = "1.0"
__CERTIFICATE__ = "/{0}/certificates".format(__API_VERSION__)
__CONTAINERS__ = "/{0}/containers".format(__API_VERSION__)
__CONTAINER__ = "/" + __API_VERSION__ + "/containers/{0}"
__EXEC__ = "/" + __API_VERSION__ + "/containers/{0}/exec"  # To complete with the container name
__PUSH__ = "/" + __API_VERSION__ + "/containers/{0}/files?path={1}"
__PULL__ = "/" + __API_VERSION__ + "/containers/{0}/files?path={1}"
__STATE__ = "/" + __API_VERSION__ + "/containers/{0}/state"
__IMAGES__ = "/{0}/images".format(__API_VERSION__)
__ALIAS__ = "/{0}/images/aliases".format(__API_VERSION__)
__OPERATION__ = "/" + __API_VERSION__ + "/operation/{0}"
