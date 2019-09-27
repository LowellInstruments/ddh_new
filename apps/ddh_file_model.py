from PyQt5.QtCore import QAbstractTableModel, QModelIndex
from PyQt5.QtCore import Qt
from pathlib import Path


FILENAME = 0
STATUS = 1
SIZE = 2


class FileModel(QAbstractTableModel):
    def __init__(self, files, parent=None):
        super().__init__(parent=None)
        self.set_files(files)
        self.parent = parent

    def set_files(self, files):
        # this will wipe the status of the model
        self.files = files
        self._status = ['Unknown'] * len(self.files)

    def get_status(self, row):
        return self._status[row]

    def set_status(self, row, status):
        self._status[row] = status
        # self.modelReset.emit()  # this works
        index_left = self.createIndex(0, row)
        index_right = self.createIndex(2, row)
        self.dataChanged.emit(index_left, index_right)

    def delete(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        self.files.pop(row)
        self._status.pop(row)
        self.endRemoveRows()

    # pyqt method
    def rowCount(self, parent=None, *args, **kwargs):
        return len(self.files)

    # pyqt method
    def columnCount(self, parent=None, *args, **kwargs):
        return 3

    # pyqt method
    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            row, col = index.row(), index.column()
            if col == FILENAME:
                return self.files[row].name
            elif col == STATUS:
                return self._status[row]
            elif col == SIZE:
                return '{} KB'.format(self.files[row].stat().st_size // 1024)

    # pyqt method
    def headerData(self, p_int, orientation, role=None):
        header = ['File name', 'Status', 'Size']
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return header[p_int]

