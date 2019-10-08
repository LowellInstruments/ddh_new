import sys
from PyQt5 import QtWidgets
from PyQt5 import QtCore
sys.path.append('../ddh')
from gui.file_table_ui import Ui_Form
from apps.ddh_file_model import FileModel
from apps.ddh_file_uploader import FileUploader
from pathlib import Path
from multiprocessing import Pipe, Process, freeze_support


class MainWindow(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.model = FileModel([])
        self.update_model()
        self.pushButton_sync.clicked.connect(self.sync)
        self.lineEdit_local.editingFinished.connect(self.update_model)
        self.lineEdit_pattern.editingFinished.connect(self.update_model)
        self.uploader = None
        self.show()

    def update_model(self):
        directory = self.lineEdit_local.text()
        pattern = self.lineEdit_pattern.text()
        files = list(Path(directory).glob(pattern))
        self.model.set_files(files)
        self.tableView.setModel(self.model)

    def resizeEvent(self, event):
        width = self.tableView.width()-25
        self.tableView.setColumnWidth(0, width/2)
        self.tableView.setColumnWidth(1, width/4)
        self.tableView.setColumnWidth(2, width/4)

    def sync(self):
        host = ('ftp.lowellinstruments.com',
                'jeff@lowellinstruments.com',
                'DDHftp5Woodland')
        self.uploader = UploadManager(
            host,
            Path(self.lineEdit_local.text()),
            self.lineEdit_remote.text(),
            files=self.model.files)
        self.uploader.update_signal.connect(self.status_update)
        self.uploader.start()

    def status_update(self, message):
        row, n_files, status = message
        self.progressBar.setValue((row+1)/n_files*100)
        self.model.set_status(row, status)


class UploadManager(QtCore.QThread):
    update_signal = QtCore.pyqtSignal(tuple)

    def __init__(self, *args, files):
        super().__init__()
        self.ftp_params = args
        self.files = files

    def run(self):
        self.receiver, self.sender = Pipe(duplex=False)
        self.ftp_process = FtpProcess(self.sender, self.ftp_params)
        self.worker_process = Process(
            target=self.ftp_process.upload, args=(self.files,))
        self.worker_process.start()
        while True:
            if self.receiver.poll(0.01):
                message = self.receiver.recv()
                if message == 'DONE':
                    break
                self.update_signal.emit(message)
            self.msleep(10)
        print('All done')


class FtpProcess:
    def __init__(self, pipe, ftp_params):
        self.pipe = pipe
        self.ftp_params = ftp_params

    def upload(self, files):
        self.uploader = FileUploader(*self.ftp_params)
        self.uploader.register_observer(self.update)
        self.uploader.upload_files(files)
        self.pipe.send('DONE')

    def update(self, i, n_files, status):
        self.pipe.send((i, n_files, status))


if __name__ == '__main__':
    freeze_support()
    app = QtWidgets.QApplication(sys.argv)
    mw = MainWindow()
    sys.exit(app.exec())
