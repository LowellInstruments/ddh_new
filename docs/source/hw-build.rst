.. _hw-setup:


Build it
########


In your desktop computer, get `Raspberry Pi Imager <https://www.raspberrypi.org/software/>`_. Connect a SSD external disk and flash it.


In your desktop computer, obtain DDH source code by:

.. code:: bash

    $ git clone https://github.com/LowellInstruments/ddh.git


DDH can also be run in a python virtualenv, we don't do this here.


Still in your desktop computer, copy the following files from DDH 'tools' folder in the downloaded github repo.

* rc.local -> /etc
* shutdown_script.py -> /home/pi/juice4halt/bin/shutdown_script.py

       
Boot the DDH / raspberry.

In your DDH, set its time & timezone with raspberry config tool.


In your DDH, install some required linux packages for desktop purposes:

.. code:: bash

    $ sudo apt update

    $ sudo apt install xscreensaver matchbox-keyboard


In your DDH, install some required linux packages for DDH DDH purposes:

.. code:: bash

    $ sudo apt-get install libatlas3-base libglib2.0-dev python3-pyqt5 libhdf5-dev python3-dev libgdal-dev
    $ pip3 install Cartopy==0.18.0


In your DDH, obtain and install the cell and GPS script from SixFab.

.. code:: bash

    $ wget https://raw.githubusercontent.com/sixfab/Sixfab_PPP_Installer/master/ppp_install_standalone.sh

    $ sudo chmod +x ppp_install_standalone.sh

    $ sudo ./ppp_install_standalone.sh


In your DDH, test DDH external hardware buttons by running:

.. code:: bash

    $ python3 tools/check_buttons.py


In your DDH, test DDH juice4halt board. Just press the power button and wait for DDH to switch off. If the juice4halt has worked as expected, the following file should be present upon restart. Delete it to repeat the test.

``/home/pi/juice4halt/bin/j4h_flag`` 


In your DDH, install a remote control soluction like `DWService <https://www.dwservice.net>`_.


In your DDH, monitor the GUI to be always kept running by monitoring it with a 2 minutes period adding this to crontab ``*/2 * * * * /home/pi/li/ddh/ddh_run.sh``:

.. code:: bash

    $ crontab -e
       

 
In your DDH, if you want, set a black background and remove icons and shortcuts by running:

.. code:: bash

    $ alacarte


In your DDH, install rpi-clone from github. Connect another SSD to USB port and:

.. code:: bash
    
    $ rpi-clone sdb


And, you are good to go.

