#!/usr/bin/env bash

# exit on error, keep track of executed commands, print error
set -e
trap 'echo ‘$BASH_COMMAND’ trapped! returned code $?' EXIT
clear

printf '\n' && printf 'Welcome to DDH installer for Raspberry platforms \n'
printf 'You only need to run this once. When installed, use git pull on DDH folder \n'
printf '************************************************************************** \n'

if [ "$EUID" -ne 0 ]; then printf 'Please run as root'; exit; fi

printf '\n\n\n\n' && printf 'Installing Raspberry linux apt dependencies... \n'
printf '============================================== \n'
apt-get update
apt-get -y install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev python3-dev libgdal-dev libproj-dev proj-data proj-bin libgeos-dev RPi

printf '\n\n\n\n' && printf 'Installing Raspberry linux python dependencies... \n'
printf '================================================= \n'
pip3 install cython Cartopy==0.18.0

printf '\n\n\n\n' && printf 'Cloning DDH source from github... \n'
printf '================================= \n'
mkdir -p /home/pi/li/ddh
git clone https://github.com/LowellInstruments/ddh.git /home/pi/li/ddh
pip3 install -r /home/pi/li/ddh/requirements.txt
