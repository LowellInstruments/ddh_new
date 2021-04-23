import glob
import os
from mat.data_converter import default_parameters, DataConverter


# place this script inside a DDH folder along with any .lid files to be converted
#   $ cd /home/pi/Desktop/<your_folder>
#   $ sudo python3 main_cnv.py
# this script will not convert already converted files


if __name__ == '__main__':
    fol = str(os.getcwd())
    # fol = '/home/joaquim/Desktop/04-ee-03-73-87-24'
    parameters = default_parameters()

    wc = fol + '/**/*.lid'
    lid_files = glob.glob(wc, recursive=True)
    wc = fol + '/**/*.csv'
    csv_files = glob.glob(wc, recursive=True)

    for f in lid_files:
        # build file name .csv
        _ = '{}_DissolvedOxygen.csv'.format(f.split('.')[0])

        if _ not in csv_files:
            try:
                # converting takes about 1.5 seconds per file
                DataConverter(f, parameters).convert()
                s = 'file {} conversion OK'.format(f)
                print(s)
            except (ValueError, Exception) as ve:
                e = 'file {} ERROR conversion -> {}'.format(f, ve)
                print(e)
