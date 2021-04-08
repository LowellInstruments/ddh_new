#!/usr/bin/env bash

echo ''
(cd /home/pi/li/ddh) || (echo "no ddh folder"; exit 1)
(cp run_ddh.sh .. && cp ddh/settings/ddh.json ..) || (echo "bad: no files to copy"; exit 1)
(git reset --hard && git pull) || (echo "bad: git"; exit 1)
(mv ../run_ddh.sh . && mv ../ddh.json ddh/settings) || (echo "bad: restoring files"; exit 1)
printf "\n\tdone! error flag = %d\n" $?

