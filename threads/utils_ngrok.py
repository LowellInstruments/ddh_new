import ftplib
import subprocess as sp
import time


FTP_SERVER_URL = 'ftp.lowellinstruments.com'
FTP_USER = 'temp@lowellinstruments.com'
FTP_PASS = 'lowellftp100'


def create_ngrok_file(ngrok_name):
    try:
        with open(ngrok_name, 'w') as _:
            _.write('create_ngrok_file')
            return True
    except Exception as ex:
        print(ex)
        return False


def ftp_download_file(file_remote) -> bool:
    with ftplib.FTP(FTP_SERVER_URL) as ftp:
        try:
            ftp.login(FTP_USER, FTP_PASS)
            res = ftp.retrlines('RETR ' + file_remote)
            if res.startswith('226'):
                return True
            print('Download failed')
        except ftplib.all_errors as e:
            print('FTP error:', e)


def ftp_upload_file(path):
    with ftplib.FTP(FTP_SERVER_URL) as ftp:
        try:
            ftp.login(FTP_USER, FTP_PASS)
            with open(path, 'rb') as fp:
                res = ftp.storlines("STOR " + path, fp)
                if not res.startswith('226'):
                    print('Upload failed {}'.format(res))
        except ftplib.all_errors as e:
            print('FTP error:', e)


def ftp_delete_file(path):
    with ftplib.FTP(FTP_SERVER_URL) as ftp:
        try:
            ftp.login(FTP_USER, FTP_PASS)
            ftp.delete(path)
            return True
        except ftplib.all_errors as e:
            print('FTP error:', e)
            return False


def ftp_dir():
    with ftplib.FTP(FTP_SERVER_URL) as ftp:
        try:
            ftp.login(FTP_USER, FTP_PASS)
            files = []
            ftp.dir(files.append)
            for _ in files:
                print(_)
        except ftplib.all_errors as e:
            print('FTP error:', e)


def ngrok_req(who):
    create_ngrok_file(who)
    ftp_upload_file(who)


def ngrok_query_req(who):
    who_req = '{}_req'.format(who)
    return ftp_download_file(who_req)


def ngrok_maybe_free(who):
    who_free = '{}_free'.format(who)
    return ftp_delete_file(who_free)


def ngrok_query_ans(who, timeout):
    who_ans = '{}_ans'.format(who)
    _till = time.perf_counter() + timeout
    while 1:
        if time.perf_counter() >= _till:
            return None
        _rv = ftp_download_file(who_ans)
        if _rv:
            with open(who_ans, 'r') as f:
                end_point = f.readlines()
            print('-> ngrok got {}'.format(end_point))
            return end_point[0]
        time.sleep(1)


def ngrok_killall():
    cmd = 'killall ngrok'
    p = sp.Popen([cmd], shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    o, e = p.communicate()
    if o != b'' or e != b'':
        print(o, e)
        return False
    return True


def ngrok_fire(req_name):
    cmd = 'rm ./ngrok.log'
    _rv = sp.run([cmd], shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    cmd = 'ls ./ngrok.log'
    _rv = sp.run([cmd], shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if _rv.returncode == 0:
        print('cannot rm ./ngrok.log')
        return None

    # start ngrok
    port_nx_server = 4400
    cmd = './ngrok tcp {} -log=./ngrok.log &'.format(port_nx_server)
    sp.run([cmd], shell=True)
    time.sleep(2)
    cmd = 'ps -aux | grep ngrok'
    _rv = sp.run([cmd], shell=True, stdout=sp.PIPE)
    if _rv.returncode != 0:
        print('cannot fire ngrok')
        return None

    cmd = 'cat ngrok.log | grep \'started tunnel\''
    _rv = sp.run([cmd], shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if _rv.returncode != 0:
        print('cannot grep ngrok')
        return None

    g = _rv.stdout
    end_point = g.decode().strip().split('url=')[1]
    print('<- ngrok fire {}'.format(end_point))

    try:
        _name = '{}_ans'.format(req_name)
        with open(_name, 'w') as f:
            f.write(end_point)
        ftp_upload_file(_name)
    except:
        print('cannot upload ngrok')
        return None
