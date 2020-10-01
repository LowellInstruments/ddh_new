#!/bin/bash

DDH_FOLDER=/home/pi/li/ddh
VENV_EXEC=/home/pi/li/venv/bin/python


clear
printf "\n%s\n" "activating venv..."
source ../venv/bin/activate || (printf "ERR act_venv\n"; exit 1)


printf "\n%s\n\n" "running DDH..."
export XAUTHORITY=/home/pi/.Xauthority
export DISPLAY=:0


# populate this with good ones
# on PyCharm: Run/ Edit Configurations/environment
export DDH_FTP_U=_U_
export DDH_FTP_H=_H_
export DDH_FTP_P=_P_


# -E considers DDH_FTP_* env vars
cd $DDH_FOLDER || (echo "ERR: cannot cd DDH folder"; exit 1)
sudo -E $VENV_EXEC main.py
