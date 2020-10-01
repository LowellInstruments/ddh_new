# Deck Data Hub
On-deck BLE-enabled Graphical User Interface for Lowell Instruments' loggers.


## Version
This is v2100. MLA.


## Developing
Coding in some distributions may require root or the following (beware security):
```
sudo setcap 'cap_net_raw,cap_net_admin+eip' `which hciconfig`
```

## Installing on Rpi
```
sudo apt-get install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev python3-dev libgdal-dev
```
Just run scripts/ddh_update.py.


## Installing: generic
You may need also some similar apt-get as RPi case.
git clone https://github.com/LowellInstruments/bluepy.git
git clone -b v2100 https://github.com/LowellInstruments/lowell-mat.git


## Running on RPi
Cron starts DDH automatically, otherwise:
```
$ cd /home/pi/li/ddh
$ ./ddh_run.sh
```
Do not sudo ddh_run.sh.
Newer versions are docker contained or virtualenv contained.


## License
This project is licensed under GPL License - see LICENSE file for details.
