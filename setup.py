import os
from distutils.core import setup

import pathlib
import py2exe
import sys

if len(sys.argv) == 1:
    sys.argv.append("py2exe")
py2exe_options = { 'includes': ['pyttsx.drivers.sapi5', 'win32com.gen_py.C866CA3A-32F7-11D2-9602-00C04F8EE628x0x5x4'],
               'typelibs': [('{C866CA3A-32F7-11D2-9602-00C04F8EE628}', 0, 5, 4)] }

tcl__path = '{}\\tcl\\tcl8.5\\init.tcl'.format(os.path.dirname(sys.executable))
setup(
    zipfile=None,
    windows=[{"script": 'SpeedReader.py'}],
    options = {'py2exe': py2exe_options},
    # data_files=[tcl__path],
    requires=['pyttsx'])

import zipfile

def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            destination_path = pathlib.Path(*pathlib.Path(os.path.join(root, file)).parts[1:])
            print(destination_path)
            ziph.write(os.path.join(root, file), destination_path.__str__())

if __name__ == '__main__':
    zipf = zipfile.ZipFile('SpeedReader.zip', 'w', zipfile.ZIP_DEFLATED)
    zipdir('dist', zipf)
    zipf.close()