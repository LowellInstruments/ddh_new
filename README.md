# Deck Data Hub
BLE Graphical User Interface for Lowell Instruments' loggers. Programmed in python3.

Intended to be used on fishing and research vessels and is fully automatic. It detects, downloads and plots loggers data and uploads their info to the cloud.

![alt text](ddh/gui/res/ddh_capture.png)

DDH are pre-configured upon delivery.

To install on a Raspberry:

```console
$ wget https://raw.githubusercontent.com/LowellInstruments/ddh/master/tools/script_install_rpi.sh
$ chmod +x script_install_rpi.sh
$ sudo script_install_rpi.sh
```

To install on a laptop or workstation, for development purposes:

```console
$ wget https://raw.githubusercontent.com/LowellInstruments/ddh/master/tools/script_install_dev.sh
$ chmod +x script_install_dev.sh
$ sudo script_install_dev.sh
```

It is left to the user to decide if a python virtual environment is used, or not.

DDH extended documentation can be found here (todo: add the readtedocs.io link).

## License
This project is licensed under GPL License - see LICENSE file for details.
