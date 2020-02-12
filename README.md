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

## Installing in RPi
```
sudo apt-get install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev
```
Next, run ddh_tools/ddh_update.py, which takes care of requirements.txt file.

This application is expected to be Docker contained in the next future.

## Running ddh_main.py
This application should start automatically after being installed.

## Versioning
This application is expected to use [SemVer](http://semver.org/). 

## License
This project is licensed under GPL License - see the [LICENSE.md](LICENSE.md) file for details
