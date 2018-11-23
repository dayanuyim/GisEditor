Manual
========
1. [Map Browsing](#sec_browsing)
2. [Waypoint Editing](#sec_wpt)
3. [Track Editing](#sec_trk)
4. [Map Saving](#sec_saveimg)
5. [Map Overlay](#sec_maplist)
6. [Map Grid Line](#sec_coordline)

![Application UI][img_main]

<a name="sec_browsing"></a>
1\. Map Browsing
----------------

### I. Open Appliction

 *  Windows:
    Double click `gisedotr.exe`

 *  Linux:
    Press the command `gisedotr` in cmdline, or Win+A to find `GisEditor` in X System

### II. Load GPS or Photo Files

*  Directly open .gpx, .gdb, or .jpg files, if the files associations are set; or
*  Open the applicatoin, then loading files from the `right-click menu`; or
*  In the cmdline, provide the arguments for file paths. Usage: _giseditor [file 1]...[file n]_

### III. Move the Map

Drag-n-Drop the map by mouse.

### IV. Scale the Map

* Move the mouse to the location you want to zoom in/out. Forward the mouse wheel to Zoom In and Backward the mouse wheel to Zoom Out. Or
* Just key in the level in the `Level`. (The default valid range: 7~19)

### V. Load the Map Tiles

If Status Bar displays `Loading...n%`, it means the map tiles are downloading. And Progress Bar will be running.

### VI. Get the coordinates of a location.

Move the mouse to the location you want and click. The coordinates will be shown in the Coordinates Bar.

### VII. Move the Map to the Specific Location

At Coordinate Bar, key in the coordinates at the coordinate systems you want; then press `Enter`.
The map will be centered at the location.
<a name=location_format></a>
 * If the input is two numbers, the two numbers need to be seperated by comma, space, or any non-number characters.
 * __For TM2 coordinates__:
    * If the input is `Taiwan-Power` coordinate format, it is parsed.
    * If the input is `one 6-digit number` or `two 3-digit numbers`, it will be represented as the 6-digit coordinate.
    * If the input is `two integer number`, the unit will be __meter__.
    * If the input is `two numbers with the decimal point`, the unit will be __kilometer__.
 * __For Lat/Lon__:
    * The input is `two numbers` with/without the decimal point, and the unit is __degree__.

<a name=sec_wpt></a>
2\. Waypoint Editing
--------------------

### I. Add Waypoints

At the location you want, right-click the mouse and click `Add wpt` from the menu.

### II. Delete Waypoints

Right-click the mouse at a waypoint, and click `Delete wpt`.
Or in [Waypoint Editing Panel](#wpt_edit), press `Del` to delete with prompt or press `Shift+Del` to delete without prompt.

<a name="wpt_edit"></a>
### III. Waypoint Editing Panel

Click any waypoints, or select `Edit waypoints` from the `right-click menu`, or hot key `Ctrl+w`

![Waypoint Editing Panel][img_wptedit]

 * **Rule**：To pop up the [Symbol Rule Panel](#sym_rule), which makes the associations between the waypoint name and the symbols. When keying in the name, the symbol will be automatically picked up by the rules.
 * **Symbol**：Click it to open [Symbol Picker Panel](#sym_board), and choose the symbol you want to change.
 * **Focus**: Locate the waypoint int the center of the map.
 * **Name**：Display or click to ddit the waypoint name.
 * **&lt;Locaton&gt;**: Disyplay or click to edit ([ref](#location_format)) the coordinate of the waypoint. _(May have options to change default coordinate system later on)_
 * **Elevation**: Display or click to edit the elevation.
 * **Time**: Display location time. (Timezone is selected automatically)

### IV. Waypoint List

`right-click menu` -> `Show waypoints list`

![Waypoint List][img_wptlist]

<a name="sym_board"></a>
### V. Symbol Picker Panel

![Symbol Picker Panel][img_symboard]

 *  __Symbol Name__: Display in the title of `Symbol Picker Panel`
 *  __Filter__: In the lower right corner, type the keyword you want to filter.
 *  __Background Color of Symbols__:
     *  _system built-in_: light gray
     *  _user custom_: dark gray 
     *  _match the filter keyword_: ~~red~~ (hide the filted symbols in a future release)

### IV. Add User-custom Symbols

Just put your symbol files to the folder`$GISEDITOR_HOME/icon`. The filename is the symbol name.

_**👍SUGGESTION** Use english filnames, png format, transparent background, and square shape files._

<a name="sym_rule"></a>
### VII. Symbol Rule Panel

![Symbol Rule Panel][img_symrule]

 * __`Save` button__: save the rules
 * __`↓↑` buttons__: tweak the priority rules
 * __Enable/Disable__: _v_ is enabled, and _x_ is disabled
 * __Type__: Click to choose conditions:
     *  Contain：When the waypoint name contains `Text`
     *  StartWith：When the waypoint name starts with `Text`
     *  EndWith：When the waypoint name ends with `Text`
     *  Equal：When the waypoint name equals to `Text`
     *  Regex：When the waypoint name matchs the regular expression represented by `Text`
 * __Text__：The text for `Type`
 * __Symbol__：Click to open [Symbol Picker Panel](#sym_board), and choose the symbol you want to change.

_📌**NOTICE** You can set the last rule to `Type=Contain, Text=(Empty)` as the default symbol._

### VIII. 自動套用航點圖示規則

`right-click menu` -> `Apply sumbol rules`

<a name="sec_trk"></a>
3\. Track Editing
------------

<a name="trk_edit_board"></a>
### I. Track Editing Panel

`right-click menu` -> `Edit Tracks` or Hot key `Ctrl+t`.

![Track Editing Panel][img_trkboard]

 *  __Track__: Track name
 *  __Color__: Track color
 *  __`X` Button__: Delete the track
 *  __Track point__: Pcik up one or more track points to hightlight in the map.
 *  __Focus Track Point__: Locate the picked track point in the center of the map.

_📌**NOTICE** You can key in any color name which Python supports but it is not portable among other applications._

### II. Delete Tracks

In the [Track Editing Panel](#trk_edit_board), Click the `X` button.

### III. Draw Tracks

 *  To enter the Track Drawing Mode by `right-click menu` -> `Draw Track...` or hot key `F1`
 *  Drag-and-drop the mouse to draw tracks in the map.
 *  Press `ESC` to exit the mode.

### IV. Automatically Split Tracks

 *  __by days__: `right-click menu` -> `Split tracks...` -> `by day`
 *  __by time gaps__: `right-click menu` -> `Split tracks...` -> `by time gap`
 *  __by distance gaps__: `right-click menu` -> `Split tracks...` -> `by distance`

### V. Output The GPS file

`right-click menu` -> `Save to gpx...`

<a name="sec_saveimg"></a>
4\. Map Saving
----------------

`right-click menu` -> `Save to image...` or hot key `F2`

![Map Saving][img_saveimage]
 * __`S` Button__: Settings:
     *  _Precision Level_: the level for the map to output
     *  _Align Grid_: Whether the upper left corner of Select Pane aligns the grid lines (if the coordinate grid lines are supported)
     *  _Fixed Size_: Fixed the size of Select Pane. The unit is kilometer.
 * __`X` Button__: Cancel the saving
 * __`O` Button__: OK to save the map
 * __Select Pane__:
     *  _Move_: Drag-n-drop or use `Arrow keys` to move
     *  _Borders Extending_: Drag-n-drop on the borders of Select Pane to extend. Or use `Ctrl + Arrow Key` to extend and `Shift + Arrow Key` to shrink.
     *  _Bottom Right Corner Extending_: Drag-n-drop at the bottom right corner of Select Pane to extend.

<a name="sec_maplist"></a>
5\. Map Overlay
------------

![Map Overlay][img_maplist]

### I. Set Sources of Maps
 *  Applicatoin will read XML files under the folder `$GISEDITOR_HOME/mapcache` to download WMTS tiles. Please refer to [MOBAC customMapSource][custom_map_source] for the XML format.

### II. Expand/Collapse the Map List
 * Click `▼` or `▲` button beside the map name to expand/collapse the map list.

### III. Enable/Disable Maps
 * Check the checkbox to eanble the map; otherwise disable the map.

### IV. Tweak Opacity (α Value)
 * Tweak the opacity of the map. 100% is normal and 0% is transparent.

### V. The Order of Map Overlay
 * _The Order of map overlay_ is the same as the order of enabled maps from top to bottom.
 * Drag-n-Drop the name of the map to tweak the order.

![Tweak the Order of Map Overlay][img_maplist_dnd]

<a name="sec_coordline"></a>
6\. Map Grid Line
------------

![Map Grid Line][img_coord_line]

To trigger the display of TM2 grid lines, showing Kilometer or 100-Meter grid lines.

 *  TWD67 TM2 Grid Lines: Hot key `Crtl+6`
 *  TWD97 TM2 Grid Lines: Hot key `Crtl+9`

[custom_map_source]: http://mobac.sourceforge.net/wiki/index.php/Custom_XML_Map_Sources#customMapSource
[img_main]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/02_main.en.png
[img_wptedit]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/03_wpt_edit.png
[img_wptlist]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/04_wpt_list.png
[img_symboard]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/05_sym_board.png
[img_symrule]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/06_sym_rule.png
[img_trkboard]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/07_trk_board.png
[img_saveimage]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/08_save_image.png
[img_maplist]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/09_maplist.en.png
[img_maplist_dnd]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/10_maplist_dnd.en.png
[img_coord_line]: https://github.com/dayanuyim/GisEditor/raw/dev/doc/pic/11_coord_line.png
