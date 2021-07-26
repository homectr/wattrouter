#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt
import time
import datetime
import configparser
import sys
import getopt
import signal
import threading
import logging

runScript = True  # global var managing script's loop cycle


class Config:
    # client, user and device details
    def __init__(self, argv):
        self.serverUrl = "localhost"
        self.username = "<<username>>"
        self.password = "<<password>>"

        self.devId = "wattrouter"  # device id, also used as mqtt client id and mqtt base topic

        self.logfile = "./wattrouter.log"
        self.logLevel = logging.INFO
        self.configFile = './wattrouter.cfg'
        self.qos = 1
        self.wrhost = "localhost"
        self.pollInterval = 15

        self.parse_args(argv)

        if len(self.configFile) > 0:
            self.read_config(self.configFile)

    def help(self):
        print('Usage: '+sys.argv[0] +
              ' -c <configfile> -v <verbose level> -l <logfile>')
        print()
        print('  -c | --config: ini-style configuration file, default is '+self.configFile)
        print('  -v | --verbose: 1-fatal, 2-error, 3-warning, 4-info, 5-debug')
        print('  -l | --logfile: log file name,default is '+self.logfile)
        print()
        print('Example: '+sys.argv[0] +
              ' -c /etc/wattrouter.cfg -v 2 -l /var/log/wattrouter.log')

    def parse_args(self, argv):
        try:
            opts, args = getopt.getopt(
                argv, "hc:v:l:", ["config=", "verbose=", "logfile="])
        except getopt.GetoptError:
            print("Command line argument error")
            self.help()
            sys.exit(2)

        for opt, arg in opts:
            if opt == '-h':
                self.help()
                sys.exit()
            elif opt in ("-c", "--config"):
                self.configFile = arg
            elif opt in ("-v", "--verbose"):
                self.logLevel = int(arg)
            elif opt in ("-l", "--logfile"):
                self.logfile = arg

    def read_config(self, cf):
        print('Using configuration file ', cf)
        config = configparser.ConfigParser()
        config.read(cf)

        try:
            seccfg = config['wattrouter']
        except KeyError:
            print('Error: configuration file is not correct or missing')
            exit(1)

        self.serverUrl = seccfg.get('host', 'localhost')
        self.username = seccfg.get('username')
        self.password = seccfg.get('password')
        self.devId = seccfg.get('id', 'wattrouter')
        self.wrhost = seccfg.get('wrhost', 'wattrouter')
        self.qos = int(seccfg.get('qos', "1"))
        self.pollInterval = int(seccfg.get('interval', "15"))

class App(threading.Thread):
    def __init__(self, id, mqttClient):
        self.id = id
        self.log = logging.getLogger(name="app")
        self._mqtt = mqttClient
        self._mqtt_reconnect = 0  # reconnect count
        self._running = True

        self._mqtt.on_message = self._on_mqtt_message
        self._mqtt.on_publish = self._on_mqtt_publish
        self._mqtt.on_connect = self._on_mqtt_connect
        self._mqtt.on_disconnect = self._on_mqtt_disconnect

        self.log.all("subscribing to MQTT channel", self.id+"/cmd")
        self._mqtt.subscribe(self.id+"/cmd", 1)

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        self.mqtt_connected = rc
        self._mqtt_reconnect = 0
        if rc != 0:
            self.log.err("MQTT connection returned result="+rc)
            self._mqtt_reconnect += 1
            if self._mqtt_reconnect > 12:
                self._mqtt_reconnect = 12
            self.mqtt_reconnect_delay = 2**self._mqtt_reconnect
        else:
            self.log.info("Connected to MQTT broker.")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        self._mqtt_reconnect = 1
        if rc != 0:
            self.log.err("MQTT unexpected disconnection.")
            self._mqtt_reconnect += 1
            self.mqtt_reconnect_delay = 10

    # display all incoming messages
    def _on_mqtt_message(self, client, userdata, message):
        self.log.debug("MQTT message="+str(message.payload))
        print("MQTT message="+str(message.payload))

    def _on_mqtt_publish(self, client, userdata, mid):
        self.log.debug("MQTT received=", mid)

    def stop(self):
        self.log.debug("Stopping app",self.id)
        self._running = False

    def run(self):
        while self._running:
            if self._mqtt_reconnect > 0:
                self.log.warn("MQTT Reconnecting...")
                self._mqtt.reconnect()
            time.sleep(5)


class Wattrouter(threading.Thread):
    
    # if set to true, monitor will send gpio changes only
    # if set to false, monitor will send gpio status together with alive update
    _sendChangesOnly = False
    
    _aliveTime = 0
    # how often will client sent alive information (in seconds)
    _aliveInterval = 60

    def __init__(self, id, mqttClient, *, qos=1, wrhost="wattrouter"):

        self._id = id
        self._mqtt = mqttClient  # mqtt client
        self._log = logging.getLogger("wr")
        self._qos = qos
        self._running = True

    def stop(self):
        self._log.info("*** Wattrouter is shutting down", self._id)
        self._running = False

    def start(self):
        self._log.info("*** Wattrouter is starting", self._id)
        self._log.info("Host=%s", self.wrhost)

    def run(self):
        while self._running:
            # request data from Wattrouter host
            # process data
            # sleep for poll-duration
            time.sleep(self.pollInterval)

    # publish a message
    def publish(self, topic, message, qos=1, retain=False):
        self._log.info("publishing topic=%s/%s message=%s", self._id, topic, message)
        mid = self._mqtt.publish(self._id+'/'+topic, message, qos, retain)[1]

def stop_script_handler(msg, logger):
    logger.all(msg)
    global runScript
    runScript = False


# -------------------------------------------------------

# parse commandline aruments and read config file if specified
cfg = Config(sys.argv[1:])

print("Going to connect to wattrouter host=", cfg.wrhost)

# configure logging
logging.basicConfig(filename=cfg.logfile, encoding="utf-8", level=cfg.logLevel, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add console to logger output
logging.addHandler(logging.StreamHandler())

# create logger
log = logging.getLogger('main')

# handle gracefull end in case of service stop
signal.signal(signal.SIGTERM, lambda signo,
              frame: stop_script_handler("Signal SIGTERM received", log))

# handles gracefull end in case of closing a terminal window
signal.signal(signal.SIGHUP, lambda signo,
              frame: stop_script_handler("Signal SIGHUP received", log))

# connect the client to MQTT broker and register a device
print("Creating MQTT client for", cfg.serverUrl)
mqttc = mqtt.Client(cfg.devId)
mqttc.username_pw_set(cfg.username, cfg.password)
mqttc.connect(cfg.serverUrl)

# create default app object (handles generic mqtt)
app = App(cfg.devId, mqttc)
app.start()

# create object for gpio monitor
print("Creating wattrouter device as", cfg.devId)
device = Wattrouter(cfg.devId, mqttc,
                   qos=cfg.qos,
                   wrhost=cfg.wrhost)

device.start()

# start thread handling mqtt communication
mqttc.loop_start()

try:
    while runScript:
        time.sleep(1)

except KeyboardInterrupt:
    log.info("Signal SIGINT received.")

# perform some cleanup
log.info("Stopping device ", cfg.devId)
device.stop()
mqttc.disconnect()
mqttc.loop_stop()
app.stop()
log.info('Stopped.')
