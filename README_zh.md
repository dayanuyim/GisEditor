Map Adapter to WMTS
===================

緣起
====

本軟體目的是在 Desktop (Windows/Linux) 上實作如 Anroid 上的 [OruxMaps][] 之地圖瀏覽軟體，可支援 WMTS用以瀏覽[經建三版地圖等其它台灣地圖][Sinica-WMTS]；並支援圖層功能，如[中研院線上百年地圖][Sinica-100y]。

Windows 免安裝檔下載：
 *  [version 0.1, 32bit版](https://drive.google.com/file/d/0B7ryOauZNjlbd0pmVFJmYWVNTkU/view?usp=sharing)
 *  [version 0.1, 64bit版](https://drive.google.com/file/d/0B7ryOauZNjlbSE9mOFZvVjhVOWs/view?usp=sharing)

Linux 安裝：

    請見以下說明。

MBTiles 下載:
 *  [經建三版 (3500 MB)](https://drive.google.com/file/d/0B7ryOauZNjlbT2EwbzBlSEpwT1U/view?usp=sharing)
 *  [經建三版(北部山區局部) (550 MB)](https://drive.google.com/file/d/0B7ryOauZNjlbWGpJTl84S1Y2OXM/view?usp=sharing)

[OruxMaps]: http://www.oruxmaps.com/index.html
[Sinica-WMTS]: http://gis.sinica.edu.tw/tileserver/
[Sinica-100y]: http://gissrv4.sinica.edu.tw/gis/twhgis.aspx

-------------------------------------------------------

目標
====

目標是實作一個以經建三版為底圖的地圖瀏覽器，功能不求強大，以能應付大部分地圖瀏覽需求為主。計有以下目標：
 -  支援經建三版地圖
 -  PC使用，至少支援 Windows 和 Linux
 -  至少支援 GPX、GDB、圖檔(內嵌地理資訊之相片)等格式
 -  簡易航點、航跡編輯
 -  自動化功能：自動選擇航點圖示、分割航跡
 -  航跡檔輸出 (GPX 格式)
 -  地圖截圖輸出

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
     *  開啟 `giseditor.exe`，右鍵->Add Files...->選擇 `$GISEDITOR_HOME/sample.gpx`，應可開啟地圖與航跡。
     *  開啟 `giseditor.exe`，右鍵->Add Files...->選擇 `$GISEDITOR_HOME/sample.gdb`，應可開啟地圖與航跡。

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
     
        選擇 `$GISEDITOR_HOME/data/sample.gpx` 檔案，右鍵->屬性->以此開啟->Giseditor->設為預設值->關閉

        選擇 `$GISEDITOR_HOME/data/sample.gdb` 檔案，右鍵->屬性->以此開啟->Giseditor->設為預設值->關閉

    ![右鍵選單][img_rightmenu]

程式功能說明
============

1. 地圖瀏覽
    1.1. 直接開啟
        windows:
            鍵入指令 gisedotr 或是雙擊 giseditor.bat (參考§2.7)
        linux:
            鍵入指令 gisedotr 或是透過 X System (Win+A 尋找 Giseditor)
    1.2. 載入航跡檔、圖檔
        直接開啟 *.gpx， *.gdb，或 *.jpg圖檔 (參考§2.8)
        <插圖>
    1.3. 載入多個檔案或資料夾下所有檔案
        鍵入指令 gisedotr <gpx/gdb/jpg/folder>...<gpx/gdb/jpg/folder>
        桌面系統需安裝 FileMenuTools 或 Nautilus-Actions 來增加右鍵選單 (參考§2.8)
    1.4. 移動地圖
        滑鼠可拖曳地圖
    1.5. 縮放地圖
        滑鼠移至地圖任一點，可用滾輪對此對做縮放。向上滾為Zoom In，向下滾為Zoom Out。
        或可直接在 [Level] 處鍵入圖層值 (有效值 7~18)
    1.6. 下載圖資
        當狀態列顯示 "Loading...(n)", 表示尚餘 n 個圖磚數需下載
    1.7 取得目前位置
        滑鼠點擊地圖任一點，可取得該點之座標，並顯示於上方座標列
    1.8 移至任一位置       
        於座標列任一座標系統，輸入座標並鍵入[Enter]，可移至該位置。
        二度分帶單位為KM, 經緯度單位為度。

2. 航點編輯
    1. 新增航點
        於地圖任一點，點擊右鍵->Add wpt 可新增航點
    2. 刪除航點
        於任一航點，點擊右鍵->Delete wpt 可刪除航點。
        或於航點編輯視窗(§3.2.3) 按 [Del]鍵(刪除前先提示) 或 [Shift+Del]鍵(直接刪除)
    3. 航點編輯視窗
        點擊任一圖示或右鍵->Edit waypoints->Edit 1-by-1
        <插圖>
        Focus: 將此航點於地圖中置中
        名稱：顯示或修改航點名稱
        圖示：點擊可開啟圖示選擇窗(參考§3.2.4)，點擊圖示可修改圖示
        Rule：可建立名稱與圖示關聯，鍵入名稱時自動選擇對應圖示 (參考§3.2.6)
    4. 航點列表視窗
        右鍵->Edit waypoints->Edit in list
        <插圖.
    4. 圖示選擇窗
        <插圖>
        圖示名稱顯示於 [圖示選擇窗]之標題列
        右下角可鍵入要過濾圖示(目前僅支援英文)，
        圖示背景色所表示意義：淺灰色(系統預設)、深灰色(使用者自訂)、紅色(符合過濾條件)
    5. 新增使用者自訂圖示
        將圖檔放入 $GISEDITOR_HOME/icon 下即可，檔名即圖示名稱。
        建議為檔名為英文、PNG 格式、背景透明、正方形之圖檔。
    6. 圖示規則視窗
        <插圖>
        Save鈕：存檔
        ↓↑鈕：調整規則優先權順序
        啟用：v表啟用，x表不啟用
        Type：
            點擊可選擇
            Contain：航點名稱包含 Text
            StartWith：航點名稱以 Text 為開頭
            EndWith：航點名稱以 Text 為結尾
            Equal：航點名稱即 Text
            Regex：航點名稱符合以 Text 表代表之 Regular Expression
        Text：根據Type所表示的文字
        圖示：點擊可開啟圖示選擇窗(參考§3.2.4)，點擊圖示可修改圖示
        [注意] 可將最後一筆規則設為 Type=Contain, Text=(空字串) 來做為預設圖示
    7. 自動套用航點圖示規則
        右鍵->Apply sumbol rules

3. 航跡編輯
    1. 航跡編輯視窗
        <插圖>
        Track: 航跡名稱
        Color：航跡顏色。可輸入任何 python 支援顏色，若為支援顏色會以綠底顯示；不支援的顏色則以紅底顏示。
        [注意] 相容於 Garmin 的顏色為：White、Cyan、Magenta、Blue、Yellow、Green、Red、DarkGray、LightGray、DarkCyan、DarkMagenta、DarkBlue、DarkGreen、DarkRed、Black。
        航跡點：選取一或多個航跡點可在地圖上顯示
        Focus Track Point：將所選取的航跡點置中於地圖
    2. 自動分割航跡
        以每日作分割：右鍵->Split tracks...->by day
        以時間差距作分割：右鍵->Split tracks...->by time gap
        以距離差距作分割：右鍵->Split tracks...->by distance

4. 輸出航跡檔
    右鍵->Save to gpx...

5. 輸出地圖截圖
    右鍵->Save to image...
    <插圖>
    S鈕：參數設定
        precision level: 輸出圖層
        Align grid：選取區左上角是否對齊二度分帶格線
        Fixed size：是否固定選取區大小。單位為KM
    X鈕：取消截圖
    O鈕：輸出選取區之對應截圖
    選取區：
        移動：拖曳可移動選取區；或可用[方向鍵]做移動
        向上延展：滑鼠移至選取區上方邊界，鼠標變為Resize圖示時可拖曳做縮放；或可[Ctrl+向上鍵]放大、[Shift+向上鍵]縮小。
        向下延展：滑鼠移至選取區下方邊界，鼠標變為Resize圖示時可拖曳做縮放；或可[Ctrl+向下鍵]放大、[Shift+向下鍵]縮小。
        向左延展：滑鼠移至選取區左方邊界，鼠標變為Resize圖示時可拖曳做縮放；或可[Ctrl+向左鍵]放大、[Shift+向左鍵]縮小。
        向右延展：滑鼠移至選取區右方邊界，鼠標變為Resize圖示時可拖曳做縮放；或可[Ctrl+向右鍵]放大、[Shift+向右鍵]縮小。
        向右下方延展：滑鼠移至選取區右下角，鼠標變為Resize圖示時可拖曳做縮放。

[img_rightmenu]: https://github.com/dayanuyim/GisEditor/blob/dev/doc/pic/01_right_menu.png
