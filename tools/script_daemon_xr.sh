#!/usr/bin/env bash


# ======================
# runs a XML-RPC server
# ======================

# terminate script at first line failing
set -e
if [[ $EUID -ne 0 ]]; then echo "need to run as root";  exit 1; fi
FOL=/usr/local/lib/python3.7/dist-packages/mat


# pre-checks
echo ""
[ -f $FOL/xr.py ] || echo "bad: no xr.py"

# run XR, in its folder
(cd $FOL && python3 xr.py) || echo "bad: running xr.py"


# post-banner
printf "\n\tdone!\r\n"
