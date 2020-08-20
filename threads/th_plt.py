from context import ctx
from threads.utils import json_mac_dns, mac_from_folder
from threads.utils_plt import (
    plot,
    emit_error,
    emit_status,
    emit_start,
    emit_result, emit_msg)


def fxn(sig, args):
    if ctx.plt_ongoing:
        s = 'no plot, conversion in progress'
        emit_msg(sig, s)
        return

    ThPLT(sig, *args)


class ThPLT:
    def __init__(self, sig, fol, ax, ts, metric_pair):
        j = ctx.json_file
        ctx.lg_name = json_mac_dns(j, mac_from_folder(fol))
        lg = ctx.lg_name
        sd = ctx.span_dict
        emit_status(sig, 'PLT: thread launched')

        # try to plot any metric of a logger
        emit_start(sig)
        for pair in metric_pair:
            rv = plot(sig, fol, ax, ts, pair, sd, lg)
            if rv:
                emit_result(sig, True)
                return
            else:
                a = (pair, ts, lg)
                e = 'PLT: no {}({}) plots for \'{}\''
                e = e.format(*a)
                emit_error(sig, e)
                e = 'cannot plot 1 {} for {}, try manually'
                e = e.format(ts, lg)
                emit_msg(sig, e)

        # we could not plot any pair of metrics
        emit_result(sig, False)
