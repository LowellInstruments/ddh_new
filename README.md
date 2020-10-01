# Deck Data Hub
BLE Graphical User Interface for Lowell Instruments' loggers.
Intended to be used on fishing and research vessels.

![alt text](gui/res/ddh_capture.png)


## Installing on RPi
Depending on platform, some pip packages such PyQt5 may be unavailable, so ensure them with:
```
sudo apt-get install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev python3-dev libgdal-dev
```

Next, create a python virtual environment inheriting them and install python dependencies.
```
cd /home/pi/li/ddh
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r ddh/requirements_rpi.txt
```


## Installing on x64
Create virtualenv, no need to inherit system packages.
```
cd ddh
python3 -m venv venv
source venv/bin/activate
pip install -r ddh/requirements_x64.txt
```


## Running
Double click or run file ddh_run.sh.
This already takes care of virtual environments.


## License
This project is licensed under GPL License - see LICENSE file for details.
