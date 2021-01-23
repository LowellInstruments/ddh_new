# GPLv3 License
# Copyright (c) 2018 Lowell Instruments, LLC, some rights reserved

from setuptools import setup
from ddh.settings.version import VER_SW

setup(name='ddh',
      version=VER_SW,
      description='DDH for BLE loggers from Lowell Instruments',
      author='Lowell Instruments',
      author_email='joaquim@lowellinstruments.com',
      packages=['ddh'],
      install_requires=[
                        'matplotlib==3.3.3',
                        'wifi==0.3.8',
                        'pandas',
                        'iso8601==0.1.12',
                        'gpiozero==1.5.0',
                        'logzero==1.5.0',
                        'tzlocal',
                        'Fiona==1.8.13.post1',
                        'boto3',
                        'PyYAML',
                        'parse',
                        'PyQt5',
                        # careful lowell-mat master OR dev branch
                        'lowell-mat@git+https://github.com/LowellInstruments/lowell-mat.git@dev',
                        'pytest'
                        ],
      classifiers=[
          "Environment :: Win32 (MS Windows)",
          "Environment :: X11 Applications",
          "Environment :: X11 Applications :: Qt",
          "Intended Audience :: Science/Research",
          "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
          "Operating System :: MacOS :: MacOS X",
          "Operating System :: POSIX :: Linux",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.6",
      ])
