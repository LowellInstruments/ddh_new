#!/usr/bin/env bash

# terminate script at first line failing
set -e
if [[ $EUID -ne 0 ]]; then echo "run this script as root";  exit 1; fi


echo ''
pip3 uninstall lowell-mat
pip3 install git+https://github.com@LowellInstruments/lowell-mat.git
printf "\n\tdone! error flag = %d\n" $?

