# Deck Data Hub
On-deck BLE-enabled Graphical User Interface for Lowell Instruments' loggers.


## Developing
Coding in some distributions may require root or the following (beware security):
```
sudo setcap 'cap_net_raw,cap_net_admin+eip' `which hciconfig`
```

## Installing in RPi
```
sudo apt-get install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev python3-dev libgdal-dev
```
Next, run ddh_tools/ddh_update.py, which takes care of requirements.txt file.


## Running
Cron starts DDH automatically, otherwise:
```
sudo python3 ddh_main.py
```
This application is expected to be Docker contained soon.


## License
This project is licensed under GPL License - see LICENSE file for details.
