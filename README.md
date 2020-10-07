# Deck Data Hub
BLE Graphical User Interface for Lowell Instruments' loggers.
Intended to be used on fishing and research vessels.

![alt text](gui/res/ddh_capture.png)

## Installing on RPi
Depending on platform, some pip packages such PyQt5 may be unavailable, so ensure them with:
```
sudo apt-get update
sudo apt-get install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev python3-dev libgdal-dev
```
Next:
```
cd /home/pi/li/
# create python virtual environment inheriting 
# some difficult packages such as pyqt5 for Rpi
python3 -m venv --system-site-packages venv
# sudo install RPi dependencies so all users have same packages
sudo venv/bin/pip install -r ./requirements.txt
# you may need to install cartopy separately
sudo venv/bin/pip install install Cartopy==0.18.0
```

## Running on RPi
Double click or run file ddh_run.sh.

## Running on x64, for development
Don't use requirements.txt, as it is for Rpi.
Open project in PyCharm and install as asked by IDE.

## License
This project is licensed under GPL License - see LICENSE file for details.
