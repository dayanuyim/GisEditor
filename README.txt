1. Install (Windows)
    a. install python 3
        - checking 'pip' is also installed
    b. install python libraries
        - pip install pillow
        - pip install pmw
    c. install gpsbabel
        - remember the install path
    d. set config giseditor.conf
        - map chache dir
        - gpsbabel dir
    e. set file association
        - associate gps, gdb, ... file with the loader/giseditor.bat
    f. set right-click menu (optinal)
        - use FileMenuTools to add right-click menu

1. Install (linux)
    a. install necessary libraries
        sudo apt-get install libjpeg libjpeg-dev libfreetype6 libfreetype6-dev zlib1g-dev libpng12-dev libopenjpeg-dev tk-dev tcl-dev

    b. install python dev
         sudo apt-get install python3-dev python3-pip python3-tk python3-imaging-tk

    c. install python libraries
         sudo pip3 install pillow
         sudo pip3 install pmw
        * If error, try set links[2]
             sudo ln -s /lib/x86_64-linux-gnu/libz.so.1 /lib/
             sudo ln -s /usr/lib/x86_64-linux-gnu/libfreetype.so.6 /usr/lib/    
             sudo ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so.62 /usr/lib/
        * Or try to uninstall, then install again.

    d. install gpsbabel
       
    e. set config giseditor.conf
        - map chache dir
        - gpsbabel dir

    f. symbol link to main.py
        - ln -s <GisEditor_HOME>/src/main.py ~/bin/giseditor
   
Reference
[1] http://stackoverflow.com/questions/8915296/python-image-library-fails-with-message-decoder-jpeg-not-available-pil
[2] http://stackoverflow.com/questions/10763440/how-to-install-python3-version-of-package-via-pip-on-ubunt

