#!/usr/bin/env bash

# exit on error, keep track of executed commands, print error
set -e
trap 'echo ‘$BASH_COMMAND’ returned code $?' EXIT
clear

FOL_LI=/home/pi/li
FOL_DDH=$FOL_LI/ddh
FOL_VENV=$FOL_LI/venv

# (un)comment this depending on if you use python virtualenv on or not
# if [ ! -d $FOL_VENV ]; then printf "DDH python venv NOT detected\n"; exit 1; fi

# setting X server vars
export XAUTHORITY=/home/pi/.Xauthority
export DISPLAY=:0

# on PyCharm, set in Run/ Edit Configurations/environment
export DDH_AWS_NAME=_AN_
export DDH_AWS_KEY_ID=_AK_
export DDH_AWS_SECRET=_AS_

# (un)comment depending on if you allow running without setting AWS
if [ $DDH_AWS_NAME == "_AN_" ]; then printf "AWS environment error\n"; exit 2; fi
if [ $DDH_AWS_KEY_ID == "_AK_" ]; then printf "AWS environment error\n"; exit 3; fi
if [ $DDH_AWS_SECRET == "_AS_"_ ]; then printf "AWS environment error\n"; exit 4; fi

# -E considers DDH_FTP_* env vars
printf "entering DDH folder\n"
cd $FOL_DDH || exit 5
printf "running DDH\n"
sudo -E FOL_VENV/bin/python main.py
