#!/bin/bash

clear
echo
echo "Running DDH..."
echo "--------------"
export XAUTHORITY=/home/pi/.Xauthority
export DISPLAY=:0


# ensure only 1 instance of this bash script
ps aux | grep ddh_main | grep -v grep
if [ $? -ne 0 ]; then
    echo "some DDH already running"
    echo
    exit 1
fi
cd ~/li/ddh || exit 1
sudo python3 ddh_main.py