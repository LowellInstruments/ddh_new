#!/usr/bin/env bash

# /bin/bash /home/kaz/PycharmProjects/ddh/tools/script_ddh_deploy_web_service.sh <vessel_name>>


MY_URL="http://127.0.0.1:5000/ddh/${1}/info.zip"
clear

if [ $# -eq 0 ]; then echo 'error: missing vessel name, bye'; exit 1; fi

(rm info.zip 2> /dev/null)
if [ -f info.zip ]; then echo 'error deleting old info.zip, bye'; exit 1; fi

# download, -f: does not create file in case of fail
(curl -f "${MY_URL}" --output info.zip)
if [ ! -f info.zip ]; then echo 'error downloading info.zip, bye'; exit 1; fi

if ! unzip info.zip; then echo 'error w/ wrong password, bye'; exit 1; fi

# proceed to copy files to ddh folder :)
#     run_ddh.sh -> for AWS credentials
#     tools/_macs_to_sn.yml -> all logger macs for this client



