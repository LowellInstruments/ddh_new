import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore
sys.path.append('../ddh')
from gui.file_table_ui import Ui_Form
from apps.ddh_file_model import FileModel
from apps.ddh_file_uploader import FileUploader
from pathlib import Path


class MainWindow(qtw.QWidget, Ui_Form):

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.update_model()
        self.pushButton_sync.clicked.connect(self.sync)
        self.lineEdit_local.editingFinished.connect(self.update_model)
        self.lineEdit_pattern.editingFinished.connect(self.update_model)
        self._upload_thread = QtCore.QThread()
        self.uploader = None
        self.show()

    def update_model(self):
        directory = self.lineEdit_local.text()
        pattern = self.lineEdit_pattern.text()
        self.model = FileModel(directory, pattern)
        self.tableView.setModel(self.model)

    def resizeEvent(self, event):
        width = self.tableView.width()-25
        self.tableView.setColumnWidth(0, width/2)
        self.tableView.setColumnWidth(1, width/4)
        self.tableView.setColumnWidth(2, width/4)

    def sync(self):
        self._upload_thread.quit()
        host = ('ftp.lowellinstruments.com',
                'jeff@lowellinstruments.com',
                'DDHftp5Woodland')
        self.uploader = FileUploader(host,
                                     Path(self.lineEdit_local.text()),
                                     self.lineEdit_remote.text())
        self.uploader.moveToThread(self._upload_thread)
        self.uploader.status.connect(self.status_update)
        self.uploader.upload_signal.connect(self.status_update)
        self._upload_thread.start()
        self.uploader.upload_files(self.model.files)

    def status_update(self, row, n_files, status):
        self.progressBar.setValue((row+1)/n_files*100)
        self.model.set_status(row, status)


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    sys.exit(app.exec())
