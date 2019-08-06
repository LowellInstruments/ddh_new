# Deck Data Hub
BLE-enabled GUI software interfacing to MAT loggers.

## Getting Started
These instructions will get you up and running.

## Prerequisites
- Python v3.5 or higher
- Linux bluez Bluetooth Stack

## Developing
Bluetooth development may require permissions. To allow tim to
develop with pycharm.sh, for example, add to sudoers:
- tim  ALL=NOPASSWD:/home/tim/pycharm-community-2019.2/bin/pycharm.sh

## Installing
For Raspbian (2018-11-13):
```
sudo apt-get install libatlas3-base libglib2.0-dev python3-pyqt5
pip3 install -r requirements_rpi.txt
```
For Debian / Ubuntu x64 installation:
```
sudo apt-get install libatlas3-base libglib2.0-dev
pip3 install -r requirements_x64.txt
```
This application is expected to be Docker contained in the next future.

## Running
This application requires Bluetooth permissions. A quick way to run it may be:
```
sudo -E python3 ddh_main.py
```

## Versioning
This application is expected to use [SemVer](http://semver.org/). 

## License
This project is licensed under GPL License - see the [LICENSE.md](LICENSE.md) file for details
