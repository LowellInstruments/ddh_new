import subprocess as sp


if __name__ == '__main__':
    print('please remember to run this as root')
    print('scanning network for Raspberry computers...')
    cmd = 'nmap -p 22 --open 192.168.0.0/24 | grep \'Raspberry\' | awk \'{ print $3 }\''
    rv = sp.run(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.stdout:
        macs = rv.stdout.split(b'\n')
        macs = [m for m in macs if m]
        s = 'found {} Raspberry macs, getting IP addresses...\n'
        print(s.format(len(macs)))

        for each_mac in macs:
            cmd = 'arp -a | grep {}'.format(each_mac.decode().lower())
            rv = sp.run(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
            # rv.stdout: b'? (192.168.0.162) at b8:27:eb:13:3f:d8...'
            each_ip = s = rv.stdout.decode().split()[1][1:-1]
            print(each_ip)
