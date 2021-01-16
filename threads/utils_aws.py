import os
import boto3
import glob
from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import ClientError


def aws_get_credentials():
    # bash: export DDH_AWS_NAME=whatever
    name = os.environ.get('DDH_AWS_NAME')
    key_id = os.environ.get('DDH_AWS_KEY_ID')
    secret = os.environ.get('DDH_AWS_SECRET')

    # testing
    if not name:
        name = 'usr-mla'
        key_id = 'AKIA2SU3QQX6WO5MAHVN'
        secret = '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'
        print('TESTING AWS with {}'.format(name))


    assert (name and key_id and secret)
    return name, key_id, secret


def aws_assert_credentials():
    return aws_get_credentials()


def check_my_aws_s3_connection():
    s3 = boto3.resource('s3')
    bucket = s3.Bucket('bucket-to-test-connection')
    if bucket.creation_date:
        return True
    return False


def get_bucket_objects_keys_as_dict(cli, buk_name):
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


def upload_objects_to_bucket(cli, usr_name, file_list: dict, buk_name):
    # file_list: {full_name: (size, short_name)}
    assert cli
    for f in file_list:
        try:
            # todo: do the proper dictionary indexing key, values
            cli.upload_file(f, buk_name, f)
        except S3UploadFailedError:
            e = '\t{} not allowed to upload objects to {}'
            print(e.format(usr_name, buk_name))


def diff_dict_local_and_remote_objects(dlo, dro):
    if not dro:
        dro = {}
    diff_dict = {}
    # dro: AWS remote objects, shortened path format
    # dlo: AWS local objects, full path format so shorten before compare
    # todo: compare shortened
    for k, v in dlo.items():
        if k not in dro.keys() or k in dro.keys() and dro[k] != v:
            diff_dict[k] = v
    # todo: we should do a dict with entries:
    # {long_name: (size, shortened_name)}
    return diff_dict


def check_connection_to_aws_s3(cli, bkt_name):
    try:
        cli.head_bucket(Bucket=bkt_name)
        return True
    except ClientError:
        return False


def aws_ddh_sync(aws_name, aws_key_id, aws_secret, folder_to_sync):
    # obtaining AWS S3 Client
    cli = boto3.client('s3',
                       region_name='us-east-1',
                       aws_access_key_id=aws_key_id,
                       aws_secret_access_key=aws_secret)

    # check there is a connection
    bkt_name = 'bkt-{}'.format(aws_name.split('-')[1])
    if not check_connection_to_aws_s3(cli, bkt_name):
        print('cannot connect our AWS S3')
        return 1

    # build dict of remote keys and sizes
    dict_remote_objects = get_bucket_objects_keys_as_dict(cli, bkt_name)

    # build dict of local keys and sizes
    csv_local_keys = glob.glob(folder_to_sync + '/*/*.csv')
    lid_local_keys = glob.glob(folder_to_sync + '/*/*.lid')
    gps_local_keys = glob.glob(folder_to_sync + '/*/*.gps')
    list_local_keys = csv_local_keys + lid_local_keys + gps_local_keys
    list_local_keys = [i for i in list_local_keys if os.path.isfile(i)]
    list_local_sizes = [os.stat(i).st_size for i in list_local_keys]
    dict_local_objects = dict(zip(list_local_keys, list_local_sizes))

    # see differences between local and remote dicts
    dlo, dro = dict_local_objects, dict_remote_objects
    dict_diff = diff_dict_local_and_remote_objects(dlo, dro)

    # upload the local ones missing in remote bucket
    upload_objects_to_bucket(cli, aws_name, dict_diff, bkt_name)

    return 0
