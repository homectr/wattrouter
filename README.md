# Wattrouter to MQTT bridge

## Installation

Requires:
* python 3.9.x

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
[wattrouter]
id=wattrouter    ; device id - should be unique, mqtt topic is prefixed by device id
host=localhost   ; mqtt broker host name or address
username=        ; mqtt user - if used
password=        ; mqtt password - if used
qos=1            ; default qos for mqtt messages
wrhost=          ; wattrouter device host name or ip address
interval=15      ; wattrouter api polling interval
```


