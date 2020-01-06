#!/usr/bin/env python3
################################################################################
"""post_client.py -- demo client script for hepia's LSDS IoT Z-Wave Lab

This script sends POST or GET HTTP requests to a REST server. POST requests
contain parameters in JSON format.

Usage:

    post_client.py [OPTIONS] CLASS COMMAND

See `post_client.py -h` for the details


REST command paths
==================

GET requests
------------

URL path:

    /<class>[/<node_id>]/<command>[/<parameter_index>]

where `node_id` and `parameter_index` must be specified via explicit CL
options, respectively `-n` and `-i`.


POST requests
-------------

URL path:

    /<class>/<command>

with JSON payload specified via the CL option `-d`.


Examples
========

Dump network topology:

    post_client.py network info


Switch to inclusion mode (20s timeout):

    post_client.py nodes add_node


Switch to exclusion mode (20s timeout):

    post_client.py nodes remove_node


Get dimmer level for a specific node (given as CL option `-n`):

    post_client.py dimmers get_level -n 5


Set dimmer level for a specific node (notice how the ID is specified in
the JSON payload):

    post_client.py dimmers set_level -d '{"node_id": 5, "value": 50}'


Get value for a generic parameter at index '111' for node '5':

    python3 post_client.py nodes get_parameter -n 5 -i 111


Set value for a generic parameter at index '111' for node '5':

    python3 post_client.py nodes set_parameter \
        -d '{"node_id": 5, "value": 480, "parameter_index": 111, "size": 4}'


Get all measures for a given node

    post_client.py sensors get_all_measures -n 2


Bugs
====

* At least CLASS and COMMAND must be given to get the script's manual with
  `-m`.

* Setting generic parameter doesn't seem to work properly: (the parameter is
  created if not existing,) it's value stays always at 0.
"""
################################################################################
import requests, argparse, json, sys, copy, logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s %(message)s'
)
logger = logging.getLogger('rest_client')


################################################################################
# constants

http_headers = {
    'Content-Type' : 'application/json'
}

# cross reference with default node ID, par index and data (where needed)
command_xref = {
    'network'   : {
        'get_nodes_configuration' : {
            'method' : 'GET',
        },
        'info' : {
            'method' : 'GET',
        },
        'reset' : { # possibly broken
            'method' : 'GET',
        },
        'set_sensor_nodes_basic_configuration' : {
            'method' : 'POST',
            'data'   : {
                'Group_Interval':       '240',
                'Group_Reports':        '240',
                'Wake-up_Interval':     '480'
            }
        },
        'start' : {
            'method' : 'GET',
        },
        'stop' : {
            'method' : 'GET',
        },
    },

    'nodes'     : {
        'add_node' : {
            'method' : 'POST',
        },
        'get_battery' : {
            'method'    : 'GET',
            'node_id'   : 1,
        },
        'get_location' : {
            'method'    : 'GET',
            'node_id'   : 1,
        },
        'get_name' : {
            'method'    : 'GET',
            'node_id'   : 1,
        },
        'get_neighbours' : {
            'method'    : 'GET',
            'node_id'   : 1,
        },
        'get_nodes_list' : {
            'method' : 'GET',
        },
        'get_parameter' : {
            'method'          : 'GET',
            'node_id'         : 1,
            'parameter_index' : 111,
        },
        'remove_node' : {
            'method' : 'POST',
        },
        'set_location' : {
            'method' : 'POST',
            'data'   : {
                'node_id' : '1',
                'value'   : 'A402'
            }
        },
        'set_name' : {
            'method' : 'POST',
            'data'   : {
                'node_id' : '4',
                'value'   : 'sensor'
            }
        },
        'set_parameter' : {
            'method' : 'POST',
            'data'   : {
                'node_id'               : '3',
                'value'                 : '480',
                'parameter_index'       : '111',
                'size'                  : '4'
            }
        }
    },
    'dimmers'   : {
        'get_dimmers_list' : {
            'method' : 'GET',
        },
        'get_level' : {
            'method'    : 'GET',
            'node_id'   : 1,
        },
        'set_level' : {
            'method' : 'POST',
            'data'   : {
                'node_id': '5',
                'value': '10'
            }
        }
    },
    'sensors'   : {
        'get_all_measures' : {
            'method'    : 'GET',
            'node_id'   : 2,
        },
        'get_humidity' : {
            'method'    : 'GET',
            'node_id'   : 2,
        },
        'get_luminance' : {
            'method'    : 'GET',
            'node_id'   : 2,
        },
        'get_motion' : {
            'method'    : 'GET',
            'node_id'   : 2,
        },
        'get_sensors_list' : {
            'method'    : 'GET',
        },
        'get_temperature' : {
            'method'    : 'GET',
            'node_id'   : 2,
        },
    },
}


################################################################################
# functions

def build_request_path(
        cclass, command, cmnd_s,
        node_id=None,
        parameter_index=None,
):
    """Build a request path.

    :returns str: a string like '/<class>[/<node_id>]/<command>[/<parameter>]'
                  or None on errors

    Arguments
    +++++++++

    :param str cclass: the resource/object class

    :param str command: the command name

    :param dict cmnd_s: the command spec dict as in `command_xref`

    Keywords arguments
    ++++++++++++++++++

    :param int node_id: the target node to query

    :param int parameter_index: the parameter index to query

    """
    if 'node_id' in cmnd_s.keys():
        node_id = node_id or cmnd_s['node_id']
    elif node_id:
        logger.error(
            "/{}/{}: unexepected 'node_id' ({}) for this request".format(
                cclass, command, node_id
            )
        )
        return None

    if 'parameter_index' in cmnd_s.keys():
        parameter_index = parameter_index or cmnd_s['parameter_index']
    elif parameter_index:
        logger.error(
            "/{}/{}: unexepected 'parameter_index' ({}) for this request".format(
                cclass, command, parameter_index
            )
        )
        return None

    return '/' + cclass + '/' \
        + (( str(node_id) + '/' ) if node_id != None else '') + command \
        + (( '/' + str(parameter_index) ) if parameter_index != None else '')


################################################################################
# main

parser = argparse.ArgumentParser(
    description='Demo client for REST-based Z-Wave deployments -- hepia/LSDS Smart-Building',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)

parser.add_argument(
    '-m', '--manual',
    dest='manual',
    action='store_true',
    help='print the full documentation'
)

parser.add_argument(
    '-u', '--server-url',
    dest='server_url',
    type=str,
    default='http://192.168.1.2',
    help='REST server URL'
)

parser.add_argument(
    '-p', '--server-port',
    dest='server_port',
    type=int,
    default=5000,
    help='REST server PORT'
)

parser.add_argument(
    '-n', '--node-id',
    dest='node_id',
    type=int,
    help='Node ID'
)

parser.add_argument(
    '-d', '--data',
    dest='data',
    type=str,
    help='JSON payload string for POST requests'
)

parser.add_argument(
    '-i', '--parameter-index',
    dest='parameter_index',
    type=int,
    help='Parameter index'
)

parser.add_argument(
    'class',
    # no metavar, else choices won't be proposed on -h
    type=str,
    choices=('network', 'nodes', 'dimmers', 'sensors'),
    help='Device/object class'
)

parser.add_argument(
    'command',
    type=str,
    choices=(
        # network
        'get_nodes_configuration',
        'info',
        'reset',
        'set_sensor_nodes_basic_configuration',
        'start',
        'stop',

        # nodes
        'add_node',
        'get_battery',
        'get_location',
        'get_name',
        'get_neighbours',
        'get_nodes_list',
        'get_parameter',
        'remove_node',
        'set_location',
        'set_name',
        'set_parameter',

        # dimmers
        'get_dimmers_list',
        'get_level',
        'set_level',

        # sensors
        'get_all_measures',
        'get_humidity',
        'get_luminance',
        'get_motion',
        'get_sensors_list',
        'get_temperature'
    ),
    help='Command to send'
)

 # easier with a dict
args = vars(parser.parse_args())

if args['manual']:
    print(__doc__)
    sys.exit(0)

cclass = args['class']
command = args['command']
data = {}
if args['data']:
    try:
        data = json.loads(args['data'])
    except Exception as e:
        logger.error("{}: invalid JSON data: {}".format(args['data'], e))
        sys.exit(1)

cmnd_s = {}
try:
    cmnd_s = command_xref[cclass][command]
except KeyError:
    parser.print_help()
    logger.error("{}: {}: no such command available for this class".format(cclass, command))
    sys.exit(1)

base_url = "{}:{}".format(args['server_url'], args['server_port'])

command_path = build_request_path(
    cclass, command, cmnd_s,
    node_id=args['node_id'],
    parameter_index=args['parameter_index']
)

if not command_path:
    logger.fatal("Can't build command path")
    sys.exit(1)

method = cmnd_s['method']
if 'data' in cmnd_s.keys():
    data = data or cmnd_s['data']
elif data:
    sys.exit("{}: unexpected data for command path".format(command_path))

logger.info("Sending {} request path: '{}'".format(method, command_path))
if data:
    logger.info("With payload: '{}'".format(data))

req = requests.request(
    method, base_url + command_path,
    headers=http_headers,
    data=json.dumps(data)
)

print("Server response:\n[{}] {}".format(req.status_code, req.text))
sys.exit(0)
