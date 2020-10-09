import json

if __name__ == '__main__':
    path_in = '../dl_files/MAT.cfg'
    path_out = '../dl_files/OUT.cfg'
    with open(path_in) as f:
        data = json.load(f)
        data['DFN'] = 'nop'

    if not data:
        quit()
    with open(path_out, 'w') as f:
        json.dump(data, f)
