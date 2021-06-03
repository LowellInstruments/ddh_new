#!/usr/bin/env bash

FOL=/home/pi/li/ddh
FST=$FOL/ddh/settings
FDL=$FOL/ddh/dl_files


# terminate script at first error
echo && set -e
if [ $# -ne 3 ]; then echo "error -> need IP & project & vessel"; exit 1; fi
if [ $EUID -ne 0 ]; then echo "error -> need run as root";  exit 1; fi

# pre-checks
if [ ! -d $FOL ]; then echo "error -> no DDH base folder";  exit 1; fi
if [ ! -d $FST ]; then echo "error -> no DDH conf folder";  exit 1; fi
if ! cp -rf $FDL /tmp; then echo "error -> backup DDH dl_files folder"; exit 1; fi

# get latest DDH code
if ! (cd $FOL && git reset --hard && git pull); then echo "error -> git"; exit 1; fi

# get configuration files from web service and install them
rm -rf conf || true
curl http://"$1":5000/"$2"/"$3".zip --output "$3".zip
if ! unzip -o "$3"; then echo "error -> bad zip password"; exit 1; fi
if ! cp "$3"/run_ddh.sh $FOL; then echo "error -> run_ddh.sh"; exit 1; fi
if ! cp "$3"/ddh.json $FST; then echo "error -> ddh.json"; exit 1; fi
if ! cp "$3"/_macs_to_sn.yml $FST; then echo "error -> _macs file"; exit 1; fi
rm -rf "$3".zip || true

# recover saved dl_files
cp -ru /tmp/dl_files $FOL/ddh

# post-banner
printf "\n\tdone!\r\n"
