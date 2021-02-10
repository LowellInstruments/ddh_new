Developing it
#############

The source code of the DDH is organized in a modular manner. We can directly match a couple of source
files to each of the information displayed in the first tab. For the sake of example, we will comment
the code about the Internet connectivity feature of the DDH, that is, the code behind this icon.


.. figure:: img_sync_color.png
    :width: 200px
    :align: center
    :height: 200px
    :alt: alternate text
    :figclass: align-center

    Network connectivity icon


The code for the networking feature is in 2 files, so called th_net.py and utils_net.py. The former
is about the behavior, what the networking feature does. The latter is about the how. The th_net.py file
consists of a single function, which executes forever the same task, without blocking. The networking
feature is about choosing the most economic way to keep internet connectivity. Thus, the DDH will try to
use wi-fi whenever possible. If this is not possible, for example when the DDH is on a vessel at sea
and there is no Access Point or hot spot available, it will switch to cell connectivity. If this is not
possible, which is not common, will fallback to no connectivity. This connectivity check runs every couple
minutes.


 .. code-block:: python
   :linenos:
   :caption: th_net.py
   :emphasize-lines: 2,5,11,13,15

    def loop(w, ev_can_i_boot):
        wait_boot_signal(w, ev_can_i_boot, 'NET')

        while 1:
            if not linux_is_rpi():
                s = '{}'.format(net_get_my_current_wlan_ssid())
                w.sig_net.update.emit(s)
                time.sleep(120)
                continue

            ctx.sem_ble.acquire()
            ctx.sem_aws.acquire()
            net_check_connectivity(w.sig_net)
            ctx.sem_aws.release()
            ctx.sem_ble.release()
            time.sleep(120)


In line 2, we wait the main thread to allow us to boot. This is to set some order in the thread booting
sequence. Line 4 starts the forever loop. As the DDH software can also be run in a traditional Linux box,
for example when developing it, we check if we are in a Raspberry pi environment, where no cell hat is
expected, so the networking code responsibility stops here.


In case we are in a Raspberry pi environment, lines 11 and 12 query other threads if they are done.
Since the DDH can run even in older Raspberry pi architectures, it is a good idea to do not interrupt
any time-sensitive code, such as the Bluetooth one. With this locking acquire and release (lines 14 and 15)
mechanism, we can ensure the more sensitive tasks will have the processing capabilities for them. In line 16,
we just wait some time until we fill adequate to re-run all this code. We don't need to check
connectivity every second, we can do this, for example, every 2 minutes, that is, 120 seconds.


The core line in this snippet is line 13, which already resides in the net_utils.py file. As mentioned,
files which name starts with 'th_code' represent what the code does, while file names ending with
'code_utils.py' files represent how the code does it.


Let's see file 'net_utils.py' next.


 .. code-block:: python
   :linenos:
   :caption: net_utils.py / function: net_check_connectivity
   :emphasize-lines: 2,5,11

    def net_check_connectivity(sig=None):
        nt = _net_get_via_to_internet()

        if nt == 'wifi':
            ssid = _net_get_my_current_wlan_ssid()
            emit_update(sig, '{}'.format(ssid))
            emit_status(sig, 'NET: wi-fi {}'.format(ssid))
            return

        # in case via is 'cell' or 'none'
        _net_switch_via_to_internet(sig, org=nt)
        emit_update(sig, '{}'.format(nt))
        emit_update(sig, 'NET: {}'.format(nt))


In line 2, we try to know the DDH's current via to the Internet. If it is wi-fi, we are good to go. In line 5
we display, or emit, the wi-fi name, or ESSID, and leave. DDH is programmed in PyQt5, and 'emit' is the proper way so
threads do not need to take care of GUI things. They emit the information, and some other thread, in our case
the code in main_windows.py, collects and displays it.


If wi-fi connectivity is not available, line 11 attempts a switch to cell connectivity. While the connectivity
code is not intended to be modified, its complexity is about the same of the shown in this page.


Similarly, other threads such as 'th_ble.py' contain what is to be done in terms of Bluetooth Low Energy, such
as detecting and downloading loggers, as we show in the following snippet in lines 4 and 9. In this case, and accordingly
to what we just explained, the how-to-do-it code of such thread resides in the file 'utils_ble.py'.


 .. code-block:: python
   :linenos:
   :caption: th_ble.py
   :emphasize-lines: 4,9

    while 1:
        try:
            # scan stage
            macs = _scan_loggers(w, h, whitelist, mb, mo)
            if not macs:
                continue

            # download stage
            _download_loggers(w, h, macs, mb, mo, (ft_s, ft_sea_s))


The `'macs'` variable is the one containing the loggers that are going to be queried, and downloaded.
This `'scan_loggers'` function already filtered the loggers already done recently.
For the sake of clarity, in this snippet we have omitted some variables collection. For example, the variable
`'h'` corresponds to the HCI interface explained in the DDH configuration section: :ref:`sw-configuring`
