from paho.mqtt import client as mqtt
import ssl
from backend import *
from threading import Timer
import json

class MqttZwaveDispatcher:

    def __init__(self):
        self.room_temp = 0
        self.room_humidity = 0
        self.sensor_battery = 0
        self.room_luminance = 0
        self.room_uv = 0

        self.path_to_root_cert = "digicert.cer"

        self.true_device_id = "ZWave-Gateway"
        self.true_sas_token = "SharedAccessSignature sr=IoT-Hub-MSE.azure-devices.net%2Fdevices%2FZWave-Gateway&sig=mu%2Fhgeaol%2Bs6mLFdl8G06CBocUeeRqx06g77hzvQBFU%3D&se=1580847387"

        self.iot_hub_name = "IoT-Hub-MSE"

        # Setup backend
        self.backend = Backend_with_dimmers_and_sensors()
    
        self.client = mqtt.Client(client_id=self.true_device_id, protocol=mqtt.MQTTv311)

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe

        self.client.username_pw_set(username=self.iot_hub_name +".azure-devices.net/" +
                                self.true_device_id + "/?api-version=2018-06-30", password=self.true_sas_token)

        self.client.tls_set(ca_certs=self.path_to_root_cert, certfile=None, keyfile=None,
                       cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
        self.client.tls_insecure_set(False)

        self.client.connect(self.iot_hub_name+".azure-devices.net", port=8883)

        # Line added to subscribe to a topic, we're gonna run two devices that communicate to each other
        self.client.subscribe("devices/" + self.true_device_id + "/messages/devicebound/#", 0)

        # Add zwave listener
        self.backend.addListener(self.listen_to_zwave)

        # Add timer for polling data
        self.t = Timer(30.0, self.get_sensor)

    def on_connect(self, client, userdata, flags, rc):
        print("Device connected with result code: " + str(rc))


    def on_disconnect(self, client, userdata, rc):
        print("Device disconnected with result code: " + str(rc))


    def on_publish(self, client, userdata, mid):
        print("Device sent message")

    def on_message(self, mosq, obj, msg):
        print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

        dimmer_value = 0
        json_data = json.loads(msg.payload)

        print('topic : '+json_data['topic'])
        print('value : '+str(json_data['value']))

        # If the given topic is light - for this device
        if json_data['topic'] == 'light':
            dimmer_value = json_data['value']

            # Limit dimmer between 0 and 100
            if dimmer_value > 99:
                dimmer_value = 99
            elif dimmer_value < 0:
                dimmer_value = 0

            print(self.backend.set_dimmer_level(6, dimmer_value))


    def on_subscribe(self, mosq, obj, mid, granted_qos):
        print("Subscribed: " + str(mid) + " " + str(granted_qos))

    def listen_to_zwave(self, network, node, value):

        # executed when a new value from a node is received
        # payload = 'Node %s: value update: %s is %s.' % (node.node_id, value.label, value.data)

        payload = ""

        # Check if the zwave essage is from the sensor
        if int(node.node_id) == 4:
            if value.label == "Alarm Level":
                payload = '{ "topic":"alarm" }'
                print(payload)
                self.client.publish("devices/" + self.true_device_id + "/messages/events/", payload, qos=1)

    def get_sensor(self):
        try:
            back_measures = self.backend.get_all_Measures(4)
            print (back_measures)
            my_json = json.loads(back_measures)

            payload = '{ "topic":"sensor", "id":%s, "humidity":%f, "temperature":%f, "luminance":%f, "motion":%s }' % (my_json['controller'], my_json['humidity'], my_json['temperature'], my_json['luminance'], str(my_json['motion']).lower())

            self.client.publish("devices/" + self.true_device_id + "/messages/events/", payload, qos=1)
#            self.t.start()
        except ValueError:
            print("Oh no boy! :(")

    def start_mqtt_dispatcher(self):
        try:
            self.backend.start()
            #    print(self.backend.get_nodes_list())
            print(self.backend.set_dimmer_level(6, 0))
            self.t.start() # after 30 seconds, "hello, world" will be printed
            self.client.loop_forever()
        except KeyboardInterrupt:
            self.backend.stop()


mqtt_boy = MqttZwaveDispatcher()
mqtt_boy.start_mqtt_dispatcher()
