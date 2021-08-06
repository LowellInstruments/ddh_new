.. _hw-build:


Build it
========


In your desktop computer, get `Raspberry Pi Imager <https://www.raspberrypi.org/software/>`_. Connect a SSD external disk and flash it.


In your desktop computer, obtain some files for DDH configuration with:

.. code:: bash

    $ wget https://raw.githubusercontent.com/LowellInstruments/ddh/master/tools/rc.local
    $ wget https://raw.githubusercontent.com/LowellInstruments/ddh/master/tools/shutdown_script.py


In your desktop computer, move such files to locations behind '->' to the DDH SSD disk, in its `rootfs` partition.

* rc.local -> /etc
* shutdown_script.py -> /home/pi/juice4halt/bin/shutdown_script.py



In your desktop computer, unmount the SSD disk. 


In your DDH, boot the DDH / raspberry.


In your DDH, set its time & timezone. The initial setup tool that will pop-up during the first boot will ask you for this, along with a system password. Also, you will set a wi-fi network so the operating system can update itself to latest version.

.. warning:

	You may be prompted to restart DDH at some point during this procedure. Don't worry and press the upside hardware power button. This is better than suing a `reboot` command, since allows the power hats to shutdown all properly.


In your DDH, enable SSH access in the raspberry configuration tool.


In your DDH, install some required linux packages for desktop purposes. Open a terminal and type:

.. code:: bash

    $ sudo apt update
    $ sudo apt install -y xscreensaver matchbox-keyboard ifmetric joe git python-rpi.gpio


In your DDH, open the screensaver settings and completely disable it. Yes, you need to install a screensaver in order to disable the screensaver settings.

In your DDH, open ``/etc/resolv.conf`` as root and edit it so it only has the following content:

    nameserver 8.8.8.8
    nameserver 8.8.4.4

In your DDH, prevent changes to ``/etc/resolv.conf`` by doing:

.. code:: bash

    $ sudo chattr +i /etc/resolv.conf

Also, ensure ``/etc/rc.local`` can be run by doing:

.. code:: bash

    $ sudo chmod +x /etc/rc.local


In your DDH, obtain and install the cell and GPS script from SixFab. DDH uses a `hat` so during the installer you will choose an option such as `6: 3G/4G Base HAT`. The installer will also ask about the USB port the cell shield is connected to. Be sure to type in `ttyUSB3`. Do not just accept, since `ttyUSB3` does not seem to be the default. You will also need to specify your SIM carrier, such as `wireless.twilio.com` and that it `does NOT need a user and password`. Finally, you say YES to enable `auto connect/reconnect service at R.Pi boot up?`.

.. code:: bash

    $ cd /home/pi/Downloads
    $ wget https://raw.githubusercontent.com/sixfab/Sixfab_PPP_Installer/master/ppp_install_standalone.sh
    $ sudo chmod +x ppp_install_standalone.sh
    $ sudo ./ppp_install_standalone.sh


.. warning::
    When using Twilio cards, ensure they are in the 'Ready' state. The 'New' state is not enough.


In your DDH, see cell communication-capabilities were installed properly by typing the followingcode. Once done, its answer must to something similar to ``ppp0: flags=4305<UP,POINTOPOINT,RUNNING,NOARP,MULTICAST>  mtu 1500``.

.. code:: bash

    $ ifconfig | grep ppp0


In your DDH, test `juice4halt` board. Just press the power button and wait for DDH to switch off. If the juice4halt has worked as expected, the file ``/home/pi/juice4halt/bin/j4h_halt_flag`` should be present upon restart. Delete it to repeat the test. You can also see if the script has been run by rc.local with:


.. code:: bash

    $ systemctl status rc.local
    $ ps -aux | grep shutdown



In your DDH, do a:

.. code:: bash

    $ sudo pi


Even if at this point the DDH GUI software may not be installed yet, set the GUI to be always kept running by monitoring it with a 2 minutes period adding ``*/2 * * * * /home/pi/li/ddh/run_ddh.sh`` to crontab by:

.. code:: bash

    $ crontab -e


In your DDH, if you want, set a black background and remove icons and shortcuts by running:

.. code:: bash

    $ alacarte


Or, you can also do this from your desktop computer by knowing and replacing your ``<DDH_IP>`` and running:

.. code:: bash

    $ ssh -X pi@<DDH_IP> alacarte


In your desktop computer, you can add your public key to the DDH by generating it and copying to it.

.. code:: bash

    $ ssh-keygen
    $ ssh-copy-id -i ~/.ssh/id_rsa.pub pi@<DDH_IP>


In your DDH, if you don't plan to clone more DDH from the one you just prepared, you can proceed to section :ref:`hw-access`.


Now, we are done. Again, DDH come with all this done so probably the procedure explained in this section will not be needed.
