#!/bin/bash
#set -x
svcname="wattrouter"
svcfld="wattrouter"

echo "Installing ${svcname} script"

function check_installed {
    local status=$?
    if [ $status -ne 0 ]; then
        echo "error: not installed"
        exit 1
    fi
    echo "ok"
}

function check_running {
    local cnt=`ps aux | grep -c ${1}`
    # assuming running if at least two lines found in ps result
    if [ $cnt -gt 1 ]; then
        echo "ok"
        return 0
    fi
    echo "error: not running"
}

echo "Checking if npm is installed"
npm --version > /dev/null
check_installed

echo "Installing required packages"
npm install

echo "Building app"
npm run build

if [ -f "/etc/${svcname}.cfg" ]; then
echo "Keeping existing configuration file /etc/${svcname}.cfg"
else
echo "Copying default configuration to /etc"
sudo cp ./examples/${svcname}.cfg.example /etc/${svcname}.cfg
fi

echo "Creating log file"
sudo touch /var/log/${svcname}.log

if [ -f "/etc/logrotate.d/${svcname}" ]; then
echo "Keeping existing logrotate configuration /etc/logrotate.d/${svcname}"
else
echo "Configuring logrotate"
sudo cp ./examples/${svcname}.logrotate /etc/logrotate.d/${svcname}
sudo systemctl restart logrotate
fi

if [ -f "/etc/systemd/system/${svcname}.service" ]; then
echo "Keeping existing service configuration /etc/systemd/system/${svcname}.service"
else
echo "Creating service"
sudo cp ./examples/${svcname}.service /etc/systemd/system
curdir=`pwd`
sed -i "/^WorkingDirectory*/c\WorkingDirectory=${curdir}" /etc/systemd/system/${svcname}.service
sudo systemctl daemon-reload
sudo systemctl enable ${svcname}.service
fi

echo "Starting service"
sudo systemctl restart ${svcname}.service

echo "Installation complete"
echo "Modify script configuration in /etc/${svcname}.cfg"
echo "Restart script service using: sudo systemctl restart ${svcname}"
echo "Check service status using: sudo systemctl status ${svcname}"