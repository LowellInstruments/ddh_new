.. _hw-build:


Build it
########


In your desktop computer, get `Raspberry Pi Imager <https://www.raspberrypi.org/software/>`_. Connect a SSD external disk and flash it.


In your desktop computer, obtain DDH source code by typing the following:

.. code:: bash

    $ git clone https://github.com/LowellInstruments/ddh.git


In your desktop computer, copy the following files from within DDH 'tools' folder to locations behind '->' to the SSD disk, in its `rootfs` partition.

* rc.local -> /etc
* shutdown_script.py -> /home/pi/juice4halt/bin/shutdown_script.py
* dwagent.sh -> /home/pi/Downloads/dwagent.sh


In your desktop computer, edit the SSD file ``/etc/dhcpcd.conf`` in the SSD disk to add at the end:

    static domain_name_servers=8.8.4.4 8.8.8.8

In your desktop computer, unmount the SSD disk and boot the DDH / raspberry.

In your DDH, set its time & timezone. The initial setup tool that will pop-up during the first boot will ask you for this, along with a system password. Also, you will set a wi-fi network so the operating system can update itself to latest version.

.. warning:

	You may be prompted to restart DDH at some point during this procedure. Don't worry and press the upside hardware power button. This is better than suing a `reboot` command, since allows the power hats to shutdown all properly.


In your DDH, decide if you are going to use a USB keyboard to continue configuration or just enable SSH access
in the raspberry configuration tool.


In your DDH, install some required linux packages for desktop purposes. Open a terminal and type:

.. code:: bash

    $ sudo apt update
    $ sudo apt install xscreensaver matchbox-keyboard ifmetric joe


In your DDH, open the screensaver settings and completely disable it. Yes, you need to install a screensaver in order
to disable the screensaver settings.


In your DDH, obtain and install the cell and GPS script from SixFab. DDH uses a `hat` so during the installer you will probably choose an option such as `6: 3G/4G Base HAT` in the `ttyUSB3` port. You will also need to specify your SIM carrier, such as `wireless.twilio.com` and that it `does NOT need a user and password`. Finally, you say YES to enable `auto connect/reconnect service at R.Pi boot up?`.

.. code:: bash

    $ cd /home/pi/Downloads
    $ wget https://raw.githubusercontent.com/sixfab/Sixfab_PPP_Installer/master/ppp_install_standalone.sh
    $ sudo chmod +x ppp_install_standalone.sh
    $ sudo ./ppp_install_standalone.sh


.. warning::
    When using Twilio cards, ensure they are in the 'Ready' state. The 'New' state is not enough.


In your DDH, see cell capabilities were installed properly by typing the following, which should result in some lines like ``ppp0: flags=4305<UP,POINTOPOINT,RUNNING,NOARP,MULTICAST>  mtu 1500``.

.. code:: bash

    $ ifconfig | grep ppp0


In your DDH, test `juice4halt` board. Just press the power button and wait for DDH to switch off. If the juice4halt has worked as expected, the file ``/home/pi/juice4halt/bin/j4h_halt_flag``  should be present upon restart. Delete it to repeat the test.


In your DDH, even if at this point the DDH GUI software may no be installer yet, monitor the GUI to be always kept running by monitoring it with a 2 minutes period adding:

    */2 * * * * /home/pi/li/ddh/ddh_run.sh

to crontab by doing:

.. code:: bash

    $ crontab -e


In your DDH, if you want, set a black background and remove icons and shortcuts by running:

.. code:: bash

    $ alacarte


In your DDH, if you are NOT cloning, you can proceed to install a remote control solution such as `DWService <https://www.dwservice.net>`_. Recall we copied its installer file, so-called `dwagent.sh`, in the ``/home/pi/Downloads`` folder during the first steps of this document.


Now, we are done. Again, DDH come with all this done so probably this procedure will not be needed.
