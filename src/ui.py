#!/usr/bin/env python3

import tkinter as tk
import Pmw as pmw
import platform
import logging
from PIL import Image, ImageTk, ImageColor
from tkinter import ttk, messagebox

import src.conf as conf
from src.util import rotateLeft, rotateRight, screentone, getPrefCornerPos
from src.common import fmtPtPosText, fmtPtEleText, fmtPtTimeText

class Dialog(tk.Toplevel):
    FOCUSOUT_NOOP = 0
    FOCUSOUT_HIDE = 1
    FOCUSOUT_CLOSE = 2

    @property
    def pos(self):
        return self.__pos

    @pos.setter
    def pos(self, v):
        self.__pos = v
        self.geometry('+%d+%d' % v)

    @property
    def focusout_act(self):
        return self.__focusout_act

    @focusout_act.setter
    def focusout_act(self, v):
        self.__focusout_act = v

    def __init__(self, master):
        super().__init__(master)

        self.__focusout_act = self.FOCUSOUT_NOOP

        #handler
        #self._handlers = {}

        #board
        self.pos = (0, 0)
        self.protocol('WM_DELETE_WINDOW', lambda: self._onClosed(None))
        self.bind('<Escape>', self._onClosed)

        #silent update
        self.withdraw()  #hidden
        self._visible = tk.BooleanVar(value=False)

    def show(self, pos=None, has_title=True):
        if pos is not None:
            self.pos = pos

        if self.__focusout_act != self.FOCUSOUT_NOOP:
            self.__bindFocusout(has_title)

        self.overrideredirect(not has_title)

        #UI
        self.transient(self.master)  #remove max/min buttons
        
        self.update()  #update window size

        self.deiconify() #show
        self._visible.set(True)

        #self.attributes("-topmost", 1) #topmost
        self.lift()
        self.focus_set()  #prevent key-press sent back to parent
        self.grab_set()   #disalbe interact of parent
        self.master.wait_variable(self._visible)

    def hidden(self):
        if self.master is not None:
            self.master.focus_set()
        self.grab_release()

        self.withdraw()
        self._visible.set(False)

    def close(self):
        self.hidden()
        self.destroy()

    def _onClosed(self, e):
        self.close()

    def __bindFocusout(self, has_title):
        def on_focusout(e):
            if self == e.widget:
                self.__doFocusoutAction()

        self.bind('<FocusOut>', on_focusout)
        #focusout is not work if overrideredirect set, using enter/leave as workaround
        if not has_title:
            self.bind('<Leave>', on_focusout)

    def __doFocusoutAction(self):
        if self.__focusout_act == self.FOCUSOUT_HIDE:
            logging.debug("dialog is focus out, hidden...")
            self.hidden()
        elif self.__focusout_act == self.FOCUSOUT_CLOSE:
            logging.debug("dialog is focus out, closing...")
            self.close()


    '''
    #{{ handler
    def invokeHandler(self, name):
        if name in self._handlers:
            self._handlers[name]()

    def addClosedHandler(self, h): self._handlers['closed'] = h;
    def onClosed(self): self.invokeHandler('closed')
    #}} handler
    '''

class EditBoard(Dialog):
    COL_TYPE_STR= 0
    COL_TYPE_BOOL= 1
    COL_TYPE_PIC= 2

    @property
    def cols(self):
        return len(self._col_hdrs)

    @property
    def rows(self):
        return len(self._data)

    @property
    def data(self):
        return self._data

    def __init__(self, master, col_hdrs):
        super().__init__(master)

        self._font = 'Arialuni 12'
        self._bfont = 'Arialuni 12 bold'
        self._col_hdrs = col_hdrs
        self._data = []
        self._widgets = {}  #row data->widgets 
        self._var_widgets = {} #var_name->widget
        self._fg_color = 'black'
        self._bg_color = self.cget('bg')
        self._hl_bg_color = 'lightblue'

    def show(self):
        self.init()
        super().show()

    def init(self):
        self._sf = pmw.ScrolledFrame(self, usehullsize = 1, hull_width = 300, hull_height = 600)
        self._sf.pack(fill = 'both', expand = 1)

        frame = self._sf.interior()
        font = self._font
        bfont = self._bfont

        row, col = 0, 0
        #show column headers
        for col_hdr in self._col_hdrs:
            type, title, editable = col_hdr
            tk.Label(frame, text=title, font=bfont).grid(row=row, column=col)
            col += 1

        for row_data in self._data:
            row += 1
            widgets = self.initRowWidgets(row)
            self.initRowData(widgets, row_data)
            self._widgets[row] = widgets

    def initRowWidgets(self, row):
        frame = self._sf.interior()
        bfont = self._bfont
        font = self._font
        widgets = []
        col = 0

        for col_hdr in self._col_hdrs:
            type, title, editable = col_hdr

            #create widget
            if type == self.COL_TYPE_STR and editable:
                w = tk.Entry(frame, font=font, relief='flat', state='disabled',
                        disabledforeground=self._fg_color, disabledbackground=self._bg_color)
                self.setWidgetEditable(w, self._onCellChanged)
            elif type == self.COL_TYPE_STR and not editable:
                w = tk.Label(frame, font=font, anchor='w')
            elif type == self.COL_TYPE_BOOL:
                w = tk.Label(frame, font=bfont, anchor='e')
            elif type == self.COL_TYPE_PIC:
                w = tk.Label(frame, anchor='w', compound='left')

            w.grid(row=row, column=col, sticky='news')
            widgets.append(w)
            col += 1

        return widgets

    def _onCellChanged(self, widget):
        pass

    def setWidgetEditable(self, w, cb):
        var = tk.StringVar()
        w.config(textvariable=var)
        w.variable = var  #keep ref: widget->var
        self._var_widgets[str(var)] = w  #keep ref: var->widget

        def onEnterEdit(e):
            e.widget.config(state='normal')
            e.widget.focus_set()

        def onLeaveEdit(e):
            if e.widget.cget('state') == 'normal':
                e.widget.config(state='disabled')

        def onEditWrite(*args):
            var_name = args[0]
            widget = self._var_widgets.get(var_name)
            cb(widget)

        w.bind('<Double-Button-1>', onEnterEdit)
        w.bind('<Leave>', onLeaveEdit)
        w.bind('<Return>', onLeaveEdit)
        w.variable.trace_variable('w', onEditWrite)


    def initRowData(self, widgets, row_data):
        col = 0
        for col_hdr in self._col_hdrs:
            type, title, editable = col_hdr

            cell_data = row_data[col]
            w = widgets[col]

            if type == self.COL_TYPE_STR and editable:
                w.variable.set(cell_data)
            elif type == self.COL_TYPE_STR and not editable:
                w.config(text=cell_data)
            elif type == self.COL_TYPE_BOOL:
                text = 'v' if cell_data else 'x'
                color = 'green' if cell_data else 'red'
                w.config(text=text, fg=color)
            elif type == self.COL_TYPE_PIC:
                img = ImageTk.PhotoImage(cell_data)
                w.config(image=img, text='')
                w.image = img  #keep ref

            col += 1

    def TMP(self):
        for w in self._elems:
            row += 1
            on_motion = lambda e: self.onMotion(e)

            #icon
            icon = ImageTk.PhotoImage(conf.getIcon(w.sym))
            icon_label = tk.Label(frame, image=icon, anchor='e')
            icon_label.image=icon
            icon_label.bind('<Motion>', on_motion)
            icon_label.grid(row=row, column=0, sticky='news')

            name_label = tk.Label(frame, text=w.name, font=font, anchor='w')
            name_label.bind('<Motion>', on_motion)
            name_label.grid(row=row, column=1, sticky='news')

            pos_txt = fmtPtPosText(w)
            pos_label = tk.Label(frame, text=pos_txt, font=font)
            pos_label.bind('<Motion>', on_motion)
            pos_label.grid(row=row, column=2, sticky='news')

            ele_label = tk.Label(frame, text=fmtPtEleText(w), font=font)
            ele_label.bind('<Motion>', on_motion)
            ele_label.grid(row=row, column=3, sticky='news')

            time_label = tk.Label(frame, text=fmtPtTimeText(w), font=font)
            time_label.bind('<Motion>', on_motion)
            time_label.grid(row=row, column=4, sticky='news')

            #save
            self.__widgets[w] = (
                    icon_label,
                    name_label,
                    pos_label,
                    ele_label,
                    time_label
            )

    def addRow(self, row_data):
        if len(row_data) != self.cols:
            raise ValueError("The data number is not equal to the column number.")
        self._data.append(tuple(row_data))


class ListEditBoard(Dialog):
    def __init__(self, master, elems, wpt=None):
        super().__init__(master)

        self.__widgets = {}  #wpt: widgets 
        self.__focused_wpt = None
        self.__bg_color = self.cget('bg')
        self.__bg_hl_color = 'lightblue'
        self.init()
                
        #set wpt
        if wpt is not None:
            self.setCurrWpt(wpt)

        #wait
        self.wait_window(self)

    def init(self):
        self.sf = pmw.ScrolledFrame(self, usehullsize = 1, hull_width = 300, hull_height = 600)
        self.sf.pack(fill = 'both', expand = 1)


        frame = self.sf.interior()
        font = self._font
        bfont = self._bold_font

        row = 0
        tk.Label(frame, text=self._title_name, font=bfont).grid(row=row, column=1)
        tk.Label(frame, text=self._title_pos,  font=bfont).grid(row=row, column=2)
        tk.Label(frame, text=self._title_ele,  font=bfont).grid(row=row, column=3)
        tk.Label(frame, text=self._title_time, font=bfont).grid(row=row, column=4)

        for w in self._elems:
            row += 1
            on_motion = lambda e: self.onMotion(e)

            #icon
            icon = ImageTk.PhotoImage(conf.getIcon(w.sym))
            icon_label = tk.Label(frame, image=icon, anchor='e')
            icon_label.image=icon
            icon_label.bind('<Motion>', on_motion)
            icon_label.grid(row=row, column=0, sticky='news')

            name_label = tk.Label(frame, text=w.name, font=font, anchor='w')
            name_label.bind('<Motion>', on_motion)
            name_label.grid(row=row, column=1, sticky='news')

            pos_txt = fmtPtPosText(w)
            pos_label = tk.Label(frame, text=pos_txt, font=font)
            pos_label.bind('<Motion>', on_motion)
            pos_label.grid(row=row, column=2, sticky='news')

            ele_label = tk.Label(frame, text=fmtPtEleText(w), font=font)
            ele_label.bind('<Motion>', on_motion)
            ele_label.grid(row=row, column=3, sticky='news')

            time_label = tk.Label(frame, text=fmtPtTimeText(w), font=font)
            time_label.bind('<Motion>', on_motion)
            time_label.grid(row=row, column=4, sticky='news')

            #save
            self.__widgets[w] = (
                    icon_label,
                    name_label,
                    pos_label,
                    ele_label,
                    time_label
            )

    def getWptOfWidget(self, w):
        for wpt, widgets in self.__widgets.items():
            if w in widgets:
                return wpt
        return None

    def onMotion(self, e):
        prev_wpt = self.__focused_wpt
        curr_wpt = self.getWptOfWidget(e.widget)

        #highligt/unhighlight
        if prev_wpt != curr_wpt:
            if prev_wpt is not None:
                self.unhighlightWpt(prev_wpt)
            if curr_wpt is not None:
                self.highlightWpt(curr_wpt)
                
        #rec
        self.__focused_wpt = curr_wpt

    #override
    def highlightWpt(self, wpt, is_focus=False):
        for w in self.__widgets[wpt]:
            w.config(bg=self.__bg_hl_color)
        super().highlightWpt(wpt)

    #override
    def unhighlightWpt(self, wpt):
        for w in self.__widgets[wpt]:
            w.config(bg=self.__bg_color)
        #super().unhighlightWpt(wpt)  #can skip, deu to followed by highlight

    #override
    def showWptIcon(self, wpt):
        pass

    #override
    def setCurrWpt(self, wpt):
        self._curr = wpt

class SingleEditBoard(Dialog):
    def __init__(self, master, elems, wpt=None):
        super().__init__(master, elems, wpt)

        #change buttons
        self.__left_btn = tk.Button(self, text="<<", command=lambda:self.onWptSelected(-1), disabledforeground='gray')
        self.__left_btn.pack(side='left', anchor='w', expand=0, fill='y')
        self.__right_btn = tk.Button(self, text=">>", command=lambda:self.onWptSelected(1), disabledforeground='gray')
        self.__right_btn.pack(side='right', anchor='e', expand=0, fill='y')

        #info
        self.info_frame = self.getInfoFrame()
        self.info_frame.pack(side='bottom', anchor='sw', expand=0, fill='x')

        #image
        self.__img_label = None
        self.__img_sz = (img_w, img_h) = (600, 450)
        if self._hasPicWpt():
            #bd=0: let widget size align image size; set width/height to disable auto resizing
            self.__img_label = tk.Label(self, bg='black', bd=0, width=img_w, height=img_h)
            self.__img_label.pack(side='top', anchor='nw', expand=1, fill='both', padx=0, pady=0)
            self.__img_label.bind('<Configure>', self.onImageResize)

        #set wpt
        if wpt is None:
            wpt = elems[0]
        self.setCurrWpt(wpt)

        #wait
        self.wait_window(self)

    def onImageResize(self, e):
        if hasattr(self.__img_label, 'image'):
            img_w = self.__img_label.image.width()
            img_h = self.__img_label.image.height()
            #print('event: %d, %d; winfo: %d, %d; label: %d, %d; img: %d, %d' % (e.width, e.height, self.__img_label.winfo_width(), self.__img_label.winfo_height(), self.__img_label['width'], self.__img_label['height'], img_w, img_h))
            if e.width < img_w or e.height < img_h or (e.width > img_w and e.height > img_h):
                #print('need to zomm image')
                self.setWptImg(self._curr)

    def onWptSelected(self, inc):
        idx = self._elems.index(self._curr) + inc
        if idx >= 0 and idx < len(self._elems):
            self.setCurrWpt(self._elems[idx])

    def getInfoFrame(self):
        font = self._font
        bold_font = self._bold_font

        frame = tk.Frame(self)#, bg='blue')

        row = 0
        #set sym rule
        tk.Button(frame, text="Rule...", font=font, relief='groove', overrelief='ridge', command=self.onEditSymRule).grid(row=row, column=0, sticky='w')
        #wpt icon
        self.__icon_label = tk.Label(frame)
        self.__icon_label.grid(row=row, column=1, sticky='e')
        self.__icon_label.bind('<Button-1>', self.onSymClick)

        #wpt name
        name_entry = tk.Entry(frame, textvariable=self._var_name, font=font)
        name_entry.bind('<Return>', lambda e: self.onWptSelected(1))
        name_entry.grid(row=row, column=2, sticky='w')

        row += 1
        #focus
        tk.Checkbutton(frame, text=self._title_focus, variable=self._var_focus).grid(row=row, column=0, sticky='w')
        #wpt positoin
        tk.Label(frame, text=self._title_pos, font=bold_font).grid(row=row, column=1, sticky='e')
        self._var_pos = tk.StringVar()
        tk.Label(frame, font=font, textvariable=self._var_pos).grid(row=row, column=2, sticky='w')

        row +=1
        #ele
        tk.Label(frame, text=self._title_ele, font=bold_font).grid(row=row, column=1, sticky='e')
        self._var_ele = tk.StringVar()
        tk.Label(frame, font=font, textvariable=self._var_ele).grid(row=row, column=2, sticky='w')

        row +=1
        #time
        tk.Label(frame, text=self._title_time, font=bold_font).grid(row=row, column=1, sticky='e')
        self._var_time = tk.StringVar()
        tk.Label(frame, textvariable=self._var_time, font=font).grid(row=row, column=2, sticky='w')

        return frame

    def onSymClick(self, e):
        wpt = self._curr
        sym = askSym(self, pos=(e.x_root, e.y_root), init_sym=wpt.sym)

        if sym is not None and sym != wpt.sym:
            wpt.sym = sym
            self._is_changed = True
            self.showWptIcon(wpt)

            #update map
            self.onAltered('wpt')
            self.highlightWpt(wpt)

    def showWptIcon(self, wpt):
        icon = ImageTk.PhotoImage(conf.getIcon(wpt.sym))
        self.__icon_label.image = icon
        self.__icon_label.config(image=icon, text=wpt.sym, compound='right')

    def setWptImg(self, wpt):
        img_w = self.__img_label

        if img_w is None:
            return
        size = self.__img_sz if not hasattr(img_w, 'image') else (img_w.winfo_width(), img_w.winfo_height())
        img = getAspectResize(wpt.img, size) if isinstance(wpt, PicDocument) else getTextImag("(No Pic)", size)
        img = ImageTk.PhotoImage(img)
        img_w.config(image=img)
        img_w.image = img #keep a ref

    def setCurrWpt(self, wpt):
        if self._curr != wpt:
            self.unhighlightWpt(self._curr)
            self.highlightWpt(wpt)

        self._curr = wpt

        #title
        self.title(wpt.name)

        #set imgae
        self.setWptImg(wpt)

        #info
        self.showWptIcon(wpt)
        self._var_name.set(wpt.name)   #this have side effect to set symbol icon
        self._var_pos.set(fmtPtPosText(wpt))
        self._var_ele.set(fmtPtEleText(wpt))
        self._var_time.set(fmtPtTimeText(wpt))

        #button state
        if self._elems is not None:
            idx = self._elems.index(wpt)
            sz = len(self._elems)
            self.__left_btn.config(state=('disabled' if idx == 0 else 'normal'))
            self.__right_btn.config(state=('disabled' if idx == sz-1 else 'normal'))

class MapRow(tk.Frame):
    ALPHA_MIN = 1
    ALPHA_MAX = 100

    @property
    def map_desc(self):
        return self.__map_desc

    @property
    def click_down_handler(self): return self.__click_down_handler

    @click_down_handler.setter
    def click_down_handler(self, h): self.__click_down_handler = h

    @property
    def click_motion_handler(self): return self.__click_motion_handler

    @click_motion_handler.setter
    def click_motion_handler(self, h): self.__click_motion_handler = h

    @property
    def click_up_handler(self): return self.__click_up_handler

    @click_up_handler.setter
    def click_up_handler(self, h): self.__click_up_handler = h

    @property
    def alpha_handler(self): return self.__alpha_handler

    @alpha_handler.setter
    def alpha_handler(self, h): self.__alpha_handler = h

    @property
    def enable_handler(self): return self.__enable_handler

    @enable_handler.setter
    def enable_handler(self, h): self.__enable_handler = h

    def __init__(self, master, map_desc):
        super().__init__(master)

        FONT = "Arialuni 12"
        BFONT = FONT + " bold"
        DISABLED_FG = 'gray70'

        #inner data
        self.__map_desc = map_desc

        #event handlers
        self.__click_up_handler = None
        self.__click_down_handler = None
        self.__click_motion_handler = None
        self.__alpha_handler = None
        self.__enable_handler = None

        #alpha variable
        alpha = int(map_desc.alpha * 100)
        self.__alpha_var = tk.IntVar(value=alpha)
        self.__alpha_var.trace('w', self.__onAlphaChanged)

        #en variable
        self.__en_var = tk.BooleanVar(value=map_desc.enabled)
        self.__en_var.trace('w', self.__onEnableChanged)

        #enabled
        ckbox = tk.Checkbutton(self, variable=self.__en_var)
        ckbox.pack(side='left', anchor='w', expand=0)

        #title
        label = tk.Label(self, text=map_desc.map_title, font=BFONT, disabledforeground=DISABLED_FG, anchor='w')
        label.pack(side='left', anchor='w', expand='1', fill='x')
        label.bind('<Button-1>', self.__onClickDown)
        label.bind('<Button1-Motion>', self.__onClickMotion)
        label.bind('<Button1-ButtonRelease>', self.__onClickUp)

        #spin
        alpha_label = tk.Label(self, text="%")
        alpha_label.pack(side='right', anchor='e', expand=0)
        alpha_spin = tk.Spinbox(self, from_=self.ALPHA_MIN, to=self.ALPHA_MAX, width=3, textvariable=self.__alpha_var)
        alpha_spin.pack(side='right', anchor='e', expand=0)
        #sacle
        #alpha_scale = tk.Scale(self, label="Transparency", from_=ALPHA_MIN, to=ALPHA_MAX, orient='horizontal',
                #resolution=1, showvalue=0, variable=self.__alpha_var)
        #alpha_scale.pack(side='right', anchor='e', expand=0, fill='x')

        #collect widgets for later use
        self.__widgets = [self, ckbox, label, alpha_spin, alpha_label]
        self.__origin_bgs = [ w['bg'] for w in self.__widgets]

        #enabled/disabled
        self.__updateState()

    def __onClickDown(self, e):
        #logging.critical('down %d %d' % (e.x, e.y))
        if self.__click_down_handler is not None:
            self.__click_down_handler(self, (e.x, e.y))

    def __onClickMotion(self, e):
        #logging.critical('motion %d %d' % (e.x, e.y))
        if self.__click_motion_handler is not None:
            self.__click_motion_handler(self, (e.x, e.y))

    def __onClickUp(self, e):
        #logging.critical('up %d %d' % (e.x, e.y))
        if self.__click_up_handler is not None:
            self.__click_up_handler(self, (e.x, e.y))

    def setBackground(self, color):
        for w in self.__widgets:
            w['bg'] = color

    def resetBackground(self):
        for i in range(len(self.__widgets)):
            self.__widgets[i]['bg'] = self.__origin_bgs[i]

    def __updateState(self):
        for w in self.__widgets:
            if isinstance(w, tk.Label) or isinstance(w, tk.Spinbox):
                w['state'] = 'normal' if self.map_desc.enabled else 'disabled'

    def __onEnableChanged(self, *args):
        old_val = self.__map_desc.enabled
        new_val = not old_val
        try:
            self.__map_desc.enabled = new_val
            self.__updateState()

            if self.__enable_handler is not None:
                self.__enable_handler(self, old_val)
        except Exception as ex:
            logging.warning("set enabled value error: " + str(ex))

    def __onAlphaChanged(self, *args):
        old_val = self.__map_desc.alpha

        try:
            #get new value
            raw_val = self.__alpha_var.get()
            if not self.ALPHA_MIN <= raw_val <= self.ALPHA_MAX: #only accept valid value
                return
            new_val = raw_val / 100.0

            #update
            if self.__map_desc.alpha != new_val:
                self.__map_desc.alpha = new_val

                if self.__alpha_handler is not None:
                    self.__alpha_handler(self, old_val)
        except Exception as ex:
            logging.warning("set alpha value error: " + str(ex))


class MapSelectFrame(pmw.ScrolledFrame):
    @property
    def map_descriptors(self):
        return [ r.map_desc for r in self.__maprows]

    @property
    def __splitors(self):
        return [ self.__widgets[i] for i in range(len(self.__widgets)) if i % 2 == 0]

    @property
    def __maprows(self):
        return [ self.__widgets[i] for i in range(len(self.__widgets)) if i % 2 == 1]

    @property
    def alpha_changed_handler(self): return self.__alpha_changed_handler

    @alpha_changed_handler.setter
    def alpha_changed_handler(self, h): self.__alpha_changed_handler = h

    @property
    def enable_changed_handler(self): return self.__enable_changed_handler

    @enable_changed_handler.setter
    def enable_changed_handler(self, h): self.__enable_changed_handler = h

    def __init__(self, master, map_descriptors):
        super().__init__(master, usehullsize=1, hull_width=450, hull_height=600)

        #event handlers (reservd)
        self.__enable_changed_handler = None
        self.__alpha_changed_handler = None

        #bookkeeper
        self.__dst_splitor = None

        #create widgets
        self.__widgets = [self._genSplitor()]
        for desc in map_descriptors:
            self.__widgets.append(self._genMapRow(desc))
            self.__widgets.append(self._genSplitor())

        #colors
        self.__normal_bg = self.__widgets[0]['bg']
        self.__candicate_bg = 'blue'
        self.__src_bg = 'blue'
        self.__dst_bg = 'red'

        #pack
        self.__pack()

    #should call this after 'self' is placed
    def fitwidth(self):
        self.update()
        max_w = max([w.winfo_width() for w in self.__maprows]) + 25  #25: scrollbar
        self['hull_width'] = max_w

    def _genSplitor(self):
        return tk.Frame(self.interior(), height=4, border=1)

    def _genMapRow(self, desc):
        w = MapRow(self.interior(), desc)
        w.alpha_handler = self.__onAlphaChanged
        w.enable_handler = self.__onEnableChanged
        w.click_up_handler = self.__onMapRowClickUp
        w.click_down_handler = self.__onMapRowClickDown
        w.click_motion_handler = self.__onMapRowClickMotion
        return w

    def __getwidget(self, pos):
        x, y = pos
        if y < 0:
            return None
        for w in self.__widgets:
            y -= w.winfo_height()
            if y < 0:
                return w
        return None

    def __getpos(self, widget):
        x, y = 0, 0
        for w in self.__widgets:
            if w == widget:
                break;
            #x += w.winfo_width()
            y += w.winfo_height()
        return x, y

    def __pack(self):
        for w in self.__widgets:
            w.pack(side='top', anchor='nw', expand=1, fill='x')

    def __unpack(self):
        for w in self.__widgets:
            w.pack_forget()

    def __onEnableChanged(self, row, old_val):
        if self.__enable_changed_handler is not None:
            self.__enable_changed_handler(row.map_desc, old_val)

    def __onAlphaChanged(self, row, old_val):
        if self.__alpha_changed_handler is not None:
            self.__alpha_changed_handler(row.map_desc, old_val)

    def __onMapRowClickDown(self, row, pos):
        #get candicate splitor
        idx = self.__widgets.index(row)
        self.__candicate_splitors = \
            [ self.__widgets[i] for i in range(len(self.__widgets)) if i % 2 == 0 and abs(i-idx) > 1]
        
        #set color
        row.setBackground(self.__src_bg)
        for s in self.__candicate_splitors:
            s['bg'] = self.__candicate_bg

    def __onMapRowClickUp(self, row, pos):
        # unset color
        row.resetBackground()
        for s in self.__splitors:
            s['bg'] = self.__normal_bg

        #get src/dst
        if self.__dst_splitor is None:
            return
        src_idx = self.__widgets.index(row)
        dst_idx = self.__widgets.index(self.__dst_splitor)
        dst_idx += 1 if dst_idx < src_idx else -1
        self.__dst_splitor = None

        #rotate
        if dst_idx < src_idx:
            rotateRight(self.__widgets, dst_idx, src_idx, 2)
        else:
            rotateLeft(self.__widgets, src_idx, dst_idx, 2)

        #rest ui
        self.__unpack()
        self.__pack()

    
    def __onMapRowClickMotion(self, row, pos):
        #calc dst pos, 
        x, y = pos
        src_x, src_y = self.__getpos(row) 
        dst_pos = src_x + x, src_y + y

        # set dst widget
        dst_w = self.__getwidget(dst_pos)

        # unset old splitor
        if self.__dst_splitor and self.__dst_splitor != dst_w:
            self.__dst_splitor['bg'] = self.__candicate_bg
            self.__dst_splitor = None
        # set new splitor
        if dst_w in self.__candicate_splitors and dst_w != self.__dst_splitor:
            self.__dst_splitor = dst_w
            self.__dst_splitor['bg'] = self.__dst_bg

def testMapSelector():
    import os
    import sys
    sys.path.insert(0, 'src')
    from tile import MapDescriptor

    root = tk.Tk()

    #desc
    map_descs = []
    mapcache = "mapcache"
    for f in os.listdir(mapcache):
        if os.path.splitext(f)[1].lower() == ".xml":
            try:
                desc = MapDescriptor.parseXml(os.path.join(mapcache, f))
                if desc.map_id in ('TM25K_2001',  'JM25K_1921'):
                    desc.enabled = True
                    desc.alpha = 0.75
                map_descs.append(desc)
            except Exception as ex:
                print("parse file '%s' error: %s" % (f, str(ex)))
    map_descs = sorted(map_descs, key=lambda d:d.map_title)

    #show
    dialog = Dialog(root)
    selector = MapSelectFrame(dialog, map_descs)
    selector.pack(side='top', anchor='nw', expand=0)
    dialog.show()

    for desc in selector.map_descriptors:
        print(desc.map_id, desc.alpha, desc.enabled)

    root.mainloop()

# Map Selector ==================================================

# Why I have 2 Dialog classes ?!
class Dialog2(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self._result = 'Unknown' #need subclass to set

        self.title('')
        self.resizable(0, 0)
        self.bind('<Escape>', lambda e: self.exit())
        self.protocol('WM_DELETE_WINDOW', self.exit)

        self.withdraw()  #for silent update
        self.visible = tk.BooleanVar(value=False)

        #update window size
        self.update()

    def exit(self):
        self.master.focus_set()
        self.grab_release()
        self.destroy()
        self.visible.set(False)

    def show(self, pos=None):
        self.setPos(pos)

        #UI
        self.transient(self.master)  #remove max/min buttons
        self.focus_set()  #prevent key-press sent back to parent

        self.deiconify() #show
        self.visible.set(True)

        self.grab_set()   #disalbe interact of parent
        self.master.wait_variable(self.visible)

        return self._result

    def setPos(self, pos):
        pos = (0,0) if pos is None else getPrefCornerPos(self, pos)
        self.geometry('+%d+%d' % pos)


class AreaSelectorSettings(Dialog2):
    def __init__(self, master, disableds=[]):
        super().__init__(master)

        self.__size_widgets = []

        #settings by conf
        self.var_level = tk.IntVar(value=conf.SELECT_AREA_LEVEL)
        self.var_align = tk.BooleanVar(value=conf.SELECT_AREA_ALIGN)
        self.var_fixed = tk.BooleanVar(value=conf.SELECT_AREA_FIXED)
        self.var_w = tk.DoubleVar(value=conf.SELECT_AREA_X)
        self.var_h = tk.DoubleVar(value=conf.SELECT_AREA_Y)

        #level
        row = 0
        f = tk.Frame(self)
        f.grid(row=row, column=0, sticky='w')
        tk.Label(f, text='precision: level', anchor='e').pack(side='left', expand=1, fill='both')
        tk.Spinbox(f, from_=conf.MIN_SUPP_LEVEL, to=conf.MAX_SUPP_LEVEL, width=2, textvariable=self.var_level)\
                .pack(side='left', expand=1, fill='both')

        #align
        row += 1
        f = tk.Frame(self)
        f.grid(row=row, column=0, sticky='w')
        tk.Checkbutton(f, text='Align grid', variable=self.var_align,
                     state='disabled' if 'align' in disableds else 'normal') \
                .pack(side='left', expand=1, fill='both')

        #fixed
        row += 1
        def checkSizeWidgets():
            for w in self.__size_widgets:
                s = 'normal' if self.var_fixed.get() else 'disabled'
                w.config(state=s)
        f = tk.Frame(self)
        f.grid(row=row, column=0, sticky='w')
        tk.Checkbutton(f, text='Fixed size (KM)', variable=self.var_fixed, command=checkSizeWidgets)\
                .pack(side='left', expand=1, fill='both')

        #size
        w = tk.Entry(f, textvariable=self.var_w, width=5)
        w.pack(side='left', expand=1, fill='both')
        self.__size_widgets.append(w)

        w = tk.Label(f, text='X')
        w.pack(side='left', expand=1, fill='both')
        self.__size_widgets.append(w)

        w = tk.Entry(f, textvariable=self.var_h, width=5)
        w.pack(side='left', expand=1, fill='both')
        self.__size_widgets.append(w)

        #init run
        checkSizeWidgets()

    #override
    def exit(self):
        if self.isModified():
            self.saveSettings()
            self._result = 'OK'
        else:
            self._result = 'Cancel'
        super().exit()

    def isModified(self):
        return conf.SELECT_AREA_LEVEL != self.var_level.get() or\
               conf.SELECT_AREA_ALIGN != self.var_align.get() or\
               conf.SELECT_AREA_FIXED != self.var_fixed.get() or\
               conf.SELECT_AREA_X != self.var_w.get() or\
               conf.SELECT_AREA_Y != self.var_h.get()

    def saveSettings(self):
        conf.SELECT_AREA_LEVEL = self.var_level.get()
        conf.SELECT_AREA_ALIGN = self.var_align.get()
        conf.SELECT_AREA_FIXED = self.var_fixed.get()
        conf.SELECT_AREA_X = self.var_w.get()
        conf.SELECT_AREA_Y = self.var_h.get()
        conf.writeUserConf()

def bindCanvasDragEvents(canvas, item, cb, cursor='', enter_cb=None, leave_cb=None, release_cb=None):
    def setCursor(c):
        canvas['cursor'] = c
    def onClick(e):
        canvas.__canvas_mpos = (e.x, e.y)
    def onClickRelease(e):
        canvas.__canvas_mpos = None
        if release_cb:
            release_cb(e)
    def onClickMotion(e):
        x, y = canvas.__canvas_mpos
        dx, dy = e.x-x, e.y-y
        canvas.__canvas_mpos = (e.x, e.y)
        cb(e, dx, dy)

    if enter_cb is None: enter_cb = lambda e: setCursor(cursor)
    if leave_cb is None: leave_cb = lambda e: setCursor('')

    canvas.tag_bind(item, "<Enter>", enter_cb)
    canvas.tag_bind(item, "<Leave>", leave_cb)
    canvas.tag_bind(item, "<Button-1>", onClick)
    canvas.tag_bind(item, "<Button1-ButtonRelease>", onClickRelease)
    canvas.tag_bind(item, "<Button1-Motion>", onClickMotion)

def unbindCanvasDragEvents(canvas, item):
    canvas.tag_unbind(item, "<Enter>")
    canvas.tag_unbind(item, "<Leave>")
    canvas.tag_unbind(item, "<Button-1>")
    canvas.tag_unbind(item, "<Button1-ButtonRelease>")
    canvas.tag_unbind(item, "<Button1-Motion>")

#if 'autorepeat' is enabled, KeyRelease will be triggered even if the key is NOT physically released.
#using timer to trigger the release event only if we think the key is actually released.
def bindWidgetKeyMoveEvents(w, cb=None, ctrl_cb=None, shift_cb=None, release_cb=None, release_delay=0.3):
    def onKeyPress(cb_, e, dx, dy):
        if release_cb:
            #cancel the recent release event, if press time is closed to relase time
            if w.__move_key_release_timer and (e.time - w.__move_key_release_time)/1000 < release_delay:
                w.__move_key_release_timer.cancel()

        cb_(e, dx, dy)

    def onKeyRelease(e):
        w.__move_key_release_time = e.time
        w.__move_key_release_timer = Timer(release_delay, release_cb, (e,))
        w.__move_key_release_timer.start()

    if cb:
        w.bind('<Up>', lambda e: onKeyPress(cb, e, 0, -1))
        w.bind('<Down>', lambda e: onKeyPress(cb, e, 0, 1))
        w.bind('<Left>', lambda e: onKeyPress(cb, e, -1, 0))
        w.bind('<Right>', lambda e: onKeyPress(cb, e, 1, 0))

    if ctrl_cb:
        w.bind('<Control-Up>', lambda e: onKeyPress(ctrl_cb, e, 0, -1))
        w.bind('<Control-Down>', lambda e: onKeyPress(ctrl_cb, e, 0, 1))
        w.bind('<Control-Left>', lambda e: onKeyPress(ctrl_cb, e, -1, 0))
        w.bind('<Control-Right>', lambda e: onKeyPress(ctrl_cb, e, 1, 0))

    if shift_cb:
        w.bind('<Shift-Up>', lambda e: onKeyPress(shift_cb, e, 0, -1))
        w.bind('<Shift-Down>', lambda e: onKeyPress(shift_cb, e, 0, 1))
        w.bind('<Shift-Left>', lambda e: onKeyPress(shift_cb, e, -1, 0))
        w.bind('<Shift-Right>', lambda e: onKeyPress(shift_cb, e, 1, 0))

    if release_cb:
        w.__move_key_release_timer = None
        w.__move_key_release_time = 0
        w.bind('<KeyRelease-Up>', onKeyRelease)
        w.bind('<KeyRelease-Down>', onKeyRelease)
        w.bind('<KeyRelease-Left>', onKeyRelease)
        w.bind('<KeyRelease-Right>', onKeyRelease)

class AreaSizeTooLarge(Exception):
    pass

class AreaSelector:
    @property
    def size(self):
        return self.__cv_panel_img.width(), self.__cv_panel_img.height()

    @property
    def pos(self):
        if self.__done.get():
            return self.__last_pos
        else:
            return self.__getpos()

    def __init__(self, canvas, geo_info):
        self.__canvas = canvas
        self.__geo_info = geo_info
        self.__button_side = 20
        self.__resizer_side = 15
        self.__done = tk.BooleanVar(value=False)
        self.__state = None
        self.__last_pos = None
        self.__except = None
        self.__panel_color = 'yellow'

        canvas_w = canvas.winfo_width()
        canvas_h = canvas.winfo_height()

        #size
        size = self.getFixedSize()
        if size is None:
            size = (round(canvas_w/2), round(canvas_h/2))
        w, h = size
        #pos
        pos = (round((canvas_w-w)/2), round((canvas_h-h)/2))

        #ceate items
        self.makeAreaPanel(pos, size)
        self.makeAreaBorders(pos, size)
        self.genOKButton()
        self.genCancelButton()
        self.genSettingButton()

        #apply
        try:
            self.applySettings()
        except AreaSizeTooLarge as ex:
            self.exit()
            raise ex

    #{{ interface
    def wait(self, parent):
        parent.wait_variable(self.__done)
        if self.__except:
            raise self.__except
        return self.__state

    def exit(self):
        if self.__done.get():
            return
        #rec the last pos
        self.__last_pos = self.__getpos()
        #delete item
        self.__canvas.delete('AS')  #delete objects of 'AreaSelector'
        self.__canvas['cursor'] = ''
        self.__done.set(True)

    #}} interface


    #{{ canvas items
    def makeAreaPanel(self, pos, size):
        self.__makeAreaPanel('panel', pos, size)

    def __makeAreaPanel(self, name, pos, size):
        #if exist and the same
        item = self.__canvas.find_withtag(name)
        if item and self.size == size:
            dx = pos[0] - self.pos[0]
            dy = pos[1] - self.pos[1]
            self.__canvas.move(name, dx, dy)
            return
        self.__canvas.delete(name)
        self.__genPanel(name, pos, size)


    def __genPanel(self, name, pos, size):
        #area img
        w = max(1, size[0])
        h = max(1, size[1])

        if platform.system() == "Darwin":
            img = Image.new('RGBA', (w,h), self.__panel_color)
            img = screentone(img)  # experimental: workaround for drawing alpha on MAC
        else:
            color = ImageColor.getrgb(self.__panel_color) + (96,) #transparent
            img = Image.new('RGBA', (w,h), color)
        img = ImageTk.PhotoImage(img) #to photo image

        #area item
        item = self.__canvas.create_image(pos, image=img, anchor='nw', tag=('AS',name))
        #bind
        bindCanvasDragEvents(self.__canvas, item, self.onMove, cursor='hand2',
            release_cb=lambda e: self.adjustPos())
        bindWidgetKeyMoveEvents(self.__canvas, self.onMove,
            lambda e, dx, dy: self.onResize('ctrl-arrow', e, dx, dy),
            lambda e, dx, dy: self.onResize('shift-arrow', e, dx, dy),
            lambda e: self.adjustPos())
        #side effect to keep ref
        self.__cv_panel_img = img

    def makeAreaBorders(self, pos, size):
        gpname = 'border'
        x, y = pos
        w, h = size
        #gen
        self.__makeBorder(gpname, 'top',    (x,y,x+w,y))
        self.__makeBorder(gpname, 'bottom', (x,y+h,x+w,y+h))
        self.__makeBorder(gpname, 'left',   (x,y,x,y+h))
        self.__makeBorder(gpname, 'right',  (x+w,y,x+w,y+h))

    def __makeBorder(self, gpname, name, coords):
        #if exist and the same
        item = self.__canvas.find_withtag(name)
        if item:
            orig_coords = self.__canvas.coords(item)
            if equalsLine(orig_coords, coords):
                #print("resizing border '%s' by moving" % (name,))
                dx = coords[0] - orig_coords[0]
                dy = coords[1] - orig_coords[1]
                self.__canvas.move(item, dx, dy) #just move
                return

        self.__canvas.delete(name)   #delete old
        self.__genBorder(gpname, name, coords)  #gen new

    def __genBorder(self, gpname, name, coords):
        color = self.__panel_color
        cursor = name + '_side'

        def onBorderEnter(e):
            if not conf.SELECT_AREA_FIXED:
                self.__canvas['cursor'] = cursor

        def onBorderLeave(e):
            if not conf.SELECT_AREA_FIXED:
                self.__canvas['cursor'] = ''

        border = self.__canvas.create_line(coords, width=2, fill=color, tag=('AS', gpname, name))
        bindCanvasDragEvents(self.__canvas, border,
            lambda e, dx, dy: self.onResize(name, e, dx, dy),
            enter_cb=onBorderEnter,
            leave_cb=onBorderLeave,
            release_cb=lambda e: self.adjustPos())

    def genOKButton(self, order=1):
        n = self.__button_side
        x = self.pos[0] + self.size[0] - self.__button_side*order #x of upper-left
        y = self.pos[1]  #y of upper-left
        item = self.__canvas.create_oval(x, y, x+n, y+n, fill='green', activefill='lime green', tag=('AS','button', 'ok'))
        self.__canvas.tag_bind(item, "<Button-1>", self.onOkClick)

    def genCancelButton(self, order=2):
        n = int(self.__button_side/4)
        x = self.pos[0] + self.size[0] - self.__button_side*order + 2*n  #x of center
        y = self.pos[1] + 2*n #y of center
        cross = ((0,n), (n,2*n), (2*n,n), (n,0), (2*n,-n), (n,-2*n), (0,-n), (-n,-2*n), (-2*n,-n), (-n,0), (-2*n,n), (-n, 2*n))
        cancel_cross = []
        for pt in cross:
            cancel_cross.append((pt[0]+x, pt[1]+y))
        item = self.__canvas.create_polygon(cancel_cross, fill='red3', activefill='red', tag=('AS','button', 'cancel'))
        self.__canvas.tag_bind(item, "<Button-1>", self.onCancelClick)

    def genSettingButton(self, order=3):
        n = int(self.__button_side/2)
        x = self.pos[0] + self.size[0] - self.__button_side*order + n  #x of center
        y = self.pos[1] + n #y of center
        item = self.__canvas.create_text(x, y, text='S', font= 'Arialuni 16 bold', fill='gray25', activefill='gray40',
                tag=('AS','button', 'setting'))
        self.__canvas.tag_bind(item, "<Button-1>", self.onSettingClick)

    def genResizer(self):
        n = self.__resizer_side
        x = self.pos[0] + self.size[0]
        y = self.pos[1] + self.size[1]
        rect_triangle = (x, y, x-n, y, x, y-n)
        resizer = self.__canvas.create_polygon(rect_triangle, fill='green', activefill='lime', tag=('AS','resizer'))

        on_resize = lambda e, dx, dy: self.onResize('resizer', e, dx, dy)
        bindCanvasDragEvents(self.__canvas, resizer, on_resize, 'bottom_right_corner')
    #}}

    #{{ internal operations
    def __getpos(self):
        panel = self.__canvas.find_withtag('panel')
        x, y = self.__canvas.coords(panel)
        return int(x), int(y)

    def move(self, dx, dy):
        self.__canvas.move('AS', dx, dy)

    def lift(self):
        self.__canvas.tag_raise('button')
        self.__canvas.tag_raise('resizer')

    def adjustPos(self):
        if conf.SELECT_AREA_ALIGN:
            try:
                grid_pt = self.__geo_info.getNearbyGridPoint(self.pos)
                if grid_pt is not None:
                    grid_x, grid_y = grid_pt
                    dx = grid_x - self.pos[0]
                    dy = grid_y - self.pos[1]
                    self.move(dx, dy)
            except Exception as ex:
                messagebox.showwarning("Adjust pos error", str(ex))

    def applySettings(self):
        self.scaleGeo()
        self.adjustPos()
        self.checkResizer()

    def scaleGeo(self):
        sz = self.getFixedSize()
        if sz is not None:
            #chck size
            w, h = sz
            if w > self.__canvas.winfo_width() and h > self.__canvas.winfo_height():
                raise AreaSizeTooLarge("The specified size is too large")
            #pos
            pos = max(0, self.pos[0]), max(0, self.pos[1]) #avoid no seeing after resize
            #resize
            self.resize(sz, pos)

    def getFixedSize(self):
        if conf.SELECT_AREA_FIXED:
            w = self.__geo_info.toPixelLength(conf.SELECT_AREA_X)
            h = self.__geo_info.toPixelLength(conf.SELECT_AREA_Y)
            return w, h
        return None

    def resize(self, size, pos=None):
        if self.size == size or \
           size[0] <= self.__button_side*len(self.__canvas.find_withtag('button')) or \
           size[1] <= self.__button_side+self.__resizer_side:
            return
        #bookkeeper
        orig_pos = self.pos
        orig_size = self.size
        if pos is None:
            pos = orig_pos
        dx = pos[0]-orig_pos[0]
        dy = pos[1]-orig_pos[1]
        dw = size[0]-orig_size[0]
        dh = size[1]-orig_size[1]
        #resize panel/borders
        self.makeAreaPanel(pos, size)
        self.makeAreaBorders(pos, size)
        #re-locate others
        self.__canvas.move('button', dx+dw, dy)
        self.__canvas.move('resizer', dx+dw, dy+dh)
        self.lift()

    def checkResizer(self):
        resizer = self.__canvas.find_withtag('resizer')
        if conf.SELECT_AREA_FIXED:
            if resizer:
                self.__canvas.delete(resizer)
        else:
            if not resizer:
                self.genResizer()


    #}} general operations

    #{{ events
    def onOkClick(self, e=None):
        self.__state = 'OK'
        self.exit()

    def onCancelClick(self, e=None):
        self.__state = 'Cancel'
        self.exit()

    def onSettingClick(self, e):
        def isAlignSupport():
            return self.__geo_info.getNearbyGridPoint((0,0)) is not None

        setting = AreaSelectorSettings(self.__canvas, disableds=['align']) if not isAlignSupport() else \
                  AreaSelectorSettings(self.__canvas)
        if setting.show((e.x_root, e.y_root)) == 'OK':
            try:
                self.applySettings()
            except AreaSizeTooLarge as ex:
                self.__except = ex
                self.exit()

    def onMove(self, e, dx, dy):
        self.move(dx, dy)

    def onResize(self, name, e, dx, dy):
        if not conf.SELECT_AREA_FIXED:
            SHIFT, CTRL = 1, 4

            x, y = self.pos
            w, h = self.size
            if e.state & SHIFT:  #reverse direction
                dx, dy = -dx, -dy

            if name == 'top' or e.keysym == 'Up':
                self.resize((w,h-dy), (x,y+dy))
            elif name == 'bottom' or e.keysym == 'Down':
                self.resize((w,h+dy))
            elif name == 'left' or e.keysym == 'Left':
                self.resize((w-dx,h), (x+dx,y))
            elif name == 'right' or e.keysym == 'Right':
                self.resize((w+dx,h))
            elif name == 'resizer':
                self.resize((w+dx,h+dy))
            else:
                raise ValueError("Unknown border '%s' to resize" % (name_,))

    #}}


if __name__ == '__main__':

    testMapSelector()

    '''
    import conf
    hdr1 = (EditBoard.COL_TYPE_BOOL, 'COL1', True)
    hdr2 = (EditBoard.COL_TYPE_PIC, 'COL2', False)
    hdr3 = (EditBoard.COL_TYPE_STR, 'COL3', True)
    hdr4 = (EditBoard.COL_TYPE_STR, 'COL4', False)
    hdrs = (hdr1, hdr2, hdr3, hdr4)

    brd = EditBoard(root, hdrs)
    brd.addClosedHandler(lambda: print('I am on closed'))
    brd.addRow((True, conf.getIcon('summit'), 'Editable Str', 'UnEditable Str'))
    brd.title('I am Dialog')
    brd.show()
    '''

