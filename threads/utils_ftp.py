from ftplib import FTP
from ftplib import all_errors as ftp_errors
from pathlib import PurePosixPath, Path


LOCAL_DIRECTORY = '/home/pi/li/ddh'


class FileUploader:
    def __init__(self, host, local_dir, remote_dir='/'):
        # host is a tuple of (address, username, password)
        self.local_dir = Path(local_dir)
        self.remote_dir = remote_dir
        self._connection = FTP(*host, timeout=15)
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
                self.notify_observers(i, len(files), 'done')
                continue
            else:
                self.notify_observers(i, len(files), 'uploading...')
                with file.open('rb') as fid:
                    self.connection().storbinary(
                        'STOR {}'.format(file.name),
                        fid)
                self.notify_observers(i, len(files), 'uploaded')
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


def _rep(i, n_files, status):
    s = 'FTP: file {} / {} {}'
    s = s.format(i + 1, n_files, status)
    # console_log.info(s)


def emit_conn(sig, s):
    if sig:
        sig.ftp_conn.emit(s)


def emit_status(sig, s):
    if sig:
        sig.ftp_status.emit(s)


def emit_error(sig, e):
    if sig:
        sig.ftp_error.emit(e)


def ftp_sync(sig):
    host = ("ftp.lowellinstruments.com",
            "MA_Lobster@lowellinstruments.com",
            "bY8oe6Hx3Aop")

    try:
        s = 'FTP: syncing'
        emit_conn(sig, s)

        ff = list(Path(LOCAL_DIRECTORY).glob('**/*.lid'))
        ul = FileUploader(host, LOCAL_DIRECTORY, '/')
        ul.register_observer(_rep)
        ul.upload_files(ff)

        ff = list(Path(LOCAL_DIRECTORY).glob('**/*.csv'))
        ul = FileUploader(host, LOCAL_DIRECTORY, '/')
        ul.register_observer(_rep)
        ul.upload_files(ff)

        ff = list(Path(LOCAL_DIRECTORY).glob('**/*.gps'))
        ul = FileUploader(host, LOCAL_DIRECTORY, '/')
        ul.register_observer(_rep)
        ul.upload_files(ff)

        s = 'FTP: OK'
        emit_conn(sig, s)
        return 0

    except ftp_errors as fe:
        e = 'FTP: error'
        emit_conn(sig, e)
        emit_error(sig, 'FTP: error')
        print('ftplib error: {}'.format(fe))
        return 1

    except (OSError, TypeError) as os_e:
        e = 'FTP: some error'
        emit_conn(sig, e)
        print('ftplib OSerror: {}'.format(os_e))
        return 1


if __name__ == '__main__':
    import time
    while 1:
        ftp_sync(None)
        time.sleep(1)
        print('.')

