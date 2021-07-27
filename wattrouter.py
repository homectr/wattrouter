#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt
import time
import configparser
import sys
import getopt
import signal
import threading
import logging
import xml.etree.ElementTree as ET
import http.client

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
                if arg == "1": self.logLevel = logging.FATAL
                if arg == "2": self.logLevel = logging.ERROR
                if arg == "3": self.logLevel = logging.WARNING
                if arg == "4": self.logLevel = logging.INFO
                if arg == "5": self.logLevel = logging.DEBUG
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
        self.wrhost = seccfg.get('wrhost', '')
        self.qos = int(seccfg.get('qos', "1"))
        self.pollInterval = int(seccfg.get('interval', "15"))

class App(threading.Thread):
    def __init__(self, id, mqttClient, device):
        print("Starting app")
        threading.Thread.__init__(self)
        self.id = id
        self._log = logging.getLogger(name="app")
        self._log.addHandler(logging.StreamHandler())
        self._mqtt = mqttClient
        self._mqtt_reconnect = 0  # reconnect count
        self._running = True
        self._device = device
        self._aliveTime = 0
        self._aliveInterval = 1800

        self._mqtt.on_message = self._on_mqtt_message
        self._mqtt.on_publish = self._on_mqtt_publish
        self._mqtt.on_connect = self._on_mqtt_connect
        self._mqtt.on_disconnect = self._on_mqtt_disconnect

        self._log.info("subscribing to MQTT channel %s/cmd", self.id)
        self._mqtt.subscribe(self.id+"/cmd", 1)

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        self.mqtt_connected = rc
        self._mqtt_reconnect = 0
        if rc != 0:
            self._log.error("MQTT connection returned result=%d",rc)
            self._mqtt_reconnect += 1
            if self._mqtt_reconnect > 12:
                self._mqtt_reconnect = 12
            self.mqtt_reconnect_delay = 2**self._mqtt_reconnect
        else:
            self._log.info("Connected to MQTT broker.")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        self._mqtt_reconnect = 1
        if rc != 0:
            self._log.error("MQTT unexpected disconnection.")
            self._mqtt_reconnect += 1
            self.mqtt_reconnect_delay = 10

    # display all incoming messages
    def _on_mqtt_message(self, client, userdata, message):
        handled = False
        self._log.debug("MQTT on_message=%s",message.payload)
        print("MQTT on_message=",message.payload)
        handled = handled or self._device.handleMessage(message)

        if not handled:
            self._log.debug("MQTT on_message not handled message={}".format(message))

    def _on_mqtt_publish(self, client, userdata, mid):
        # self.log.debug("MQTT on_publish mid=%s", mid)
        return

    def stop(self):
        self._log.debug("Stopping app %s",self.id)
        self._running = False
        self._device.stop()
        self._mqtt.disconnect()
        self._mqtt.loop_stop()

    def run(self):
        print("App started")
        self._device.start()
        while self._running:
            if time.time()-self._aliveTime > self._aliveInterval:
                self._log.info("App alive (%s) %s", self._aliveInterval, time.strftime("%Y-%m-%d %H:%M:%S"))
                self._aliveTime = time.time()
            if self._mqtt_reconnect > 0:
                self._log.warning("MQTT Reconnecting...")
                self._mqtt.reconnect()
            time.sleep(1)


class Wattrouter(threading.Thread):
    
    # if set to true, monitor will send gpio changes only
    # if set to false, monitor will send gpio status together with alive update
    _sendChangesOnly = False
    
    _aliveTime = 0
    # how often will client sent alive information (in seconds)
    _aliveInterval = 60

    def __init__(self, id, mqttClient, wrConnection, *, qos=1, wrhost="wattrouter", interval=15):
        print("Creating wattrouter")
        threading.Thread.__init__(self)
        self._id = id
        self._mqtt = mqttClient  # mqtt client
        self._wr = wrConnection
        self._log = logging.getLogger("wr")
        self._log.addHandler(logging.StreamHandler())
        self._qos = qos
        self._running = True
        self._wrhost = wrhost
        self._pollInterval = interval
        self._aliveTime
        self._aliveInterval = 900

        for i in range(1,7):
            self._mqtt.subscribe("{id}/O{i}/T/set".format(id=self._id, i=i))

    def stop(self):
        self._log.info("*** Wattrouter is shutting down %s", self._id)
        self._running = False

    def run(self):
        print("Wattrouter started")
        while self._running:
            if time.time()-self._aliveTime > self._aliveInterval:
                self._log.info("Wattrouter alive (%s) %s", self._aliveInterval, time.strftime("%Y-%m-%d %H:%M:%S"))
                self._aliveTime = time.time()
            # request data from Wattrouter host
            self._wr.request("GET","/meas.xml")
            r = self._wr.getresponse()
            if r.status != 200:
                self._log.error("Error getting response from Wattrouter status=%d",r.status)
                time.sleep(300)
                continue

            # process data
            data = r.read()
            dataxml = ET.fromstring(data)
            # process inputs
            for i in range(1,8):
                v = dataxml.findtext("./I{i}/P".format(i=i))
                if v != None: self.publish("I{i}/P".format(i=i),v)
                v = dataxml.findtext("./I{i}/E".format(i=i))
                if v != None: self.publish("I{i}/E".format(i=i),v)

            # process outputs
            for i in range(1,7): 
                v = dataxml.findtext("./O{i}/P".format(i=i))
                if v != None: self.publish("O{i}/P".format(i=i),v)
                v = dataxml.findtext("./O{i}/HN".format(i=i))
                if v != None: self.publish("O{i}/HN".format(i=i),v)
                v = dataxml.findtext("./O{i}/T".format(i=i))
                if v != None: self.publish("O{i}/T".format(i=i),v)

            # process temperature sensors
            for i in range(1,5):
                v = dataxml.findtext("./DQ{i}".format(i=i))
                if v != None: self.publish("DQ{i}".format(i=i),v)

            v = dataxml.findtext("./PPS") # total power
            if v != None: 
                self.publish("PPS",v)
                self._log.info("PPS=%s",v)
            v = dataxml.findtext("./VAC") # L1 volatge
            if v != None: self.publish("VAC",v)
            v = dataxml.findtext("./EL1") # L1 voltage error
            if v != None: 
                self.publish("EL1",v)
                if v=="1": self._log.warning("Voltage error detected")
            v = dataxml.findtext("./ETS") # temperature sensors error
            if v != None: self.publish("ETS",v)
            v = dataxml.findtext("./ILT")
            if v != None: self.publish("ILT",v)
            v = dataxml.findtext("./ICW")
            if v != None: self.publish("ICW",v)
            v = dataxml.findtext("./ITS")
            if v != None: self.publish("ITS",v)
            v = dataxml.findtext("./IDST")
            if v != None: self.publish("IDST",v)
            v = dataxml.findtext("./ISC")
            if v != None: self.publish("ISC",v)
            v = dataxml.findtext("./SRT")
            if v != None: self.publish("SRT",v)
            v = dataxml.findtext("./DW")
            if v != None: self.publish("DW",v)

            # sleep for poll-duration
            for i in range(self._pollInterval):
                time.sleep(1)
                if not self._running: break

    # publish a message
    def publish(self, topic, message, qos=1, retain=False):
        self._log.debug("publish topic=%s/%s message=%s", self._id, topic, message)
        mid = self._mqtt.publish(self._id+'/'+topic, message, qos, retain)[1]

    def toggleTest(self, outputNo, value):
        self._log.debug("Toggle no={no} v={v}".format(no=outputNo,v=value))
        nvalue = "1" if value==1 or value=="1" or value==b'1' else "0"

        self._wr.request("POST","/test.xml",headers = {'Content-Type': 'application/xml'}, body="<test><TST{no}>{value}</TST{no}><UN>admin</UN><UP>1234</UP></test>".format(no=outputNo,value=nvalue))
        r = self._wr.getresponse()
        if r.status != 200:
            self._log.error("Error changing test status for output {no} to value {value}".format(no=outputNo, value=nvalue))
            return
        else:
            self._log.debug("Output test toggle o={no} value={value}".format(no=outputNo,value=nvalue))
            self.publish("O{i}/T".format(i=outputNo),nvalue)

    def handleMessage(self,message):
        for i in range(1,7):
            if message.topic == "{id}/O{i}/T/set".format(id=self._id, i=i):
                self.toggleTest(i,message.payload)
                return True

def stop_script_handler(msg, logger):
    logger.info(msg)
    global runScript
    runScript = False


# -------------------------------------------------------

# parse commandline aruments and read config file if specified
cfg = Config(sys.argv[1:])

# configure logging
logging.basicConfig(filename=cfg.logfile, level=cfg.logLevel, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# create logger
log = logging.getLogger('main')

# add console to logger output
log.addHandler(logging.StreamHandler())

log.info("*** Wattrouter Bridge Starting")
log.info("Wattrouter host=%s", cfg.wrhost)

if cfg.wrhost == '':
    log.fatal("Wattrouter host not specified in config file.")
    exit(1)

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

# start thread handling mqtt communication
mqttc.loop_start()

# create http connection to wattrouter device
wrc = http.client.HTTPConnection(cfg.wrhost)

# create object for gpio monitor
print("Creating wattrouter device as", cfg.devId)
device = Wattrouter(cfg.devId, mqttc, wrc,
                   qos=cfg.qos,
                   wrhost=cfg.wrhost, interval=cfg.pollInterval)

# create default app object (handles generic mqtt)
app = App(cfg.devId, mqttc, device)
app.start()

try:
    while runScript:
        time.sleep(1)

except KeyboardInterrupt:
    log.info("Signal SIGINT received.")

# perform some cleanup
log.info("Stopping device id=%s", cfg.devId)
app.stop()
log.info('Wattrouter stopped.')
