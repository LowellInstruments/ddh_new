.. _hw-clone:


Clone it
========

Prepare a DDH SSD with the instructions in :ref:`hw-build`. The rest of DDH will be cloned from this one.


1st way to clone
----------------

In your desktop computer, connect the prepared SSD, it will assign ``/dev/sda`` to it and a blank one, which will be assigned as ``/dev/sdb``. Mind the order. Then:

.. code:: bash

    $ sudo dd if=/dev/sda of=/dev/sdb bs=4M status=progress


2nd way to clone
----------------

In your DDH, look for utility ``SD card copier``. Your source disk will be ``/dev/sda``, your destination ``/dev/sdb``. Please make sure of this. Tick the ``generate new UUID`` box.

In another DDH, try to boot it with the newly cloned disk.


3rd way to clone
----------------

In your DDH, install rpi-clone from github.

.. code:: bash

    $ git clone https://github.com/billw2/rpi-clone.git
    $ cd rpi-clone
    $ sudo cp rpi-clone rpi-clone-setup /usr/local/sbin

In your DDH, connect another SSD to USB port and:

.. code:: bash

    $ rpi-clone sdb


Post-setup
----------

Now, after cloining, install a remote control solution such as `DWService <https://www.dwservice.net>`_. Its installer may already be present in the home folder under the name `dwagent.sh`.

You will need to connect once via SSH to this DDH in order to add it to your known SSH hosts file. Next, you can automate tasks on it with tools like ``parallel-ssh``. The ``phosts.txt`` file has one line entries in the format ``pi@X.X.X.X``. 

If you set SSH public key authentication, you can use ``parallel-ssh`` as follows. The -i flag means display std output and std error as execution of the command on each server complete.

.. code:: bash

    $ parallel-ssh -h phosts.txt -i "uptime"

If you did not set SSH public key authentication, you can use ``parallel-ssh`` as follows. The -A flag asks for a password. The -P flag prints immediately. You can also test -i flag.

.. code:: bash

    $ parallel-ssh -h phosts.txt -A -P "uptime"

Your DDH already has cell-network features enabled, so be careful with data usage, if any request to Internet is done. Recall removing your wi-fi networks from the cloned DDH, if so.


Booting the clone for the first time
------------------------------------

First time ever you boot a newly cloned SSD you may find a blank screen. Just unplug the power. Wait 5 minutes (ensure the RPI red led is off) and try again.




