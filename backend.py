#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import logging
import configpi

from louie import dispatcher
from datetime import datetime
from flask import jsonify
from collections import OrderedDict

from openzwave.network import ZWaveNetwork
from openzwave.option import ZWaveOption

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('openzwave')

started = False
name = configpi.name


# #########    Root parent backend class     ##############


class Backend():

    def __init__(self):

        # ##################  instanciation de l'objet backend ############################
        # ##### options needed for python openzwave library like config files path, logging,
        device = configpi.interface
        options = ZWaveOption(device, config_path="/home/pi/IoTLab/python-openzwave/openzwave/config", user_path=".",
                              cmd_line="")
        options.set_log_file("OZW.log")
        options.set_append_log_file(False)
        options.set_console_output(False)
        options.set_save_log_level('Warning')
        options.set_logging(True)
        options.lock()

        # creation of the object network using the options entity already created
        self.network = ZWaveNetwork(options, autostart=False)

        # ##### 	 These dispatchers associate a method to a signal. the signals are generated by the library
        # python-openzwave. #####   Once the signal is received. It's associated method is executed (see
        # "_node_added" example below in "_network_started" method)
        dispatcher.connect(self._network_started, ZWaveNetwork.SIGNAL_NETWORK_STARTED)
        dispatcher.connect(self._network_ready, ZWaveNetwork.SIGNAL_NETWORK_READY)

        # ##### backend object attributes
        #        self.devices = OrderedDict()  ### will contain the list of nodes in the network
        #        self.sensors = OrderedDict()  ### will contain the list of sensors (only) in the network
        self.node_added = False
        self.node_removed = False
        self.timestamps = {}  # ## will contain the time of the last values' update for each sensor
        self.queryStages = {  # ## the diffrent stages that a node object gets through before being ready
            "None": 1,  # Query process hasn't started for this node
            "ProtocolInfo": 2,  # Retrieve protocol information
            "Probe": 3,  # Ping device to see if alive
            "WakeUp": 4,  # Start wake up process if a sleeping node
            "ManufacturerSpecific1": 5,  # Retrieve manufacturer name and product ids if ProtocolInfo lets us
            "NodeInfo": 6,  # Retrieve info about supported, controlled command classes
            "SecurityReport": 7,  # Retrieve a list of Command Classes that require Security
            "ManufacturerSpecific2": 8,  # Retrieve manufacturer name and product ids
            "Versions": 9,  # Retrieve version information
            "Instances": 10,  # Retrieve information about multiple command class instances
            "Static": 11,  # Retrieve static information (doesn't change)
            "Probe1": 12,  # Ping a device upon starting with configuration
            "Associations": 13,  # Retrieve information about associations
            "Neighbors": 14,  # Retrieve node neighbor list
            "Session": 15,  # Retrieve session information (changes infrequently)
            "Dynamic": 16,  # Retrieve dynamic information (changes frequently)
            "Configuration": 17,  # Retrieve configurable parameter information (only done on request)
            "Complete": 18  # Query process is completed for this node
        }

    # #####################################################################################################
    # ############ LAUNCH  ################################################################################
    # #####################################################################################################

    def _network_started(self, network):

        # executed once the software representation is started. the discovery of the network components has begun.
        # they will be mapped into objects

        print("network started - %d nodes were found." % network.nodes_count)

        # these dispatchers associate a method to a signal. the signals are generated by the library
        # python-openzwave. a signal may contain a number of parameters that are passed to the method associated to
        # the signal. for exemple, the dispatcher below associates the signal "SIGNAL_NODE_ADDED" to the method
        # "_node_added" that is implemented below (line 111). the signal "SIGNAL_NODE_ADDED" transports two
        # parameters which are the objects network and node. once this signal is received, these two parameters will
        # be passed to the method "_node_added" and the method will be executed.

        dispatcher.connect(self._node_added, ZWaveNetwork.SIGNAL_NODE_ADDED)
        dispatcher.connect(self._node_removed, ZWaveNetwork.SIGNAL_NODE_REMOVED)

    def _network_ready(self, network):

        # executed once the software representation is ready

        print("network : ready : %d nodes were found." % network.nodes_count)
        print("network : controller is : %s" % network.controller)
        dispatcher.connect(self._value_update, ZWaveNetwork.SIGNAL_VALUE)

    def _node_added(self, network, node):

        # executed when node is added to the software representation. it's executed after the method
        # "_debug_node_new" (see below)

        print('node added: %s.' % node.node_id)
        self.timestamps["timestamp" + str(node.node_id)] = "None"
        self.node_added = True

    def _node_removed(self, network, node):

        # executed when node is removed from the software representation

        print('node removed: %s.' % node.name)
        self.node_removed = True

    def _value_update(self, network, node, value):

        # executed when a new value from a node is received

        print('Node %s: value update: %s is %s.' % (node.node_id, value.label, value.data))
        self.timestamps["timestamp" + str(node.node_id)] = int(time.time())

    ################################################################################################################
    # ################# START AND STOP THE SOFTWARE REPRESENTATION #################################################
    ################################################################################################################

    def start(self):

        # this method starts the software representation
        global started

        if started:
            print "Already started"
            return
        started = True
        self.network.start()
        print "Z-Wave Network Starting..."
        for i in range(0, 300):
            if self.network.state == self.network.STATE_READY:
                break
            else:
                time.sleep(1.0)
        if not self.network.is_ready:
            print "Network is not ready but continue anyway"
        print "------------------------------------------------------------"
        print "Nodes in network : %s" % self.network.nodes_count
        print "------------------------------------------------------------"

    def stop(self):

        # this method stops the software representation

        global started
        started = False
        print "Stopping Z-Wave Network... "
        self.network.stop()

    def reset(self):
        if self.network.nodes_count == 1:
            self.network.controller.hard_reset()
            return "Hard Reset Done"
        return "Cannot make Hard Reset while nodes included in network"

    # ###############################################################################################################
    # ############ NETWORK ##########################################################################################
    # ###############################################################################################################

    def network_info(self):

        #### COMPLETE THIS METHOD ##############

        return "this method returns a JSON that lists all network nodes and gives some informations about each one of them like the ID, neighbors, ..."

    # ###############################################################################################################
    # ############ NODES ############################################################################################
    # ###############################################################################################################

    def ordered_nodes_dict(self):

        # returns an ordered list of the network's nodes sorted by node's id

        return OrderedDict(sorted(self.network.nodes.items()))

    def addNode(self):

        #### COMPLETE THIS METHOD ##############

        return "this method passes the controller to inclusion mode and gets it out of it after 20 seconds "

    def removeNode(self):

        #### COMPLETE THIS METHOD ##############

        return "this method passes the controller to exclusion mode and gets it out of it after 20 seconds "

    def get_nodes_list(self):  # Jonathan
        l = {}
        for node in self.network.nodes.itervalues():
            l[node.node_id] = node.name
        return jsonify(l)

    def set_node_location(self, n, value):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady:
                node.location = value
                return jsonify(location=value)
        return "Node not ready or wrong sensor node !"

    def set_node_name(self, n, value):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady:
                node.name = value
                return jsonify(name=value)
        return "Node not ready or wrong sensor node !"

    def get_node_location(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady:
                return jsonify(name=node.location)
        return "Node not ready or wrong sensor node !"

    def get_node_name(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady:
                return jsonify(name=node.name)
        return "Node not ready or wrong sensor node !"

    def get_neighbours_list(self, n):

        #### COMPLETE THIS METHOD ##############

        return "this method gets the list of neighbours of a specific sensor node"

    def set_node_config_parameter(self, n, param, value, size):

        #### COMPLETE THIS METHOD ##############

        return "this method sets a configuration parameter to a given value"

    def get_node_config_parameter(self, n, param):

        #### COMPLETE THIS METHOD ##############

        return "this method gets the value of a configuration parameter"

    def get_nodes_Configuration(self):

        #### COMPLETE THIS METHOD ##############

        return "this method returns a JSON that gives an overview of the network and it's nodes' configuration parameters (like the ID, Wake-up Interval, Group 1 Reports, Group 1 Interval ...)"


# ####################################################################################################################
# ############ Multisensors ##########################################################################################
# ####################################################################################################################

class Backend_with_sensors(Backend):

    def get_sensors_list(self): # Adam TODO test
        l = {}
        for node in self.network.nodes.itervalues():
            if node.node_id != 1:
                l[node.node_id] = node.name
        return jsonify(l)

    def get_temperature(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp" + str(node.node_id) in self.timestamps:
                values = node.get_values(0x31, "User", "All", True, False)
                for value in values.itervalues():
                    if value.label == "Temperature":
                        val = round(value.data, 1)
                        #        if len(node.location) < 3:
                        #            node.location = configpi.sensors[str(node.node_id)][:4]
                        return jsonify(controller=name, sensor=node.node_id, location=node.location,
                                       type=value.label.lower(),
                                       updateTime=self.timestamps["timestamp" + str(node.node_id)], value=val)
        return "Node not ready or wrong sensor node !"

    def get_humidity(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp" + str(node.node_id) in self.timestamps:
                values = node.get_values(0x31, "User", "All", True, False)
                for value in values.itervalues():
                    if value.label == "Relative Humidity":
                        val = int(value.data)
                        #       if len(node.location) < 3:
                        #           node.location = configpi.sensors[str(node.node_id)][:4]
                        return jsonify(controller=name, sensor=node.node_id, location=node.location,
                                       type=value.label.lower(),
                                       updateTime=self.timestamps["timestamp" + str(node.node_id)], value=val)
        return "Node not ready or wrong sensor node !"

    def get_luminance(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp" + str(node.node_id) in self.timestamps:
                values = node.get_values(0x31, "User", "All", True, False)
                for value in values.itervalues():
                    if value.label == "Luminance":
                        val = int(value.data)
                        return jsonify(controller=name, sensor=node.node_id, location=node.location,
                                       type=value.label.lower(),
                                       updateTime=self.timestamps["timestamp" + str(node.node_id)], value=val)
        return "Node not ready or wrong sensor node !"

    def get_motion(self, n):    # Adam TODO test
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp" + str(node.node_id) in self.timestamps:
                values = node.get_values("All", "User", "All", True, False)
                for value in values.itervalues():
                    if value.label == "Sensor":
                        val = bool(value.data)
                        return jsonify(controller=name, sensor=node.node_id, location=node.location,
                                       type=value.label.lower(),
                                       updateTime=self.timestamps["timestamp" + str(node.node_id)], value=val)
        return "Node not ready or wrong sensor node ! --"

    def get_battery(self, n): # Adam TODO test
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp" + str(node.node_id) in self.timestamps:
                values = node.get_values("All", "User", "All", True, False)
                for value in values.itervalues():
                    if value.label == "Battery Level":
                        val = int(value.data)
                        return jsonify(controller=name, sensor=node.node_id, location=node.location,
                                       type=value.label.lower(),
                                       updateTime=self.timestamps["timestamp" + str(node.node_id)], value=val)
        return "Node not ready or wrong sensor node !"

    def get_all_Measures(self, n):  # Adam, I realise this could be so much more efficient
                                    # All the more reason for TODO test
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp" + str(node.node_id) in self.timestamps:
                values = node.get_values("All", "User", "All", True, False)
                bat = 0
                hum = 0
                lum = 0
                temp = 0
                mot = 0
                for value in values.itervalues():
                    if value.label == "Battery Level":
                        bat = int(value.data)
                    elif value.label == "Relative Humidity":
                        hum = int(value.data)
                    elif value.label == "Luminance":
                        lum = int(value.data)
                    elif value.label == "Temperature":
                        temp = int(value.data)
                    elif value.label == "Sensor":
                        mot = bool(value.data)

                return jsonify(controller=name, sensor=node.node_id, location=node.location,
                                battery=bat, humidity=hum,
                                luminance=lum, temperature=temp,
                                motion=mot, updateTime=self.timestamps["timestamp" + str(node.node_id)])
        return "Node not ready or wrong sensor node !"

    def set_basic_sensor_nodes_configuration(self, Grp_interval, Grp_reports, Wakeup_interval):

        #### COMPLETE THIS METHOD ##############

        return "this method configures the sensor nodes with a specific configuration"


###########################################################################################################################
###########################################################################################################################
##################    Dimmers class     ##################################################################################
###########################################################################################################################
###########################################################################################################################

class Backend_with_dimmers(Backend):

    def __init__(self):
        Backend.__init__(self)

    def get_dimmers(self):
        l = {}
        for node in self.network.nodes.itervalues():
            if node.node_id != 1:
                l[node.node_id] = node.name
        return jsonify(l)

    def get_dimmer_level(self, n): # Adam, really not sure of this one ...
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp" + str(node.node_id) in self.timestamps:
                values = node.get_values()
                for value in values.itervalues():
                    if value.label == "Level":
                        val = int(value.data)
                        return jsonify(controller=name, dimmer=node.node_id, location=node.location,
                                       type=value.label.lower(),
                                       updateTime=self.timestamps["timestamp" + str(node.node_id)], value=val)
        return "Node not ready or wrong dimmer node !"

    def set_dimmer_level(self, n, level):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp" + str(node.node_id) in self.timestamps:
                values = node.get_values()
                for value in values.itervalues():
                    if value.label == "Level":
                        value.data = level
                    return "Value has been changed"
        return "Node not ready or wrong dimmer node !"


###########################################################################################################################
###########################################################################################################################
##########    Dimmers and multisensors class         ######################################## #############################
###########################################################################################################################
###########################################################################################################################

class Backend_with_dimmers_and_sensors(Backend_with_dimmers,
                                       Backend_with_sensors):  # Cette classe sera utilise dans "flask-main"

    pass
