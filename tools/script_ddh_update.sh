#!/usr/bin/env bash

# ===============================
# to run when updating a DDH GUI
# ===============================

# terminate script at first line failing
echo ""
set -e
if [[ $EUID -ne 0 ]]; then echo "need to run as root";  exit 1; fi
FOL=/home/pi/li/ddh
FST=$FOL/ddh/settings
FDL=$FOL/ddh/dl_files


# pre-checks
[ -d $FOL ] || echo "bad: no ddh folder"
[ -d $FST ] || echo "bad: no settings folder"


# saving current DDH files
cp $FOL/run_ddh.sh /tmp || echo "bad: no run_ddh"
cp $FST/ddh.json /tmp || echo "bad: no ddh.json"
cp $FST/_macs_to_sn.yml /tmp || echo "bad: no _macs_to_sn.yml"
cp -rf $FDL /tmp


# updating DDH
(cd $FOL && git reset --hard && git pull) || echo "bad: git"


# restoring DDH files
cp /tmp/run_ddh.sh $FOL || echo "bad: at restoring run_ddh"
cp /tmp/ddh.json $FST || echo "bad: at restoring ddh.json"
cp /tmp/_macs_to_sn.yml $FST || echo "bad: no _macs_to_sn.yml"
cp -ru /tmp/dl_files $FOL/ddh


# post-banner
printf "\n\tdone!\r\n"
