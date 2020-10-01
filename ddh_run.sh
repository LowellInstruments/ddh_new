#!/bin/bash

clear
echo "Running DDH..."
echo "--------------"
export XAUTHORITY=/home/pi/.Xauthority
export DISPLAY=:0


# ensure only 1 instance of this bash script
pgrep -f ddh_main.py
if [ $? -eq 0 ]; then
    printf 'bash --> some DDH already running\n'
    exit 1
fi
cd ~/li/ddh || exit 1
sudo python3 ddh_main.py
printf 'remember do not sudo ./ddh_run.sh\n\n'
