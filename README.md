# Deck Data Hub
BLE-enabled GUI software interfacing to MAT loggers.

## Prerequisites
- Python v3.5 or higher
- Linux bluez Bluetooth Stack

## Installing in RPi
```
sudo apt-get install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev
```
git clone -b v1200 https://github.com/LowellInstruments/ddh.git
git clone -b v1200 https://github.com/LowellInstruments/lowell-mat.git 

## Running ddh_main.py
Cron daemon does it for you. Give it 2 minutes and otherwise:
```
$ cd /home/pi/li/ddh
$ ./ddh_run.sh
```
Do not sudo ./ddh_run.sh.

## License
This project is licensed under GPL License - see the [LICENSE.md](LICENSE.md) file for details
