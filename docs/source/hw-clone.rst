.. _hw-clone:


Clone it
########

Prepare one SSD with the instructions in :ref:`hw-build`.


In your DDH, install rpi-clone from github. Connect another SSD to USB port and:

.. code:: bash
    
    $ rpi-clone sdb


Now, after cloining, install a remote control solution such as `DWService <https://www.dwservice.net>`. Its installer
may already be present in the home folder under the name `dwagent.sh`.
