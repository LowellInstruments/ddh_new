#!/bin/bash

clear
echo
echo "Running DDH..."
echo "--------------"
export XAUTHORITY=/home/pi/.Xauthority
export DISPLAY=:0
cd ~/li/ddh || exit 1
sudo python3 ddh_main.py