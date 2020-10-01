#!/bin/bash
clear


echo
if [ ! -d ~/li/ddh ]; then
    echo "Error Uninstalling: Lowell Instruments application folder ~/li/ddh does not exist"
    echo
    exit 1
fi


echo "Removing Lowell Instruments MAT library..."
sudo pip3 uninstall -y lowell-mat
echo



echo
echo "Removing Lowell Instruments application folder ~/li/ddh..."
read -p "Are you sure? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo rm -rf ~/li/ddh
    echo "Deck Data Hub uninstalled"
else
    echo "Lowell Instruments application folder ~/li/ddh NOT removed"
fi
