#!/usr/bin/env bash

# exit on error
clear; set -e
trap 'echo ‘$BASH_COMMAND’ trapped, returned code $?' EXIT

# vars
FOL_LI=/home/pi/li; FOL_DDH=$FOL_LI/ddh; FOL_VENV=$FOL_LI/venv

# (un)comment this depending on if you use python virtualenv on or not
# if [ ! -d $FOL_VENV ]; then printf "DDH python venv NOT detected\n"; exit 1; fi

# ensure we place ourselves
cd $FOL_DDH
if [ $? -ne 0 ]; then
  printf "cannot enter DDH folder"
  exit 1
fi

# set X server vars for raspberry
export XAUTHORITY=/home/pi/.Xauthority
export DISPLAY=:0

# set AWS vars, on PyCharm, do in 'edit run configuration'
export DDH_AWS_NAME=_AN_
export DDH_AWS_KEY_ID=_AK_
export DDH_AWS_SECRET=_AS_

# (un)comment depending on if you allow running without AWS
if [ $DDH_AWS_NAME == "_AN_" ]; then printf "AWS env error\n"; exit 2; fi
if [ $DDH_AWS_KEY_ID == "_AK_" ]; then printf "AWS env error\n"; exit 3; fi
if [ $DDH_AWS_SECRET == "_AS_"_ ]; then printf "AWS env error\n"; exit 4; fi

# sudo -E considers environment vars such as DDH_AWS_NAME
printf "entering DDH folder\n"; cd $FOL_DDH || exit 5

# printf "running DDH in a virtual environment \n"
# sudo -E FOL_VENV/bin/python3 main.py

printf "running DDH \n"
sudo -E python3 main.py
