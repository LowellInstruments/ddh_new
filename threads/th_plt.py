from settings import ctx
from threads.utils import json_mac_dns, mac_from_folder, json_get_span_dict
from threads.utils_plt import (
    plot,
    emit_error,
    emit_status,
    emit_start,
    emit_result, emit_msg)


def fxn(sig, args):
    ctx.sem_plt.acquire()
    ctx.sem_plt.release()
    ThPLT(sig, *args)


class ThPLT:
    def __init__(self, sig, fol, ax, ts, metric_pair):
        j = ctx.json_file
        lg = json_mac_dns(j, mac_from_folder(fol))
        sd = json_get_span_dict(j)
        emit_status(sig, 'PLT: thread launched')

        # try to plot any metric of a logger
        emit_start(sig)
        for pair in metric_pair:
            if plot(sig, fol, ax, ts, pair, sd, lg):
                emit_result(sig, True, None)
                return

            # plot went wrong
            a = (pair, ts, lg)
            e = 'PLT: no {}({}) plots for \'{}\''
            e = e.format(*a)
            emit_error(sig, e)
            e = 'cannot plot 1{} for \'{}\''
            e = e.format(ts, lg)
            emit_msg(sig, e)
            emit_result(sig, False, e)
