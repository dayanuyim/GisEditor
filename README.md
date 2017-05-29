Map Adapter to WMTS
===================

目的
----

本軟體目的是在 Desktop (Windows/Linux) 上實作如 Anroid 上的 [OruxMaps][] 之地圖瀏覽軟體，可支援 WMTS用以瀏覽[經建三版地圖等其它台灣地圖][Sinica-WMTS]；並支援圖層功能，如[中研院線上百年地圖][Sinica-100y]。計有以下目標：
  -  支援 WMTS (線上圖磚服務)
  -  PC使用，至少支援 Windows 和 Linux
  -  至少支援 GPX、GDB、圖檔(內嵌地理資訊之相片)等格式
  -  簡易航點、航跡編輯
  -  自動化功能：自動選擇航點圖示、分割航跡
  -  航跡檔輸出 (GPX 格式)
  -  地圖截圖輸出

[OruxMaps]: http://www.oruxmaps.com/index.html
[Sinica-WMTS]: http://gis.sinica.edu.tw/tileserver/
[Sinica-100y]: http://gissrv4.sinica.edu.tw/gis/twhgis.aspx

軟體安裝 (Windows)
------------------

 *  免安裝檔：
     *  [version 0.23][giseditor-0.23]
 *  自動安裝：暫無。
 *  手動安裝：請參考[手動安裝](#win_install)。

 [giseditor-0.1-32]: https://drive.google.com/file/d/0B7ryOauZNjlbd0pmVFJmYWVNTkU/view?usp=sharing
 [giseditor-0.1-64]: https://drive.google.com/file/d/0B7ryOauZNjlbSE9mOFZvVjhVOWs/view?usp=sharing
 [giseditor-0.2-32]: https://drive.google.com/file/d/0B7ryOauZNjlbX2NjbnBUUTc4bU0/view?usp=sharing
 [giseditor-0.2-64]: https://drive.google.com/file/d/0B7ryOauZNjlbTndFbW1oTEtxWWs/view?usp=sharing
 [giseditor-0.21-32]: https://drive.google.com/file/d/0B7ryOauZNjlbZV9OcjFPNUwzYUU/view?usp=sharing
 [giseditor-0.21-64]: https://drive.google.com/file/d/0B7ryOauZNjlbNFBheXEwWTE5U2s/view?usp=sharing
 [giseditor-0.22-32]: https://drive.google.com/file/d/0B7ryOauZNjlbbVhoNTZWUW9uN2s/view?usp=sharing
 [giseditor-0.22-64]: https://drive.google.com/file/d/0B7ryOauZNjlbU2ZBQVkzd2dLbUE/view?usp=sharing
 [giseditor-0.23]: https://drive.google.com/file/d/0B7ryOauZNjlbVm8zRGZCemVPVGc/view?usp=sharing


軟體安裝 (Linux)
----------------

 *  自動安裝：暫無。
 *  手動安裝：請參考[手動安裝](#linux_install)。

MBTiles 下載 (可選)
-------------------
 *  [經建三版 (3500 MB)](https://drive.google.com/file/d/0B7ryOauZNjlbT2EwbzBlSEpwT1U/view?usp=sharing)
 *  [經建三版(北部山區局部) (550 MB)](https://drive.google.com/file/d/0B7ryOauZNjlbWGpJTl84S1Y2OXM/view?usp=sharing)

操作說明
--------

請見[操作手冊](https://github.com/dayanuyim/GisEditor/blob/dev/manual.md)

更新歷史
--------
  - 0.23 版
      - 加入[台灣通用電子地圖][emap]支援
      - 新的地圖列表介面
      - MapSource 相容性修正
      - 疊圖情況下圖檔輸出錯誤修正

[emap]: http://emap.nlsc.gov.tw

-------------------------------------------------------

手動安裝 (Windows) <a name="win_install"></a>
==================

1. 下載並安裝 [python3][] (安裝過程請勾選安裝 pip、並允許設定環境變數)

    _注意_ 若系統同時有 python2, python3，請注意安裝的是 python3相關library

[python3]: https://www.python.org/downloads/windows/ 

2. 下載 python 套件，在命令提示字元視窗下指令：
    紀錄在requirement.txt，以下列指令執行
    ```pip install -r requirement.txt```

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

6. 執行
     *  雙擊 `main.py`，應可開啟。
     *  開啟 `giseditor.exe`，`右鍵->Add Files...`，選擇 `$GISEDITOR_HOME/sample.gpx`，應可開啟地圖與航跡。
     *  開啟 `giseditor.exe`，`右鍵->Add Files...`，選擇 `$GISEDITOR_HOME/sample.gdb`，應可開啟地圖與航跡。
         *  若無法開啟請確認 `$GISEDITOR_HOME/conf/giseditor.conf 的 gpsbabel_exe` 之設定是否正確

7. 建立桌面環境與檔案關聯

    如果上一步驟的測試都PASS的話，安裝應該已成功。再來只要設定檔案關聯就好。

     *  選擇 `$GISEDITOR_HOME/sample.gpx` 檔案、右鍵選擇預設開啟程式、選擇以 `$GISEDITOR_HOME/giseditor.exe` 開啟
     *  選擇 `$GISEDITOR_HOME/sample.gdb` 檔案、右鍵選擇預設開啟程式、選擇以 `$GISEDITOR_HOME/giseditor.exe` 開啟
     *  可選：若需要一次個啟多個GPX、GDB、圖檔、或是資料夾，可以安裝 [FileMenuTools][] 新增右鍵選單。

[FileMenuTools]: https://briian.com/11030/filemenu-tools.html

-------------------------------------------------------

手動安裝 (Linux)  <a name="linux_install"></a>  
============

1. 安裝字型
    預設使用ubuntu OS內建ukai
    
    Arch Linux:
    ```# pacman -S ttf-arphic-ukai```

    CentOS:
    ```# yum install cjkuni-ukai-fonts```

2. 環境
    python3, gpsbabel(for *.gpb), freetype, image

    ```sudo apt-get install python5-dev python3-pip python3-tk python3-imaging-tk libjpeg libjpeg-dev libfreetype6 libfreetype6-dev zlib1g-dev libpng12-dev libopenjpeg-dev tk-dev tcl-dev gpsbabel```

   *注意* 若系統同時有 python2, python3，請注意安裝的是 python3相關library

3. 下載 python 套件
    紀錄在requirement.txt，以下列指令執行
    ```sudo pip3 install -r requirement.txt```

    
4. 下載程式。

    可透過 [git][git_repo]，或是直接[下載][git_arch]。

    下載完可以解壓縮至任何地方。 以下以 `$GISEDITOR_HOME` 做為程式所在資料夾來說明。

[git_repo]: https://github.com/dayanuyim/GisEditor.git
[git_arch]: https://github.com/dayanuyim/GisEditor/archive/master.zip

5. 預先下載圖資(可選)

    解壓縮 mbtiles 檔至 `$GISEDITOR_HOME/mapcache` 資料夾之下。

     *  [經建三版 (3500 MB)](https://drive.google.com/file/d/0B7ryOauZNjlbT2EwbzBlSEpwT1U/view?usp=sharing)
     *  [經建三版(北部山區局部) (550 MB)](https://drive.google.com/file/d/0B7ryOauZNjlbWGpJTl84S1Y2OXM/view?usp=sharing)

6. 執行

    ```
    $ cd $GISEDITOR_HOME
    $ python3 main.py   
    ```
    或是雙擊main.py

    *快速載入航跡與地圖*
    ```
    $ python3 main.py $GISEDITOR_HOME/data/test.gpx
    $ python3 main.py $GISEDITOR_HOME/data/test.gdb
    ```
    *  若無法開啟*.gdb請確認 `$GISEDITOR_HOME/conf/giseditor.conf 的 gpsbabel_exe` 之設定是否正確

7. 建立桌面環境與檔案關聯

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


MAC (手動安裝)
===========

1. install python 3

2. install ActiveTcl 8.5.18.0
    
    * Must install the version, higher or lower version may not work.

    * Please check _Security & Privacy_ if MAC prevent you from installation.

3. install library

    ```
    brew install libtiff libjpeg webp little-cms2 freetype
    ```

4. install python requirement

    ```
    pip install -r requirement.txt
    ```

5. install gpsbabel
    
    ```
    brew install gpsbabel
    ```

