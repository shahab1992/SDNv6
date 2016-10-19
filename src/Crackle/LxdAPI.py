"""
This class manages the interaction with the LXD daemon through REST APIs and websockets.

"""
import logging
import ssl
import urllib
from websocket import WebSocket

import requests
import requests.exceptions as req_except

from Crackle import Globals
from Crackle import Constants

module_logger = logging.getLogger(__name__)
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

default_container = {

    "name": "router-container-base",                  # 64 chars max, ASCII, no slash, no colon and no comma
    "architecture": "x86_64",
    "profiles": ["default"],                          # List of profiles
    "ephemeral": True,                                # Whether to destroy the container on shutdown
    "config": {"limits.cpu": "4"},                    # Config override.
    "source": {"type": "image",                       # Can be: "image", "migration", "copy" or "none"
               "mode": "pull",                        # One of "local" (default) or "pull"
               "server": "https://cloud-images.ubuntu.com/releases/",     # Remote server (pull mode only)
               "protocol": "simplestreams",                     # Protocol (one of lxd or simplestreams, defaults to lxd)
               "alias": "trusty"}                     # Name of the alias

}

default_file_modes = {
       Constants.__header_X_LXD_gid__: "0",
       Constants.__header_X_LXD_uid__: "0",
       Constants.__header_X_LXD_mode__: "700"
}

default_publish_description = {

    "public":   True,         # Whether the image can be downloaded by untrusted users  (defaults to false)
    "properties": {           # Image properties (optional)
        "os": "Ubuntu",
        "architecture": "x86_64"
    },
    "source": {
        "type": "container",  # One of "container" or "snapshot"
        "name": "icn-router-image"
    }
}


def stop_container(server="", container="", async=False):

    url_prefix = "{0}{1}{2}{3}".format("https://",
                                       server,
                                       ":",
                                       Globals.lxd_port)

    url = "{0}{1}".format(url_prefix,
                          Constants.__STATE__.format(container))

    state_json = {
        "action": "stop",       # State change action (stop, start, restart, freeze or unfreeze)
        "timeout": 30,          # A timeout after which the state change is considered as failed
    }

    try:
        resp = requests.put(url=url,
                            json=state_json,
                            cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                            verify=False)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("Error stopping container {0}. "
                            "Error: {1}".format(container,
                                                http_error.strerror))
        raise RuntimeError

    response = resp.json()

    if response[Constants.__response_type__] == Constants.__failure__:
        module_logger.error("[{0}]Error stopping container on server {1}. "
                            "Error code: {2}".format(response[container,
                                                              server,
                                                              Constants.__error_code__]))
        raise RuntimeError
    elif response[Constants.__response_type__] == Constants.__async__:
        module_logger.debug("[{0}] Container stopped on {1}. Details: {2}".format(container,
                                                                                  server,
                                                                                  response[Constants.__metadata__]))
    if not async:
        operation_url = "{0}{1}".format(url_prefix,
                                        response[Constants.__operation__])

        try:
            resp = requests.get(url=operation_url + "/wait?timeout=30",
                                cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                                verify=False)
            resp.raise_for_status()
        except req_except.HTTPError as http_error:
            module_logger.error("[{0}] Error stopping the container. Error: {1}".format(container, http_error.strerror))
            raise RuntimeError

        result = resp.json()[Constants.__status__]

        if result != Constants.__success__:
            module_logger.error("[{0}] Impossible to stop the container.".format(container))
            raise RuntimeError
        else:
            module_logger.debug("[{0}] Container successfully stopped".format(container))


def start_container(server="", container=""):

    url_prefix = "{0}{1}{2}{3}".format("https://",
                                       server,
                                       ":",
                                       Globals.lxd_port)

    url = "{0}{1}".format(url_prefix,
                          Constants.__STATE__.format(container))

    state_json = {
        "action": "start",       # State change action (stop, start, restart, freeze or unfreeze)
        "timeout": 30,           # A timeout after which the state change is considered as failed
    }

    try:
        resp = requests.put(url=url,
                            json=state_json,
                            cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                            verify=False)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("Error starting container {0}. "
                            "Error: {1}".format(container,
                                                http_error.strerror))
        raise RuntimeError

    response = resp.json()

    if response[Constants.__response_type__] == Constants.__failure__:
        module_logger.error("[{0}]Error starting container on server {1}. "
                            "Error code: {2}".format(response[container,
                                                              server,
                                                              Constants.__error_code__]))
        raise RuntimeError
    elif response[Constants.__response_type__] == Constants.__async__:
        module_logger.debug("[{0}] Container starting on {1}. Details: {2}".format(container,
                                                                                   server,
                                                                                   response[Constants.__metadata__]))

    operation_url = "{0}{1}".format(url_prefix,
                                    response[Constants.__operation__])

    try:
        resp = requests.get(url=operation_url + "/wait?timeout=30",
                            cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                            verify=False)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("[{0}] Error starting the container. Error: {1}".format(container, http_error.strerror))
        raise RuntimeError

    result = resp.json()[Constants.__status__]

    if result != Constants.__success__:
        module_logger.error("[{0}] Impossible to start the container.".format(container))
        raise RuntimeError
    else:
        module_logger.debug("[{0}] Container successfully started".format(container))


def create_container(description=default_container,
                     server="",
                     error_message="Error creating the container.",
                     success_message="Container successfully created"):

    if server == "":
        module_logger.error("Server on which starting the container not specified.")
        raise RuntimeError

    url_prefix = "{0}{1}{2}{3}".format("https://",
                                       server,
                                       ":",
                                       Globals.lxd_port)

    url = "{0}{1}".format(url_prefix,
                          Constants.__CONTAINERS__)

    # Create the container on the server

    try:
        resp = requests.post(url=url,
                             json=description,
                             cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                             verify=False)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:

        module_logger.error("Error creating the router base image. Error: {0}".format(http_error.strerror))
        raise RuntimeError

    response = resp.json()
    if response[Constants.__response_type__] == Constants.__failure__:
        module_logger.error("{0} Error code: {1}. Return Message = {2}".format(error_message,
                                                                               response[Constants.__error_code__],
                                                                               response))
        raise RuntimeError
    elif response[Constants.__response_type__] == Constants.__async__:
        module_logger.debug("Container creation started on {0}. Details: {1}".format(server,
                                                                                     response[Constants.__metadata__]))
    # Wait the operation end

    operation_url = "{0}{1}".format(url_prefix,
                                    response[Constants.__operation__])

    # Wait for container creation

    try:
        resp = requests.get(url=operation_url + "/wait?timeout=60",
                            cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                            verify=False)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("{0}. Error: {1}".format(error_message, http_error.strerror))
        raise RuntimeError

    result = resp.json()[Constants.__metadata__][Constants.__status__]
    if result != Constants.__success__:
        module_logger.error("[{0}] {1}. Response: {2}".format(description["name"], error_message, resp.json()))
        raise RuntimeError
    else:
        module_logger.debug("[{0}] {1}. Response: {2}".format(description["name"], success_message, resp.json()))


def push_file(server="", container="", source_path="", destination_path="", mode=default_file_modes):

    url_prefix = "{0}{1}{2}{3}".format("https://",
                                       server,
                                       ":",
                                       Globals.lxd_port)

    url = "{0}{1}".format(url_prefix,
                          Constants.__PUSH__.format(container,
                                                    destination_path))

    file = open(source_path, "rb")

    headers = mode.copy()
    headers[Constants.__header_content_type__] = "application/octet-stream"

    try:
        resp = requests.post(url=url,
                             cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                             verify=False,
                             headers=headers,
                             data=file)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("Error pushing file {0}. "
                            "Error: {1}".format(source_path,
                                                http_error.strerror))
        raise RuntimeError

    result = resp.json()[Constants.__status__]

    if result == Constants.__success__:
        module_logger.debug("File {0} correctly pushed on base container.".format(source_path))
    else:
        module_logger.error("Error pushing file {0} on container {1}.".format(source_path,
                                                                              container))
        raise RuntimeError


def pull_file(server="", container="", source_path="", destination_path="", mode=default_file_modes):

    url_prefix = "{0}{1}{2}{3}".format("https://",
                                       server,
                                       ":",
                                       Globals.lxd_port)

    url = "{0}{1}".format(url_prefix,
                          Constants.__PULL__.format(container,
                                                    source_path))

    try:
        resp = requests.get(url=url,
                            cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                            verify=False,
                            stream=True)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("Error pulling file {0}. "
                            "Error: {1}".format(source_path,
                                                http_error.strerror))
        raise RuntimeError

    with open(destination_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=2048):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)


def publish_image(server="",
                  publish_description=default_publish_description):

    url_prefix = "{0}{1}{2}{3}".format("https://",
                                       server,
                                       ":",
                                       Globals.lxd_port)

    url = "{0}{1}".format(url_prefix,
                          Constants.__IMAGES__)

    try:
        resp = requests.post(url=url,
                             cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                             verify=False,
                             json=publish_description)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("Error publishing image {on 0}. "
                            "Error: {1}".format(server,
                                                http_error.strerror))
        raise RuntimeError

    response = resp.json()

    result = response[Constants.__status_code__]
    command_status = response[Constants.__metadata__][Constants.__status_code__]

    if result != Constants.__operation_created__ or command_status != Constants.__operation_running__:
        module_logger.error("Impossible to publish the image on {0}. Info: {1}".format(server,
                                                                                       response))
        raise RuntimeError

    # Wait the operation end

    operation_url = "{0}{1}".format(url_prefix,
                                    response[Constants.__operation__])

    # Wait for image creation

    try:
        resp = requests.get(url=operation_url + "/wait",
                            cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                            verify=False)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("[{0}] Error publishing image. Error: {1}".format(server,
                                                                              http_error.strerror))
        raise RuntimeError

    result = resp.json()[Constants.__status__]

    if result != Constants.__success__:
        module_logger.error("[{0}] Image creation failed. Response: {1}".format(server,
                                                                                resp.json()))
        raise RuntimeError
    else:
        module_logger.debug("[{0}] Image creation succeed. {1}".format(server,
                                                                       resp.json()))

    return resp.json()[Constants.__metadata__][Constants.__metadata__][Constants.__fingerprint__]


def set_alias(server="", image_fingerprint="", alias=""):

    url_prefix = "{0}{1}{2}{3}".format("https://",
                                       server,
                                       ":",
                                       Globals.lxd_port)

    url = "{0}{1}".format(url_prefix,
                          Constants.__ALIAS__)

    alias_dict = {

        "description": "Ubuntu 14.04 image with ICN software already installed",
        "target": image_fingerprint,
        "name": alias
    }

    try:
        resp = requests.post(url=url,
                             json=alias_dict,
                             cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                             verify=False)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("Error setting alias for router image on {0}. Error: {1}".format(server,
                                                                                             http_error.strerror))
        raise RuntimeError


def delete_container(server="", container=""):

    url_prefix = "{0}{1}{2}{3}".format("https://",
                                       server,
                                       ":",
                                       Globals.lxd_port)

    url = "{0}{1}".format(url_prefix,
                          Constants.__CONTAINER__.format(container))

    delete_command = {}

    try:
        resp = requests.delete(url=url,
                               json=delete_command,
                               cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                               verify=False)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("[{0}] Error deleting container. "
                            "Error: {1}".format(container, http_error.strerror))
        raise RuntimeError


def list_images(server=""):

    url_prefix = "{0}{1}{2}{3}".format("https://",
                                       server,
                                       ":",
                                       Globals.lxd_port)

    url = "{0}{1}".format(url_prefix,
                          Constants.__ALIAS__)

    try:
        resp = requests.get(url=url,
                            cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                            verify=False)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("Error listing alias of {0}. Error: {1}".format(server,
                                                                            http_error.strerror))
        raise RuntimeError

    return resp.json()[Constants.__metadata__]


def exec_cmd(server="", container="", cmd=[],
             environment={}, interactive=False,
             output=False, websocket=False,
             check_return=True, sync=True):

    command_json = {
        "command": cmd,
        "environment": environment
    }

    url_prefix = "{0}{1}{2}{3}".format("https://",
                                       server,
                                       ":",
                                       Globals.lxd_port)

    if interactive:
        command_json["interactive"] = True
    else:
        command_json["interactive"] = False

    if websocket:
        command_json["wait-for-websocket"] = True
    else:
        command_json["wait-for-websocket"] = False

    url = "{0}{1}".format(url_prefix,
                          Constants.__EXEC__.format(container))

    try:
        resp = requests.post(url=url,
                             json=command_json,
                             cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                             verify=False)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("[{0}] Error executing command {1}. "
                            "Error: {0}".format(container, cmd, http_error.strerror))
        raise RuntimeError

    response = resp.json()

    result = response[Constants.__status_code__]
    command_status = response[Constants.__metadata__][Constants.__status_code__]

    if result != Constants.__operation_created__ or command_status != Constants.__operation_running__:
        module_logger.error("[{0}] Impossible to start the command {1}. Info: {2}".format(container,
                                                                                          cmd,
                                                                                          response))
        raise RuntimeError

    operation_url = "{0}{1}".format(url_prefix,
                                    response[Constants.__operation__])

    if sync:

        # Wait the operation end

        if websocket:
            # Read from websocket
            op = response['operation']
            fds = response['metadata']['metadata']['fds']
            sockets = {}

            stdout, stdin, stderr = '1', '0', '2'

            for fd in [stdin, stdout, stderr]:
                secret = urllib.parse.urlencode({'secret': fds[fd]})
                wsurl = "wss://{0}{1}/websocket?{2}".format("{0}:{1}".format(server, Globals.lxd_port),
                                                            op,
                                                            secret)
                ws = WebSocket(
                    sslopt={"keyfile": Constants.lxd_client_key_path,
                            "certfile": Constants.lxd_client_cert_path,
                            "cert_reqs": ssl.CERT_NONE})
                ws.connect(wsurl)
                sockets[fd] = ws

            # stdout = 1, stderr = 2
            buffer = sockets[stdout].recv()
            while output and buffer:
                print(buffer.decode(), end="", flush=True)
                buffer = sockets[stdout].recv()


        try:
            response = requests.get(url=operation_url + "/wait",
                                cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                                verify=False)
            # if response.status_code != 404:
            #     response.raise_for_status()
            # else:
            #     return
        except req_except.HTTPError as http_error:
            module_logger.error("[{0}] Error executing CMD {1}. Error: {2}. Status: {3}".format(container,
                                                                                                cmd,
                                                                                                http_error.strerror,
                                                                                                response.status_code))
            raise RuntimeError

        result = response.json()[Constants.__status__]
        status_code = int(response.json()[Constants.__metadata__][Constants.__metadata__][Constants.__return__])

        if result != Constants.__success__ or (status_code and check_return):
            module_logger.error("[{0}] Command {1} failed, returning {2}".format(container,
                                                                                 cmd,
                                                                                 status_code))
            raise RuntimeError
        else:
            module_logger.debug("[{0}] Command {1} executed successfully. Response: {2}".format(container,
                                                                                                cmd,
                                                                                                resp.json()))


def get_container_status(server="", name=""):
    """
    Query the LXD daemon to retrieve the status of the container

    :param server: The server on which the container is running
    :param name: The name of the container
    :return: The container status
    """

    url_prefix = "{0}{1}{2}{3}".format("https://",
                                       server,
                                       ":",
                                       Globals.lxd_port)

    url = "{0}{1}".format(url_prefix,
                          Constants.__STATE__.format(name))

    try:
        resp = requests.get(url=url,
                            cert=(Constants.lxd_client_cert_path, Constants.lxd_client_key_path),
                            verify=False)
        resp.raise_for_status()
    except req_except.HTTPError as http_error:
        module_logger.error("[{0}] Error retrieving status of {1}. Error: {2}".format(server,
                                                                                      name,
                                                                                      http_error.strerror))
        raise RuntimeError

    return resp.json()
