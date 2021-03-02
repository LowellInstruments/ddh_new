.. _hw-clone:


Clone it
########

Prepare one SSD with the instructions in :ref:`hw-build`.

In your DDH, look for utility ``SD card copier``. Your source disk will be ``/dev/sda``, your destination ``/dev/sdb``. Please make sure of this.

In another DDH, try to boot it with the newly cloned disk.

If the previous does NOT work, we can try another way.

In your DDH, install rpi-clone from github. 

.. code:: bash

    $ git clone https://github.com/billw2/rpi-clone.git 
	$ cd rpi-clone
	$ sudo cp rpi-clone rpi-clone-setup /usr/local/sbin

In your DDH, connect another SSD to USB port and:

.. code:: bash
    
    $ rpi-clone sdb


Now, after cloining, install a remote control solution such as `DWService <https://www.dwservice.net>`. Its installer
may already be present in the home folder under the name `dwagent.sh`.
