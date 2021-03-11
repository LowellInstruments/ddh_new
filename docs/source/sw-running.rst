.. _sw-using:


Running it
==========

The DDH is executed automatically by the operating system. More precisely, its ``run_ddh.sh``, as explained in Section :ref:`software`. 

.. note::

    The ``run_ddh.sh`` file contains your AWS credentials. If they are not set within in, the DDH will not start. Ask us to provide this for you, if not yet.


The DDH operates autonomously and its Graphical User Interface of the DDH is very simple. It consists of 3 tabs.
The first tab summarizes the operation of the DDH.
The second tab shows the plots, of the downloaded data, if any.
The third tab is a history log displaying when and where each logger was last seen.


The first tab has 4 icons. Each icon displays the result of a thread in the source code.
The first icon is the GPS icon. This icon may be colored grey, when
no GPS signal is detected, brown, when the DDH is not at sea,
or blue, when it is. Next to it, we display GPS position and time. The DDH can synchronize
its time via GPS or NTP, this information is shown here, too.


.. image:: img_gps_land.png
    :width: 175px
    :align: center
    :height: 200px
    :alt: GPS icon


The second icon is the Bluetooth icon. These indicates the progress of the
detected logger, if any. This icon will show the scan, download and re-configuration
of each logger in sequence, all done automatically.


.. image:: img_blue_color.png
    :width: 200px
    :align: center
    :height: 200px
    :alt: BLE icon


The third icon is the Internet connectivity one. This show if the DDH has
either a cell Internet connection, a wi-fi Internet connection or none. It also
shows the status of the cloud file upload synchronization.


.. image:: img_sync_color.png
    :width: 200px
    :align: center
    :height: 200px
    :alt: Network icon


Finally, the fourth and last icon is about the data files downloaded from the loggers.
Such files have `'.lid`' extension and are binary. Once the DDH has them locally,
it will try to convert them to `'.csv`', as well as plot a summary of them. This icon
will show the status of both operations.


.. image:: img_plot_color.png
    :width: 200px
    :align: center
    :height: 200px
    :alt: Plot Icon


As mentioned, the DDH requires no intervention of any kind from the user.
It will automatically display data plots when the files are downloaded from loggers,
upload such files to the cloud, keep a history log about them, etc.
However, the DDH feature 3 buttons which can be used to modify the appearance of
the plotted data, although such data is uploaded to the cloud for the user to check it
at the office or lab more comfortably. The first button will switch between the data downloaded from
different loggers. The third button modifies the span of the plots
so the user can see the last hour of the downloaded data, last day, last week, last
month or last year. The second button is left for future use.


.. note:

	If you ever need to reboot the DDH, don't worry and press the upside hardware power button. This is better than suing a `reboot` shell command, since allows the power hats to shutdown all properly. Same thing to shutdown the DDH completely.