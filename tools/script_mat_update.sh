#!/usr/bin/env bash

# =======================================
# to run when updating MAT lib in DDH
# =======================================

# terminate script at first line failing
set -e
if [[ $EUID -ne 0 ]]; then echo "need to run as root";  exit 1; fi


echo ''
pip3 uninstall -y lowell-mat
pip3 install git+https://github.com/LowellInstruments/lowell-mat.git
printf "\n\tdone!\r\n"

