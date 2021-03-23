import pathlib
import signal
import sys
from PyQt5.QtWidgets import QApplication
from ddh.settings import ctx
from ddh.settings.ctx import only_one_instance
from ddh.gui.main_window import DDHQtApp, on_ctrl_c


if __name__ == "__main__":
    # system checks
    only_one_instance('ddh')
    assert sys.version_info >= (3, 5)

    # common application context
    r = pathlib.Path.cwd() / 'ddh'
    ctx.app_dl_folder = r / 'dl_files/'
    ctx.app_conf_folder = r / 'settings/'
    ctx.app_logs_folder = r / 'logs/'
    ctx.app_res_folder = r / 'gui/res/'
    ctx.app_json_file = r / 'settings/ddh.json'
    ctx.db_his = str(r / 'db/db_his.db')
    ctx.db_plt = str(r / 'db/db_plt.db')
    # shelve, do not change this extension
    ctx.db_color_macs = str(r / 'db/.color_macs.sl')

    # catch control + c
    signal.signal(signal.SIGINT, on_ctrl_c)

    # launch DDH PyQt5 app
    app = QApplication(sys.argv)
    ex = DDHQtApp()
    ex.show()
    sys.exit(app.exec_())
