#!/usr/bin/env bash


# ==============================================================
# runs a LI webservice for DDH to get their configuration files
# ==============================================================


# /bin/bash script_ddh_webservice.sh <vessel_name>>
MY_URL="http://127.0.0.1:5000/ddh/${1}/info.zip"
FIL="/dev/shm/info.zip"


# terminate script at first line failing
set -e && clear
[ $# -eq 0 ] || echo 'error: missing vessel name'


# deleting any thing previously downloaded
(rm $FIL 2> /dev/null)
[ -f $FIL ] || echo 'error deleting old info.zip'


# download, -f: does not create file upon failure
(curl -f "${MY_URL}" --output $FIL)
[ ! -f $FIL ] || echo 'error downloading info.zip'


# uncompress the password-protected file
if ! unzip $FIL; then echo 'error w/ wrong password, bye'; exit 1; fi


# next, copy files to ddh folder
#     run_ddh.sh -> for AWS credentials
#     tools/_macs_to_sn.yml -> all logger macs for this client
