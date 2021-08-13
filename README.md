# Wattrouter to MQTT bridge

## Installation

Requires:

- node.js 14+

To install run `install.sh` script.

## Starting

Script is installed as `systemd` service. So in order to start `sudo systemctl start wattrouter`

## Logging

Script logs by default into file `/var/log/wattrouter.log`.
Log level and log file can be modified in systemd unit file `/etc/systemd/system/wattrouter.service`

Log file is maintained by logrotate service. Log rotate configuration is in `/etc/logrotate.d/wattrouter`

## Configuration

Configuration is by default stored in `/etc/wattrouter.cfg`

```
{
  "mqtt": {
    "clientid": "wattrouter",   ; device id - should be unique, mqtt topic is prefixed by device id
    "host": "tcp://openhabian", ; mqtt broker host name or address
    "username": "user",         ; optional mqtt user name
    "password": "password"      ; optional mqtt password
  },
  "wattrouter": {
    "host": "172.16.26.21",     ; wattrouter device host name or ip address
    "interval": 15              ; wattrouter api polling interval (in seconds)
  }
}

```
