#!/usr/bin/env bash

# terminate script at first line failing
set -e
if [[ $EUID -ne 0 ]]; then echo "need to run as root";  exit 1; fi
FOL=/usr/local/lib/python3.7/dist-packages/mat


# pre-checks
echo ""
[ -f $FOL/n2ll_agent.py ] || echo "bad: no n2ll_agent.py"

# run XR, in its folder
(cd $FOL && python3 n2ll_agent.py) || echo "bad: running n2ll_agent.py"

