#!/usr/bin/env bash

# exit on error, keep track of executed commands, print error
set -e
trap 'captured! echo ‘$BASH_COMMAND’ returned code $?' EXIT
clear


printf '\n' && printf 'Welcome to DDH installer for Raspberry platforms \n'
printf 'You only need to run this once. When installed, use git pull on DDH folder \n'
printf '************************************************************************** \n'

if [ "$EUID" -ne 0 ]; then printf 'Please run as root'; exit; fi

printf '\n\n\n\n' && printf 'Installing Raspberry linux apt dependencies... \n'
printf '============================================== \n'
apt-get install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev python3-dev libgdal-dev

printf '\n\n\n\n' && printf 'Installing Raspberry linux python dependencies... \n'
printf '================================================= \n'
printf 'TODO check if we need this on Rpi \n'
# more of them, from https://stackoverflow.com/questions/53697814/using-pip-install-to-install-cartopy-but-missing-proj-version-at-least-4-9-0
apt-get install libproj-dev proj-data proj-bin libgeos-dev
pip3 install cython Cartopy==0.18.0

printf '\n\n\n\n' && printf 'Cloning DDH source from github... \n'
printf '================================= \n'
cd /home/pi/li
git clone https://github.com/LowellInstruments/ddh.git
cd /home/pi/li/ddh
pip3 install -r requirements.txt
