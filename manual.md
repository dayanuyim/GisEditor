操作手冊
========
1. [地圖瀏覽](#sec_browsing)
2. [航點編輯](#sec_wpt)
3. [航跡編輯](#sec_trk)
4. [輸出地圖截圖](#sec_saveimg)
5. [地圖疊圖](#sec_maplist)
6. [地圖格線](#sec_coordline)

![程式畫面][img_main]

1\. 地圖瀏覽<a name="sec_browsing"></a>
------------

1. 開啟
     *  windows:
        直接開啟 gisedotr.exe

     *  linux:
        鍵入指令 gisedotr 或是透過 X System (Win+A 尋找 Giseditor)

2. 載入航跡檔、圖檔

     *  設定檔案關聯後，開啟 *.gpx， *.gdb，或 *.jpg圖檔，或
     *  開啟程式後由右鍵選單加入，或
     *  指令列參數帶入檔案路徑

3. 移動地圖

    滑鼠可拖曳地圖

4. 縮放地圖

    滑鼠移至地圖任一點，可用滾輪對此對做縮放。向上滾為Zoom In，向下滾為Zoom Out。
    或可直接在 [Level] 處鍵入圖層值 (有效值 7~18)

5. 下載圖資

    當狀態列顯示 "Loading...n%", 表示下載進度；亦會顯示於進度條

6. 取得目前位置

    滑鼠點擊地圖任一點，可取得該點之座標，並顯示於上方座標列

7. 移至任一位置

    於座標列任一座標系統，輸入座標並鍵入[Enter]，可移至該位置。
     * 輸入格式若為2個數字，以逗點、空白或非數字之字元隔開
     * 二度分帶輸入
        * 若為1個六位數整數或2個三位數整數，為**六碼座標**
        * 若為2個整數，單位為**公尺**
        * 若為2個小數點，單位為**公里**
     * 經緯度輸入可為2個整數或小數，單位為度。

2\. 航點編輯<a name=sec_wpt></a>
------------

1. 新增航點

    於地圖任一點，點擊`右鍵->Add wpt` 可新增航點

2. 刪除航點

    於任一航點，點擊`右鍵->Delete wpt` 可刪除航點。
    或於[航點編輯視窗](#wpt_edit) 按 [Del]鍵(刪除前先提示) 或 [Shift+Del]鍵(直接刪除)

3. 航點編輯視窗<a name="wpt_edit"></a>

    點擊任一航點圖示或`右鍵->Edit waypoints`或熱鍵`Ctrl+w`

    ![航點編輯視窗][img_wptedit]

     *  Focus: 將此航點於地圖中置中
     *  名稱：顯示或修改航點名稱
     *  圖示：點擊可開啟[圖示選擇窗](#sym_board)，點擊圖示可修改圖示
     *  Rule：可建立名稱與圖示關聯，鍵入名稱時自動選擇對應圖示，規則建立請見[圖示規則視窗](#sym_rule)

4. 航點列表視窗

    右鍵->Show waypoints list

    ![航點列表視窗][img_wptlist]

5. 圖示選擇窗<a name="sym_board"></a>

    ![圖示選擇窗][img_symboard]

     *  圖示名稱顯示於 [圖示選擇窗]之標題列
     *  右下角可鍵入要過濾圖示名稱
     *  圖示背景色所表示意義：
         *  淺灰色(系統預設)
         *  深灰色(使用者自訂)
         *  紅色(符合過濾條件)

6. 新增使用者自訂圖示

    將圖檔放入 `$GISEDITOR_HOME/icon` 下即可，檔名即圖示名稱。

    *建議* 使用英文檔名、PNG 格式、背景透明、正方形之圖檔。

7. 圖示規則視窗<a name="sym_rule"></a>

    ![圖示規則視窗][img_symrule]

     *  Save鈕：存檔
     *  ↓↑鈕：調整規則優先權順序
     *  啟用：v表啟用，x表不啟用
     *  Type：
        點擊可選擇
         *  Contain：航點名稱包含 Text
         *  StartWith：航點名稱以 Text 為開頭
         *  EndWith：航點名稱以 Text 為結尾
         *  Equal：航點名稱即 Text
         *  Regex：航點名稱符合以 Text 表代表之 Regular Expression
     *  Text：根據Type所表示的文字
     *  圖示：點擊可開啟圖示選擇窗(參考§3.2.4)，點擊圖示可修改圖示

    *注意* 可將最後一筆規則設為 Type=Contain, Text=(空字串) 來做為預設圖示

8. 自動套用航點圖示規則

    `右鍵->Apply sumbol rules`

3\. 航跡編輯<a name="sec_trk"></a>
------------

1. 航跡編輯視窗<a name="trk_edit_board"></a>

    `右鍵->Edit Tracks`或熱鍵`Ctrl+t`

    ![航跡編輯視窗][img_trkboard]

     *  Track: 航跡名稱
     *  Color：航跡顏色。
     *  刪除鈕：刪除此航跡
     *  航跡點：選取一或多個航跡點可在地圖上顯示
     *  Focus Track Point：將所選取的航跡點置中於地圖

    *注意* 航跡顏色亦輸入任何 python 支援顏色，但不具可攜性

2. 刪除航跡

    請進入[航跡編輯視窗](#trk_edit_board)，點擊刪除鈕。

3. 繪製航跡

     *  `右鍵->Draw Track...`或熱鍵`F1` 進入航跡繪製模式
     *  左鍵在地圖上拖曳可繪製地圖
     *  熱鍵`ESC` 可離開航跡繪製模式

4. 自動分割航跡

     *  以每日作分割：`右鍵->Split tracks...->by day`
     *  以時間差距作分割：`右鍵->Split tracks...->by time gap`
     *  以距離差距作分割：`右鍵->Split tracks...->by distance`

5. 輸出航跡檔

    `右鍵->Save to gpx...`

4\. 輸出地圖截圖<a name="sec_saveimg"></a>
----------------

`右鍵->Save to image...`或熱鍵`F2`

![地圖截圖][img_saveimage]
 *  S鈕：參數設定
     *  precision level: 輸出圖層
     *  Align grid：選取區左上角是否對齊二度分帶格線
     *  Fixed size：是否固定選取區大小。單位為KM
 *  X鈕：取消截圖
 *  O鈕：輸出選取區之對應截圖
 *  選取區：
     *  移動：拖曳可移動選取區；或可用[方向鍵]做移動
     *  上/下/左/右邊界延展：滑鼠移至選取區邊界，鼠標變為Resize圖示時可拖曳做縮放；或可[Ctrl+方向鍵]放大、[Shift+方向鍵]縮小。
     *  右下邊界延展：滑鼠移至選取區右下角，鼠標變為Resize圖示時可拖曳做縮放。

5\. 地圖疊圖<a name="sec_maplist"></a>
------------

![地圖疊圖][img_maplist]

1. 設定地圖來源
     *  系統會讀取 `$GISEDITOR_HOME/mapcache` 的 XML 檔，格式可參考 [MOBAC customMapSource][custom_map_source]。

2. 開啟地圖列表
     * 點選地圖名稱旁的`[▼]按鈕`可展開地圖列表。

3. 收闔地圖列表
     * 按`ESC鍵`或地圖名稱旁的`[▲]按鈕`可收起地圖列表

4. 啟用/不啟用地圖
     * 勾選checkbox可啟用地圖，不勾選則不啟用地圖。

5. 調整不透明度(α值)
     * 百分比可調整地圖的不透明度，100%為完全不透明，0%表示完全透明。

6. 疊圖順序
     * *疊圖順序*即為啟用中的地圖*由上而下*之順序。
     * 可按住地圖名稱，拖曳插入以調整順序。

    ![拖曳疊圖順序][img_maplist_dnd]

<a name="sec_coordline"></a>
6\. 地圖格線
------------

![地圖格線][img_coord_line]

可開啟TM2格線，畫出KM或100KM格線。

1. TWD67 TM2 格線：熱鍵 `Crtl+6`
2. TWD97 TM2 格線：熱鍵 `Crtl+9`

[custom_map_source]: http://mobac.sourceforge.net/wiki/index.php/Custom_XML_Map_Sources#customMapSource
[img_main]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/02_main.png
[img_wptedit]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/03_wpt_edit.png
[img_wptlist]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/04_wpt_list.png
[img_symboard]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/05_sym_board.png
[img_symrule]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/06_sym_rule.png
[img_trkboard]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/07_trk_board.png
[img_saveimage]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/08_save_image.png
[img_maplist]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/09_maplist.png
[img_maplist_dnd]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/10_maplist_dnd.png
[img_coord_line]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/11_coord_line.png
