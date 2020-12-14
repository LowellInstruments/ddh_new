import threading
from settings import ctx
from threads.utils import json_mac_dns, mac_from_folder, json_get_span_dict
from threads.utils_plt import plot


def _plot_data(w, plt_args):
    def _plot():
        fol, ax, ts, metric_pair = plt_args
        j = ctx.json_file
        lg = json_mac_dns(j, mac_from_folder(fol))
        sd = json_get_span_dict(j)

        # plot
        for pair in metric_pair:
            if plot(w.sig_plt, fol, ax, ts, pair, sd, lg):
                w.sig_plt.end.emit(True, None)
                return

            # oops, went wrong
            e = 'PLT: no {}({}) plots for \'{}\''.format(pair, ts, lg)
            w.sig_plt.error.emit(e)
            e = 'cannot plot 1{} for \'{}\''.format(ts, lg)
            w.sig_plt.msg.emit(e)
            w.sig_plt.end.emit(False, e)

    th = threading.Thread(target=_plot)
    th.start()
    th.join()


def loop(w):
    w.sig_plt.status.emit('SYS: PLT thread started')
    while 1:
        # w: Qt5 windowed app, wait for it to ask a plot
        plt_args = w.qpo.get()
        ctx.sem_plt.acquire()
        ctx.sem_plt.release()
        _plot_data(w, plt_args)
