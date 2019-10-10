import json
from ftp_sync.ddh_file_uploader import FileUploader
from pathlib import Path

"""
An example of using the file uploader class. See file_uploader_gui for 
use in a GUI.
"""

LOCAL_DIRECTORY = 'C:/Projects/ddh/dl_files'


def main():
    with open('../ddh.json') as f:
        config = json.load(f)

    host = (config['ftp_site'],
            config['ftp_username'],
            config['ftp_password'])

    files = list(Path(LOCAL_DIRECTORY).glob('**/*.*'))
    uploader = FileUploader(host, LOCAL_DIRECTORY, '/')
    uploader.register_observer(update)
    uploader.upload_files(files)


def update(i, n_files, status):
    print('File {} of {} reports {}'.format(i + 1, n_files, status))


if __name__ == '__main__':
    main()
