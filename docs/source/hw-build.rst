.. _hw-build:


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
* `DWService <https://www.dwservice.net>`_ OR nomachine.tar.gz -> /home/pi/Downloads

       
Boot the DDH / raspberry.

In your DDH, set its time & timezone with raspberry config tool.


In your DDH, install some required linux packages for desktop purposes:

.. code:: bash

    $ sudo apt update
    $ sudo apt install xscreensaver matchbox-keyboard


In your DDH, obtain and install the cell and GPS script from SixFab.

.. code:: bash

    $ wget https://raw.githubusercontent.com/sixfab/Sixfab_PPP_Installer/master/ppp_install_standalone.sh
    $ sudo chmod +x ppp_install_standalone.sh
    $ sudo ./ppp_install_standalone.sh


.. warning::
    When using Twilio cards, ensure they are in the 'Ready' state. The 'New' state is not enough.


In your DDH, test Sixfab Hat Internet-via-cell capabilities by running:

.. code:: bash

    $ ifmetric ppp0 0
    $ ping www.google.com
    $ ip route get 8.8.8.8


In your DDH, test Sixfab Hat GPS capabilities by following these `official instructions <https://sixfab.com/gps-tracker-with-3g-4glte-shield/>`_.


In your DDH, test external hardware buttons by running:

.. code:: bash

    $ python3 tools/check_buttons.py


In your DDH, test `juice4halt` board. Just press the power button and wait for DDH to switch off. If the juice4halt has worked as expected, the following file should be present upon restart. Delete it to repeat the test.

``/home/pi/juice4halt/bin/j4h_flag`` 


In your DDH, monitor the GUI to be always kept running by monitoring it with a 2 minutes period adding this to crontab ``*/2 * * * * /home/pi/li/ddh/ddh_run.sh``:

.. code:: bash

    $ crontab -e
       

 
In your DDH, if you want, set a black background and remove icons and shortcuts by running:

.. code:: bash

    $ alacarte
