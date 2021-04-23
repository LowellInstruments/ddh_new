# !/usr/bin/env python3

import subprocess as sp
import argparse
import sys
import yaml


if __name__ == '__main__':

    # grab optional YAML argument file containing <DDH wifi macs, SN> pairs
    print('python script to detect DDH w/ open SSH port in network')
    print('\tusage: python3 check_nmap_rpi.py --macs_to_sn ~/_wifi_macs_to_sn.yaml')
    parser = argparse.ArgumentParser()
    # example file entry -> b8:27:...a8: 2002501, mind trailing ':'
    parser.add_argument('--macs_to_sn', type=str)
    args = parser.parse_args()
    my_d = {}
    try:
        with open(args.macs_to_sn) as f:
            my_d = yaml.load(f, Loader=yaml.FullLoader)
    except (TypeError, FileNotFoundError, AttributeError):
        print('omitted or error on --macs_to_sn, using None')
    print('remember running this as root, nmap needs so')

    # nmap to detect open SSH raspberries in current network
    cmd = 'nmap -p 22 --open 192.168.0.0/24 | grep \'Raspberry\' | awk \'{ print $3 }\''
    rv = sp.run(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if not rv.stdout:
        sys.exit(0)

    # only keep macs strings of the previous nmap result
    macs = rv.stdout.split(b'\n')
    macs = [m.decode().lower() for m in macs if m]
    print('found {} Rpi macs, getting IPs...\n'.format(len(macs)))

    # show DDH wi-fi mac, IP and serial number, ARP answers contain '?' symbol
    for each_mac in macs:
        each_sn = my_d.setdefault(each_mac, 'unknown SN')
        cmd = 'arp -a | grep {}'.format(each_mac)
        rv = sp.run(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        # rv.stdout: b'? (192.168.0.162) at b8:27:eb:13:3f:d8...'
        each_ip = s = rv.stdout.decode().split()[1][1:-1]
        print(each_ip, each_mac, each_sn)
