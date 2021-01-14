import os


def aws_get_credentials():
    # bash: export DDH_AWS_KEY
    h = os.environ.get('DDH_FTP_H')
    s = os.environ.get('DDH_FTP_U')

    # or, simulate it
    k = '_k'
    s = '_s'
    assert (k and s)
    return k, s

def aws_assert_credentials():
    return aws_get_credentials()