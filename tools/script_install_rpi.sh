#!/usr/bin/env bash


# keep track of executed commands, print and exit upon error
set -e
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
trap 'echo "\"${last_command}\" command filed with exit code $?."' EXIT


clear
printf 'Welcome to DDH installer for Raspberry platforms \n'
printf 'You only need to run this once. When installed, use git pull'
printf '============================================================ \n\n\n\n'

if [ "$EUID" -ne 0 ]; then printf 'Please run as root'; exit; fi

printf 'Installing Raspberry linux apt dependencies... \n'
printf '============================================== \n\n\n\n'
sudo apt-get install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev python3-dev libgdal-dev

printf 'Installing Raspberry linux python dependencies... \n'
printf '================================================= \n\n\n\n'
pip3 install Cartopy==0.18.0

printf 'Cloning DDH source from github... \n'
printf '================================= \n\n\n\n'
cd /home/pi
git clone https://github.com/LowellInstruments/ddh.git
cd /home/pi/ddh
pip3 install -r requirements.txt
