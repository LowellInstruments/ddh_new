import threading
import time

from ddh.settings import ctx
from ddh.threads.utils import (
    json_mac_dns,
    get_mac_from_folder_path,
    json_get_span_dict,
    wait_boot_signal,
    emit_error
)
from ddh.threads.utils_plt import plot


def _plot_data(w, plt_args):
    def _plot():
        fol, ax, ts, metric_pairs = plt_args
        j = ctx.app_json_file
        lg = json_mac_dns(j, get_mac_from_folder_path(fol))
        sd = json_get_span_dict(j)

        # -------------------------------------------------------
        # plot start
        rv = False
        for each_pair in metric_pairs:
            rv |= plot(w.sig_plt, fol, ax, ts, each_pair, sd, lg)
            # one plot went OK :)
            if rv:
                w.sig_plt.end.emit(True, None)
                return
        # -------------------------------------------------------

        # oops, all plots went wrong
        e = 'PLT: end -> can\'t plot anything for \'{}\''.format(lg)
        w.sig_plt.error.emit(e)

        # this is shown to GUI
        e = 'can\'t plot 1{} \'{}\''.format(ts, lg)
        w.sig_plt.end.emit(False, e)

    th = threading.Thread(target=_plot)
    th.start()


def loop(w, ev_can_i_boot):
    """ plots, when triggered """

    wait_boot_signal(w, ev_can_i_boot, 'PLT')

    while 1:
        # wait to be unblocked by a plot petition
        plt_args = w.qpo.get()
        time.sleep(1)
        ctx.sem_plt.acquire()
        _plot_data(w, plt_args)
        ctx.sem_plt.release()
