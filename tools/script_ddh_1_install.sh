#!/usr/bin/env bash

# =======================================
# to run when building DDH from scratch
# =======================================

# exit on error, keep track of executed commands, print
clear && set -e
trap 'echo ‘$BASH_COMMAND’ trapped! returned code $?' EXIT


printf '\n>> Welcome to DDH installer \n'
if [ "$EUID" -ne 0 ]; then printf '\n>> Please run as root \n'; exit; fi


read -p "\n>> Remove DDH, including downloaded files. Continue (y/n)? " ch
case "$ch" in
  y|Y ) echo "yes";; n|N ) echo "no"; exit;; * ) echo "invalid"; exit;;
esac
if [ -d "/home/pi/li/ddh" ]; then rm -rf /home/pi/li/ddh; fi


printf '\n>> Installing APT dependencies... \n'
apt-get update
apt-get -y install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev python3-dev \
    libgdal-dev libproj-dev proj-data proj-bin libgeos-dev python3-gdbm


printf '\n>> Installing PIP dependencies... \n'
pip3 install cython Cartopy==0.18.0


printf '\n>> Cloning DDH source from github... \n'
mkdir -p /home/pi/li/ddh
git clone https://github.com/LowellInstruments/ddh.git /home/pi/li/ddh
pip3 install -r /home/pi/li/ddh/requirements.txt


printf '\n>> Now you may /home/pi/li/ddh/tools/script_ddh_2_configure.sh \n'
