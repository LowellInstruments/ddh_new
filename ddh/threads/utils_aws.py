import os
import boto3
import glob
from logzero import logger as logzero_logger
from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import ClientError, NoCredentialsError


def aws_credentials_get():
    # bash: export DDH_AWS_NAME=whatever
    # pycharm: run configuration edit
    name = os.environ.get('DDH_AWS_NAME')
    key_id = os.environ.get('DDH_AWS_KEY_ID')
    secret = os.environ.get('DDH_AWS_SECRET')

    # todo: on production, restore this assert
    # assert (name and key_id and secret)
    return name, key_id, secret


def aws_credentials_assert():
    return aws_credentials_get()


def _get_bucket_objects_keys(cli, buk_name) -> dict:
    """ can return a filled dict, an empty dict or None """
    assert cli
    dict_objects = {}
    try:
        rsp = cli.list_objects_v2(Bucket=buk_name)
        contents = rsp['Contents']
        for each in contents:
            dict_objects[each['Key']] = each['Size']
        return dict_objects
    except ClientError:
        return None
    except KeyError:
        # empty folder
        return None


def _upload_objects_to_bucket(cli, usr_name, file_list: dict, buk_name):
    # file_list: {full_name: (size, short_name)}
    assert cli
    uploaded_ones = []
    for full_name, v in file_list.items():
        try:
            uploaded_ones.append(v[1])
            cli.upload_file(full_name, buk_name, v[1])
        except S3UploadFailedError:
            e = '\t{} not allowed to upload objects to {}'
            print(e.format(usr_name, buk_name))
            return None
    return uploaded_ones


def _diff_local_and_remote_objects(dlo, dro) -> dict:
    if not dro:
        dro = {}
    diff_dict = {}
    # dlo: AWS local objects, full path, must shorten (sh) pre-compare
    # dro: AWS remote objects, short path format
    for k, v in dlo.items():
        # sh: <mac>/<file.x>
        _ = k.rsplit('/', 2)
        sh = '{}/{}'.format(_[-2], _[-1])
        if sh not in dro.keys() or sh in dro.keys() and dro[sh] != v:
            # {long_name: (size, shortened_name)}
            diff_dict[k] = (v, sh)
    return diff_dict


def aws_check_connection_to_s3(cli, bkt_name):
    try:
        cli.head_bucket(Bucket=bkt_name)
        return True
    except (ClientError, NoCredentialsError) as e:
        logzero_logger.error('AWS: {}'.format(e))
        return False


def aws_ddh_sync(aws_name, aws_key_id, aws_secret, folder_to_sync, bkt=None, sig=None):
    assert(folder_to_sync != '.')

    # obtaining AWS S3 Client
    cli = boto3.client('s3',
                       region_name='us-east-1',
                       aws_access_key_id=aws_key_id,
                       aws_secret_access_key=aws_secret)

    # grab or generate bucket name
    bkt_name = bkt if bkt else 'bkt-{}'.format(aws_name)

    # check there is a connection
    if not aws_check_connection_to_s3(cli, bkt_name):
        e = 'AWS: cannot connect S3 as user \'{}\''
        if sig:
            sig.emit(e.format(aws_name))
        return None

    # build dict of remote keys and sizes
    dict_remote_objects = _get_bucket_objects_keys(cli, bkt_name)

    # build dict of local keys and sizes
    csv_local_keys = glob.glob(folder_to_sync + '/*/*.csv')
    lid_local_keys = glob.glob(folder_to_sync + '/*/*.lid')
    gps_local_keys = glob.glob(folder_to_sync + '/*/*.gps')
    list_local_keys = csv_local_keys + lid_local_keys + gps_local_keys
    list_local_keys = [i for i in list_local_keys if os.path.isfile(i)]
    list_local_sizes = [os.stat(i).st_size for i in list_local_keys]
    dict_local_objects = dict(zip(list_local_keys, list_local_sizes))

    # useful note
    if not list_local_keys:
        s = 'note files to sync must be in {}/<sub-folder>/files.csv'
        print(s.format(folder_to_sync))

    # see differences between local and remote dicts
    dlo, dro = dict_local_objects, dict_remote_objects
    dict_diff = _diff_local_and_remote_objects(dlo, dro)

    # upload the local ones missing in remote bucket
    return _upload_objects_to_bucket(cli, aws_name, dict_diff, bkt_name)
