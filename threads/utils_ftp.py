import os
from ftplib import FTP
from ftplib import all_errors as ftp_errors
from pathlib import PurePosixPath, Path

from threads.utils import emit_update, emit_status, emit_error


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


def ftp_get_credentials():
    # bash: export DDH_FTP_H='ftp._.com'
    _h = os.environ.get('DDH_FTP_H')
    _u = os.environ.get('DDH_FTP_U')
    _p = os.environ.get('DDH_FTP_P')

    # or, simulate it
    _h = '_h'
    _u = '_u'
    _p = '_p'
    assert (_h and _u and _p)
    return _h, _u, _p


def ftp_assert_credentials():
    ftp_get_credentials()


def ftp_sync(sig, local_folder: str, cred_folder: str) -> bool:
    host = ftp_get_credentials()

    try:
        s = 'FTP: syncing {}'.format(local_folder)
        emit_status(sig, s)
        s = 'FTP syncing'
        emit_update(sig, s)

        wc = ['**/*.lid', '**/*.csv', '**/*.gps']
        for _ in wc:
            ff = list(Path(local_folder).glob(_))
            ul = FileUploader(host, local_folder, '/')
            ul.register_observer(_rep)
            ul.upload_files(ff)

        s = 'FTP: OK'
        emit_status(sig, s)
        s = 'FTP OK'
        emit_update(sig, s)
        return True

    except ftp_errors as fe:
        e = 'FTP: error'
        emit_error(sig, e)
        emit_update(sig, e)
        print('ftplib error: {}'.format(fe))
        return False

    except (OSError, TypeError) as os_e:
        e = 'FTP: some error'
        emit_error(sig, e)
        emit_update(sig, e)
        print('ftplib OSerror: {}'.format(os_e))
        return False


if __name__ == '__main__':
    import time
    while 1:
        ftp_sync(None, '../dl_files/', '../settings/')
        time.sleep(1)
        print('.')
