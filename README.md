# Deck Data Hub
BLE-enabled GUI software interfacing to MAT loggers.

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
Clone DDH repository, may be private. Install it with pip.
Clone MAT lib repository, proper branch, may be private. Move it to /home/pi/li/ddh. 

## Running ddh_main.py
Cron daemon should start automatically after being installed. Give it 2 minutes.
Otherwise:
```
cd /home/pi/li/ddh
sudo python3 ddh_main.py
```

## License
This project is licensed under GPL License - see the [LICENSE.md](LICENSE.md) file for details
