#!/usr/bin/env bash

# exit on error, keep track of executed commands, print error
set -e
trap 'captured! echo ‘$BASH_COMMAND’ returned code $?' EXIT
clear


printf '\n' && printf 'Welcome to DDH installer for Raspberry platforms with python virtualenv\n'
printf 'You only need to run this once. When installed, use git pull on DDH folder \n'
printf '************************************************************************** \n\n\n\n'
if [ "$EUID" -ne 0 ]; then printf 'Please run as root'; exit; fi

printf '\n' && printf 'Installing Raspberry linux apt dependencies... \n'
printf '============================================== \n\n\n\n'
apt-get install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev python3-dev libgdal-dev

printf '\n' && printf 'Installing Raspberry linux python dependencies... \n'
printf 'todo: the same as the other but using complete paths for venv/bin/pip3 and venv/bin/python3'