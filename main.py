import pathlib
import signal
import sys
from PyQt5.QtWidgets import QApplication
from settings import ctx
from settings.ctx import only_one_instance
from gui.main_window import DDHQtApp, on_ctrl_c


if __name__ == "__main__":
    # system checks
    only_one_instance('ddh')
    assert sys.version_info >= (3, 5)

    # common application context
    r = pathlib.Path.cwd()
    ctx.app_root_folder = r
    ctx.dl_files_folder = r / 'dl_files/'
    ctx.app_conf_folder = r / 'settings/'
    ctx.json_file = r / 'settings/ddh.json'
    ctx.db_his = str(r / 'db/db_his.db')
    ctx.db_plt = str(r / 'db/db_plt.db')
    ctx.db_blk = str(r / 'db/db_blk.db')

    # catch control + c
    signal.signal(signal.SIGINT, on_ctrl_c)

    # PyQt5-enabled app
    app = QApplication(sys.argv)
    ex = DDHQtApp()
    ex.show()
    sys.exit(app.exec_())
