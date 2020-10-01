#!/bin/bash

clear
if [ -d ~/li/ddh ]; then
    printf 'error: ~/li/ddh already exists\n'
    exit 1
fi


printf 'entering fresh folder ~/li/ddh...\n'
mkdir -p ~/li/ddh
pushd .
cd ~/li || exit 2


printf 'cloning MAT library...\n'
git clone -b v2100 https://github.com/LowellInstruments/lowell-mat.git
if [ $? -ne 0 ]; then
    printf 'error: cannot clone MAT library\n'
    exit 1
fi
printf 'cloning MOD bluepy library...\n'
git clone https://github.com/LowellInstruments/bluepy.git
if [ $? -ne 0 ]; then
    printf 'error: cannot clone MOD bluepy library\n'
    exit 1
fi


printf 'installing DDH requirements file\n'
sudo pip3 install -r ~/li/ddh/requirements.txt


printf 'Deck Data Hub installed in ~/li/ddh/\n\n'
