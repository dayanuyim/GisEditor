操作手冊
========
![程式畫面][img_main]

1\. 地圖瀏覽
------------

1. 開啟
     *  windows:
        直接開啟 gisedotr.exe

     *  linux:
        鍵入指令 gisedotr 或是透過 X System (Win+A 尋找 Giseditor)

2. 載入航跡檔、圖檔

    設定檔案關聯後，開啟 *.gpx， *.gdb，或 *.jpg圖檔。

    或開啟程式後由右鍵選單加入

3. 移動地圖

    滑鼠可拖曳地圖

4. 縮放地圖

    滑鼠移至地圖任一點，可用滾輪對此對做縮放。向上滾為Zoom In，向下滾為Zoom Out。
    或可直接在 [Level] 處鍵入圖層值 (有效值 7~18)

5. 下載圖資

    當狀態列顯示 "Loading...(n)", 表示尚餘 n 個圖磚數需下載

6. 取得目前位置

    滑鼠點擊地圖任一點，可取得該點之座標，並顯示於上方座標列

7. 移至任一位置

    於座標列任一座標系統，輸入座標並鍵入[Enter]，可移至該位置。二度分帶單位為KM, 經緯度單位為度。

2\. 航點編輯
------------

1. 新增航點

    於地圖任一點，點擊`右鍵->Add wpt` 可新增航點

2. 刪除航點

    於任一航點，點擊`右鍵->Delete wpt` 可刪除航點。
    或於[航點編輯視窗](#wpt_edit) 按 [Del]鍵(刪除前先提示) 或 [Shift+Del]鍵(直接刪除)

3. 航點編輯視窗<a name="wpt_edit"></a>

    點擊任一航點圖示或`右鍵->Edit waypoints->Edit 1-by-1`

    ![航點編輯視窗][img_wptedit]

     *  Focus: 將此航點於地圖中置中
     *  名稱：顯示或修改航點名稱
     *  圖示：點擊可開啟[圖示選擇窗](#sym_board)，點擊圖示可修改圖示
     *  Rule：可建立名稱與圖示關聯，鍵入名稱時自動選擇對應圖示，規則建立請見[圖示規則視窗](#sym_rule)

4. 航點列表視窗

    右鍵->Edit waypoints->Edit in list

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

3\. 航跡編輯
------------

1. 航跡編輯視窗

    ![航跡編輯視窗][img_trkboard]

     *  Track: 航跡名稱
     *  Color：航跡顏色。
     *  航跡點：選取一或多個航跡點可在地圖上顯示
     *  Focus Track Point：將所選取的航跡點置中於地圖

    *注意* 航跡顏色亦輸入任何 python 支援顏色，但不具可攜性

2. 自動分割航跡

     *  以每日作分割：`右鍵->Split tracks...->by day`
     *  以時間差距作分割：`右鍵->Split tracks...->by time gap`
     *  以距離差距作分割：`右鍵->Split tracks...->by distance`

3. 輸出航跡檔

    `右鍵->Save to gpx...`

4\. 輸出地圖截圖
----------------

`右鍵->Save to image...`

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

[img_main]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/02_main.png
[img_wptedit]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/03_wpt_edit.png
[img_wptlist]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/04_wpt_list.png
[img_symboard]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/05_sym_board.png
[img_symrule]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/06_sym_rule.png
[img_trkboard]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/07_trk_board.png
[img_saveimage]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/08_save_image.png
