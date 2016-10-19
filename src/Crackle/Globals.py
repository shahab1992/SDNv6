# This file if empty because it is filled at runtime with the configuration written in the file
# settings.conf inside the folder containing the configuration files.

# In this way it is possible to entirely split the configuration from the software itself.

# global variables for the crackle project
test_folder = ""
username = ""
remote_log_dir = ""
scripts_dir = ""
log_dir = ""

# Global settings for the test
test_start_time = None
test_duration = None
chunk_size = None  # This is the size of one chunk (in Byte)
layer2_prot = None  # can be udp, tcp or ethernet

# Client Parameters

file_size_distribution = None
flow_control_gamma = None
flow_control_beta = None
flow_control_p_min = None
flow_control_p_max = None
flow_control_est_len = None
flow_control_timeout = None
fwd_alhpa_avg_pi = None
nfd_stats_interval = None

# WLDR Parameters

wldr_face = None

# Global Routing

global_routing = None

# Mobility Parameters

mobility_area_x_0 = None
mobility_area_x_max = None
mobility_area_y_0 = None
mobility_area_y_max = None

# Random Waypoint/Walk (for NS-3) Parameters
mobility_model = ""
min_pause = None  # Available just for random waypoint
max_pause = None  # Available just for random waypoint
min_speed = None
max_speed = None
# Routing Algorithm
routing_algorithm = ""

# Random Waypoint (for NS-3) Parameterssd
min_pause = None  # seconds
max_pause = None

# NS-3 script Location
home_folder = ""
ndnmobility = ""
ns3_folder = ""
ns3_conf_file_name = ""
ns3_script = ""

# Cluster configuration

image_server = ""
server_names = ""
interfaces = ""
ip_addresses = ""
lxd_password = ""
lxd_port = ""

router_base_image = ""

# Experiment ID for multiple experiments on a server

experiment_id = ""
