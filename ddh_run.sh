#!/bin/bash

clear
echo
echo "Running DDH..."
echo "--------------"
export XAUTHORITY=/home/pi/.Xauthority
export DISPLAY=:0


cd /home/pi/li/ddh || (echo "cannot enter ddh folder"; exit 1)
sudo python3 main.py
