# Deck Data Hub
BLE Graphical User Interface for Lowell Instruments' loggers.

Intended to be used on fishing and research vessels.

This GUI is fully automatic. It detects, downloads and plots loggers data and uploads their info to the cloud.

![alt text](ddh/gui/res/ddh_capture.png)

## Installing on RPi from scratch
You may not need this, DDH are delivered totally installed and configured.

Depending on platform, some pip packages such PyQt5 are unavailable, so ensure them with:
```
sudo apt-get update
sudo apt-get install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev python3-dev libgdal-dev
```
Next:
```
cd /home/pi/li/
# create python virtual environment inheriting packages installed above
python3 -m venv --system-site-packages venv
# you may need to install cartopy separately
pip3 install install Cartopy==0.18.0
# then run the automatic Lowell Instruments DDH installer
pip3 install git+https://github.com/LowellInstruments/li_installer.git@installer_ddh
# run DDH or crontab will do it automatically
cd ddh
sudo venv/bin/python3 main.py
```
You may also modify provided script run_ddh.sh.

## License
This project is licensed under GPL License - see LICENSE file for details.
