#!/usr/bin/env bash

# exit on error, keep track of executed commands, print error
set -e
trap 'captured! echo ‘$BASH_COMMAND’ returned code $?' EXIT
clear


printf '\n' && printf 'Welcome to DDH installer for development purposes \n'
printf '************************************************* \n'

printf '\n\n\n\n' && printf 'Installing linux apt dependencies... \n'
printf '=================================== \n'
apt-get install libatlas3-base libglib2.0-dev libhdf5-dev python3-dev libgdal-dev

printf '\n\n\n\n' && printf 'Cloning DDH source from github... \n'
printf '================================= \n'
git clone https://github.com/LowellInstruments/ddh.git
printf 'left the downloaded source in %s', $(pwd)


printf '\n\n\n\n Now review (and install) file ddh/tools/requirements_dev.txt \n'
printf 'you decide if you use a python virtualenv, or not'

