from PyQt5.QtCore import QObject, pyqtSignal, QCoreApplication
from ftplib import FTP
from time import sleep
from pathlib import PurePosixPath, Path


"""
FileUploader will do a one-way sync (upstream) between a local folder and 
a remote FTP folder. 

Usage:
FileUploader requires a tuple containing an FTP server and credentials in the
following format: (ftp_address, username, password)
You must also specify an absolute path to the local folder you wish to 
sync. You can optionally provide a remote path on the server that the
local directory will sync into. If you don't provide a remote address, the 
root directory will be assumed.

Once you have created a FileUploader object, pass a list of Path objects
(from the pathlib library - the glob function is helpful here) to the 
upload_files method. NOTE: the files must be contained within local_dir 
specified during instantiation. Otherwise, an error will occur. Explicitly 
passing in a list is slightly awkward, but allows for more flexibility.
"""


class FileUploader:
    def __init__(self, host, local_dir, remote_dir='/'):
        # host is a tuple of (address, username, password)
        self.local_dir = Path(local_dir)
        self.remote_dir = remote_dir
        self._connection = FTP(*host)
        self.current_dir = ''
        self.mlsd = {}
        self.observers = []

    def register_observer(self, fcn):
        # observers must accept three params: file index, total files, status
        self.observers.append(fcn)

    def notify_observers(self, i, n_files, status):
        for observer in self.observers:
            observer(i, n_files, status)

    def connection(self):
        # put a connection check here, maybe this:
        # self._connection.voidcmd('NOOP')
        return self._connection

    def upload_files(self, files):
        for i, file in enumerate(files):
            relative_dir = file.relative_to(self.local_dir).parent
            self.change_dir(relative_dir)
            size = self.file_size(file.name)
            if size == file.stat().st_size:
                self.notify_observers(i, len(files), 'Done')
                continue
            else:
                self.notify_observers(i, len(files), 'Uploading...')
                with file.open('rb') as fid:
                    self.connection().storbinary(
                        'STOR {}'.format(file.name),
                        fid)
                self.notify_observers(i, len(files), 'Synced')
        self.connection().close()

    def change_dir(self, path):
        # make sure the path is in posix format for the ftp server
        ftp_path = PurePosixPath(self.remote_dir) / path
        if ftp_path == self.current_dir:
            return
        self.current_dir = ftp_path
        for parent in ftp_path.parts:
            try:
                self.connection().cwd(parent)
            except:
                self.connection().mkd(parent)
                self.connection().cwd(parent)

    def file_size(self, filename):
        if not self.mlsd.get(self.current_dir, None):
            self.mlsd[self.current_dir] = list(self.connection().mlsd())
        for remote_file_name, facts in self.mlsd[self.current_dir]:
            if filename == remote_file_name:
                return int(facts['size'])
        return 0
