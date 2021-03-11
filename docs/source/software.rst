.. _software:


The DDH Software
================

The software is entirely written in python3 and comprises a Graphical User Interface, or GUI,
which main screen is shown next, built on top of a so-called MAT library from Lowell Instruments.
There is no need to understand or check the MAT library to use the DDH.


.. figure:: ddh_screenshot.png
    :width: 700px
    :align: center
    :height: 440px
    :alt: DDH Graphical User Interface
    :figclass: align-center

    The DDH Graphical User Interface


In the DDH project, loggers are intended to be attached to fishing equipment such as cages. As an application
example, when a fisherman arrives to a fishing spot, it recovers its lobster cage and hauls
it up to the fishing vessel. When the onboard DDH detects a logger, it records its current GPS position. Then,
it stops the logger, stopping a data collection which probably has been running for months. Next, it downloads,
checks and converts the binary data files in the logger as a CSV friendly format. Finally,
it re-setups the logger, performs sanity configuration checks and re-runs it so if the cage is re-deployed
the next data files recovered will start at the current precise time.


DDH are delivered with all the software already pre-installed. However, to install the DDH software on one
completely from scratch on a Raspberry:

.. code-block:: bash

    $ cd /home/pi/Downloads
    $ wget https://raw.githubusercontent.com/LowellInstruments/ddh/master/tools/script_install_rpi.sh
    $ chmod +x script_install_rpi.sh
    $ sudo ./script_install_rpi.sh

.. note::

    When on a DDH platform, recall to check crontab file with ``crontab -e`` (for editing) or ``crontab -l`` for displaying to see if the DDH gui is kept monitored, that is, restarted in case it crashes, if ever. (Un)comment the line depending on what you need.

To install on a laptop or workstation, for development purposes:

.. code-block:: bash

    $ wget https://raw.githubusercontent.com/LowellInstruments/ddh/master/tools/script_install_dev.sh
    $ chmod +x script_install_dev.sh
    $ sudo ./script_install_dev.sh


It is left to the user to decide if a python virtual environment is used, or not.


The rest of this Software section introduces DDH configuration and development.


.. toctree::
   :maxdepth: 1

   sw-configuring
   sw-running
   sw-developing
