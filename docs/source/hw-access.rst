.. _hw-access:


Access it
=========

Recall we copied its installer file, so-called `dwagent.sh`, in the ``/home/pi/Downloads`` folder during the first steps of this document. We will run the installed contained in such file so we can access DDH worldwide. But first, let's configure SSH.

You will need to connect once via SSH to this DDH in order to add it to your known SSH hosts file. Next, you can automate tasks on it with tools like ``parallel-ssh``. The ``phosts.txt`` file has one line entries in the format ``pi@X.X.X.X``. 

If you set SSH public key authentication, you can use ``parallel-ssh`` as follows. The -i flag means display std output and std error as execution of the command on each server complete.

.. code:: bash

    $ parallel-ssh -h phosts.txt -i "uptime"

If you did not set SSH public key authentication, you can use ``parallel-ssh`` as follows. The -A flag asks for a password. The -P flag prints immediately. You can also try -i flag.

.. code:: bash

    $ parallel-ssh -h phosts.txt -A -P "uptime"

You probably need to copy your AWS credentials. They are inside file ``run_ddh.sh``, which should have been provided for you by Lowell Instruments. Easiest way to do it:

.. code:: bash

    $ parallel-scp -h phosts.txt ./run_ddh.sh /home/pi/li/ddh/run_ddh.sh

Finally, install DWService. If you cloned this DDH from an existing one, run the 2 lines next. Otherwise, you only need to run the second one:

.. code:: bash

    $ sudo ./dwagent.sh uninstall
    $ sudo ./dwagent.sh -silent user=<YOUR_USER@HERE> password=<YOUR_PASS_HERE> name=<DDH_UNIQUE_SERIAL_NAME_HERE>

And should appear in your DWService Agents page.

.. note::

    Your DDH already has cell-network features enabled, so be careful with data usage, if any request to Internet is done. Recall removing your wi-fi networks from the cloned DDH, if so.






