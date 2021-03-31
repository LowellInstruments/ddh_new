import subprocess as sp
import argparse
import sys
import yaml


if __name__ == '__main__':
    """ this script detects DDH with open SSH port in current network """

    # argument parses for optional YAML file containing DDH macs
    # ex: macs_to_sn.yaml entry -> b8:27:...a8: 2002501, mind trailing ':'
    print('usage: python3 check_nmap_rpi.py --macs_to_sn ~/macs_to_sn.yaml')
    parser = argparse.ArgumentParser()
    parser.add_argument('--macs_to_sn', type=str)
    args = parser.parse_args()
    dict_macs_to_sn = {}
    try:
        with open(args.macs_to_sn) as f:
            dict_macs_to_sn = yaml.load(f, Loader=yaml.FullLoader)
    except (TypeError, FileNotFoundError, AttributeError):
        print('omitted or error on --macs_to_sn, using None')

    # some banners
    print('please remember to run this as root')
    print('scanning network for Raspberry computers...')

    # run nmap to detect DDH with open SSH in the current network
    cmd = 'nmap -p 22 --open 192.168.0.0/24 | grep \'Raspberry\' | awk \'{ print $3 }\''
    rv = sp.run(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)

    if rv.stdout:
        # from all SSH open ports in the network, only keep DDH (RPi) results
        macs = rv.stdout.split(b'\n')
        macs = [m for m in macs if m]
        s = 'found {} Raspberry macs, getting IP addresses...\n'
        print(s.format(len(macs)))

        # display DDH mac and serial number
        for each_mac in macs:
            each_mac = each_mac.decode().lower()
            each_sn = dict_macs_to_sn.setdefault(each_mac, 'unknown SN')

            cmd = 'arp -a | grep {}'.format(each_mac)
            rv = sp.run(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
            # rv.stdout: b'? (192.168.0.162) at b8:27:eb:13:3f:d8...'
            each_ip = s = rv.stdout.decode().split()[1][1:-1]
            print(each_ip, each_mac, each_sn)
