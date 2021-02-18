#!/usr/bin/env bash

# keep track of executed commands, print and exit upon error
set -e
trap 'echo ‘$BASH_COMMAND’ failed with error code $?' EXIT
clear


printf '\n' && printf 'Welcome to DDH installer for Raspberry platforms \n'
printf 'You only need to run this once. When installed, use git pull \n'
printf '============================================================ \n\n\n\n'

if [ "$EUID" -ne 0 ]; then printf 'Please run as root'; exit; fi

printf '\n' && printf 'Installing Raspberry linux apt dependencies... \n'
printf '============================================== \n\n\n\n'
sudo apt-get install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev python3-dev libgdal-dev

printf '\n' && printf 'Installing Raspberry linux python dependencies... \n'
printf '================================================= \n\n\n\n'
sudo pip3 install Cartopy==0.18.0

printf '\n' && printf 'Cloning DDH source from github... \n'
printf '================================= \n\n\n\n'
cd /home/pi/li
git clone https://github.com/LowellInstruments/ddh.git
cd /home/pi/li/ddh
sudo pip3 install -r requirements.txt
