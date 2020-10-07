#!/bin/bash

function cleanup {
  printf "DDH NOT running\n"
}
trap cleanup EXIT

# in RPi, root check not needed, sudo at the end
clear
FOL_LI=/home/pi/li
FOL_DDH=$FOL_LI/ddh
FOL_VENV=$FOL_LI/venv

# check venv
if [ ! -d $FOL_VENV ]; then printf "DDH python venv NOT detected\n"; exit 1; fi

# setting X server vars
export XAUTHORITY=/home/pi/.Xauthority
export DISPLAY=:0

# on PyCharm, set in Run/ Edit Configurations/environment
export DDH_FTP_U=_U_
export DDH_FTP_H=_H_
export DDH_FTP_P=_P_
if [ $DDH_FTP_U == _U_ ]; then printf "DDH FTP env vars U error\n"; exit 2; fi
if [ $DDH_FTP_P == _P_ ]; then printf "DDH FTP env vars P error\n"; exit 3; fi
if [ $DDH_FTP_H == _H_ ]; then printf "DDH FTP env vars H error\n"; exit 4; fi

# -E considers DDH_FTP_* env vars
printf "entering DDH folder\n"
cd $FOL_DDH || exit 5
printf "running DDH\n"
sudo -E FOL_VENV/bin/python main.py
