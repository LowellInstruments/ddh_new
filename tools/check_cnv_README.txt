In a DDH, place this folder in the Desktop.
You can connect via VNC and use the upper tool bar to send files (and folders) to DDH.
Then, place your .lid files to be converted inside such folder.



Then, in a terminal, run:
    cd /home/pi/Desktop/check_cnv
    sudo python3 main_cnv.py
Probably, it will also work double-clicking on main_cnv.sh and choosing "Run from terminal".



This script will not convert already converted files.
This folder already has one good.lid and one bad.lid example files for you to see an example test output.
When this folder is not populated with your files, runnign this code will simply output:
    
    
    file ... bad.lid ERROR conversion -> Header tags missing
    file ... good.lid conversion OK




