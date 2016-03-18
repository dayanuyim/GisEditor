Map Adapter to WMTS
===================

緣起
----

本軟體目的是在 Desktop (Windows/Linux) 上實作如 Anroid 上的 [OruxMaps][] 之地圖瀏覽軟體，可支援 WMTS用以瀏覽[經建三版地圖等其它台灣地圖][Sinica-WMTS]；並支援圖層功能，如[中研院線上百年地圖][Sinica-100y]。

[OruxMaps]: http://www.oruxmaps.com/index.html
[Sinica-WMTS]: http://gis.sinica.edu.tw/tileserver/
[Sinica-100y]: http://gissrv4.sinica.edu.tw/gis/twhgis.aspx

目標
----

 -  支援 WMTS (線上圖磚服務)
 -  PC使用，至少支援 Windows 和 Linux
 -  至少支援 GPX、GDB、圖檔(內嵌地理資訊之相片)等格式
 -  簡易航點、航跡編輯
 -  自動化功能：自動選擇航點圖示、分割航跡
 -  航跡檔輸出 (GPX 格式)
 -  地圖截圖輸出

Windows 安裝：
-------------

Windows 免安裝檔下載：
 *  [version 0.1, 32bit版](https://drive.google.com/file/d/0B7ryOauZNjlbd0pmVFJmYWVNTkU/view?usp=sharing)
 *  [version 0.1, 64bit版](https://drive.google.com/file/d/0B7ryOauZNjlbSE9mOFZvVjhVOWs/view?usp=sharing)


    手動安裝請見下方安裝說明。

Linux 安裝：
-----------

    手動安裝請見下方安裝說明。

MBTiles 下載:
-------------
 *  [經建三版 (3500 MB)](https://drive.google.com/file/d/0B7ryOauZNjlbT2EwbzBlSEpwT1U/view?usp=sharing)
 *  [經建三版(北部山區局部) (550 MB)](https://drive.google.com/file/d/0B7ryOauZNjlbWGpJTl84S1Y2OXM/view?usp=sharing)

操作說明：
---------

請見[操作手冊](https://github.com/dayanuyim/GisEditor/raw/dev/manual.md)

-------------------------------------------------------

安裝 (Windows)
==============
Windows 可直接下載免安裝檔：
* [version 0.1, 32bit版](https://drive.google.com/file/d/0B7ryOauZNjlbd0pmVFJmYWVNTkU/view?usp=sharing)
* [version 0.1, 64bit版](https://drive.google.com/file/d/0B7ryOauZNjlbSE9mOFZvVjhVOWs/view?usp=sharing)

*注意* 執行檔 giseditor.exe 實際上是個 python loader，若系統上已安裝 python3，也可修改 giseditor.exe.config 中的 PythonDirPath 路徑，指到你的系統上的 python3 版本

以下為手動安裝步驟。

手動安裝 (Windows)
------------------

1. 下載並安裝 [python3][] (安裝過程請勾選安裝 pip)

    _注意_ 若系統同時有 python2, python3，請注意安裝的是 python3相關library

[python3]: https://www.python.org/downloads/windows/ 

2. 下載 python 套件，在命令提示字元視窗下指令：

        pip install pillow
        pip install pmw

3. 下載並安裝 [gpsbabel][]

    _注意_ 下載此軟體，才可支援 GDB 檔

[gpsbabel]: http://www.gpsbabel.org/download.html

4. 下載程式。

    可透過 [git][git_repo]，或是直接[下載][git_arch]。

    下載完可以解壓縮至任何地方。 以下以 `$GISEDITOR_HOME` 做為程式所在資料夾來說明。

[git_repo]: https://github.com/dayanuyim/GisEditor.git
[git_arch]: https://github.com/dayanuyim/GisEditor/archive/master.zip

5. 預先下載圖資(可選)

    解壓縮 mbtiles 檔至 `$GISEDITOR_HOME/mapcache` 資料夾之下。

     *  [經建三版 (3500 MB)](https://drive.google.com/file/d/0B7ryOauZNjlbT2EwbzBlSEpwT1U/view?usp=sharing)
     *  [經建三版(北部山區局部) (550 MB)](https://drive.google.com/file/d/0B7ryOauZNjlbWGpJTl84S1Y2OXM/view?usp=sharing)

6. 設定程式參數

     *  將 `$GISEDITOR_HOME/conf/giseditor.conf.win.sample` 複製至 `$GISEDITOR_HOME/conf/giseditor.conf`

        開啟此檔，請確認 gpsbabel 執行檔所在位置:

            64位元系統設定 `gpsbabel_exe=C:\Program Files (x86)\GPSBabel\gpsbabel.exe`
            32位元系統設定 `gpsbabel_exe=C:\Program Files\GPSBabel\gpsbabel.exe`

        修改後存檔。

7. 建立執行檔

     *  複製 `$GISEDITOR_HOME/install/win/giseditor.exe` 及 `$GISEDITOR_HOME/install/win/giseditor.exe.config` 兩個檔案至
    `$GISEDITOR_HOME` 之下

     *  修改 giseditor.exe.config，設定 PythonDirPath 至 python3 資夾料，如：`C:\Program Files (x86)\Python35-32`

    `測試`
     *  雙擊 `giseditor.exe`，應可開啟。
     *  開啟 `giseditor.exe`，`右鍵->Add Files...`，選擇 `$GISEDITOR_HOME/sample.gpx`，應可開啟地圖與航跡。
     *  開啟 `giseditor.exe`，`右鍵->Add Files...`，選擇 `$GISEDITOR_HOME/sample.gdb`，應可開啟地圖與航跡。

8. 建立桌面環境與檔案關聯

    如果上一步驟的測試都PASS的話，安裝應該已成功。再來只要設定檔案關聯就好。

     *  選擇 `$GISEDITOR_HOME/sample.gpx` 檔案、右鍵選擇預設開啟程式、選擇以 `$GISEDITOR_HOME/giseditor.exe` 開啟
     *  選擇 `$GISEDITOR_HOME/sample.gdb` 檔案、右鍵選擇預設開啟程式、選擇以 `$GISEDITOR_HOME/giseditor.exe` 開啟
     *  可選：若需要一次個啟多個GPX、GDB、圖檔、或是資料夾，可以安裝 [FileMenuTools][] 新增右鍵選單。

[FileMenuTools]: https://briian.com/11030/filemenu-tools.html


安裝 (Linux)
============

1. 下載並安裝 python3


    sudo apt-get install python5-dev python3-pip python3-tk python3-imaging-tk libjpeg libjpeg-dev libfreetype6 libfreetype6-dev zlib1g-dev libpng12-dev libopenjpeg-dev tk-dev tcl-dev

   *注意* 若系統同時有 python2, python3，請注意安裝的是 python3相關library

2. 下載 python 套件


    sudo pip3 install pillow
    sudo pip3 install pmw

3. 下載並安裝 gpsbabel


    sudo apt-get install gpsbabel

4. 下載程式。

    可透過 [git][git_repo]，或是直接[下載][git_arch]。

    下載完可以解壓縮至任何地方。 以下以 `$GISEDITOR_HOME` 做為程式所在資料夾來說明。

[git_repo]: https://github.com/dayanuyim/GisEditor.git
[git_arch]: https://github.com/dayanuyim/GisEditor/archive/master.zip

5. 預先下載圖資(可選)

    解壓縮 mbtiles 檔至 `$GISEDITOR_HOME/mapcache` 資料夾之下。

     *  [經建三版 (3500 MB)](https://drive.google.com/file/d/0B7ryOauZNjlbT2EwbzBlSEpwT1U/view?usp=sharing)
     *  [經建三版(北部山區局部) (550 MB)](https://drive.google.com/file/d/0B7ryOauZNjlbWGpJTl84S1Y2OXM/view?usp=sharing)

6. 設定程式參數

    將 `$GISEDITOR_HOME/conf/sample/giseditor.conf.linux.sample` 複製至 `$GISEDITOR_HOME/conf/giseditor.conf`

    開啟此檔，確認參數是否正確，修改後存檔。

7. 建立執行檔

        mkdir ~/bin
        chmod +x $GISEDITOR_HOME/src/main.py
        ln -s $GISEDITOR_HOME/src/main.py ~/bin/giseditor

    *注意* ~/bin 必須在包含在 $PATH 之內

    *測試*
     *  下指令 giseditor，應可開啟地圖
     *  下指令 giseditor `$GISEDITOR_HOME/data/test.gpx`，應可開啟地圖與航跡
     *  下指令 giseditor `$GISEDITOR_HOME/data/test.gdb`，應可開啟地圖與航跡

8. 建立桌面環境與檔案關聯

     *  建立 desktop 檔

            sudo cp $GISEDITOR_HOME/data/giseditor.desktop /usr/share/applications

     *  建立圖示檔
     
            sudo cp -a $GISEDITOR_HOME/data/icons /usr/share/

     *  登出並重新登入

     *  設定檔案關聯
     
        選擇 `$GISEDITOR_HOME/data/sample.gpx` 檔案，`右鍵->屬性->以此開啟->Giseditor->設為預設值->關閉`

        選擇 `$GISEDITOR_HOME/data/sample.gdb` 檔案，`右鍵->屬性->以此開啟->Giseditor->設為預設值->關閉`

    ![右鍵選單][img_rightmenu]

[img_rightmenu]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/01_right_menu.png
