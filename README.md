Map Adapter to WMTS
===================

目的
----

本軟體目的是在 Desktop (Windows/Linux) 上實作如 Anroid 上的 [OruxMaps][] 之地圖瀏覽軟體，可支援 [WMTS][wmts_wiki]用以瀏覽[經建三版地圖等其它台灣地圖][Sinica-WMTS]；並支援圖層功能，如[中研院線上百年地圖][Sinica-100y]。計有以下目標：
  -  支援 WMTS (線上圖磚服務)
  -  PC使用，至少支援 Windows 和 Linux
  -  至少支援 GPX、GDB、圖檔(內嵌地理資訊之相片)等格式
  -  簡易航點、航跡編輯
  -  自動化功能：自動選擇航點圖示、分割航跡
  -  航跡檔輸出 (GPX 格式)
  -  地圖截圖輸出

[wmts_wiki]: https://en.wikipedia.org/wiki/Web_Map_Tile_Service
[OruxMaps]: http://www.oruxmaps.com/index.html
[Sinica-WMTS]: http://gis.sinica.edu.tw/tileserver/
[Sinica-100y]: http://gissrv4.sinica.edu.tw/gis/twhgis.aspx

安裝
----

 *  Windows免安裝檔

    [version 0.27 (latest)][giseditor-0.27]

    _若啟動失敗，請先安裝`font`資料夾下之字型_

 *  預載地圖(可選)

    - [經建三版 (3.5GB)](https://drive.google.com/file/d/0B7ryOauZNjlbT2EwbzBlSEpwT1U/view?usp=sharing)

    📝 解壓縮 mbtiles 檔至 `mapcache` 資料夾之下。

 *  其它參考

    [Win](  https://github.com/dayanuyim/GisEditor/blob/dev/install.md#win_install) |
    [Linux](https://github.com/dayanuyim/GisEditor/blob/dev/install.md#linux_install) |
    [MAC](  https://github.com/dayanuyim/GisEditor/blob/dev/install.md#mac_install)

 [giseditor-0.1-32]: https://drive.google.com/file/d/0B7ryOauZNjlbd0pmVFJmYWVNTkU/view?usp=sharing
 [giseditor-0.1-64]: https://drive.google.com/file/d/0B7ryOauZNjlbSE9mOFZvVjhVOWs/view?usp=sharing
 [giseditor-0.2-32]: https://drive.google.com/file/d/0B7ryOauZNjlbX2NjbnBUUTc4bU0/view?usp=sharing
 [giseditor-0.2-64]: https://drive.google.com/file/d/0B7ryOauZNjlbTndFbW1oTEtxWWs/view?usp=sharing
 [giseditor-0.21-32]: https://drive.google.com/file/d/0B7ryOauZNjlbZV9OcjFPNUwzYUU/view?usp=sharing
 [giseditor-0.21-64]: https://drive.google.com/file/d/0B7ryOauZNjlbNFBheXEwWTE5U2s/view?usp=sharing
 [giseditor-0.22-32]: https://drive.google.com/file/d/0B7ryOauZNjlbbVhoNTZWUW9uN2s/view?usp=sharing
 [giseditor-0.22-64]: https://drive.google.com/file/d/0B7ryOauZNjlbU2ZBQVkzd2dLbUE/view?usp=sharing
 [giseditor-0.23]: https://drive.google.com/file/d/0B7ryOauZNjlbVm8zRGZCemVPVGc/view?usp=sharing
 [giseditor-0.25]: https://drive.google.com/file/d/1S9pry2DPY2XI9wC80XC49-FgQeT6umwk/view?usp=sharing
 [giseditor-0.27]: https://drive.google.com/file/d/19ImwLU-vfoaouA_xMbgxxk1g0mHoaIyh/view?usp=sharing



操作說明
--------

請見[操作手冊](https://github.com/dayanuyim/GisEditor/blob/dev/manual.md)

更新歷史
--------
  - v0.27
      - 支援電力座標
      - 航點可編輯高度與位置
      - FIX: 魯地圖存圖錯誤

  - v0.26
      - 支援魯地圖

  - v0.25
      - TM2格線
      - 支援六碼座標

  - v0.24
      - 使用者個人設定檔 (~/.config)
      - 自動選擇字型

  - v0.23 版
      - 加入[台灣通用電子地圖][emap]支援
      - 新的地圖列表介面
      - MapSource 相容性修正
      - 疊圖情況下圖檔輸出錯誤修正


[emap]: http://emap.nlsc.gov.tw

